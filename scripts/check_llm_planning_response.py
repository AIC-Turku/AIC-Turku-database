"""Offline linting for saved LLM microscopy-planning responses.

The checker deliberately validates identifiers and route membership only. It does
not add microscopy knowledge and it does not decide which microscope is best.
All authority comes from ``llm_inventory.json``.

Usage::

    python -m scripts.check_llm_planning_response \
        --inventory dashboard_docs/assets/llm_inventory.json \
        --response saved_response.json

The response may be JSON or plain text. JSON gives the strongest checks when it
uses explicit keys such as ``instrument_id``, ``route_id``, ``component_id``,
``endpoint_id`` or ``objective_id``. Plain text is checked for the same tagged
forms (for example ``route_id: tirf``).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROUTE_FACT_KEYS = (
    "selected_or_selectable_sources",
    "selected_or_selectable_excitation_filters",
    "selected_or_selectable_dichroics",
    "selected_or_selectable_emission_filters",
    "selected_or_selectable_splitters",
    "selected_or_selectable_branch_selectors",
    "selected_or_selectable_endpoints",
    "selected_or_selectable_modulators",
)

COMPONENT_CLAIM_KEYS = {
    "component_id",
    "source_id",
    "excitation_filter_id",
    "dichroic_id",
    "emission_filter_id",
    "splitter_id",
    "branch_selector_id",
    "endpoint_id",
    "detector_id",
    "modulator_id",
}

OBJECTIVE_CLAIM_KEYS = {"objective_id"}

_TAGGED_ID_RE = re.compile(
    r"(?im)\b(?P<key>instrument_id|route_id|component_id|source_id|"
    r"excitation_filter_id|dichroic_id|emission_filter_id|splitter_id|"
    r"branch_selector_id|endpoint_id|detector_id|modulator_id|objective_id)"
    r"\s*[:=]\s*[`\"']?(?P<value>[A-Za-z0-9][A-Za-z0-9_.:-]*)"
)


def _clean_id(value: Any) -> str:
    return str(value or "").strip()


def _collect_ids(value: Any) -> set[str]:
    ids: set[str] = set()
    if isinstance(value, dict):
        item_id = _clean_id(value.get("id"))
        if item_id:
            ids.add(item_id)
        for child in value.values():
            ids.update(_collect_ids(child))
    elif isinstance(value, list):
        for child in value:
            ids.update(_collect_ids(child))
    return ids


def build_authoritative_claim_index(inventory: dict[str, Any]) -> dict[str, Any]:
    """Build an identifier/membership index from the exported authoritative data."""
    instruments: dict[str, Any] = {}
    route_locations: dict[str, set[str]] = {}
    all_route_component_ids: set[str] = set()
    all_hardware_ids: set[str] = set()

    for microscope in inventory.get("active_microscopes") or []:
        if not isinstance(microscope, dict):
            continue
        instrument_id = _clean_id(microscope.get("id"))
        if not instrument_id:
            continue

        hardware = microscope.get("hardware") if isinstance(microscope.get("hardware"), dict) else {}
        generic_hardware_ids = _collect_ids(hardware)
        objective_ids = _collect_ids(hardware.get("objectives") or [])
        all_hardware_ids.update(generic_hardware_ids)

        route_map: dict[str, Any] = {}
        contract = (
            ((microscope.get("llm_context") or {}).get("authoritative_route_contract") or {})
            if isinstance(microscope.get("llm_context"), dict)
            else {}
        )
        routes = contract.get("routes") if isinstance(contract.get("routes"), list) else []

        for route in routes:
            if not isinstance(route, dict):
                continue
            route_id = _clean_id(route.get("id"))
            if not route_id:
                continue
            route_locations.setdefault(route_id, set()).add(instrument_id)
            route_facts = route.get("route_optical_facts") if isinstance(route.get("route_optical_facts"), dict) else {}
            component_ids: set[str] = set()
            for key in ROUTE_FACT_KEYS:
                component_ids.update(_collect_ids(route_facts.get(key) or []))
            all_route_component_ids.update(component_ids)

            # Future-proof: objective compatibility is considered proven only if
            # an authoritative route fact explicitly carries an objective relation.
            route_objective_ids: set[str] = set()
            for key, value in route_facts.items():
                if "objective" in str(key).lower():
                    route_objective_ids.update(_collect_ids(value))

            route_map[route_id] = {
                "component_ids": component_ids,
                "objective_ids": route_objective_ids,
            }

        instruments[instrument_id] = {
            "route_map": route_map,
            "generic_hardware_ids": generic_hardware_ids,
            "objective_ids": objective_ids,
        }

    return {
        "instruments": instruments,
        "route_locations": route_locations,
        "all_route_component_ids": all_route_component_ids,
        "all_hardware_ids": all_hardware_ids,
    }


def _extract_json_claims(value: Any, context: dict[str, str] | None = None) -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    inherited = dict(context or {})

    if isinstance(value, dict):
        local = dict(inherited)
        for key in ("instrument_id", "route_id"):
            candidate = _clean_id(value.get(key))
            if candidate:
                local[key] = candidate

        for key in COMPONENT_CLAIM_KEYS | OBJECTIVE_CLAIM_KEYS:
            candidate = _clean_id(value.get(key))
            if candidate:
                claims.append({**local, "claim_key": key, "claim_id": candidate})

        if _clean_id(value.get("instrument_id")):
            claims.append({**local, "claim_key": "instrument_id", "claim_id": local["instrument_id"]})
        if _clean_id(value.get("route_id")):
            claims.append({**local, "claim_key": "route_id", "claim_id": local["route_id"]})

        for child in value.values():
            claims.extend(_extract_json_claims(child, local))
    elif isinstance(value, list):
        for child in value:
            claims.extend(_extract_json_claims(child, inherited))

    return claims


def _extract_text_claims(text: str) -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for match in _TAGGED_ID_RE.finditer(text):
        key = match.group("key")
        value = match.group("value")
        if key in {"instrument_id", "route_id"}:
            current[key] = value
        claims.append({**current, "claim_key": key, "claim_id": value})
    return claims


def extract_claims(response_text: str) -> list[dict[str, str]]:
    """Extract explicit identifier claims from JSON or tagged plain text."""
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError:
        return _extract_text_claims(response_text)
    return _extract_json_claims(parsed)


def audit_response_claims(inventory: dict[str, Any], response_text: str) -> dict[str, Any]:
    """Return deterministic violations for claims unsupported by route authority."""
    index = build_authoritative_claim_index(inventory)
    instruments = index["instruments"]
    violations: list[dict[str, str]] = []
    claims = extract_claims(response_text)

    for claim in claims:
        claim_key = claim.get("claim_key", "")
        claim_id = claim.get("claim_id", "")
        instrument_id = claim.get("instrument_id", "")
        route_id = claim.get("route_id", "")

        if claim_key == "instrument_id":
            if claim_id not in instruments:
                violations.append({
                    "code": "unknown_instrument_id",
                    "claim_id": claim_id,
                    "message": f"Instrument ID {claim_id!r} is absent from active_microscopes.",
                })
            continue

        if instrument_id and instrument_id not in instruments:
            violations.append({
                "code": "unknown_instrument_id",
                "claim_id": instrument_id,
                "message": f"Instrument ID {instrument_id!r} is absent from active_microscopes.",
            })
            continue

        if claim_key == "route_id":
            if instrument_id:
                if claim_id not in instruments[instrument_id]["route_map"]:
                    violations.append({
                        "code": "route_not_on_instrument",
                        "claim_id": claim_id,
                        "message": f"Route ID {claim_id!r} is not authoritative for instrument {instrument_id!r}.",
                    })
            elif claim_id not in index["route_locations"]:
                violations.append({
                    "code": "unknown_route_id",
                    "claim_id": claim_id,
                    "message": f"Route ID {claim_id!r} is absent from all authoritative route contracts.",
                })
            continue

        if claim_key in OBJECTIVE_CLAIM_KEYS:
            if instrument_id:
                instrument = instruments[instrument_id]
                if claim_id not in instrument["objective_ids"]:
                    violations.append({
                        "code": "unknown_objective_id",
                        "claim_id": claim_id,
                        "message": f"Objective ID {claim_id!r} is not recorded on instrument {instrument_id!r}.",
                    })
                    continue
                if route_id:
                    route = instrument["route_map"].get(route_id)
                    if route is None:
                        violations.append({
                            "code": "route_not_on_instrument",
                            "claim_id": route_id,
                            "message": f"Route ID {route_id!r} is not authoritative for instrument {instrument_id!r}.",
                        })
                    elif claim_id not in route["objective_ids"]:
                        violations.append({
                            "code": "objective_route_compatibility_unproven",
                            "claim_id": claim_id,
                            "message": (
                                f"Objective ID {claim_id!r} is installed on {instrument_id!r}, but the authoritative "
                                f"route {route_id!r} does not explicitly link that objective."
                            ),
                        })
            elif claim_id not in index["all_hardware_ids"]:
                violations.append({
                    "code": "unknown_objective_id",
                    "claim_id": claim_id,
                    "message": f"Objective ID {claim_id!r} is absent from recorded hardware.",
                })
            continue

        if claim_key in COMPONENT_CLAIM_KEYS:
            if instrument_id and route_id:
                instrument = instruments[instrument_id]
                route = instrument["route_map"].get(route_id)
                if route is None:
                    violations.append({
                        "code": "route_not_on_instrument",
                        "claim_id": route_id,
                        "message": f"Route ID {route_id!r} is not authoritative for instrument {instrument_id!r}.",
                    })
                elif claim_id not in route["component_ids"]:
                    code = (
                        "generic_hardware_not_route_evidence"
                        if claim_id in instrument["generic_hardware_ids"]
                        else "component_not_on_route"
                    )
                    violations.append({
                        "code": code,
                        "claim_id": claim_id,
                        "message": (
                            f"Component ID {claim_id!r} is not present in authoritative route facts for "
                            f"{instrument_id!r}/{route_id!r}."
                        ),
                    })
            elif claim_id not in index["all_route_component_ids"]:
                code = (
                    "generic_hardware_not_route_evidence"
                    if claim_id in index["all_hardware_ids"]
                    else "unknown_component_id"
                )
                violations.append({
                    "code": code,
                    "claim_id": claim_id,
                    "message": f"Component ID {claim_id!r} is not established by any authoritative route fact.",
                })

    return {
        "claim_count": len(claims),
        "violation_count": len(violations),
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--response", required=True, type=Path)
    args = parser.parse_args()

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    response_text = args.response.read_text(encoding="utf-8")
    report = audit_response_claims(inventory, response_text)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["violation_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
