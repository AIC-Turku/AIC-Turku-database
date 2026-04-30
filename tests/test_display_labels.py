"""Tests for the centralized display-label resolution in scripts/display_labels.py."""

import unittest
from dataclasses import dataclass
from typing import Any

from scripts.display_labels import (
    _MISSING_MARKER,
    resolve_component_type_label,
    resolve_display_label,
    resolve_endpoint_type_label,
    resolve_inventory_class_label,
    resolve_light_source_kind_label,
    resolve_route_label,
    resolve_stage_role_label,
    resolve_vocab_label,
    resolve_vocab_section_title,
)


@dataclass
class _FakeTerm:
    id: str
    label: str


class _FakeVocab:
    """Minimal vocabulary stub for testing."""

    def __init__(self, terms_by_vocab: dict[str, dict[str, _FakeTerm]]) -> None:
        self.terms_by_vocab = terms_by_vocab


def _vocab_with(**vocabs: dict[str, str]) -> _FakeVocab:
    terms: dict[str, dict[str, _FakeTerm]] = {}
    for vocab_name, mapping in vocabs.items():
        terms[vocab_name] = {
            term_id: _FakeTerm(id=term_id, label=label)
            for term_id, label in mapping.items()
        }
    return _FakeVocab(terms)


class ResolveDisplayLabelTests(unittest.TestCase):
    """Tests for the core resolve_display_label function."""

    def test_explicit_label_takes_priority(self) -> None:
        vocab = _vocab_with(optical_routes={"confocal": "Confocal"})
        result = resolve_display_label(
            "confocal",
            vocab_name="optical_routes",
            vocab=vocab,
            explicit_label="Custom Label",
        )
        self.assertEqual(result, "Custom Label")

    def test_vocab_lookup_used_when_no_explicit_label(self) -> None:
        vocab = _vocab_with(optical_routes={"confocal": "Confocal"})
        result = resolve_display_label("confocal", vocab_name="optical_routes", vocab=vocab)
        self.assertEqual(result, "Confocal")

    def test_missing_vocab_term_returns_raw_with_marker(self) -> None:
        vocab = _vocab_with(optical_routes={"confocal": "Confocal"})
        result = resolve_display_label("unknown_route", vocab_name="optical_routes", vocab=vocab)
        self.assertIn("unknown_route", result)
        self.assertIn(_MISSING_MARKER, result)

    def test_none_raw_value_returns_empty_string(self) -> None:
        result = resolve_display_label(None)
        self.assertEqual(result, "")

    def test_no_vocab_returns_raw_with_marker(self) -> None:
        result = resolve_display_label("some_value", vocab_name="missing_vocab", vocab=None)
        self.assertIn("some_value", result)
        self.assertIn(_MISSING_MARKER, result)


class ResolveVocabLabelTests(unittest.TestCase):
    def test_known_term(self) -> None:
        vocab = _vocab_with(detector_kinds={"pmt": "Photomultiplier Tube"})
        self.assertEqual(resolve_vocab_label(vocab, "detector_kinds", "pmt"), "Photomultiplier Tube")

    def test_unknown_term(self) -> None:
        vocab = _vocab_with(detector_kinds={"pmt": "Photomultiplier Tube"})
        result = resolve_vocab_label(vocab, "detector_kinds", "exotic")
        self.assertIn(_MISSING_MARKER, result)

    def test_empty_value(self) -> None:
        vocab = _vocab_with(detector_kinds={"pmt": "Photomultiplier Tube"})
        self.assertEqual(resolve_vocab_label(vocab, "detector_kinds", ""), "")
        self.assertEqual(resolve_vocab_label(vocab, "detector_kinds", None), "")


class ResolveRouteLabelTests(unittest.TestCase):
    def test_with_vocab(self) -> None:
        vocab = _vocab_with(optical_routes={"tirf": "TIRF"})
        self.assertEqual(resolve_route_label("tirf", vocab=vocab), "TIRF")

    def test_explicit_name_wins(self) -> None:
        vocab = _vocab_with(optical_routes={"tirf": "TIRF"})
        self.assertEqual(resolve_route_label("tirf", vocab=vocab, explicit_name="Custom"), "Custom")


class ResolveComponentTypeLabelTests(unittest.TestCase):
    def test_known_type(self) -> None:
        vocab = _vocab_with(optical_component_types={"bandpass": "Bandpass"})
        self.assertEqual(resolve_component_type_label("bandpass", vocab), "Bandpass")

    def test_missing_type(self) -> None:
        vocab = _vocab_with(optical_component_types={"bandpass": "Bandpass"})
        result = resolve_component_type_label("exotic_filter", vocab)
        self.assertIn(_MISSING_MARKER, result)


