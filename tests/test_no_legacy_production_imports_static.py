import unittest
from pathlib import Path


PRODUCTION_MODULES = [
    "scripts/build_context.py",
    "scripts/dashboard_builder.py",
    "scripts/dashboard/loaders.py",
    "scripts/dashboard/instrument_view.py",
    "scripts/dashboard/optical_path_view.py",
    "scripts/dashboard/llm_export.py",
    "scripts/dashboard/methods_export.py",
    "scripts/dashboard/vm_export.py",
]


class NoLegacyProductionImportsStaticTests(unittest.TestCase):
    def test_production_modules_do_not_import_legacy_adapters(self) -> None:
        forbidden_tokens = [
            "import_legacy_light_path_model",
            "scripts.lightpath.legacy_import",
            "from scripts.lightpath import import_legacy_light_path_model",
            "canonicalize_light_path_model(",  # strict production should use strict canonicalizer/build context
        ]
        for file_path in PRODUCTION_MODULES:
            src = Path(file_path).read_text(encoding="utf-8")
            for token in forbidden_tokens:
                self.assertNotIn(token, src, f"Forbidden legacy dependency token '{token}' found in {file_path}")

    def test_whitelisted_legacy_locations(self) -> None:
        # Whitelist rationale:
        # - migration CLI + parser legacy importer wrappers
        # - audit and validation may detect/report legacy topology
        whitelist = {
            "scripts/light_path_parser.py",
            "scripts/lightpath/legacy_import.py",
            "scripts/migrate_light_paths.py",
            "scripts/full_audit.py",
            "scripts/validate.py",
            "docs/dataflow_contract.md",
            "tests/test_build_context.py",
            "tests/test_no_production_fallbacks_static.py",
        }
        for path in Path("scripts").rglob("*.py"):
            src = path.read_text(encoding="utf-8")
            if "import_legacy_light_path_model" in src or "has_legacy_light_path_input" in src:
                if path.as_posix() not in whitelist:
                    # Only enforce on production scripts directory; tests/docs handled separately.
                    self.assertFalse(path.as_posix().startswith("scripts/dashboard"), f"Unexpected legacy marker in production dashboard module: {path}")

    def test_vm_payload_generator_defaults_to_strict_parser(self) -> None:
        src = Path("scripts/light_path_parser.py").read_text(encoding="utf-8")
        section = src.split("def _generate_virtual_microscope_payload_inner", 1)[1].split("def _build_route_sequences_and_graph", 1)[0]
        self.assertIn("parse_strict_canonical_light_path_model", section)


if __name__ == "__main__":
    unittest.main()
