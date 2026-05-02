"""LLM-safe dashboard inventory export.

This module owns the derived LLM export projection.

Authoritative production dataflow:

    YAML
    -> strict validation
    -> canonical build context / canonical DTOs
    -> derived exports:
       dashboard_view
       llm_inventory
       methods_export
       virtual_microscope_payload

This module must not import scripts.dashboard_builder.
"""

from __future__ import annotations

import copy
from typing import Any

from scripts.build_context import clean_text


def _collect_known_missing_paths(value: Any, prefix: str = "") -> tuple[list[str], list[str]]:
    """Return dotted known/missing field paths for an arbitrary JSON-like value."""
    known_fields: list[str] = []
    missing_fields: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            child_known, child_missing = _collect_known_missing_paths(child, child_prefix)
            known_fields.extend(child_known)
            missing_fields.extend(child_missing)
        return known_fields, missing_fields

    if isinstance(value, list):
        if not value:
            known_fields.append(prefix)
            return known_fields, missing_fields

        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]"
            child_known, child_missing = _collect_known_missing_paths(child, child_prefix)
            known_fields.extend(child_known)
            missing_fields.extend(child_missing)

        return known_fields, missing_fields

    if value is None:
        missing_fields.append(prefix)
    else:
        known_fields.append(prefix)

    return known_fields, missing_fields


def _display_labels(rows: Any, *, installed_only: bool = False) -> list[str]:
    """Extract stable display labels from canonical row dictionaries."""
    labels: list[str] = []

    if not isinstance(rows, list):
        return labels

    for row in rows:
        if not isinstance(row, dict):
            continue

        if installed_only and row.get("is_installed") is False:
            continue

        label = clean_text(
            row.get("display_label")
            or row.get("name")
            or row.get("model")
            or row.get("id")
        )
        if label:
            labels.append(label)

    return labels


