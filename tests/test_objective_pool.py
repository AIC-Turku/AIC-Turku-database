"""Source-preserving pool inventory, validation, and export boundaries."""
import copy
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader

from scripts.objective_pool import (
    ObjectivePoolError, build_objective_pool_view, load_objective_pool,
    pool_schema, staff_contact_url, validate_pool,
)

ROOT = Path(__file__).resolve().parents[1]


def canonical():
    return load_objective_pool(ROOT)


def by_code(data, code):
    return next(row for row in data['items'] if row['product_code'] == code)


def render(data=None):
    view = build_objective_pool_view(data or canonical(), pool_schema(ROOT))
    env = Environment(loader=FileSystemLoader(ROOT / 'scripts/templates'), autoescape=True)
    return env.get_template('objective_pool.html.j2').render(pool=view, staff_url='https://example.org/contact')


def test_source_inventory_coverage_and_faults():
    data = canonical()
    assert len(data['items']) == 35
    assert sum(i['kind'] == 'objective' for i in data['items']) == 34
    assert {f: sum(i['family_id'] == f for i in data['items']) for f in ['zeiss','leica','olympus','incucyte','nikon']} == {
        'zeiss':18,'leica':11,'olympus':3,'incucyte':2,'nikon':1}
    assert sum(i['condition'] == 'reported_issue' for i in data['items']) == 7
    assert sum(i['condition'] == 'reported_unusable' for i in data['items']) == 1
    assert by_code(data, '1022-818 (1080-398)')['condition_note'] == 'Inner lenses with droplets!'
    assert by_code(data, '4628')['condition'] == 'reported_unusable'
    assert by_code(data, '506082')['condition_note'] == 'problem with UV transmission'
    assert all(i['quantity'] is None and i['location'] is None and i['inspection'] is None for i in data['items'])
    assert all(i['availability'] == 'unconfirmed' for i in data['items'])


def test_unknowns_ranges_original_codes_and_units_are_preserved():
    data = canonical()
    assert data['source']['date_text'] == '020426' and data['source']['date_iso'] is None
    assert data['source']['working_distance_unit'] is None
    assert by_code(data, '506170')['working_distance_text'] is None
    assert by_code(data, '506007')['numerical_aperture_text'] == '1.00-0.50'
    assert by_code(data, '506188')['numerical_aperture_text'] == '1.40-0.60'
    assert by_code(data, '506316')['numerical_aperture_text'] == '1.40-0.70'
    assert by_code(data, '441351-9970')['working_distance_text'] == '2,9 at cover glass 0,75'
    assert by_code(data, '44 07 60 (1100-829)')['name'] == 'Plan-APOCHROMAT 63x/1.4 Oil'
    cal = by_code(data, '420639-9000-700')
    assert cal['magnification'] is None and cal['numerical_aperture_text'] is None
    assert cal['immersion'] == 'not_recorded'
    assert by_code(data, 'MRH 00041')['immersion'] == 'not_recorded'
    assert next(f for f in data['families'] if f['id'] == 'nikon')['mount_text'] is None
    assert next(f for f in data['families'] if f['id'] == 'incucyte')['mount_text'] == 'thread -23 (as written)'


@pytest.mark.parametrize('change', [
    lambda d: d['items'].append(copy.deepcopy(d['items'][0])),
    lambda d: d['families'].append(copy.deepcopy(d['families'][0])),
    lambda d: d['items'][0].update(family_id='missing'),
    lambda d: d['items'][0].update(condition='available'),
    lambda d: d['items'][0].update(magnification=float('nan')),
    lambda d: d['items'][0].update(magnification=0),
    lambda d: d['items'][0].update(magnification=True),
    lambda d: d['items'][0].update(numerical_aperture_text='0'),
    lambda d: d['items'][0].update(condition='reported_issue',condition_note=None),
    lambda d: d['items'][0].update(availability='available'),
    lambda d: d['items'][0].update(condition='verified_serviceable'),
    lambda d: d['items'][0].update(inspection={'date':'2026-02-31','by':'Staff'}),
    lambda d: d['items'][0].update(unknown_field='typo'),
    lambda d: d['items'][0].update(inspection={'date':'2026-09-13','by':'   '}),
    lambda d: d['source'].update(date_iso='020426'),
])
def test_invalid_or_unsupported_state_is_rejected(change):
    data = canonical()
    change(data)
    with pytest.raises(ObjectivePoolError):
        validate_pool(data, pool_schema(ROOT))


