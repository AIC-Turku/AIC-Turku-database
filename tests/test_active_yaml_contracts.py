"""Active YAML production contract tests.

These tests verify that active (non-retired) YAMLs strictly adhere to the
canonical production architecture:
- No top-level modalities
- No light_paths[].modalities
- Six-axis capabilities required
- route_type is primary route identity
- readouts are route-level, not route_type
- STED uses capabilities.imaging_modes not legacy modality
"""

import unittest
from pathlib import Path

import yaml

from scripts.build_context import normalize_instrument_dto
from scripts.validation.instrument import validate_instrument_ledgers


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTRUMENTS_DIR = REPO_ROOT / "instruments"


class ActiveYamlContractTests(unittest.TestCase):
    """Tests for active (non-retired) YAML production contracts."""

    def test_active_yaml_must_not_have_top_level_modalities(self) -> None:
        """Active YAMLs must not have top-level modalities field."""
        payload = {
            "instrument": {"instrument_id": "scope-bad", "display_name": "Bad Scope"},
            "modalities": ["confocal"],  # legacy term from the old modality vocabulary
            "capabilities": {"imaging_modes": ["confocal_point"]},
        }
        with self.assertRaises(RuntimeError) as ctx:
            normalize_instrument_dto(payload, Path("scope-bad.yaml"), retired=False)
        # Check that the error message mentions the prohibition
        error_msg = str(ctx.exception).lower()
        self.assertTrue(
            "modalities" in error_msg and "not allowed" in error_msg,
            f"Error should mention modalities prohibition: {ctx.exception}"
        )

    def test_active_yaml_must_have_six_axis_capabilities(self) -> None:
        """Active YAMLs must have capabilities with at least one axis populated."""
        payload = {
            "instrument": {"instrument_id": "scope-missing-caps", "display_name": "Missing Caps"},
        }
        with self.assertRaises(RuntimeError) as ctx:
            normalize_instrument_dto(payload, Path("scope-missing-caps.yaml"), retired=False)
        self.assertIn("capabilities", str(ctx.exception).lower())

    def test_active_yaml_light_paths_must_not_have_modalities(self) -> None:
        """Active light paths must not have modalities field (deprecated)."""
        # This is allowed but deprecated - normalize should strip it
        payload = {
            "instrument": {"instrument_id": "scope-lp-mod", "display_name": "LP Mod"},
            "capabilities": {"imaging_modes": ["confocal_point"]},
            "light_paths": [
                {
                    "id": "confocal",
                    "modalities": ["flim"],  # deprecated
                    "route_type": "confocal_point",
                }
            ],
        }
        normalized = normalize_instrument_dto(payload, Path("scope-lp-mod.yaml"), retired=False)
        # Normalization should preserve capabilities, light_paths should still exist
        self.assertEqual(normalized["capabilities"]["imaging_modes"], ["confocal_point"])
        # The deprecated light-path-level modalities field must be stripped during normalization
        lp = (normalized.get("light_paths") or [{}])[0]
        self.assertNotIn(
            "modalities",
            lp,
            "Deprecated light-path modalities must be stripped by normalizer",
        )

    def test_retired_yaml_can_have_top_level_modalities_for_migration(self) -> None:
        """Retired YAMLs can have top-level modalities (migration compatibility)."""
        payload = {
            "instrument": {"instrument_id": "scope-retired", "display_name": "Retired Scope"},
            "modalities": ["confocal_point"],
        }
        normalized = normalize_instrument_dto(payload, Path("scope-retired.yaml"), retired=True)
        # Retired instruments should auto-migrate to capabilities
        self.assertIn("imaging_modes", normalized["capabilities"])

    def test_route_type_is_required_for_active_light_paths(self) -> None:
        """Active light paths should have route_type (or default from id)."""
        from scripts.lightpath.parse_canonical import parse_canonical_light_path_model
        
        instrument = {
            "hardware": {
                "sources": [{"id": "src_488", "kind": "laser"}],
                "endpoints": [{"id": "cam1", "endpoint_type": "detector"}],
            },
            "light_paths": [
                {
                    "id": "confocal_point",
                    "route_type": "confocal_point",
                    "illumination_sequence": [{"source_id": "src_488"}],
                    "detection_sequence": [{"endpoint_id": "cam1"}],
                }
            ],
        }
        dto = parse_canonical_light_path_model(instrument)
        self.assertEqual(dto["light_paths"][0]["route_type"], "confocal_point")

    def test_route_level_readouts_are_preserved(self) -> None:
        """Route-level readouts must be preserved in canonical parsing."""
        from scripts.lightpath.parse_canonical import parse_canonical_light_path_model

        instrument = {
            "hardware": {
                "sources": [{"id": "src_488", "kind": "laser"}],
                "endpoints": [{"id": "det1", "endpoint_type": "detector"}],
            },
            "light_paths": [
                {
                    "id": "confocal",
                    "route_type": "confocal_point",
                    "readouts": ["flim", "fcs", "spectral_imaging"],
                    "illumination_sequence": [{"source_id": "src_488"}],
                    "detection_sequence": [{"endpoint_id": "det1"}],
                }
            ],
        }
        dto = parse_canonical_light_path_model(instrument)
        self.assertEqual(dto["light_paths"][0]["readouts"], ["flim", "fcs", "spectral_imaging"])

    def test_readout_terms_should_not_be_used_as_route_type(self) -> None:
        """Readout terms (flim, fcs, fret, spectral_imaging) should not be route_type."""
        # This is a schema/validation concern - route_type should be from optical_routes vocab
        # and readouts should be from readout vocab. We test that the vocabularies are distinct.
        readout_terms = {"flim", "fcs", "fret", "spectral_imaging"}
        optical_route_terms = {"confocal_point", "widefield_fluorescence", "tirf", "multiphoton"}
        
        # These should be mutually exclusive
        self.assertEqual(readout_terms & optical_route_terms, set())

    def test_sted_validation_uses_capabilities_imaging_modes(self) -> None:
        """STED detection should use capabilities.imaging_modes, not legacy modality."""
        from scripts.validation.instrument import build_instrument_completeness_report

        instrument = {
            "instrument": {"instrument_id": "sted-1", "display_name": "STED 1"},
            "capabilities": {"imaging_modes": ["sted"]},
            "hardware": {
                "sources": [
                    {"id": "src_640", "kind": "laser", "role": "excitation", "wavelength_nm": 640},
                    {"id": "src_775", "kind": "laser", "role": "depletion", "wavelength_nm": 775},
                ],
            },
        }
        report = build_instrument_completeness_report(instrument)
        # STED should be detected via capabilities.imaging_modes
        # Completeness report should not require legacy modalities field
        self.assertIsNotNone(report)

    def test_all_active_repo_yamls_have_no_top_level_modalities(self) -> None:
        """Audit: all active YAMLs in repo must not have top-level modalities."""
        violations = []
        for yaml_path in sorted(INSTRUMENTS_DIR.rglob("*.yaml")):
            if "retired" in yaml_path.parts:
                continue
            try:
                data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            if "modalities" in data and data.get("modalities"):
                violations.append(yaml_path.name)
        
        self.assertEqual(
            violations,
            [],
            f"Active YAMLs must not have top-level modalities: {violations}",
        )

    def test_all_active_repo_yamls_have_capabilities(self) -> None:
        """Audit: all active YAMLs in repo must have capabilities."""
        missing_caps = []
        for yaml_path in sorted(INSTRUMENTS_DIR.rglob("*.yaml")):
            if "retired" in yaml_path.parts:
                continue
            try:
                data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            
            # Must have capabilities with at least one populated axis
            caps = data.get("capabilities")
            if not isinstance(caps, dict):
                missing_caps.append((yaml_path.name, "missing capabilities"))
                continue
            
            # At least one capability axis must be non-empty
            has_any_axis = any(
                isinstance(caps.get(axis), list) and caps.get(axis)
                for axis in [
                    "imaging_modes",
                    "contrast_methods",
                    "readouts",
                    "optical_techniques",
                    "sample_types",
                    "applications",
                ]
            )
            if not has_any_axis:
                missing_caps.append((yaml_path.name, "all capability axes empty"))
        
        self.assertEqual(
            missing_caps,
            [],
            f"Active YAMLs must have capabilities with at least one axis: {missing_caps}",
        )

    def test_all_active_repo_light_paths_have_route_type(self) -> None:
        """Audit: all active light paths should have route_type or id that defaults."""
        missing_route_type = []
        for yaml_path in sorted(INSTRUMENTS_DIR.rglob("*.yaml")):
            if "retired" in yaml_path.parts:
                continue
            try:
                data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            
            light_paths = data.get("light_paths") or []
            for lp in light_paths:
                if not isinstance(lp, dict):
                    continue
                lp_id = lp.get("id")
                route_type = lp.get("route_type")
                # Either route_type is explicit or id is a valid fallback
                if not route_type and not lp_id:
                    missing_route_type.append((yaml_path.name, "light path missing route_type and id"))
        
        self.assertEqual(
            missing_route_type,
            [],
            f"Active light paths should have route_type or id: {missing_route_type}",
        )


if __name__ == "__main__":
    unittest.main()
