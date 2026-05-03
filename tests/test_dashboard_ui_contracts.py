"""Dashboard UI production contract tests.

These tests verify that the dashboard UI correctly implements the canonical
production architecture in user-facing displays:
- Index uses capability chips from capabilities, not modalities
- Active instrument pages have NO "Legacy modalities" section
- Route display uses route_type_label and readouts
- Missing data is visible and diagnostic, not invented
"""

import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from scripts.build_context import normalize_instrument_dto
from scripts.dashboard.instrument_view import build_instrument_mega_dto
from scripts.dashboard.site_render import _annotate_display_labels, _build_vocabulary
from scripts.validate import Vocabulary


REPO_ROOT = Path(__file__).resolve().parents[1]


class DashboardUiContractTests(unittest.TestCase):
    """Tests for dashboard UI production contracts."""

    def _template_env(self) -> Environment:
        templates_dir = REPO_ROOT / "scripts" / "templates"
        return Environment(loader=FileSystemLoader(templates_dir), autoescape=False)

    def test_index_capability_chips_use_axis_qualified_ids(self) -> None:
        """Index page capability filter chips must use axis:term_id format."""
        vocabulary = _build_vocabulary(Path.cwd())
        instruments = [
            {
                "id": "scope1",
                "display_name": "Scope 1",
                "capabilities": {
                    "imaging_modes": ["confocal_point"],
                    "readouts": ["flim"],
                },
                "modalities": ["confocal"],  # legacy should be ignored
                "modules": [],
            }
        ]
        retired = [
            {
                "id": "scope-old",
                "display_name": "Old Scope",
                "capabilities": {"imaging_modes": ["widefield_fluorescence"]},
                "modalities": [],
                "modules": [],
            }
        ]
        _annotate_display_labels(instruments, retired, vocabulary)

        ids = instruments[0]["capabilities_primary_ids"]
        self.assertIn("imaging_modes:confocal_point", ids)
        self.assertIn("readouts:flim", ids)
        # Legacy modalities should NOT be in the chip IDs
        self.assertNotIn("confocal", ids)
        self.assertNotIn("modalities:confocal", ids)
        # Retired instrument should also get annotated correctly
        self.assertIn(
            "imaging_modes:widefield_fluorescence",
            retired[0]["capabilities_primary_ids"],
        )

    def test_index_template_data_capabilities_attribute_is_axis_qualified(self) -> None:
        """Index template must use data-capabilities with axis:term format."""
        tpl = self._template_env().get_template("index.md.j2")
        rendered = tpl.render(
            counts={"total": 1, "green": 1, "yellow": 0, "red": 0},
            instruments=[
                {
                    "id": "scope1",
                    "display_name": "Scope 1",
                    "manufacturer": "Acme",
                    "model": "X",
                    "image_filename": "placeholder.svg",
                    "status": {"color": "green", "badge": "Online"},
                    "capabilities_primary": [{"label": "FLIM"}],
                    "capabilities_primary_ids": ["readouts:flim"],
                }
            ],
            capability_filter_options=[
                {"id": "readouts:flim", "label": "Readout: FLIM"}
            ],
        )

        self.assertIn('data-capabilities="readouts:flim"', rendered)
        self.assertIn("Readout: FLIM", rendered)

    def test_active_instrument_spec_has_no_legacy_modalities_section(self) -> None:
        """Active instrument spec pages must not show 'Legacy modalities' section."""
        vocabulary = Vocabulary(vocab_registry={})

        # Active instrument with capabilities (no legacy modalities)
        active_inst = {
            "id": "scope-active",
            "display_name": "Active Scope",
            "canonical": {
                "instrument": {
                    "instrument_id": "scope-active",
                    "display_name": "Active Scope",
                    "manufacturer": "Acme",
                    "model": "X1",
                },
                "capabilities": {"imaging_modes": ["confocal_point"]},
                "modalities": [],  # should be empty or absent
                "hardware": {},
            },
        }

        dto = build_instrument_mega_dto(vocabulary, active_inst, {"light_paths": []})

        # Should not have legacy_modalities field or it should be empty
        legacy_mods = dto.get("legacy_modalities")
        self.assertFalse(legacy_mods, "Active instrument should not have legacy_modalities")

    def test_route_display_uses_route_type_label_and_readouts(self) -> None:
        """Route display must show route_type_label and readouts, not legacy modality."""
        from scripts.lightpath.parse_canonical import parse_canonical_light_path_model

        instrument = {
            "hardware": {
                "sources": [{"id": "src_488", "kind": "laser"}],
                "endpoints": [{"id": "det1", "endpoint_type": "detector"}],
            },
            "light_paths": [
                {
                    "id": "confocal",
                    "name": "Confocal FLIM",
                    "route_type": "confocal_point",
                    "readouts": ["flim", "fcs"],
                    "illumination_sequence": [{"source_id": "src_488"}],
                    "detection_sequence": [{"endpoint_id": "det1"}],
                }
            ],
        }

        dto = parse_canonical_light_path_model(instrument)

        # The canonical DTO should preserve route_type and readouts
        light_paths = dto.get("light_paths", [])
        self.assertTrue(len(light_paths) > 0)
        route = light_paths[0]

        # Should have route_type
        self.assertEqual(route.get("route_type"), "confocal_point")
        # Should have readouts
        self.assertEqual(route.get("readouts"), ["flim", "fcs"])

    def test_missing_metadata_produces_visible_diagnostic_not_invented_value(self) -> None:
        """Missing metadata should produce visible diagnostics, not invented values."""
        from scripts.dashboard.methods_export import build_methods_generator_instrument_export

        # Instrument with missing canonical data
        inst = {
            "id": "scope-incomplete",
            "display_name": "Incomplete Scope",
            "dto": {},
            "canonical": {},  # missing hardware, software
            "lightpath_dto": {},  # missing light_paths
        }

        export = build_methods_generator_instrument_export(inst)

        # Should have diagnostics for missing data
        diagnostics = export["methods_view_dto"]["diagnostics"]
        self.assertTrue(len(diagnostics) > 0, "Missing data should produce diagnostics")

        # Should have diagnostic codes
        codes = {d.get("code") for d in diagnostics}
        self.assertTrue(
            codes & {"missing_canonical_hardware", "missing_canonical_software", "missing_canonical_routes"},
            "Should diagnose missing canonical data",
        )

    def test_dashboard_does_not_infer_missing_laser_power_or_detector_settings(self) -> None:
        """Dashboard should not infer missing laser power/detector settings."""
        from scripts.dashboard.instrument_view import build_hardware_dto

        vocabulary = Vocabulary(vocab_registry={})

        inst = {
            "canonical": {
                "hardware": {
                    "sources": [
                        {
                            "id": "src_488",
                            "kind": "laser",
                            "wavelength_nm": 488,
                            # intentionally omitting: power, power_max, power_controllable
                        }
                    ],
                }
            }
        }

        hardware_dto = build_hardware_dto(vocabulary, inst, {"light_paths": []})
        source = hardware_dto["light_sources"][0]

        # Source must be present with the fields that were provided
        self.assertEqual(source["id"], "src_488")
        self.assertEqual(source["wavelength_nm"], 488)
        # Fields that were not supplied must remain absent – never silently invented
        self.assertNotIn("power_max", source)
        self.assertNotIn("power", source)
        self.assertNotIn("power_controllable", source)


if __name__ == "__main__":
    unittest.main()
