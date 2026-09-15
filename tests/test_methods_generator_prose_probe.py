"""Temporary prose probe for the grounded Methods Generator.

This test intentionally fails with exact generated output so the PR workflow log
can be inspected while auditing publication-facing prose. It will be replaced by
stable regression assertions after the wording review.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

from scripts.dashboard.methods_export import build_methods_generator_instrument_export


ROOT = Path(__file__).resolve().parents[1]


def _load_runner():
    path = ROOT / "tests" / "test_methods_generator_template.py"
    spec = importlib.util.spec_from_file_location("methods_template_probe_runner", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    cls = module.MethodsGeneratorTemplateTests
    cls.setUpClass()
    return cls(methodName="test_methods_app_does_not_invent_missing_capabilities")


def _route_fact(label: str, **extra):
    return {"id": label.lower().replace(" ", "_"), "display_label": label, **extra}


def _instrument(*, route_facts=None, runtime=None, blocked=False):
    route_facts = route_facts or {}
    source = {
        "id": "laser488",
        "display_label": "488 nm laser",
        "inventory_class": "light_source",
        "method_sentence": "Excitation used the 488 nm laser.",
    }
    detector_a = {
        "id": "camera-a",
        "display_label": "Camera A",
        "inventory_class": "endpoint",
        "method_sentence": "Images were recorded using Camera A.",
    }
    detector_b = {
        "id": "camera-b",
        "display_label": "Camera B",
        "inventory_class": "endpoint",
        "method_sentence": "Images were recorded using Camera B.",
    }
    objectives = [
        {"id": "obj20", "display_label": "20× NA 0.8", "method_sentence": "A 20× NA 0.8 objective was used."},
        {"id": "obj60", "display_label": "60× oil NA 1.40", "method_sentence": "A 60× oil-immersion NA 1.40 objective was used."},
    ]
    methods = {
        "base_sentence": "Images were acquired using Current Scope, controlled by CurrentControl 9.",
        "specimen_preparation_recommendation": "[PLEASE SPECIFY: specimen preparation and mounting medium].",
        "acquisition_settings_recommendation": "[PLEASE SPECIFY: settings].",
        "nyquist_recommendation": "Acquisition parameters should satisfy Nyquist sampling.",
        "data_deposition_recommendation": "[DATA AVAILABILITY]: deposit raw files.",
        "quarep_light_path_recommendation_needed": False,
        "quarep_light_path_recommendation": "",
    }
    inst = {
        "id": "scope-grounding",
        "display_name": "Current Scope",
        "canonical": {
            "instrument": {"instrument_id": "scope-grounding", "display_name": "Current Scope"},
            "hardware": {"objectives": objectives, "detectors": [detector_a, detector_b], "sources": [source]},
            "software": [{"role": "acquisition", "name": "CurrentControl 9"}],
            "software_status": "documented",
        },
        "lightpath_dto": {
            "light_paths": [{"id": "widefield", "name": "Widefield", "selected_execution": {"selected_route_steps": []}}],
        },
        "methods_generation": {
            "is_blocked": blocked,
            "blockers": ([{"kind": "instrument_metadata", "title": "Acquisition software version"}] if blocked else []),
        },
        "runtime_selected_configuration": copy.deepcopy(runtime),
        "dto": {
            "id": "scope-grounding",
            "display_name": "Current Scope",
            "methods_generation": {
                "is_blocked": blocked,
                "blockers": ([{"kind": "instrument_metadata", "title": "Acquisition software version"}] if blocked else []),
            },
            "methods": copy.deepcopy(methods),
            "hardware": {
                "objectives": copy.deepcopy(objectives),
                "scanner": {"present": False},
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {
                    "hardware_inventory_renderables": [copy.deepcopy(source), copy.deepcopy(detector_a), copy.deepcopy(detector_b)],
                    "authoritative_route_contract": {
                        "routes": [{
                            "id": "widefield",
                            "display_label": "Widefield fluorescence",
                            "illumination_mode": "widefield",
                            "relevant_hardware": {
                                "sources": [copy.deepcopy(source)],
                                "endpoints": [copy.deepcopy(detector_a), copy.deepcopy(detector_b)],
                            },
                            "route_identity": {"readouts": []},
                            "route_optical_facts": copy.deepcopy(route_facts),
                        }]
                    },
                },
            },
            "modalities": [],
            "modules": [],
        },
    }
    return build_methods_generator_instrument_export(inst)


def _run(runner, instrument, actions):
    return runner.run_template(
        instruments=[instrument],
        actions_js=actions + "\nreturn { output: document.getElementById('output-text').value };",
    )["output"]


def test_methods_generator_prose_probe():
    runner = _load_runner()
    outputs = {}

    outputs["simple"] = _run(runner, _instrument(), """
      const select = document.getElementById('system-select');
      select.value = 'scope-grounding';
      select.listeners.change({ target: select });
      document.getElementById('session-label').value = 'Fixed cells';
      document.getElementById('add-btn').listeners.click();
    """)

    outputs["objective_route_source_detector"] = _run(runner, _instrument(), """
      const select = document.getElementById('system-select');
      select.value = 'scope-grounding';
      select.listeners.change({ target: select });
      document.getElementById('session-label').value = 'Two-colour fixed-cell acquisition';
      document.querySelectorAll('input[id^="route-"]')[0].checked = true;
      document.querySelectorAll('input[id^="obj-"]')[1].checked = true;
      document.querySelectorAll('input[id^="light-"]')[0].checked = true;
      document.querySelectorAll('input[id^="det-"]')[0].checked = true;
      document.getElementById('add-btn').listeners.click();
    """)

    outputs["two_detectors"] = _run(runner, _instrument(), """
      const select = document.getElementById('system-select');
      select.value = 'scope-grounding';
      select.listeners.change({ target: select });
      document.querySelectorAll('input[id^="det-"]')[0].checked = true;
      document.querySelectorAll('input[id^="det-"]')[1].checked = true;
      document.getElementById('add-btn').listeners.click();
    """)

    route_facts = {
        "selected_or_selectable_emission_filters": [
            _route_fact("GFP filter cube", selection_state="selected", selected_position_key="GFP", product_code="49002"),
            _route_fact(
                "Filter wheel",
                selection_state="selectable",
                available_positions=[
                    {"position_key": "DAPI", "display_label": "DAPI"},
                    {"position_key": "FITC", "display_label": "FITC"},
                ],
            ),
        ]
    }
    runtime = {
        "scope_id": "scope-grounding",
        "route": "widefield",
        "validSelection": True,
        "sources": [{"id": "laser488", "display_label": "488 nm laser", "selected_wavelength_nm": 488}],
        "selected_route_steps": [
            {"kind": "optical_component", "display_label": "GFP filter cube", "position_key": "GFP"}
        ],
        "detectors": [{"id": "camera-a", "display_label": "Camera A", "collection_min_nm": 500, "collection_max_nm": 550}],
    }
    outputs["confirmed_simulator"] = _run(runner, _instrument(route_facts=route_facts, runtime=runtime), """
      const select = document.getElementById('system-select');
      select.value = 'scope-grounding';
      select.listeners.change({ target: select });
      document.getElementById('runtime-confirm').checked = true;
      document.getElementById('add-btn').listeners.click();
    """)

    uncertain = {
        "selected_or_selectable_dichroics": [
            _route_fact("Dichroic turret", selection_state="unresolved")
        ]
    }
    outputs["uncertain_route"] = _run(runner, _instrument(route_facts=uncertain), """
      const select = document.getElementById('system-select');
      select.value = 'scope-grounding';
      select.listeners.change({ target: select });
      document.querySelectorAll('input[id^="route-"]')[0].checked = true;
      document.getElementById('add-btn').listeners.click();
    """)

    outputs["incomplete_metadata"] = _run(runner, _instrument(blocked=True), """
      const select = document.getElementById('system-select');
      select.value = 'scope-grounding';
      select.listeners.change({ target: select });
      document.getElementById('add-btn').listeners.click();
    """)

    raise AssertionError("\n\n" + "\n\n==========\n\n".join(
        f"### {name}\n{output}" for name, output in outputs.items()
    ))
