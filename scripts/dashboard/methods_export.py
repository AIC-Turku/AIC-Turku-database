"""Methods-generator dashboard export.

This module owns the methods-generator derived export projection.

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
from pathlib import Path
from typing import Any

import yaml

from scripts.build_context import clean_text
from scripts.dashboard.loaders import facility_short_name


class AcknowledgementConfigError(ValueError):
    """`facility.acknowledgements` cannot be applied faithfully."""


LEGACY_ACK_KEYS = ("xcelligence_addition",)

# A recorded value that only restates that the value is unknown is not an identity.
_PLACEHOLDER_IDENTITY_VALUES = {"unknown", "unknown manufacturer", "n/a", "na", "none", "-", "--", "?"}


def _build_ack_data(
    ack: dict[str, Any],
    known_instrument_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Normalize acknowledgement copy for frontend configuration.

    `standard` is added to every draft. Each `additional` entry is added only
    when one of its `instrument_ids` was used, so a funder or donor credit that
    belongs to a single instrument stays bound to that instrument's recorded ID
    rather than to a name the frontend has to recognise.
    """
    legacy = [key for key in LEGACY_ACK_KEYS if key in ack]
    if legacy:
        raise AcknowledgementConfigError(
            "facility.acknowledgements." + ", ".join(legacy) + " is no longer read. "
            "Move the text to acknowledgements.additional[] and list the "
            "instrument_ids it applies to."
        )

    raw_additional = ack.get("additional", [])
    if not isinstance(raw_additional, list):
        raise AcknowledgementConfigError(
            "facility.acknowledgements.additional must be a list"
        )

    additional: list[dict[str, Any]] = []
    for entry in raw_additional:
        if not isinstance(entry, dict):
            raise AcknowledgementConfigError(
                "facility.acknowledgements.additional[] entries must be mappings "
                "with 'text' and 'instrument_ids'"
            )
        text = entry.get("text")
        if not isinstance(text, str) or not text.strip():
            raise AcknowledgementConfigError(
                "facility.acknowledgements.additional[].text must be non-empty text"
            )
        instrument_ids = entry.get("instrument_ids")
        if (
            not isinstance(instrument_ids, list)
            or not instrument_ids
            or any(not isinstance(value, str) or not value.strip() for value in instrument_ids)
        ):
            raise AcknowledgementConfigError(
                "facility.acknowledgements.additional[].instrument_ids must be a "
                "non-empty list of instrument IDs"
            )
        # An acknowledgement that silently stops appearing because a record was
        # renamed is worse than a failed build, so unknown IDs are rejected the
        # same way `facility.non_public_instrument_ids` rejects them.
        if known_instrument_ids is not None:
            unknown = sorted({value for value in instrument_ids} - known_instrument_ids)
            if unknown:
                raise AcknowledgementConfigError(
                    "facility.acknowledgements.additional[].instrument_ids refers to "
                    "unknown instrument IDs: " + ", ".join(unknown)
                )
        additional.append(
            {
                "text": text.strip(),
                "instrument_ids": [value.strip() for value in instrument_ids],
            }
        )

    return {
        "standard": str(ack.get("standard", "")),
        "additional": additional,
    }


