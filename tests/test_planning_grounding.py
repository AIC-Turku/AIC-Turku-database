"""Grounding guarantees for the AI experiment-planning workflow.

The planning page hands `llm_inventory.json` and a generated prompt to an
assistant nobody here controls. These tests pin the parts of that handoff the
repository is responsible for:

- the export states what it does and does not establish, so a planner does not
  have to fill the gaps by assumption;
- the scenario suite in `tests/fixtures/planning_scenarios.yaml` stays consistent
  with the ledger, so it cannot encode a stale recommendation;
- `scripts/planning_eval.py` catches ungrounded claims in a saved answer.

Every expectation is recomputed from repository data. Nothing here asserts which
microscope is right for an experiment.
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
    """`llm_inventory.json` is generated, so build it before asserting against it."""
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
    """JSON paths whose key or string value contains `needle`.

    Returning paths rather than asserting against `json.dumps(...)` keeps a
    failure message readable: an `assertNotIn` against a megabyte of JSON makes
    pytest render the whole document.
    """
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
    """Walk a `a.b[].c` path, returning every value it reaches."""
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


# --------------------------------------------------------------------------
# Export structure
# --------------------------------------------------------------------------


class PlanningContractTests(unittest.TestCase):
    """The export says what it does and does not establish."""

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
        """A path the contract calls complete must actually be there to read."""
        inventory = _inventory()
        for record in inventory["active_microscopes"]:
            for dotted in CLOSED_WORLD_FIELDS:
                with self.subTest(instrument=record["id"], path=dotted):
                    self.assertTrue(
                        _resolve_path(record, dotted),
                        f"{dotted} is declared a complete enumeration but is absent",
                    )

    def test_export_states_that_availability_is_not_recorded(self) -> None:
        availability = _inventory()["planning_contract"]["availability"]
        self.assertIs(availability["records_booking_availability"], False)

    def test_export_carries_no_booking_or_training_data(self) -> None:
        """The contract's claim has to stay true of the payload.

        `planning_contract` and `policy` are the statements *about* the absence,
        so they are allowed to name it; everything else is data.
        """
        inventory = _inventory()
        prose = frozenset({"planning_contract", "policy"})
        for term in ("bookable", "booking_url", "access_policy", "training_required"):
            with self.subTest(term=term):
                self.assertEqual(_paths_containing(inventory, term, skip_keys=prose), [])


class StatusEvidenceTests(unittest.TestCase):
    """A green status derived from silence must say so."""

    def test_status_carries_its_evidence(self) -> None:
        for record in _inventory()["active_microscopes"]:
            status = record["hardware_focus_summary"]["status"]
            with self.subTest(instrument=record["id"]):
                self.assertIn(
                    status["evidence"],
                    {
                        "qc_and_maintenance_record",
                        "qc_record_only",
                        "maintenance_record_only",
                        "no_qc_or_maintenance_record",
                    },
                )

    def test_absent_records_are_reported_as_absent_not_as_a_passed_check(self) -> None:
        status = _status_with_evidence(
            {"color": "green", "badge": "Online", "reason": "Operational",
             "last_qc_date": "", "last_maint_date": ""}
        )
        self.assertEqual(status["evidence"], "no_qc_or_maintenance_record")
        self.assertIn("not a passed check", status["evidence_note"])

    def test_recorded_events_are_distinguished_from_silence(self) -> None:
        for dates, expected in (
            (("2024-01-01", "2024-02-02"), "qc_and_maintenance_record"),
            (("2024-01-01", ""), "qc_record_only"),
            (("", "2024-02-02"), "maintenance_record_only"),
        ):
            with self.subTest(dates=dates):
                status = _status_with_evidence(
                    {"color": "green", "last_qc_date": dates[0], "last_maint_date": dates[1]}
                )
                self.assertEqual(status["evidence"], expected)

    def test_the_fleet_actually_contains_evidence_free_statuses(self) -> None:
        """Guard against the check passing because the case no longer occurs."""
        evidence_free = [
            record["id"]
            for record in _inventory()["active_microscopes"]
            if record["hardware_focus_summary"]["status"]["evidence"]
            == "no_qc_or_maintenance_record"
        ]
        self.assertTrue(
            evidence_free,
            "No instrument reports a status without evidence; if the ledger now has "
            "QC or maintenance for every instrument, this guard can be relaxed.",
        )


class ScreeningSummaryTests(unittest.TestCase):
    """The screening surface must not collapse distinct components."""

    def test_light_source_labels_are_unique_per_instrument(self) -> None:
        """Four LaserStack v4 lasers at different wavelengths are four components."""
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
            known = {
                row["id"]
                for row in _route_contract(record).get("hardware_inventory") or []
            }
            with self.subTest(instrument=record["id"]):
                self.assertIn("route_ids", summary)
                for entry in summary["light_sources"] + summary["detectors"]:
                    self.assertIn(entry["id"], known)

    def test_screening_summary_says_it_is_not_route_bound(self) -> None:
        for record in _inventory()["active_microscopes"]:
            with self.subTest(instrument=record["id"]):
                self.assertIn(
                    "not bound to a route",
                    record["hardware_focus_summary"]["screening_scope_note"],
                )


class ObjectiveScopeTests(unittest.TestCase):
    """Objectives are per instrument; the export must not imply per route."""

    def test_route_objectives_are_not_labelled_highly_relevant(self) -> None:
        """The old key name asserted a route relevance the records do not carry."""
        self.assertEqual(
            _paths_containing(_inventory(), "highly_relevant_installed_objectives"), []
        )

    def test_every_route_declares_the_objective_scope(self) -> None:
        for record in _inventory()["active_microscopes"]:
            summary = record["llm_context"]["route_planning_summary"]
            for route in summary.get("routes") or []:
                with self.subTest(instrument=record["id"], route=route["route_id"]):
                    optics = route["planning_optics"]
                    self.assertIn("instrument_installed_objectives", optics)
                    self.assertIn("per instrument, not per route", optics["objective_scope_note"])


class CapabilityRouteReconciliationTests(unittest.TestCase):
    """Capability and route are different authored axes; relate them, don't guess."""

    def test_route_family_coverage_matches_the_vocabulary(self) -> None:
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

    def test_reconciliation_is_present_and_consistent_for_every_instrument(self) -> None:
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

    def test_capabilities_without_a_route_family_term_are_reconciled_not_dropped(self) -> None:
        """TIRF and STED have no route term; the coverage map is what relates them."""
        route_terms = set(_inventory()["route_family_coverage"])
        for mode, family in (("tirf", "widefield_fluorescence"), ("sted", "confocal_point")):
            with self.subTest(mode=mode):
                self.assertNotIn(mode, route_terms)
                self.assertIn(
                    mode,
                    _inventory()["route_family_coverage"][family]["covers_imaging_modes"],
                )

    def test_reconciliation_reports_an_uncovered_mode(self) -> None:
        reconciliation = _build_capability_route_reconciliation(
            {"imaging_modes": ["confocal_point", "multiphoton"]},
            ["confocal_point"],
            {"confocal_point": {"covers_imaging_modes": ["confocal_point", "sted"]}},
        )
        self.assertEqual(
            reconciliation["modes_without_a_covering_recorded_route"], ["multiphoton"]
        )
        self.assertIn("ask facility staff", reconciliation["note"])


