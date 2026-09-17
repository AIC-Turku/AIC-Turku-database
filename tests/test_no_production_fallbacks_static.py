import copy
import re
import unittest
from pathlib import Path

from scripts.dashboard.methods_export import build_methods_generator_instrument_export


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

    def test_llm_export_section_does_not_use_vm_or_dashboard_view_as_authority(self) -> None:
        llm_section = Path("scripts/dashboard/llm_export.py").read_text(encoding="utf-8")
        self.assertNotIn("vm_payload", llm_section)
        self.assertNotIn("dashboard_view_dto", llm_section)
        self.assertNotIn("hardware.get(\"optical_path\")", llm_section)

    def test_methods_export_canonical_facts_are_independent_of_dashboard_view_dto(self) -> None:
        """The facts methods_export.py itself authors from canonical/lightpath DTOs
        must not change when the dashboard-derived `inst["dto"]` is swapped for a
        poisoned one. A previous version of this test only grepped methods_export.py
        for the strings "dashboard_view_dto" and "hardware.optical_path" and passed
        even though the dashboard view is passed in indirectly as `inst["dto"]`.
        """
        canonical = {
            "instrument": {"instrument_id": "scope-x", "display_name": "Scope X"},
            "hardware": {
                "objectives": [{"id": "obj20", "display_label": "20x"}],
                "detectors": [{"id": "cam1", "display_label": "Camera 1"}],
                "sources": [{"id": "laser1", "display_label": "488 nm laser"}],
            },
            "software": [{"role": "acquisition", "name": "RealControl", "version": "1.0"}],
            "software_status": "documented",
            "capabilities": {"confocal": True},
        }
        lightpath_dto = {
            "light_paths": [
                {
                    "id": "route1",
                    "name": "Route One",
                    "selected_execution": {"selected_route_steps": []},
                }
            ],
        }

        inst_clean = {
            "id": "scope-x",
            "canonical": copy.deepcopy(canonical),
            "lightpath_dto": copy.deepcopy(lightpath_dto),
            "dto": {},
        }
        inst_poisoned = {
            "id": "scope-x",
            "canonical": copy.deepcopy(canonical),
            "lightpath_dto": copy.deepcopy(lightpath_dto),
            "dto": {
                "id": "poison-id",
                "display_name": "Poisoned Display Name",
                "objectives": [{"id": "poison_obj", "display_label": "Fake objective"}],
                "detectors": [{"id": "poison_det", "display_label": "Fake detector"}],
                "software": [{"role": "acquisition", "name": "PoisonControl"}],
                "capabilities": {"sted": True},
                "routes": [{"id": "poison_route", "display_label": "Fake route"}],
            },
        }

        clean_out = build_methods_generator_instrument_export(inst_clean)
        poisoned_out = build_methods_generator_instrument_export(inst_poisoned)

        for key in ("id", "display_name", "objectives", "detectors", "light_sources",
                    "software", "capabilities", "routes", "diagnostics", "methods_view_dto"):
            self.assertEqual(
                clean_out[key], poisoned_out[key],
                f"methods export field {key!r} changed when only the dashboard-derived "
                "dto was poisoned; it must be sourced from canonical/lightpath DTOs only",
            )

    @unittest.expectedFailure
    def test_methods_export_prose_should_not_depend_on_dashboard_view_dto(self) -> None:
        """Known gap (PR #462 follow-up review, finding 1/3): methods_export.py reads
        `dto.get("identity")`, `dto.get("retired")` and `dto["hardware"]["optical_path"]`
        directly off the dashboard-derived `inst["dto"]` rather than off canonical/
        lightpath DTOs, so the generated prose and QUAREP prompt are not actually
        independent of the dashboard view. Remove @unittest.expectedFailure once
        _microscope_sentence/_ground_methods_projection are changed to source
        identity and route-optical-facts from canonical/lightpath instead of `dto`.
        """
        canonical = {
            "instrument": {"instrument_id": "scope-x", "display_name": "Scope X"},
            "hardware": {"objectives": [], "detectors": [], "sources": []},
            "software": [],
            "software_status": "not_applicable",
            "capabilities": {},
        }
        lightpath_dto = {
            "light_paths": [
                {
                    "id": "route1",
                    "name": "Route One",
                    "selected_execution": {"selected_route_steps": []},
                }
            ],
        }

        inst_clean = {
            "id": "scope-x",
            "canonical": copy.deepcopy(canonical),
            "lightpath_dto": copy.deepcopy(lightpath_dto),
            "dto": {},
        }
        inst_poisoned = {
            "id": "scope-x",
            "canonical": copy.deepcopy(canonical),
            "lightpath_dto": copy.deepcopy(lightpath_dto),
            "dto": {
                "identity": {
                    "manufacturer": "PoisonCorp",
                    "model": "Fake9000",
                    "stand_orientation": {"display_label": "upright"},
                },
                "retired": True,
                "hardware": {
                    "optical_path": {
                        "authoritative_route_contract": {
                            "routes": [
                                {
                                    "id": "route1",
                                    "display_label": "Route One",
                                    "route_optical_facts": {
                                        "selected_or_selectable_emission_filters": [
                                            {
                                                "id": "poison_filter",
                                                "display_label": "Poison Filter",
                                                "selection_state": "selectable",
                                                "available_positions": [
                                                    {"position_key": "1", "display_label": "DAPI"},
                                                ],
                                            }
                                        ]
                                    },
                                }
                            ]
                        }
                    }
                },
            },
        }

        clean_out = build_methods_generator_instrument_export(inst_clean)
        poisoned_out = build_methods_generator_instrument_export(inst_poisoned)

        self.assertEqual(
            clean_out["methods"]["base_sentence"], poisoned_out["methods"]["base_sentence"]
        )
        self.assertEqual(
            clean_out["methods"]["retired_review_prompt"], poisoned_out["methods"]["retired_review_prompt"]
        )
        self.assertEqual(
            clean_out["methods"].get("quarep_light_path_recommendation_needed", False),
            poisoned_out["methods"].get("quarep_light_path_recommendation_needed", False),
        )

    def test_legacy_import_usage_is_whitelisted(self) -> None:
        for path in Path("scripts").rglob("*.py"):
            src = path.read_text(encoding="utf-8")
            if "import_legacy_light_path_model" in src or re.search(r"\bcanonicalize_light_path_model\(", src):
                self.assertIn(path.as_posix(), LEGACY_IMPORT_WHITELIST)


if __name__ == "__main__":
    unittest.main()