def build_methods_generator_page_config(
    facility: dict[str, Any],
    repo_root: Path,
    known_instrument_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Build frontend config for the methods generator page."""
    ack_override_path = repo_root / "acknowledgements.yaml"

    if ack_override_path.is_file():
        with ack_override_path.open(encoding="utf-8") as handle:
            override_ack = yaml.safe_load(handle.read()) or {}

        if not isinstance(override_ack, dict):
            override_ack = {}

        ack_data = _build_ack_data(override_ack, known_instrument_ids)
    else:
        facility_ack = (
            facility.get("acknowledgements", {})
            if isinstance(facility.get("acknowledgements"), dict)
            else {}
        )
        ack_data = _build_ack_data(facility_ack, known_instrument_ids)

    methods_config = (
        facility.get("methods_generator", {})
        if isinstance(facility.get("methods_generator"), dict)
        else {}
    )

    return {
        "output_title": str(
            methods_config.get("output_title", "Light Microscopy Methods")
        ),
        "instrument_data_url": str(
            methods_config.get(
                "instrument_data_url",
                "../assets/instruments_data.json",
            )
        ),
        "acknowledgements": ack_data,
    }


def build_plan_experiments_page_config(facility: dict[str, Any]) -> dict[str, Any]:
    """Build frontend config for the experiment-planning page."""
    planner_config = (
        facility.get("plan_experiments", {})
        if isinstance(facility.get("plan_experiments"), dict)
        else {}
    )

    short_name = facility_short_name(facility)
    facility_contact_url = str(facility.get("contact_url", "#"))

    return {
        "facility_short_name": short_name,
        "facility_contact_url": facility_contact_url,
        "facility_contact_label": str(
            planner_config.get(
                "contact_button_label",
                f"Contact {short_name} Staff",
            )
        ),
        "llm_inventory_asset_url": str(
            planner_config.get(
                "llm_inventory_asset_url",
                "assets/llm_inventory.json",
            )
        ),
    }


# Route facts about a source, detector or endpoint say only that the component sits
# on the route. `selected_execution._derive_selection_state` returns "fixed" for every
# one of them unconditionally, so "fixed" on these collections is route membership,
# not evidence that the component was used for a particular acquisition.
_ROUTE_MEMBERSHIP_FACT_KEYS = frozenset(
    {
        "selected_or_selectable_sources",
        "selected_or_selectable_endpoints",
    }
)

# For an optical element, "fixed" means the element has no selectable position, so
# light on this route must traverse exactly this component. That is a genuine
# route-implied fact and may be reported.
_ROUTE_FIXED_SELECTION_STATES = frozenset({"selected", "resolved"})


def _has_explicit_route_fact_selection(row: dict[str, Any], fact_key: str = "") -> bool:
    """Return True only when a route fact records an item used for this acquisition.

    The route view intentionally contains `selected_or_selectable_*` collections.
    Those are useful for planning, but a Methods draft must not turn availability
    into an acquisition claim.  Keep only facts with explicit selection evidence;
    acquisition-specific simulator selections are reported separately from the
    reviewed runtime snapshot.

    A row that still offers alternatives is never evidence, whatever its
    ``selection_state`` says: if the record knows the element has other positions,
    the one that was used has not been established.
    """
    if row.get("available_positions"):
        return False

    selection_state = clean_text(row.get("selection_state")).lower()
    has_selected_position = bool(
        clean_text(row.get("selected_position_key") or row.get("selected_position_id"))
    )

    if fact_key in _ROUTE_MEMBERSHIP_FACT_KEYS:
        # Only an explicit per-acquisition selection promotes one of these.
        return selection_state == "selected" or has_selected_position

    if selection_state in _ROUTE_FIXED_SELECTION_STATES:
        return True
    if has_selected_position:
        return True
    # A single-position element on a flattened fixed route is unavoidable, so the
    # route itself is the evidence. An element that merely lacks a recorded
    # position is not.
    if selection_state == "fixed" and clean_text(
        row.get("position_key") or row.get("position_id")
    ):
        return True
    return False


def _strip_route_fact_alternatives(row: dict[str, Any]) -> dict[str, Any]:
    """Remove availability collections from a fact that survived grounding.

    Publication prose must never enumerate positions that were not used, even
    alongside one that was.
    """
    row.pop("available_positions", None)
    row.pop("selectable_positions", None)
    return row


def _acquisition_software_sentence(dto: dict[str, Any]) -> str:
    """Offer the recorded acquisition software as a confirmable statement."""
    software = dto.get("software") if isinstance(dto.get("software"), list) else []
    for row in software:
        if not isinstance(row, dict):
            continue
        if clean_text(row.get("role")).lower() != "acquisition":
            continue
        name = clean_text(row.get("name"))
        if not name or name.lower() in _PLACEHOLDER_IDENTITY_VALUES:
            continue
        version = clean_text(row.get("version"))
        label = f"{name} (v{version})" if version else name
        suffix = "" if version else " [PLEASE SPECIFY: acquisition software version]"
        return f"Instrument control and image acquisition were performed using {label}.{suffix}"
    return ""


def _microscope_sentence(dto: dict[str, Any]) -> str:
    """Name the microscope from every identity field the record holds.

    Manufacturer, model and stand orientation are canonical instrument facts, not
    acquisition settings, so a draft that drops them makes the instrument harder to
    identify than the record allows. Acquisition software is deliberately excluded:
    the record describes the software installed now, which is an acquisition-time
    claim the user must confirm, not an instrument identity.
    """
    display_name = clean_text(dto.get("display_name"))
    if not display_name:
        return "[PLEASE VERIFY: microscope identity is missing from the facility record]."

    identity = dto.get("identity") if isinstance(dto.get("identity"), dict) else {}
    manufacturer = clean_text(identity.get("manufacturer"))
    model = clean_text(identity.get("model"))
    stand = identity.get("stand_orientation") if isinstance(identity.get("stand_orientation"), dict) else {}
    stand_label = clean_text(stand.get("display_label")).lower()

    reference = " ".join(part for part in (manufacturer, model) if part).strip()
    normalized_name = display_name.lower()
    reference_clause = (
        f" ({reference})"
        if reference and reference.lower() not in normalized_name
        else ""
    )

    # "other"/"unknown" is a vocabulary placeholder, not a description of the stand.
    if stand_label in {"other", "unknown", "not applicable"}:
        stand_label = ""

    if stand_label and stand_label not in normalized_name:
        article = "an" if stand_label[:1] in {"a", "e", "i", "o", "u"} else "a"
        return (
            f"Images were acquired using the {display_name}{reference_clause}, "
            f"{article} {stand_label} microscope."
        )
    return f"Images were acquired using the {display_name}{reference_clause}."


def _ground_methods_projection(dto: dict[str, Any]) -> None:
    """Constrain the methods projection to acquisition-safe deterministic facts.

    This is a boundary between a planning-capability DTO and publication prose.
    It deliberately removes route alternatives and generic advice that are useful
    elsewhere but should not read as facts about a particular acquisition.
    """
    methods = dto.get("methods") if isinstance(dto.get("methods"), dict) else {}
    dto["methods"] = methods

    methods["base_sentence"] = _microscope_sentence(dto)
    # The record documents the software installed now, which is an acquisition-time
    # claim rather than an instrument identity. Offer it as something the user can
    # confirm instead of asserting it or pretending it is unrecorded.
    methods["acquisition_software_sentence"] = _acquisition_software_sentence(dto)
    # A retired record describes the instrument as it was last configured, which is
    # a caveat on the whole draft. It belongs in the review block, not spliced into
    # the sentence other facts are composed onto.
    methods["retired_review_prompt"] = (
        "[PLEASE VERIFY: this instrument is recorded as retired; confirm the configuration "
        "that was in use at the time of acquisition]"
        if dto.get("retired")
        else ""
    )
    methods["acquisition_settings_recommendation"] = (
        "[PLEASE SPECIFY: acquisition software/version (if applicable), exposure "
        "time(s), excitation power(s), detector gain/offset, binning, zoom/averaging, "
        "pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable]."
    )
    # These are useful guidance, not acquisition facts. Keeping them in the page
    # documentation is preferable to appending them to every publication draft.
    methods["nyquist_recommendation"] = ""
    methods["data_deposition_recommendation"] = ""

    optical_path = (
        dto.get("hardware", {}).get("optical_path", {})
        if isinstance(dto.get("hardware"), dict)
        and isinstance(dto.get("hardware", {}).get("optical_path"), dict)
        else {}
    )
    route_contract = (
        optical_path.get("authoritative_route_contract", {})
        if isinstance(optical_path.get("authoritative_route_contract"), dict)
        else {}
    )
    routes = route_contract.get("routes") if isinstance(route_contract.get("routes"), list) else []

    removed_nonselected_fact = False
    for route in routes:
        if not isinstance(route, dict):
            continue
        route_facts = route.get("route_optical_facts")
        if not isinstance(route_facts, dict):
            continue
        for key, rows in list(route_facts.items()):
            if not key.startswith("selected_or_selectable_") or not isinstance(rows, list):
                continue
            selected_rows = [
                _strip_route_fact_alternatives(copy.deepcopy(row))
                for row in rows
                if isinstance(row, dict) and _has_explicit_route_fact_selection(row, key)
            ]
            if len(selected_rows) != len(rows):
                removed_nonselected_fact = True
            route_facts[key] = selected_rows

    if removed_nonselected_fact and not methods.get(
        "quarep_light_path_recommendation_needed"
    ):
        methods["quarep_light_path_recommendation_needed"] = True
        methods["quarep_light_path_recommendation"] = (
            "[PLEASE VERIFY: the instrument record contains light-path options that were not "
            "selected for this acquisition; confirm the exact filters, dichroics, "
            "splitters, and detector path actually used]."
        )


def build_methods_generator_instrument_export(inst: dict[str, Any]) -> dict[str, Any]:
    """Build methods export DTO from canonical instrument + canonical light-path DTOs.

    Methods export must not infer undocumented capabilities. Missing canonical fields
    are surfaced as diagnostics instead of invented fallback text.
    """
    canonical = copy.deepcopy(
        inst.get("canonical_instrument_dto")
        or inst.get("canonical")
        or {}
    )
    lightpath = copy.deepcopy(
        inst.get("canonical_lightpath_dto")
        or inst.get("lightpath_dto")
        or {}
    )

    canonical_instrument = (
        canonical.get("instrument")
        if isinstance(canonical.get("instrument"), dict)
        else {}
    )

    dto: dict[str, Any] = copy.deepcopy(inst.get("dto") if isinstance(inst.get("dto"), dict) else {})
    dto["id"] = clean_text(
        inst.get("id")
        or canonical_instrument.get("instrument_id")
        or dto.get("id")
    )
    dto["display_name"] = clean_text(
        inst.get("display_name")
        or canonical_instrument.get("display_name")
        or dto.get("display_name")
    )

    diagnostics: list[dict[str, str]] = []

    canonical_hardware = (
        canonical.get("hardware")
        if isinstance(canonical.get("hardware"), dict)
        else {}
    )
    canonical_software = (
        canonical.get("software")
        if isinstance(canonical.get("software"), list)
        else []
    )
    software_status = clean_text(canonical.get("software_status")).lower()

    if not canonical_hardware:
        diagnostics.append(
            {
                "severity": "warning",
                "code": "missing_canonical_hardware",
                "path": "canonical.hardware",
                "message": "missing in DTO: canonical.hardware",
                "source": "methods_export",
                "affected_export": "methods",
            }
        )

    if not canonical_software and software_status != "not_applicable":
        diagnostics.append(
            {
                "severity": "warning",
                "code": "missing_canonical_software",
                "path": "canonical.software",
                "message": "missing in DTO: canonical.software",
                "source": "methods_export",
                "affected_export": "methods",
            }
        )

    canonical_routes = [
        {
            "id": clean_text(route.get("id")),
            "display_label": clean_text(
                route.get("name")
                or route.get("display_label")
                or route.get("id")
            ),
            "route_order": index,
            "route_type": clean_text(route.get("route_type")) or clean_text(route.get("id")),
            "readouts": [clean_text(r) for r in (route.get("readouts") or []) if isinstance(r, str) and clean_text(r)],
        }
        for index, route in enumerate(lightpath.get("light_paths") or [])
        if isinstance(route, dict) and clean_text(route.get("id"))
    ]

    if not canonical_routes:
        diagnostics.append(
            {
                "severity": "warning",
                "code": "missing_canonical_routes",
                "path": "lightpath_dto.light_paths",
                "message": "missing in DTO: lightpath_dto.light_paths",
                "source": "methods_export",
                "affected_export": "methods",
            }
        )

    if any(
        not isinstance(route.get("selected_execution"), dict)
        for route in (lightpath.get("light_paths") or [])
        if isinstance(route, dict)
    ):
        diagnostics.append(
            {
                "severity": "error",
                "code": "missing_selected_execution",
                "path": "lightpath_dto.light_paths[].selected_execution",
                "message": "missing in DTO: selected_execution.selected_route_steps",
                "source": "methods_export",
                "affected_export": "methods",
            }
        )

    methods_view_dto = {
        "objectives": copy.deepcopy(canonical_hardware.get("objectives") or []),
        "detectors": copy.deepcopy(canonical_hardware.get("detectors") or []),
        "light_sources": copy.deepcopy(
            canonical_hardware.get("sources")
            or canonical_hardware.get("light_sources")
            or []
        ),
        "software": copy.deepcopy(canonical_software),
        "software_status": software_status,
        "routes": canonical_routes,
        "diagnostics": diagnostics,
    }

    dto["methods_generation"] = copy.deepcopy(inst.get("methods_generation") or {})
    dto["methods_view_dto"] = methods_view_dto
    # Keep methods-specific DTO explicit while also exporting top-level fields
    # required by methods_generator_app.js runtime contract.
    dto["objectives"] = copy.deepcopy(methods_view_dto["objectives"])
    dto["detectors"] = copy.deepcopy(methods_view_dto["detectors"])
    dto["light_sources"] = copy.deepcopy(methods_view_dto["light_sources"])
    dto["software"] = copy.deepcopy(methods_view_dto["software"])
    dto["capabilities"] = copy.deepcopy((canonical.get("capabilities") if isinstance(canonical.get("capabilities"), dict) else {}))
    dto["routes"] = copy.deepcopy(methods_view_dto["routes"])
    dto["diagnostics"] = copy.deepcopy(methods_view_dto["diagnostics"])

    # Runtime-selected optical truth is exported on the DTO and should be the
    # primary source for methods text when present. localStorage is fallback-only.
    dto["runtime_selected_configuration"] = (
        None
        if any(diagnostic.get("code") == "missing_selected_execution" for diagnostic in diagnostics)
        else copy.deepcopy(inst.get("runtime_selected_configuration"))
    )

    _ground_methods_projection(dto)
    return dto


__all__ = [
    "AcknowledgementConfigError",
    "build_methods_generator_page_config",
    "build_plan_experiments_page_config",
    "build_methods_generator_instrument_export",
]