class PayloadContractTests(unittest.TestCase):
    """The payload builder keeps working without a coverage map."""

    def test_coverage_is_optional(self) -> None:
        payload = build_llm_inventory_payload({"short_name": "Example"}, [])
        self.assertEqual(payload["route_family_coverage"], {})
        self.assertIn("planning_contract", payload)


# --------------------------------------------------------------------------
# Generated prompt
# --------------------------------------------------------------------------


class GeneratedPromptTests(unittest.TestCase):
    """The prompt must not ask for judgements the inventory cannot ground."""

    def _prompt(self) -> str:
        page = (REPO_ROOT / "dashboard_docs" / "plan_experiments.md").read_text(encoding="utf-8")
        top = re.search(r"const basePromptTop = `(.*?)`;", page, re.S)
        bottom = re.search(r"const basePromptBottom = `(.*?)`;", page, re.S)
        self.assertIsNotNone(top)
        self.assertIsNotNone(bottom)
        return top.group(1) + bottom.group(1)

    def test_prompt_does_not_ask_the_model_to_judge_availability(self) -> None:
        """Nothing in the export records whether an instrument can be booked."""
        prompt = self._prompt().lower()
        self.assertNotIn("eliminate unavailable", prompt)
        self.assertNotIn("exclude unavailable", prompt)

    def test_prompt_states_that_availability_is_not_recorded(self) -> None:
        prompt = self._prompt().lower()
        self.assertIn("no booking, access or training availability", prompt)

    def test_prompt_distinguishes_closed_world_from_unknown(self) -> None:
        prompt = self._prompt().lower()
        self.assertIn("not on that route", prompt)
        self.assertIn("anywhere else is unknown", prompt)

    def test_prompt_points_at_the_capability_reconciliation(self) -> None:
        prompt = self._prompt()
        self.assertIn("capability_route_reconciliation", prompt)
        self.assertIn("route_family_coverage", prompt)
        self.assertIn("planning_contract", prompt)

    def test_prompt_stays_short_enough_to_read(self) -> None:
        """A prompt a user will not read is a prompt they will not check."""
        self.assertLess(len(self._prompt().split()), 500)


