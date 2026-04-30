import unittest

from scripts.build_context import build_instrument_context
from scripts.dashboard.instrument_view import build_instrument_mega_dto
from scripts.dashboard.llm_export import build_llm_inventory_payload
from scripts.dashboard.methods_export import build_methods_generator_instrument_export
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
                "light_paths": [
                    {
                        "id": "route_custom",
                        "name": "Route Custom",
                        "illumination_sequence": [{"source_id": "src_488"}],
                        "detection_sequence": [{"endpoint_id": "det_cam"}],
                    },
                    {
                        "id": "route_secondary",
                        "name": "Route Secondary",
                        "illumination_sequence": [{"source_id": "src_488"}],
                        "detection_sequence": [{"endpoint_id": "det_cam"}],
                    },
                ],
            },
            "policy": {},
        }
        return {"id": "scope-e2e", "display_name": "Scope E2E", "canonical": canonical, "dto": {"id": "scope-e2e", "display_name": "Scope E2E"}}

    def test_e2e_contract_alignment(self):
        inst = self._fixture_inst()
        ctx = build_instrument_context(
            inst,
            vocabulary=self.vocabulary,
            build_dashboard_view_dto=build_instrument_mega_dto,
            build_methods_view_dto=build_methods_generator_instrument_export,
            build_llm_inventory_record=lambda i: build_llm_inventory_payload({"short_name": "Core"}, [i])["active_microscopes"][0],
        )
        methods = ctx.methods_export_dto
        llm = ctx.llm_inventory_record
        vm = ctx.vm_payload

        self.assertEqual(ctx.instrument_id, methods["id"])
        self.assertEqual(methods["display_name"], llm["display_name"])
        self.assertEqual(ctx.instrument_id, ctx.dashboard_view_dto["id"])
        self.assertEqual(ctx.instrument_id, vm["instrument"]["instrument_id"])

        canonical_routes = [r["id"] for r in ctx.canonical_lightpath_dto["light_paths"]]
        self.assertEqual(canonical_routes, [r["id"] for r in methods["methods_view_dto"]["routes"]])
        self.assertEqual(canonical_routes, [r["id"] for r in vm["light_paths"]])
        self.assertEqual(canonical_routes, [r["id"] for r in llm["llm_context"]["authoritative_route_contract"]["routes"]])

        canonical_source_ids = {s["id"] for s in ctx.canonical_instrument_dto["hardware"]["sources"]}
        methods_source_ids = {s["id"] for s in methods["methods_view_dto"]["light_sources"]}
        vm_source_ids = {s["id"] for s in vm["sources"]}
        dto_source_ids = {s["id"] for s in ctx.dashboard_view_dto.get("hardware", {}).get("sources", [])}
        self.assertEqual(canonical_source_ids, methods_source_ids)
        self.assertEqual(canonical_source_ids, vm_source_ids)
        self.assertEqual(canonical_source_ids, dto_source_ids)

        canonical_endpoint_ids = {e["id"] for e in ctx.canonical_instrument_dto["hardware"]["endpoints"]}
        vm_endpoint_ids = {e["id"] for e in vm["endpoints"]}
        dto_endpoint_ids = {e["id"] for e in ctx.dashboard_view_dto.get("hardware", {}).get("endpoints", [])}
        methods_endpoint_ids = {d["id"] for d in methods["methods_view_dto"]["detectors"]}
        self.assertEqual(canonical_endpoint_ids, vm_endpoint_ids)
        self.assertEqual(canonical_endpoint_ids, dto_endpoint_ids)
        self.assertEqual(canonical_endpoint_ids, methods_endpoint_ids)

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

    def test_missing_selected_execution_blocks_exports(self):
        import scripts.build_context as bc

        inst = self._fixture_inst()
        original_gen = bc.generate_virtual_microscope_payload

        # Patch vm payload generator to return routes without selected_execution
        # to verify that the build context detects and diagnoses missing execution contract
        bc.generate_virtual_microscope_payload = lambda *args, **kwargs: {
            "sources": [],
            "optical_path_elements": [],
            "endpoints": [],
            "light_paths": [{"id": "route_custom", "name": "Route Custom"}],
        }
        try:
            ctx = build_instrument_context(
                inst,
                vocabulary=self.vocabulary,
                build_dashboard_view_dto=build_instrument_mega_dto,
                build_methods_view_dto=build_methods_generator_instrument_export,
                build_llm_inventory_record=lambda i: build_llm_inventory_payload({"short_name": "Core"}, [i])["active_microscopes"][0],
            )
        finally:
            bc.generate_virtual_microscope_payload = original_gen

        self.assertTrue(any(d.get("code") == "missing_selected_execution" for d in ctx.diagnostics))
        self.assertIn("export_diagnostics", ctx.vm_payload)
        self.assertIn("export_diagnostics", ctx.dashboard_view_dto)
        self.assertIn("export_diagnostics", ctx.methods_export_dto)
        self.assertIn("export_diagnostics", ctx.llm_inventory_record)

    def test_custom_route_id_and_name_preserved(self):
        inst = self._fixture_inst()
        # Use build_instrument_context to exercise the canonical pipeline end-to-end
        ctx = build_instrument_context(
            inst,
            vocabulary=self.vocabulary,
            build_dashboard_view_dto=build_instrument_mega_dto,
            build_methods_view_dto=build_methods_generator_instrument_export,
            build_llm_inventory_record=lambda i: build_llm_inventory_payload({"short_name": "Core"}, [i])["active_microscopes"][0],
        )
        methods = ctx.methods_export_dto
        self.assertEqual(methods["methods_view_dto"]["routes"][0]["id"], "route_custom")
        self.assertEqual(methods["methods_view_dto"]["routes"][0]["display_label"], "Route Custom")


if __name__ == "__main__":
    unittest.main()
