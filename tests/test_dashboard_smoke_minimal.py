import copy
import unittest

from scripts.dashboard.llm_export import build_llm_inventory_payload
from scripts.dashboard.methods_export import build_methods_generator_instrument_export
from scripts.dashboard.vm_export import build_vm_payload
from scripts.dashboard.loaders import evaluate_instrument_status


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


if __name__ == '__main__':
    unittest.main()
