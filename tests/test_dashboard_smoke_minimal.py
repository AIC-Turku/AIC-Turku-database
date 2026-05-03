import copy
import unittest
from pathlib import Path
import tempfile
import os

import yaml  # type: ignore[import]

from scripts.dashboard.llm_export import build_llm_inventory_payload
from scripts.dashboard.methods_export import build_methods_generator_instrument_export
from scripts.dashboard.vm_export import build_vm_payload
from scripts.dashboard.loaders import evaluate_instrument_status
from scripts.dashboard.loaders import get_all_instrument_logs
from scripts.validate import validate_event_ledgers


class DashboardSmokeMinimalTests(unittest.TestCase):
    def test_llm_export_payload_shape(self) -> None:
        payload = build_llm_inventory_payload({}, [])
        self.assertIn('policy', payload)
        self.assertIn('active_microscopes', payload)
        self.assertIsInstance(payload['active_microscopes'], list)

    def test_methods_export_missing_selected_execution_diagnostic(self) -> None:
        baseline = {"id": "stale-id", "hardware": {"objectives": [{"id": "stale_obj"}]}}
        inst = {
            "dto": copy.deepcopy(baseline),
            'canonical': {'instrument': {'instrument_id': 'abc'}},
            'lightpath_dto': {'light_paths': [{'id': 'r1'}]},
            "canonical_instrument_dto": {
                "hardware": {
                    "objectives": [{"id": "obj_1"}],
                    "detectors": [{"id": "det_1"}],
                    "sources": [{"id": "src_1"}],
                },
                "software": [{"name": "AcqSoft"}],
            },
            "runtime_selected_configuration": {"route_id": "r1"},
        }
        out = build_methods_generator_instrument_export(inst)
        diags = out['methods_view_dto']['diagnostics']
        self.assertTrue(any(d.get('code') == 'missing_selected_execution' for d in diags if isinstance(d, dict)))
        for key in [
            "objectives",
            "detectors",
            "light_sources",
            "software",
            "routes",
            "diagnostics",
            "runtime_selected_configuration",
            "methods_view_dto",
        ]:
            self.assertIn(key, out)
        self.assertEqual(out["objectives"][0]["id"], "obj_1")
        self.assertEqual(out["detectors"][0]["id"], "det_1")
        self.assertEqual(out["light_sources"][0]["id"], "src_1")
        self.assertIsNone(out["runtime_selected_configuration"])
        self.assertEqual(inst["dto"], baseline)

    def test_methods_export_canonical_id_takes_precedence_over_stale_dto_id(self) -> None:
        # Invariant 2: canonical/methods-derived data must win over stale dashboard baseline.
        inst = {
            "id": "canonical-id",
            "display_name": "Canonical Name",
            "dto": {"id": "stale-id", "display_name": "Stale Name"},
            "lightpath_dto": {"light_paths": []},
        }
        out = build_methods_generator_instrument_export(inst)
        self.assertEqual(out["id"], "canonical-id")
        self.assertEqual(out["display_name"], "Canonical Name")
        # Original dto must not be mutated.
        self.assertEqual(inst["dto"]["id"], "stale-id")

    def test_vm_export_deepcopy_and_display_name(self) -> None:
        inst = {
            'id': 'scope-1',
            'display_name': 'Scope One',
            'lightpath_dto': {'light_paths': []},
        }
        vm = build_vm_payload(inst)
        self.assertEqual(vm.get('instrument_id'), 'scope-1')
        self.assertEqual(vm.get('display_name'), 'Scope One')
        vm['light_paths'].append({'id': 'mut'})
        self.assertEqual(inst['lightpath_dto']['light_paths'], [])

    def test_evaluate_instrument_status_green_yellow_red(self) -> None:
        green = evaluate_instrument_status({}, {})
        yellow = evaluate_instrument_status({'evaluation': {'overall_status': 'warn'}}, {})
        red = evaluate_instrument_status({'evaluation': {'overall_status': 'fail'}}, {})
        self.assertEqual(green['color'], 'green')
        self.assertEqual(yellow['color'], 'yellow')
        self.assertEqual(red['color'], 'red')

    def test_qc_maintenance_events_propagate_to_dashboard_and_llm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "schema").mkdir(parents=True, exist_ok=True)
            (repo / "vocab").mkdir(parents=True, exist_ok=True)
            (repo / "qc/sessions/scope-1/2026").mkdir(parents=True, exist_ok=True)
            (repo / "maintenance/events/scope-1/2026").mkdir(parents=True, exist_ok=True)
            (repo / "schema/QC_policy.yaml").write_text(yaml.safe_dump({"record_type": "qc_session", "field_rules": []}))
            (repo / "schema/maintenance_policy.yaml").write_text(yaml.safe_dump({"record_type": "maintenance_event", "field_rules": []}))
            (repo / "qc/sessions/scope-1/2026/2026-01-01_qc.yaml").write_text(yaml.safe_dump({"record_type": "qc_session", "microscope": "scope-1", "date": "2026-01-01", "evaluation": {"overall_status": "warn", "summary": "drift"}}))
            (repo / "maintenance/events/scope-1/2026/2026-01-02_maint.yaml").write_text(yaml.safe_dump({"record_type": "maintenance_event", "microscope": "scope-1", "date": "2026-01-02", "service_provider": "Vendor", "status": "limited", "reason": "laser_alignment"}))

            cwd = Path.cwd()
            os.chdir(repo)
            try:
                report = validate_event_ledgers(instrument_ids={"scope-1"})
            finally:
                os.chdir(cwd)
            self.assertFalse(report.errors)

            cwd = Path.cwd()
            os.chdir(repo)
            try:
                qc_logs = get_all_instrument_logs("qc/sessions", "scope-1")
                maint_logs = get_all_instrument_logs("maintenance/events", "scope-1")
            finally:
                os.chdir(cwd)
            self.assertEqual(qc_logs[-1]["data"]["microscope"], "scope-1")
            self.assertEqual(maint_logs[-1]["data"]["service_provider"], "Vendor")
            self.assertEqual(maint_logs[-1]["data"]["status"], "limited")

            status = evaluate_instrument_status(qc_logs[-1]["data"], maint_logs[-1]["data"])
            self.assertEqual(status["color"], "yellow")


if __name__ == '__main__':
    unittest.main()
