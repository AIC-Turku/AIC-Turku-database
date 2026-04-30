import re
import unittest
from pathlib import Path


PRODUCTION_SCAN_FILES = [
    "scripts/light_path_parser.py",
    "scripts/dashboard_builder.py",
    "scripts/build_context.py",
    "scripts/dashboard/vm_export.py",
    "scripts/dashboard/llm_export.py",
    "scripts/dashboard/methods_export.py",
    "scripts/templates/virtual_microscope_runtime.js",
    "scripts/templates/virtual_microscope_app.js",
    "assets/javascripts/methods_generator_app.js",
]

# Explicit whitelist: migration/audit compatibility only.
LEGACY_IMPORT_WHITELIST = {
    "scripts/light_path_parser.py",
    "scripts/lightpath/legacy_import.py",
    "scripts/lightpath/parse_canonical.py",
    "scripts/lightpath/model.py",
    "scripts/lightpath/__init__.py",
    "scripts/lightpath/vm_payload.py",
    "scripts/lightpath/validate_contract.py",
    "scripts/migrate_light_paths.py",
    "scripts/full_audit.py",
    "scripts/validate.py",
    "scripts/validation/instrument.py",
}


def _violations_for_source(source: str) -> list[str]:
    violations: list[str] = []
    if 'vm_payload = copy.deepcopy((dashboard_view_dto.get("hardware")' in source:
        violations.append("vm_from_dashboard_optical_path")
    if "hardware.get(\"optical_path\")" in source:
        violations.append("dashboard_optical_path_as_authority")
    if "ROUTE_SORT_ORDER" in source or "ROUTE_LABELS" in source or "ROUTE_TAGS" in source or "RESERVED_ROUTE_TAGS" in source:
        violations.append("route_constant_hardcoding")
    if "itemRoutes.includes('shared')" in source or "itemRoutes.includes('all')" in source:
        violations.append("route_magic_shared_all")
    if "record.route_steps" in source and "function selectedRouteStepsForRecord" in source:
        violations.append("selected_steps_fallback_to_route_steps")
    if "optical_path.light_paths or optical_path.route_renderables or optical_path.routes" in source:
        violations.append("dashboard_optical_path_compat_chain")
    return violations


class NoProductionFallbacksStaticTests(unittest.TestCase):
    def test_violation_detector_catches_deliberate_forbidden_examples(self) -> None:
        fake = "function selectedRouteStepsForRecord(){ return record.route_steps; } const x=itemRoutes.includes('shared');"
        violations = _violations_for_source(fake)
        self.assertIn("selected_steps_fallback_to_route_steps", violations)
        self.assertIn("route_magic_shared_all", violations)

    def test_production_files_have_no_forbidden_fallback_patterns(self) -> None:
        for file_path in PRODUCTION_SCAN_FILES:
            src = Path(file_path).read_text(encoding="utf-8")
            violations = _violations_for_source(src)
            self.assertEqual([], violations, f"{file_path} contains forbidden production fallback patterns: {violations}")

    def test_methods_and_llm_export_sections_do_not_use_vm_or_dashboard_view_as_authority(self) -> None:
        methods_section = Path("scripts/dashboard/methods_export.py").read_text(encoding="utf-8")
        self.assertNotIn("vm_payload", methods_section)
        self.assertNotIn("dashboard_view_dto", methods_section)
        self.assertNotIn("hardware.optical_path", methods_section)

        llm_section = Path("scripts/dashboard/llm_export.py").read_text(encoding="utf-8")
        self.assertNotIn("vm_payload", llm_section)
        self.assertNotIn("dashboard_view_dto", llm_section)
        self.assertNotIn("hardware.get(\"optical_path\")", llm_section)

    def test_legacy_import_usage_is_whitelisted(self) -> None:
        for path in Path("scripts").rglob("*.py"):
            src = path.read_text(encoding="utf-8")
            if "import_legacy_light_path_model" in src or re.search(r"\bcanonicalize_light_path_model\(", src):
                self.assertIn(path.as_posix(), LEGACY_IMPORT_WHITELIST)


if __name__ == "__main__":
    unittest.main()
