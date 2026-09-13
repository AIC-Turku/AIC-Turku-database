"""Unified discovery must not change ownership, installation or source facts."""
import copy
import json
from pathlib import Path
from functools import lru_cache

import pytest
from jinja2 import Environment, FileSystemLoader

from scripts.dashboard.loaders import load_instruments, load_facility_config
from scripts.dashboard.site_render import _build_vocabulary
from scripts.dashboard.objective_catalogue import (
    ObjectiveCatalogueError, build_objective_catalogue_view, instrument_catalogue_link,
)
from scripts.objective_pool import load_objective_pool, pool_schema, build_objective_pool_view

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _load_inputs():
    facility = load_facility_config(ROOT)['facility']
    instruments = load_instruments(str(ROOT/'instruments')) + load_instruments(str(ROOT/'instruments'), include_retired=True)
    pool = build_objective_pool_view(load_objective_pool(ROOT), pool_schema(ROOT), facility)
    return pool, instruments, _build_vocabulary(ROOT), facility


def inputs():
    pool, instruments, vocab, facility = _load_inputs()
    return copy.deepcopy(pool), copy.deepcopy(instruments), vocab, copy.deepcopy(facility)


def catalogue():
    return build_objective_catalogue_view(*inputs())


def render_catalogue(view=None):
    env = Environment(loader=FileSystemLoader(ROOT/'scripts/templates'), autoescape=True)
    return env.get_template('objective_pool.html.j2').render(pool=view or catalogue(), staff_url=None)


def fixture(installed_marker='omit', *, identifier='source-objective', retired=False):
    objective = {'id': identifier, 'model': 'Objective model', 'manufacturer': 'Zeiss',
                 'magnification': 40, 'numerical_aperture': 1.2, 'immersion': 'water',
                 'product_code': 'SAME-CODE', 'working_distance': '0.62 mm', 'notes': 'Recorded note'}
    if installed_marker != 'omit':
        objective['is_installed'] = installed_marker
    return {'retired': retired, 'canonical': {'instrument': {'instrument_id': 'scope-fixture',
            'display_name': 'Fixture microscope', 'location': 'Room 1'}, 'hardware': {'objectives': [objective]}}}


def fixture_view(inst, pool=None):
    original_pool, _, vocab, _ = inputs()
    return build_objective_catalogue_view(pool or original_pool, [inst], vocab)


def test_complete_catalogue_coverage_states_and_synthetic_exclusion():
    view = catalogue()
    assert view['total'] == 137
    assert view['current_count'] == 135
    assert view['spare_count'] == 35 and view['instrument_count'] == 100
    assert view['historical_count'] == 2
    assert view['problem_count'] == 8
    assert view['excluded_instrument_ids'] == ['scope-testx1']
    assert all(row['instrument_id'] != 'scope-testx1' for row in view['items'])
    assert sum(row['installation_status'] == 'installed' and not row['retired'] for row in view['items']) == 90
    assert sum(row['installation_status'] == 'not_installed' for row in view['items']) == 10


@pytest.mark.parametrize('flag,expected', [(True,'installed'), (False,'not_installed'), (None,'unconfirmed'), ('omit','unconfirmed')])
def test_explicit_boolean_and_unknown_states_are_not_guessed(flag, expected):
    row = fixture_view(fixture(flag))['items'][0]
    assert row['installation_status'] == expected
    assert row['is_installed'] is (None if flag == 'omit' else flag)
    assert row['source_kind'] == 'instrument'
    assert row['condition'] == 'not_assessed'
    assert row['availability'] == 'unconfirmed'
    assert row['enquiry'] is None


def test_non_boolean_flag_is_rejected_not_coerced():
    with pytest.raises(ObjectiveCatalogueError, match='boolean'):
        fixture_view(fixture('false'))


