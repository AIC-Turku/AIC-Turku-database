"""Regressions for publication issues found by exercising real microscope exports.

These tests deliberately use the production Methods Generator script through the
existing Node DOM harness. They pin review-prompt propagation, software placeholder
handling, FLIM-neutral review guidance, advisory acquisition-setting language, and
defensive runtime position resolution.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _runner():
    path = ROOT / "tests" / "test_methods_generator_template.py"
    spec = importlib.util.spec_from_file_location("methods_real_output_runner", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    cls = module.MethodsGeneratorTemplateTests
    cls.setUpClass()
    return cls(methodName="test_methods_app_does_not_invent_missing_capabilities")


def _instrument(*, runtime=None):
    turret = {
        "id": "turret",
        "display_label": "Filter Turret",
        "inventory_class": "optical_element",
        "publication_label": "Filter Turret",
        "publication_template": "The light path included {label}.",
        "method_sentence": "The light path included Filter Turret.",
        "selectable_positions": [
            # Deliberate collision: this display label equals the next position's id.
            {"id": "Pos_2", "display_label": "Pos_1", "product_code": "BAD"},
            {"id": "Pos_1", "display_label": "GFP cube", "product_code": "49002"},
        ],
    }
    route = {
        "id": "widefield",
        "display_label": "Widefield fluorescence",
        "route_type": "widefield_fluorescence",
        "route_identity": {"readouts": [{"id": "flim", "display_label": "FLIM"}]},
        "relevant_hardware": {
            "sources": [],
            "filters": [turret],
            "splitters": [],
            "endpoints": [],
        },
    }
    return {
        "id": "scope-real-output",
        "display_name": "Real Output Scope",
        "retired": False,
        "software": [
            {"role": "acquisition", "name": "ControlSuite", "version": "unknown"},
        ],
        "methods_generation": {"is_blocked": False, "blockers": []},
        "methods": {
            "base_sentence": "Images were acquired using the Real Output Scope.",
            "specimen_preparation_recommendation": "[PLEASE SPECIFY: specimen preparation].",
            "acquisition_settings_recommendation": (
                "[PLEASE SPECIFY: acquisition software/version (if applicable), exposure "
                "time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, "
                "pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable]."
            ),
            "quarep_light_path_recommendation_needed": False,
            "retired_review_prompt": "",
        },
        "modules": [
            {
                "id": "module-1",
                "display_label": "Environmental module",
                "method_sentence": "The environmental module was used.",
                "review_prompts": ["[PLEASE SPECIFY: environmental module setpoint]"],
            }
        ],
        "modalities": [],
        "capabilities": {"imaging_modes": ["widefield_fluorescence"]},
        "hardware": {
            "scanner": {
                "present": True,
                "id": "scanner-1",
                "display_label": "Test scanner",
                "method_sentence": "The test scanner was used.",
                "review_prompts": ["[PLEASE SPECIFY: scanner setting]"],
            },
            "objectives": [],
            "magnification_changers": [
                {
                    "id": "mag-1",
                    "display_label": "Magnification changer",
                    "method_sentence": "A magnification changer was used.",
                    "review_prompts": ["[PLEASE SPECIFY: magnification changer setting]"],
                }
            ],
            "optical_modulators": [
                {
                    "id": "slm-1",
                    "display_label": "easy3D SLM",
                    "method_sentence": "STED beam shaping used Abberior easy3D SLM.",
                    "review_prompts": ["[PLEASE SPECIFY: which phase mask profile was applied]"],
                }
            ],
            "illumination_logic": [
                {
                    "id": "logic-1",
                    "display_label": "Illumination logic",
                    "method_sentence": "Adaptive illumination control was used.",
                    "review_prompts": ["[PLEASE SPECIFY: adaptive illumination setting]"],
                }
            ],
            "optical_path": {
                "hardware_inventory_renderables": [turret],
                "authoritative_route_contract": {"routes": [route]},
            },
        },
        "runtime_selected_configuration": runtime,
    }


def _run(instrument, actions):
    return _runner().run_template(
        instruments=[instrument],
        actions_js=actions + "\nreturn { output: document.getElementById('output-text').value };",
    )["output"]


def _select_scope():
    return """
      const select = document.getElementById('system-select');
      select.value = 'scope-real-output';
      select.listeners.change({ target: select });
    """


def test_selected_hardware_keeps_review_prompts_and_software_placeholders_out_of_prose():
    output = _run(
        _instrument(),
        _select_scope()
        + """
      ['module', 'scanner', 'magnification-changer', 'optical-modulator', 'illumination-logic', 'confirmed']
        .forEach(prefix => {
          const node = document.querySelectorAll(`input[id^="${prefix}-"]`)[0];
          if (node) node.checked = true;
        });
      document.getElementById('add-btn').listeners.click();
    """,
    )

    prose = output.split("Review before publication:", 1)[0]
    assert "The environmental module was used." in prose
    assert "The test scanner was used." in prose
    assert "A magnification changer was used." in prose
    assert "STED beam shaping used Abberior easy3D SLM." in prose
    assert "Adaptive illumination control was used." in prose
    # Built from the structured software row above, which records the version as
    # "unknown": a placeholder is not a version, so it is asked for rather than
    # printed as "ControlSuite (vunknown)".
    assert "ControlSuite." in prose
    assert "vunknown" not in prose
    assert "[PLEASE SPECIFY" not in prose

    for prompt in (
        "environmental module setpoint",
        "scanner setting",
        "magnification changer setting",
        "which phase mask profile was applied",
        "adaptive illumination setting",
        # Version requests are grouped into one line, so several confirmed products
        # do not each add a near-identical request.
        "the version of ControlSuite",
    ):
        assert prompt in output


def test_flim_prompt_is_domain_neutral_and_replaces_redundant_generic_settings():
    output = _run(
        _instrument(),
        _select_scope()
        + """
      const route = document.querySelectorAll('input[id^="route-"]')[0];
      route.checked = true;
      const readout = document.querySelectorAll('input[id^="readout-"]')[0];
      readout.checked = true;
      document.getElementById('add-btn').listeners.click();
    """,
    )

    assert "whether acquisition was time-domain or frequency-domain" in output
    assert "timing or modulation settings" in output
    assert "signal or photon statistics where applicable" in output
    assert "laser repetition rate, photons collected per pixel" not in output
    assert "any remaining acquisition settings needed to reproduce the experiment" in output
    assert "detector gain/offset" not in output
    assert "zoom/averaging" not in output
    assert "[RECOMMENDED FOR REPORTING:" in output
    assert "light-microscopy community recommends also reporting" in output
    assert "original image metadata" in output
    assert "Recover acquisition settings from image metadata" in output


def test_exposure_and_generic_acquisition_settings_are_advisory_not_mandatory():
    instrument = _instrument()
    route = instrument["hardware"]["optical_path"]["authoritative_route_contract"]["routes"][0]
    route["route_type"] = "confocal_spinning_disk"

    output = _run(
        instrument,
        _select_scope()
        + """
      const route = document.querySelectorAll('input[id^="route-"]')[0];
      route.checked = true;
      document.getElementById('add-btn').listeners.click();
    """,
    )

    assert "[RECOMMENDED FOR REPORTING:" in output
    assert "light-microscopy community recommends also reporting camera exposure per channel" in output
    assert "original image metadata" in output
    assert "Recover acquisition settings from image metadata" in output
    assert "[PLEASE SPECIFY: camera exposure per channel" not in output
    assert "any remaining acquisition settings needed to reproduce the experiment" in output

    generic_output = _run(
        _instrument(),
        _select_scope() + "document.getElementById('add-btn').listeners.click();",
    )
    assert "[RECOMMENDED FOR REPORTING:" in generic_output
    assert "exposure time(s)" in generic_output
    assert "original image metadata" in generic_output
    assert "[PLEASE SPECIFY: acquisition software/version" not in generic_output


def test_runtime_position_key_wins_over_a_colliding_display_label():
    runtime = {
        "scope_id": "scope-real-output",
        "route": "widefield",
        "validSelection": True,
        "selected_route_steps": [
            {
                "kind": "optical_component",
                "component_id": "turret",
                "display_label": "Filter Turret",
                "position_key": "Pos_1",
                "position_label": "GFP cube",
            }
        ],
    }
    output = _run(
        _instrument(runtime=runtime),
        _select_scope()
        + """
      document.getElementById('runtime-confirm').checked = true;
      document.getElementById('add-btn').listeners.click();
    """,
    )

    prose = output.split("Review before publication:", 1)[0]
    assert "GFP cube (catalogue no. 49002) in the Filter Turret" in prose
    assert "catalogue no. BAD" not in prose
    assert "do not describe the same recorded position" not in output


def test_duplicate_position_labels_are_review_only_without_a_stable_key():
    instrument = _instrument()
    turret = instrument["hardware"]["optical_path"]["hardware_inventory_renderables"][0]
    turret["selectable_positions"] = [
        {"id": "A", "display_label": "Duplicate", "product_code": "A1"},
        {"id": "B", "display_label": "Duplicate", "product_code": "B1"},
    ]
    instrument["hardware"]["optical_path"]["authoritative_route_contract"]["routes"][0][
        "relevant_hardware"
    ]["filters"] = [turret]
    instrument["runtime_selected_configuration"] = {
        "scope_id": "scope-real-output",
        "route": "widefield",
        "validSelection": True,
        "selected_route_steps": [
            {
                "kind": "optical_component",
                "component_id": "turret",
                "display_label": "Filter Turret",
                "position_label": "Duplicate",
            }
        ],
    }

    output = _run(
        instrument,
        _select_scope()
        + """
      document.getElementById('runtime-confirm').checked = true;
      document.getElementById('add-btn').listeners.click();
    """,
    )

    prose = output.split("Review before publication:", 1)[0]
    assert "catalogue no. A1" not in prose
    assert "catalogue no. B1" not in prose
    assert "more than one recorded position has that label" in output


def _with_camera(runtime):
    """The instrument above, plus a recorded camera a runtime plan can name."""
    camera = {
        "id": "cam1",
        "display_label": "Test Camera",
        "inventory_class": "endpoint",
        "publication_label": "Test Camera",
        "publication_template": "Images were recorded using {label}.",
        "method_sentence": "Images were recorded using Test Camera.",
    }
    instrument = _instrument(runtime=runtime)
    optical_path = instrument["hardware"]["optical_path"]
    optical_path["hardware_inventory_renderables"].append(camera)
    optical_path["authoritative_route_contract"]["routes"][0]["relevant_hardware"]["endpoints"] = [camera]
    return instrument


def _confirm_runtime_and_add():
    return _select_scope() + """
      document.getElementById('runtime-confirm').checked = true;
      document.getElementById('add-btn').listeners.click();
    """


def test_a_runtime_detector_satisfies_the_detector_the_entry_must_name():
    """A confirmed plan that names the camera has named the camera.

    The completeness check used to read only the tick boxes, so the same draft
    said "Images were recorded using Test Camera" and then asked the author which
    detector had been used.
    """
    output = _run(
        _with_camera({
            "scope_id": "scope-real-output", "route": "widefield", "validSelection": True,
            "detectors": [{"id": "cam1", "display_label": "Test Camera"}],
        }),
        _confirm_runtime_and_add(),
    )

    assert "Images were recorded using Test Camera" in output
    assert "[PLEASE SPECIFY: the detector" not in output


def test_a_runtime_optic_alone_does_not_satisfy_the_illumination():
    """A filter is not a light source.

    Any runtime component used to count as illumination, so a plan naming only a
    filter turret produced a draft that stated no illumination at all and did not
    ask for one.
    """
    output = _run(
        _with_camera({
            "scope_id": "scope-real-output", "route": "widefield", "validSelection": True,
            "selected_route_steps": [{
                "kind": "optical_component", "component_id": "turret",
                "display_label": "Filter Turret", "position_key": "Pos_1",
            }],
        }),
        _confirm_runtime_and_add(),
    )

    assert "[PLEASE SPECIFY: the illumination" in output
