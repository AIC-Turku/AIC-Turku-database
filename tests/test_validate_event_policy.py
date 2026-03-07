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

from scripts.validate import validate_event_ledgers


class EventPolicyValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmpdir.name)
        self.prev_cwd = Path.cwd()
        os.chdir(self.repo)

        (self.repo / 'schema').mkdir(parents=True, exist_ok=True)
        (self.repo / 'vocab').mkdir(parents=True, exist_ok=True)
        (self.repo / 'qc/sessions/scope-1/2026').mkdir(parents=True, exist_ok=True)
        (self.repo / 'maintenance/events/scope-1/2026').mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        os.chdir(self.prev_cwd)
        self._tmpdir.cleanup()

    def _write_yaml(self, relative: str, payload: dict) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding='utf-8')

    def test_qc_requiredness_and_unsupported_conditions_reported(self) -> None:
        self._write_yaml(
            'schema/QC_policy.yaml',
            {
                'record_type': 'qc_session',
                'vocab_registry': {
                    'qc_type': {'source': 'inline', 'allowed_values': ['laser_power']},
                },
                'field_rules': [
                    {'path': 'record_type', 'status': 'required', 'type': 'string', 'allowed_values': ['qc_session']},
                    {'path': 'microscope', 'status': 'required', 'type': 'instrument_id'},
                    {'path': 'performed', 'status': 'required', 'type': 'list', 'min_items': 1},
                    {'path': 'performed[].qc_type', 'status': 'required', 'type': 'enum', 'vocab': 'qc_type'},
                    {
                        'path': 'laser_inputs_human',
                        'status': 'conditionally_required',
                        'type': 'mapping',
                        'required_if': {'unsupported_key': True},
                    },
                    {
                        'path': 'performed_by',
                        'status': 'required',
                        'type': 'string',
                    },
                ],
                'legacy_and_migration_rules': [],
                'cross_field_rules': [],
            },
        )
        self._write_yaml(
            'schema/maintenance_policy.yaml',
            {'record_type': 'maintenance_event', 'field_rules': [], 'vocab_registry': {}},
        )

        self._write_yaml(
            'qc/sessions/scope-1/2026/2026-01-01_qc.yaml',
            {
                'record_type': 'qc_session',
                'microscope': 'scope-1',
                'started_utc': '2026-01-01T00:00:00Z',
                'performed': [{'qc_type': 'laser_power'}],
            },
        )

        report = validate_event_ledgers(instrument_ids={'scope-1'})
        error_codes = {issue.code for issue in report.errors}

        self.assertIn('missing_required_field', error_codes)
        self.assertIn('unsupported_required_if_condition', error_codes)

    def test_maintenance_legacy_migration_and_vocab_warnings(self) -> None:
        self._write_yaml(
            'schema/QC_policy.yaml',
            {'record_type': 'qc_session', 'field_rules': [], 'vocab_registry': {}},
        )
        self._write_yaml(
            'schema/maintenance_policy.yaml',
            {
                'record_type': 'maintenance_event',
                'vocab_registry': {
                    'reason': {'source': 'file', 'path': 'vocab/maintenance_reason.yaml'},
                    'service_provider': {'source': 'inline', 'allowed_values': ['vendor', 'internal']},
                },
                'field_rules': [
                    {'path': 'record_type', 'status': 'required', 'type': 'string', 'allowed_values': ['maintenance_event']},
                    {'path': 'microscope', 'status': 'required', 'type': 'instrument_id'},
                    {'path': 'event_id', 'status': 'legacy_alias', 'type': 'string'},
                    {
                        'path': 'maintenance_id',
                        'status': 'conditionally_required',
                        'type': 'string',
                        'required_if': {'missing_legacy_event_id': True},
                    },
                    {'path': 'started_utc', 'status': 'required', 'type': 'datetime_utc'},
                    {'path': 'reason', 'status': 'required', 'type': 'enum', 'vocab': 'reason'},
                    {'path': 'service_provider', 'status': 'required', 'type': 'enum', 'vocab': 'service_provider'},
                ],
                'legacy_and_migration_rules': [
                    {'path': 'event_id', 'migrate_to': 'maintenance_id', 'migration_prompt': 'move event_id to maintenance_id'},
                ],
                'cross_field_rules': [
                    {'id': 'exactly_one_primary_id'},
                ],
            },
        )

        self._write_yaml(
            'vocab/maintenance_reason.yaml',
            {
                'terms': [
                    {'id': 'cleaning', 'synonyms': ['Cleaning']},
                ]
            },
        )

        self._write_yaml(
            'maintenance/events/scope-1/2026/2026-01-02_maint.yaml',
            {
                'record_type': 'maintenance_event',
                'microscope': 'scope-1',
                'event_id': 'maint_scope-1_20260102_vendor',
                'started_utc': '2026-01-02T10:00:00Z',
                'reason': 'Cleaning',
                'service_provider': 'vendor',
                'unexpected_field': 'boom',
            },
        )

        report = validate_event_ledgers(instrument_ids={'scope-1'})

        self.assertTrue(any(issue.code == 'legacy_field_present' for issue in report.migration_notices))
        self.assertTrue(any(issue.code == 'vocab_synonym_used' for issue in report.warnings))
        self.assertTrue(any(issue.code == 'unsupported_event_field' for issue in report.errors))
        self.assertFalse(any('maintenance_id' in issue.path and issue.code == 'missing_required_field' for issue in report.errors))


if __name__ == '__main__':
    unittest.main()