def _build_hardware_focus_summary(
    canonical_instrument_dto: dict[str, Any],
    canonical_lightpath_dto: dict[str, Any],
    *,
    inventory_completeness: dict[str, Any] | None = None,
    status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build explicit derived summary for LLM screening from canonical DTO inputs."""
    hardware = (
        canonical_instrument_dto.get("hardware")
        if isinstance(canonical_instrument_dto.get("hardware"), dict)
        else {}
    )

    authoritative_route_contract = (
        (((canonical_lightpath_dto.get("projections") or {}).get("llm")) or {}).get(
            "authoritative_route_contract"
        )
        if isinstance(canonical_lightpath_dto, dict)
        else {}
    ) or {}

    route_rows = (
        authoritative_route_contract.get("available_routes")
        if isinstance(authoritative_route_contract.get("available_routes"), list)
        else []
    )

    route_labels = [
        clean_text(route.get("label") or route.get("display_label") or route.get("id"))
        for route in route_rows
        if isinstance(route, dict)
        and clean_text(route.get("label") or route.get("display_label") or route.get("id"))
    ]

    supporting_features: list[str] = []

    environment = (
        hardware.get("environment")
        if isinstance(hardware.get("environment"), dict)
        else {}
    )
    if environment.get("present"):
        supporting_features.append("environmental control")

    hardware_autofocus = (
        hardware.get("hardware_autofocus")
        if isinstance(hardware.get("hardware_autofocus"), dict)
        else {}
    )
    if hardware_autofocus.get("present"):
        supporting_features.append("hardware autofocus")

    triggering = (
        hardware.get("triggering")
        if isinstance(hardware.get("triggering"), dict)
        else {}
    )
    if triggering.get("present"):
        supporting_features.append("hardware triggering")

    if _display_labels(hardware.get("optical_modulators")):
        supporting_features.append("optical modulation")

    if _display_labels(hardware.get("illumination_logic")):
        supporting_features.append("adaptive illumination")

    if _display_labels(hardware.get("magnification_changers")):
        supporting_features.append("magnification changer")

    completeness = inventory_completeness if isinstance(inventory_completeness, dict) else {}

    policy_missing_required = (
        completeness.get("policy_missing_required")
        if isinstance(completeness.get("policy_missing_required"), list)
        else []
    )

    policy_missing_conditional = (
        completeness.get("policy_missing_conditional")
        if isinstance(completeness.get("policy_missing_conditional"), list)
        else []
    )

    caveat_titles = [
        clean_text(entry.get("title") or entry.get("path"))
        for entry in [*policy_missing_required, *policy_missing_conditional]
        if isinstance(entry, dict) and clean_text(entry.get("title") or entry.get("path"))
    ]

    return {
        "modality_labels": (_display_labels(canonical_instrument_dto.get("modalities")) or _display_labels((canonical_instrument_dto.get("capabilities") or {}).get("imaging_modes"))),
        "route_labels": route_labels,
        "installed_objective_labels": _display_labels(
            hardware.get("objectives"),
            installed_only=True,
        ),
        "light_source_labels": _display_labels(
            hardware.get("sources") or hardware.get("light_sources")
        ),
        "detector_labels": _display_labels(hardware.get("detectors")),
        "supporting_feature_labels": sorted(dict.fromkeys(supporting_features)),
        "planning_caveat_labels": caveat_titles[:8],
        "status": copy.deepcopy(status or {}),
    }


def _build_route_planning_summary(
    dto: dict[str, Any],
    authoritative_route_contract: dict[str, Any],
) -> dict[str, Any]:
    """Build route-planning convenience summary from the authoritative route contract."""
    routes = (
        authoritative_route_contract.get("routes")
        if isinstance(authoritative_route_contract.get("routes"), list)
        else []
    )

    hardware = dto.get("hardware") if isinstance(dto.get("hardware"), dict) else {}

    installed_objectives = [
        {
            "id": clean_text(obj.get("id")),
            "display_label": clean_text(
                obj.get("display_label")
                or obj.get("name")
                or obj.get("model")
                or obj.get("id")
            ),
            "manufacturer": clean_text(obj.get("manufacturer")),
            "model": clean_text(obj.get("model")),
            "product_code": clean_text(obj.get("product_code")),
        }
        for obj in (hardware.get("objectives") or [])
        if isinstance(obj, dict) and obj.get("is_installed") is not False
    ]

    route_rows: list[dict[str, Any]] = []

    for route in routes:
        if not isinstance(route, dict):
            continue

        route_facts = (
            route.get("route_optical_facts")
            if isinstance(route.get("route_optical_facts"), dict)
            else {}
        )

        def fact_rows(key: str) -> list[dict[str, Any]]:
            return [
                copy.deepcopy(item)
                for item in (route_facts.get(key) or [])
                if isinstance(item, dict)
            ]

        sources = fact_rows("selected_or_selectable_sources")
        excitation_filters = fact_rows("selected_or_selectable_excitation_filters")
        dichroics = fact_rows("selected_or_selectable_dichroics")
        emission_filters = fact_rows("selected_or_selectable_emission_filters")
        splitters = fact_rows("selected_or_selectable_splitters")
        branch_selectors = fact_rows("selected_or_selectable_branch_selectors")
        endpoints = fact_rows("selected_or_selectable_endpoints")
        modulators = fact_rows("selected_or_selectable_modulators")

        all_fact_rows = [
            *sources,
            *excitation_filters,
            *dichroics,
            *emission_filters,
            *splitters,
            *branch_selectors,
            *endpoints,
            *modulators,
        ]

        has_incomplete_or_unsupported = any(
            row.get("_cube_incomplete") or row.get("_unsupported_spectral_model")
            for row in all_fact_rows
        )

        has_unresolved_selectors = any(
            clean_text(row.get("selection_state")).lower() in {"unresolved", "selectable"}
            or (
                isinstance(row.get("available_positions"), list)
                and len(row.get("available_positions")) > 1
                and not clean_text(row.get("selected_position_key") or row.get("position_key"))
            )
            for row in all_fact_rows
        )

        has_route_specific_facts = bool(all_fact_rows)

        missing_categories = [
            label
            for label, values in (
                ("sources", sources),
                ("excitation_filters", excitation_filters),
                ("dichroics", dichroics),
                ("emission_filters", emission_filters),
                ("splitters", splitters),
                ("branch_selectors", branch_selectors),
                ("endpoints", endpoints),
            )
            if not values
        ]

        has_missing_route_optics = (
            not has_route_specific_facts
            or len(missing_categories) > 0
        )

        if has_incomplete_or_unsupported:
            actionable_note = (
                "Route optics include incomplete or unsupported spectral-model elements; "
                "use known labels/positions and report unknown cube internals explicitly."
            )
        elif has_unresolved_selectors:
            actionable_note = (
                "Route selectors have multiple available positions but no resolved position; "
                "ask for the exact selected wheel/turret/splitter slot."
            )
        elif not has_route_specific_facts:
            actionable_note = (
                "No route-specific optics were exported for this route; "
                "ask follow-up questions before planning."
            )
        else:
            actionable_note = (
                "Route optics are deterministically specified in exported route facts."
            )

        route_rows.append(
            {
                "route_id": clean_text(route.get("id")),
                "route_label": clean_text(route.get("display_label") or route.get("id")),
                "illumination_mode": clean_text(
                    route.get("illumination_mode") or route.get("id")
                ),
                "route_identity": copy.deepcopy(route.get("route_identity") or {}),
                "planning_optics": {
                    "selected_or_selectable_sources": sources,
                    "selected_or_selectable_excitation_filters": excitation_filters,
                    "selected_or_selectable_dichroics": dichroics,
                    "selected_or_selectable_emission_filters": emission_filters,
                    "selected_or_selectable_splitters": splitters,
                    "selected_or_selectable_branch_selectors": branch_selectors,
                    "selected_or_selectable_endpoints": endpoints,
                    "selected_or_selectable_modulators": modulators,
                    "highly_relevant_installed_objectives": copy.deepcopy(
                        installed_objectives
                    ),
                },
                "route_specific_vs_generic": {
                    "route_specific_facts_source": "route_optical_facts",
                    "generic_installed_hardware_reference": copy.deepcopy(
                        route.get("relevant_hardware") or {}
                    ),
                },
                "known_vs_unknown": {
                    "is_deterministic": (
                        has_route_specific_facts
                        and not has_incomplete_or_unsupported
                        and not has_unresolved_selectors
                    ),
                    "has_incomplete_or_unsupported_spectral_model": (
                        has_incomplete_or_unsupported
                    ),
                    "has_unresolved_selectors": has_unresolved_selectors,
                    "has_missing_route_optics": has_missing_route_optics,
                    "missing_categories": missing_categories,
                    "actionable_note": actionable_note,
                },
                "caveat_flags": {
                    "cube_incomplete": any(
                        bool(row.get("_cube_incomplete")) for row in all_fact_rows
                    ),
                    "unsupported_spectral_model": any(
                        bool(row.get("_unsupported_spectral_model"))
                        for row in all_fact_rows
                    ),
                },
            }
        )

    return {
        "contract_version": "route_planning_summary.v1",
        "authoritative_source": "llm_context.authoritative_route_contract.routes",
        "usage_note": (
            "Use this summary for route planning convenience, but treat "
            "llm_context.authoritative_route_contract as the source of truth."
        ),
        "routes": route_rows,
    }


def build_llm_inventory_payload(
    facility: dict[str, Any],
    instruments: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the LLM-safe experiment-planning inventory export."""
    llm_payload: dict[str, Any] = {
        "facility_name": str(
            facility.get("short_name")
            or facility.get("full_name")
            or "Core Imaging Facility"
        ),
        "facility_contact_url": str(facility.get("contact_url", "")),
        "public_site_url": str(facility.get("public_site_url", "")),
        "policy": {
            "intent": "LLM-safe experiment planning inventory",
            "grounding_requirement": (
                "Only use fields explicitly present in this JSON file."
            ),
            "llm_usage_note": (
                "Use hardware_focus_summary for quick screening, then use "
                "llm_context.authoritative_route_contract as primary route truth; "
                "llm_context.route_planning_summary is a convenience view derived "
                "from that truth. Prefer capabilities (grouped axes) and "
                "route_identity.readouts in authoritative_route_contract.routes "
                "as semantic facts; the flat modalities list is compatibility-only "
                "and must not be used as primary truth. "
                "Cite raw hardware fields only for supplemental detail."
            ),
            "do_not_infer_constraints": [
                (
                    "Do not invent hardware specifications, accessories, wavelengths, "
                    "objectives, detector performance, or automation features that are "
                    "not explicitly listed."
                ),
                (
                    "Treat null values and listed missing fields as unknown. "
                    "Unknown does not mean available."
                ),
                (
                    "When required details are missing, ask follow-up questions or "
                    "clearly state uncertainty."
                ),
            ],
        },
        "active_microscopes": [],
    }

    for inst in instruments:
        canonical_lightpath_dto = copy.deepcopy(
            inst.get("canonical_lightpath_dto")
            or inst.get("lightpath_dto")
            or {}
        )

        canonical_instrument_dto = copy.deepcopy(
            inst.get("canonical_instrument_dto")
            or inst.get("canonical")
            or {}
        )

        canonical_instrument = (
            canonical_instrument_dto.get("instrument")
            if isinstance(canonical_instrument_dto.get("instrument"), dict)
            else {}
        )

        llm_record: dict[str, Any] = {
            "id": clean_text(
                inst.get("id")
                or canonical_instrument.get("instrument_id")
            ),
            "display_name": clean_text(
                canonical_instrument.get("display_name")
                or inst.get("display_name")
            ),
            "hardware": copy.deepcopy(canonical_instrument_dto.get("hardware") or {}),
            "methods": copy.deepcopy(canonical_instrument_dto.get("methods") or {}),
            "capabilities": copy.deepcopy(canonical_instrument_dto.get("capabilities") or {}),
            "software": copy.deepcopy(canonical_instrument_dto.get("software") or []),
            "software_status": clean_text(canonical_instrument_dto.get("software_status")).lower(),
        }
        legacy_modalities = copy.deepcopy(canonical_instrument_dto.get("modalities") or [])
        if inst.get("retired") or legacy_modalities:
            llm_record["modalities"] = legacy_modalities
            llm_record["modalities_note"] = (
                "Compatibility-only flat list for retired/legacy records."
            )
        llm_record["modalities_note"] = (
            "Compatibility-only field; canonical capability semantics are carried by capabilities and route readouts."
        )
        if llm_record["software_status"] == "not_applicable":
            llm_record["software_status_caveat"] = (
                "No acquisition/control software is part of this instrument record."
            )

        known_fields, missing_fields = _collect_known_missing_paths(llm_record)

        policy = (
            canonical_instrument_dto.get("policy") or {}
            if isinstance(canonical_instrument_dto, dict)
            else {}
        )

        llm_record["inventory_completeness"] = {
            "known_fields": sorted(known_fields),
            "missing_fields": sorted(missing_fields),
            "known_field_count": len(known_fields),
            "missing_field_count": len(missing_fields),
            "policy_missing_required": copy.deepcopy(
                policy.get("missing_required") or []
            ),
            "policy_missing_conditional": copy.deepcopy(
                policy.get("missing_conditional") or []
            ),
            "alias_fallbacks": copy.deepcopy(policy.get("alias_fallbacks") or []),
            "uncertainty_note": "Missing fields are unknown and must not be assumed.",
        }

        llm_record["hardware_focus_summary"] = _build_hardware_focus_summary(
            llm_record,
            canonical_lightpath_dto,
            inventory_completeness=llm_record["inventory_completeness"],
            status=inst.get("status") if isinstance(inst.get("status"), dict) else {},
        )

        authoritative_route_contract = copy.deepcopy(
            (((canonical_lightpath_dto.get("projections") or {}).get("llm")) or {}).get(
                "authoritative_route_contract"
            )
            or {}
        )

        llm_context = (
            llm_record.get("llm_context")
            if isinstance(llm_record.get("llm_context"), dict)
            else {}
        )

        llm_context["diagnostics"] = copy.deepcopy(
            inst.get("diagnostics")
            or inst.get("dto", {}).get("diagnostics")
            or []
        )

        if any(
            not isinstance(route.get("selected_execution"), dict)
            for route in (canonical_lightpath_dto.get("light_paths") or [])
            if isinstance(route, dict)
        ):
            llm_context["diagnostics"].append(
                {
                    "severity": "error",
                    "code": "missing_selected_execution",
                    "source": "llm_export",
                }
            )

        llm_context["authoritative_route_contract"] = authoritative_route_contract

        has_missing_selected_execution = any(
            diagnostic.get("code") == "missing_selected_execution"
            for diagnostic in llm_context["diagnostics"]
            if isinstance(diagnostic, dict)
        )

        route_planning_summary = (
            {
                "status": "blocked",
                "reason": "missing_selected_execution",
            }
            if has_missing_selected_execution
            else _build_route_planning_summary(
                llm_record,
                authoritative_route_contract,
            )
        )

        llm_context["derived_summaries"] = {
            "route_planning_summary": route_planning_summary,
            "hardware_focus_summary": copy.deepcopy(
                llm_record.get("hardware_focus_summary") or {}
            ),
            "methods_summary": copy.deepcopy(
                (
                    llm_record.get("methods")
                    if isinstance(llm_record.get("methods"), dict)
                    else {}
                )
                or {}
            ),
        }

        llm_context["route_planning_summary"] = copy.deepcopy(
            llm_context["derived_summaries"]["route_planning_summary"]
        )

        llm_record["llm_context"] = llm_context
        llm_payload["active_microscopes"].append(llm_record)

    return llm_payload


__all__ = [
    "build_llm_inventory_payload",
    "_build_hardware_focus_summary",
    "_build_route_planning_summary",
]
