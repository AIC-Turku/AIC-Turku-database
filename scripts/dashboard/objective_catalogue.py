"""Read-only catalogue joining canonical microscope objectives and the spare pool.

Association is not stock, compatibility, serviceability or physical asset identity.
No source records or installed-hardware exports are mutated by this projection.
"""
from __future__ import annotations

import copy
import json
import math
from urllib.parse import quote

from scripts.dashboard.instrument_view import vocab_label


class ObjectiveCatalogueError(ValueError):
    """Catalogue input cannot be represented faithfully."""


INSTALLATION_LABELS = {
    "installed": "Installed - as recorded",
    "not_installed": "Associated - not installed",
    "unconfirmed": "Installation unconfirmed",
}


def excluded_instruments(facility: dict, known_ids: set[str]) -> set[str]:
    """Explicit presentation exclusions, never inferred from model names."""
    config = facility.get("objective_catalogue", {})
    if not isinstance(config, dict) or set(config) - {"exclude_instrument_ids"}:
        raise ObjectiveCatalogueError("objective_catalogue: expected exclude_instrument_ids only")
    values = config.get("exclude_instrument_ids", [])
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise ObjectiveCatalogueError("objective_catalogue.exclude_instrument_ids must be a list of instrument IDs")
    if len(values) != len(set(values)) or set(values) - known_ids:
        raise ObjectiveCatalogueError("objective_catalogue exclusions must be unique, known instrument IDs")
    return set(values)


def _text(value) -> str:
    return str(value).strip() if value is not None else ""


def _number(value) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) and number > 0 else None
    except (TypeError, ValueError):
        return None


def instrument_catalogue_link(instrument_id: str) -> str:
    # Keep the existing public path so previously shared pool links continue working.
    return "../../objective_pool.md?instrument=" + quote(instrument_id, safe="")