def test_explicit_inspection_allows_serviceable_pool_state():
    data = canonical()
    data['items'][0].update(condition='verified_serviceable',availability='available',
                            inspection={'date':'2026-09-13','by':'Test reviewer'})
    validate_pool(data,pool_schema(ROOT))
    row = build_objective_pool_view(data,pool_schema(ROOT))['items'][0]
    assert 'not assessed' not in row['enquiry']


def test_duplicate_yaml_keys_and_missing_file_fail(tmp_path):
    (tmp_path/'inventory').mkdir()
    (tmp_path/'inventory/objective_pool.yaml').write_text('schema_version: 1\nschema_version: 2\n')
    with pytest.raises(ObjectivePoolError):
        load_objective_pool(tmp_path)
    (tmp_path/'inventory/objective_pool.yaml').unlink()
    with pytest.raises(ObjectivePoolError):
        load_objective_pool(tmp_path)


def test_view_is_explicitly_separate_and_does_not_mutate_source():
    data = canonical(); before = copy.deepcopy(data)
    view = build_objective_pool_view(data,pool_schema(ROOT))
    assert data == before
    assert view['inventory_kind'] == 'objective_pool'
    assert view['installed_hardware'] is False
    assert view['compatibility_status'] == 'not_verified'
    assert view['problem_count'] == 8
    assert 'reported-unusable' in by_code(view, '4628')['enquiry']
    assert 'available and suitable' not in by_code(view, '4628')['enquiry']
    html = render()
    assert html.count('class="pool-item"') == 35
    assert 'not installed microscope configurations' in html
    assert 'date format not yet confirmed' in html
    assert 'their units are not stated in the source' in html


def test_html_escapes_source_and_config_urls_are_checked():
    data = canonical()
    data['items'][0]['name'] = '<img src=x onerror="alert(1)">'
    data['items'][0]['source_text'] = '</pre><script>alert(1)</script>'
    html = render(data)
    assert '<img src=x' not in html and '<script>alert' not in html
    assert '&lt;img' in html
    assert staff_contact_url({'contact_url':'javascript:alert(1)'}) is None
    assert staff_contact_url({'contact_url':'//evil.example'}) is None
    assert staff_contact_url({'contact_url':'https://['}) is None
    assert staff_contact_url({'contact_url':'https://example.org/contact'}) == 'https://example.org/contact'


def test_empty_inventory_is_readable():
    data = canonical();data['items']=[]
    assert '0 source records' in render(data)


def test_navigation_and_ci_watch_pool_changes():
    from scripts.dashboard.site_render import build_nav
    assert {'Spare objectives':'objective_pool.md'} in build_nav([],[])
    for name in ['validate.yml','deploy-dashboard.yml']:
        assert '"inventory/**"' in (ROOT/'.github/workflows'/name).read_text()
    source = (ROOT/'scripts/dashboard/site_render.py').read_text()
    assert 'assets" / "objective_pool.json' in source
    assert 'pool_template.render(pool=pool' in source
    for name in ['methods_export.py','llm_export.py']:
        assert 'objective_pool' not in (ROOT/'scripts/dashboard'/name).read_text()


def test_cli_keeps_minimal_instrument_fixtures_but_requires_complete_pool_extension(tmp_path, monkeypatch):
    from scripts.validation import reporting
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(reporting, 'validate_instrument_ledgers', lambda: (set(), [], []))
    monkeypatch.setattr(reporting, 'validate_event_ledgers', lambda **kwargs: SimpleNamespace(errors=[], warnings=[], migration_notices=[]))
    assert reporting.main() == 0
    (tmp_path/'schema').mkdir()
    (tmp_path/'schema/objective_pool.schema.json').write_text('{}')
    assert reporting.main() == 1


def test_every_imported_row_is_grounded_in_the_preserved_source_text():
    normal = lambda value: ' '.join(value.split())
    transcript = normal((ROOT/'docs/sources/objective_pool_020426.txt').read_text())
    for item in canonical()['items']:
        assert normal(item['source_text']) in transcript
        if item['kind'] == 'objective':
            match = re.search(r'(\d+(?:\.\d+)?)x/(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?)', item['source_text'])
            assert match, item['id']
            assert float(match[1]) == item['magnification']
            assert match[2] == item['numerical_aperture_text']