class ResolveEndpointTypeLabelTests(unittest.TestCase):
    def test_known_type(self) -> None:
        vocab = _vocab_with(endpoint_types={"camera_port": "Camera port"})
        self.assertEqual(resolve_endpoint_type_label("camera_port", vocab), "Camera port")

    def test_empty(self) -> None:
        self.assertEqual(resolve_endpoint_type_label("", None), "")
        self.assertEqual(resolve_endpoint_type_label(None, None), "")


class ResolveStageRoleLabelTests(unittest.TestCase):
    def test_known_role(self) -> None:
        vocab = _vocab_with(optical_path_stage_roles={"excitation": "Excitation"})
        self.assertEqual(resolve_stage_role_label("excitation", vocab), "Excitation")

    def test_empty(self) -> None:
        self.assertEqual(resolve_stage_role_label(""), "")
        self.assertEqual(resolve_stage_role_label(None), "")


class ResolveLightSourceKindLabelTests(unittest.TestCase):
    def test_known_kind(self) -> None:
        vocab = _vocab_with(light_source_kinds={"laser": "Laser"})
        self.assertEqual(resolve_light_source_kind_label("laser", vocab), "Laser")

    def test_missing_kind(self) -> None:
        vocab = _vocab_with(light_source_kinds={"laser": "Laser"})
        result = resolve_light_source_kind_label("plasma_torch", vocab)
        self.assertIn(_MISSING_MARKER, result)


class ResolveInventoryClassLabelTests(unittest.TestCase):
    def test_static_label(self) -> None:
        self.assertEqual(resolve_inventory_class_label("light_source"), "Light Source")
        self.assertEqual(resolve_inventory_class_label("endpoint"), "Endpoint")
        self.assertEqual(resolve_inventory_class_label("optical_element"), "Optical Element")
        self.assertEqual(resolve_inventory_class_label("splitter"), "Splitter")

    def test_empty(self) -> None:
        self.assertEqual(resolve_inventory_class_label(""), "")
        self.assertEqual(resolve_inventory_class_label(None), "")

    def test_unknown_class(self) -> None:
        result = resolve_inventory_class_label("exotic_class")
        self.assertIn(_MISSING_MARKER, result)


class ResolveVocabSectionTitleTests(unittest.TestCase):
    def test_snake_case_to_title(self) -> None:
        self.assertEqual(resolve_vocab_section_title("optical_component_types"), "Optical Component Types")
        self.assertEqual(resolve_vocab_section_title("detector_kinds"), "Detector Kinds")


class VocabBackedParserIntegrationTests(unittest.TestCase):
    """Verify that the parser uses vocab labels when vocab is provided."""

    def test_available_routes_use_vocab_label(self) -> None:
        from scripts.light_path_parser import generate_virtual_microscope_payload

        vocab = _vocab_with(
            optical_routes={"confocal": "Confocal (vocab)"},
            optical_component_types={"bandpass": "Bandpass"},
            light_source_kinds={"laser": "Laser"},
            light_source_roles={},
            endpoint_types={"camera_port": "Camera port"},
        )
        instrument = {
            "hardware": {
                "sources": [{"id": "src_488", "kind": "laser", "wavelength_nm": 488}],
                "optical_path_elements": [],
                "endpoints": [{"id": "cam_1", "endpoint_type": "camera_port"}],
            },
            "light_paths": [
                {
                    "id": "confocal",
                    "illumination_sequence": [{"source_id": "src_488"}],
                    "detection_sequence": [{"endpoint_id": "cam_1"}],
                }
            ],
        }
        payload = generate_virtual_microscope_payload(instrument, vocab=vocab)
        projections = (payload.get("projections") or {}).get("virtual_microscope") or {}
        routes = projections.get("available_routes", [])
        self.assertTrue(len(routes) >= 1)
        confocal = next((r for r in routes if r["id"] == "confocal"), None)
        self.assertIsNotNone(confocal)
        self.assertEqual(confocal["label"], "Confocal (vocab)")

    def test_no_vocab_uses_route_labels_fallback(self) -> None:
        from scripts.light_path_parser import generate_virtual_microscope_payload

        instrument = {
            "hardware": {
                "sources": [{"id": "src_488", "kind": "laser", "wavelength_nm": 488}],
                "optical_path_elements": [],
                "endpoints": [{"id": "cam_1", "endpoint_type": "camera_port"}],
            },
            "light_paths": [
                {
                    "id": "confocal",
                    "illumination_sequence": [{"source_id": "src_488"}],
                    "detection_sequence": [{"endpoint_id": "cam_1"}],
                }
            ],
        }
        payload = generate_virtual_microscope_payload(instrument, vocab=None)
        projections = (payload.get("projections") or {}).get("virtual_microscope") or {}
        routes = projections.get("available_routes", [])
        confocal = next((r for r in routes if r["id"] == "confocal"), None)
        self.assertIsNotNone(confocal)
        # Without vocab, the route ID is returned directly as the label
        self.assertEqual(confocal["label"], "confocal")


if __name__ == "__main__":
    unittest.main()
