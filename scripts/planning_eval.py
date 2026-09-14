"""Check a saved planning answer against the authoritative inventory.

The experiment-planning page hands `llm_inventory.json` and a prompt to an
assistant of the user's choosing. Nothing in this repository sees the answer, so
nothing catches an assistant that names an instrument the facility does not own,
attaches a laser to a route it is not on, or reports an instrument as available.

This harness closes that loop offline. Save an answer to a file, run it against
the generated inventory, and it reports every identifier the answer claims that
the authoritative context does not support.

    PYTHONPATH=. python -m scripts.planning_eval \\
        --inventory dashboard_docs/assets/llm_inventory.json \\
        --response saved_answer.md

It calls no model and no network: it reads a file you already have. That keeps it
usable in CI, where there is no API key and no budget for one.

What it checks:

- instrument IDs and display names that are not in the inventory;
- component IDs that are not recorded for the instrument they are attributed to;
- components attached to a route they are not recorded on (cross-route mixing);
- availability, booking or training claims, which the inventory never records;
- status claims that repeat "operational" for an instrument whose status rests on
  no QC or maintenance record at all.

What it cannot check: whether the microscopy advice is any good. It answers one
question only — is every identifier in this answer traceable to the inventory.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


# Identifier shapes the inventory uses. Instrument IDs are authored slugs;
# component IDs are the `class:hardware_id` form the route contract builds.
INSTRUMENT_ID_PATTERN = re.compile(r"\bscope-[a-z0-9]+(?:-[a-z0-9]+)*\b")
COMPONENT_ID_PATTERN = re.compile(
    r"\b(?:source|optical_path_element|endpoint|detector|objective):"
    r"[A-Za-z0-9_][A-Za-z0-9_.-]*\b"
)

# Claims the inventory cannot ground. These are deliberately narrow: they match
# an assertion about access, not a caveat asking the reader to check with staff.
AVAILABILITY_CLAIM_PATTERNS = (
    re.compile(r"\b(?:is|are|remains?)\s+(?:currently\s+)?(?:available|free|bookable)\b", re.I),
    re.compile(r"\bcan\s+be\s+booked\b", re.I),
    re.compile(r"\bno\s+training\s+(?:is\s+)?(?:required|needed)\b", re.I),
    re.compile(r"\bopen\s+access\b", re.I),
)

OPERATIONAL_CLAIM_PATTERN = re.compile(
    r"\b(?:fully\s+)?operational\b|\bin\s+good\s+working\s+order\b|\brecently\s+serviced\b",
    re.I,
)

# A line that says availability is NOT recorded, or asks the reader to confirm it,
# is the behaviour the prompt asks for. Flagging it would train answers away from
# stating their own limits, so caveats are exempt.
#
# The exemption is deliberately specific. A bare negation is not enough: "no
# training is required" contains "no" and is still an availability claim.
CAVEAT_PATTERN = re.compile(
    r"records?\s+no\b"
    r"|\b(?:does|do|did)\s+not\s+record\b"
    r"|\bnot\s+recorded\b"
    r"|\bno\s+(?:booking|availability|access|scheduling|training)\s+(?:data|information)\b"
    r"|\b(?:unknown|unverified|unclear)\b"
    r"|\bwhether\b"
    r"|\b(?:confirm|check|ask)\b[^.]{0,40}\bstaff\b",
    re.I,
)

# Words that turn two endpoints in one exclusive branch block into a claim that
# both are used at once.
SIMULTANEITY_PATTERN = re.compile(
    r"\b(?:simultaneous(?:ly)?|at\s+the\s+same\s+time|in\s+parallel|both\s+cameras|"
    r"concurrently|dual[- ]camera)\b",
    re.I,
)


@dataclass(frozen=True)
class Finding:
    """One ungrounded claim, with enough context to judge it."""

    code: str
    severity: str
    detail: str
    evidence: str = ""

    def render(self) -> str:
        line = f"[{self.severity}] {self.code}: {self.detail}"
        return f"{line}\n    evidence: {self.evidence}" if self.evidence else line


@dataclass
class AuthoritativeContext:
    """The identifiers the inventory actually supports."""

    instrument_ids: set[str] = field(default_factory=set)
    display_names: dict[str, str] = field(default_factory=dict)
    components_by_instrument: dict[str, set[str]] = field(default_factory=dict)
    route_ids_by_instrument: dict[str, set[str]] = field(default_factory=dict)
    # (instrument, route) -> component ids recorded on that route
    components_by_route: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    # instruments whose reported status rests on no recorded QC/maintenance event
    status_without_evidence: set[str] = field(default_factory=set)
    # (instrument, route) -> list of endpoint-id sets that are mutually exclusive
    exclusive_endpoint_groups: dict[tuple[str, str], list[set[str]]] = field(default_factory=dict)

    @property
    def all_components(self) -> set[str]:
        return {value for values in self.components_by_instrument.values() for value in values}


def load_context(inventory: dict[str, Any]) -> AuthoritativeContext:
    """Read the authoritative identifiers out of a generated inventory payload."""
    context = AuthoritativeContext()

    for record in inventory.get("active_microscopes") or []:
        if not isinstance(record, dict):
            continue
        instrument_id = str(record.get("id") or "").strip()
        if not instrument_id:
            continue

        context.instrument_ids.add(instrument_id)
        display_name = str(record.get("display_name") or "").strip()
        if display_name:
            context.display_names[display_name.casefold()] = instrument_id

        llm_context = record.get("llm_context") if isinstance(record.get("llm_context"), dict) else {}
        contract = (
            llm_context.get("authoritative_route_contract")
            if isinstance(llm_context.get("authoritative_route_contract"), dict)
            else {}
        )

        components: set[str] = set()
        for row in contract.get("hardware_inventory") or []:
            if isinstance(row, dict) and str(row.get("id") or "").strip():
                components.add(str(row["id"]).strip())
        context.components_by_instrument[instrument_id] = components

        routes: set[str] = set()
        for usage in contract.get("route_hardware_usage") or []:
            if not isinstance(usage, dict):
                continue
            route_id = str(usage.get("route_id") or "").strip()
            if not route_id:
                continue
            routes.add(route_id)
            context.components_by_route[(instrument_id, route_id)] = {
                str(value).strip()
                for value in (usage.get("hardware_inventory_ids") or [])
                if str(value).strip()
            }

            groups: list[set[str]] = []
            for block in usage.get("branch_blocks") or []:
                if not isinstance(block, dict) or block.get("selection_mode") != "exclusive":
                    continue
                endpoints = {
                    str(value).strip()
                    for branch in (block.get("branches") or [])
                    if isinstance(branch, dict)
                    for value in (branch.get("endpoint_inventory_ids") or [])
                    if str(value).strip()
                }
                if len(endpoints) > 1:
                    groups.append(endpoints)
            if groups:
                context.exclusive_endpoint_groups[(instrument_id, route_id)] = groups
        context.route_ids_by_instrument[instrument_id] = routes

        status = (
            (record.get("hardware_focus_summary") or {}).get("status")
            if isinstance(record.get("hardware_focus_summary"), dict)
            else {}
        )
        if isinstance(status, dict) and status.get("evidence") == "no_qc_or_maintenance_record":
            context.status_without_evidence.add(instrument_id)

    return context


def _instruments_mentioned(response: str, context: AuthoritativeContext) -> set[str]:
    """Instrument IDs the answer refers to, by ID or by recorded display name."""
    mentioned = {
        value for value in INSTRUMENT_ID_PATTERN.findall(response) if value in context.instrument_ids
    }
    folded = response.casefold()
    for display_name, instrument_id in context.display_names.items():
        if display_name and display_name in folded:
            mentioned.add(instrument_id)
    return mentioned


def _lines_with(response: str, pattern: re.Pattern[str]) -> Iterable[tuple[str, re.Match[str]]]:
    for line in response.splitlines():
        match = pattern.search(line)
        if match:
            yield line.strip(), match


def check_response(response: str, context: AuthoritativeContext) -> list[Finding]:
    """Report identifier claims the authoritative context does not support."""
    findings: list[Finding] = []

    for claimed in sorted(set(INSTRUMENT_ID_PATTERN.findall(response))):
        if claimed not in context.instrument_ids:
            findings.append(
                Finding(
                    code="unknown_instrument_id",
                    severity="error",
                    detail=f"{claimed} is not an active instrument in the inventory.",
                )
            )

    mentioned_instruments = _instruments_mentioned(response, context)
    known_components = context.all_components

    for claimed in sorted(set(COMPONENT_ID_PATTERN.findall(response))):
        if claimed not in known_components:
            findings.append(
                Finding(
                    code="unknown_component_id",
                    severity="error",
                    detail=f"{claimed} is not recorded on any active instrument.",
                )
            )
            continue

        owners = {
            instrument_id
            for instrument_id, components in context.components_by_instrument.items()
            if claimed in components
        }
        if mentioned_instruments and not (owners & mentioned_instruments):
            findings.append(
                Finding(
                    code="component_not_on_named_instrument",
                    severity="error",
                    detail=(
                        f"{claimed} is recorded on {sorted(owners)}, but the answer "
                        f"discusses {sorted(mentioned_instruments)}."
                    ),
                )
            )

    findings.extend(_check_route_attribution(response, context))
    findings.extend(_check_exclusive_branches(response, context))

    for line, _ in _lines_with(response, OPERATIONAL_CLAIM_PATTERN):
        for instrument_id in _instruments_mentioned(line, context) & context.status_without_evidence:
            findings.append(
                Finding(
                    code="status_claim_without_evidence",
                    severity="warning",
                    detail=(
                        f"{instrument_id} has no QC or maintenance record; its status is the "
                        "absence of a recorded problem, not a passed check."
                    ),
                    evidence=line,
                )
            )

    flagged_availability: set[str] = set()
    for pattern in AVAILABILITY_CLAIM_PATTERNS:
        for line, _ in _lines_with(response, pattern):
            if CAVEAT_PATTERN.search(line) or line in flagged_availability:
                continue
            flagged_availability.add(line)
            findings.append(
                Finding(
                    code="availability_claim",
                    severity="error",
                    detail="The inventory records no booking, access or training availability.",
                    evidence=line,
                )
            )

    return findings


def _iter_scoped_lines(
    response: str,
    context: AuthoritativeContext,
) -> Iterable[tuple[str, str | None]]:
    """Yield each line with the instrument it belongs to.

    Answers name the instrument in a heading and then discuss its route and
    hardware on later lines, so a line-local check misses exactly the mistakes
    worth catching. The instrument most recently named stays in scope until
    another one is named; a line naming two instruments clears the scope rather
    than guessing between them.
    """
    current: str | None = None
    for line in response.splitlines():
        mentioned = _instruments_mentioned(line, context)
        if len(mentioned) == 1:
            current = next(iter(mentioned))
        elif len(mentioned) > 1:
            current = None
        yield line, current


def _check_route_attribution(response: str, context: AuthoritativeContext) -> list[Finding]:
    """Flag components attached to a route they are not recorded on.

    Route membership is a closed enumeration built from the authored light-path
    sequences, so a component missing from a route's hardware list is not on that
    route. A line is only judged when exactly one of the instrument's routes is
    named on it, so prose that merely lists hardware is left alone.
    """
    findings: list[Finding] = []

    for line, instrument_id in _iter_scoped_lines(response, context):
        if instrument_id is None:
            continue

        routes = {
            route_id
            for route_id in context.route_ids_by_instrument.get(instrument_id, set())
            if re.search(rf"\b{re.escape(route_id)}\b", line)
        }
        if len(routes) != 1:
            continue
        route_id = next(iter(routes))

        allowed = context.components_by_route.get((instrument_id, route_id), set())
        owned = context.components_by_instrument.get(instrument_id, set())

        for claimed in sorted(set(COMPONENT_ID_PATTERN.findall(line))):
            if claimed in owned and claimed not in allowed:
                findings.append(
                    Finding(
                        code="component_not_on_route",
                        severity="error",
                        detail=(
                            f"{claimed} is recorded on {instrument_id} but not on route "
                            f"'{route_id}'."
                        ),
                        evidence=line.strip(),
                    )
                )

    return findings


def _check_exclusive_branches(response: str, context: AuthoritativeContext) -> list[Finding]:
    """Flag simultaneous use of endpoints the records mark mutually exclusive.

    A branch block with `selection_mode: exclusive` records that the route sends
    light to one of its branches, so an answer promising two cameras at once is
    describing an acquisition the ledger does not support.
    """
    findings: list[Finding] = []

    for line, instrument_id in _iter_scoped_lines(response, context):
        if instrument_id is None or not SIMULTANEITY_PATTERN.search(line):
            continue

        claimed = set(COMPONENT_ID_PATTERN.findall(line))
        if len(claimed) < 2:
            continue

        # The same endpoints are usually exclusive on several of an instrument's
        # routes. That is one mistake in the answer, so report it once and name
        # the routes it applies to.
        seen_overlaps: set[tuple[str, ...]] = set()
        for group_key in sorted(
            {
                tuple(sorted(claimed & group))
                for (owner, _), groups in context.exclusive_endpoint_groups.items()
                if owner == instrument_id
                for group in groups
                if len(claimed & group) > 1
            }
        ):
            if group_key in seen_overlaps:
                continue
            seen_overlaps.add(group_key)
            routes = sorted(
                route_id
                for (owner, route_id), groups in context.exclusive_endpoint_groups.items()
                if owner == instrument_id
                and any(set(group_key) <= group for group in groups)
            )
            findings.append(
                Finding(
                    code="exclusive_branch_used_simultaneously",
                    severity="error",
                    detail=(
                        f"{instrument_id} records {list(group_key)} as mutually exclusive "
                        f"endpoints on route(s) {routes}. Simultaneous use is not supported "
                        "by the records."
                    ),
                    evidence=line.strip(),
                )
            )

    return findings


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check a saved planning answer for instrument/component claims that the "
            "authoritative inventory does not support. Offline; calls no model."
        )
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path("dashboard_docs/assets/llm_inventory.json"),
        help="Generated llm_inventory.json (default: %(default)s).",
    )
    parser.add_argument(
        "--response",
        type=Path,
        required=True,
        help="File holding the assistant's saved answer.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write findings as JSON.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not args.inventory.is_file():
        print(f"Inventory not found: {args.inventory}", file=sys.stderr)
        print("Build it first: PYTHONPATH=. python -m scripts.dashboard_builder", file=sys.stderr)
        return 2
    if not args.response.is_file():
        print(f"Response not found: {args.response}", file=sys.stderr)
        return 2

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    context = load_context(inventory)
    findings = check_response(args.response.read_text(encoding="utf-8"), context)

    if args.json_out is not None:
        args.json_out.write_text(
            json.dumps([finding.__dict__ for finding in findings], indent=2),
            encoding="utf-8",
        )

    if not findings:
        print(
            f"No ungrounded identifier claims found "
            f"({len(context.instrument_ids)} instruments in authoritative context)."
        )
        return 0

    errors = sum(1 for finding in findings if finding.severity == "error")
    print(f"{len(findings)} finding(s), {errors} error(s):\n")
    for finding in findings:
        print(finding.render())

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
