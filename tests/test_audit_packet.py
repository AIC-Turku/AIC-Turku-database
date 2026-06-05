import unittest
import unittest.mock

from scripts.audit_packet import build_staff_validation_packet
from scripts.build_context import build_instrument_context
from scripts.dashboard.instrument_view import build_instrument_mega_dto
from scripts.dashboard.llm_export import build_llm_inventory_payload
from scripts.dashboard.methods_export import build_methods_generator_instrument_export
from scripts.validate import Vocabulary


class StaffValidationPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vocabulary = Vocabulary(
            vocab_registry={
                "detector_kinds": {"source": "inline", "allowed_values": ["camera"]},
                "light_source_kinds": {"source": "inline", "allowed_values": ["laser"]},
            }
        )

    def _context(self):
        inst = {
            "id": "scope-packet",
            "display_name": "Packet Scope",
            "source_file": "instruments/Packet Scope.yaml",
            "canonical": {
                "instrument": {
                    "instrument_id": "scope-packet",
                    "display_name": "Packet Scope",
                },
                "capabilities": {"imaging_modes": ["widefield_fluorescence"]},
                "modules": [{"type": "camera_port", "manufacturer": "ExampleCo"}],
                "software": [{"role": "acquisition", "name": "ControlSoft"}],
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser", "wavelength_nm": 488}],
                    "detectors": [],
                    "objectives": [{"id": "obj_20", "model": "20x"}],
                    "optical_path_elements": [
                        {
                            "id": "em_filter",
                            "stage_role": "emission",
                            "element_type": "filter_wheel",
                            "positions": {1: {"type": "bandpass", "center_nm": 525}},
                        }
                    ],
                    "endpoints": [{"id": "cam_a", "endpoint_type": "camera"}],
                },
                "light_paths": [
                    {
                        "id": "widefield",
                        "illumination_sequence": [{"source_id": "src_488"}],
                        "detection_sequence": [
                            {"optical_path_element_id": "em_filter"},
                            {"endpoint_id": "cam_a"},
                        ],
                    }
                ],
                "policy": {
                    "missing_required": [
                        {
                            "path": "hardware.detectors",
                            "title": "Detectors",
                            "status": "required",
                        }
                    ],
                    "missing_conditional": [],
                    "sections": [],
                    "alias_fallbacks": [],
                },
            },
        }
        return build_instrument_context(
            inst,
            vocabulary=self.vocabulary,
            build_dashboard_view_dto=build_instrument_mega_dto,
            build_methods_view_dto=build_methods_generator_instrument_export,
            build_llm_inventory_record=lambda i: build_llm_inventory_payload(
                {"short_name": "Core"}, [i]
            )["active_microscopes"][0],
        )

    def test_packet_is_built_from_context_with_source_paths(self) -> None:
        packet = build_staff_validation_packet(self._context())

        self.assertEqual(packet.instrument_id, "scope-packet")
        self.assertGreater(len(packet.rows), 0)

        source_paths = {row.source_path for row in packet.rows}
        self.assertIn("canonical_instrument_dto.capabilities.imaging_modes", source_paths)
        self.assertIn("canonical_lightpath_dto.endpoints[0].id", source_paths)
        self.assertIn("canonical_lightpath_dto.light_paths[0].id", source_paths)

        sections = packet.section_entries()
        self.assertIn("capabilities", sections)
        self.assertIn("endpoints", sections)
        self.assertIn("light_paths", sections)
        self.assertTrue(
            all("source_path" in entry for entries in sections.values() for entry in entries)
        )

    def test_packet_includes_diagnostics_and_no_invented_detector_fallbacks(self) -> None:
        packet = build_staff_validation_packet(self._context())
        context = packet.as_template_context()

        self.assertTrue(context["schema_errors"])
        self.assertTrue(context["packet_diagnostics"])

        detector_values = {str(entry["value"]) for entry in context["detectors"]}
        self.assertNotIn("Manual Observation Only", detector_values)
        self.assertNotIn("External Camera Port Available", detector_values)

    def test_packet_serializes_for_json_traceability(self) -> None:
        packet = build_staff_validation_packet(self._context())
        payload = packet.as_dict()

        self.assertEqual(payload["instrument_id"], "scope-packet")
        self.assertTrue(payload["rows"])
        self.assertIn("source_path", payload["rows"][0])
        self.assertIn("schema_errors", payload)

    def test_csv_rows_include_staff_correction_columns(self) -> None:
        import importlib
        import sys
        import types

        weasyprint_stub = types.ModuleType("weasyprint")
        weasyprint_stub.CSS = object
        weasyprint_stub.HTML = object
        with unittest.mock.patch.dict(sys.modules, {"weasyprint": weasyprint_stub}):
            module = importlib.import_module("scripts.generate_audit_pdfs")

        packet = build_staff_validation_packet(self._context())
        rows = module._packet_csv_rows(packet)

        self.assertTrue(rows)
        self.assertEqual(rows[0]["reviewer_status"], "")
        self.assertEqual(rows[0]["reviewer_comment"], "")
        self.assertEqual(rows[0]["corrected_value"], "")
        self.assertIn("source_path", rows[0])

    def test_traceability_payload_includes_full_export_dtos(self) -> None:
        import importlib
        import sys
        import types

        weasyprint_stub = types.ModuleType("weasyprint")
        weasyprint_stub.CSS = object
        weasyprint_stub.HTML = object
        with unittest.mock.patch.dict(sys.modules, {"weasyprint": weasyprint_stub}):
            module = importlib.import_module("scripts.generate_audit_pdfs")

        context = self._context()
        packet = build_staff_validation_packet(context)
        payload = module._traceability_payload(context, packet)

        self.assertIn("canonical_instrument_dto", payload)
        self.assertIn("canonical_lightpath_dto", payload)
        self.assertIn("dashboard_view_dto", payload)
        self.assertIn("methods_export_dto", payload)
        self.assertIn("llm_inventory_record", payload)
        self.assertIn("vm_payload", payload)
        self.assertIn("staff_validation_packet", payload)


if __name__ == "__main__":
    unittest.main()
