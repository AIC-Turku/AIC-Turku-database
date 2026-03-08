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
    _resolve_rule_nodes,
    Vocabulary,
    build_instrument_completeness_report,
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

    def test_evaluate_required_if_supports_compound_all_of_any_of(self) -> None:
        vocabulary = Vocabulary(vocab_registry={'modalities': {'source': 'inline', 'allowed_values': ['flim', 'sim']}})
        payload = {
            'software': {'analysis': {'version': '1.0'}},
            'hardware': {'scanner': {'type': 'resonant'}},
            'modalities': ['sim'],
        }

        condition = {
            'all_of': [
                {'parent_present': 'software.analysis'},
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
                {'parent_present': 'software.analysis', 'scanner_type_in': ['resonant']},
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


if __name__ == '__main__':
    unittest.main()
