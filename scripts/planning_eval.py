"""Check a saved planning answer against the authoritative inventory.

This is an offline grounding check for answers produced after a user attaches the
generated ``llm_inventory.json`` to an LLM conversation. It deliberately does not
judge scientific quality. It checks whether explicit instrument/component claims
are traceable to the inventory, whether route membership is respected, whether
exclusive branches are misrepresented as simultaneous, and whether the answer
asserts availability that the inventory does not record.

No model, network connection or API key is used.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


# Portable identifier recognition. Component IDs in the canonical route contract
# use a ``namespace:value`` shape, but the namespace itself is not hard-coded.
COMPONENT_ID_PATTERN = re.compile(
    r"\b[A-Za-z][A-Za-z0-9_.-]*:[A-Za-z0-9_][A-Za-z0-9_.-]*\b"
)
TAGGED_INSTRUMENT_PATTERN = re.compile(
    r"(?im)\binstrument_id\s*[:=]\s*[`\"']?(?P<value>[A-Za-z0-9][A-Za-z0-9_.:-]*)"
)
ID_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_.:-])[A-Za-z0-9][A-Za-z0-9_.:-]*(?![A-Za-z0-9_.:-])"
)

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
# Claims that the facility records nothing of a kind. A hallucinated absence is
# as harmful as a hallucinated presence and reads as appropriate caution: it
# sends a researcher away from capability the facility actually has.
#
# Each entry pairs a phrasing with the side of it the claim's subject sits on:
# "X is recorded for none" puts X before, "no instrument records X" after.
# Searching only that side keeps an unrelated capability named later in the same
# sentence from being read as the thing being denied.
ABSENCE_CLAIM_PATTERNS = (
    (re.compile(r"recorded\s+(?:for|on|by)\s+(?:none|no\s+instrument)", re.I), "before"),
    (re.compile(r"\bnot\s+recorded\s+(?:for|on)\s+any\b", re.I), "before"),
    (re.compile(r"\bis\s+not\s+recorded\s+anywhere\b", re.I), "before"),
    (re.compile(r"\brecorded\s+for\s+neither\b", re.I), "before"),
    (re.compile(r"\bno\s+(?:active\s+)?instruments?\s+(?:here\s+)?records?\b", re.I), "after"),
    (
        re.compile(r"\bnone\s+of\s+(?:the\s+)?(?:\d+\s+)?instruments?\s+records?\b", re.I),
        "after",
    ),
)

SIMULTANEITY_PATTERN = re.compile(
    r"\b(?:simultaneous(?:ly)?|at\s+the\s+same\s+time|in\s+parallel|both\s+cameras|"
    r"concurrently|dual[- ]camera)\b",
    re.I,
)


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    detail: str
    evidence: str = ""

    def render(self) -> str:
        line = f"[{self.severity}] {self.code}: {self.detail}"
        return f"{line}\n    evidence: {self.evidence}" if self.evidence else line


@dataclass
class AuthoritativeContext:
    instrument_ids: set[str] = field(default_factory=set)
    display_names: dict[str, str] = field(default_factory=dict)
    components_by_instrument: dict[str, set[str]] = field(default_factory=dict)
    objective_ids_by_instrument: dict[str, set[str]] = field(default_factory=dict)
    route_ids_by_instrument: dict[str, set[str]] = field(default_factory=dict)
    components_by_route: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    status_without_evidence: set[str] = field(default_factory=set)
    exclusive_endpoint_groups: dict[tuple[str, str], list[set[str]]] = field(default_factory=dict)
    # Searchable phrase -> instruments recording it. Lets an "X is recorded for
    # none" claim be checked rather than taken on trust.
    recorded_terms: dict[str, set[str]] = field(default_factory=dict)

    @property
    def all_components(self) -> set[str]:
        return {value for values in self.components_by_instrument.values() for value in values}

    @property
    def instrument_id_prefixes(self) -> set[str]:
        """Prefixes learned from the inventory for spotting ID-shaped prose claims."""
        prefixes: set[str] = set()
        for instrument_id in self.instrument_ids:
            match = re.match(r"^([A-Za-z0-9]+[-_:])", instrument_id)
            if match:
                prefixes.add(match.group(1))
        return prefixes


def load_context(inventory: dict[str, Any]) -> AuthoritativeContext:
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
        objectives: set[str] = set()
        for row in contract.get("hardware_inventory") or []:
            if not isinstance(row, dict):
                continue
            component_id = str(row.get("id") or "").strip()
            if not component_id:
                continue
            components.add(component_id)
            if (
                str(row.get("inventory_class") or "").strip() == "objective"
                or component_id.startswith("objective:")
            ):
                objectives.add(component_id)
        context.components_by_instrument[instrument_id] = components
        context.objective_ids_by_instrument[instrument_id] = objectives

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

        _record_capability_terms(context, instrument_id, record, contract)

    return context


def _record_capability_terms(
    context: AuthoritativeContext,
    instrument_id: str,
    record: dict[str, Any],
    contract: dict[str, Any],
) -> None:
    """Index every capability the inventory records, in searchable forms.

    Controlled terms are authored as slugs (`live_cell_imaging`), while an answer
    writes prose ("live cell imaging"), so both spellings are indexed. Supporting
    features are already prose and are indexed as-is.
    """

    def add(term: Any) -> None:
        text = str(term or "").strip().lower()
        if not text:
            return
        for spelling in {text, text.replace("_", " ")}:
            context.recorded_terms.setdefault(spelling, set()).add(instrument_id)

    capabilities = record.get("capabilities") if isinstance(record.get("capabilities"), dict) else {}
    for values in capabilities.values():
        if isinstance(values, list):
            for value in values:
                if isinstance(value, str):
                    add(value)

    summary = (
        record.get("hardware_focus_summary")
        if isinstance(record.get("hardware_focus_summary"), dict)
        else {}
    )
    for label in summary.get("supporting_feature_labels") or []:
        add(label)

    for route in contract.get("routes") or []:
        if not isinstance(route, dict):
            continue
        for readout in ((route.get("route_identity") or {}).get("readouts") or []):
            add(readout.get("id") if isinstance(readout, dict) else readout)


def _contains_token(text: str, token: str) -> bool:
    return bool(
        re.search(rf"(?<![A-Za-z0-9_.:-]){re.escape(token)}(?![A-Za-z0-9_.:-])", text)
    )


def _tagged_instrument_claims(response: str) -> set[str]:
    return {match.group("value") for match in TAGGED_INSTRUMENT_PATTERN.finditer(response)}


def _free_prose_instrument_claims(
    response: str,
    context: AuthoritativeContext,
) -> set[str]:
    """Find instrument-ID-shaped tokens using prefixes learned from the inventory.

    This restores checking of ordinary saved LLM prose without assuming that a
    facility uses AIC's ``scope-`` prefix. For example, if the inventory contains
    IDs beginning ``scope-`` or ``microscope-``, an untagged token with that same
    learned prefix is treated as an instrument-ID claim and validated.
    """
    prefixes = context.instrument_id_prefixes
    if not prefixes:
        return set()
    return {
        token
        for token in ID_TOKEN_PATTERN.findall(response)
        if any(token.startswith(prefix) for prefix in prefixes)
    }


def _instrument_claims(response: str, context: AuthoritativeContext) -> set[str]:
    return _tagged_instrument_claims(response) | _free_prose_instrument_claims(response, context)


def _instruments_mentioned(response: str, context: AuthoritativeContext) -> set[str]:
    mentioned = {
        instrument_id
        for instrument_id in context.instrument_ids
        if _contains_token(response, instrument_id)
    }
    folded = response.casefold()
    for display_name, instrument_id in context.display_names.items():
        if display_name and display_name in folded:
            mentioned.add(instrument_id)
    mentioned.update(
        claim for claim in _instrument_claims(response, context) if claim in context.instrument_ids
    )
    return mentioned


def _component_claims(response: str) -> set[str]:
    return set(COMPONENT_ID_PATTERN.findall(response))


def _lines_with(response: str, pattern: re.Pattern[str]) -> Iterable[tuple[str, re.Match[str]]]:
    for line in response.splitlines():
        match = pattern.search(line)
        if match:
            yield line.strip(), match


def _iter_scoped_lines(
    response: str,
    context: AuthoritativeContext,
) -> Iterable[tuple[str, str | None]]:
    current: str | None = None
    for line in response.splitlines():
        mentioned = _instruments_mentioned(line, context)
        if len(mentioned) == 1:
            current = next(iter(mentioned))
        elif len(mentioned) > 1:
            current = None
        yield line, current


def _check_component_attribution(
    response: str,
    context: AuthoritativeContext,
) -> list[Finding]:
    """Check component ownership against the locally scoped instrument.

    A response may discuss several microscopes. Comparing a component against the
    set of every instrument named anywhere in the answer can hide a bad assignment
    under one candidate merely because the true owner appears in a later section.
    """
    findings: list[Finding] = []
    known_components = context.all_components

    for line, instrument_id in _iter_scoped_lines(response, context):
        if instrument_id is None:
            continue
        owned = context.components_by_instrument.get(instrument_id, set())
        for claimed in sorted(_component_claims(line)):
            if claimed not in known_components or claimed in owned:
                continue
            owners = sorted(
                owner
                for owner, components in context.components_by_instrument.items()
                if claimed in components
            )
            findings.append(
                Finding(
                    code="component_not_on_named_instrument",
                    severity="error",
                    detail=(
                        f"{claimed} is recorded on {owners}, not on the locally named "
                        f"instrument {instrument_id}."
                    ),
                    evidence=line.strip(),
                )
            )

    return findings


def _check_route_attribution(response: str, context: AuthoritativeContext) -> list[Finding]:
    findings: list[Finding] = []

    for line, instrument_id in _iter_scoped_lines(response, context):
        if instrument_id is None:
            continue
        routes = {
            route_id
            for route_id in context.route_ids_by_instrument.get(instrument_id, set())
            if _contains_token(line, route_id)
        }
        if len(routes) != 1:
            continue
        route_id = next(iter(routes))
        allowed = context.components_by_route.get((instrument_id, route_id), set())
        owned = context.components_by_instrument.get(instrument_id, set())

        for claimed in sorted(_component_claims(line)):
            if claimed not in owned:
                continue
            if claimed in context.objective_ids_by_instrument.get(instrument_id, set()):
                findings.append(
                    Finding(
                        code="objective_route_compatibility_unproven",
                        severity="error",
                        detail=(
                            f"{claimed} is installed on {instrument_id}, but objective-to-route "
                            f"compatibility is not established for route '{route_id}'."
                        ),
                        evidence=line.strip(),
                    )
                )
            elif claimed not in allowed:
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
    findings: list[Finding] = []

    for line, instrument_id in _iter_scoped_lines(response, context):
        if instrument_id is None or not SIMULTANEITY_PATTERN.search(line):
            continue
        claimed = _component_claims(line)
        if len(claimed) < 2:
            continue

        overlaps = {
            tuple(sorted(claimed & group))
            for (owner, _), groups in context.exclusive_endpoint_groups.items()
            if owner == instrument_id
            for group in groups
            if len(claimed & group) > 1
        }
        for group_key in sorted(overlaps):
            routes = sorted(
                route_id
                for (owner, route_id), groups in context.exclusive_endpoint_groups.items()
                if owner == instrument_id and any(set(group_key) <= group for group in groups)
            )
            findings.append(
                Finding(
                    code="exclusive_branch_used_simultaneously",
                    severity="error",
                    detail=(
                        f"{instrument_id} records {list(group_key)} as mutually exclusive "
                        f"endpoints on route(s) {routes}."
                    ),
                    evidence=line.strip(),
                )
            )

    return findings


def _iter_sentences(response: str) -> Iterable[str]:
    """Yield sentences, reuniting a claim that a line wrap split in two.

    The line-based scanners above are fine for short assertions, but an absence
    claim routinely reads "environmental control is recorded for none of the 22
    instruments" and a wrapped copy of that sentence hides either the claim or
    the term it is about. Blank lines and list bullets end a sentence so an
    unpunctuated bullet does not swallow the next one.
    """
    buffer: list[str] = []
    for raw_line in response.splitlines():
        line = raw_line.strip()
        starts_new_block = not line or re.match(r"^(?:[-*+]|#|\d+[.)])\s", line)
        if starts_new_block and buffer:
            yield " ".join(buffer)
            buffer = []
        if not line:
            continue
        buffer.append(re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", line))
    if buffer:
        yield " ".join(buffer)


def _split_sentences(block: str) -> Iterable[str]:
    for sentence in re.split(r"(?<=[.!?;])\s+", block):
        cleaned = sentence.strip()
        if cleaned:
            yield cleaned


def _mentions_capability(text: str, term: str) -> bool:
    """Match a capability term as whole words, letting punctuation end it.

    `_contains_token` is for identifiers and treats a trailing "." as part of
    the token, which never matches prose ending a sentence. Hyphen and
    underscore still bind, so `tirf` does not match inside `scope-zeiss-tirf` —
    reading an instrument id as the denied capability inverts the sentence.
    """
    pattern = rf"(?<![A-Za-z0-9_-]){re.escape(term)}(?![A-Za-z0-9_-])"
    return bool(re.search(pattern, text))


def _check_false_absence(response: str, context: AuthoritativeContext) -> list[Finding]:
    """Flag "nothing here records X" when the inventory in fact records X.

    A fabricated absence is not the cautious failure it looks like: it steers a
    researcher away from capability the facility has, and no other check in this
    module can see it, because every identifier in such a sentence is real.
    """
    findings: list[Finding] = []
    seen: set[tuple[str, str | None]] = set()

    for block in _iter_sentences(response):
        for sentence in _split_sentences(block):
            named = _instruments_mentioned(sentence, context)
            # "no instrument records X" stays a fleet claim even when it names an
            # example; only a single named instrument narrows the scope.
            scope = next(iter(named)) if len(named) == 1 else None

            for pattern, side in ABSENCE_CLAIM_PATTERNS:
                match = pattern.search(sentence)
                if match is None:
                    continue
                subject = (
                    sentence[: match.start()] if side == "before" else sentence[match.end() :]
                ).casefold()

                for term in sorted(context.recorded_terms, key=len, reverse=True):
                    if len(term) < 4 or not _mentions_capability(subject, term):
                        continue
                    recorders = context.recorded_terms[term]
                    if scope is not None:
                        if scope not in recorders:
                            continue
                        detail = f"{scope} does record {term!r}."
                    elif recorders:
                        detail = (
                            f"{term!r} is recorded for {len(recorders)} active instrument(s), "
                            f"including {sorted(recorders)[0]}."
                        )
                    else:
                        continue
                    key = (term, scope)
                    if key not in seen:
                        seen.add(key)
                        findings.append(
                            Finding(
                                code="false_absence_claim",
                                severity="error",
                                detail=detail,
                                evidence=sentence,
                            )
                        )
                    # One finding per phrasing: terms are checked longest first,
                    # so a hit on "live cell imaging" must not also report
                    # "imaging".
                    break

    return findings


def check_response(response: str, context: AuthoritativeContext) -> list[Finding]:
    findings: list[Finding] = []

    for claimed in sorted(_instrument_claims(response, context)):
        if claimed not in context.instrument_ids:
            findings.append(
                Finding(
                    code="unknown_instrument_id",
                    severity="error",
                    detail=f"{claimed} is not an active instrument in the inventory.",
                )
            )

    known_components = context.all_components
    for claimed in sorted(_component_claims(response)):
        if claimed not in known_components:
            findings.append(
                Finding(
                    code="unknown_component_id",
                    severity="error",
                    detail=f"{claimed} is not recorded on any active instrument.",
                )
            )

    findings.extend(_check_component_attribution(response, context))
    findings.extend(_check_route_attribution(response, context))
    findings.extend(_check_exclusive_branches(response, context))
    findings.extend(_check_false_absence(response, context))

    for line, _ in _lines_with(response, OPERATIONAL_CLAIM_PATTERN):
        for instrument_id in _instruments_mentioned(line, context) & context.status_without_evidence:
            findings.append(
                Finding(
                    code="status_claim_without_evidence",
                    severity="warning",
                    detail=(
                        f"{instrument_id} has no QC or maintenance record; its reported status "
                        "is the absence of a recorded problem, not a passed check."
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


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check a saved planning answer for claims unsupported by the authoritative "
            "inventory. Offline; calls no model."
        )
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path("dashboard_docs/assets/llm_inventory.json"),
        help="Generated llm_inventory.json (default: %(default)s).",
    )
    parser.add_argument("--response", type=Path, required=True, help="Saved assistant answer.")
    parser.add_argument("--json-out", type=Path, default=None, help="Optional JSON findings path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not args.inventory.is_file():
        print(f"Inventory not found: {args.inventory}", file=sys.stderr)
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
