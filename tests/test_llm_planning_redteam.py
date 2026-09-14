import json
import unittest
from pathlib import Path

from scripts.check_llm_planning_response import audit_response_claims
from scripts.dashboard.llm_export import build_llm_inventory_payload


REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = REPO_ROOT / "tests" / "fixtures" / "llm_planning_scenarios.json"
PLAN_TEMPLATE_PATH = REPO_ROOT / "scripts" / "templates" / "plan_experiments.md.j2"


class LlmPlanningRedTeamTests(unittest.TestCase):
    def _payload(self):
        record = {
            "id": "scope-a",
            "display_name": "Scope A",
            "status": {"color": "green", "badge": "Online"},
            "canonical_instrument_dto": {
                "instrument": {
                    "instrument_id": "scope-a",
                    "display_name": "Scope A",
                },
                "hardware": {
                    "objectives": [
                        {
                            "id": "obj-60",
                            "display_label": "60x objective",
                            "is_installed": True,
                        }
                    ],
                    "sources": [
                        {"id": "src-route-a", "display_label": "Source A"},
                        {"id": "src-route-b", "display_label": "Source B"},
                        {"id": "src-generic-only", "display_label": "Generic source"},
                    ],
                    "detectors": [
                        {"id": "det-a", "display_label": "Detector A"},
                        {"id": "det-b", "display_label": "Detector B"},
                    ],
                },
                "capabilities": {
                    "imaging_modes": ["tirf"],
                    "measurement_readouts": ["flim"],
                },
            },
            "canonical_lightpath_dto": {
                "projections": {
                    "llm": {
                        "authoritative_route_contract": {
                            "routes": [
                                {
                                    "id": "route-a",
                                    "display_label": "Route A",
                                    "route_identity": {
                                        "route_type": "tirf",
                                        "route_type_label": "TIRF",
                                        "readouts": [
                                            {"id": "flim", "display_label": "FLIM"}
                                        ],
                                    },
                                    "readouts": [
                                        {"id": "flim", "display_label": "FLIM"}
                                    ],
                                    "route_optical_facts": {
                                        "selected_or_selectable_sources": [
                                            {"id": "src-route-a"}
                                        ],
                                        "selected_or_selectable_excitation_filters": [],
                                        "selected_or_selectable_dichroics": [],
                                        "selected_or_selectable_emission_filters": [],
                                        "selected_or_selectable_splitters": [],
                                        "selected_or_selectable_branch_selectors": [
                                            {
                                                "id": "selector-a",
                                                "selection_state": "selectable",
                                                "available_positions": [
                                                    {"id": "position-1"},
                                                    {"id": "position-2"},
                                                ],
                                            }
                                        ],
                                        "selected_or_selectable_endpoints": [
                                            {"id": "det-a"}
                                        ],
                                        "selected_or_selectable_modulators": [],
                                    },
                                },
                                {
                                    "id": "route-b",
                                    "display_label": "Route B",
                                    "route_identity": {
                                        "route_type": "widefield_fluorescence",
                                        "route_type_label": "Widefield fluorescence",
                                    },
                                    "route_optical_facts": {
                                        "selected_or_selectable_sources": [
                                            {"id": "src-route-b"}
                                        ],
                                        "selected_or_selectable_excitation_filters": [],
                                        "selected_or_selectable_dichroics": [],
                                        "selected_or_selectable_emission_filters": [],
                                        "selected_or_selectable_splitters": [],
                                        "selected_or_selectable_branch_selectors": [],
                                        "selected_or_selectable_endpoints": [
                                            {"id": "det-b"}
                                        ],
                                        "selected_or_selectable_modulators": [],
                                    },
                                },
                            ],
                            "available_routes": [
                                {"id": "route-a", "label": "Route A"},
                                {"id": "route-b", "label": "Route B"},
                            ],
                        }
                    }
                },
                "light_paths": [
                    {"id": "route-a", "selected_execution": {}},
                    {"id": "route-b", "selected_execution": {}},
                ],
            },
            "diagnostics": [],
        }
        return build_llm_inventory_payload({"short_name": "Core"}, [record])

    def test_red_team_scenario_suite_covers_requested_cases_without_preferred_microscope(self):
        payload = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
        scenarios = payload["scenarios"]
        self.assertEqual(
            {scenario["id"] for scenario in scenarios},
            {
                "live_gfp_mcherry_24h",
                "very_fast_two_colour_dynamics",
                "tirf_imaging",
                "flim",
                "deep_3d_imaging",
                "sted",
                "low_phototoxicity_long_timelapse",
                "thick_cleared_sample",
                "three_colour_potentially_incompatible_routes",
                "unsatisfied_request",
            },
        )
        for scenario in scenarios:
            self.assertNotIn("preferred_instrument", scenario)
            expectations = scenario["repository_only_expectations"]
            self.assertIn("definitely_impossible_rule", expectations)
            self.assertIn("components_must_not_be_claimed_rule", expectations)
            self.assertIn("supported_routes_rule", expectations)
            self.assertTrue(expectations["must_remain_unknown"])
            self.assertTrue(expectations["staff_confirmation_when_unrecorded"])

    def test_prompt_forbids_major_hallucination_paths(self):
        source = PLAN_TEMPLATE_PATH.read_text(encoding="utf-8")
        required_phrases = [
            "Never build a route by combining hardware from different routes.",
            "installed objective is not route-compatible",
            "If a selector is unresolved/selectable, do not silently choose",
            "Operational/QC status is not booking or access availability.",
            "classification",
            "missing, null, empty, or unrecorded values as unknown",
            "If the inventory cannot establish a suitable route, say so.",
            "Do not force a best microscope or backup",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, source)
        self.assertNotIn("Choose one best route on the top instrument", source)
        self.assertNotIn("The best-fit microscope and one backup", source)
        self.assertNotIn("Exclude unavailable or incompatible microscopes", source)

    def test_export_separates_route_facts_from_instrument_objectives(self):
        payload = self._payload()
        policy = payload["policy"]
        self.assertEqual(
            policy["claim_scope"]["generic_hardware_scope"],
            "instrument_only_not_route_evidence",
        )
        self.assertEqual(
            policy["claim_scope"]["objective_route_compatibility"],
            "unknown_unless_explicitly_linked_in_authoritative_route_facts",
        )
        microscope = payload["active_microscopes"][0]
        self.assertIn(
            "does not encode booking availability",
            microscope["hardware_focus_summary"]["status_scope_note"],
        )
        planning_routes = microscope["llm_context"]["route_planning_summary"]["routes"]
        route_a = next(route for route in planning_routes if route["route_id"] == "route-a")
        self.assertNotIn("highly_relevant_installed_objectives", route_a["planning_optics"])
        self.assertEqual(
            route_a["instrument_level_context"]["installed_objectives"][0]["id"],
            "obj-60",
        )
        self.assertEqual(
            route_a["claim_boundaries"]["objective_route_compatibility"],
            "unknown_no_route_objective_link",
        )
        self.assertEqual(
            set(route_a["claim_boundaries"]["route_component_ids"]),
            {"src-route-a", "selector-a", "det-a"},
        )
        self.assertTrue(route_a["claim_boundaries"]["selector_resolution_required"])
        self.assertEqual(
            route_a["claim_boundaries"]["booking_or_access_availability"],
            "not_encoded_by_route_or_status",
        )

    def test_response_checker_accepts_ids_from_the_same_authoritative_route(self):
        response = json.dumps(
            {
                "recommendations": [
                    {
                        "instrument_id": "scope-a",
                        "route_id": "route-a",
                        "source_id": "src-route-a",
                        "endpoint_id": "det-a",
                    }
                ]
            }
        )
        report = audit_response_claims(self._payload(), response)
        self.assertEqual(report["violations"], [])

    def test_response_checker_rejects_cross_route_component_mixing(self):
        response = json.dumps(
            {
                "instrument_id": "scope-a",
                "route_id": "route-a",
                "source_id": "src-route-b",
            }
        )
        report = audit_response_claims(self._payload(), response)
        self.assertIn(
            "component_not_on_route",
            {item["code"] for item in report["violations"]},
        )

    def test_response_checker_rejects_generic_hardware_as_route_evidence(self):
        response = json.dumps(
            {
                "instrument_id": "scope-a",
                "route_id": "route-a",
                "source_id": "src-generic-only",
            }
        )
        report = audit_response_claims(self._payload(), response)
        self.assertIn(
            "generic_hardware_not_route_evidence",
            {item["code"] for item in report["violations"]},
        )

    def test_response_checker_keeps_objective_route_compatibility_unknown(self):
        response = json.dumps(
            {
                "instrument_id": "scope-a",
                "route_id": "route-a",
                "objective_id": "obj-60",
            }
        )
        report = audit_response_claims(self._payload(), response)
        self.assertIn(
            "objective_route_compatibility_unproven",
            {item["code"] for item in report["violations"]},
        )

    def test_response_checker_flags_unknown_ids_in_json_and_tagged_text(self):
        json_report = audit_response_claims(
            self._payload(),
            json.dumps({"instrument_id": "scope-does-not-exist"}),
        )
        self.assertIn(
            "unknown_instrument_id",
            {item["code"] for item in json_report["violations"]},
        )

        text_report = audit_response_claims(
            self._payload(),
            "instrument_id: scope-a\nroute_id: route-a\ncomponent_id: invented-component",
        )
        self.assertIn(
            "component_not_on_route",
            {item["code"] for item in text_report["violations"]},
        )

    def test_unsatisfied_scenario_does_not_encode_a_fallback_recommendation(self):
        scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))["scenarios"]
        scenario = next(item for item in scenarios if item["id"] == "unsatisfied_request")
        expectations = scenario["repository_only_expectations"]
        self.assertEqual(
            expectations["required_route_types"],
            ["__intentionally_absent_route_type__"],
        )
        self.assertEqual(
            expectations["required_readouts"],
            ["__intentionally_absent_readout__"],
        )
        self.assertIn("must be empty", expectations["supported_routes_rule"])


if __name__ == "__main__":
    unittest.main()