def build_objective_catalogue_view(pool: dict, instruments: list[dict], vocabulary,
                                  facility: dict | None = None) -> dict:
    """Join validated views, preserving each source record and boolean/null state.

    `instruments` are loader/build records containing their canonical instrument DTO.
    A product code is deliberately never used as a record key or deduplication key.
    """
    facility = facility or {}
    known_ids = {inst["canonical"]["instrument"]["instrument_id"] for inst in instruments}
    excluded = excluded_instruments(facility, known_ids)
    rows = []
    instrument_options = []
    for inst in sorted(instruments, key=lambda item: item["canonical"]["instrument"]["display_name"].casefold()):
        canonical = inst["canonical"]
        identity = canonical["instrument"]
        instrument_id = identity["instrument_id"]
        if instrument_id in excluded:
            continue
        objectives = canonical.get("hardware", {}).get("objectives", [])
        if not objectives:
            continue
        retired = inst.get("retired") is True
        instrument_name = identity["display_name"]
        instrument_options.append({"id": instrument_id, "label": instrument_name,
                                   "retired": retired})
        for objective in objectives:
            objective_id = _text(objective.get("id"))
            if not objective_id:
                raise ObjectiveCatalogueError(f"{instrument_id}: objective needs a stable source ID")
            installed = objective.get("is_installed")
            if installed is not None and type(installed) is not bool:
                raise ObjectiveCatalogueError(f"{instrument_id}/{objective_id}: is_installed must be boolean or unknown")
            state = "installed" if installed is True else "not_installed" if installed is False else "unconfirmed"
            manufacturer = _text(objective.get("manufacturer"))
            immersion = _text(objective.get("immersion"))
            mag = _number(objective.get("magnification"))
            identifier = f"objective-{quote(instrument_id, safe='')}--{quote(objective_id, safe='')}"
            row = {
                "id": identifier, "source_kind": "instrument", "instrument_id": instrument_id,
                "objective_id": objective_id, "instrument_name": instrument_name,
                "instrument_url": f"../instruments/{quote(instrument_id, safe='')}/#objectives",
                "retired": retired, "is_installed": installed,
                "installation_status": state, "installation_label": INSTALLATION_LABELS[state],
                "association_label": ("Historical record: " if retired else "") + INSTALLATION_LABELS[state],
                "name": _text(objective.get("model")) or "Model not recorded",
                "product_code": objective.get("product_code"), "kind": "objective", "kind_label": "Objective",
                "family_id": manufacturer.casefold() or "not_recorded",
                "family_label": manufacturer or "Manufacturer not recorded",
                "magnification": mag, "magnification_label": f"{mag:g}x" if mag is not None else "Not recorded",
                "numerical_aperture_text": _text(objective.get("numerical_aperture")),
                "immersion": immersion or "not_recorded", "immersion_filter": immersion or "not_recorded",
                "immersion_label": vocab_label(vocabulary, "objective_immersion", immersion) if immersion else "Not recorded",
                "working_distance_text": _text(objective.get("working_distance")),
                "working_distance_label": _text(objective.get("working_distance")) or "Not recorded",
                "working_distance_heading": "Working distance (as recorded)",
                "mount_label": None, "availability": "unconfirmed", "availability_label": "Ask staff; not a loan offer",
                "condition": "not_assessed", "condition_label": "Not assessed by this catalogue",
                "condition_note": None, "has_reported_problem": False,
                "condition_description": "Installation status is not a serviceability check. See the microscope record and staff for current status.",
                "notes": _text(objective.get("notes")), "location": identity.get("location") or None,
                "quantity": None, "inspection": None,
                "source_heading": f"Microscope record: {instrument_id}; objective: {objective_id}",
                "source_text": json.dumps(objective, ensure_ascii=False, indent=2),
                "source_record": {"instrument_id": instrument_id, "objective_id": objective_id,
                                  "field": "hardware.objectives", "objective": copy.deepcopy(objective)},
                "enquiry": None,
            }
            rows.append(row)

    for item in pool["items"]:
        row = copy.deepcopy(item)
        wd_unit = pool["source"]["working_distance_unit"]
        row.update({
            "source_kind": "spare_pool", "instrument_id": "", "instrument_name": None,
            "instrument_url": None, "retired": False, "is_installed": None,
            "installation_status": "pool_listing", "installation_label": "Not established by pool listing",
            "association_label": "Spare-pool listing", "notes": "",
            "working_distance_heading": "Working distance" + (" (unit unconfirmed)" if not wd_unit else ""),
            "working_distance_label": (item["working_distance_text"] + (" " + wd_unit if wd_unit else ""))
                if item["working_distance_text"] else "Not recorded",
            # Display-only grouping: the source's Dry label/value stays intact on the card and in JSON.
            "immersion_filter": "air" if item["immersion"] == "dry" else item["immersion"],
        })
        rows.append(row)

    if len({row["id"] for row in rows}) != len(rows):
        raise ObjectiveCatalogueError("Catalogue record IDs must be unique; duplicate source IDs cannot be silently merged")
    for index, row in enumerate(rows):
        row["order"] = index
        # Fragment URLs must encode percent signs in the stable DOM record ID.
        row["anchor"] = quote(row["id"], safe="")
        row["search_text"] = " ".join(_text(row.get(key)) for key in (
            "id", "family_label", "name", "product_code", "source_text", "mount_label",
            "immersion_label", "kind_label", "condition_label", "magnification_label", "condition_note",
            "instrument_name", "association_label", "location", "notes"))

    def options(key, label_key):
        labels = {}
        for row in rows:
            labels.setdefault(row[key], row[label_key])
        return [{"id": key, "label": label} for key, label in sorted(labels.items(), key=lambda item: item[1].casefold())]

    immersion_options = options("immersion_filter", "immersion_label")
    for option in immersion_options:
        if option["id"] == "air":
            option["label"] = "Air / dry"
    return {
        "schema_version": 1, "inventory_kind": "objective_catalogue",
        "record_semantics": "source_records_not_physical_assets", "authoritative_for_installation": False,
        "source": copy.deepcopy(pool["source"]), "items": rows, "instruments": instrument_options,
        "excluded_instrument_ids": sorted(excluded), "families": options("family_id", "family_label"),
        "filters": {"immersion": immersion_options, "condition": options("condition", "condition_label"),
                    "kind": options("kind", "kind_label"),
                    "installation_status": [{"id": key, "label": value} for key, value in INSTALLATION_LABELS.items()]},
        "total": len(rows), "current_count": sum(not row["retired"] for row in rows),
        "historical_count": sum(row["retired"] for row in rows),
        "instrument_count": sum(row["source_kind"] == "instrument" and not row["retired"] for row in rows),
        "spare_count": len(pool["items"]), "objective_count": sum(row["kind"] == "objective" for row in rows),
        "problem_count": pool["problem_count"],
    }
