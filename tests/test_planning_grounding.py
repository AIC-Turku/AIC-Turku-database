"""Grounding guarantees for the AI experiment-planning workflow.

The generated inventory is meant to be an easy-to-read factual handoff that a
user can attach to an LLM conversation. These tests therefore protect two things
at once: factual grounding and restraint. A fixture must never smuggle microscopy
advice into the inventory by translating vague user goals into preferred
modalities.
"""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

import pytest
import yaml

from scripts.dashboard.llm_export import (
    CLOSED_WORLD_FIELDS,
    _build_capability_route_reconciliation,
    _status_with_evidence,
    build_llm_inventory_payload,
)
from scripts.planning_eval import check_response, load_context


REPO_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = REPO_ROOT / "dashboard_docs" / "assets" / "llm_inventory.json"
SCENARIO_PATH = Path(__file__).resolve().parent / "fixtures" / "planning_scenarios.yaml"
RESPONSE_DIR = Path(__file__).resolve().parent / "fixtures" / "planning_responses"


@pytest.fixture(scope="module", autouse=True)
def _generated_inventory() -> None:
    subprocess.run(
        [sys.executable, "-m", "scripts.dashboard_builder", "--strict"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )


def _inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def _scenarios() -> dict:
    return yaml.safe_load(SCENARIO_PATH.read_text(encoding="utf-8"))


def _records(inventory: dict) -> dict[str, dict]:
    return {record["id"]: record for record in inventory["active_microscopes"]}


def _route_contract(record: dict) -> dict:
    return record["llm_context"]["authoritative_route_contract"]


def _declared_modes(record: dict) -> set[str]:
    return set((record.get("capabilities") or {}).get("imaging_modes") or [])


def _declared_readouts(record: dict) -> set[str]:
    return {
        readout.get("id") if isinstance(readout, dict) else readout
        for route in (_route_contract(record).get("routes") or [])
        for readout in ((route.get("route_identity") or {}).get("readouts") or [])
    }


def _paths_containing(payload, needle: str, *, skip_keys: frozenset[str] = frozenset()) -> list[str]:
    hits: list[str] = []

    def walk(value, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in skip_keys:
                    continue
                child_path = f"{path}.{key}" if path else str(key)
                if needle in str(key).lower():
                    hits.append(child_path)
                walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
        elif isinstance(value, str) and needle in value.lower():
            hits.append(path)

    walk(payload, "")
    return hits


def _resolve_path(payload, dotted: str):
    values = [payload]
    for part in dotted.split("."):
        key, _, suffix = part.partition("[")
        next_values = []
        for value in values:
            if isinstance(value, dict) and key in value:
                next_values.append(value[key])
        if suffix:
            expanded = []
            for value in next_values:
                if isinstance(value, list):
                    expanded.extend(value)
            next_values = expanded
        values = next_values
        if not values:
            return []
    return values


class PlanningContractTests(unittest.TestCase):
    def test_planning_contract_is_present_and_versioned(self) -> None:
        contract = _inventory()["planning_contract"]
        self.assertEqual(contract["contract_version"], "planning_contract.v1")
        for section in (
            "closed_world_fields",
            "availability",
            "status_semantics",
            "objective_scope",
            "capability_vs_route",
        ):
            self.assertIn(section, contract)

    def test_closed_world_paths_exist_in_every_record(self) -> None:
        inventory = _inventory()
        for record in inventory["active_microscopes"]:
            for dotted in CLOSED_WORLD_FIELDS:
                with self.subTest(instrument=record["id"], path=dotted):
                    self.assertTrue(
                        _resolve_path(record, dotted),
                        f"{dotted} is declared complete but is absent",
                    )

    def test_export_states_availability_is_not_recorded(self) -> None:
        availability = _inventory()["planning_contract"]["availability"]
        self.assertIs(availability["records_booking_availability"], False)

    def test_inventory_does_not_sneak_in_booking_or_training_data(self) -> None:
        inventory = _inventory()
        prose = frozenset({"planning_contract", "policy"})
        for term in ("bookable", "booking_url", "access_policy", "training_required"):
            with self.subTest(term=term):
                self.assertEqual(_paths_containing(inventory, term, skip_keys=prose), [])


class StatusEvidenceTests(unittest.TestCase):
    def test_status_carries_its_evidence(self) -> None:
        allowed = {
            "qc_and_maintenance_record",
            "qc_record_only",
            "maintenance_record_only",
            "no_qc_or_maintenance_record",
        }
        for record in _inventory()["active_microscopes"]:
            with self.subTest(instrument=record["id"]):
                self.assertIn(record["hardware_focus_summary"]["status"]["evidence"], allowed)

    def test_absent_records_are_not_described_as_a_passed_check(self) -> None:
        status = _status_with_evidence(
            {
                "color": "green",
                "badge": "Online",
                "reason": "Operational",
                "last_qc_date": "",
                "last_maint_date": "",
            }
        )
        self.assertEqual(status["evidence"], "no_qc_or_maintenance_record")
        self.assertIn("not a passed check", status["evidence_note"])

    def test_fleet_contains_evidence_free_statuses(self) -> None:
        evidence_free = [
            record["id"]
            for record in _inventory()["active_microscopes"]
            if record["hardware_focus_summary"]["status"]["evidence"]
            == "no_qc_or_maintenance_record"
        ]
        self.assertTrue(
            evidence_free,
            "The status guard became vacuous because every instrument now has QC/maintenance evidence.",
        )


class ScreeningSummaryTests(unittest.TestCase):
    def test_light_source_labels_are_unique_per_instrument(self) -> None:
        for record in _inventory()["active_microscopes"]:
            labels = record["hardware_focus_summary"]["light_source_labels"]
            with self.subTest(instrument=record["id"]):
                self.assertEqual(
                    len(labels),
                    len(set(labels)),
                    f"duplicate screening labels hide distinct sources: {labels}",
                )

    def test_screening_summary_carries_traceable_ids(self) -> None:
        for record in _inventory()["active_microscopes"]:
            summary = record["hardware_focus_summary"]
            known = {row["id"] for row in _route_contract(record).get("hardware_inventory") or []}
            with self.subTest(instrument=record["id"]):
                self.assertIn("route_ids", summary)
                for entry in summary["light_sources"] + summary["detectors"]:
                    self.assertIn(entry["id"], known)

    def test_every_screening_label_has_a_traceable_id(self) -> None:
        """A label without an id is what makes a reader invent one.

        The id lists were previously allowed to be empty while the label lists
        stayed full, and the check above passed vacuously by iterating nothing.
        Comparing the counts is what makes it bite.
        """
        for record in _inventory()["active_microscopes"]:
            summary = record["hardware_focus_summary"]
            for labels_key, ids_key in (
                ("light_source_labels", "light_sources"),
                ("detector_labels", "detectors"),
            ):
                with self.subTest(instrument=record["id"], field=ids_key):
                    self.assertEqual(
                        len(summary[ids_key]),
                        len(summary[labels_key]),
                        f"{ids_key} has {len(summary[ids_key])} entries but "
                        f"{labels_key} has {len(summary[labels_key])}: "
                        "labels without ids invite invented ids",
                    )

    def test_the_fleet_actually_has_screening_ids_to_check(self) -> None:
        """Guard against the comparison above passing on two empty lists."""
        totals = {"light_sources": 0, "detectors": 0}
        for record in _inventory()["active_microscopes"]:
            for key in totals:
                totals[key] += len(record["hardware_focus_summary"][key])
        for key, total in totals.items():
            with self.subTest(field=key):
                self.assertGreater(total, 0, f"no {key} entries anywhere in the fleet")

    def test_screening_summary_says_it_is_not_route_bound(self) -> None:
        for record in _inventory()["active_microscopes"]:
            with self.subTest(instrument=record["id"]):
                self.assertIn(
                    "not bound to a route",
                    record["hardware_focus_summary"]["screening_scope_note"],
                )


class ClaimBoundaryTests(unittest.TestCase):
    """Route limits must be readable as values, not only as prose."""

    def _routes(self):
        for record in _inventory()["active_microscopes"]:
            summary = record["llm_context"]["route_planning_summary"]
            for route in summary.get("routes") or []:
                yield record["id"], summary, route

    def test_summary_version_moves_with_its_shape(self) -> None:
        for _, summary, _ in self._routes():
            self.assertEqual(summary["contract_version"], "route_planning_summary.v2")

    def test_every_route_publishes_claim_boundaries(self) -> None:
        for instrument_id, _, route in self._routes():
            with self.subTest(instrument=instrument_id, route=route["route_id"]):
                boundaries = route["claim_boundaries"]
                self.assertIn("route_component_ids", boundaries)
                self.assertTrue(boundaries["must_not_combine_with_other_routes"])
                self.assertEqual(
                    boundaries["booking_or_access_availability"],
                    "not_encoded_by_route_or_status",
                )

    def test_component_lists_match_the_authoritative_contract(self) -> None:
        for record in _inventory()["active_microscopes"]:
            usage = {
                row["route_id"]: sorted(set(row.get("hardware_inventory_ids") or []))
                for row in _route_contract(record).get("route_hardware_usage") or []
            }
            for route in record["llm_context"]["route_planning_summary"].get("routes") or []:
                with self.subTest(instrument=record["id"], route=route["route_id"]):
                    self.assertEqual(
                        route["claim_boundaries"]["route_component_ids"],
                        usage.get(route["route_id"], []),
                    )

    def test_component_lists_are_not_uniformly_empty(self) -> None:
        """An empty list reads as "this route has no components".

        Deriving it from route_optical_facts, which is empty for every route in
        this export, would publish exactly that everywhere.
        """
        populated = [
            route
            for _, _, route in self._routes()
            if route["claim_boundaries"]["route_component_ids"]
        ]
        self.assertGreater(len(populated), 1)

    def test_objective_route_compatibility_is_derived_not_asserted(self) -> None:
        for instrument_id, _, route in self._routes():
            boundaries = route["claim_boundaries"]
            expected = (
                "explicit_route_links_present"
                if boundaries["explicit_route_objective_ids"]
                else "unknown_no_route_objective_link"
            )
            with self.subTest(instrument=instrument_id, route=route["route_id"]):
                self.assertEqual(boundaries["objective_route_compatibility"], expected)

    def test_selector_resolution_flag_matches_the_route_state(self) -> None:
        for instrument_id, _, route in self._routes():
            with self.subTest(instrument=instrument_id, route=route["route_id"]):
                self.assertEqual(
                    route["claim_boundaries"]["selector_resolution_required"],
                    route["known_vs_unknown"]["has_unresolved_selectors"],
                )


class ObjectiveScopeTests(unittest.TestCase):
    def test_old_route_relevance_name_is_gone(self) -> None:
        self.assertEqual(
            _paths_containing(_inventory(), "highly_relevant_installed_objectives"), []
        )

    def test_route_planning_summary_is_v2(self) -> None:
        for record in _inventory()["active_microscopes"]:
            summary = record["llm_context"]["route_planning_summary"]
            if summary.get("status") == "blocked":
                continue
            with self.subTest(instrument=record["id"]):
                self.assertEqual(summary["contract_version"], "route_planning_summary.v2")

    def test_objectives_are_separate_from_route_optics(self) -> None:
        for record in _inventory()["active_microscopes"]:
            summary = record["llm_context"]["route_planning_summary"]
            for route in summary.get("routes") or []:
                with self.subTest(instrument=record["id"], route=route["route_id"]):
                    optics = route["planning_optics"]
                    self.assertNotIn("instrument_installed_objectives", optics)
                    self.assertNotIn("objective_scope_note", optics)
                    context = route["instrument_level_context"]
                    self.assertIn("installed_objectives", context)
                    self.assertIn("not on this route", context["objective_scope_note"])


class CapabilityRouteReconciliationTests(unittest.TestCase):
    def test_route_family_coverage_matches_vocabulary(self) -> None:
        authored = {
            term["id"]: sorted((term.get("covers") or {}).get("imaging_modes") or [])
            for term in yaml.safe_load(
                (REPO_ROOT / "vocab" / "optical_routes.yaml").read_text(encoding="utf-8")
            )["terms"]
        }
        exported = {
            route_id: entry["covers_imaging_modes"]
            for route_id, entry in _inventory()["route_family_coverage"].items()
        }
        self.assertEqual(exported, authored)

    def test_reconciliation_is_consistent_for_every_instrument(self) -> None:
        inventory = _inventory()
        coverage = inventory["route_family_coverage"]
        for record in inventory["active_microscopes"]:
            reconciliation = record["capability_route_reconciliation"]
            covered = {
                mode
                for route_type in reconciliation["recorded_route_types"]
                for mode in (coverage.get(route_type) or {}).get("covers_imaging_modes", [])
            }
            with self.subTest(instrument=record["id"]):
                self.assertEqual(
                    set(reconciliation["modes_covered_by_a_recorded_route"]),
                    _declared_modes(record) & covered,
                )
                self.assertEqual(
                    set(reconciliation["modes_without_a_covering_recorded_route"]),
                    _declared_modes(record) - covered,
                )

    def test_tirf_and_sted_use_authored_family_mapping(self) -> None:
        route_terms = set(_inventory()["route_family_coverage"])
        for mode, family in (("tirf", "widefield_fluorescence"), ("sted", "confocal_point")):
            with self.subTest(mode=mode):
                self.assertNotIn(mode, route_terms)
                self.assertIn(
                    mode,
                    _inventory()["route_family_coverage"][family]["covers_imaging_modes"],
                )

    def test_reconciliation_reports_uncovered_mode(self) -> None:
        reconciliation = _build_capability_route_reconciliation(
            {"imaging_modes": ["confocal_point", "multiphoton"]},
            ["confocal_point"],
            {"confocal_point": {"covers_imaging_modes": ["confocal_point", "sted"]}},
        )
        self.assertEqual(reconciliation["modes_without_a_covering_recorded_route"], ["multiphoton"])


class PayloadContractTests(unittest.TestCase):
    def test_coverage_map_is_optional_for_builder(self) -> None:
        payload = build_llm_inventory_payload({"short_name": "Example"}, [])
        self.assertEqual(payload["route_family_coverage"], {})
        self.assertIn("planning_contract", payload)


class GeneratedPromptTests(unittest.TestCase):
    def _prompt(self) -> str:
        page = (REPO_ROOT / "dashboard_docs" / "plan_experiments.md").read_text(encoding="utf-8")
        top = re.search(r"const basePromptTop = `(.*?)`;", page, re.S)
        bottom = re.search(r"const basePromptBottom = `(.*?)`;", page, re.S)
        self.assertIsNotNone(top)
        self.assertIsNotNone(bottom)
        return top.group(1) + bottom.group(1)

    def test_prompt_stays_short_enough_to_read(self) -> None:
        """A prompt nobody reads is a prompt nobody checks.

        Every safeguard here is a sentence a researcher has to paste and skim.
        Without a budget the rule list grows on each audit until it is scrolled
        past.
        """
        words = len(self._prompt().split())
        self.assertLess(words, 380, f"planning prompt has grown to {words} words")

    def test_prompt_does_not_restate_the_instructions_it_removed(self) -> None:
        """Negating a bad instruction still puts it in front of the reader."""
        prompt = self._prompt()
        for removed in (
            "Eliminate unavailable or incompatible instruments first",
            "Choose one best route on the top instrument and one backup route/instrument",
            "legacy instruction",
        ):
            with self.subTest(removed=removed):
                self.assertNotIn(removed, prompt)

    def test_prompt_does_not_force_best_or_backup(self) -> None:
        prompt = self._prompt().lower()
        self.assertNotIn("the best-fit microscope and one backup", prompt)
        self.assertNotIn("choose one best route on the top instrument and one backup route/instrument", prompt)
        self.assertNotIn("legacy instruction", prompt)
        self.assertIn("do not force a best microscope or backup", prompt)

    def test_prompt_does_not_claim_availability(self) -> None:
        prompt = self._prompt().lower()
        self.assertIn("records no booking, access or training availability", prompt)
        self.assertNotIn("eliminate unavailable", prompt)

    def test_prompt_preserves_closed_world_route_membership(self) -> None:
        prompt = self._prompt().lower()
        self.assertIn("component missing from a complete route hardware list is not on that route", prompt)
        self.assertIn("other missing or null values are unknown", prompt)

    def test_prompt_points_at_capability_reconciliation(self) -> None:
        prompt = self._prompt()
        self.assertIn("capability_route_reconciliation", prompt)
        self.assertIn("route_family_coverage", prompt)

    def test_prompt_warns_against_unrecorded_performance_inference(self) -> None:
        prompt = self._prompt().lower()
        for term in ("speed", "depth", "phototoxicity", "sample compatibility"):
            with self.subTest(term=term):
                self.assertIn(term, prompt)

    def test_prompt_invites_one_clarifying_question(self) -> None:
        """Asking beats guessing, and the prompt should not leave it to chance.

        In the simulated planning runs the answers that asked a single question
        about the sample were consistently more useful, but nothing in the
        prompt requested it, so it happened only when the model volunteered.
        The invitation is capped at one question: a prompt that invites a
        questionnaire gets a questionnaire.
        """
        prompt = self._prompt().lower()
        self.assertIn("clarifying question", prompt)
        self.assertIn("one clarifying question", prompt)

    def test_prompt_does_not_ask_for_a_question_list(self) -> None:
        prompt = self._prompt().lower()
        for plural in ("clarifying questions", "any questions you have"):
            with self.subTest(phrase=plural):
                self.assertNotIn(plural, prompt)

    def test_prompt_remains_compact(self) -> None:
        self.assertLess(len(self._prompt().split()), 450)


def test_scenario_fixture_has_exact_red_team_cases() -> None:
    scenarios = _scenarios()["scenarios"]
    assert len(scenarios) == 10
    assert len({scenario["id"] for scenario in scenarios}) == 10
    for scenario in scenarios:
        assert scenario["request"].strip(), scenario["id"]
        assert scenario["expect"]["staff_confirmation_required"] is True, scenario["id"]


def test_scenario_requirements_use_controlled_terms() -> None:
    modes = {
        term["id"]
        for term in yaml.safe_load(
            (REPO_ROOT / "vocab" / "imaging_modes.yaml").read_text(encoding="utf-8")
        )["terms"]
    }
    readouts = {
        term["id"]
        for term in yaml.safe_load(
            (REPO_ROOT / "vocab" / "measurement_readouts.yaml").read_text(encoding="utf-8")
        )["terms"]
    }
    for scenario in _scenarios()["scenarios"]:
        requires = scenario.get("requires") or {}
        for mode in requires.get("imaging_modes") or []:
            assert mode in modes, f"{scenario['id']}: unknown imaging mode {mode}"
        for readout in requires.get("readouts") or []:
            assert readout in readouts, f"{scenario['id']}: unknown readout {readout}"


def test_only_explicit_modality_requests_encode_controlled_requirements() -> None:
    scenarios = {scenario["id"]: scenario for scenario in _scenarios()["scenarios"]}
    for scenario_id in (
        "live_two_colour_24h",
        "fast_two_colour_dynamics",
        "deep_3d_imaging",
        "low_phototoxicity_timelapse",
        "thick_cleared_sample",
        "three_colour_route_conflict",
    ):
        assert not (scenarios[scenario_id].get("requires") or {}), scenario_id

    assert scenarios["tirf_adhesions"]["requires"]["imaging_modes"] == ["tirf"]
    assert scenarios["sted_super_resolution"]["requires"]["imaging_modes"] == ["sted"]
    assert scenarios["flim_lifetime"]["requires"]["readouts"] == ["flim"]
    assert scenarios["unsatisfiable_multiphoton_request"]["requires"]["imaging_modes"] == ["multiphoton"]


def test_explicit_scenario_candidate_sets_match_ledger() -> None:
    records = _records(_inventory())
    for scenario in _scenarios()["scenarios"]:
        requires = scenario.get("requires") or {}
        needed_modes = set(requires.get("imaging_modes") or [])
        needed_readouts = set(requires.get("readouts") or [])
        if not needed_modes and not needed_readouts:
            assert scenario["expect"]["instruments_declaring_requirements"] == []
            continue

        actual = sorted(
            instrument_id
            for instrument_id, record in records.items()
            if needed_modes <= _declared_modes(record)
            and needed_readouts <= _declared_readouts(record)
        )
        assert actual == sorted(scenario["expect"]["instruments_declaring_requirements"]), (
            f"{scenario['id']}: fixture says {scenario['expect']['instruments_declaring_requirements']} "
            f"but ledger says {actual}"
        )


def test_covering_route_families_match_authored_vocabulary() -> None:
    coverage = _inventory()["route_family_coverage"]
    for scenario in _scenarios()["scenarios"]:
        needed = set((scenario.get("requires") or {}).get("imaging_modes") or [])
        if not needed:
            assert scenario["expect"]["covering_route_families"] == []
            continue
        actual = sorted(
            route_id
            for route_id, entry in coverage.items()
            if needed & set(entry["covers_imaging_modes"])
        )
        assert actual == sorted(scenario["expect"]["covering_route_families"]), scenario["id"]


def test_absent_route_types_really_are_absent() -> None:
    route_terms = set(_inventory()["route_family_coverage"])
    for scenario in _scenarios()["scenarios"]:
        for term in scenario["expect"].get("route_types_absent_from_vocabulary") or []:
            assert term not in route_terms, f"{scenario['id']}: {term} is now a route family"


def test_cross_route_traps_are_real() -> None:
    records = _records(_inventory())
    for scenario in _scenarios()["scenarios"]:
        for trap in scenario["expect"].get("cross_route_traps") or []:
            contract = _route_contract(records[trap["instrument"]])
            owned = {row["id"] for row in contract["hardware_inventory"]}
            on_route = {
                usage["route_id"]: set(usage["hardware_inventory_ids"])
                for usage in contract["route_hardware_usage"]
            }
            assert trap["component"] in owned, scenario["id"]
            assert trap["component"] not in on_route[trap["not_on_route"]], scenario["id"]


def test_exclusive_branch_expectations_are_real() -> None:
    records = _records(_inventory())
    for scenario in _scenarios()["scenarios"]:
        for entry in scenario["expect"].get("exclusive_branch_blocks") or []:
            usages = {
                usage["route_id"]: usage
                for usage in _route_contract(records[entry["instrument"]])["route_hardware_usage"]
            }
            blocks = usages[entry["route"]].get("branch_blocks") or []
            assert any(
                block.get("selection_mode") == "exclusive" and len(block.get("branches") or []) > 1
                for block in blocks
            ), scenario["id"]


def test_unsatisfied_explicit_request_has_no_candidate() -> None:
    scenario = next(
        row for row in _scenarios()["scenarios"] if row["id"] == "unsatisfiable_multiphoton_request"
    )
    assert scenario["expect"]["instruments_declaring_requirements"] == []


def test_never_recorded_facts_stay_absent() -> None:
    inventory = _inventory()
    prose = frozenset({"planning_contract", "policy"})
    for fact in _scenarios()["never_recorded"]:
        assert _paths_containing(inventory, fact, skip_keys=prose) == []


class GroundingHarnessTests(unittest.TestCase):
    def _check(self, name: str) -> list:
        context = load_context(_inventory())
        return check_response((RESPONSE_DIR / name).read_text(encoding="utf-8"), context)

    def test_grounded_answer_has_no_findings(self) -> None:
        self.assertEqual([finding.render() for finding in self._check("grounded_answer.md")], [])

    def test_hallucinated_answer_is_caught(self) -> None:
        codes = {finding.code for finding in self._check("hallucinated_answer.md")}
        self.assertTrue(
            {
                "unknown_instrument_id",
                "unknown_component_id",
                "component_not_on_route",
                "exclusive_branch_used_simultaneously",
                "availability_claim",
            }
            <= codes
        )

    def test_untagged_invented_instrument_id_is_caught(self) -> None:
        context = load_context(_inventory())
        findings = check_response(
            "I would use scope-invented-super-microscope for this experiment.",
            context,
        )
        self.assertIn("unknown_instrument_id", {finding.code for finding in findings})

    def test_availability_caveat_is_not_flagged(self) -> None:
        context = load_context(_inventory())
        for line in (
            "The inventory records no booking availability.",
            "Whether the microscope can be booked is not recorded; confirm with staff.",
            "Access and training requirements are unknown.",
        ):
            with self.subTest(line=line):
                codes = {finding.code for finding in check_response(line, context)}
                self.assertNotIn("availability_claim", codes)

    def test_cli_is_offline(self) -> None:
        source = (REPO_ROOT / "scripts" / "planning_eval.py").read_text(encoding="utf-8")
        for forbidden in ("requests", "urllib", "httpx", "openai", "anthropic", "api_key"):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, source)

    def test_cli_returns_nonzero_for_planted_defects(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.planning_eval",
                "--inventory",
                str(INVENTORY_PATH),
                "--response",
                str(RESPONSE_DIR / "hallucinated_answer.md"),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown_instrument_id", result.stdout)

    def test_cli_returns_zero_for_grounded_answer(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.planning_eval",
                "--inventory",
                str(INVENTORY_PATH),
                "--response",
                str(RESPONSE_DIR / "grounded_answer.md"),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout)


class FalseAbsenceTests(unittest.TestCase):
    """A fabricated absence sends a researcher away from recorded capability.

    It is the one hallucination class that reads as caution, and every
    identifier-based check in the evaluator passes it, because such a sentence
    names nothing that does not exist. The terms below are taken from the
    generated inventory rather than written into the test, so the suite fails
    with the data instead of drifting from it.
    """

    def setUp(self) -> None:
        self.context = load_context(_inventory())
        self.recorded = sorted(
            term
            for term, owners in self.context.recorded_terms.items()
            if owners and " " in term and len(term) >= 8
        )
        self.assertTrue(self.recorded, "no multi-word capability terms were indexed")

    def _codes(self, text: str) -> set[str]:
        return {finding.code for finding in check_response(text, self.context)}

    def test_capability_terms_are_indexed_from_the_inventory(self) -> None:
        declared = {
            value
            for record in _inventory()["active_microscopes"]
            for values in record["capabilities"].values()
            if isinstance(values, list)
            for value in values
            if isinstance(value, str)
        }
        self.assertTrue(declared)
        missing = sorted(
            value for value in declared if value.replace("_", " ") not in self.context.recorded_terms
        )
        self.assertEqual(missing, [], "declared capabilities missing from the absence index")

    def test_fleet_wide_denial_of_a_recorded_capability_is_caught(self) -> None:
        for term in self.recorded[:5]:
            for sentence in (
                f"{term.capitalize()} is recorded for none of the active instruments.",
                f"No instrument records {term}.",
                f"{term.capitalize()} is not recorded for any microscope here.",
                f"None of the instruments records {term}.",
            ):
                with self.subTest(sentence=sentence):
                    self.assertIn("false_absence_claim", self._codes(sentence))

    def test_a_denial_split_by_a_line_wrap_is_still_caught(self) -> None:
        term = self.recorded[0]
        wrapped = f"{term.capitalize()} is recorded for\nnone of the active instruments."
        self.assertIn("false_absence_claim", self._codes(wrapped))

    def test_a_truthful_absence_is_not_flagged(self) -> None:
        absent = "plate handling and unattended run duration"
        self.assertNotIn(absent, self.context.recorded_terms)
        self.assertNotIn(
            "false_absence_claim",
            self._codes(f"{absent.capitalize()} is recorded for no instrument."),
        )

    def test_an_unrelated_capability_later_in_the_sentence_is_not_the_subject(self) -> None:
        """The denial is about what precedes it, not everything in the line.

        This is the shape that produced the first false positive: a sentence
        denying one unrecorded thing while correctly naming a recorded
        capability alongside it.
        """
        term = self.recorded[0]
        sentence = (
            "Plate handling is recorded for no instrument, and "
            f'"{term}" here is a capability label, not a description of hardware.'
        )
        self.assertNotIn("false_absence_claim", self._codes(sentence))

    def test_denial_scoped_to_one_instrument_uses_that_instrument(self) -> None:
        term = next(
            term
            for term in self.recorded
            if 0 < len(self.context.recorded_terms[term]) < len(self.context.instrument_ids)
        )
        recorders = self.context.recorded_terms[term]
        owner = sorted(recorders)[0]
        other = sorted(self.context.instrument_ids - recorders)[0]

        with self.subTest(case="records it"):
            self.assertIn(
                "false_absence_claim",
                self._codes(f"For {owner}, {term} is not recorded for any route."),
            )
        with self.subTest(case="genuinely does not"):
            self.assertNotIn(
                "false_absence_claim",
                self._codes(f"For {other}, {term} is not recorded for any route."),
            )

    def test_a_term_inside_an_instrument_id_is_not_read_as_the_subject(self) -> None:
        """Instrument ids embed capability words, and a substring match inverts
        the sentence being checked.

        `scope-zeiss-tirf` contains `tirf`, so a scoped denial of something else
        entirely was reported as a denial of TIRF on the very instrument that
        records it.
        """
        embedded = [
            (instrument_id, term)
            for instrument_id in self.context.instrument_ids
            for term in self.context.recorded_terms
            if " " not in term and term in instrument_id and term != instrument_id
        ]
        self.assertTrue(embedded, "no instrument id embeds a capability term")
        for instrument_id, term in embedded:
            sentence = f"For {instrument_id}, plate handling is not recorded for any route."
            with self.subTest(instrument=instrument_id, term=term):
                self.assertNotIn("false_absence_claim", self._codes(sentence))

    def test_one_finding_per_denial_not_one_per_overlapping_term(self) -> None:
        term = next((t for t in self.recorded if " " in t), self.recorded[0])
        findings = [
            finding
            for finding in check_response(f"No instrument records {term}.", self.context)
            if finding.code == "false_absence_claim"
        ]
        self.assertEqual(len(findings), 1)