def test_ids_are_stable_not_deduplicated_by_model_or_product_code():
    pool, _, vocab, _ = inputs()
    pool['items'][0]['product_code'] = 'SAME-CODE'
    inst = fixture(True)
    other = copy.deepcopy(inst)
    other['canonical']['instrument'].update(instrument_id='scope-second', display_name='Second microscope')
    view = build_objective_catalogue_view(pool, [inst, other], vocab)
    same = [row for row in view['items'] if row.get('product_code') == 'SAME-CODE']
    assert len(same) == 3 and len({row['id'] for row in same}) == 3
    reverse = build_objective_catalogue_view(pool, [other, inst], vocab)
    assert {row['id'] for row in reverse['items']} == {row['id'] for row in view['items']}
    assert same[0]['instrument_url'] == '../instruments/scope-fixture/#objectives'
    assert instrument_catalogue_link('scope-fixture') == '../../objective_pool.md?instrument=scope-fixture'


def test_source_views_and_hardware_are_unchanged():
    pool, instruments, vocab, facility = inputs()
    before_pool, before_inst = copy.deepcopy(pool), copy.deepcopy(instruments)
    view = build_objective_catalogue_view(pool, instruments, vocab, facility)
    assert pool == before_pool and instruments == before_inst
    assert view['inventory_kind'] == 'objective_catalogue'
    assert view['authoritative_for_installation'] is False
    source_rows = {inst['canonical']['instrument']['instrument_id']: inst['canonical']['hardware']['objectives'] for inst in instruments}
    for row in view['items']:
        if row['source_kind'] == 'instrument':
            source = next(obj for obj in source_rows[row['instrument_id']] if obj['id'] == row['objective_id'])
            assert source == row['source_record']['objective'] == json.loads(row['source_text'])
        else:
            source = next(obj for obj in pool['items'] if obj['id'] == row['id'])
            for key in ['source_text','condition','condition_note','enquiry','quantity','availability','product_code']:
                assert row[key] == source[key]


def test_units_optional_notes_and_retired_status_stay_distinct():
    view = catalogue()
    optional = next(row for row in view['items'] if row['instrument_id'] == 'scope-olympus-bx60' and row['objective_id'] == '60x_oil')
    assert optional['installation_status'] == 'not_installed'
    assert 'Optional objective' in optional['notes']
    assert optional['working_distance_label'] == 'Not recorded'
    assert all('Historical record' in row['association_label'] for row in view['items'] if row['retired'])
    assert all(row['source_kind'] == 'instrument' for row in view['items'] if row['retired'])
    pool_wd = next(row for row in view['items'] if row['id'] == 'pool-zeiss-441351-9970')
    assert pool_wd['working_distance_label'] == '2,9 at cover glass 0,75'
    assert 'unit unconfirmed' in pool_wd['working_distance_heading']
    assert fixture_view(fixture())['items'][0]['working_distance_label'] == '0.62 mm'


@pytest.mark.parametrize('config', [None, {'exclude_instrument_ids': 'scope-fixture'},
    {'exclude_instrument_ids':['not-a-scope']}, {'exclude_instrument_ids':['scope-fixture','scope-fixture']}, {'typo': []}])
def test_bad_exclusion_config_does_not_silently_drop_records(config):
    pool, _, vocab, _ = inputs()
    with pytest.raises(ObjectiveCatalogueError):
        build_objective_catalogue_view(pool, [fixture()], vocab, {'objective_catalogue': config})


def test_missing_or_duplicate_source_ids_fail_instead_of_merging():
    inst = fixture()
    inst['canonical']['hardware']['objectives'].append(copy.deepcopy(inst['canonical']['hardware']['objectives'][0]))
    with pytest.raises(ObjectiveCatalogueError, match='unique'):
        fixture_view(inst)
    with pytest.raises(ObjectiveCatalogueError, match='stable source ID'):
        fixture_view(fixture(identifier=''))


def test_source_display_is_escaped_and_stock_is_not_invented():
    inst = fixture(False)
    inst['canonical']['instrument']['display_name'] = '<script>alert(1)</script>'
    inst['canonical']['hardware']['objectives'][0]['notes'] = '</p><img src=x onerror=alert(1)>'
    view = fixture_view(inst)
    html = render_catalogue(view)
    assert '<script>alert' not in html and '<img src=x' not in html
    assert '&lt;script&gt;' in html
    assert 'Ask staff; not a loan offer' in html
    assert 'objective-scope-fixture--source-objective' in html
