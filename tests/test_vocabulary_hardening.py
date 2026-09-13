from pathlib import Path
import tempfile
import yaml

import pytest

from scripts.validation.vocabulary import Vocabulary, VocabularyDefinitionError, merge_vocab_registries
from scripts.dashboard.loaders import evaluate_instrument_status
from scripts.build_context import normalize_software
from scripts.lightpath.spectral_ops import _spectral_ops_for_component
from scripts.validation.policy import _load_instrument_policy


def write_vocab(root: Path, name: str, terms):
    (root / 'vocab').mkdir(parents=True, exist_ok=True)
    (root / 'vocab' / f'{name}.yaml').write_text(yaml.safe_dump({'terms': terms}, sort_keys=False))


def test_ambiguous_synonym_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_vocab(tmp_path, 'x', [
        {'id': 'a', 'label': 'A', 'description': 'A', 'synonyms': ['same']},
        {'id': 'b', 'label': 'B', 'description': 'B', 'synonyms': ['same']},
    ])
    with pytest.raises(VocabularyDefinitionError, match='ambiguous'):
        Vocabulary(tmp_path / 'vocab')


def test_synonym_cannot_shadow_other_canonical_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_vocab(tmp_path, 'x', [
        {'id': 'air', 'label': 'Air', 'description': 'Air'},
        {'id': 'water', 'label': 'Water', 'description': 'Water', 'synonyms': ['air']},
    ])
    with pytest.raises(VocabularyDefinitionError, match='shadows canonical id'):
        Vocabulary(tmp_path / 'vocab')


def test_registry_conflict_is_rejected():
    with pytest.raises(VocabularyDefinitionError, match='inconsistently'):
        merge_vocab_registries({'x': {'path': 'vocab/a.yaml'}}, {'x': {'path': 'vocab/b.yaml'}})


def test_offline_synonym_cannot_render_online():
    repo = Path(__file__).resolve().parents[1]
    vocab = Vocabulary(repo / 'vocab', vocab_registry={
        'maintenance_status': {'source': 'file', 'path': 'vocab/maintenance_status.yaml'}
    })
    result = evaluate_instrument_status(None, {'microscope_status_after': 'offline'}, vocab)
    assert result['color'] == 'red'
    assert 'Offline' in result['badge']


def test_unknown_explicit_status_is_fail_safe():
    result = evaluate_instrument_status(None, {'microscope_status_after': 'OUT_OF_SERVCE'})
    assert result['color'] == 'yellow'
    assert 'unknown' in result['badge'].lower()


def test_software_role_aliases_and_future_roles_are_not_collapsed():
    assert normalize_software([{'role': 'capture', 'name': 'X'}])[0]['role'] == 'acquisition'
    assert normalize_software([{'role': 'quantification', 'name': 'X'}])[0]['role'] == 'analysis'
    assert normalize_software([{'role': 'quality_control', 'name': 'X'}])[0]['role'] == 'quality_control'


def test_neutral_density_is_explicitly_unsupported_not_silent_passthrough():
    ops = _spectral_ops_for_component({'component_type': 'neutral_density'})
    assert ops['illumination'][0]['unsupported_reason'] == 'neutral_density_attenuation_not_modeled'
    assert ops['detection'][0]['unsupported_reason'] == 'neutral_density_attenuation_not_modeled'


def test_policy_rejects_misspelled_allowed_constraint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'schema').mkdir()
    (tmp_path / 'schema' / 'instrument_policy.yaml').write_text(yaml.safe_dump({
        'vocab_registry': {},
        'sections': [{'id': 'x', 'rules': [{'path': 'x', 'status': 'optional', 'type': 'string', 'allowed': ['a']}]}],
    }, sort_keys=False))
    policy, error = _load_instrument_policy(Path('schema/instrument_policy.yaml'))
    assert policy is None
    assert "use 'allowed_values'" in error


def test_deployment_watches_vocabulary_changes():
    repo = Path(__file__).resolve().parents[1]
    workflow = (repo / '.github/workflows/deploy-dashboard.yml').read_text()
    assert '"vocab/**"' in workflow
    assert '"schema/**"' in workflow

def test_duplicate_yaml_keys_are_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'vocab').mkdir()
    (tmp_path / 'vocab' / 'x.yaml').write_text(
        'terms:\n  - id: a\n    label: A\n    label: B\n    description: A\n'
    )
    with pytest.raises(VocabularyDefinitionError, match='Duplicate YAML key'):
        Vocabulary(tmp_path / 'vocab')


def test_broken_cross_vocabulary_reference_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_vocab(tmp_path, 'imaging_modes', [
        {'id': 'widefield', 'label': 'Widefield', 'description': 'Widefield'},
    ])
    write_vocab(tmp_path, 'contrast_methods', [
        {'id': 'bf', 'label': 'BF', 'description': 'Brightfield'},
    ])
    write_vocab(tmp_path, 'optical_routes', [
        {'id': 'route', 'label': 'Route', 'description': 'Route', 'covers': {'imaging_modes': ['missing'], 'contrast_methods': []}},
    ])
    with pytest.raises(VocabularyDefinitionError, match='unknown referenced term'):
        Vocabulary(tmp_path / 'vocab')


def test_invalid_branch_mode_is_rejected_by_lightpath_contract():
    from scripts.lightpath.validate_contract import validate_light_path
    payload = {
        'hardware': {
            'sources': [{'id': 's'}],
            'optical_path_elements': [{'id': 'split'}],
            'endpoints': [{'id': 'd'}],
        },
        'light_paths': [{
            'id': 'r', 'route_type': 'widefield_fluorescence',
            'illumination_sequence': [{'source_id': 's'}],
            'detection_sequence': [
                {'optical_path_element_id': 'split'},
                {'branches': {'selection_mode': 'exclusive', 'items': [
                    {'branch_id': 'b', 'mode': 'sideways', 'sequence': [{'endpoint_id': 'd'}]},
                ]}},
            ],
        }],
    }
    errors = validate_light_path(payload)
    assert any('.mode:' in error and 'transmitted' in error for error in errors)
