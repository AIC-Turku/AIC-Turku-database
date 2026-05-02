from __future__ import annotations

import unittest
import warnings
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from scripts.build_context import normalize_instrument_dto
from scripts.dashboard.site_render import _annotate_display_labels, _build_vocabulary


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTRUMENTS_DIR = REPO_ROOT / "instruments"


def _template_env() -> Environment:
    templates_dir = REPO_ROOT / "scripts" / "templates"
    return Environment(loader=FileSystemLoader(templates_dir), autoescape=False)


def _load_optical_routes_vocab() -> set[str]:
    """Return valid optical route IDs from vocab/optical_routes.yaml."""
    import yaml  # type: ignore[import]
    vocab_path = REPO_ROOT / "vocab" / "optical_routes.yaml"
    data = yaml.safe_load(vocab_path.read_text(encoding="utf-8"))
    ids: set[str] = set()
    for term in data.get("terms", []):
        if isinstance(term, dict) and term.get("id"):
            ids.add(term["id"])
    return ids


class CapabilityMigrationTests(unittest.TestCase):

    def test_capability_filter_options_use_axis_ids_and_labels(self) -> None:
        vocabulary = _build_vocabulary(Path.cwd())
        instruments = [{
            "id": "scope1",
            "display_name": "Scope 1",
            "modalities": ["confocal"],
            "capabilities": {"imaging_modes": ["confocal_point"], "readouts": ["flim"]},
            "modules": [],
        }]
        _annotate_display_labels(instruments, [], vocabulary)
        ids = instruments[0]["capabilities_primary_ids"]
        self.assertIn("imaging_modes:confocal_point", ids)
        self.assertIn("readouts:flim", ids)
        self.assertNotIn("confocal", ids)

    def test_index_template_uses_capability_filter_options(self) -> None:
        tpl = _template_env().get_template("index.md.j2")
        rendered = tpl.render(
            counts={"total": 1, "green": 1, "yellow": 0, "red": 0},
            instruments=[{
                "id": "scope1",
                "display_name": "Scope 1",
                "manufacturer": "Acme",
                "model": "X",
                "image_filename": "placeholder.svg",
                "status": {"color": "green", "badge": "Online"},
                "capabilities_primary": [{"label": "Confocal point scanning"}],
                "capabilities_primary_ids": ["imaging_modes:confocal_point"],
            }],
            capability_filter_options=[{"id": "imaging_modes:confocal_point", "label": "Imaging: Confocal point scanning"}],
        )
        self.assertIn("Imaging: Confocal point scanning", rendered)
        self.assertIn('data-capabilities="imaging_modes:confocal_point"', rendered)

    def test_instrument_spec_route_type_and_readouts_are_separate(self) -> None:
        tpl = _template_env().get_template("instrument_spec.md.j2")
        dto = {
            "identity": {"display_name": "Scope", "id": "scope", "image_filename": "placeholder.svg", "manufacturer": "", "model": "", "stand_orientation": {"display_label": ""}, "ocular_availability": {"display_label": ""}, "location": "", "year_of_purchase": "", "funding": ""},
            "status": {"color": "green", "badge": "Online", "reason": "ok"},
            "capabilities": {k: [] for k in ["imaging_modes", "contrast_methods", "readouts", "workflows", "assay_operations", "non_optical"]},
            "modalities": [],
            "modules": [],
            "software": [],
            "hardware": {
                "environment": {"present": False},
                "light_sources": [],
                "scanner": {"present": False},
                "detectors": [],
                "objectives": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "stages": [],
                "hardware_autofocus": {"present": False},
                "triggering": {"present": False},
                "optical_path": {"sections": [], "authoritative_route_contract": {"routes": [{"id": "route1", "display_label": "Confocal route", "illumination_mode": "confocal_point", "route_identity": {"route_type": "confocal_point", "route_type_label": "Confocal point scanning", "readouts": [{"id": "flim", "display_label": "FLIM"}, {"id": "fcs", "display_label": "FCS"}]}}]}},
            },
        }
        rendered = tpl.render(
            instrument={"dto": dto},
            latest_metrics={}, metric_names={}, policy={"missing_required": [], "missing_conditional": [], "alias_fallbacks": []}
        )
        self.assertIn("Route type:", rendered)
        self.assertIn("Confocal point scanning", rendered)
        self.assertIn("FLIM", rendered)
        self.assertIn("FCS", rendered)

    def test_all_active_instruments_have_explicit_capabilities(self) -> None:
        """Every active (non-retired) instrument YAML must have at least one non-empty capabilities axis."""
        import yaml  # type: ignore[import]
        missing: list[str] = []
        for yaml_path in sorted(INSTRUMENTS_DIR.glob("*.yaml")):
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            caps = data.get("capabilities")
            if not isinstance(caps, dict) or not any(
                isinstance(v, list) and v for v in caps.values()
            ):
                missing.append(yaml_path.name)
        self.assertFalse(
            missing,
            f"Active instruments missing non-empty capabilities: {missing}. "
            "Add explicit capabilities.* axes to these YAML files.",
        )

    def test_all_active_instruments_light_path_ids_are_valid_optical_routes(self) -> None:
        """Every light_path id in active instrument YAMLs must be a recognised optical route term."""
        import yaml  # type: ignore[import]
        valid_route_ids = _load_optical_routes_vocab()
        invalid: list[str] = []
        for yaml_path in sorted(INSTRUMENTS_DIR.glob("*.yaml")):
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            light_paths = data.get("light_paths")
            if not isinstance(light_paths, list):
                continue
            for lp in light_paths:
                if not isinstance(lp, dict):
                    continue
                route_id = (lp.get("id") or "").strip()
                if route_id and route_id not in valid_route_ids:
                    invalid.append(f"{yaml_path.name}: light_path id='{route_id}'")
        self.assertFalse(
            invalid,
            "Light path IDs are not recognised optical route vocabulary terms. "
            "Use route types from vocab/optical_routes.yaml; move readout-axis terms "
            "(flim, fcs, spectral_imaging) to light_paths[].readouts:\n"
            + "\n".join(f"  - {item}" for item in invalid),
        )

    def test_normalize_instrument_dto_emits_warning_when_capabilities_absent(self) -> None:
        """normalize_instrument_dto must emit a UserWarning when capabilities are absent
        and the legacy-modalities fallback fires, rather than silently deriving them."""
        payload = {
            "instrument": {"instrument_id": "scope-test-fallback", "display_name": "Test"},
            "modalities": ["confocal_point"],
            # No 'capabilities' key → fallback should fire with a warning
        }
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = normalize_instrument_dto(payload, Path("test_fallback.yaml"), retired=False)
        self.assertIsNotNone(result)
        user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
        self.assertTrue(
            user_warnings,
            "normalize_instrument_dto should emit a UserWarning when capabilities are absent "
            "and the legacy-modalities fallback is used.",
        )
        warning_text = str(user_warnings[0].message)
        self.assertTrue(
            "capabilities" in warning_text.lower() or "legacy" in warning_text.lower(),
            f"Warning message should mention capabilities or legacy fallback; got: {warning_text}",
        )


