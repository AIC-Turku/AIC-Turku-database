from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from scripts.dashboard.site_render import _annotate_display_labels, _build_vocabulary


def _template_env() -> Environment:
    templates_dir = Path(__file__).resolve().parents[1] / "scripts" / "templates"
    return Environment(loader=FileSystemLoader(templates_dir), autoescape=False)


def test_capability_filter_options_use_axis_ids_and_labels() -> None:
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
    assert "imaging_modes:confocal_point" in ids
    assert "readouts:flim" in ids
    assert "confocal" not in ids


def test_index_template_uses_capability_filter_options() -> None:
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
    assert "Imaging: Confocal point scanning" in rendered
    assert 'data-capabilities="imaging_modes:confocal_point"' in rendered


def test_instrument_spec_route_type_and_readouts_are_separate() -> None:
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
    assert "Route type:" in rendered
    assert "Confocal point scanning" in rendered
    assert "FLIM" in rendered and "FCS" in rendered