# --------------------------------------------------------------------------
# Scenario suite
# --------------------------------------------------------------------------


def test_scenario_fixture_covers_the_named_planning_situations() -> None:
    scenarios = _scenarios()["scenarios"]
    assert len(scenarios) >= 10
    assert len({scenario["id"] for scenario in scenarios}) == len(scenarios)
    for scenario in scenarios:
        assert scenario["request"].strip(), scenario["id"]
        assert scenario["expect"]["staff_confirmation_required"] is True, scenario["id"]
        assert scenario["expect"]["confirmation_reason"].strip(), scenario["id"]


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
            assert mode in modes, f"{scenario['id']}: {mode} is not a controlled imaging mode"
        for readout in requires.get("readouts") or []:
            assert readout in readouts, f"{scenario['id']}: {readout} is not a controlled readout"


def test_scenario_instrument_expectations_match_the_ledger() -> None:
    """Recompute each scenario's candidate set; a stale fixture fails here."""
    records = _records(_inventory())
    for scenario in _scenarios()["scenarios"]:
        requires = scenario.get("requires") or {}
        needed_modes = set(requires.get("imaging_modes") or [])
        needed_readouts = set(requires.get("readouts") or [])

        actual = sorted(
            instrument_id
            for instrument_id, record in records.items()
            if needed_modes <= _declared_modes(record)
            and needed_readouts <= _declared_readouts(record)
        )
        assert actual == sorted(scenario["expect"]["instruments_declaring_requirements"]), (
            f"{scenario['id']}: fixture lists "
            f"{scenario['expect']['instruments_declaring_requirements']} but the ledger says {actual}"
        )


def test_scenario_covering_route_families_match_the_vocabulary() -> None:
    coverage = _inventory()["route_family_coverage"]
    for scenario in _scenarios()["scenarios"]:
        needed = set((scenario.get("requires") or {}).get("imaging_modes") or [])
        if not needed:
            continue
        actual = sorted(
            route_id
            for route_id, entry in coverage.items()
            if needed & set(entry["covers_imaging_modes"])
        )
        assert actual == sorted(scenario["expect"]["covering_route_families"]), (
            f"{scenario['id']}: covering families drifted to {actual}"
        )


def test_scenario_absent_route_types_really_are_absent() -> None:
    route_terms = set(_inventory()["route_family_coverage"])
    for scenario in _scenarios()["scenarios"]:
        for term in scenario["expect"].get("route_types_absent_from_vocabulary") or []:
            assert term not in route_terms, (
                f"{scenario['id']}: '{term}' is now a route family; the scenario needs updating"
            )


