"""Validate the separate spare pool and build its explicitly non-installed view.

YAML -> JSON Schema + semantic checks -> canonical pool -> page / dedicated JSON.
Never append these records to instrument hardware, methods or simulator exports.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from ruamel.yaml import YAML


class ObjectivePoolError(ValueError):
    """Invalid inventory; safe to display as a build diagnostic."""


def pool_schema(repo_root: Path) -> dict:
    return json.loads((repo_root / "schema/objective_pool.schema.json").read_text(encoding="utf-8"))


def validate_pool(data: object, schema: dict) -> None:
    """Reject contradictory state; missing local facts must be explicit nulls."""
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data),
                    key=lambda error: str(list(error.absolute_path)))
    if errors:
        raise ObjectivePoolError("; ".join(
            f"{'.'.join(map(str, error.absolute_path)) or 'root'}: {error.message}" for error in errors))
    assert isinstance(data, dict)

    def check_strings(node):
        if isinstance(node, str) and not node.strip():
            raise ObjectivePoolError("Blank strings are not known facts; use null for missing values.")
        if isinstance(node, dict):
            for value in node.values():
                check_strings(value)
        elif isinstance(node, list):
            for value in node:
                check_strings(value)

    check_strings(data)
    families = [row["id"] for row in data["families"]]
    ids = [row["id"] for row in data["items"]]
    if len(families) != len(set(families)) or len(ids) != len(set(ids)):
        raise ObjectivePoolError("Family and item IDs must be unique.")
    for item in data["items"]:
        identifier = item["id"]
        if item["family_id"] not in families:
            raise ObjectivePoolError(f"{identifier}: unknown family_id {item['family_id']}")
        if item["magnification"] is not None and not math.isfinite(item["magnification"]):
            raise ObjectivePoolError(f"{identifier}: magnification must be finite.")
        na = item["numerical_aperture_text"]
        if na is not None and any(not 0 < float(part) <= 2 for part in na.split("-")):
            raise ObjectivePoolError(f"{identifier}: numerical aperture must be in (0, 2].")
        if item["condition"] in {"reported_issue", "reported_unusable"} and not (item["condition_note"] or "").strip():
            raise ObjectivePoolError(f"{identifier}: a reported problem needs its condition_note.")
        if item["condition"] == "verified_serviceable" and item["inspection"] is None:
            raise ObjectivePoolError(f"{identifier}: checked serviceable needs an inspection date and person.")
        if item["availability"] == "available" and item["condition"] != "verified_serviceable":
            raise ObjectivePoolError(f"{identifier}: availability requires a serviceability check, not absence of a fault note.")


def load_objective_pool(repo_root: Path) -> dict:
    """Load canonical records, rejecting duplicate YAML keys and malformed data."""
    path = repo_root / "inventory/objective_pool.yaml"
    try:
        loader = YAML(typ="safe")
        loader.allow_duplicate_keys = False
        with path.open(encoding="utf-8") as handle:
            data = loader.load(handle)
        validate_pool(data, pool_schema(repo_root))
    except ObjectivePoolError:
        raise
    except Exception as error:
        raise ObjectivePoolError(f"{path}: {error}") from error
    return copy.deepcopy(data)


def _labels(schema: dict, name: str) -> dict[str, str]:
    return {row["const"]: row["title"] for row in schema["$defs"][name]["oneOf"]}


def staff_contact_url(facility: dict) -> str | None:
    """A config value is not permission to embed arbitrary script URLs."""
    value = facility.get("contact_url")
    if not isinstance(value, str):
        return None
    value = value.strip()
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    return value if parsed.scheme in {"https", "http"} and parsed.netloc else None


def build_objective_pool_view(pool: dict, schema: dict, facility: dict | None = None) -> dict:
    """Pure projection: formatted fields and enquiry text, no compatibility guesses."""
    validate_pool(pool, schema)
    labels = {key: _labels(schema, key) for key in ("kind", "immersion", "condition", "availability")}
    facility_cfg = facility or {}
    facility_name = str(
        facility_cfg.get("short_name")
        or facility_cfg.get("full_name")
        or "imaging facility"
    ).strip()
    family_index = {row["id"]: row for row in pool["families"]}
    items = []
    for index, item in enumerate(pool["items"]):
        family = family_index[item["family_id"]]
        row = copy.deepcopy(item)
        row.update({"order": index, "family_label": family["label"],
                    "mount_label": family["mount_text"] or "Not recorded",
                    "source_heading": family["source_heading"],
                    "magnification_label": f"{item['magnification']:g}x" if item["magnification"] is not None else "Not recorded"})
        for key, mapping in labels.items():
            row[f"{key}_label"] = mapping[item[key]]
        row["has_reported_problem"] = item["condition"] in {"reported_issue", "reported_unusable"}
        row["condition_description"] = {
            "not_assessed": "No problem noted in the source; this is not a serviceability check.",
            "reported_issue": "Do not use until staff have reviewed the reported problem.",
            "reported_unusable": "Recorded as unusable. Not offered for imaging.",
            "verified_serviceable": "Serviceability checked; microscope suitability still requires staff approval.",
        }[item["condition"]]
        row["search_text"] = " ".join(str(value) for value in [
            row["id"], row["family_label"], row["name"], row["product_code"] or "",
            row["source_text"], row["mount_label"], row["immersion_label"],
            row["kind_label"], row["condition_label"], row["magnification_label"],
            row["condition_note"] or ""])
        purpose = ("Could you advise on the status of this reported-unusable item?"
                   if item["condition"] == "reported_unusable" else
                   "Could you check whether this item is available and suitable for my experiment?")
        row["enquiry"] = "\n".join([
            f"Hi {facility_name} team,", purpose,
            f"Item: {family['label']} {item['name']}",
            f"Pool record: {item['id']}; product code: {item['product_code'] or 'not recorded'}",
            f"Recorded condition: {row['condition_label']}",
            f"Condition note: {item['condition_note'] or row['condition_description']}",
            f"Availability: {row['availability_label']}",
            "Microscope: [please enter]", "Experiment and planned date: [please enter]",
            "Please confirm compatibility and arrange any installation. Thank you.",
        ])
        items.append(row)
    return {
        "schema_version": pool["schema_version"], "inventory_kind": "objective_pool",
        "installed_hardware": False, "compatibility_status": "not_verified",
        "source": copy.deepcopy(pool["source"]), "families": copy.deepcopy(pool["families"]),
        "filters": {key: [{"id": k, "label": v} for k, v in mapping.items()
                          if any(row[key] == k for row in items)] for key, mapping in labels.items()},
        "items": items, "total": len(items),
        "objective_count": sum(row["kind"] == "objective" for row in items),
        "problem_count": sum(row["has_reported_problem"] for row in items),
    }
