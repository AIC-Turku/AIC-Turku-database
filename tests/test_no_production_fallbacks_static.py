import unittest
from pathlib import Path


class NoProductionFallbacksStaticTests(unittest.TestCase):
    """Static guardrails against split dataflow regressions in production paths."""

    def test_vm_export_not_sourced_from_dashboard_optical_path(self) -> None:
        src = Path("scripts/build_context.py").read_text(encoding="utf-8")
        self.assertIn("vm_payload = copy.deepcopy(canonical_lightpath_dto", src)
        self.assertNotIn('vm_payload = copy.deepcopy((dashboard_view_dto.get("hardware")', src)

    def test_methods_export_not_using_vm_payload(self) -> None:
        src = Path("scripts/dashboard_builder.py").read_text(encoding="utf-8")
        section = src.split("def build_methods_generator_instrument_export", 1)[1].split("def _display_labels", 1)[0]
        self.assertNotIn("vm_payload", section)

    def test_llm_export_not_using_vm_payload_source_of_truth(self) -> None:
        src = Path("scripts/dashboard_builder.py").read_text(encoding="utf-8")
        section = src.split("def build_llm_inventory_payload", 1)[1].split("def _build_route_planning_summary", 1)[0]
        self.assertNotIn("vm_payload", section)

    def test_production_build_context_uses_strict_parser(self) -> None:
        src = Path("scripts/build_context.py").read_text(encoding="utf-8")
        self.assertIn("canonicalize_light_path_model_strict", src)

    def test_route_sort_order_not_hardcoded_in_python_parser(self) -> None:
        src = Path("scripts/light_path_parser.py").read_text(encoding="utf-8")
        self.assertNotIn("ROUTE_SORT_ORDER", src)

    def test_no_silent_unknown_as_authoritative_data(self) -> None:
        # Display-only unknown labels are allowed in templates/tests, but not as
        # authoritative export contracts in production parser/build-context paths.
        for file_path in ["scripts/build_context.py", "scripts/light_path_parser.py"]:
            src = Path(file_path).read_text(encoding="utf-8")
            self.assertNotIn('"Unknown"', src)

    def test_selected_execution_not_replaced_by_route_steps_in_vm_runtime(self) -> None:
        src = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")
        self.assertIn("selected_execution", src)
        self.assertIn("selected_route_steps", src)

    def test_whitelisted_legacy_compatibility_locations_only(self) -> None:
        # Whitelist rationale:
        # - migration script explicitly upgrades legacy YAML
        # - audit script may detect/report legacy topology
        whitelist = {
            "scripts/light_path_parser.py",
            "scripts/migrate_light_paths.py",
            "scripts/full_audit.py",
            "scripts/validate.py",
        }
        for path in Path("scripts").glob("*.py"):
            src = path.read_text(encoding="utf-8")
            mentions_legacy = "import_legacy_light_path_model" in src or "has_legacy_light_path_input" in src
            if mentions_legacy:
                self.assertIn(path.as_posix(), whitelist)


if __name__ == "__main__":
    unittest.main()
