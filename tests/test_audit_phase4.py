import csv
import importlib
import json
import sys
import tempfile
import types
import unittest
import unittest.mock
from pathlib import Path

from scripts.audit_packet import build_staff_validation_packet
from scripts.build_context import build_instrument_context
from scripts.dashboard.instrument_view import build_instrument_mega_dto
from scripts.dashboard.llm_export import build_llm_inventory_payload
from scripts.dashboard.methods_export import build_methods_generator_instrument_export
from scripts.validate import Vocabulary


class Phase4AuditArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vocabulary = Vocabulary(
            vocab_registry={
                "detector_kinds": {"source": "inline", "allowed_values": ["camera"]},
                "light_source_kinds": {"source": "inline", "allowed_values": ["laser"]},
            }
        )

    def _context(self):
        canonical = {
            "instrument": {
                "instrument_id": "scope-phase4",
                "display_name": "Phase 4 Scope",
                "notes": "Authoritative notes",
            },
            "modalities": [],
            "capabilities": {"imaging_modes": ["widefield_fluorescence"]},
            "modules": [{"type": "camera_port", "manufacturer": "ExampleCo"}],
            "notes": "Top-level canonical notes",
            "software": [{"role": "acquisition", "name": "ControlSoft"}],
            "software_status": "documented",
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
            "provenance": {"source_contract": "validated_canonical_yaml"},
        }
        inst = {
            "id": "scope-phase4",
            "display_name": "Phase 4 Scope",
            "source_file": "instruments/Phase 4 Scope.yaml",
            "canonical": canonical,
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

    def _generate_module(self):
        weasyprint_stub = types.ModuleType("weasyprint")
        weasyprint_stub.CSS = object
        weasyprint_stub.HTML = object
        with unittest.mock.patch.dict(sys.modules, {"weasyprint": weasyprint_stub}):
            return importlib.import_module("scripts.generate_audit_pdfs")

    def test_default_pdf_packet_includes_more_than_objectives(self) -> None:
        module = self._generate_module()
        with unittest.mock.patch.dict("os.environ", {}, clear=True):
            section_keys = [section["key"] for section in module._selected_sections()]

        self.assertIn("objectives", section_keys)
        self.assertIn("capabilities", section_keys)
        self.assertIn("canonical_dto_coverage", section_keys)
        self.assertGreater(len(section_keys), 1)

    def test_every_top_level_canonical_dto_key_appears_in_packet(self) -> None:
        context = self._context()
        packet = build_staff_validation_packet(context)
        packet_paths = {row.source_path for row in packet.rows}

        for key in context.canonical_instrument_dto:
            self.assertIn(f"canonical_instrument_dto.{key}", packet_paths)

    def test_canonical_lightpath_dto_fields_appear_in_packet(self) -> None:
        context = self._context()
        packet = build_staff_validation_packet(context)
        packet_paths = {row.source_path for row in packet.rows}

        for key in ("sources", "optical_path_elements", "endpoints", "light_paths"):
            self.assertIn(f"canonical_lightpath_dto.{key}", packet_paths)
        self.assertIn("canonical_lightpath_dto.light_paths[0].id", packet_paths)

    def test_missing_hardware_values_are_diagnostics_not_invented_labels(self) -> None:
        packet = build_staff_validation_packet(self._context())
        detector_rows = [row for row in packet.rows if row.source_path == "canonical_instrument_dto.hardware.detectors"]

        self.assertTrue(detector_rows)
        self.assertTrue(detector_rows[0].is_missing)
        self.assertTrue(detector_rows[0].diagnostics)
        detector_values = {str(row.value) for row in detector_rows}
        self.assertNotIn("Manual Observation Only", detector_values)
        self.assertNotIn("External Camera Port Available", detector_values)

    def test_generated_artifacts_include_pdf_json_and_csv(self) -> None:
        module = self._generate_module()
        context = self._context()
        packet = build_staff_validation_packet(context)

        class FakeHTML:
            def __init__(self, *, string, base_url):
                self.string = string
                self.base_url = base_url

            def write_pdf(self, output_path, stylesheets=None):
                Path(output_path).write_bytes(b"%PDF-1.4 fake\n")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pdf_dir = tmp_path / "pdf"
            csv_dir = tmp_path / "csv"
            json_dir = tmp_path / "json"
            pdf_dir.mkdir()
            csv_dir.mkdir()
            json_dir.mkdir()

            with unittest.mock.patch.object(module, "HTML", FakeHTML):
                result = module._write_instrument_artifacts(
                    instrument_id=context.instrument_id,
                    rendered_html="<html><body>audit</body></html>",
                    repo_root=tmp_path,
                    stylesheets=[],
                    pdf_dir=pdf_dir,
                    csv_dir=csv_dir,
                    json_dir=json_dir,
                    build_context=context,
                    staff_validation_packet=packet,
                )

            self.assertTrue(Path(result["pdf_path"]).exists())
            self.assertTrue(Path(result["csv_path"]).exists())
            self.assertTrue(Path(result["json_path"]).exists())

            with Path(result["csv_path"]).open(encoding="utf-8", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertTrue(csv_rows)
            self.assertIn("corrected_value", csv_rows[0])

            traceability = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
            self.assertIn("canonical_instrument_dto", traceability)
            self.assertIn("canonical_lightpath_dto", traceability)
            self.assertIn("staff_validation_packet", traceability)

    def test_output_directory_is_cleaned_before_generation(self) -> None:
        module = self._generate_module()
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "audit_reports"
            stale_file = output_dir / "stale_root_audit.pdf"
            stale_file.parent.mkdir()
            stale_file.write_text("stale", encoding="utf-8")

            pdf_dir, csv_dir, json_dir = module._prepare_output_dirs(output_dir)

            self.assertFalse(stale_file.exists())
            self.assertTrue(pdf_dir.is_dir())
            self.assertTrue(csv_dir.is_dir())
            self.assertTrue(json_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
