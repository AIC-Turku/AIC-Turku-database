import unittest

from scripts.build_context import build_instrument_context
from scripts.dashboard_builder import (
    build_instrument_mega_dto,
    build_llm_inventory_payload,
    build_methods_generator_instrument_export,
)
from scripts.validate import Vocabulary


class DataflowContractE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.vocabulary = Vocabulary(vocab_registry={
            "modalities": {"source": "inline", "allowed_values": ["confocal", "custom_mode"]},
            "detector_kinds": {"source": "inline", "allowed_values": ["camera", "hybrid"]},
            "light_source_kinds": {"source": "inline", "allowed_values": ["laser"]},
        })

    def _fixture_inst(self):
        canonical = {
            "instrument": {"instrument_id": "scope-e2e", "display_name": "Scope E2E"},
            "modalities": ["custom_mode"],
            "software": [{"id": "sw_ctrl", "name": "ControlSoft"}],
            "hardware": {
                "sources": [{"id": "src_488", "kind": "laser", "model": "488 Laser"}],
                "detectors": [{"id": "det_cam", "kind": "camera", "model": "Main Cam"}],
                "objectives": [{"id": "obj_60", "model": "60x"}],
                "optical_path_elements": [{"id": "cube_1", "stage_role": "cube", "element_type": "filter_cube_turret"}],
                "endpoints": [{"id": "det_cam", "endpoint_type": "camera"}],
            },
            "policy": {},
        }
        lightpath_dto = {
            "sources": [{"id": "src_488"}],
            "optical_path_elements": [{"id": "cube_1"}],
            "endpoints": [{"id": "det_cam"}],
            "light_paths": [
                {"id": "route_custom", "name": "Route Custom", "selected_execution": {"selected_route_steps": []}},
                {"id": "route_secondary", "name": "Route Secondary", "selected_execution": {"selected_route_steps": []}},
            ],
            "projections": {"llm": {"authoritative_route_contract": {"available_routes": [{"id": "route_custom", "display_label": "Route Custom"}, {"id": "route_secondary", "display_label": "Route Secondary"}], "routes": [{"id": "route_custom"}, {"id": "route_secondary"}]}}}
        }
        return {"id": "scope-e2e", "display_name": "Scope E2E", "canonical": canonical, "lightpath_dto": lightpath_dto, "dto": {"id": "scope-e2e", "display_name": "Scope E2E"}}

    def test_e2e_contract_alignment(self):
        inst = self._fixture_inst()
        ctx = build_instrument_context(
            inst,
            vocabulary=self.vocabulary,
            build_dashboard_view_dto=build_instrument_mega_dto,
            build_methods_view_dto=build_methods_generator_instrument_export,
            build_llm_inventory_record=lambda i: {"id": i["id"]},
        )
        inst["dto"] = ctx.dashboard_view_dto
        inst["lightpath_dto"] = ctx.canonical_lightpath_dto
        methods = build_methods_generator_instrument_export(inst)
        llm = build_llm_inventory_payload({"short_name": "Core"}, [inst])["active_microscopes"][0]
        vm = ctx.vm_payload

        self.assertEqual(ctx.instrument_id, methods["id"])
        self.assertEqual(methods["display_name"], llm["display_name"])

        canonical_routes = [r["id"] for r in inst["lightpath_dto"]["light_paths"]]
        self.assertEqual(canonical_routes, [r["id"] for r in methods["methods_view_dto"]["routes"]])
        self.assertEqual(canonical_routes, [r["id"] for r in vm["light_paths"]])

        canonical_source_ids = {s["id"] for s in inst["canonical"]["hardware"]["sources"]}
        methods_source_ids = {s["id"] for s in methods["methods_view_dto"]["light_sources"]}
        vm_source_ids = {s["id"] for s in vm["sources"]}
        self.assertEqual(canonical_source_ids, methods_source_ids)
        self.assertEqual(canonical_source_ids, vm_source_ids)

        canonical_endpoint_ids = {e["id"] for e in inst["canonical"]["hardware"]["endpoints"]}
        vm_endpoint_ids = {e["id"] for e in vm["endpoints"]}
        self.assertEqual(canonical_endpoint_ids, vm_endpoint_ids)

    def test_negative_missing_canonical_data_produces_diagnostics(self):
        inst = {"id": "scope-bad", "canonical": {}, "dto": {"id": "scope-bad"}, "lightpath_dto": {}}
        ctx = build_instrument_context(
            inst,
            vocabulary=self.vocabulary,
            build_dashboard_view_dto=lambda *_args, **_kwargs: {"hardware": {"optical_path": {}}},
            build_methods_view_dto=build_methods_generator_instrument_export,
            build_llm_inventory_record=lambda *_args, **_kwargs: {},
        )
        self.assertTrue(ctx.diagnostics)

    def test_custom_route_id_and_name_preserved(self):
        inst = self._fixture_inst()
        methods = build_methods_generator_instrument_export(inst)
        self.assertEqual(methods["methods_view_dto"]["routes"][0]["id"], "route_custom")
        self.assertEqual(methods["methods_view_dto"]["routes"][0]["display_label"], "Route Custom")


if __name__ == "__main__":
    unittest.main()
