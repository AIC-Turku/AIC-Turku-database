import importlib
import sys
import types
import unittest
from unittest.mock import patch

from scripts.audit_analyzer import analyze_instrument_completeness


class AuditPdfPhase1Tests(unittest.TestCase):
    def test_default_selected_sections_include_all_registered_sections(self) -> None:
        weasyprint_stub = types.ModuleType("weasyprint")
        weasyprint_stub.CSS = object
        weasyprint_stub.HTML = object
        with patch.dict(sys.modules, {"weasyprint": weasyprint_stub}):
            module = importlib.import_module("scripts.generate_audit_pdfs")

        with patch.dict("os.environ", {}, clear=True):
            selected = module._selected_sections()

        self.assertEqual([section["key"] for section in selected], list(module.SECTION_DEFINITIONS))
        self.assertIn("capabilities", module.SECTION_DEFINITIONS)
        self.assertIn("modules", module.SECTION_DEFINITIONS)
        self.assertIn("endpoints", module.SECTION_DEFINITIONS)
        self.assertIn("optical_path_elements", module.SECTION_DEFINITIONS)
        self.assertIn("light_paths", module.SECTION_DEFINITIONS)
        self.assertIn("policy", module.SECTION_DEFINITIONS)
        self.assertIn("provenance", module.SECTION_DEFINITIONS)

    def test_selected_sections_still_supports_explicit_subset(self) -> None:
        weasyprint_stub = types.ModuleType("weasyprint")
        weasyprint_stub.CSS = object
        weasyprint_stub.HTML = object
        with patch.dict(sys.modules, {"weasyprint": weasyprint_stub}):
            module = importlib.import_module("scripts.generate_audit_pdfs")

        with patch.dict("os.environ", {"AUDIT_PDF_SECTIONS": "objectives,endpoints"}, clear=True):
            selected = module._selected_sections()

        self.assertEqual([section["key"] for section in selected], ["objectives", "endpoints"])

    def test_analyzer_exposes_phase1_canonical_sections(self) -> None:
        audit = analyze_instrument_completeness(
            {
                "id": "scope-phase1",
                "display_name": "Phase 1 Scope",
                "canonical": {
                    "capabilities": {
                        "imaging_modes": ["confocal_point"],
                        "readouts": ["flim"],
                    },
                    "modules": [
                        {
                            "name": "Camera Port",
                            "type": "camera_port",
                            "manufacturer": "ExampleCo",
                        }
                    ],
                    "hardware": {
                        "detectors": [],
                        "endpoints": [
                            {
                                "id": "cam_a",
                                "kind": "camera",
                                "endpoint_type": "camera",
                            }
                        ],
                        "optical_path_elements": [
                            {
                                "id": "em_filter",
                                "stage_role": "emission",
                                "positions": {1: {"type": "bandpass", "center_nm": 525}},
                            }
                        ],
                    },
                    "light_paths": [
                        {
                            "id": "confocal",
                            "route_type": "confocal_point",
                            "readouts": ["flim"],
                            "illumination_sequence": [{"source_id": "laser_488"}],
                            "detection_sequence": [{"endpoint_id": "cam_a"}],
                        }
                    ],
                    "policy": {
                        "missing_required": [
                            {"path": "hardware.objectives", "title": "Objectives"}
                        ],
                        "missing_conditional": [],
                    },
                    "provenance": {
                        "source_contract": "validated_canonical_yaml",
                        "deprecated_compatibility": {
                            "top_level_objectives_to_hardware_objectives": False,
                        },
                    },
                },
            }
        )

        self.assertEqual(audit["capabilities"][0]["label"], "Capabilities Imaging Modes")
        self.assertEqual(audit["modules"][0]["label"], "Module 1 Name")
        self.assertEqual(audit["endpoints"][0]["label"], "Endpoint 1 Id")
        self.assertIn(
            "Optical Path Element 1 Positions 1 Type",
            {entry["label"] for entry in audit["optical_path_elements"]},
        )
        self.assertIn("Light Path 1 Id", {entry["label"] for entry in audit["light_paths"]})
        self.assertIn("Policy Missing Required 1 Path", {entry["label"] for entry in audit["policy"]})
        self.assertIn("Provenance Source Contract", {entry["label"] for entry in audit["provenance"]})

        detector_values = {str(entry["value"]) for entry in audit["detectors"]}
        self.assertNotIn("Manual Observation Only", detector_values)
        self.assertNotIn("External Camera Port Available", detector_values)


if __name__ == "__main__":
    unittest.main()
