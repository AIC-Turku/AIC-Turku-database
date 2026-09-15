"""Adversarial regression matrix for Methods Generator claim grounding.

These tests exercise the publication-facing export boundary.  The browser-level
Methods tests separately cover selection carry-over, repeated acquisitions and
simulator confirmation; this matrix pins the evidence rules that prevent planning
or inventory metadata from becoming acquisition claims.
"""
from __future__ import annotations

import copy
import json
import unittest

from scripts.dashboard.methods_export import build_methods_generator_instrument_export


def _route_fact(label: str, **extra):
    return {"id": label.lower().replace(" ", "_"), "display_label": label, **extra}


def _instrument(*, route_facts=None, objectives=None, detectors=None, software=None, dto_methods=None):
    route_facts = route_facts or {}
    objectives = objectives or []
    detectors = detectors or []
    software = software if software is not None else [{"role": "acquisition", "name": "CurrentControl 9"}]
    dto_methods = dto_methods or {
        "base_sentence": "Images were acquired using Current Scope, controlled by CurrentControl 9.",
        "specimen_preparation_recommendation": "[PLEASE SPECIFY: specimen preparation].",
        "acquisition_settings_recommendation": "[PLEASE SPECIFY: settings].",
        "nyquist_recommendation": "Acquisition parameters should satisfy Nyquist sampling.",
        "data_deposition_recommendation": "[DATA AVAILABILITY]: deposit raw files.",
        "quarep_light_path_recommendation_needed": False,
        "quarep_light_path_recommendation": "",
    }
    return {
        "id": "scope-grounding",
        "display_name": "Current Scope",
        "canonical": {
            "instrument": {"instrument_id": "scope-grounding", "display_name": "Current Scope"},
            "hardware": {"objectives": objectives, "detectors": detectors, "sources": []},
            "software": software,
            "software_status": "documented" if software else "unknown",
        },
        "lightpath_dto": {
            "light_paths": [{"id": "widefield", "name": "Widefield", "selected_execution": {"selected_route_steps": []}}],
        },
        "dto": {
            "id": "scope-grounding",
            "display_name": "Current Scope",
            "methods": copy.deepcopy(dto_methods),
            "hardware": {
                "objectives": copy.deepcopy(objectives),
                "optical_path": {
                    "authoritative_route_contract": {
                        "routes": [{"id": "widefield", "display_label": "Widefield", "route_optical_facts": copy.deepcopy(route_facts)}]
                    },
                    "hardware_inventory_renderables": [],
                },
            },
        },
    }


