from __future__ import annotations

from scripts._vocab_audit_patch_common import ROOT, write

write(
    "tests/test_vocabulary_second_audit.py",
    '''from pathlib import Path
from unittest import mock

import pytest
import yaml

from scripts.autofix_yaml import _canonicalize_rule_values, parse_args
from scripts.build_context import normalize_software
from scripts.dashboard.site_render import build_vocabulary_dictionary_markdown
from scripts.lightpath.model import _detector_class, _normalize_endpoint_type, _normalize_light_source_kind, get_active_vocab, set_active_vocab
from scripts.validation.events import validate_event_ledgers
from scripts.validation.instrument import build_instrument_completeness_report
from scripts.validation.model import InstrumentPolicy, PolicyRule
from scripts.validation.policy import _build_item_field_vocab_index, _build_path_vocab_index, _evaluate_required_if, load_policy
from scripts.validation.vocabulary import Vocabulary, VocabularyDefinitionError, build_repository_vocabulary

ROOT = Path(__file__).resolve().parents[1]


def write_vocab(root: Path, name: str, terms) -> Path:
    path = root / 'vocab' / f'{name}.yaml'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({'terms': terms}, sort_keys=False, allow_unicode=True), encoding='utf-8')
    return path


def test_completeness_vocabulary_failure_propagates_not_nameerror(tmp_path):
    policy = InstrumentPolicy(policy_path=tmp_path / 'policy.yaml', vocab_registry={'broken': {'source': 'file', 'path': 'vocab/missing.yaml'}}, rules=[])
    with mock.patch('scripts.validation.instrument._load_instrument_policy', return_value=(policy, None)):
        with pytest.raises(VocabularyDefinitionError):
            build_instrument_completeness_report({})


def _minimal_event_policy(record_type: str, vocab_path: str, *, allow_empty: bool = False):
    rule = {'path': 'state', 'status': 'optional', 'type': 'enum', 'vocab': 'state'}
    if allow_empty:
        rule['allow_empty'] = True
    return {
        'record_type': record_type,
        'vocab_registry': {'state': {'source': 'file', 'path': vocab_path, 'canonical_ids_only': True, 'allow_synonyms_on_input': True}},
        'field_rules': [
            {'path': 'microscope', 'status': 'required', 'type': 'instrument_id'},
            {'path': 'record_type', 'status': 'required', 'type': 'string'},
            rule,
        ],
        'legacy_and_migration_rules': [],
        'cross_field_rules': [],
    }


def _write_event_fixture(tmp_path: Path, value: str, *, allow_empty: bool = False):
    write_vocab(tmp_path, 'state', [{'id': 'ok', 'label': 'OK', 'description': 'ok'}])
    schema = tmp_path / 'schema'; schema.mkdir()
    for filename, record_type in (('QC_policy.yaml', 'qc_session'), ('maintenance_policy.yaml', 'maintenance_event')):
        (schema / filename).write_text(yaml.safe_dump(_minimal_event_policy(record_type, 'vocab/state.yaml', allow_empty=allow_empty), sort_keys=False), encoding='utf-8')
    event_dir = tmp_path / 'qc/sessions/scope-test/2026'; event_dir.mkdir(parents=True)
    (event_dir / '2026-01-01_test.yaml').write_text(yaml.safe_dump({'microscope': 'scope-test', 'record_type': 'qc_session', 'started_utc': '2026-01-01T00:00:00Z', 'state': value}, sort_keys=False), encoding='utf-8')


def test_unknown_canonical_event_vocab_term_is_error(tmp_path, monkeypatch):
    _write_event_fixture(tmp_path, 'typo'); monkeypatch.chdir(tmp_path)
    report = validate_event_ledgers(instrument_ids={'scope-test'})
    assert any(item.code == 'unknown_vocab_term' for item in report.errors)
    assert not any(item.code == 'unknown_vocab_term' for item in report.warnings)


def test_explicit_allow_empty_skips_vocab_validation_without_inventing_unitless(tmp_path, monkeypatch):
    _write_event_fixture(tmp_path, '', allow_empty=True); monkeypatch.chdir(tmp_path)
    report = validate_event_ledgers(instrument_ids={'scope-test'})
    assert not any(item.code in {'unknown_vocab_term', 'invalid_field_type'} and item.path.endswith(':state') for item in [*report.errors, *report.warnings])


def test_policy_duplicate_keys_are_rejected(tmp_path):
    path = tmp_path / 'policy.yaml'
    path.write_text('record_type: qc_session\\nrecord_type: maintenance_event\\nfield_rules: []\\n', encoding='utf-8')
    payload, error = load_policy(path)
    assert payload is None
    assert 'Duplicate YAML key' in error


def test_classified_values_are_preserved_and_not_rewrite_synonyms(tmp_path):
    write_vocab(tmp_path, 'objective_specialties', [{'id': 'dic', 'label': 'DIC', 'description': 'DIC', 'synonyms': ['DIC'], 'classified_values': ['DIC Prism A']}])
    vocabulary = Vocabulary(tmp_path / 'vocab')
    assert vocabulary.resolve_canonical('objective_specialties', 'DIC') == 'dic'
    assert vocabulary.resolve_canonical('objective_specialties', 'DIC Prism A') is None
    assert vocabulary.classify_canonical('objective_specialties', 'DIC Prism A') == 'dic'
    data = {'specialties': ['DIC', 'DIC Prism A']}
    changed = _canonicalize_rule_values(data, [('specialties', 'objective_specialties')], vocabulary)
    assert changed == 1
    assert data['specialties'] == ['dic', 'DIC Prism A']


def test_repository_objective_prism_is_classification_not_synonym():
    vocabulary = build_repository_vocabulary(ROOT)
    assert vocabulary.resolve_canonical('objective_specialties', 'DIC Prism A') is None
    assert vocabulary.classify_canonical('objective_specialties', 'DIC Prism A') == 'dic'


def test_autofix_is_read_only_by_default_and_validates_before_pr():
    assert parse_args([]).write is False
    source = (ROOT / 'scripts/autofix_yaml.py').read_text(encoding='utf-8')
    assert 'load_vocabs' not in source and 'metric_class_rules' not in source
    workflow = (ROOT / '.github/workflows/autofix.yml').read_text(encoding='utf-8')
    assert 'scripts/autofix_yaml.py --write' in workflow
    assert workflow.index('python -m scripts.validate') < workflow.index('peter-evans/create-pull-request')
    assert workflow.index('python -m scripts.dashboard_builder --strict') < workflow.index('peter-evans/create-pull-request')


def test_required_if_canonicalizes_generic_membership_operators(tmp_path):
    write_vocab(tmp_path, 'role', [{'id': 'excitation', 'label': 'Excitation', 'description': 'x', 'synonyms': ['illumination']}])
    write_vocab(tmp_path, 'state', [{'id': 'online', 'label': 'Online', 'description': 'x', 'synonyms': ['available']}])
    vocabulary = Vocabulary(tmp_path / 'vocab', vocab_registry={'role': {'source': 'file', 'path': 'vocab/role.yaml'}, 'state': {'source': 'file', 'path': 'vocab/state.yaml'}})
    rules = [PolicyRule(path='hardware.sources[].role', status='optional', field_type='string', vocab='role'), PolicyRule(path='state', status='optional', field_type='string', vocab='state')]
    item_index = _build_item_field_vocab_index(rules); path_index = _build_path_vocab_index(rules)
    payload = {'hardware': {'sources': [{'role': 'illumination'}]}, 'state': 'available'}
    for condition in [
        {'any_item_field_in': {'path': 'hardware.sources[]', 'field': 'role', 'values': ['excitation']}},
        {'any_item_matches': {'path': 'hardware.sources[]', 'field_in': {'role': ['excitation']}}},
        {'field_equals_any': {'field': 'state', 'values': ['online']}},
    ]:
        assert _evaluate_required_if(condition, payload=payload, item_context=None, vocabulary=vocabulary, item_field_vocabs=item_index.get('hardware.sources[]'), path_vocabs=path_index)


def test_downstream_normalization_uses_vocabulary_authority():
    vocabulary = build_repository_vocabulary(ROOT); old = get_active_vocab(); set_active_vocab(vocabulary)
    try:
        assert _normalize_light_source_kind('laser_diode') == 'laser'
        assert _detector_class('sCMOS') == 'camera'
        assert _normalize_endpoint_type('ocular') == 'eyepiece'
    finally:
        set_active_vocab(old)
    assert normalize_software([{'role': 'capture', 'name': 'X'}])[0]['role'] == 'acquisition'
    assert normalize_software([{'role': 'quality_control', 'name': 'X'}])[0]['role'] == 'quality_control'
    build_context = (ROOT / 'scripts/build_context.py').read_text(encoding='utf-8')
    lightpath_model = (ROOT / 'scripts/lightpath/model.py').read_text(encoding='utf-8')
    full_audit = (ROOT / 'scripts/full_audit.py').read_text(encoding='utf-8')
    assert 'legacy_role_map' not in build_context
    assert '_LIGHT_SOURCE_KIND_ALIASES' not in lightpath_model
    assert 'CAMERA_DETECTOR_KINDS' not in lightpath_model
    assert 'POINT_DETECTOR_KINDS' not in lightpath_model and 'POINT_DETECTOR_KINDS' not in full_audit


def test_dictionary_deduplicates_registry_aliases_and_labels_classification(tmp_path):
    path = write_vocab(tmp_path, 'x', [{'id': 'a', 'label': 'A', 'description': 'A', 'synonyms': ['alpha'], 'classified_values': ['A subtype']}])
    vocabulary = Vocabulary(tmp_path / 'vocab', vocab_registry={'alias_a': {'source': 'file', 'path': str(path)}, 'alias_b': {'source': 'file', 'path': str(path)}})
    rendered = build_vocabulary_dictionary_markdown(vocabulary)
    assert rendered.count('`a`') == 1
    assert '`alias_a`' in rendered and '`alias_b`' in rendered
    assert 'Classified values (preserved)' in rendered and 'A subtype' in rendered


def test_temporary_vocabulary_transfer_machinery_is_removed():
    assert not (ROOT / '.vocab-transfer').exists()
    assert not (ROOT / '.github/workflows/apply-vocabulary-hardening.yml').exists()
''',
)

print("Added second-audit regression tests")
