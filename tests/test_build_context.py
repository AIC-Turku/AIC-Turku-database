import copy
import unittest

from scripts.build_context import build_instrument_context
from scripts.lightpath.legacy_import import migrate_instrument_to_light_path_v2


class BuildContextTests(unittest.TestCase):
    def _minimal_instrument(self) -> dict:
        return {
            "id": "scope-testx1",
            "source_file": "instruments/Test Scope.yaml",
            "source_payload": {"instrument": {"instrument_id": "scope-testx1"}},
            "canonical": {
                "instrument": {"instrument_id": "scope-testx1", "display_name": "Test Scope"},
                "hardware": {"sources": [{"id": "src_a", "kind": "laser"}], "optical_path_elements": [], "endpoints": []},
            },
            "dto": {"id": "scope-testx1"},
        }

    def test_minimal_fixture_builds_context_successfully(self) -> None:
        inst = self._minimal_instrument()

        context = build_instrument_context(
            inst,
            vocabulary=None,
            build_dashboard_view_dto=lambda _v, i, lp: {"id": i["id"], "hardware": {"optical_path": {"routes": []}}, "lightpath": lp},
            build_methods_view_dto=lambda i: {"id": i["id"], "methods": {}},
            build_llm_inventory_record=lambda i: {"id": i["id"], "summary": {}},
        )

        self.assertEqual(context.instrument_id, "scope-testx1")
        self.assertIsInstance(context.canonical_instrument_dto, dict)
        self.assertIsInstance(context.dashboard_view_dto, dict)

    def test_context_contains_canonical_and_derived_dtos(self) -> None:
        inst = self._minimal_instrument()
        context = build_instrument_context(
            inst,
            vocabulary=None,
            build_dashboard_view_dto=lambda _v, i, lp: {"derived_kind": "dashboard_view", "id": i["id"], "hardware": {"optical_path": {}}, "lp": lp},
            build_methods_view_dto=lambda i: {"derived_kind": "methods_view", "id": i["id"]},
            build_llm_inventory_record=lambda i: {"derived_kind": "llm_record", "id": i["id"]},
        )

        self.assertIn("instrument", context.canonical_instrument_dto)
        self.assertEqual(context.dashboard_view_dto.get("derived_kind"), "dashboard_view")
        self.assertEqual(context.methods_view_dto.get("derived_kind"), "methods_view")

    def test_canonical_and_derived_are_distinguishable(self) -> None:
        inst = self._minimal_instrument()
        context = build_instrument_context(
            inst,
            vocabulary=None,
            build_dashboard_view_dto=lambda _v, i, lp: {"view_contract": "derived", "id": i["id"], "hardware": {"optical_path": {}}, "lp": lp},
            build_methods_view_dto=lambda i: {"view_contract": "derived_methods", "id": i["id"]},
            build_llm_inventory_record=lambda i: {"view_contract": "derived_llm", "id": i["id"]},
        )

        self.assertIn("instrument", context.canonical_instrument_dto)
        self.assertEqual(context.dashboard_view_dto.get("view_contract"), "derived")
        self.assertNotIn("view_contract", context.canonical_instrument_dto)

    def test_diagnostics_capture_payload_errors(self) -> None:
        import scripts.build_context as bc

        inst = self._minimal_instrument()
        original = bc.generate_virtual_microscope_payload
        bc.generate_virtual_microscope_payload = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            context = build_instrument_context(
                inst,
                vocabulary=None,
                build_dashboard_view_dto=lambda _v, i, _lp: {"id": i["id"], "hardware": {"optical_path": {}}},
                build_methods_view_dto=lambda i: copy.deepcopy(i.get("dto") or {}),
                build_llm_inventory_record=lambda i: copy.deepcopy(i.get("dto") or {}),
            )
        finally:
            bc.generate_virtual_microscope_payload = original

        self.assertTrue(any(item.get("code") == "lightpath_payload_error" for item in context.diagnostics))

    def test_vm_payload_is_not_taken_from_dashboard_view_dto(self) -> None:
        import scripts.build_context as bc

        inst = self._minimal_instrument()
        original = bc.generate_virtual_microscope_payload
        original_strict = bc.canonicalize_light_path_model_strict
        bc.canonicalize_light_path_model_strict = lambda *_args, **_kwargs: {"ok": True}
        bc.generate_virtual_microscope_payload = lambda *_args, **_kwargs: {
            "sources": [{"id": "src_a"}],
            "optical_path_elements": [{"id": "elem_a"}],
            "endpoints": [{"id": "end_a"}],
            "light_paths": [
                {"id": "route_custom_2", "selected_execution": {"route_id": "route_custom_2", "selected_route_steps": []}},
                {"id": "route_custom_1", "selected_execution": {"route_id": "route_custom_1", "selected_route_steps": []}},
            ],
        }
        try:
            context = build_instrument_context(
                inst,
                vocabulary=None,
                build_dashboard_view_dto=lambda _v, i, _lp: {"id": i["id"], "hardware": {"optical_path": {"from": "dashboard_view"}}},
                build_methods_view_dto=lambda i: {"id": i["id"]},
                build_llm_inventory_record=lambda i: {"id": i["id"]},
            )
        finally:
            bc.generate_virtual_microscope_payload = original
            bc.canonicalize_light_path_model_strict = original_strict

        self.assertIn("sources", context.vm_payload)
        self.assertIn("optical_path_elements", context.vm_payload)
        self.assertIn("endpoints", context.vm_payload)
        self.assertIn("light_paths", context.vm_payload)
        self.assertEqual([route["id"] for route in context.vm_payload["light_paths"]], ["route_custom_2", "route_custom_1"])
        self.assertTrue(all("selected_execution" in route for route in context.vm_payload["light_paths"]))
        self.assertTrue(all(isinstance(route["selected_execution"].get("selected_route_steps"), list) for route in context.vm_payload["light_paths"]))
        self.assertNotEqual(context.vm_payload, context.dashboard_view_dto["hardware"]["optical_path"])

    def test_legacy_only_instrument_fails_strict_production_build_context(self) -> None:
        inst = {
            "id": "scope-legacy",
            "source_file": "instruments/legacy.yaml",
            "source_payload": {},
            "canonical": {"hardware": {"light_path": {"filters": []}, "light_sources": [{"wavelength_nm": 488}]}}
        }
        context = build_instrument_context(
            inst,
            vocabulary=None,
            build_dashboard_view_dto=lambda *_args, **_kwargs: {"hardware": {"optical_path": {}}},
            build_methods_view_dto=lambda *_args, **_kwargs: {},
            build_llm_inventory_record=lambda *_args, **_kwargs: {},
        )
        self.assertTrue(any("Legacy-only topology is not allowed" in item.get("message", "") for item in context.diagnostics))

    def test_legacy_only_instrument_can_be_processed_by_migration_tool(self) -> None:
        legacy = {"hardware": {"light_path": {"excitation": []}, "light_sources": [{"wavelength_nm": 488, "type": "laser"}]}}
        migrated = migrate_instrument_to_light_path_v2(legacy)
        self.assertIn("light_paths", migrated)
        self.assertIn("sources", migrated.get("hardware", {}))


if __name__ == "__main__":
    unittest.main()