class MethodsGeneratorGroundingAudit(unittest.TestCase):
    """Golden claim-boundary tests corresponding to the adversarial audit matrix."""

    def test_simple_fixed_cell_export_is_concise_and_keeps_missing_settings_explicit(self):
        out = build_methods_generator_instrument_export(_instrument())
        methods = out["methods"]
        self.assertEqual(methods["base_sentence"], "Images were acquired using the Current Scope.")
        self.assertIn("[PLEASE SPECIFY:", methods["acquisition_settings_recommendation"])
        self.assertIn("exposure time(s)", methods["acquisition_settings_recommendation"])
        self.assertIn("pixel size (µm/px)", methods["acquisition_settings_recommendation"])
        self.assertIn("z-step (µm)", methods["acquisition_settings_recommendation"])
        self.assertEqual(methods["nyquist_recommendation"], "")
        self.assertEqual(methods["data_deposition_recommendation"], "")

    def test_repeated_exports_are_deterministic_and_do_not_mutate_input(self):
        inst = _instrument()
        original = copy.deepcopy(inst)
        first = build_methods_generator_instrument_export(inst)
        second = build_methods_generator_instrument_export(inst)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(inst, original)

    def test_two_objectives_remain_available_choices_not_automatic_claims(self):
        objectives = [
            {"id": "obj20", "display_label": "20×", "method_sentence": "A 20× objective was used."},
            {"id": "obj63", "display_label": "63×", "method_sentence": "A 63× objective was used."},
        ]
        out = build_methods_generator_instrument_export(_instrument(objectives=objectives))
        self.assertEqual([row["id"] for row in out["methods_view_dto"]["objectives"]], ["obj20", "obj63"])
        self.assertNotIn("20×", out["methods"]["base_sentence"])
        self.assertNotIn("63×", out["methods"]["base_sentence"])

    def test_multiple_detectors_remain_choices_not_automatic_claims(self):
        detectors = [
            {"id": "cam_a", "display_label": "Camera A", "method_sentence": "Camera A was used."},
            {"id": "cam_b", "display_label": "Camera B", "method_sentence": "Camera B was used."},
        ]
        out = build_methods_generator_instrument_export(_instrument(detectors=detectors))
        self.assertEqual([row["id"] for row in out["methods_view_dto"]["detectors"]], ["cam_a", "cam_b"])
        self.assertNotIn("Camera A", out["methods"]["base_sentence"])
        self.assertNotIn("Camera B", out["methods"]["base_sentence"])

    def test_incomplete_instrument_metadata_does_not_gain_authoritative_fallbacks(self):
        inst = _instrument(software=[])
        inst["canonical"]["hardware"] = {}
        out = build_methods_generator_instrument_export(inst)
        codes = {row["code"] for row in out["methods_view_dto"]["diagnostics"]}
        self.assertIn("missing_canonical_hardware", codes)
        self.assertIn("missing_canonical_software", codes)
        self.assertNotIn("CurrentControl", out["methods"]["base_sentence"])

    def test_missing_user_settings_keep_placeholder_and_units(self):
        out = build_methods_generator_instrument_export(_instrument())
        placeholder = out["methods"]["acquisition_settings_recommendation"]
        for token in ("Exposure time", "excitation power", "gain/offset", "binning", "µm/px", "z-step (µm)", "time interval"):
            self.assertIn(token.lower(), placeholder.lower())

    def test_simulator_route_alternatives_are_not_promoted_to_selected_facts(self):
        facts = {
            "selected_or_selectable_emission_filters": [
                _route_fact(
                    "Filter wheel",
                    selection_state="selectable",
                    available_positions=[
                        {"position_key": "1", "display_label": "DAPI"},
                        {"position_key": "2", "display_label": "FITC"},
                    ],
                )
            ]
        }
        out = build_methods_generator_instrument_export(_instrument(route_facts=facts))
        rows = out["hardware"]["optical_path"]["authoritative_route_contract"]["routes"][0]["route_optical_facts"]["selected_or_selectable_emission_filters"]
        self.assertEqual(rows, [])
        self.assertTrue(out["methods"]["quarep_light_path_recommendation_needed"])
        self.assertIn("were not selected", out["methods"]["quarep_light_path_recommendation"])

    def test_historical_acquisition_cannot_inherit_current_software_as_fact(self):
        # Acquisition dates are user/session data handled by the browser. The
        # export therefore must not bake current software into its automatic
        # microscope sentence, where it could be paired with any historical date.
        out = build_methods_generator_instrument_export(_instrument())
        self.assertNotIn("CurrentControl 9", out["methods"]["base_sentence"])
        self.assertIn("software/version", out["methods"]["acquisition_settings_recommendation"])

    def test_multiple_acquisitions_share_no_mutable_export_state(self):
        first = build_methods_generator_instrument_export(_instrument(objectives=[{"id": "obj20", "display_label": "20×"}]))
        second = build_methods_generator_instrument_export(_instrument(objectives=[{"id": "obj63", "display_label": "63×"}]))
        self.assertEqual([row["id"] for row in first["methods_view_dto"]["objectives"]], ["obj20"])
        self.assertEqual([row["id"] for row in second["methods_view_dto"]["objectives"]], ["obj63"])

    def test_optional_hardware_present_but_unselected_is_not_a_route_fact(self):
        facts = {
            "selected_or_selectable_splitters": [
                _route_fact("Optional splitter", selection_state="selectable")
            ]
        }
        out = build_methods_generator_instrument_export(_instrument(route_facts=facts))
        route_facts = out["hardware"]["optical_path"]["authoritative_route_contract"]["routes"][0]["route_optical_facts"]
        self.assertEqual(route_facts["selected_or_selectable_splitters"], [])
        self.assertNotIn("Optional splitter", out["methods"]["base_sentence"])

    def test_uncertain_route_information_is_not_silently_resolved(self):
        facts = {
            "selected_or_selectable_dichroics": [
                _route_fact("Unknown dichroic", selection_state="unresolved")
            ]
        }
        out = build_methods_generator_instrument_export(_instrument(route_facts=facts))
        route_facts = out["hardware"]["optical_path"]["authoritative_route_contract"]["routes"][0]["route_optical_facts"]
        self.assertEqual(route_facts["selected_or_selectable_dichroics"], [])
        self.assertIn("[PLEASE VERIFY:", out["methods"]["quarep_light_path_recommendation"])

    def test_explicitly_selected_route_fact_is_preserved(self):
        facts = {
            "selected_or_selectable_emission_filters": [
                _route_fact(
                    "GFP cube",
                    selection_state="selected",
                    selected_position_key="2",
                    product_code="49002",
                )
            ]
        }
        out = build_methods_generator_instrument_export(_instrument(route_facts=facts))
        rows = out["hardware"]["optical_path"]["authoritative_route_contract"]["routes"][0]["route_optical_facts"]["selected_or_selectable_emission_filters"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["product_code"], "49002")


if __name__ == "__main__":
    unittest.main()