def test_scenario_cross_route_traps_are_real() -> None:
    """Each trap must be a component on the instrument but off the named route."""
    records = _records(_inventory())
    for scenario in _scenarios()["scenarios"]:
        for trap in scenario["expect"].get("cross_route_traps") or []:
            record = records[trap["instrument"]]
            contract = _route_contract(record)
            owned = {row["id"] for row in contract["hardware_inventory"]}
            on_route = {
                usage["route_id"]: set(usage["hardware_inventory_ids"])
                for usage in contract["route_hardware_usage"]
            }
            assert trap["component"] in owned, f"{scenario['id']}: {trap['component']} not recorded"
            assert trap["not_on_route"] in on_route, f"{scenario['id']}: unknown route"
            assert trap["component"] not in on_route[trap["not_on_route"]], (
                f"{scenario['id']}: {trap['component']} IS on {trap['not_on_route']}; "
                "the trap is no longer valid"
            )


def test_scenario_exclusive_branches_are_still_exclusive() -> None:
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
            ), f"{scenario['id']}: {entry['instrument']}/{entry['route']} is no longer exclusive"


def test_unsatisfiable_scenarios_have_no_candidate_instrument() -> None:
    """The suite must contain a request the recorded inventory cannot meet."""
    scenarios = _scenarios()["scenarios"]
    unsatisfiable = [
        scenario
        for scenario in scenarios
        if not scenario["expect"]["instruments_declaring_requirements"]
    ]
    assert unsatisfiable, "no scenario exercises an unsatisfiable request"


def test_never_recorded_facts_are_absent_from_the_export() -> None:
    """Facts the scenarios rely on being unrecorded must stay unrecorded.

    `planning_contract` and `policy` are skipped: they are the export's own
    statement that these facts are absent, so naming them there is the point.
    """
    inventory = _inventory()
    prose = frozenset({"planning_contract", "policy"})
    for fact in _scenarios()["never_recorded"]:
        hits = _paths_containing(inventory, fact, skip_keys=prose)
        assert hits == [], f"{fact} is now exported at {hits[:3]}; update the scenario suite"


# --------------------------------------------------------------------------
# Offline grounding harness
# --------------------------------------------------------------------------


class GroundingHarnessTests(unittest.TestCase):
    """`scripts/planning_eval.py` must catch planted defects and nothing else."""

    def _check(self, name: str) -> list:
        context = load_context(_inventory())
        return check_response((RESPONSE_DIR / name).read_text(encoding="utf-8"), context)

    def test_a_grounded_answer_produces_no_findings(self) -> None:
        findings = self._check("grounded_answer.md")
        self.assertEqual([finding.render() for finding in findings], [])

    def test_a_hallucinated_answer_is_caught(self) -> None:
        codes = {finding.code for finding in self._check("hallucinated_answer.md")}
        self.assertEqual(
            codes,
            {
                "unknown_instrument_id",
                "unknown_component_id",
                "component_not_on_route",
                "exclusive_branch_used_simultaneously",
                "availability_claim",
            },
        )

    def test_stating_that_availability_is_unrecorded_is_not_a_finding(self) -> None:
        """The prompt asks for this caveat; flagging it would train it away."""
        context = load_context(_inventory())
        for line in (
            "The inventory records no booking availability for either instrument.",
            "Whether the microscope can be booked is not recorded; confirm with staff.",
            "Access and training requirements are unknown.",
        ):
            with self.subTest(line=line):
                codes = {finding.code for finding in check_response(line, context)}
                self.assertNotIn("availability_claim", codes)

    def test_an_availability_claim_containing_a_negation_is_still_caught(self) -> None:
        context = load_context(_inventory())
        findings = check_response(
            "The system is currently available and no training is required.", context
        )
        self.assertIn("availability_claim", {finding.code for finding in findings})

    def test_component_claimed_for_the_wrong_instrument_is_caught(self) -> None:
        context = load_context(_inventory())
        findings = check_response(
            "Use scope-zeiss-tirf with source:laserstack_v4_2 for the 488 nm line.",
            context,
        )
        self.assertIn(
            "component_not_on_named_instrument", {finding.code for finding in findings}
        )

    def test_harness_reads_only_local_files(self) -> None:
        """CI has no API key; the harness must never need one."""
        source = (REPO_ROOT / "scripts" / "planning_eval.py").read_text(encoding="utf-8")
        for forbidden in ("requests", "urllib", "httpx", "openai", "anthropic", "api_key"):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, source)

    def test_cli_reports_findings_and_exits_nonzero(self) -> None:
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

    def test_cli_exits_zero_on_a_grounded_answer(self) -> None:
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
