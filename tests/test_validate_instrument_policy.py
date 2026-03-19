import os
import tempfile
import unittest
from pathlib import Path

import json
import sys
import types

yaml_stub = types.ModuleType('yaml')


class _YamlError(Exception):
    pass


def _safe_load(value):
    return json.loads(value)


yaml_stub.safe_load = _safe_load
yaml_stub.YAMLError = _YamlError
sys.modules.setdefault('yaml', yaml_stub)


from scripts.validate import (
    _evaluate_required_if,
    _is_valid_instrument_id,
    _resolve_rule_nodes,
    Vocabulary,
    build_instrument_completeness_report,
    validate_instrument_ledgers,
)


class InstrumentPolicyValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmpdir.name)
        self.prev_cwd = Path.cwd()
        os.chdir(self.repo)
        (self.repo / 'schema').mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        self._tmpdir.cleanup()

    def _write_json_yaml(self, relative: str, payload: dict) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding='utf-8')

    def test_resolve_rule_nodes_emits_missing_leaf_for_existing_parent_items(self) -> None:
        payload = {
            'hardware': {
                'filters': [
                    {'kind': 'emission'},
                    {'kind': 'excitation', 'name': 'Filter B'},
                ]
            }
        }

        nodes = _resolve_rule_nodes(payload, 'hardware.filters[].name')

        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].path, 'hardware.filters[0].name')
        self.assertIsNone(nodes[0].value)
        self.assertEqual(nodes[1].path, 'hardware.filters[1].name')
        self.assertEqual(nodes[1].value, 'Filter B')


    def test_resolve_rule_nodes_keeps_root_list_as_single_node(self) -> None:
        payload = {'software': [{'role': 'acquisition', 'name': 'NIS-Elements AR'}]}

        nodes = _resolve_rule_nodes(payload, 'software[]')

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].path, 'software')
        self.assertIsInstance(nodes[0].value, list)
        self.assertEqual(len(nodes[0].value), 1)

    def test_slug_validation_accepts_underscore_separated_light_path_ids(self) -> None:
        self.assertTrue(_is_valid_instrument_id('laserstack_v4'))
        self.assertTrue(_is_valid_instrument_id('405_nm'))
        self.assertTrue(_is_valid_instrument_id('camera_port'))
        self.assertTrue(_is_valid_instrument_id('scope-1'))
        self.assertFalse(_is_valid_instrument_id('invalid slug'))
        self.assertFalse(_is_valid_instrument_id('UPPER'))

    def test_evaluate_required_if_supports_compound_all_of_any_of(self) -> None:
        vocabulary = Vocabulary(vocab_registry={'modalities': {'source': 'inline', 'allowed_values': ['flim', 'sim']}})
        payload = {
            'software': [{'role': 'analysis', 'version': '1.0'}],
            'hardware': {'scanner': {'type': 'resonant'}},
            'modalities': ['sim'],
        }

        condition = {
            'all_of': [
                {'parent_present': 'software[]'},
                {
                    'any_of': [
                        {'scanner_type_in': ['resonant']},
                        {'modalities_any_of': ['flim']},
                    ]
                },
            ]
        }

        self.assertTrue(_evaluate_required_if(condition, payload=payload, item_context=None, vocabulary=vocabulary))

        payload['hardware']['scanner']['type'] = 'galvo'
        payload['modalities'] = ['sim']
        self.assertFalse(_evaluate_required_if(condition, payload=payload, item_context=None, vocabulary=vocabulary))

        self.assertFalse(
            _evaluate_required_if(
                {'parent_present': 'software[]', 'scanner_type_in': ['resonant']},
                payload=payload,
                item_context=None,
                vocabulary=vocabulary,
            )
        )


    def test_evaluate_required_if_supports_modules_and_detector_kind_conditions(self) -> None:
        vocabulary = Vocabulary(
            vocab_registry={
                'modules': {'source': 'inline', 'allowed_values': ['incubation', 'hardware_autofocus']},
                'detector_kinds': {'source': 'inline', 'allowed_values': ['scmos', 'pmt']},
            }
        )
        payload = {
            'modules': [{'name': 'incubation'}],
            'hardware': {'detectors': [{'kind': 'scmos'}]},
        }

        self.assertTrue(
            _evaluate_required_if(
                {'modules_any_of': ['incubation']},
                payload=payload,
                item_context=None,
                vocabulary=vocabulary,
            )
        )
        self.assertTrue(
            _evaluate_required_if(
                {'detector_kinds_any_of': ['scmos']},
                payload=payload,
                item_context=None,
                vocabulary=vocabulary,
            )
        )
        self.assertTrue(
            _evaluate_required_if(
                {'any_of': [{'modules_any_of': ['hardware_autofocus']}, {'detector_kinds_any_of': ['scmos']}]},
                payload=payload,
                item_context=None,
                vocabulary=vocabulary,
            )
        )
        self.assertFalse(
            _evaluate_required_if(
                {'modules_any_of': ['hardware_autofocus']},
                payload=payload,
                item_context=None,
                vocabulary=vocabulary,
            )
        )

        self.assertTrue(
            _evaluate_required_if(
                {'software_roles_any_of': ['acquisition']},
                payload={
                    'software': [
                        {'role': 'acquisition', 'name': 'ZEN'},
                        {'role': 'analysis', 'name': 'ImageJ'},
                    ]
                },
                item_context=None,
                vocabulary=vocabulary,
            )
        )
        self.assertTrue(
            _evaluate_required_if(
                {'software_roles_none_of': ['acquisition']},
                payload={'software': [{'role': 'processing', 'name': 'Huygens'}]},
                item_context=None,
                vocabulary=vocabulary,
            )
        )
        self.assertFalse(
            _evaluate_required_if(
                {'software_roles_none_of': ['acquisition']},
                payload={'software': [{'role': 'acquisition', 'name': 'ZEN'}]},
                item_context=None,
                vocabulary=vocabulary,
            )
        )

        self.assertTrue(
            _evaluate_required_if(
                {'software_roles_any_of': ['analysis']},
                payload={'software': {'analysis': {'name': 'ImageJ'}}},
                item_context=None,
                vocabulary=vocabulary,
            )
        )
        self.assertFalse(
            _evaluate_required_if(
                {'software_roles_none_of': ['analysis']},
                payload={'software': {'analysis': {'name': 'ImageJ'}}},
                item_context=None,
                vocabulary=vocabulary,
            )
        )



    def test_evaluate_required_if_modules_any_of_uses_type_field(self) -> None:
        vocabulary = Vocabulary(vocab_registry={'modules': {'source': 'inline', 'allowed_values': ['incubation']}})
        payload = {'modules': [{'type': 'incubation'}]}
        self.assertTrue(
            _evaluate_required_if(
                {'modules_any_of': ['incubation']},
                payload=payload,
                item_context=None,
                vocabulary=vocabulary,
            )
        )

    def test_validate_instrument_ledgers_warns_when_product_code_duplicates_model_or_name(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {},
                'sections': [
                    {
                        'id': 'hardware',
                        'title': 'Hardware',
                        'rules': [
                            {'path': 'hardware.sources', 'status': 'optional', 'type': 'list', 'item_type': 'object'},
                            {'path': 'hardware.sources[].model', 'status': 'optional', 'type': 'string'},
                            {'path': 'hardware.sources[].name', 'status': 'optional', 'type': 'string'},
                            {'path': 'hardware.sources[].product_code', 'status': 'optional', 'type': 'string'},
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/example.yaml',
            {
                'instrument': {'instrument_id': 'scope-1', 'display_name': 'Scope 1'},
                'hardware': {
                    'sources': [
                        {'id': 'src_1', 'model': 'OBIS 488', 'product_code': 'OBIS 488'},
                        {'id': 'src_2', 'name': 'Blue laser', 'product_code': 'Blue laser'},
                        {'id': 'src_3', 'name': 'Blue laser', 'model': 'OBIS 488', 'product_code': 'SKU-001'},
                    ],
                    'endpoints': [{'id': 'cam_main', 'endpoint_type': 'camera'}],
                },
                'light_paths': [{'id': 'epi', 'illumination_sequence': [{'source_id': 'src_1'}], 'detection_sequence': [{'endpoint_id': 'cam_main'}]}],
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertEqual(issues, [])
        redundant = [w for w in warnings if w.code == 'redundant_product_code']
        self.assertEqual(len(redundant), 2)

    def test_validate_instrument_ledgers_warns_when_name_duplicates_model(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {},
                'sections': [
                    {
                        'id': 'hardware',
                        'title': 'Hardware',
                        'rules': [
                            {'path': 'hardware.sources', 'status': 'optional', 'type': 'list', 'item_type': 'object'},
                            {'path': 'hardware.sources[].model', 'status': 'optional', 'type': 'string'},
                            {'path': 'hardware.sources[].name', 'status': 'optional', 'type': 'string'},
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/example.yaml',
            {
                'instrument': {'instrument_id': 'scope-1', 'display_name': 'Scope 1'},
                'hardware': {
                    'sources': [
                        {'id': 'src_a', 'name': 'OBIS 488', 'model': 'OBIS 488'},
                        {'id': 'src_b', 'name': 'Blue laser', 'model': 'OBIS 488'},
                    ],
                    'endpoints': [{'id': 'cam_main', 'endpoint_type': 'camera'}],
                },
                'light_paths': [{'id': 'epi', 'illumination_sequence': [{'source_id': 'src_a'}], 'detection_sequence': [{'endpoint_id': 'cam_main'}]}],
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertEqual(issues, [])
        redundant = [w for w in warnings if w.code == 'redundant_name_model']
        self.assertEqual(len(redundant), 1)
        self.assertIn('name', redundant[0].message)

    def test_validate_instrument_ledgers_reports_legacy_topology_as_migration_only(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {},
                'sections': [
                    {
                        'id': 'hardware',
                        'title': 'Hardware',
                        'rules': [
                            {'path': 'hardware.sources', 'status': 'optional', 'type': 'list', 'item_type': 'object'},
                            {'path': 'hardware.optical_path_elements', 'status': 'optional', 'type': 'list', 'item_type': 'object'},
                            {'path': 'hardware.endpoints', 'status': 'optional', 'type': 'list', 'item_type': 'object'},
                            {'path': 'light_paths', 'status': 'optional', 'type': 'list', 'item_type': 'object'},
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/example.yaml',
            {
                'instrument': {'instrument_id': 'scope-1', 'display_name': 'Scope 1'},
                'hardware': {
                    'light_sources': [{'kind': 'laser', 'wavelength_nm': 488, 'path': 'epi'}],
                    'light_path': {
                        'excitation_mechanisms': [{'positions': {1: {'component_type': 'bandpass', 'center_nm': 488, 'width_nm': 10}}}],
                    },
                },
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertEqual(issues, [])
        legacy_messages = [w.message for w in warnings if w.code == 'legacy_topology_present']
        self.assertTrue(any("hardware.light_sources" in msg for msg in legacy_messages))
        self.assertTrue(any("hardware.light_path.excitation_mechanisms" in msg for msg in legacy_messages))

    def test_completeness_report_preserves_used_by_and_flags_missing_item_leaf(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {'modalities': {'source': 'inline', 'allowed_values': ['flim', 'sim']}},
                'sections': [
                    {
                        'id': 'hardware',
                        'title': 'Hardware',
                        'rules': [
                            {
                                'path': 'hardware.filters[].name',
                                'status': 'conditional',
                                'type': 'string',
                                'required_if': {'parent_present': 'hardware.filters[]'},
                                'used_by': ['dashboard', 'audit_pdf'],
                            }
                        ],
                    }
                ],
            },
        )

        report = build_instrument_completeness_report(
            {
                'hardware': {
                    'filters': [
                        {'kind': 'emission'},
                        {'kind': 'excitation', 'name': 'Filter B'},
                    ]
                }
            }
        )

        self.assertTrue(report.missing_conditional)
        rule_entry = report.sections[0]['rules'][0]
        self.assertEqual(rule_entry['used_by'], ['dashboard', 'audit_pdf'])
        self.assertTrue(rule_entry['missing'])
        self.assertEqual(report.missing_conditional[0]['used_by'], ['dashboard', 'audit_pdf'])
        self.assertEqual(report.missing_conditional[0]['section_id'], 'hardware')
        self.assertTrue(report.missing_conditional[0]['condition_triggered'])



    def test_vocabulary_loading_from_registry_files(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {
                    'light_source_roles': {'source': 'file', 'path': 'vocab/light_source_roles.yaml'}
                },
                'sections': [],
            },
        )
        self._write_json_yaml(
            'vocab/light_source_roles.yaml',
            {
                'terms': [
                    {'id': 'excitation', 'label': 'Excitation', 'description': '', 'synonyms': ['exc']},
                    {'id': 'depletion', 'label': 'Depletion', 'description': '', 'synonyms': ['sted']},
                ]
            },
        )

        vocabulary = Vocabulary(vocab_registry={'light_source_roles': {'source': 'file', 'path': 'vocab/light_source_roles.yaml'}})
        self.assertEqual(vocabulary.resolve_canonical('light_source_roles', 'sted'), 'depletion')
        self.assertTrue(vocabulary.check('light_source_roles', 'excitation')[0])

    def test_validate_instrument_ledgers_returns_only_instruments_without_blocking_issues(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {},
                'sections': [
                    {
                        'id': 'hardware',
                        'title': 'Hardware',
                        'rules': [
                            {'path': 'hardware.detectors', 'status': 'required', 'type': 'list', 'min_items': 1},
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/valid.yaml',
            {
                'instrument': {'instrument_id': 'valid-scope'},
                'hardware': {'detectors': [{'kind': 'scmos'}]},
            },
        )
        self._write_json_yaml(
            'instruments/invalid.yaml',
            {
                'instrument': {'instrument_id': 'invalid-scope'},
                'hardware': {},
            },
        )

        instrument_ids, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertIn('valid-scope', instrument_ids)
        self.assertIn('invalid-scope', instrument_ids)
        self.assertIn('missing_required_field', {warning.code for warning in warnings})

    def test_missing_canonical_and_alias_detector_pixel_fields_do_not_emit_false_superseded_warning(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {
                    'detector_kinds': {'source': 'inline', 'allowed_values': ['scmos']},
                },
                'sections': [
                    {
                        'id': 'detectors',
                        'title': 'Detectors',
                        'rules': [
                            {'path': 'hardware.detectors', 'status': 'required', 'type': 'list', 'min_items': 1},
                            {'path': 'hardware.detectors[].kind', 'status': 'conditional', 'type': 'string', 'vocab': 'detector_kinds', 'required_if': {'parent_present': 'hardware.detectors[]'}},
                            {
                                'path': 'hardware.detectors[].pixel_pitch_um',
                                'status': 'conditional',
                                'type': 'positive_number',
                                'aliases': ['hardware.detectors[].pixel_size_um'],
                                'required_if': {'item_kind_in': ['scmos']},
                            },
                            {
                                'path': 'hardware.detectors[].pixel_size_um',
                                'status': 'optional',
                                'type': 'positive_number',
                                'superseded_by': 'hardware.detectors[].pixel_pitch_um',
                            },
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/camera-gap.yaml',
            {
                'instrument': {'instrument_id': 'camera-gap'},
                'hardware': {
                    'detectors': [
                        {'kind': 'scmos'},
                    ]
                },
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')
        issue_codes = [issue.code for issue in issues]
        warning_codes = [warning.code for warning in warnings]
        self.assertIn('missing_conditional_field', warning_codes)
        self.assertNotIn('field_superseded', warning_codes)

    def test_evaluate_required_if_supports_item_field_in(self) -> None:
        vocabulary = Vocabulary(vocab_registry={})
        condition = {'item_field_in': {'timing_mode': ['pulsed'], 'role': ['depletion']}}

        self.assertTrue(
            _evaluate_required_if(
                condition,
                payload={},
                item_context={'timing_mode': 'pulsed', 'role': 'depletion'},
                vocabulary=vocabulary,
            )
        )
        self.assertTrue(
            _evaluate_required_if(
                {'item_field_in': {'supports_time_gating': [True]}},
                payload={},
                item_context={'supports_time_gating': True},
                vocabulary=vocabulary,
            )
        )
        self.assertFalse(
            _evaluate_required_if(
                condition,
                payload={},
                item_context={'timing_mode': 'cw', 'role': 'depletion'},
                vocabulary=vocabulary,
            )
        )

    def test_migration_compatibility_object_map_wildcard_item_field_in_reports_missing_bands(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {},
                'sections': [
                    {
                        'id': 'light-path',
                        'title': 'Light Path',
                        'rules': [
                            {'path': 'hardware.light_path.excitation_mechanisms', 'status': 'required', 'type': 'list', 'min_items': 1},
                            {
                                'path': 'hardware.light_path.excitation_mechanisms[].positions{}.bands',
                                'status': 'conditional',
                                'type': 'list',
                                'required_if': {'item_field_in': {'component_type': ['multiband_bandpass']}},
                            },
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/map-missing-bands.yaml',
            {
                'instrument': {'instrument_id': 'map-missing-bands'},
                'hardware': {
                    'light_path': {
                        'excitation_mechanisms': [
                            {
                                'positions': {
                                    'Pos_1': {'component_type': 'multiband_bandpass'},
                                }
                            }
                        ]
                    }
                },
            },
        )

        _, _, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')
        self.assertIn('missing_conditional_field', {warning.code for warning in warnings})
        self.assertTrue(
            any(
                path.endswith('instruments/map-missing-bands.yaml:hardware.light_path.excitation_mechanisms[0].positions.Pos_1.bands')
                for path in {warning.path for warning in warnings}
            )
        )

    def test_migration_compatibility_object_map_wildcard_item_field_in_passes_when_bands_present(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {},
                'sections': [
                    {
                        'id': 'light-path',
                        'title': 'Light Path',
                        'rules': [
                            {'path': 'hardware.light_path.excitation_mechanisms', 'status': 'required', 'type': 'list', 'min_items': 1},
                            {
                                'path': 'hardware.light_path.excitation_mechanisms[].positions{}.bands',
                                'status': 'conditional',
                                'type': 'list',
                                'required_if': {'item_field_in': {'component_type': ['multiband_bandpass']}},
                            },
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/map-bands-present.yaml',
            {
                'instrument': {'instrument_id': 'map-bands-present'},
                'hardware': {
                    'light_path': {
                        'excitation_mechanisms': [
                            {
                                'positions': {
                                    'Pos_1': {
                                        'component_type': 'multiband_bandpass',
                                        'bands': [
                                            {'center_nm': 520, 'width_nm': 35},
                                        ],
                                    },
                                }
                            }
                        ]
                    }
                },
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')
        self.assertEqual(issues, [])
        self.assertNotIn('missing_conditional_field', {w.code for w in warnings})


    def test_migration_compatibility_schema_requires_multiband_bands_for_excitation_and_emission_positions(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {},
                'sections': [
                    {
                        'id': 'light-path',
                        'title': 'Light Path',
                        'rules': [
                            {'path': 'hardware.light_path.excitation_mechanisms', 'status': 'required', 'type': 'list', 'min_items': 1},
                            {'path': 'hardware.light_path.emission_mechanisms', 'status': 'required', 'type': 'list', 'min_items': 1},
                            {
                                'path': 'hardware.light_path.excitation_mechanisms[].positions{}.bands',
                                'status': 'conditional',
                                'type': 'list',
                                'min_items': 1,
                                'required_if': {'item_field_in': {'component_type': ['multiband_bandpass']}},
                            },
                            {
                                'path': 'hardware.light_path.excitation_mechanisms[].positions{}.bands[].center_nm',
                                'status': 'conditional',
                                'type': 'positive_number',
                                'required_if': {'parent_present': 'hardware.light_path.excitation_mechanisms[].positions{}.bands[]'},
                            },
                            {
                                'path': 'hardware.light_path.excitation_mechanisms[].positions{}.bands[].width_nm',
                                'status': 'conditional',
                                'type': 'positive_number',
                                'required_if': {'parent_present': 'hardware.light_path.excitation_mechanisms[].positions{}.bands[]'},
                            },
                            {
                                'path': 'hardware.light_path.emission_mechanisms[].positions{}.bands',
                                'status': 'conditional',
                                'type': 'list',
                                'min_items': 1,
                                'required_if': {'item_field_in': {'component_type': ['multiband_bandpass']}},
                            },
                            {
                                'path': 'hardware.light_path.emission_mechanisms[].positions{}.bands[].center_nm',
                                'status': 'conditional',
                                'type': 'positive_number',
                                'required_if': {'parent_present': 'hardware.light_path.emission_mechanisms[].positions{}.bands[]'},
                            },
                            {
                                'path': 'hardware.light_path.emission_mechanisms[].positions{}.bands[].width_nm',
                                'status': 'conditional',
                                'type': 'positive_number',
                                'required_if': {'parent_present': 'hardware.light_path.emission_mechanisms[].positions{}.bands[]'},
                            },
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/map-missing-multiband-bands.yaml',
            {
                'instrument': {'instrument_id': 'map-missing-multiband-bands'},
                'hardware': {
                    'light_path': {
                        'excitation_mechanisms': [
                            {'positions': {'Pos_1': {'component_type': 'multiband_bandpass', 'bands': [{'center_nm': 488, 'width_nm': 20}]}}}
                        ],
                        'emission_mechanisms': [
                            {'positions': {'Pos_1': {'component_type': 'multiband_bandpass'}}}
                        ],
                    }
                },
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')
        self.assertIn('missing_conditional_field', {warning.code for warning in warnings})
        self.assertTrue(
            any(
                warning.path.endswith(
                    'instruments/map-missing-multiband-bands.yaml:hardware.light_path.emission_mechanisms[0].positions.Pos_1.bands'
                )
                for warning in warnings
            )
        )

    def test_migration_compatibility_schema_accepts_multiband_bands_with_required_fields_for_positions(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {},
                'sections': [
                    {
                        'id': 'light-path',
                        'title': 'Light Path',
                        'rules': [
                            {'path': 'hardware.light_path.excitation_mechanisms', 'status': 'required', 'type': 'list', 'min_items': 1},
                            {'path': 'hardware.light_path.emission_mechanisms', 'status': 'required', 'type': 'list', 'min_items': 1},
                            {
                                'path': 'hardware.light_path.excitation_mechanisms[].positions{}.bands',
                                'status': 'conditional',
                                'type': 'list',
                                'min_items': 1,
                                'required_if': {'item_field_in': {'component_type': ['multiband_bandpass']}},
                            },
                            {
                                'path': 'hardware.light_path.excitation_mechanisms[].positions{}.bands[].center_nm',
                                'status': 'conditional',
                                'type': 'positive_number',
                                'required_if': {'parent_present': 'hardware.light_path.excitation_mechanisms[].positions{}.bands[]'},
                            },
                            {
                                'path': 'hardware.light_path.excitation_mechanisms[].positions{}.bands[].width_nm',
                                'status': 'conditional',
                                'type': 'positive_number',
                                'required_if': {'parent_present': 'hardware.light_path.excitation_mechanisms[].positions{}.bands[]'},
                            },
                            {
                                'path': 'hardware.light_path.emission_mechanisms[].positions{}.bands',
                                'status': 'conditional',
                                'type': 'list',
                                'min_items': 1,
                                'required_if': {'item_field_in': {'component_type': ['multiband_bandpass']}},
                            },
                            {
                                'path': 'hardware.light_path.emission_mechanisms[].positions{}.bands[].center_nm',
                                'status': 'conditional',
                                'type': 'positive_number',
                                'required_if': {'parent_present': 'hardware.light_path.emission_mechanisms[].positions{}.bands[]'},
                            },
                            {
                                'path': 'hardware.light_path.emission_mechanisms[].positions{}.bands[].width_nm',
                                'status': 'conditional',
                                'type': 'positive_number',
                                'required_if': {'parent_present': 'hardware.light_path.emission_mechanisms[].positions{}.bands[]'},
                            },
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/map-valid-multiband-bands.yaml',
            {
                'instrument': {'instrument_id': 'map-valid-multiband-bands'},
                'hardware': {
                    'light_path': {
                        'excitation_mechanisms': [
                            {
                                'positions': {
                                    'Pos_1': {
                                        'component_type': 'multiband_bandpass',
                                        'bands': [{'center_nm': 488, 'width_nm': 20}],
                                    }
                                }
                            }
                        ],
                        'emission_mechanisms': [
                            {
                                'positions': {
                                    'Pos_1': {
                                        'component_type': 'multiband_bandpass',
                                        'bands': [{'center_nm': 525, 'width_nm': 30}],
                                    }
                                }
                            }
                        ],
                    }
                },
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')
        self.assertEqual(issues, [])
        self.assertNotIn('missing_conditional_field', {warning.code for warning in warnings})



    def test_migration_compatibility_required_if_field_equals_any_is_enforced_for_conditional_slots(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {'mechanism_types': {'source': 'inline', 'allowed_values': ['filter_wheel', 'single_slot']}},
                'sections': [
                    {
                        'id': 'lp',
                        'title': 'Light Path',
                        'rules': [
                            {'path': 'hardware.light_path.excitation_mechanisms', 'status': 'required', 'type': 'list', 'min_items': 1},
                            {'path': 'hardware.light_path.excitation_mechanisms[].type', 'status': 'conditional', 'type': 'string', 'vocab': 'mechanism_types', 'required_if': {'parent_present': 'hardware.light_path.excitation_mechanisms[]'}},
                            {
                                'path': 'hardware.light_path.excitation_mechanisms[].slots',
                                'status': 'conditional',
                                'type': 'positive_number',
                                'required_if': {
                                    'all_of': [
                                        {'parent_present': 'hardware.light_path.excitation_mechanisms[]'},
                                        {'field_equals_any': {'field': 'hardware.light_path.excitation_mechanisms[].type', 'values': ['filter_wheel']}},
                                    ]
                                },
                            },
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/field-equals-any-missing.yaml',
            {
                'instrument': {'instrument_id': 'field-equals-any-missing'},
                'hardware': {
                    'light_path': {
                        'excitation_mechanisms': [
                            {'type': 'filter_wheel'},
                        ]
                    }
                },
            },
        )

        _, _, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertIn('missing_required_field', {warning.code for warning in warnings})
        self.assertTrue(any('excitation_mechanisms[].slots' in warning.message for warning in warnings if warning.code == 'missing_required_field'))

    def test_migration_compatibility_required_if_field_equals_any_not_triggered_when_values_do_not_match(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {'mechanism_types': {'source': 'inline', 'allowed_values': ['filter_wheel', 'single_slot']}},
                'sections': [
                    {
                        'id': 'lp',
                        'title': 'Light Path',
                        'rules': [
                            {'path': 'hardware.light_path.excitation_mechanisms', 'status': 'required', 'type': 'list', 'min_items': 1},
                            {'path': 'hardware.light_path.excitation_mechanisms[].type', 'status': 'conditional', 'type': 'string', 'vocab': 'mechanism_types', 'required_if': {'parent_present': 'hardware.light_path.excitation_mechanisms[]'}},
                            {
                                'path': 'hardware.light_path.excitation_mechanisms[].slots',
                                'status': 'conditional',
                                'type': 'positive_number',
                                'required_if': {
                                    'all_of': [
                                        {'parent_present': 'hardware.light_path.excitation_mechanisms[]'},
                                        {'field_equals_any': {'field': 'hardware.light_path.excitation_mechanisms[].type', 'values': ['filter_wheel']}},
                                    ]
                                },
                            },
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/field-equals-any-not-triggered.yaml',
            {
                'instrument': {'instrument_id': 'field-equals-any-not-triggered'},
                'hardware': {
                    'light_path': {
                        'excitation_mechanisms': [
                            {'type': 'single_slot'},
                        ]
                    }
                },
            },
        )

        _, _, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertNotIn('missing_conditional_field', {warning.code for warning in warnings})

    def test_validator_v2_sources_do_not_infer_tunable_requirements_from_notes(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {},
                'sections': [
                    {
                        'id': 'ls',
                        'title': 'Light Sources',
                        'rules': [
                            {'path': 'hardware.sources', 'status': 'required', 'type': 'list', 'min_items': 1},
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/tunable-notes-only.yaml',
            {
                'instrument': {'instrument_id': 'tunable-notes-only'},
                'hardware': {
                    'sources': [
                        {'id': 'src_tunable', 'kind': 'laser', 'notes': 'Tunable range 440-790 nm'},
                    ],
                    'endpoints': [{'id': 'cam_main', 'endpoint_type': 'camera'}],
                },
                'light_paths': [{'id': 'epi', 'illumination_sequence': [{'source_id': 'src_tunable'}], 'detection_sequence': [{'endpoint_id': 'cam_main'}]}],
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertEqual(issues, [])
        self.assertNotIn('cross_field_rule_warning', {warning.code for warning in warnings})

    def test_evaluate_required_if_item_field_in_resolves_vocab_synonyms(self) -> None:
        self._write_json_yaml(
            'vocab/light_source_timing_modes.yaml',
            {
                'terms': [
                    {'id': 'cw', 'label': 'CW', 'description': '', 'synonyms': []},
                    {'id': 'pulsed', 'label': 'Pulsed', 'description': '', 'synonyms': ['pulse']},
                ]
            },
        )
        vocabulary = Vocabulary(
            vocab_registry={
                'light_source_timing_modes': {'source': 'file', 'path': 'vocab/light_source_timing_modes.yaml'}
            }
        )

        self.assertTrue(
            _evaluate_required_if(
                {'item_field_in': {'timing_mode': ['pulsed']}},
                payload={},
                item_context={'timing_mode': 'pulse'},
                vocabulary=vocabulary,
                item_field_vocabs={'timing_mode': 'light_source_timing_modes'},
            )
        )

    def test_evaluate_required_if_supports_any_item_conditions(self) -> None:
        vocabulary = Vocabulary(vocab_registry={})
        payload = {
            'hardware': {
                'sources': [
                    {'role': 'excitation', 'timing_mode': 'pulsed'},
                    {'role': 'depletion', 'timing_mode': 'continuous'},
                ]
            }
        }

        self.assertTrue(
            _evaluate_required_if(
                {'any_item_field_in': {'path': 'hardware.sources[]', 'field': 'role', 'values': ['depletion']}},
                payload=payload,
                item_context=None,
                vocabulary=vocabulary,
            )
        )
        self.assertTrue(
            _evaluate_required_if(
                {'any_item_matches': {'path': 'hardware.sources[]', 'field_in': {'role': ['depletion'], 'timing_mode': ['continuous']}}},
                payload=payload,
                item_context=None,
                vocabulary=vocabulary,
            )
        )
        self.assertFalse(
            _evaluate_required_if(
                {'any_item_matches': {'path': 'hardware.sources[]', 'field_in': {'role': ['depletion'], 'timing_mode': ['pulsed']}}},
                payload=payload,
                item_context=None,
                vocabulary=vocabulary,
            )
        )

    def test_valid_sted_instrument_example_uses_v2_sources(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {
                    'modalities': {'source': 'inline', 'allowed_values': ['sted']},
                    'light_source_roles': {'source': 'inline', 'allowed_values': ['excitation', 'depletion']},
                    'light_source_timing_modes': {'source': 'inline', 'allowed_values': ['cw', 'pulsed']},
                    'detector_kinds': {'source': 'inline', 'allowed_values': ['pmt']},
                    'optical_modulator_types': {'source': 'inline', 'allowed_values': ['slm']},
                    'phase_mask_types': {'source': 'inline', 'allowed_values': ['vortex']},
                    'adaptive_illumination_methods': {'source': 'inline', 'allowed_values': ['rescue_sted']},
                },
                'sections': [
                    {'id': 'm', 'title': 'M', 'rules': [{'path': 'modalities', 'status': 'required', 'type': 'list', 'vocab': 'modalities'}]},
                    {'id': 'ls', 'title': 'LS', 'rules': [
                        {'path': 'hardware.sources', 'status': 'required', 'type': 'list', 'min_items': 1},
                        {'path': 'hardware.sources[].role', 'status': 'optional', 'type': 'string', 'vocab': 'light_source_roles'},
                        {'path': 'hardware.sources[].timing_mode', 'status': 'optional', 'type': 'string', 'vocab': 'light_source_timing_modes'},
                        {'path': 'hardware.sources[].pulse_width_ps', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'item_field_in': {'timing_mode': ['pulsed']}}},
                        {'path': 'hardware.sources[].repetition_rate_mhz', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'item_field_in': {'timing_mode': ['pulsed']}}},
                        {'path': 'hardware.sources[].depletion_targets_nm', 'status': 'conditional', 'type': 'list', 'required_if': {'item_field_in': {'role': ['depletion']}}},
                    ]},
                    {'id': 'd', 'title': 'D', 'rules': [
                        {'path': 'hardware.detectors', 'status': 'optional', 'type': 'list'},
                        {'path': 'hardware.detectors[].kind', 'status': 'conditional', 'type': 'string', 'vocab': 'detector_kinds', 'required_if': {'parent_present': 'hardware.detectors[]'}},
                        {'path': 'hardware.detectors[].supports_time_gating', 'status': 'optional', 'type': 'boolean'},
                        {'path': 'hardware.detectors[].default_gating_delay_ns', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'item_field_in': {'supports_time_gating': [True]}}},
                        {'path': 'hardware.detectors[].default_gate_width_ns', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'item_field_in': {'supports_time_gating': [True]}}},
                    ]},
                    {'id': 'om', 'title': 'OM', 'rules': [
                        {'path': 'hardware.optical_modulators', 'status': 'optional', 'type': 'list', 'min_items': 1},
                        {'path': 'hardware.optical_modulators[].type', 'status': 'conditional', 'type': 'string', 'vocab': 'optical_modulator_types', 'required_if': {'parent_present': 'hardware.optical_modulators[]'}},
                        {'path': 'hardware.optical_modulators[].supported_phase_masks', 'status': 'optional', 'type': 'list', 'vocab': 'phase_mask_types'},
                    ]},
                    {'id': 'il', 'title': 'IL', 'rules': [
                        {'path': 'hardware.illumination_logic', 'status': 'optional', 'type': 'list', 'min_items': 1},
                        {'path': 'hardware.illumination_logic[].method', 'status': 'conditional', 'type': 'string', 'vocab': 'adaptive_illumination_methods', 'required_if': {'parent_present': 'hardware.illumination_logic[]'}},
                        {'path': 'hardware.illumination_logic[].default_enabled', 'status': 'conditional', 'type': 'boolean', 'required_if': {'parent_present': 'hardware.illumination_logic[]'}},
                    ]},
                ],
            },
        )
        self._write_json_yaml(
            'instruments/sted-valid.yaml',
            {
                'instrument': {'instrument_id': 'sted-test'},
                'modalities': ['sted'],
                'software': [{'role': 'acquisition', 'name': 'Control SW'}],
                'hardware': {
                    'sources': [
                        {'id': 'src_exc', 'role': 'excitation', 'timing_mode': 'cw'},
                        {'id': 'src_dep', 'role': 'depletion', 'timing_mode': 'pulsed', 'pulse_width_ps': 600, 'repetition_rate_mhz': 80, 'depletion_targets_nm': [775]},
                    ],
                    'detectors': [{'kind': 'pmt', 'supports_time_gating': True, 'default_gating_delay_ns': 0.2, 'default_gate_width_ns': 5.0}],
                    'endpoints': [{'id': 'hyd_ep', 'endpoint_type': 'detector'}],
                    'optical_modulators': [{'type': 'slm', 'supported_phase_masks': ['vortex']}],
                    'illumination_logic': [{'method': 'rescue_sted', 'default_enabled': True}],
                },
                'light_paths': [{'id': 'sted', 'illumination_sequence': [{'source_id': 'src_exc'}, {'source_id': 'src_dep'}], 'detection_sequence': [{'endpoint_id': 'hyd_ep'}]}],
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')
        self.assertEqual(issues, [])
        self.assertEqual(warnings, [])

    def test_invalid_sted_instrument_example_uses_v2_sources(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {
                    'modalities': {'source': 'inline', 'allowed_values': ['sted']},
                    'light_source_roles': {'source': 'inline', 'allowed_values': ['excitation', 'depletion']},
                    'light_source_timing_modes': {'source': 'inline', 'allowed_values': ['cw', 'pulsed']},
                },
                'sections': [
                    {'id': 'm', 'title': 'M', 'rules': [{'path': 'modalities', 'status': 'required', 'type': 'list', 'vocab': 'modalities'}]},
                    {'id': 'ls', 'title': 'LS', 'rules': [
                        {'path': 'hardware.sources', 'status': 'required', 'type': 'list', 'min_items': 1},
                        {'path': 'hardware.sources[].role', 'status': 'optional', 'type': 'string', 'vocab': 'light_source_roles'},
                        {'path': 'hardware.sources[].timing_mode', 'status': 'optional', 'type': 'string', 'vocab': 'light_source_timing_modes'},
                        {'path': 'hardware.sources[].pulse_width_ps', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'item_field_in': {'timing_mode': ['pulsed']}}},
                        {'path': 'hardware.sources[].depletion_targets_nm', 'status': 'conditional', 'type': 'list', 'required_if': {'item_field_in': {'role': ['depletion']}}},
                    ]},
                ],
            },
        )
        self._write_json_yaml(
            'instruments/sted-invalid.yaml',
            {
                'instrument': {'instrument_id': 'sted-test-invalid'},
                'modalities': ['sted'],
                'hardware': {'sources': [{'role': 'depletion', 'timing_mode': 'pulsed'}]},
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')
        warning_codes = {warning.code for warning in warnings}
        self.assertIn('missing_conditional_field', warning_codes)


    def test_list_item_type_validation_for_depletion_targets_on_v2_sources(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {'modalities': {'source': 'inline', 'allowed_values': ['sted']}},
                'sections': [
                    {
                        'id': 'ls',
                        'title': 'LS',
                        'rules': [
                            {'path': 'modalities', 'status': 'required', 'type': 'list', 'vocab': 'modalities'},
                            {'path': 'hardware.sources', 'status': 'required', 'type': 'list', 'min_items': 1},
                            {
                                'path': 'hardware.sources[].depletion_targets_nm',
                                'status': 'optional',
                                'type': 'list',
                                'item_type': 'positive_number',
                            },
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/sted-list-items.yaml',
            {
                'instrument': {'instrument_id': 'sted-list-items'},
                'modalities': ['sted'],
                'hardware': {
                    'sources': [
                        {'depletion_targets_nm': [561, 'foo']},
                    ]
                },
            },
        )

        _, issues, _ = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')
        self.assertIn('invalid_list_item_type', {issue.code for issue in issues})

    def test_conditional_depletion_targets_enforce_numeric_item_type_on_v2_sources(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {
                    'light_source_roles': {'source': 'file', 'path': 'vocab/light_source_roles.yaml'},
                },
                'sections': [
                    {
                        'id': 'ls',
                        'title': 'LS',
                        'rules': [
                            {'path': 'hardware.sources', 'status': 'required', 'type': 'list', 'min_items': 1},
                            {
                                'path': 'hardware.sources[].role',
                                'status': 'optional',
                                'type': 'string',
                                'vocab': 'light_source_roles',
                            },
                            {
                                'path': 'hardware.sources[].depletion_targets_nm',
                                'status': 'conditional',
                                'type': 'list',
                                'item_type': 'positive_number',
                                'required_if': {'item_field_in': {'role': ['depletion']}},
                            },
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'vocab/light_source_roles.yaml',
            {
                'terms': [
                    {'id': 'depletion', 'label': 'Depletion', 'description': '', 'synonyms': ['sted_depletion']},
                ]
            },
        )
        self._write_json_yaml(
            'instruments/sted-conditional-list-items.yaml',
            {
                'instrument': {'instrument_id': 'sted-conditional-list-items'},
                'hardware': {
                    'sources': [
                        {'role': 'depletion', 'depletion_targets_nm': [775, 'foo']},
                    ]
                },
            },
        )

        _, issues, _ = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')
        self.assertIn('invalid_list_item_type', {issue.code for issue in issues})

    def test_item_field_in_conditions_apply_for_vocab_synonyms_in_validator_on_v2_sources(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {
                    'light_source_roles': {'source': 'file', 'path': 'vocab/light_source_roles.yaml'},
                    'light_source_timing_modes': {'source': 'file', 'path': 'vocab/light_source_timing_modes.yaml'},
                },
                'sections': [
                    {
                        'id': 'ls',
                        'title': 'LS',
                        'rules': [
                            {'path': 'hardware.sources', 'status': 'required', 'type': 'list', 'min_items': 1},
                            {'path': 'hardware.sources[].role', 'status': 'optional', 'type': 'string', 'vocab': 'light_source_roles'},
                            {'path': 'hardware.sources[].timing_mode', 'status': 'optional', 'type': 'string', 'vocab': 'light_source_timing_modes'},
                            {
                                'path': 'hardware.sources[].pulse_width_ps',
                                'status': 'conditional',
                                'type': 'positive_number',
                                'required_if': {'item_field_in': {'timing_mode': ['pulsed']}},
                            },
                            {
                                'path': 'hardware.sources[].depletion_targets_nm',
                                'status': 'conditional',
                                'type': 'list',
                                'item_type': 'positive_number',
                                'required_if': {'item_field_in': {'role': ['depletion']}},
                            },
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'vocab/light_source_roles.yaml',
            {
                'terms': [
                    {'id': 'depletion', 'label': 'Depletion', 'description': '', 'synonyms': ['sted_depletion']},
                ]
            },
        )
        self._write_json_yaml(
            'vocab/light_source_timing_modes.yaml',
            {
                'terms': [
                    {'id': 'pulsed', 'label': 'Pulsed', 'description': '', 'synonyms': ['pulse']},
                ]
            },
        )
        self._write_json_yaml(
            'instruments/sted-synonym-conditions.yaml',
            {
                'instrument': {'instrument_id': 'sted-synonym-conditions'},
                'hardware': {
                    'sources': [
                        {'role': 'sted_depletion', 'timing_mode': 'pulse'},
                    ]
                },
            },
        )

        _, _, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')
        missing_conditional_messages = [w.message for w in warnings if w.code == 'missing_conditional_field']
        self.assertTrue(any('hardware.sources[].pulse_width_ps' in msg for msg in missing_conditional_messages))
        self.assertTrue(any('hardware.sources[].depletion_targets_nm' in msg for msg in missing_conditional_messages))

    def test_sted_completeness_audit_warns_for_missing_depletion_and_time_gating_on_v2_sources(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {
                    'modalities': {'source': 'inline', 'allowed_values': ['sted']},
                    'detector_kinds': {'source': 'inline', 'allowed_values': ['pmt']},
                },
                'sections': [
                    {'id': 'm', 'title': 'M', 'rules': [{'path': 'modalities', 'status': 'required', 'type': 'list', 'vocab': 'modalities'}]},
                    {'id': 'ls', 'title': 'LS', 'rules': [{'path': 'hardware.sources', 'status': 'required', 'type': 'list', 'min_items': 1}]},
                    {'id': 'd', 'title': 'D', 'rules': [{'path': 'hardware.detectors', 'status': 'optional', 'type': 'list'}, {'path': 'hardware.detectors[].kind', 'status': 'optional', 'type': 'string', 'vocab': 'detector_kinds'}]},
                ],
            },
        )
        self._write_json_yaml(
            'instruments/sted-gap.yaml',
            {
                'instrument': {'instrument_id': 'sted-gap'},
                'modalities': ['sted'],
                'software': [{'role': 'acquisition', 'name': 'Control SW'}],
                'hardware': {
                    'sources': [{'kind': 'laser', 'role': 'excitation'}],
                    'detectors': [{'kind': 'pmt'}],
                },
            },
        )

        _, _, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')
        gap_messages = [w.message for w in warnings if w.code == 'sted_completeness_gap']
        self.assertTrue(any("canonical source" in msg for msg in gap_messages))
        self.assertTrue(any('supports_time_gating=true' in msg for msg in gap_messages))


    def test_migration_compatibility_optical_component_discriminator_rules_fail_when_required_shape_fields_missing(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {},
                'sections': [
                    {
                        'id': 'light-path',
                        'title': 'Light Path',
                        'rules': [
                            {'path': 'hardware.light_path.excitation_mechanisms[].positions{}.component_type', 'status': 'conditional', 'type': 'string', 'required_if': {'parent_present': 'hardware.light_path.excitation_mechanisms[].positions{}'}},
                            {'path': 'hardware.light_path.excitation_mechanisms[].positions{}.center_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'item_field_in': {'component_type': ['bandpass', 'notch']}}},
                            {'path': 'hardware.light_path.excitation_mechanisms[].positions{}.width_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'item_field_in': {'component_type': ['bandpass', 'notch']}}},
                            {'path': 'hardware.light_path.emission_mechanisms[].positions{}.bands', 'status': 'conditional', 'type': 'list', 'required_if': {'item_field_in': {'component_type': ['multiband_bandpass']}}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.cut_on_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'item_field_in': {'component_type': ['longpass']}}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.cutoffs_nm', 'status': 'conditional', 'type': 'list', 'required_if': {'item_field_in': {'component_type': ['dichroic']}}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands', 'status': 'optional', 'type': 'list'},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands[].center_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'parent_present': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands[]'}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands[].width_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'parent_present': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands[]'}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands', 'status': 'optional', 'type': 'list'},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands[].center_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'parent_present': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands[]'}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands[].width_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'parent_present': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands[]'}},
                            {'path': 'hardware.light_path.emission_mechanisms[].positions{}.cut_off_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'item_field_in': {'component_type': ['shortpass']}}},
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/missing-optical-shape-fields.yaml',
            {
                'instrument': {'instrument_id': 'missing-optical-shape-fields'},
                'hardware': {
                    'light_path': {
                        'excitation_mechanisms': [{'positions': {'Pos_1': {'component_type': 'bandpass', 'width_nm': 20}}}],
                        'emission_mechanisms': [{'positions': {'Pos_1': {'component_type': 'multiband_bandpass'}, 'Pos_2': {'component_type': 'shortpass'}}}],
                        'dichroic_mechanisms': [{'positions': {'Pos_1': {'component_type': 'longpass'}, 'Pos_2': {'component_type': 'multiband_dichroic'}}}],
                        'cube_mechanisms': [
                            {'positions': {'Pos_1': {
                                'excitation_filter': {'component_type': 'shortpass'},
                                'dichroic': {'component_type': 'multiband_dichroic'},
                                'emission_filter': {'component_type': 'bandpass', 'center_nm': 525, 'width_nm': 30},
                            }}}
                        ],
                    }
                },
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')
        missing_messages = [w.message for w in warnings if w.code == 'missing_conditional_field']
        self.assertFalse(any(w.code == 'invalid_light_path' for w in warnings))
        self.assertTrue(any('hardware.light_path.excitation_mechanisms[].positions{}.center_nm' in message for message in missing_messages))
        self.assertTrue(any('hardware.light_path.emission_mechanisms[].positions{}.bands' in message for message in missing_messages))
        self.assertTrue(any('hardware.light_path.dichroic_mechanisms[].positions{}.cut_on_nm' in message for message in missing_messages))
        self.assertFalse(any('hardware.light_path.dichroic_mechanisms[].positions{}.cutoffs_nm' in message for message in missing_messages))
        self.assertTrue(any('hardware.light_path.emission_mechanisms[].positions{}.cut_off_nm' in message for message in missing_messages))

    def test_migration_compatibility_optical_component_discriminator_rules_accept_valid_shape_fields(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {},
                'sections': [
                    {
                        'id': 'light-path',
                        'title': 'Light Path',
                        'rules': [
                            {'path': 'hardware.light_path.excitation_mechanisms[].positions{}.center_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'item_field_in': {'component_type': ['bandpass', 'notch']}}},
                            {'path': 'hardware.light_path.excitation_mechanisms[].positions{}.width_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'item_field_in': {'component_type': ['bandpass', 'notch']}}},
                            {'path': 'hardware.light_path.emission_mechanisms[].positions{}.bands', 'status': 'conditional', 'type': 'list', 'required_if': {'item_field_in': {'component_type': ['multiband_bandpass']}}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.cut_on_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'item_field_in': {'component_type': ['longpass']}}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.cutoffs_nm', 'status': 'conditional', 'type': 'list', 'required_if': {'item_field_in': {'component_type': ['dichroic']}}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands', 'status': 'optional', 'type': 'list'},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands[].center_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'parent_present': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands[]'}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands[].width_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'parent_present': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands[]'}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands', 'status': 'optional', 'type': 'list'},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands[].center_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'parent_present': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands[]'}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands[].width_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'parent_present': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands[]'}},
                            {'path': 'hardware.light_path.emission_mechanisms[].positions{}.cut_off_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'item_field_in': {'component_type': ['shortpass']}}},
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/valid-optical-shape-fields.yaml',
            {
                'instrument': {'instrument_id': 'valid-optical-shape-fields'},
                'hardware': {
                    'light_path': {
                        'excitation_mechanisms': [{'positions': {'Pos_1': {'component_type': 'bandpass', 'center_nm': 488, 'width_nm': 20}}}],
                        'emission_mechanisms': [{'positions': {'Pos_1': {'component_type': 'multiband_bandpass', 'bands': [{'center_nm': 525, 'width_nm': 30}]}, 'Pos_2': {'component_type': 'shortpass', 'cut_off_nm': 700}}}],
                        'dichroic_mechanisms': [{'positions': {'Pos_1': {'component_type': 'longpass', 'cut_on_nm': 560}, 'Pos_2': {'component_type': 'multiband_dichroic', 'transmission_bands': [{'center_nm': 520, 'width_nm': 30}], 'reflection_bands': [{'center_nm': 450, 'width_nm': 40}]}}}],
                        'cube_mechanisms': [
                            {'positions': {'Pos_1': {
                                'excitation_filter': {'component_type': 'shortpass', 'cut_off_nm': 700},
                                'dichroic': {'component_type': 'multiband_dichroic', 'transmission_bands': [{'center_nm': 520, 'width_nm': 30}], 'reflection_bands': [{'center_nm': 450, 'width_nm': 40}]},
                                'emission_filter': {'component_type': 'bandpass', 'center_nm': 525, 'width_nm': 30},
                            }}}
                        ],
                    }
                },
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')
        self.assertEqual(issues, [])
        self.assertNotIn('missing_conditional_field', {warning.code for warning in warnings})


    def test_migration_compatibility_dichroic_schema_accepts_explicit_bands_and_legacy_single_cutoff(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {},
                'sections': [
                    {
                        'id': 'light-path',
                        'title': 'Light Path',
                        'rules': [
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.component_type', 'status': 'conditional', 'type': 'string', 'required_if': {'parent_present': 'hardware.light_path.dichroic_mechanisms[].positions{}'}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.cutoffs_nm', 'status': 'conditional', 'type': 'list', 'required_if': {'item_field_in': {'component_type': ['dichroic']}}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands', 'status': 'optional', 'type': 'list'},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands[].center_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'parent_present': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands[]'}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands[].width_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'parent_present': 'hardware.light_path.dichroic_mechanisms[].positions{}.transmission_bands[]'}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands', 'status': 'optional', 'type': 'list'},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands[].center_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'parent_present': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands[]'}},
                            {'path': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands[].width_nm', 'status': 'conditional', 'type': 'positive_number', 'required_if': {'parent_present': 'hardware.light_path.dichroic_mechanisms[].positions{}.reflection_bands[]'}},
                        ],
                    }
                ],
            },
        )
        self._write_json_yaml(
            'instruments/valid-dichroics.yaml',
            {
                'instrument': {'instrument_id': 'valid-dichroics'},
                'hardware': {
                    'light_path': {
                        'dichroic_mechanisms': [{
                            'positions': {
                                'Pos_1': {
                                    'component_type': 'multiband_dichroic',
                                    'transmission_bands': [{'center_nm': 521, 'width_nm': 25}],
                                },
                                'Pos_2': {
                                    'component_type': 'multiband_dichroic',
                                    'reflection_bands': [{'center_nm': 488, 'width_nm': 20}],
                                },
                                'Pos_3': {
                                    'component_type': 'dichroic',
                                    'cutoffs_nm': [560],
                                },
                            }
                        }]
                    }
                },
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')
        self.assertEqual(issues, [])
        self.assertFalse(any(w.code == 'missing_conditional_field' for w in warnings))

    def test_light_path_validator_warns_when_detection_route_lacks_explicit_endpoint(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {'vocab_registry': {}, 'sections': []},
        )
        self._write_json_yaml(
            'instruments/missing-route-endpoint.yaml',
            {
                'instrument': {'instrument_id': 'missing-route-endpoint'},
                'hardware': {
                    'optical_path_elements': [
                        {'id': 'emission_filter', 'stage_role': 'emission', 'element_type': 'filter_wheel'}
                    ]
                },
                'light_paths': [
                    {
                        'id': 'epi',
                        'illumination_sequence': [],
                        'detection_sequence': [{'optical_path_element_id': 'emission_filter'}],
                    }
                ],
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertEqual(issues, [])
        self.assertTrue(any(w.code == 'light_path_endpoint_warning' for w in warnings))
        self.assertTrue(any('route does not terminate in a clear explicit endpoint_id' in w.message for w in warnings))

    def test_schema_allows_optical_path_elements_without_stage_role(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {
                'vocab_registry': {
                    'optical_path_stage_roles': {
                        'source': 'inline',
                        'allowed_values': ['excitation', 'dichroic', 'emission', 'cube', 'splitter'],
                    },
                    'optical_path_element_types': {
                        'source': 'inline',
                        'allowed_values': ['filter_wheel', 'splitter'],
                    },
                },
                'sections': [
                    {
                        'path': 'hardware.optical_path_elements[].stage_role',
                        'title': 'Optical path element stage role',
                        'status': 'optional',
                        'type': 'string',
                        'vocab': 'optical_path_stage_roles',
                    },
                    {
                        'path': 'hardware.optical_path_elements[].element_type',
                        'title': 'Optical path element type',
                        'status': 'required',
                        'type': 'string',
                        'vocab': 'optical_path_element_types',
                    },
                ],
            },
        )
        self._write_json_yaml(
            'instruments/stage-role-optional.yaml',
            {
                'instrument': {'instrument_id': 'stage-role-optional'},
                'hardware': {
                    'endpoints': [{'id': 'camera_port_1', 'endpoint_type': 'camera_port'}],
                    'optical_path_elements': [
                        {'id': 'generic_filter', 'element_type': 'filter_wheel'}
                    ],
                },
                'light_paths': [
                    {
                        'id': 'epi',
                        'illumination_sequence': [],
                        'detection_sequence': [
                            {'optical_path_element_id': 'generic_filter'},
                            {'endpoint_id': 'camera_port_1'},
                        ],
                    }
                ],
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertEqual(issues, [])
        self.assertEqual(warnings, [])

    def test_light_path_validator_warns_when_branch_lacks_explicit_endpoint(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {'vocab_registry': {}, 'sections': []},
        )
        self._write_json_yaml(
            'instruments/missing-branch-endpoint.yaml',
            {
                'instrument': {'instrument_id': 'missing-branch-endpoint'},
                'hardware': {
                    'optical_path_elements': [
                        {'id': 'splitter_1', 'stage_role': 'splitter', 'element_type': 'splitter'},
                        {'id': 'green_filter', 'stage_role': 'emission', 'element_type': 'filter_wheel'},
                    ],
                    'detectors': [{'id': 'detector_1', 'kind': 'camera'}],
                },
                'light_paths': [
                    {
                        'id': 'epi',
                        'illumination_sequence': [],
                        'detection_sequence': [
                            {'optical_path_element_id': 'splitter_1'},
                            {
                                'branches': {
                                    'selection_mode': 'exclusive',
                                    'items': [
                                        {'branch_id': 'good', 'sequence': [{'endpoint_id': 'detector_1'}]},
                                        {'branch_id': 'bad', 'sequence': [{'optical_path_element_id': 'green_filter'}]},
                                    ],
                                }
                            },
                        ],
                    }
                ],
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertEqual(issues, [])
        self.assertTrue(any(w.code == 'light_path_endpoint_warning' for w in warnings))
        self.assertTrue(any('.branches.items[1].sequence: branch does not terminate' in w.message for w in warnings))

    def test_light_path_validator_accepts_endpoint_ids_normalized_from_detector_inventory(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {'vocab_registry': {}, 'sections': []},
        )
        self._write_json_yaml(
            'instruments/normalized-detector-endpoint.yaml',
            {
                'instrument': {'instrument_id': 'normalized-detector-endpoint'},
                'hardware': {
                    'detectors': [{'id': 'detector_1', 'kind': 'camera'}],
                },
                'light_paths': [
                    {
                        'id': 'epi',
                        'illumination_sequence': [],
                        'detection_sequence': [{'endpoint_id': 'detector_1'}],
                    }
                ],
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertEqual(issues, [])
        self.assertEqual(warnings, [])

    def test_light_path_validator_errors_on_duplicate_endpoint_ids_across_endpoint_capable_sections(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {'vocab_registry': {}, 'sections': []},
        )
        self._write_json_yaml(
            'instruments/duplicate-endpoint-id.yaml',
            {
                'instrument': {'instrument_id': 'duplicate-endpoint-id'},
                'hardware': {
                    'detectors': [{'id': 'shared_endpoint', 'kind': 'camera'}],
                    'eyepieces': [{'id': 'shared_endpoint'}],
                },
                'light_paths': [
                    {
                        'id': 'epi',
                        'illumination_sequence': [],
                        'detection_sequence': [{'endpoint_id': 'shared_endpoint'}],
                    }
                ],
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertFalse(warnings)
        self.assertTrue(any(issue.code == 'invalid_light_path' for issue in issues))
        self.assertTrue(any('normalized endpoint id `shared_endpoint`' in issue.message for issue in issues))

    def test_light_path_validator_rejects_mixed_topology_keys_in_sequence_items(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {'vocab_registry': {}, 'sections': []},
        )
        self._write_json_yaml(
            'instruments/mixed-sequence-item.yaml',
            {
                'instrument': {'instrument_id': 'mixed-sequence-item'},
                'hardware': {
                    'sources': [{'id': 'src_488', 'kind': 'laser'}],
                    'optical_path_elements': [{'id': 'exc_filter', 'stage_role': 'excitation', 'element_type': 'filter_wheel'}],
                    'detectors': [{'id': 'detector_1', 'kind': 'camera'}],
                },
                'light_paths': [
                    {
                        'id': 'epi',
                        'illumination_sequence': [{'source_id': 'src_488', 'optical_path_element_id': 'exc_filter'}],
                        'detection_sequence': [{'endpoint_id': 'detector_1'}],
                    }
                ],
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertFalse(warnings)
        self.assertTrue(any(issue.code == 'invalid_light_path' for issue in issues))
        self.assertTrue(any('illumination sequence item must declare exactly one of source_id, or optical_path_element_id.' in issue.message for issue in issues))

    def test_light_path_validator_rejects_illumination_branch_blocks_in_v1(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {'vocab_registry': {}, 'sections': []},
        )
        self._write_json_yaml(
            'instruments/illumination-branch-block.yaml',
            {
                'instrument': {'instrument_id': 'illumination-branch-block'},
                'hardware': {
                    'sources': [{'id': 'src_488', 'kind': 'laser'}],
                    'optical_path_elements': [{'id': 'exc_filter', 'element_type': 'filter_wheel'}],
                    'detectors': [{'id': 'detector_1', 'kind': 'camera'}],
                },
                'light_paths': [
                    {
                        'id': 'epi',
                        'illumination_sequence': [
                            {'source_id': 'src_488'},
                            {'branches': {'selection_mode': 'exclusive', 'items': [{'branch_id': 'alt', 'sequence': [{'optical_path_element_id': 'exc_filter'}]}]}},
                        ],
                        'detection_sequence': [{'endpoint_id': 'detector_1'}],
                    }
                ],
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertFalse(warnings)
        self.assertTrue(any(issue.code == 'invalid_light_path' for issue in issues))
        self.assertTrue(any('illumination sequence item must declare exactly one of source_id, or optical_path_element_id.' in issue.message for issue in issues))

    def test_light_path_validator_rejects_branch_blocks_missing_required_fields(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {'vocab_registry': {}, 'sections': []},
        )
        self._write_json_yaml(
            'instruments/missing-branch-fields.yaml',
            {
                'instrument': {'instrument_id': 'missing-branch-fields'},
                'hardware': {
                    'optical_path_elements': [{'id': 'det_splitter', 'stage_role': 'splitter', 'element_type': 'splitter'}],
                    'detectors': [{'id': 'detector_1', 'kind': 'camera'}],
                },
                'light_paths': [
                    {
                        'id': 'epi',
                        'illumination_sequence': [],
                        'detection_sequence': [
                            {'optical_path_element_id': 'det_splitter'},
                            {'branches': {'items': [{'sequence': [{'endpoint_id': 'detector_1'}]}]}},
                        ],
                    }
                ],
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertFalse(warnings)
        self.assertTrue(any(issue.code == 'invalid_light_path' for issue in issues))
        self.assertTrue(any('branches.selection_mode: must be one of fixed, exclusive, multiple.' in issue.message for issue in issues))
        self.assertTrue(any('.branch_id: is required.' in issue.message for issue in issues))

    def test_light_path_validator_rejects_deprecated_hardware_owned_branch_routing(self) -> None:
        self._write_json_yaml(
            'schema/instrument_policy.yaml',
            {'vocab_registry': {}, 'sections': []},
        )
        self._write_json_yaml(
            'instruments/deprecated-hardware-branch-routing.yaml',
            {
                'instrument': {'instrument_id': 'deprecated-hardware-branch-routing'},
                'hardware': {
                    'optical_path_elements': [
                        {
                            'id': 'legacy_splitter',
                            'stage_role': 'splitter',
                            'element_type': 'splitter',
                            'branches': [{'id': 'path_a', 'target_ids': ['detector_1']}],
                        }
                    ],
                    'detectors': [{'id': 'detector_1', 'kind': 'camera'}],
                },
                'light_paths': [
                    {
                        'id': 'epi',
                        'illumination_sequence': [],
                        'detection_sequence': [{'optical_path_element_id': 'legacy_splitter'}, {'endpoint_id': 'detector_1'}],
                    }
                ],
            },
        )

        _, issues, warnings = validate_instrument_ledgers(instruments_dir=self.repo / 'instruments')

        self.assertFalse(warnings)
        self.assertTrue(any(issue.code == 'invalid_light_path' for issue in issues))
        self.assertTrue(any('deprecated hardware-owned routing metadata is not allowed in canonical topology' in issue.message for issue in issues))

if __name__ == '__main__':
    unittest.main()
