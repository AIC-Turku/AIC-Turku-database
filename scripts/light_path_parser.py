"""Utilities for validating and serializing microscope light-path definitions.

The virtual microscope consumes a validated, normalized hardware payload generated from
instrument YAML. This module keeps that payload browser-friendly while preserving enough
metadata for route-aware spectral simulation.

Identity field semantics used by parser payloads:
- manufacturer: company/vendor/brand that makes a component
- model: vendor-facing model/designation (primary structured identity)
- product_code: explicit catalog/order/SKU/reference code only, never inferred
- name: local/display instance label for UI context
"""

from __future__ import annotations

import json
import re
from itertools import product
from typing import Any

from scripts.display_labels import (
    VocabLookup,
    resolve_component_type_label,
    resolve_light_source_kind_label,
    resolve_route_label,
    resolve_stage_role_label,
)


DICHROIC_TYPES = {"dichroic", "multiband_dichroic", "polychroic"}
NO_WAVELENGTH_TYPES = {"empty", "mirror", "block", "passthrough", "neutral_density"}
ROUTE_TAGS = {"epi", "widefield_fluorescence", "tirf", "confocal", "confocal_point", "confocal_spinning_disk", "multiphoton", "light_sheet", "transmitted", "transmitted_brightfield", "phase_contrast", "darkfield", "dic", "reflected_brightfield", "optical_sectioning", "spectral_imaging", "flim", "fcs", "ism", "smlm", "spt", "fret", "shared", "all"}
ROUTE_LABELS = {
    "confocal": "Confocal",
    "confocal_point": "Point-Scanning Confocal",
    "confocal_spinning_disk": "Spinning-Disk Confocal",
    "epi": "Epi-fluorescence",
    "widefield_fluorescence": "Epi-fluorescence",
    "tirf": "TIRF",
    "multiphoton": "Multiphoton",
    "light_sheet": "Light Sheet",
    "transmitted": "Transmitted light",
    "transmitted_brightfield": "Transmitted Brightfield",
    "phase_contrast": "Phase Contrast",
    "darkfield": "Darkfield",
    "dic": "DIC",
    "reflected_brightfield": "Reflected Brightfield",
    "optical_sectioning": "Optical Sectioning",
    "spectral_imaging": "Spectral Imaging",
    "flim": "FLIM",
    "fcs": "FCS",
    "ism": "ISM",
    "smlm": "SMLM",
    "spt": "SPT",
    "fret": "FRET",
}
ROUTE_SORT_ORDER = ("confocal", "confocal_point", "confocal_spinning_disk", "epi", "widefield_fluorescence", "tirf", "multiphoton", "light_sheet", "transmitted", "transmitted_brightfield", "phase_contrast", "darkfield", "dic", "reflected_brightfield", "optical_sectioning", "spectral_imaging", "flim", "fcs", "ism", "smlm", "spt", "fret")
CUBE_LINK_KEYS = ("excitation_filter", "dichroic", "emission_filter")
CAMERA_DETECTOR_KINDS = {"camera", "scmos", "cmos", "ccd", "emccd"}
POINT_DETECTOR_KINDS = {"pmt", "gaasp_pmt", "hyd", "apd", "spad"}
POWER_VALUE_RE = re.compile(r"(\d+(?:\.\d+)?)")
CANONICAL_ENDPOINT_COLLECTION_KEYS = ("endpoints", "terminals", "detection_endpoints")
ENDPOINT_CAPABLE_INVENTORY_KEYS = ("detectors", "eyepieces")
SEQUENCE_TOPOLOGY_KEYS = ("source_id", "optical_path_element_id", "endpoint_id", "branches")

# Module-level vocabulary context set by generate_virtual_microscope_payload()
# so deeply nested helpers can resolve vocab-backed display labels without
# requiring every internal function to accept a vocab parameter.
_active_vocab: VocabLookup | None = None


def _resolve_route_label(route_id: str, explicit_name: str | None = None) -> str:
    """Resolve a display label for a route id using vocab or ROUTE_LABELS fallback."""
    if explicit_name:
        return explicit_name
    if _active_vocab is not None:
        return resolve_route_label(route_id, _active_vocab)
    return ROUTE_LABELS.get(route_id, route_id.replace("_", " ").title())


def _resolve_component_type_label(component_type: str) -> str:
    """Resolve a display label for a component type via vocab or fallback."""
    if _active_vocab is not None:
        return resolve_component_type_label(component_type, _active_vocab)
    return component_type.replace("_", " ").title()


def _resolve_light_source_kind(kind: str) -> str:
    """Resolve a display label for a light source kind via vocab or fallback."""
    if _active_vocab is not None:
        return resolve_light_source_kind_label(kind, _active_vocab)
    return kind.replace("_", " ")


_CUBE_LINK_LABELS = {
    "excitation_filter": "Excitation Filter",
    "dichroic": "Dichroic",
    "emission_filter": "Emission Filter",
}


def _resolve_cube_link_label(link_key: str) -> str:
    """Resolve a display label for a filter cube link key."""
    return _CUBE_LINK_LABELS.get(link_key, link_key.replace("_", " ").title())


def _is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _coerce_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _format_numeric(value: Any) -> str:
    numeric = _coerce_number(value)
    if numeric is None:
        return str(value)
    return str(int(numeric)) if float(numeric).is_integer() else str(numeric)


def _clean_string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _coerce_slot_key(value: Any) -> int | None:
    """Normalize mechanism/cube position keys from legacy YAML spellings.

    Existing ledgers use both integer keys and labels such as ``Pos_1``. The
    parser/runtime should preserve the mechanical slot order rather than drop
    these positions during normalization.
    """

    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        if cleaned.isdigit():
            return int(cleaned)
        match = re.search(r"(\d+)$", cleaned)
        if match:
            return int(match.group(1))
    return None


def _iter_mechanisms(light_path: dict[str, Any], stage_key: str) -> list[dict[str, Any]]:
    raw_mechanisms = light_path.get(stage_key, [])
    if isinstance(raw_mechanisms, list):
        return [entry for entry in raw_mechanisms if isinstance(entry, dict)]
    if isinstance(raw_mechanisms, dict):
        return [
            entry
            for _, entry in sorted(raw_mechanisms.items(), key=lambda item: str(item[0]))
            if isinstance(entry, dict)
        ]
    return []


def _collect_splitters(hardware: dict[str, Any], light_path: dict[str, Any]) -> list[dict[str, Any]]:
    splitters: list[dict[str, Any]] = []
    nested = light_path.get("splitters", [])
    top_level = hardware.get("splitters", [])
    for collection in (nested, top_level):
        if not isinstance(collection, list):
            continue
        for entry in collection:
            if isinstance(entry, dict):
                splitters.append(entry)
    return splitters



def _collect_endpoint_rows(hardware: dict[str, Any], light_path: dict[str, Any]) -> list[dict[str, Any]]:
    endpoints: list[dict[str, Any]] = []
    for collection in (
        light_path.get("endpoints", []),
        light_path.get("terminals", []),
        light_path.get("detection_endpoints", []),
        hardware.get("endpoints", []),
        hardware.get("terminals", []),
        hardware.get("detection_endpoints", []),
    ):
        if not isinstance(collection, list):
            continue
        for entry in collection:
            if isinstance(entry, dict):
                endpoints.append(entry)
    return endpoints


def _endpoint_capable_row_id(entry: dict[str, Any], source_section: str, index: int) -> str:
    return (
        _clean_identifier(
            entry.get("id")
            or entry.get("terminal_id")
            or entry.get("channel_name")
            or entry.get("display_label")
            or entry.get("name")
            or entry.get("model")
        )
        or f"{source_section.rstrip('s')}_{index}"
    )


def _normalize_endpoint_capable_row(
    endpoint: dict[str, Any],
    *,
    source_section: str,
    index: int,
) -> dict[str, Any]:
    entry = dict(endpoint)
    entry_id = _endpoint_capable_row_id(entry, source_section, index)
    entry["id"] = entry_id
    entry["source_section"] = source_section
    entry["endpoint_origin"] = "inventory" if source_section in ENDPOINT_CAPABLE_INVENTORY_KEYS else "explicit"
    entry["endpoint_type"] = _normalize_endpoint_type(
        entry.get("endpoint_type")
        or ("detector" if source_section == "detectors" else "eyepiece" if source_section == "eyepieces" else "")
        or entry.get("type")
        or entry.get("kind")
        or source_section
    )
    display_label = _clean_string(
        entry.get("display_label")
        or entry.get("channel_name")
        or entry.get("name")
        or entry.get("model")
        or entry.get("id")
    )
    if display_label:
        entry["display_label"] = display_label
    modalities = _normalize_modalities(
        entry.get("modalities")
        or entry.get("path")
        or entry.get("paths")
        or entry.get("route")
        or entry.get("routes")
    )
    if modalities:
        entry["modalities"] = modalities
        entry["path"] = modalities[0]
    return entry


def _normalized_endpoint_inventory(
    hardware: dict[str, Any],
    legacy_light_path: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    collisions: list[str] = []
    sources: list[tuple[str, list[dict[str, Any]]]] = []

    for key in CANONICAL_ENDPOINT_COLLECTION_KEYS:
        raw_rows = hardware.get(key)
        if isinstance(raw_rows, list):
            sources.append((key, [row for row in raw_rows if isinstance(row, dict)]))

    endpoints_already_normalized = any(
        isinstance(row, dict) and (
            isinstance(row.get("source_section"), str)
            or isinstance(row.get("endpoint_origin"), str)
        )
        for row in (hardware.get("endpoints") or [])
    )

    if not endpoints_already_normalized:
        for key in ENDPOINT_CAPABLE_INVENTORY_KEYS:
            raw_rows = hardware.get(key)
            if isinstance(raw_rows, list):
                sources.append((key, [row for row in raw_rows if isinstance(row, dict)]))

    if legacy_light_path is not None:
        sources.extend(
            (key, [row for row in legacy_light_path.get(key, []) if isinstance(row, dict)])
            for key in CANONICAL_ENDPOINT_COLLECTION_KEYS
            if isinstance(legacy_light_path.get(key), list)
        )

    for source_section, collection in sources:
        for index, endpoint in enumerate(collection, start=1):
            entry = _normalize_endpoint_capable_row(endpoint, source_section=source_section, index=index)
            entry_id = entry["id"]
            previous_source = seen.get(entry_id)
            if previous_source is not None:
                collisions.append(
                    f"normalized endpoint id `{entry_id}` is declared in both `{previous_source}` and `{source_section}`."
                )
                continue
            seen[entry_id] = source_section
            rows.append(entry)
    return rows, collisions



def _clean_identifier(value: Any) -> str:
    cleaned = _clean_string(value).lower()
    if not cleaned:
        return ""
    return re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")



def _normalize_endpoint_type(value: Any) -> str:
    raw = _clean_string(value).lower()
    token = _clean_identifier(raw)
    if not raw and not token:
        return "detector"
    if any(keyword in raw for keyword in ("eyepiece", "ocular")) or token in {"eyepiece", "eyepieces", "ocular", "oculars", "binocular", "trinocular"}:
        return "eyepiece"
    if ("camera" in raw and "port" in raw) or token in {"camera_port", "cameraport"}:
        return "camera_port"
    if token in CAMERA_DETECTOR_KINDS | POINT_DETECTOR_KINDS | {"hyd", "apd", "spad", "detector", "camera"}:
        return "detector"
    return token or "detector"



def _routes_overlap(left: list[str], right: list[str]) -> bool:
    left_set = {tag for tag in left if tag != "all"}
    right_set = {tag for tag in right if tag != "all"}
    if not left_set or not right_set:
        return True
    if "shared" in left_set or "shared" in right_set:
        return True
    return bool(left_set & right_set)


def _validate_splitter_branch(branch: dict[str, Any], errors: list[str], context: str) -> None:
    targets = branch.get("targets") or branch.get("target_ids") or branch.get("terminal_ids") or branch.get("endpoint_ids")
    if targets is not None:
        values = targets if isinstance(targets, list) else [targets]
        if not all(isinstance(item, str) and item.strip() for item in values):
            errors.append(f"{context}: targets must be a string or list of non-empty strings when provided.")


def _normalize_modalities(value: Any) -> list[str]:
    items = value if isinstance(value, list) else [value]
    modalities: list[str] = []
    for item in items:
        cleaned = _clean_string(item).lower()
        if cleaned and cleaned in ROUTE_TAGS and cleaned not in {"shared", "all"} and cleaned not in modalities:
            modalities.append(cleaned)
    return modalities



def _identifier_slug(*parts: Any, fallback: str = "item") -> str:
    joined = "_".join(_clean_identifier(part) for part in parts if _clean_identifier(part))
    return joined or fallback



def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]



def _copy_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}



def _normalize_canonical_source_rows(raw_sources: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, source in enumerate(raw_sources or [], start=1):
        if not isinstance(source, dict):
            continue
        entry = dict(source)
        base_id = _clean_identifier(
            entry.get("id")
            or entry.get("source_id")
            or entry.get("channel_name")
            or entry.get("name")
            or entry.get("model")
            or f"source_{index}"
        ) or f"source_{index}"
        entry["id"] = base_id if base_id not in seen_ids else f"{base_id}_{index}"
        seen_ids.add(entry["id"])
        modalities = _normalize_modalities(
            entry.get("modalities")
            or entry.get("path")
            or entry.get("paths")
            or entry.get("route")
            or entry.get("routes")
        )
        if modalities:
            entry["modalities"] = modalities
            entry["path"] = modalities[0]
        rows.append(entry)
    return rows



def _parse_canonical_source_rows(hardware: dict[str, Any]) -> list[dict[str, Any]]:
    raw_sources = hardware.get("sources")
    if not isinstance(raw_sources, list):
        return []
    return _normalize_canonical_source_rows(raw_sources)



def _import_legacy_source_rows(hardware: dict[str, Any]) -> list[dict[str, Any]]:
    raw_sources = hardware.get("light_sources")
    if not isinstance(raw_sources, list):
        return []
    return _normalize_canonical_source_rows(raw_sources)



def _parse_canonical_endpoint_rows(hardware: dict[str, Any]) -> list[dict[str, Any]]:
    rows, _ = _normalized_endpoint_inventory(hardware)
    return rows



def _import_legacy_endpoint_rows(hardware: dict[str, Any], legacy_light_path: dict[str, Any]) -> list[dict[str, Any]]:
    rows, _ = _normalized_endpoint_inventory(hardware, legacy_light_path)
    return rows



def _normalize_splitter_branch(branch: dict[str, Any], *, fallback_id: str) -> dict[str, Any]:
    entry = dict(branch)
    entry["id"] = _clean_identifier(entry.get("id") or entry.get("label") or entry.get("name")) or fallback_id
    target_ids = entry.get("target_ids") or entry.get("targets") or entry.get("terminal_ids") or entry.get("endpoint_ids") or entry.get("endpoint_id") or entry.get("target") or entry.get("endpoint")
    entry["target_ids"] = [item for item in (_clean_identifier(value) for value in _as_list(target_ids)) if item]
    component = entry.get("component") if isinstance(entry.get("component"), dict) else entry.get("emission_filter")
    if isinstance(component, dict):
        entry["component"] = dict(component)
    elif isinstance(entry.get("components"), list):
        entry["components"] = [dict(item) for item in entry.get("components") if isinstance(item, dict)]
    return entry



def _stage_role_from_element(entry: dict[str, Any]) -> str | None:
    stage_role = _clean_string(entry.get("stage_role") or entry.get("role")).lower()
    if stage_role:
        return stage_role
    if any(isinstance(entry.get(key), dict) for key in CUBE_LINK_KEYS):
        return "cube"
    positions = entry.get("positions") if isinstance(entry.get("positions"), dict) else {}
    for position in positions.values():
        if isinstance(position, dict) and any(isinstance(position.get(key), dict) for key in CUBE_LINK_KEYS):
            return "cube"
    element_type = _clean_string(entry.get("element_type") or entry.get("type")).lower()
    if element_type in {"selector", "splitter", "emission_splitter", "image_splitter", "dual_view", "quad_view"}:
        return "splitter"
    return None



def _normalize_canonical_optical_path_elements(raw_elements: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, element in enumerate(raw_elements or [], start=1):
        if not isinstance(element, dict):
            continue
        entry = dict(element)
        entry["id"] = _clean_identifier(entry.get("id") or entry.get("name") or entry.get("display_label") or entry.get("model") or f"optical_path_element_{index}") or f"optical_path_element_{index}"
        if entry["id"] in seen:
            entry["id"] = f"{entry['id']}_{index}"
        seen.add(entry["id"])
        entry.setdefault("element_type", entry.get("type") or "mechanism")
        modalities = _normalize_modalities(
            entry.get("modalities")
            or entry.get("path")
            or entry.get("paths")
            or entry.get("route")
            or entry.get("routes")
        )
        if modalities:
            entry["modalities"] = modalities
            entry["path"] = modalities[0]
        inferred_stage_role = _stage_role_from_element(entry)
        if inferred_stage_role:
            entry["stage_role"] = inferred_stage_role
        else:
            entry.pop("stage_role", None)
        rows.append(entry)
    return rows



def _parse_canonical_optical_path_elements(hardware: dict[str, Any]) -> list[dict[str, Any]]:
    raw_elements = hardware.get("optical_path_elements")
    if not isinstance(raw_elements, list):
        return []
    return _normalize_canonical_optical_path_elements(raw_elements)



def _import_legacy_optical_path_elements(hardware: dict[str, Any], legacy_light_path: dict[str, Any]) -> list[dict[str, Any]]:
    raw_elements: list[dict[str, Any]] = []
    stage_sources = [
        ("cube", legacy_light_path.get("cube_mechanisms")),
        ("excitation", legacy_light_path.get("excitation_mechanisms")),
        ("dichroic", legacy_light_path.get("dichroic_mechanisms")),
        ("emission", legacy_light_path.get("emission_mechanisms")),
    ]
    for stage_role, collection in stage_sources:
        for entry in collection or []:
            if not isinstance(entry, dict):
                continue
            cloned = dict(entry)
            cloned.setdefault("stage_role", stage_role)
            raw_elements.append(cloned)
    for splitter in _collect_splitters(hardware, legacy_light_path):
        if isinstance(splitter, dict):
            cloned = dict(splitter)
            cloned.setdefault("stage_role", "splitter")
            raw_elements.append(cloned)
    return _normalize_canonical_optical_path_elements(raw_elements)



def _modality_match(modalities: list[str], route_id: str) -> bool:
    return not modalities or route_id in modalities



def _canonicalize_sequence_item(
    item: Any,
    sources: list[dict[str, Any]],
    elements: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
    *,
    sequence_key: str,
    allow_branches: bool = True,
) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    source_ids = {row.get("id") for row in sources}
    element_ids = {row.get("id") for row in elements}
    endpoint_ids = {row.get("id") for row in endpoints}
    allowed_ref_keys = ("source_id", "optical_path_element_id") if sequence_key.startswith("illumination_sequence") else ("optical_path_element_id", "endpoint_id")
    raw_branches = item.get("branches")
    if allow_branches and isinstance(raw_branches, dict):
        if any(item.get(key) for key in SEQUENCE_TOPOLOGY_KEYS if key != "branches"):
            return None
        selection_mode = _clean_string(raw_branches.get("selection_mode")).lower()
        if selection_mode not in {"fixed", "exclusive", "multiple"}:
            return None
        raw_items = raw_branches.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            return None
        normalized_items: list[dict[str, Any]] = []
        for branch_index, branch in enumerate(raw_items, start=1):
            if not isinstance(branch, dict):
                return None
            branch_id = _clean_identifier(branch.get("branch_id"))
            if not branch_id:
                return None
            raw_sequence = branch.get("sequence")
            if not isinstance(raw_sequence, list) or not raw_sequence:
                return None
            normalized_sequence = [
                normalized
                for normalized in (
                    _canonicalize_sequence_item(
                        sequence_item,
                        sources,
                        elements,
                        endpoints,
                        sequence_key=sequence_key,
                        allow_branches=False,
                    )
                    for sequence_item in raw_sequence
                )
                if normalized
            ]
            if len(normalized_sequence) != len(raw_sequence):
                return None
            branch_payload = {
                "branch_id": branch_id,
                "label": _clean_string(branch.get("label")) or _resolve_route_label(branch_id),
                "sequence": normalized_sequence,
            }
            if branch.get("mode"):
                branch_payload["mode"] = _clean_string(branch.get("mode")).lower()
            normalized_items.append(branch_payload)
        return {
            "branches": {
                "selection_mode": selection_mode,
                "items": normalized_items,
            }
        }
    populated_ref_keys = [key for key in allowed_ref_keys if item.get(key)]
    if len(populated_ref_keys) != 1:
        return None
    selected_key = populated_ref_keys[0]
    if any(item.get(key) for key in SEQUENCE_TOPOLOGY_KEYS if key not in {selected_key, "position_id"}):
        return None
    normalized_value = _clean_identifier(item.get(selected_key))
    if not normalized_value:
        return None
    if selected_key == "source_id" and normalized_value not in source_ids:
        return None
    if selected_key == "optical_path_element_id" and normalized_value not in element_ids:
        return None
    if selected_key == "endpoint_id" and normalized_value not in endpoint_ids:
        return None
    normalized_item = {selected_key: normalized_value}
    if selected_key == "optical_path_element_id":
        position_id = _clean_string(item.get("position_id"))
        if position_id:
            normalized_item["position_id"] = position_id
    return normalized_item



def _parse_canonical_light_paths(raw_light_paths: list[dict[str, Any]], sources: list[dict[str, Any]], elements: list[dict[str, Any]], endpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for index, route in enumerate(raw_light_paths, start=1):
        if not isinstance(route, dict):
            continue
        route_id = _clean_identifier(route.get("id") or route.get("name") or f"route_{index}")
        if not route_id:
            continue
        illumination_sequence = [
            normalized
            for normalized in (
                _canonicalize_sequence_item(
                    item,
                    sources,
                    elements,
                    endpoints,
                    sequence_key="illumination_sequence",
                    allow_branches=False,
                )
                for item in _as_list(route.get("illumination_sequence"))
            )
            if normalized
        ]
        detection_sequence = [
            normalized
            for normalized in (
                _canonicalize_sequence_item(item, sources, elements, endpoints, sequence_key="detection_sequence")
                for item in _as_list(route.get("detection_sequence"))
            )
            if normalized
        ]
        route_modalities = _normalize_modalities(route.get("modalities") or route.get("routes") or route.get("path"))
        routes.append({
            "id": route_id,
            "name": _clean_string(route.get("name")) or _resolve_route_label(route_id),
            "modalities": route_modalities or [route_id],
            "illumination_sequence": illumination_sequence,
            "detection_sequence": detection_sequence,
        })
    return routes



def _import_legacy_light_paths(sources: list[dict[str, Any]], elements: list[dict[str, Any]], endpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    route_ids: set[str] = set()
    for collection in (sources, elements, endpoints):
        for row in collection:
            route_ids.update(_normalize_modalities(row.get("modalities") or row.get("path") or row.get("routes")))
    if not route_ids:
        route_ids = {"epi"}
    ordered_routes = sorted(route_ids, key=_route_sort_key)
    routes: list[dict[str, Any]] = []
    stage_order = {"illumination": ["excitation", "cube", "dichroic"], "detection": ["cube", "dichroic", "emission", "analyzer", "splitter"]}
    for route_id in ordered_routes:
        illumination_sequence = [{"source_id": source["id"]} for source in sources if _modality_match(_normalize_modalities(source.get("modalities") or source.get("path") or source.get("routes")), route_id)]
        for stage_role in stage_order["illumination"]:
            illumination_sequence.extend(
                {"optical_path_element_id": element["id"]}
                for element in elements
                if element.get("stage_role") == stage_role and _modality_match(_normalize_modalities(element.get("modalities") or element.get("path") or element.get("routes")), route_id)
            )
        detection_sequence: list[dict[str, Any]] = []
        for stage_role in stage_order["detection"]:
            detection_sequence.extend(
                {"optical_path_element_id": element["id"]}
                for element in elements
                if element.get("stage_role") == stage_role and _modality_match(_normalize_modalities(element.get("modalities") or element.get("path") or element.get("routes")), route_id)
            )
        if not any(element.get("stage_role") == "splitter" and _modality_match(_normalize_modalities(element.get("modalities") or element.get("path") or element.get("routes")), route_id) for element in elements):
            detection_sequence.extend(
                {"endpoint_id": endpoint["id"]}
                for endpoint in endpoints
                if _modality_match(_normalize_modalities(endpoint.get("modalities") or endpoint.get("path") or endpoint.get("routes")), route_id)
            )
        if not illumination_sequence and not detection_sequence:
            continue
        routes.append({
            "id": route_id,
            "name": _resolve_route_label(route_id),
            "illumination_sequence": illumination_sequence,
            "detection_sequence": detection_sequence,
        })
    return routes



def _apply_route_modalities_from_sequences(
    *,
    sources: list[dict[str, Any]],
    elements: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
    light_paths: list[dict[str, Any]],
) -> None:
    source_by_id = {entry.get("id"): entry for entry in sources}
    element_by_id = {entry.get("id"): entry for entry in elements}
    endpoint_by_id = {entry.get("id"): entry for entry in endpoints}

    def apply_to_ref(ref_key: str, ref_id: str, route_id: str) -> None:
        if ref_key == "source_id":
            row = source_by_id.get(ref_id)
        elif ref_key == "optical_path_element_id":
            row = element_by_id.get(ref_id)
        else:
            row = endpoint_by_id.get(ref_id)
        if not row:
            return
        modalities = _normalize_modalities(row.get("modalities") or row.get("path") or row.get("routes"))
        if route_id not in modalities:
            row["modalities"] = modalities + [route_id] if modalities else [route_id]
            row["path"] = row["modalities"][0]

    def walk_sequence(sequence: list[dict[str, Any]], route_id: str) -> None:
        for item in sequence:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("branches"), dict):
                for branch in item["branches"].get("items") or []:
                    if isinstance(branch, dict):
                        walk_sequence(branch.get("sequence") or [], route_id)
                continue
            for ref_key in ("source_id", "optical_path_element_id", "endpoint_id"):
                ref_id = _clean_identifier(item.get(ref_key))
                if ref_id:
                    apply_to_ref(ref_key, ref_id, route_id)

    for route in light_paths:
        route_ids = _normalize_modalities(route.get("modalities") or route.get("routes") or route.get("path")) or [route["id"]]
        for route_id in route_ids:
            for sequence_key in ("illumination_sequence", "detection_sequence"):
                walk_sequence(route.get(sequence_key, []), route_id)



def _canonical_light_path_model(
    *,
    sources: list[dict[str, Any]],
    optical_path_elements: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
    light_paths: list[dict[str, Any]],
) -> dict[str, Any]:
    _apply_route_modalities_from_sequences(
        sources=sources,
        elements=optical_path_elements,
        endpoints=endpoints,
        light_paths=light_paths,
    )
    return {
        "sources": sources,
        "optical_path_elements": optical_path_elements,
        "endpoints": endpoints,
        "light_paths": light_paths,
    }



def _has_canonical_light_path_input(instrument_dict: dict[str, Any]) -> bool:
    hardware = instrument_dict.get("hardware") if isinstance(instrument_dict.get("hardware"), dict) else {}
    return any(
        (
            isinstance(hardware.get("sources"), list),
            isinstance(hardware.get("optical_path_elements"), list),
            isinstance(hardware.get("endpoints"), list),
            isinstance(hardware.get("terminals"), list),
            isinstance(hardware.get("detection_endpoints"), list),
            isinstance(instrument_dict.get("light_paths"), list),
        )
    )



def parse_canonical_light_path_model(instrument_dict: dict[str, Any]) -> dict[str, Any]:
    """Parse the explicit canonical v2 authoring contract only.

    This parser consumes:
    - hardware.sources[]
    - hardware.optical_path_elements[]
    - normalized hardware endpoints synthesized from hardware.endpoints[] and endpoint-capable inventories
    - light_paths[].illumination_sequence[]
    - light_paths[].detection_sequence[]

    It intentionally does not inspect or synthesize from legacy light-path structures.
    """
    hardware = instrument_dict.get("hardware") if isinstance(instrument_dict.get("hardware"), dict) else {}
    sources = _parse_canonical_source_rows(hardware)
    elements = _parse_canonical_optical_path_elements(hardware)
    endpoints = _parse_canonical_endpoint_rows(hardware)
    raw_light_paths = instrument_dict.get("light_paths") if isinstance(instrument_dict.get("light_paths"), list) else []
    light_paths = _parse_canonical_light_paths(raw_light_paths, sources, elements, endpoints)
    return _canonical_light_path_model(
        sources=sources,
        optical_path_elements=elements,
        endpoints=endpoints,
        light_paths=light_paths,
    )



def import_legacy_light_path_model(instrument_dict: dict[str, Any]) -> dict[str, Any]:
    """Import legacy light-path topology into the canonical v2 shape.

    This adapter is the only place where legacy `hardware.light_path` and
    `hardware.light_sources` structures are converted into canonical v2 data.
    """
    hardware = instrument_dict.get("hardware") if isinstance(instrument_dict.get("hardware"), dict) else {}
    legacy_light_path = hardware.get("light_path") if isinstance(hardware.get("light_path"), dict) else {}
    sources = _import_legacy_source_rows(hardware)
    elements = _import_legacy_optical_path_elements(hardware, legacy_light_path)
    endpoints = _import_legacy_endpoint_rows(hardware, legacy_light_path)
    light_paths = _import_legacy_light_paths(sources, elements, endpoints)
    return _canonical_light_path_model(
        sources=sources,
        optical_path_elements=elements,
        endpoints=endpoints,
        light_paths=light_paths,
    )



def canonicalize_light_path_model(instrument_dict: dict[str, Any]) -> dict[str, Any]:
    """Return canonical v2 light-path data for downstream consumers.

    Canonical v2 input is structurally primary. Legacy support is retained only
    via the explicit import adapter.
    """
    payload = instrument_dict if isinstance(instrument_dict, dict) else {}
    if _has_canonical_light_path_input(payload):
        return parse_canonical_light_path_model(payload)
    return import_legacy_light_path_model(payload)


def migrate_instrument_to_light_path_v2(instrument_dict: dict[str, Any]) -> dict[str, Any]:
    canonical = canonicalize_light_path_model(instrument_dict)
    payload = json.loads(json.dumps(instrument_dict))
    hardware = payload.setdefault("hardware", {})
    hardware["sources"] = canonical["sources"]
    hardware["optical_path_elements"] = canonical["optical_path_elements"]
    hardware["endpoints"] = canonical["endpoints"]
    payload["light_paths"] = canonical["light_paths"]
    hardware.pop("light_path", None)
    if "light_sources" in hardware:
        hardware.pop("light_sources", None)
    return payload



def validate_light_path(instrument_dict: dict) -> list[str]:
    errors, _ = validate_light_path_diagnostics(instrument_dict)
    return errors


def validate_light_path_warnings(instrument_dict: dict) -> list[str]:
    _, warnings = validate_light_path_diagnostics(instrument_dict)
    return warnings


def _sequence_terminates_with_explicit_endpoint(sequence: Any) -> bool:
    if not isinstance(sequence, list):
        return False
    for item in reversed(sequence):
        if not isinstance(item, dict):
            continue
        branch_block = item.get("branches")
        if isinstance(branch_block, dict):
            branches = [branch for branch in branch_block.get("items") or [] if isinstance(branch, dict)]
            return bool(branches) and all(_sequence_terminates_with_explicit_endpoint(branch.get("sequence")) for branch in branches)
        if _clean_identifier(item.get("endpoint_id")):
            return True
        if _clean_identifier(item.get("optical_path_element_id")) or _clean_identifier(item.get("source_id")):
            return False
    return False


def _sequence_item_allowed_keys(sequence_key: str, *, allow_branches: bool) -> tuple[str, ...]:
    reference_keys = ("source_id", "optical_path_element_id") if sequence_key.startswith("illumination_sequence") else ("optical_path_element_id", "endpoint_id")
    return reference_keys + (("branches",) if allow_branches else ())


def _sequence_item_union_message(sequence_key: str, *, allow_branches: bool) -> str:
    allowed_keys = _sequence_item_allowed_keys(sequence_key, allow_branches=allow_branches)
    if sequence_key.startswith("illumination_sequence"):
        context = "illumination sequence item"
    elif sequence_key.startswith("detection_sequence"):
        context = "detection sequence item" if allow_branches else "branch-local detection sequence item"
    else:
        context = "sequence item"
    if sequence_key.startswith("illumination_sequence") and ".branches.items[" in sequence_key:
        context = "branch-local illumination sequence item"
    return f"{context} must declare exactly one of {', '.join(allowed_keys[:-1])}, or {allowed_keys[-1]}." if len(allowed_keys) > 1 else f"{context} must declare {allowed_keys[0]}."


def validate_light_path_diagnostics(instrument_dict: dict) -> tuple[list[str], list[str]]:
    """Validate canonical YAML-first light-path definitions.

    Canonical schema:
    - hardware.sources[]
    - hardware.optical_path_elements[]
    - unified hardware endpoints normalized from endpoint-capable inventories
    - light_paths[] with illumination_sequence / detection_sequence

    Legacy hardware.light_path structures are normalized through the migration layer
    so validation remains centralized here.
    """
    errors: list[str] = []
    warnings: list[str] = []
    canonical = canonicalize_light_path_model(instrument_dict if isinstance(instrument_dict, dict) else {})
    sources = canonical["sources"]
    elements = canonical["optical_path_elements"]
    endpoints = canonical["endpoints"]
    raw_light_paths = canonical["light_paths"]
    hardware_inventory, hardware_index_map = _build_hardware_inventory(sources, elements, endpoints)
    inventory_lookup = {item["id"]: item for item in hardware_inventory if isinstance(item, dict) and item.get("id")}
    source_lookup = {entry.get("id"): entry for entry in sources if isinstance(entry, dict) and entry.get("id")}
    element_lookup = {entry.get("id"): entry for entry in elements if isinstance(entry, dict) and entry.get("id")}
    endpoint_lookup = {entry.get("id"): entry for entry in endpoints if isinstance(entry, dict) and entry.get("id")}
    light_paths: list[dict[str, Any]] = []
    route_hardware_usage: list[dict[str, Any]] = []
    for route in raw_light_paths:
        if not isinstance(route, dict):
            continue
        resolved_route, usage = _build_route_sequences_and_graph(
            route,
            source_lookup=source_lookup,
            element_lookup=element_lookup,
            endpoint_lookup=endpoint_lookup,
            inventory_lookup=inventory_lookup,
        )
        light_paths.append(resolved_route)
        route_hardware_usage.append(usage)

    route_usage_by_inventory_id: dict[str, list[str]] = {}
    for usage in route_hardware_usage:
        route_id = _clean_string(usage.get("route_id"))
        for inventory_id in usage.get("hardware_inventory_ids") or []:
            route_usage_by_inventory_id.setdefault(inventory_id, [])
            if route_id and route_id not in route_usage_by_inventory_id[inventory_id]:
                route_usage_by_inventory_id[inventory_id].append(route_id)
    for item in hardware_inventory:
        inventory_id = item.get("id")
        if inventory_id:
            item["route_usage_summary"] = route_usage_by_inventory_id.get(inventory_id, [])
    raw_light_paths = instrument_dict.get("light_paths") if isinstance(instrument_dict.get("light_paths"), list) else []
    light_paths_for_validation = raw_light_paths if (_has_canonical_light_path_input(instrument_dict) and raw_light_paths) else light_paths

    source_ids = {entry.get("id") for entry in sources}
    element_ids = {entry.get("id") for entry in elements}
    endpoint_ids = {entry.get("id") for entry in endpoints}

    has_topology = bool(sources or elements or endpoints or light_paths or _collect_splitters((instrument_dict.get("hardware") or {}), ((instrument_dict.get("hardware") or {}).get("light_path") or {})))
    if not has_topology:
        return [], []
    if not light_paths_for_validation:
        errors.append("light_paths must declare at least one route with illumination_sequence and detection_sequence.")

    hardware = instrument_dict.get("hardware") if isinstance(instrument_dict.get("hardware"), dict) else {}
    legacy_light_path = hardware.get("light_path") if isinstance(hardware.get("light_path"), dict) else {}
    _, endpoint_collisions = _normalized_endpoint_inventory(hardware, legacy_light_path)
    errors.extend(endpoint_collisions)
    raw_elements = hardware.get("optical_path_elements") if isinstance(hardware.get("optical_path_elements"), list) else []
    for element_index, element in enumerate(raw_elements):
        if not isinstance(element, dict):
            continue
        if not isinstance(element.get("branches"), list):
            continue
        errors.append(
            f"hardware.optical_path_elements[{element_index}].branches: deprecated hardware-owned routing metadata is not allowed in canonical topology; move branch routing into light_paths[].detection_sequence[].branches."
        )

    seen_route_ids: set[str] = set()

    def validate_sequence_item(
        item: Any,
        *,
        route_context: str,
        route_id: str,
        sequence_key: str,
        item_index: int,
        allow_branches: bool,
        previous_element_id: str,
    ) -> tuple[str, list[str]]:
        local_errors: list[str] = []
        if not isinstance(item, dict):
            local_errors.append(f"{route_context}.{sequence_key}[{item_index}]: sequence item must be an object.")
            return previous_element_id, local_errors

        allowed_keys = _sequence_item_allowed_keys(sequence_key, allow_branches=allow_branches)
        populated_keys = [
            key
            for key in SEQUENCE_TOPOLOGY_KEYS
            if (
                isinstance(item.get("branches"), dict) if key == "branches" else bool(_clean_identifier(item.get(key)))
            )
        ]
        if len(populated_keys) != 1 or populated_keys[0] not in allowed_keys:
            local_errors.append(
                f"{route_context}.{sequence_key}[{item_index}]: {_sequence_item_union_message(sequence_key, allow_branches=allow_branches)}"
            )
            return previous_element_id, local_errors

        branch_block = item.get("branches")
        if isinstance(branch_block, dict):
            if not allow_branches:
                local_errors.append(f"{route_context}.{sequence_key}[{item_index}]: nested branches are not supported in branch-local sequences.")
                return previous_element_id, local_errors
            if not previous_element_id:
                local_errors.append(f"{route_context}.{sequence_key}[{item_index}]: branches must follow an optical_path_element_id so the route fork is explicit.")
            selection_mode = _clean_string(branch_block.get("selection_mode")).lower()
            if selection_mode not in {"fixed", "exclusive", "multiple"}:
                local_errors.append(f"{route_context}.{sequence_key}[{item_index}].branches.selection_mode: must be one of fixed, exclusive, multiple.")
            items = branch_block.get("items")
            if not isinstance(items, list) or not items:
                local_errors.append(f"{route_context}.{sequence_key}[{item_index}].branches.items: must be a non-empty list.")
                return previous_element_id, local_errors
            seen_branch_ids: set[str] = set()
            for branch_index, branch in enumerate(items):
                branch_context = f"{route_context}.{sequence_key}[{item_index}].branches.items[{branch_index}]"
                if not isinstance(branch, dict):
                    local_errors.append(f"{branch_context}: branch item must be an object.")
                    continue
                branch_id = _clean_identifier(branch.get("branch_id") or branch.get("id"))
                if not branch_id:
                    local_errors.append(f"{branch_context}.branch_id: is required.")
                elif branch_id in seen_branch_ids:
                    local_errors.append(f"{branch_context}.branch_id: duplicate branch id `{branch_id}` within the same branch block.")
                seen_branch_ids.add(branch_id)
                branch_sequence = branch.get("sequence")
                if not isinstance(branch_sequence, list) or not branch_sequence:
                    local_errors.append(f"{branch_context}.sequence: must be a non-empty list.")
                    continue
                branch_previous = ""
                for sequence_index, sequence_item in enumerate(branch_sequence):
                    branch_previous, branch_errors = validate_sequence_item(
                        sequence_item,
                        route_context=route_context,
                        route_id=route_id,
                        sequence_key=f"{sequence_key}[{item_index}].branches.items[{branch_index}].sequence",
                        item_index=sequence_index,
                        allow_branches=False,
                        previous_element_id=branch_previous,
                    )
                    local_errors.extend(branch_errors)
            return previous_element_id, local_errors

        source_id = _clean_identifier(item.get("source_id"))
        element_id = _clean_identifier(item.get("optical_path_element_id"))
        endpoint_id = _clean_identifier(item.get("endpoint_id"))
        if source_id:
            if source_id not in source_ids:
                local_errors.append(f"{route_context}.{sequence_key}[{item_index}]: unknown source_id `{source_id}`.")
            row = next((candidate for candidate in sources if candidate.get("id") == source_id), None)
        elif element_id:
            if element_id not in element_ids:
                local_errors.append(f"{route_context}.{sequence_key}[{item_index}]: unknown optical_path_element_id `{element_id}`.")
            row = next((candidate for candidate in elements if candidate.get("id") == element_id), None)
            previous_element_id = element_id
        else:
            if endpoint_id not in endpoint_ids:
                local_errors.append(f"{route_context}.{sequence_key}[{item_index}]: unknown endpoint_id `{endpoint_id}`.")
            row = next((candidate for candidate in endpoints if candidate.get("id") == endpoint_id), None)
        if row:
            modalities = _normalize_modalities(row.get("modalities") or row.get("path") or row.get("routes"))
            if modalities and route_id not in modalities:
                local_errors.append(
                    f"{route_context}.{sequence_key}[{item_index}]: `{source_id or element_id or endpoint_id}` is declared for modalities {modalities} and does not permit route `{route_id}`."
                )
        return previous_element_id, local_errors

    for route_index, route in enumerate(light_paths_for_validation):
        route_id = _clean_identifier(route.get("id"))
        context = f"light_paths[{route_index}]"
        if not route_id:
            errors.append(f"{context}: id is required.")
            continue
        if route_id in seen_route_ids:
            errors.append(f"{context}: duplicate light path id `{route_id}`.")
        seen_route_ids.add(route_id)
        for sequence_key in ("illumination_sequence", "detection_sequence"):
            sequence = route.get(sequence_key)
            if not isinstance(sequence, list):
                errors.append(f"{context}.{sequence_key}: sequence must be a list.")
                continue
            previous_element_id = ""
            sequence_error_count = len(errors)
            for item_index, item in enumerate(sequence):
                previous_element_id, item_errors = validate_sequence_item(
                    item,
                    route_context=context,
                    route_id=route_id,
                    sequence_key=sequence_key,
                    item_index=item_index,
                    allow_branches=sequence_key == "detection_sequence",
                    previous_element_id=previous_element_id,
                )
                errors.extend(item_errors)
            if sequence_key == "detection_sequence":
                for item_index, item in enumerate(sequence):
                    branch_block = item.get("branches") if isinstance(item, dict) else None
                    if not isinstance(branch_block, dict):
                        continue
                    for branch_index, branch in enumerate(branch_block.get("items") or []):
                        if not isinstance(branch, dict):
                            continue
                        branch_sequence = branch.get("sequence") or []
                        if _sequence_terminates_with_explicit_endpoint(branch_sequence):
                            continue
                        warnings.append(
                            f"{context}.{sequence_key}[{item_index}].branches.items[{branch_index}].sequence: branch does not terminate in a clear explicit endpoint_id."
                        )
                if len(errors) == sequence_error_count and not _sequence_terminates_with_explicit_endpoint(sequence):
                    warnings.append(
                        f"{context}.{sequence_key}: route does not terminate in a clear explicit endpoint_id; add an endpoint_id or explicit branch endpoints."
                    )

    legacy_hardware = hardware
    known_target_ids = {endpoint.get("id") for endpoint in endpoints if endpoint.get("id")}
    known_target_ids.update(
        _clean_identifier(detector.get("id") or detector.get("channel_name") or detector.get("display_label") or detector.get("name"))
        for detector in legacy_hardware.get("detectors", []) if isinstance(detector, dict)
    )
    for split_idx, splitter in enumerate(_collect_splitters(legacy_hardware, legacy_light_path)):
        split_ctx = f"splitters[{split_idx}]"
        for key in ("path_1", "path_2"):
            if isinstance(splitter.get(key), dict):
                _validate_splitter_branch(splitter[key], errors, f"{split_ctx}.{key}")
                for target in _as_list(splitter[key].get("targets") or splitter[key].get("target_ids") or splitter[key].get("endpoint_ids") or splitter[key].get("terminal_ids")):
                    normalized = _clean_identifier(target)
                    if normalized and normalized not in known_target_ids:
                        errors.append(f"{split_ctx}.{key}: target `{normalized}` does not match any declared detector or endpoint.")

    seen_element_ids: set[str] = set()
    for element_index, element in enumerate(elements):
        context = f"hardware.optical_path_elements[{element_index}]"
        element_id = _clean_identifier(element.get("id"))
        if not element_id:
            errors.append(f"{context}: id is required.")
            continue
        if element_id in seen_element_ids:
            errors.append(f"{context}: duplicate optical_path_element id `{element_id}`.")
        seen_element_ids.add(element_id)
        selection_mode = _clean_string(element.get("selection_mode")).lower()
        if selection_mode and selection_mode not in {"fixed", "exclusive", "multiple"}:
            errors.append(f"{context}: selection_mode must be one of fixed, exclusive, multiple.")

    return errors, warnings

# ---------------------------------------------------------------------------
# Payload serialization helpers
# ---------------------------------------------------------------------------


def _band_strings(component: dict[str, Any], key: str) -> list[str]:
    raw_bands = component.get(key)
    if not isinstance(raw_bands, list):
        return []
    rendered: list[str] = []
    for band in raw_bands:
        if not isinstance(band, dict):
            continue
        center = _coerce_number(band.get("center_nm"))
        width = _coerce_number(band.get("width_nm"))
        if _is_positive_number(center) and _is_positive_number(width):
            rendered.append(f"{_format_numeric(center)}/{_format_numeric(width)}")
    return rendered



def _build_label(component: dict[str, Any]) -> str:
    component_type = component.get("component_type", "unknown")

    if component_type in {"bandpass", "notch", "multiband_bandpass"}:
        bands = component.get("bands")
        if isinstance(bands, list) and bands:
            band_strings: list[str] = []
            for band in bands:
                if not isinstance(band, dict):
                    continue
                center = band.get("center_nm")
                width = band.get("width_nm")
                if _is_positive_number(center) and _is_positive_number(width):
                    band_strings.append(f"{_format_numeric(center)}/{_format_numeric(width)}")
            if band_strings:
                return " + ".join(band_strings)

        center = component.get("center_nm")
        width = component.get("width_nm")
        if _is_positive_number(center) and _is_positive_number(width):
            return f"{_format_numeric(center)}/{_format_numeric(width)}"
        return _resolve_component_type_label(str(component_type))
    if component_type == "longpass":
        cut_on = component.get("cut_on_nm")
        return f"LP {_format_numeric(cut_on)}" if _is_positive_number(cut_on) else "Longpass"
    if component_type == "shortpass":
        cut_off = component.get("cut_off_nm")
        return f"SP {_format_numeric(cut_off)}" if _is_positive_number(cut_off) else "Shortpass"
    if component_type in DICHROIC_TYPES:
        if component_type in {"multiband_dichroic", "polychroic"}:
            transmission = _band_strings(component, "transmission_bands")
            reflection = _band_strings(component, "reflection_bands")
            if transmission or reflection:
                parts: list[str] = []
                if transmission:
                    parts.append(f"T[{ ' + '.join(transmission) }]")
                if reflection:
                    parts.append(f"R[{ ' + '.join(reflection) }]")
                return f"Dichroic {' | '.join(parts)}"

        cutoffs = component.get("cutoffs_nm")
        if isinstance(cutoffs, list) and cutoffs:
            rendered = ", ".join(_format_numeric(value) for value in cutoffs)
            return f"Dichroic [{rendered}]"

        transmission = _band_strings(component, "transmission_bands")
        reflection = _band_strings(component, "reflection_bands")
        if transmission or reflection:
            parts: list[str] = []
            if transmission:
                parts.append(f"T[{ ' + '.join(transmission) }]")
            if reflection:
                parts.append(f"R[{ ' + '.join(reflection) }]")
            return f"Dichroic {' | '.join(parts)}"
        return "Dichroic"
    if component_type in NO_WAVELENGTH_TYPES:
        return _resolve_component_type_label(str(component_type))

    return _resolve_component_type_label(str(component_type))



def _render_kind(component: dict[str, Any]) -> str:
    component_type = str(component.get("component_type", "unknown")).lower()
    if component_type in {"laser", "light_source", "led"}:
        return "source"
    if component_type in {"detector"}:
        return "detector"
    if component_type in {"bandpass", "notch", "multiband_bandpass", "filter_cube"}:
        return "band"
    if component_type in {"longpass"}:
        return "longpass"
    if component_type in {"shortpass"}:
        return "shortpass"
    if component_type in {"tunable"}:
        return "tunable"
    if component_type in NO_WAVELENGTH_TYPES:
        return "empty"
    if component_type in DICHROIC_TYPES:
        return "dichroic"
    if component_type in {"analyzer"}:
        return "analyzer"
    return "other"



def _build_details(component: dict[str, Any]) -> str:
    manufacturer = component.get("manufacturer")
    model = component.get("model")
    product_code = component.get("product_code")
    notes = component.get("notes")
    parts = [
        str(part).strip()
        for part in (manufacturer, model, product_code, notes)
        if isinstance(part, str) and part.strip()
    ]
    return " | ".join(parts)



def _normalize_routes(value: Any) -> list[str]:
    candidates = value if isinstance(value, list) else [value]
    routes: list[str] = []
    for candidate in candidates:
        cleaned = _clean_string(candidate).lower()
        if cleaned and cleaned in ROUTE_TAGS and cleaned not in routes:
            routes.append(cleaned)
    return routes



def _normalize_power_weight(raw_power: Any) -> float | None:
    if isinstance(raw_power, (int, float)) and not isinstance(raw_power, bool):
        return float(raw_power)
    if not isinstance(raw_power, str):
        return None
    match = POWER_VALUE_RE.search(raw_power)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None




def _normalize_component_numeric_fields(component_payload: dict[str, Any], source: dict[str, Any]) -> None:
    for key in ("center_nm", "width_nm", "cut_on_nm", "cut_off_nm", "wavelength_nm", "tunable_min_nm", "tunable_max_nm", "pulse_width_ps", "repetition_rate_mhz", "qe_peak_pct", "read_noise_e", "default_gating_delay_ns", "default_gate_width_ns", "power_weight", "collection_min_nm", "collection_max_nm", "collection_center_nm", "collection_width_nm", "channel_center_nm", "bandwidth_nm", "min_nm", "max_nm"):
        if key in source:
            numeric = _coerce_number(source.get(key))
            if numeric is not None:
                component_payload[key] = numeric
            elif source.get(key) is not None:
                component_payload[key] = source.get(key)

    cutoffs = source.get("cutoffs_nm")
    if isinstance(cutoffs, list):
        component_payload["cutoffs_nm"] = [value for value in (_coerce_number(item) for item in cutoffs) if value is not None]

    bands = source.get("bands")
    if isinstance(bands, list):
        normalized_bands = []
        for band in bands:
            if not isinstance(band, dict):
                continue
            normalized_band: dict[str, Any] = {}
            center = _coerce_number(band.get("center_nm"))
            width = _coerce_number(band.get("width_nm"))
            if center is not None:
                normalized_band["center_nm"] = center
            if width is not None:
                normalized_band["width_nm"] = width
            if normalized_band:
                normalized_bands.append(normalized_band)
        if normalized_bands:
            component_payload["bands"] = normalized_bands

    for band_key in ("transmission_bands", "reflection_bands"):
        raw_bands = source.get(band_key)
        if not isinstance(raw_bands, list):
            continue
        normalized_bands = []
        for band in raw_bands:
            if not isinstance(band, dict):
                continue
            center = _coerce_number(band.get("center_nm"))
            width = _coerce_number(band.get("width_nm"))
            if center is None or width is None:
                continue
            normalized_bands.append({"center_nm": center, "width_nm": width})
        if normalized_bands:
            component_payload[band_key] = normalized_bands



def _component_payload(component: dict[str, Any], *, default_name: str = "", branch_mode: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = dict(component)
    component_type = _clean_string(component.get("component_type")).lower() or "unknown"
    payload["component_type"] = component_type
    payload["type"] = component_type
    payload["label"] = _build_label(component)
    payload["display_label"] = payload.get("label")
    payload["details"] = _build_details(component)
    payload["render_kind"] = _render_kind(component)
    if default_name and not _clean_string(payload.get("name")):
        payload["name"] = default_name
    routes = _normalize_routes(component.get("path") or component.get("paths") or component.get("route") or component.get("routes"))
    if routes:
        payload["routes"] = routes
        payload["path"] = routes[0]
    if branch_mode:
        payload["branch_mode"] = branch_mode
    _normalize_component_numeric_fields(payload, component)
    # Flag component types whose spectral behavior is not modeled so the
    # runtime and UI can surface a note instead of silently treating them
    # as transparent.
    if component_type == "analyzer":
        payload["_unsupported_spectral_model"] = True
    payload["spectral_ops"] = _spectral_ops_for_component(payload)
    return payload


def _extract_dichroic_spectral_data(component: dict[str, Any]) -> dict[str, Any]:
    """Extract the raw dichroic spectral specification fields from a component."""
    data: dict[str, Any] = {}
    if isinstance(component.get("transmission_bands"), list) and component["transmission_bands"]:
        data["transmission_bands"] = component["transmission_bands"]
    if isinstance(component.get("reflection_bands"), list) and component["reflection_bands"]:
        data["reflection_bands"] = component["reflection_bands"]
    if isinstance(component.get("bands"), list) and component["bands"]:
        data["bands"] = component["bands"]
    cut_on = _coerce_number(component.get("cut_on_nm"))
    if cut_on is not None:
        data["cut_on_nm"] = cut_on
    if isinstance(component.get("cutoffs_nm"), list) and component["cutoffs_nm"]:
        data["cutoffs_nm"] = component["cutoffs_nm"]
    return data


def _spectral_ops_for_component(component: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Compute parser-authoritative spectral operations keyed by phase.

    Every mechanism position and component payload receives this field so the
    browser runtime never has to interpret component types to decide spectral
    behavior.  The runtime becomes a pure executor of these pre-computed ops.

    Returns ``{"illumination": [...], "detection": [...]}`` where each value
    is an ordered list of spectral operation dicts the runtime must apply.
    """
    ctype = _clean_string(component.get("component_type") or component.get("type")).lower()

    _passthrough: list[dict[str, Any]] = [{"op": "passthrough"}]

    if not ctype or ctype in {"mirror", "empty", "passthrough", "neutral_density"}:
        return {"illumination": list(_passthrough), "detection": list(_passthrough)}

    if ctype in {"block", "blocker"}:
        both: list[dict[str, Any]] = [{"op": "block"}]
        return {"illumination": list(both), "detection": list(both)}

    if ctype == "analyzer":
        both = [{"op": "passthrough", "unsupported_reason": "polarization_not_modeled"}]
        return {"illumination": list(both), "detection": list(both)}

    if ctype == "bandpass":
        center = _coerce_number(component.get("center_nm"))
        width = _coerce_number(component.get("width_nm"))
        if center is not None and width is not None:
            op: dict[str, Any] = {"op": "bandpass", "center_nm": center, "width_nm": width}
        else:
            bands = component.get("bands")
            if isinstance(bands, list) and bands:
                normalized = [b for b in (
                    {"center_nm": _coerce_number(b.get("center_nm")), "width_nm": _coerce_number(b.get("width_nm"))}
                    for b in bands if isinstance(b, dict)
                ) if b.get("center_nm") is not None]
                if normalized:
                    op = {"op": "multiband_bandpass", "bands": normalized}
                else:
                    op = {"op": "passthrough", "unsupported_reason": "bandpass missing usable spectral data"}
            else:
                op = {"op": "passthrough", "unsupported_reason": "bandpass missing center_nm/width_nm and no bands"}
        return {"illumination": [op], "detection": [op]}

    if ctype == "multiband_bandpass":
        bands = component.get("bands")
        if isinstance(bands, list) and bands:
            normalized = [b for b in (
                {"center_nm": _coerce_number(b.get("center_nm")), "width_nm": _coerce_number(b.get("width_nm"))}
                for b in bands if isinstance(b, dict)
            ) if b.get("center_nm") is not None]
            if normalized:
                op = {"op": "multiband_bandpass", "bands": normalized}
            else:
                op = {"op": "passthrough", "unsupported_reason": "multiband_bandpass bands are invalid"}
        else:
            op = {"op": "passthrough", "unsupported_reason": "multiband_bandpass missing bands"}
        return {"illumination": [op], "detection": [op]}

    if ctype == "longpass":
        cut_on = _coerce_number(component.get("cut_on_nm"))
        if cut_on is not None:
            op = {"op": "longpass", "cut_on_nm": cut_on}
        else:
            op = {"op": "passthrough", "unsupported_reason": "longpass missing cut_on_nm"}
        return {"illumination": [op], "detection": [op]}

    if ctype == "shortpass":
        cut_off = _coerce_number(component.get("cut_off_nm"))
        if cut_off is not None:
            op = {"op": "shortpass", "cut_off_nm": cut_off}
        else:
            op = {"op": "passthrough", "unsupported_reason": "shortpass missing cut_off_nm"}
        return {"illumination": [op], "detection": [op]}

    if ctype == "notch":
        center = _coerce_number(component.get("center_nm"))
        width = _coerce_number(component.get("width_nm"))
        if center is not None and width is not None:
            op = {"op": "notch", "center_nm": center, "width_nm": width}
        else:
            op = {"op": "passthrough", "unsupported_reason": "notch missing center_nm or width_nm"}
        return {"illumination": [op], "detection": [op]}

    if ctype == "tunable":
        start = _coerce_number(component.get("band_start_nm")) or _coerce_number(component.get("min_nm"))
        end = _coerce_number(component.get("band_end_nm")) or _coerce_number(component.get("max_nm"))
        if start is not None and end is not None:
            op = {"op": "tunable_bandpass", "start_nm": start, "end_nm": end}
        else:
            op = {"op": "passthrough", "unsupported_reason": "tunable missing start/end bounds"}
        return {"illumination": [op], "detection": [op]}

    if ctype in DICHROIC_TYPES:
        dichroic_data = _extract_dichroic_spectral_data(component)
        if not any(key in dichroic_data for key in ("transmission_bands", "reflection_bands", "bands", "cut_on_nm")):
            op = {"op": "passthrough", "unsupported_reason": "dichroic requires transmission_bands, reflection_bands, bands, or cut_on_nm"}
            return {"illumination": [op], "detection": [op]}
        return {
            "illumination": [{"op": "dichroic_reflect", **dichroic_data}],
            "detection": [{"op": "dichroic_transmit", **dichroic_data}],
        }

    if ctype == "filter_cube":
        return _cube_spectral_ops(component)

    return {
        "illumination": [{"op": "passthrough", "unsupported_reason": f"unknown component type '{ctype}'"}],
        "detection": [{"op": "passthrough", "unsupported_reason": f"unknown component type '{ctype}'"}],
    }


def _cube_spectral_ops(component: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Compute phase-aware spectral ops for a filter cube from its sub-components.

    In illumination: excitation_filter + dichroic (reflection mode).
    In detection: dichroic (transmission mode) + emission_filter.
    """
    exc = component.get("excitation_filter") or component.get("excitation") or component.get("ex")
    di = component.get("dichroic") or component.get("dichroic_filter") or component.get("di")
    em = component.get("emission_filter") or component.get("emission") or component.get("em")

    linked_components = component.get("linked_components")
    if not isinstance(linked_components, dict):
        linked_components = {}
    if isinstance(exc, dict):
        linked_components.setdefault("excitation_filter", exc)
    if isinstance(di, dict):
        linked_components.setdefault("dichroic", di)
    if isinstance(em, dict):
        linked_components.setdefault("emission_filter", em)
    if linked_components:
        component["linked_components"] = linked_components

    illumination: list[dict[str, Any]] = []
    detection: list[dict[str, Any]] = []

    if isinstance(exc, dict):
        exc_ops = _spectral_ops_for_component(exc)
        for op in exc_ops.get("illumination", []):
            illumination.append({**op, "sub_role": "excitation_filter"})
    if isinstance(di, dict):
        di_data = _extract_dichroic_spectral_data(di)
        illumination.append({"op": "dichroic_reflect", "sub_role": "dichroic", **di_data})
        detection.append({"op": "dichroic_transmit", "sub_role": "dichroic", **di_data})
    if isinstance(em, dict):
        em_ops = _spectral_ops_for_component(em)
        for op in em_ops.get("detection", []):
            detection.append({**op, "sub_role": "emission_filter"})

    if not illumination:
        illumination = [{"op": "passthrough", "unsupported_reason": "filter_cube missing excitation/dichroic data"}]
    if not detection:
        detection = [{"op": "passthrough", "unsupported_reason": "filter_cube missing dichroic/emission data"}]

    return {"illumination": illumination, "detection": detection}


def _light_source_display_label(source: dict[str, Any]) -> str:
    raw_kind = _clean_string(source.get("kind") or source.get("type") or "source")
    kind = _resolve_light_source_kind(raw_kind)
    manufacturer = _clean_string(source.get("manufacturer"))
    model = _clean_string(source.get("model"))
    wavelength = source.get("wavelength_nm")
    tunable_min = source.get("tunable_min_nm")
    tunable_max = source.get("tunable_max_nm")
    prefix = ""
    if _coerce_number(wavelength) is not None:
        prefix = f"{_format_numeric(wavelength)} nm"
    elif _coerce_number(tunable_min) is not None and _coerce_number(tunable_max) is not None:
        prefix = f"{_format_numeric(tunable_min)}-{_format_numeric(tunable_max)} nm"
    elif isinstance(wavelength, str) and wavelength.strip():
        prefix = wavelength.strip()
    return " ".join(part for part in [prefix, kind, manufacturer, model] if part).strip() or model or _resolve_light_source_kind(raw_kind) or "Light Source"



def infer_light_source_role(source: dict[str, Any]) -> str:
    """SIMULATOR-ONLY fallback role inference.

    This helper is intentionally non-authoritative and must not be used to populate
    canonical/production role fields. Canonical role must come from explicit YAML `role`.
    """
    explicit = _clean_string(source.get("role")).lower()
    if explicit:
        return explicit

    routes = _normalize_routes(source.get("path") or source.get("paths") or source.get("route") or source.get("routes"))
    if "transmitted" in routes:
        return "transmitted_illumination"

    return "excitation"



def _source_role(source: dict[str, Any]) -> str:
    return _clean_string(source.get("role")).lower()



def _detector_class(kind: str) -> str:
    normalized = kind.lower().strip()
    if normalized in {"eyepiece", "eyepieces", "ocular", "oculars"}:
        return "eyepiece"
    if normalized in {"camera_port", "cameraport"}:
        return "camera_port"
    if normalized in CAMERA_DETECTOR_KINDS:
        return "camera"
    if normalized in {"hyd"}:
        return "hybrid"
    if normalized in {"apd", "spad"}:
        return "apd"
    if normalized in POINT_DETECTOR_KINDS:
        return "point"
    return "detector"



def _source_spectral_mode(kind: str, wavelength: Any, width_nm: Any, tunable_min_nm: Any, tunable_max_nm: Any) -> str:
    if _coerce_number(tunable_min_nm) is not None and _coerce_number(tunable_max_nm) is not None:
        if kind in {"laser", "white_light_laser", "multiphoton_laser", "supercontinuum"}:
            return "tunable_line"
        return "tunable_band"
    if kind in {"arc_lamp", "halogen_lamp", "metal_halide"}:
        return "broadband"
    if _coerce_number(width_nm) is not None and _coerce_number(width_nm) > 0:
        return "band"
    if _coerce_number(wavelength) is not None:
        return "line"
    return "broadband"



def _source_position(slot: int, source: dict[str, Any]) -> dict[str, Any]:
    tunable_min = source.get("tunable_min_nm")
    tunable_max = source.get("tunable_max_nm")

    wavelength = source.get("wavelength_nm")
    width_nm = source.get("width_nm")
    kind = _clean_string(source.get("kind") or source.get("type") or "light_source").lower() or "light_source"
    display_label = _light_source_display_label({**source, "tunable_min_nm": tunable_min, "tunable_max_nm": tunable_max})
    role = _source_role(source)
    position = {
        "slot": slot,
        "component_type": "laser" if kind in {"laser", "white_light_laser", "multiphoton_laser", "supercontinuum"} else "light_source",
        "render_kind": "source",
        "type": kind,
        "kind": kind,
        "role": role,
        "simulator_inferred_role": infer_light_source_role(source) if not role else role,
        "name": display_label,
        "display_label": display_label,
        "manufacturer": source.get("manufacturer"),
        "product_code": source.get("product_code"),
        "model": source.get("model"),
        "technology": source.get("technology"),
        "wavelength_nm": wavelength,
        "width_nm": width_nm,
        "tunable_min_nm": tunable_min,
        "tunable_max_nm": tunable_max,
        "spectral_mode": _source_spectral_mode(kind, wavelength, width_nm, tunable_min, tunable_max),
        "timing_mode": source.get("timing_mode"),
        "pulse_width_ps": source.get("pulse_width_ps"),
        "repetition_rate_mhz": source.get("repetition_rate_mhz"),
        "depletion_targets_nm": source.get("depletion_targets_nm") if isinstance(source.get("depletion_targets_nm"), list) else [],
        "power": source.get("power"),
        "power_weight": _normalize_power_weight(source.get("power")),
        "details": _build_details(source),
        "notes": source.get("notes"),
    }
    routes = _normalize_routes(source.get("path") or source.get("paths") or source.get("route") or source.get("routes"))
    if routes:
        position["routes"] = routes
        position["path"] = routes[0]
    _normalize_component_numeric_fields(position, position)
    return position



def _detector_position(slot: int, detector: dict[str, Any], *, terminal_id: str | None = None, mechanism_id: str | None = None) -> dict[str, Any]:
    kind = _clean_string(detector.get("kind") or detector.get("type") or "detector").lower() or "detector"
    manufacturer = _clean_string(detector.get("manufacturer"))
    model = _clean_string(detector.get("model"))
    channel_name = _clean_string(detector.get("channel_name") or detector.get("channel") or detector.get("name")) or f"Detector {slot}"
    display_label = " ".join(part for part in [channel_name if channel_name not in {manufacturer, model} else "", manufacturer, model] if part).strip() or channel_name or manufacturer or model or f"Detector {slot}"
    resolved_terminal_id = terminal_id or _clean_identifier(detector.get("id")) or f"terminal_detector_{slot}"
    position = {
        "id": resolved_terminal_id,
        "terminal_id": resolved_terminal_id,
        "slot": 1,
        "component_type": "detector",
        "render_kind": "detector",
        "type": "detector",
        "endpoint_type": "detector",
        "kind": kind,
        "detector_class": _detector_class(kind),
        "name": display_label,
        "display_label": display_label,
        "channel_name": channel_name,
        "manufacturer": detector.get("manufacturer"),
        "product_code": detector.get("product_code"),
        "model": detector.get("model"),
        "pixel_pitch_um": detector.get("pixel_pitch_um") or detector.get("pixel_size_um"),
        "sensor_format_px": detector.get("sensor_format_px"),
        "binning": detector.get("binning"),
        "bit_depth": detector.get("bit_depth"),
        "qe_peak_pct": detector.get("qe_peak_pct"),
        "read_noise_e": detector.get("read_noise_e"),
        "supports_time_gating": detector.get("supports_time_gating"),
        "default_gating_delay_ns": detector.get("default_gating_delay_ns"),
        "default_gate_width_ns": detector.get("default_gate_width_ns"),
        "collection_min_nm": detector.get("collection_min_nm") or detector.get("min_nm"),
        "collection_max_nm": detector.get("collection_max_nm") or detector.get("max_nm"),
        "collection_center_nm": detector.get("collection_center_nm") or detector.get("channel_center_nm"),
        "collection_width_nm": detector.get("collection_width_nm") or detector.get("bandwidth_nm"),
        "channel_center_nm": detector.get("channel_center_nm"),
        "bandwidth_nm": detector.get("bandwidth_nm"),
        "min_nm": detector.get("min_nm"),
        "max_nm": detector.get("max_nm"),
        "notes": detector.get("notes"),
        "details": _build_details(detector),
        "source_mechanism_id": mechanism_id,
        "default_enabled": detector.get("default_enabled") if isinstance(detector.get("default_enabled"), bool) else True,
        "is_digital": True,
    }
    routes = _normalize_routes(detector.get("path") or detector.get("paths") or detector.get("route") or detector.get("routes"))
    if routes:
        position["routes"] = routes
        position["path"] = routes[0]
    _normalize_component_numeric_fields(position, position)
    return position



def _terminal_payload_from_endpoint(index: int, endpoint: dict[str, Any], *, default_name: str | None = None) -> dict[str, Any]:
    endpoint_type = _normalize_endpoint_type(
        endpoint.get("endpoint_type") or endpoint.get("type") or endpoint.get("kind") or endpoint.get("name")
    )
    terminal_id = _clean_identifier(endpoint.get("id")) or f"terminal_{endpoint_type}_{index}"
    kind = _clean_string(endpoint.get("kind") or endpoint_type).lower() or endpoint_type
    default_labels = {
        "eyepiece": "Eyepieces",
        "camera_port": "Camera Port",
        "detector": f"Endpoint {index}",
    }
    display_label = _clean_string(endpoint.get("display_label") or endpoint.get("name") or default_name) or default_labels.get(endpoint_type, f"Endpoint {index}")
    payload: dict[str, Any] = {
        "id": terminal_id,
        "terminal_id": terminal_id,
        "slot": 1,
        "component_type": "detector",
        "render_kind": "detector",
        "type": endpoint_type,
        "endpoint_type": endpoint_type,
        "kind": kind if endpoint_type == "detector" else endpoint_type,
        "detector_class": endpoint_type if endpoint_type in {"eyepiece", "camera_port"} else _detector_class(kind),
        "name": display_label,
        "display_label": display_label,
        "channel_name": display_label,
        "manufacturer": endpoint.get("manufacturer"),
        "product_code": endpoint.get("product_code"),
        "model": endpoint.get("model"),
        "pixel_pitch_um": endpoint.get("pixel_pitch_um") or endpoint.get("pixel_size_um"),
        "sensor_format_px": endpoint.get("sensor_format_px"),
        "binning": endpoint.get("binning"),
        "bit_depth": endpoint.get("bit_depth"),
        "qe_peak_pct": endpoint.get("qe_peak_pct"),
        "read_noise_e": endpoint.get("read_noise_e"),
        "supports_time_gating": endpoint.get("supports_time_gating"),
        "default_gating_delay_ns": endpoint.get("default_gating_delay_ns"),
        "default_gate_width_ns": endpoint.get("default_gate_width_ns"),
        "collection_min_nm": endpoint.get("collection_min_nm") or endpoint.get("min_nm"),
        "collection_max_nm": endpoint.get("collection_max_nm") or endpoint.get("max_nm"),
        "collection_center_nm": endpoint.get("collection_center_nm") or endpoint.get("channel_center_nm"),
        "collection_width_nm": endpoint.get("collection_width_nm") or endpoint.get("bandwidth_nm"),
        "channel_center_nm": endpoint.get("channel_center_nm"),
        "bandwidth_nm": endpoint.get("bandwidth_nm"),
        "min_nm": endpoint.get("min_nm"),
        "max_nm": endpoint.get("max_nm"),
        "notes": endpoint.get("notes"),
        "details": _build_details(endpoint),
        "default_enabled": endpoint.get("default_enabled") if isinstance(endpoint.get("default_enabled"), bool) else False,
        "is_digital": endpoint_type == "detector",
    }
    if endpoint_type == "eyepiece":
        if payload.get("collection_min_nm") is None:
            payload["collection_min_nm"] = 390
        if payload.get("collection_max_nm") is None:
            payload["collection_max_nm"] = 700
        if payload.get("collection_enabled") is None:
            payload["collection_enabled"] = True
    elif endpoint_type == "camera_port":
        if payload.get("collection_enabled") is None:
            payload["collection_enabled"] = False
    routes = _normalize_routes(endpoint.get("path") or endpoint.get("paths") or endpoint.get("route") or endpoint.get("routes"))
    if routes:
        payload["routes"] = routes
        payload["path"] = routes[0]
    _normalize_component_numeric_fields(payload, payload)
    return payload



def _terminal_mechanism_payload(index: int, terminal: dict[str, Any]) -> dict[str, Any]:
    mechanism_payload: dict[str, Any] = {
        "id": f"endpoint_{_clean_identifier(terminal.get('id')) or index}",
        "name": terminal.get("display_label") or terminal.get("name") or f"Endpoint {index}",
        "display_label": terminal.get("display_label") or terminal.get("name") or f"Endpoint {index}",
        "type": "endpoint_group",
        "control_kind": "detector_toggle",
        "selection_mode": "multi",
        "positions": {1: dict(terminal)},
        "options": [{"slot": 1, "display_label": terminal.get("display_label") or terminal.get("name"), "value": dict(terminal)}],
    }
    routes = _normalize_routes(terminal.get("routes") or terminal.get("path"))
    if routes:
        mechanism_payload["routes"] = routes
        mechanism_payload["path"] = routes[0]
    return mechanism_payload



def _candidate_terminals_for_routes(terminals: list[dict[str, Any]], routes: list[str]) -> list[dict[str, Any]]:
    return [
        terminal
        for terminal in terminals
        if _routes_overlap(routes, terminal.get("routes") if isinstance(terminal.get("routes"), list) else _normalize_routes(terminal.get("path")))
    ]



def _resolve_target_ids(raw_targets: Any, terminals: list[dict[str, Any]]) -> list[str]:
    values = raw_targets if isinstance(raw_targets, list) else [raw_targets]
    terminals_by_id: dict[str, str] = {}
    for terminal in terminals:
        if not isinstance(terminal, dict):
            continue
        for key in ("id", "terminal_id"):
            identifier = _clean_identifier(terminal.get(key))
            if identifier and identifier not in terminals_by_id and isinstance(terminal.get("id"), str):
                terminals_by_id[identifier] = terminal["id"]

    resolved: list[str] = []
    for value in values:
        identifier = _clean_identifier(value)
        if not identifier or identifier not in terminals_by_id:
            continue
        resolved_id = terminals_by_id[identifier]
        if resolved_id not in resolved:
            resolved.append(resolved_id)
    return resolved



def _append_inferred_terminal(terminals: list[dict[str, Any]], endpoint_type: str, *, name: str, path: str | None = None, default_enabled: bool = False) -> None:
    payload = _terminal_payload_from_endpoint(
        len(terminals) + 1,
        {
            "id": f"auto_{endpoint_type}",
            "name": name,
            "type": endpoint_type,
            "path": path or "shared",
            "default_enabled": default_enabled,
            "notes": "Auto-generated endpoint inferred from microscope metadata.",
        },
    )
    terminals.append(payload)



def _infer_default_terminals(
    instrument_dict: dict[str, Any],
    splitters: list[dict[str, Any]],
    terminals: list[dict[str, Any]],
) -> None:
    instrument_meta = instrument_dict.get("instrument", {}) if isinstance(instrument_dict.get("instrument"), dict) else {}
    ocular = _clean_string(instrument_meta.get("ocular_availability")).lower()
    has_digital = any(bool(terminal.get("is_digital")) for terminal in terminals)

    def has_endpoint(endpoint_type: str) -> bool:
        return any(_normalize_endpoint_type(terminal.get("endpoint_type") or terminal.get("type") or terminal.get("kind")) == endpoint_type for terminal in terminals)

    default_enable = not has_digital
    if ocular in {"binocular", "trinocular"} and not has_endpoint("eyepiece"):
        _append_inferred_terminal(terminals, "eyepiece", name="Eyepieces", path="shared", default_enabled=default_enable)
    if ocular in {"trinocular", "camera_only"} and not has_endpoint("camera_port"):
        _append_inferred_terminal(terminals, "camera_port", name="Camera Port", path="shared", default_enabled=default_enable)

    for splitter in splitters:
        text = " ".join(
            part for part in (
                _clean_string(splitter.get("name")),
                _clean_string(splitter.get("notes")),
            )
            if part
        ).lower()
        routes = _normalize_routes(splitter.get("path") or splitter.get("paths") or splitter.get("route") or splitter.get("routes"))
        route_hint = routes[0] if routes else "shared"
        if "camera" in text and "port" in text and not has_endpoint("camera_port"):
            _append_inferred_terminal(terminals, "camera_port", name="Camera Port", path=route_hint, default_enabled=default_enable)
        if any(keyword in text for keyword in ("eyepiece", "ocular")) and not has_endpoint("eyepiece"):
            _append_inferred_terminal(terminals, "eyepiece", name="Eyepieces", path=route_hint, default_enabled=default_enable)

def _mechanism_payload(stage_prefix: str, index: int, mechanism: dict[str, Any]) -> dict[str, Any]:
    raw_positions = mechanism.get("positions", {})
    positions: list[dict[str, Any]] = []

    if isinstance(raw_positions, dict):
        normalized_positions = sorted(
            (
                (_coerce_slot_key(slot), slot, component)
                for slot, component in raw_positions.items()
            ),
            key=lambda item: (item[0] is None, item[0]),
        )
        for slot, original_key, component in normalized_positions:
            if slot is None or not isinstance(component, dict):
                continue
            component_payload = _component_payload(component)
            component_payload["slot"] = slot
            component_payload["position_key"] = str(original_key)
            component_payload["display_label"] = f"Slot {slot}: {component_payload.get('label')}"
            positions.append(component_payload)

    _stage_label = resolve_stage_role_label(stage_prefix) if _active_vocab is not None else stage_prefix.replace("_", " ").title()
    mechanism_payload = {
        "id": f"{stage_prefix}_mech_{index}",
        "name": mechanism.get("name") or f"{_stage_label} {index + 1}",
        "display_label": mechanism.get("name") or f"{_stage_label} {index + 1}",
        "type": mechanism.get("type", "unknown"),
        "positions": positions,
    }

    mechanism_type = str(mechanism.get("type", "")).lower()
    mechanism_payload["control_kind"] = "dropdown"
    mechanism_payload["control_label"] = mechanism_payload["display_label"]
    if mechanism_type in {"tunable", "spectral_slider"}:
        mechanism_payload["control_kind"] = "tunable_slider"
        mechanism_payload["min_nm"] = mechanism.get("min_nm", 400)
        mechanism_payload["max_nm"] = mechanism.get("max_nm", 800)
        mechanism_payload["default_min_nm"] = mechanism.get("default_min_nm", 500)
        mechanism_payload["default_max_nm"] = mechanism.get("default_max_nm", 550)
    mechanism_payload["options"] = [
        {
            "slot": position.get("slot"),
            "display_label": position.get("display_label"),
            "value": position,
        }
        for position in positions
    ]
    routes = _normalize_routes(mechanism.get("path") or mechanism.get("paths") or mechanism.get("route") or mechanism.get("routes"))
    if routes:
        mechanism_payload["routes"] = routes
        mechanism_payload["path"] = routes[0]
    if isinstance(mechanism.get("notes"), str) and mechanism["notes"].strip():
        mechanism_payload["notes"] = mechanism["notes"].strip()

    if mechanism.get("type") == "spectral_array":
        mechanism_payload["control_kind"] = "spectral_array"
        min_nm = mechanism.get("min_nm") if _is_positive_number(mechanism.get("min_nm")) else mechanism.get("band_min_nm")
        max_nm = mechanism.get("max_nm") if _is_positive_number(mechanism.get("max_nm")) else mechanism.get("band_max_nm")
        bands = mechanism.get("bands") if _is_positive_number(mechanism.get("bands")) else mechanism.get("max_bands")

        spectral_payload: dict[str, Any] = {}
        if _is_positive_number(min_nm):
            spectral_payload["min_nm"] = min_nm
            mechanism_payload["band_min_nm"] = min_nm
        if _is_positive_number(max_nm):
            spectral_payload["max_nm"] = max_nm
            mechanism_payload["band_max_nm"] = max_nm
        if _is_positive_number(bands):
            spectral_payload["bands"] = bands
            mechanism_payload["max_bands"] = int(bands)

        if _is_positive_number(mechanism.get("default_band_width_nm")):
            mechanism_payload["default_band_width_nm"] = mechanism.get("default_band_width_nm")

        if spectral_payload:
            mechanism_payload["spectral_array"] = spectral_payload

    return mechanism_payload


def _estimate_dichroic_cut_on(
    bands: Any,
    cut_on_nm: Any,
) -> float | None:
    """Estimate a dichroic cut-on wavelength from emission band data.

    For a single-band cube the dichroic is placed ~20 nm below the lower edge
    of the emission band (center - width/2).  For multiband cubes the lowest
    band edge is used.  When only a longpass *cut_on_nm* is present the
    dichroic is placed 20 nm below that cut-on.

    Returns ``None`` if no estimate can be made.
    """
    if isinstance(bands, list) and bands:
        edges: list[float] = []
        for band in bands:
            if not isinstance(band, dict):
                continue
            center = _coerce_number(band.get("center_nm"))
            width = _coerce_number(band.get("width_nm"))
            if center is not None and width is not None and width > 0:
                edges.append(center - width / 2)
        if edges:
            return round(min(edges) - 20, 1)
    raw = cut_on_nm
    if isinstance(raw, list) and raw:
        raw = raw[0]
    coerced = _coerce_number(raw)
    if coerced is not None:
        return round(coerced - 20, 1)
    return None


def _cube_mechanism_payload(index: int, mechanism: dict[str, Any]) -> dict[str, Any]:
    raw_positions = mechanism.get("positions", {})
    positions: list[dict[str, Any]] = []
    if isinstance(raw_positions, dict):
        normalized_positions = sorted(
            (
                (_coerce_slot_key(slot), slot, cube_position)
                for slot, cube_position in raw_positions.items()
            ),
            key=lambda item: (item[0] is None, item[0]),
        )
        for slot, original_key, cube_position in normalized_positions:
            if slot is None or not isinstance(cube_position, dict):
                continue

            linked_components: dict[str, dict[str, Any]] = {}
            for link_key in CUBE_LINK_KEYS:
                component = cube_position.get(link_key)
                if not isinstance(component, dict):
                    continue
                linked_components[link_key] = _component_payload(component, default_name=_resolve_cube_link_label(link_key))

            # Flattened filter_cube positions (component_type: filter_cube with bands
            # but no explicit excitation_filter/dichroic/emission_filter sub-components)
            # are expanded into full composite optics: emission_filter plus a
            # synthetic dichroic estimated from the emission band edge.  When
            # only emission data is available the cube is flagged _cube_incomplete
            # so the runtime can warn the user.
            cube_label = cube_position.get("name") or f"Cube {slot}"
            if not linked_components and _clean_string(cube_position.get("component_type")).lower() == "filter_cube":
                bands = cube_position.get("bands")
                cut_on_nm = cube_position.get("cut_on_nm")
                synth: dict[str, Any] = {"name": cube_label}
                if isinstance(bands, list) and len(bands) > 1:
                    synth["component_type"] = "multiband_bandpass"
                    synth["bands"] = bands
                elif isinstance(bands, list) and len(bands) == 1:
                    synth["component_type"] = "bandpass"
                    synth["bands"] = bands
                    band = bands[0]
                    if isinstance(band, dict):
                        if band.get("center_nm") is not None:
                            synth["center_nm"] = band["center_nm"]
                        if band.get("width_nm") is not None:
                            synth["width_nm"] = band["width_nm"]
                elif isinstance(cut_on_nm, list) and cut_on_nm:
                    synth["component_type"] = "longpass"
                    synth["cut_on_nm"] = _coerce_number(cut_on_nm[0])
                elif _coerce_number(cut_on_nm) is not None:
                    synth["component_type"] = "longpass"
                    synth["cut_on_nm"] = _coerce_number(cut_on_nm)
                else:
                    synth["component_type"] = "bandpass"
                if synth.get("component_type"):
                    linked_components["emission_filter"] = _component_payload(synth, default_name=cube_label)

                # Synthesize a dichroic from the emission band lower edge so the
                # runtime can model excitation reflection + emission transmission.
                dichroic_cut_on = _estimate_dichroic_cut_on(bands, cut_on_nm)
                if dichroic_cut_on is not None:
                    linked_components["dichroic"] = _component_payload(
                        {"name": f"{cube_label} (dichroic)", "component_type": "dichroic", "cut_on_nm": dichroic_cut_on},
                        default_name=f"{cube_label} (dichroic)",
                    )

            position_payload: dict[str, Any] = {
                "slot": slot,
                "position_key": str(original_key),
                "type": "cube",
                "component_type": "filter_cube",
                "label": cube_label,
                "display_label": cube_label,
                "details": _build_details(cube_position),
                "linked_components": linked_components,
                # Backward-compatible direct aliases used by the browser runtime.
                "excitation_filter": linked_components.get("excitation_filter"),
                "dichroic": linked_components.get("dichroic"),
                "emission_filter": linked_components.get("emission_filter"),
            }
            # Flag cubes that have no explicit excitation data so the runtime
            # can warn users about incomplete cube modeling.
            if linked_components and "excitation_filter" not in linked_components:
                position_payload["_cube_incomplete"] = True
            # Parser-authoritative spectral ops for the browser runtime.
            position_payload["spectral_ops"] = _cube_spectral_ops(position_payload)
            routes = _normalize_routes(cube_position.get("path") or cube_position.get("paths") or cube_position.get("route") or cube_position.get("routes") or mechanism.get("path"))
            if routes:
                position_payload["routes"] = routes
                position_payload["path"] = routes[0]
            positions.append(position_payload)

    mechanism_payload: dict[str, Any] = {
        "id": f"cube_mech_{index}",
        "name": mechanism.get("name") or f"Cube {index + 1}",
        "display_label": mechanism.get("name") or f"Cube {index + 1}",
        "type": mechanism.get("type", "unknown"),
        "positions": positions,
        "control_kind": "dropdown",
        "control_label": mechanism.get("name") or f"Cube {index + 1}",
        "options": [
            {
                "slot": position.get("slot"),
                "display_label": position.get("label") or f"Cube {position.get('slot')}",
                "value": position,
            }
            for position in positions
        ],
    }
    routes = _normalize_routes(mechanism.get("path") or mechanism.get("paths") or mechanism.get("route") or mechanism.get("routes"))
    if routes:
        mechanism_payload["routes"] = routes
        mechanism_payload["path"] = routes[0]
    if isinstance(mechanism.get("notes"), str) and mechanism["notes"].strip():
        mechanism_payload["notes"] = mechanism["notes"].strip()
    return mechanism_payload



def _route_tags(selection: dict[str, Any]) -> set[str]:
    tags: set[str] = set()
    routes = selection.get("routes")
    if isinstance(routes, list):
        tags.update(_normalize_routes(routes))
    path = selection.get("path")
    if isinstance(path, str) and path.strip():
        tags.update(_normalize_routes(path))

    linked_components = selection.get("linked_components")
    if isinstance(linked_components, dict):
        for linked in linked_components.values():
            if isinstance(linked, dict):
                tags.update(_route_tags(linked))
    return tags



def _routes_compatible(route_tags: set[str]) -> bool:
    constrained = {tag for tag in route_tags if tag not in {"all", "shared"}}
    return len(constrained) <= 1



def _choice_positions(mechanism: dict[str, Any]) -> list[dict[str, Any]]:
    positions = mechanism.get("positions", [])
    if isinstance(positions, list):
        return [pos for pos in positions if isinstance(pos, dict) and isinstance(pos.get("slot"), int)]
    if isinstance(positions, dict):
        return [
            {"slot": normalized_slot, **position}
            for slot, position in positions.items()
            for normalized_slot in [_coerce_slot_key(slot)]
            if normalized_slot is not None and isinstance(position, dict)
        ]
    return []


def _route_sort_key(route_id: str) -> tuple[int, str]:
    try:
        return ROUTE_SORT_ORDER.index(route_id), route_id
    except ValueError:
        return len(ROUTE_SORT_ORDER), route_id


def _endpoint_ids_in_sequence(sequence: list[dict[str, Any]]) -> list[str]:
    endpoint_ids: list[str] = []
    for item in sequence:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("branches"), dict):
            for branch in item["branches"].get("items") or []:
                if isinstance(branch, dict):
                    for endpoint_id in _endpoint_ids_in_sequence(branch.get("sequence") or []):
                        if endpoint_id not in endpoint_ids:
                            endpoint_ids.append(endpoint_id)
            continue
        endpoint_id = _clean_identifier(item.get("endpoint_id"))
        if endpoint_id and endpoint_id not in endpoint_ids:
            endpoint_ids.append(endpoint_id)
    return endpoint_ids


def _component_payload_from_element_reference(
    element_id: str,
    optical_path_elements: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    element = optical_path_elements.get(element_id) or {}
    if isinstance(element.get("component"), dict):
        return _component_payload(element.get("component"), default_name=element.get("name") or element_id)
    if isinstance(element.get("dichroic"), dict):
        return _component_payload(element.get("dichroic"), default_name=element.get("name") or element_id)
    positions = element.get("positions")
    if isinstance(positions, dict):
        first_position = next((value for _, value in sorted(positions.items(), key=lambda item: str(item[0])) if isinstance(value, dict)), None)
        if isinstance(first_position, dict):
            if isinstance(first_position.get("component"), dict):
                return _component_payload(first_position["component"], default_name=element.get("name") or element_id)
            linked = first_position.get("emission_filter") or first_position.get("dichroic") or first_position.get("excitation_filter")
            if isinstance(linked, dict):
                return _component_payload(linked, default_name=element.get("name") or element_id)
    return {}


def _iter_element_positions(element: dict[str, Any]) -> list[tuple[str, int | None, dict[str, Any]]]:
    positions = element.get("positions")
    candidates: list[tuple[str, int | None, dict[str, Any]]] = []
    if isinstance(positions, dict):
        for raw_key, position in positions.items():
            if not isinstance(position, dict):
                continue
            key_text = str(raw_key)
            slot = _coerce_slot_key(position.get("slot"))
            if slot is None:
                slot = _coerce_slot_key(raw_key)
            candidates.append((key_text, slot, position))
    elif isinstance(positions, list):
        for idx, position in enumerate(positions, start=1):
            if not isinstance(position, dict):
                continue
            key_text = _clean_string(position.get("position_key")) or str(position.get("slot") or idx)
            slot = _coerce_slot_key(position.get("slot"))
            candidates.append((key_text, slot, position))
    candidates.sort(key=lambda item: (item[1] is None, item[1] if item[1] is not None else 0, item[0]))
    return candidates


def _resolve_positioned_component_from_element(
    element: dict[str, Any],
    *,
    position_id: str = "",
) -> tuple[dict[str, Any], str | None, str | None, str | None]:
    position_candidates = _iter_element_positions(element)
    requested = _clean_string(position_id)
    requested_identifier = _clean_identifier(position_id)
    requested_slot = _coerce_slot_key(position_id)

    selected_key: str | None = None
    selected_slot: int | None = None
    selected_position: dict[str, Any] | None = None
    if requested and position_candidates:
        for key_text, slot, position in position_candidates:
            position_key = _clean_string(position.get("position_key"))
            identifiers = {
                _clean_identifier(key_text),
                _clean_identifier(position_key),
                _clean_identifier(position.get("id")),
            }
            key_matches = (
                requested == key_text
                or requested == position_key
                or (requested_identifier and requested_identifier in identifiers)
            )
            slot_matches = requested_slot is not None and slot == requested_slot
            if key_matches or slot_matches:
                selected_key = key_text
                selected_slot = slot
                selected_position = position
                break

    if selected_position is None and position_candidates:
        selected_key, selected_slot, selected_position = position_candidates[0]

    if isinstance(selected_position, dict):
        if isinstance(selected_position.get("component"), dict):
            component_payload = _component_payload(
                selected_position["component"],
                default_name=element.get("name") or element.get("display_label") or element.get("id") or "",
            )
        elif any(isinstance(selected_position.get(link_key), dict) for link_key in CUBE_LINK_KEYS):
            component_payload = dict(selected_position)
            component_payload.setdefault("component_type", "filter_cube")
            component_payload.setdefault("type", component_payload.get("component_type"))
            component_payload.setdefault("label", _clean_string(selected_position.get("label") or selected_position.get("name")))
            component_payload.setdefault("display_label", _clean_string(selected_position.get("display_label") or selected_position.get("label") or selected_position.get("name")))
            component_payload.setdefault("spectral_ops", _cube_spectral_ops(component_payload))
        else:
            component_payload = _component_payload(
                selected_position,
                default_name=element.get("name") or element.get("display_label") or element.get("id") or "",
            )
        position_key = _clean_string(selected_position.get("position_key")) or selected_key
        resolved_position_id = requested or (str(selected_slot) if selected_slot is not None else position_key)
        position_label = (
            _clean_string(selected_position.get("display_label"))
            or _clean_string(selected_position.get("label"))
            or _clean_string(selected_position.get("name"))
            or _clean_string(component_payload.get("display_label"))
            or _clean_string(component_payload.get("label"))
            or None
        )
        return component_payload, resolved_position_id or None, position_key or None, position_label

    component_payload = _component_payload_from_element_reference(_clean_identifier(element.get("id")), {element.get("id"): element})
    return component_payload, None, None, None


def _collect_route_owned_splitters(
    light_paths: list[dict[str, Any]],
    elements: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    element_lookup = {entry.get("id"): entry for entry in elements if isinstance(entry, dict) and entry.get("id")}
    endpoint_lookup = {entry.get("id"): entry for entry in endpoints if isinstance(entry, dict) and entry.get("id")}
    splitters: dict[str, dict[str, Any]] = {}

    def ensure_splitter(element_id: str, selection_mode: str, route_id: str) -> dict[str, Any]:
        element = element_lookup.get(element_id) or {}
        splitter = splitters.setdefault(
            element_id,
            {
                "id": element_id,
                "name": element.get("name") or element.get("display_label") or element_id,
                "display_label": element.get("display_label") or element.get("name") or element_id,
                "selection_mode": selection_mode or _clean_string(element.get("selection_mode")).lower() or "exclusive",
                "branch_selection_required": (selection_mode or _clean_string(element.get("selection_mode")).lower() or "exclusive") == "exclusive",
                "branches": [],
                "__branch_index": {},
                "routes": [],
                "path": route_id,
            },
        )
        if route_id and route_id not in splitter["routes"]:
            splitter["routes"].append(route_id)
        if not splitter.get("path") and route_id:
            splitter["path"] = route_id
        return splitter

    def attach_sequence(sequence: list[dict[str, Any]], route_id: str) -> None:
        last_element_id = ""
        for item in sequence:
            if not isinstance(item, dict):
                continue
            element_id = _clean_identifier(item.get("optical_path_element_id"))
            if element_id:
                last_element_id = element_id
                continue
            branch_block = item.get("branches")
            if not isinstance(branch_block, dict) or not last_element_id:
                continue
            splitter = ensure_splitter(last_element_id, _clean_string(branch_block.get("selection_mode")).lower(), route_id)
            branch_index: dict[str, int] = splitter["__branch_index"]
            for branch_position, branch in enumerate(branch_block.get("items") or [], start=1):
                if not isinstance(branch, dict):
                    continue
                branch_id = _clean_identifier(branch.get("branch_id")) or f"branch_{branch_position}"
                dedupe_key = branch_id
                if dedupe_key in branch_index:
                    branch_payload = splitter["branches"][branch_index[dedupe_key]]
                else:
                    branch_payload = {
                        "id": branch_id,
                        "label": branch.get("label") or _resolve_route_label(branch_id),
                        "target_ids": [],
                        "sequence": json.loads(json.dumps(branch.get("sequence") or [])),
                        "__routes": [route_id] if route_id else [],
                    }
                    if branch.get("mode"):
                        branch_payload["mode"] = branch.get("mode")
                    component = next(
                        (
                            _component_payload_from_element_reference(_clean_identifier(step.get("optical_path_element_id")), element_lookup)
                            for step in branch.get("sequence") or []
                            if isinstance(step, dict) and step.get("optical_path_element_id")
                        ),
                        {},
                    )
                    if component:
                        branch_payload["component"] = component
                    splitter["branches"].append(branch_payload)
                    branch_index[dedupe_key] = len(splitter["branches"]) - 1
                for endpoint_id in _endpoint_ids_in_sequence(branch.get("sequence") or []):
                    if endpoint_id in endpoint_lookup and endpoint_id not in branch_payload["target_ids"]:
                        branch_payload["target_ids"].append(endpoint_id)
                if route_id and route_id not in branch_payload["__routes"]:
                    branch_payload["__routes"].append(route_id)

    for route in light_paths:
        if not isinstance(route, dict):
            continue
        route_id = _clean_identifier(route.get("id"))
        attach_sequence(route.get("illumination_sequence") or [], route_id)
        attach_sequence(route.get("detection_sequence") or [], route_id)

    ordered: list[dict[str, Any]] = []
    for splitter in splitters.values():
        splitter.pop("__branch_index", None)
        ordered.append(splitter)
    return ordered


def _route_catalog_entries(payload: dict[str, Any]) -> list[dict[str, str]]:
    constrained_routes: set[str] = set()

    def collect_from_component(component: Any) -> None:
        if not isinstance(component, dict):
            return
        constrained_routes.update(
            route for route in _normalize_routes(component.get("routes") or component.get("path") or component.get("paths") or component.get("route"))
            if route not in {"shared", "all"}
        )
        linked_components = component.get("linked_components")
        if isinstance(linked_components, dict):
            for linked in linked_components.values():
                collect_from_component(linked)

    for mechanism in payload.get("light_sources", []) or []:
        if isinstance(mechanism, dict):
            for position in _choice_positions(mechanism):
                collect_from_component(position)

    for mechanism in payload.get("detectors", []) or []:
        if isinstance(mechanism, dict):
            for position in _choice_positions(mechanism):
                collect_from_component(position)

    for terminal in payload.get("terminals", []) or []:
        collect_from_component(terminal)

    stages = payload.get("stages") if isinstance(payload.get("stages"), dict) else {}
    for stage_name in ("excitation", "dichroic", "emission", "cube"):
        for mechanism in stages.get(stage_name, []) if isinstance(stages, dict) else []:
            if not isinstance(mechanism, dict):
                continue
            collect_from_component(mechanism)
            for position in _choice_positions(mechanism):
                collect_from_component(position)

    for splitter in payload.get("splitters", []) or []:
        if not isinstance(splitter, dict):
            continue
        collect_from_component(splitter)
        for branch in splitter.get("branches", []) or []:
            if isinstance(branch, dict):
                collect_from_component(branch)
                collect_from_component(branch.get("component"))

    return [
        {
            "id": route_id,
            "label": _resolve_route_label(route_id),
        }
        for route_id in sorted(constrained_routes, key=_route_sort_key)
    ]



def calculate_valid_paths(payload: dict) -> list[dict[str, int]]:
    """Calculate mechanically valid stage combinations for single-choice selectors.

    Light sources and detectors are multi-select in the browser runtime, so `valid_paths`
    focuses on route-compatible stage selectors. The browser still uses route tags to
    constrain multi-select controls.
    """
    stages = payload.get("stages", {})
    if not isinstance(stages, dict):
        return []

    discrete_choices: list[tuple[str, str, list[dict[str, Any]]]] = []
    for stage_name in ("excitation", "dichroic", "emission", "cube", "analyzer"):
        mechanisms = stages.get(stage_name, [])
        if not isinstance(mechanisms, list):
            continue

        for mechanism in mechanisms:
            if not isinstance(mechanism, dict):
                continue
            mechanism_id = mechanism.get("id")
            positions = _choice_positions(mechanism)
            if isinstance(mechanism_id, str) and positions:
                discrete_choices.append((stage_name, mechanism_id, positions))

    if not discrete_choices:
        return []

    valid_paths: list[dict[str, int]] = []
    for combination in product(*(choices for _, _, choices in discrete_choices)):
        if any(str(selection.get("type") or selection.get("component_type")) == "block" for selection in combination):
            continue

        combined_routes: set[str] = set()
        for (_, _, _), selection in zip(discrete_choices, combination):
            combined_routes.update(_route_tags(selection))

        if not _routes_compatible(combined_routes):
            continue

        valid_paths.append({
            mech_id: int(selection["slot"])
            for (_, mech_id, _), selection in zip(discrete_choices, combination)
        })

    return valid_paths



def _splitter_payload(index: int, splitter: dict[str, Any], terminals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    name = splitter.get("name", f"Splitter {index + 1}")
    dichroic_component = splitter.get("dichroic", {}).copy() if isinstance(splitter.get("dichroic"), dict) else {}
    if "cut_on_nm" in dichroic_component and "cutoffs_nm" not in dichroic_component:
        dichroic_component["cutoffs_nm"] = [dichroic_component["cut_on_nm"]]

    routes = _normalize_routes(splitter.get("path") or splitter.get("paths") or splitter.get("route") or splitter.get("routes"))
    candidate_terminals = _candidate_terminals_for_routes(terminals or [], routes)

    dichroic_pos = _component_payload(dichroic_component, default_name="Splitter Dichroic") if dichroic_component else {}

    def branch_component(raw_branch: dict[str, Any], *, default_name: str, branch_mode: str) -> dict[str, Any]:
        component = raw_branch.get("emission_filter") if isinstance(raw_branch.get("emission_filter"), dict) else raw_branch.get("component")
        if not isinstance(component, dict):
            component = {}
        return _component_payload(component, default_name=default_name, branch_mode=branch_mode)

    def branch_targets(raw_branch: dict[str, Any]) -> list[str]:
        return _resolve_target_ids(
            raw_branch.get("targets")
            or raw_branch.get("target_ids")
            or raw_branch.get("terminal_ids")
            or raw_branch.get("endpoint_ids")
            or raw_branch.get("target")
            or raw_branch.get("endpoint"),
            candidate_terminals or (terminals or []),
        )

    branches: list[dict[str, Any]] = []
    raw_branches = splitter.get("branches") if isinstance(splitter.get("branches"), list) else []
    if raw_branches:
        for branch_index, raw_branch in enumerate(raw_branches, start=1):
            if not isinstance(raw_branch, dict):
                continue
            mode = _clean_string(raw_branch.get("mode")).lower() or ("transmitted" if branch_index == 1 else "reflected")
            component = branch_component(raw_branch, default_name=f"Branch {branch_index} Filter", branch_mode=mode)
            branch_payload = {
                "id": _clean_identifier(raw_branch.get("id")) or f"splitter_{index}_branch_{branch_index}",
                "label": _clean_string(raw_branch.get("name") or raw_branch.get("label")) or f"Branch {branch_index}",
                "mode": mode,
                "component": component,
                "target_ids": branch_targets(raw_branch),
            }
            if routes:
                branch_payload["routes"] = list(routes)
                branch_payload["path"] = routes[0]
            branches.append(branch_payload)

    display_parts = []
    if dichroic_pos:
        display_parts.append(f"Di: {dichroic_pos.get('label')}")
    for branch in branches:
        branch_label = branch.get("component", {}).get("label") if isinstance(branch.get("component"), dict) else ""
        if branch_label:
            display_parts.append(f"{branch.get('label')}: {branch_label}")

    # `path1` / `path2` remain in the derived splitter payload only as an explicit
    # compatibility adapter for older runtime/app consumers. Canonical authoring truth
    # lives in `branches` plus the ordered `light_paths` sequences.
    path1_pos = branches[0].get("component") if branches else {}
    path2_pos = branches[1].get("component") if len(branches) > 1 else {}

    splitter_payload = {
        "id": f"splitter_{index}",
        "name": name,
        "display_label": " | ".join(part for part in display_parts if part) or name,
        "dichroic": {
            "name": "Splitter Dichroic",
            "positions": {1: dichroic_pos} if dichroic_pos else {},
        },
        "path1": {
            "name": branches[0].get("label") if branches else "Path 1 (Transmitted)",
            "positions": {1: path1_pos} if isinstance(path1_pos, dict) else {},
        },
        "path2": {
            "name": branches[1].get("label") if len(branches) > 1 else "Path 2 (Reflected)",
            "positions": {1: path2_pos} if isinstance(path2_pos, dict) else {},
        },
        "branches": branches,
        "control_kind": "dropdown",
        "control_label": name,
        "branch_selection_required": any(not branch.get("target_ids") for branch in branches) and len(branches) > 1,
    }
    if routes:
        splitter_payload["routes"] = routes
        splitter_payload["path"] = routes[0]
    if isinstance(splitter.get("notes"), str) and splitter["notes"].strip():
        splitter_payload["notes"] = splitter["notes"].strip()
    splitter_payload["options"] = [
        {
            "slot": 1,
            "display_label": splitter_payload["display_label"] or name,
            "value": {
                "id": splitter_payload["id"],
                "label": splitter_payload["display_label"] or name,
                "dichroic": splitter_payload["dichroic"],
                "path1": splitter_payload["path1"],
                "path2": splitter_payload["path2"],
                "branches": branches,
                "branch_selection_required": splitter_payload["branch_selection_required"],
            },
        }
    ]
    return splitter_payload


def _component_inventory_key(component_type: str, component_id: str) -> str:
    return f"{component_type}:{component_id}"


def _component_inventory_class(component_type: str, row: dict[str, Any]) -> str:
    if component_type == "source":
        return "light_source"
    if component_type == "endpoint":
        endpoint_type = _normalize_endpoint_type(row.get("endpoint_type") or row.get("type") or row.get("kind"))
        if endpoint_type == "eyepiece":
            return "eyepiece"
        if endpoint_type == "camera_port":
            return "camera_port"
        return "endpoint"
    stage_role = _clean_string(row.get("stage_role")).lower()
    if stage_role == "splitter":
        return "splitter"
    return "optical_element"


def _component_display_label(component_type: str, row: dict[str, Any]) -> str:
    if component_type == "source":
        wavelength = row.get("wavelength_nm") or row.get("wavelength")
        parts = []
        if wavelength not in (None, ""):
            parts.append(_format_numeric(wavelength) + " nm")
        parts.extend(
            part
            for part in (
                _clean_string(row.get("kind") or row.get("type")),
                _clean_string(row.get("manufacturer")),
                _clean_string(row.get("model")),
            )
            if part
        )
        return _clean_string(row.get("display_label") or row.get("name") or " ".join(parts) or row.get("id"))
    return _clean_string(
        row.get("display_label")
        or row.get("name")
        or " ".join(
            part for part in (_clean_string(row.get("manufacturer")), _clean_string(row.get("model"))) if part
        )
        or row.get("model")
        or row.get("id")
    )


def _inventory_metadata(component_type: str, row: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if component_type == "source":
        source_meta = {
            key: row.get(key)
            for key in (
                "kind",
                "technology",
                "role",
                "timing_mode",
                "wavelength_nm",
                "tunable_min_nm",
                "tunable_max_nm",
                "power",
                "pulse_width_ps",
                "repetition_rate_mhz",
                "depletion_targets_nm",
            )
            if row.get(key) not in (None, "", [])
        }
        if source_meta:
            metadata["source_metadata"] = source_meta
        return metadata
    if component_type == "endpoint":
        endpoint_meta = {
            key: row.get(key)
            for key in (
                "endpoint_type",
                "source_section",
                "channel_name",
                "details",
                "kind",
                "min_nm",
                "max_nm",
                "collection_min_nm",
                "collection_max_nm",
            )
            if row.get(key) not in (None, "", [])
        }
        if endpoint_meta:
            metadata["endpoint_metadata"] = endpoint_meta
        return metadata
    optical_meta = {
        key: row.get(key)
        for key in (
            "stage_role",
            "element_type",
            "selection_mode",
            "supported_branch_modes",
            "supported_branch_count",
            "component_type",
            "center_nm",
            "width_nm",
            "cut_on_nm",
            "cut_off_nm",
            "cutoffs_nm",
            "bands",
            "transmission_bands",
            "reflection_bands",
        )
        if row.get(key) not in (None, "", [])
    }
    if optical_meta:
        metadata["optical_element_metadata"] = optical_meta
    return metadata


def _build_hardware_inventory(
    sources: list[dict[str, Any]],
    elements: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    by_inventory_id: dict[str, int] = {}
    by_ref: dict[str, str] = {}
    by_hardware_id: dict[str, int] = {}
    ordered_rows = [
        *[("source", row) for row in sources if isinstance(row, dict)],
        *[("optical_path_element", row) for row in elements if isinstance(row, dict)],
        *[("endpoint", row) for row in endpoints if isinstance(row, dict)],
    ]

    for display_number, (component_type, row) in enumerate(ordered_rows, start=1):
        component_id = _clean_identifier(row.get("id"))
        if not component_id:
            continue
        inventory_id = _component_inventory_key(component_type, component_id)
        modalities = _normalize_modalities(row.get("modalities") or row.get("path") or row.get("routes"))
        item = {
            "id": inventory_id,
            "hardware_id": component_id,
            "component_type": component_type,
            "inventory_class": _component_inventory_class(component_type, row),
            "manufacturer": _clean_string(row.get("manufacturer")),
            "model": _clean_string(row.get("model")),
            "product_code": _clean_string(row.get("product_code")),
            "display_label": _component_display_label(component_type, row),
            "display_number": display_number,
            "modalities": modalities,
            "source_ref": {"component_type": component_type, "id": component_id},
            "inventory_identity": {
                "inventory_id": inventory_id,
                "hardware_id": component_id,
                "component_type": component_type,
            },
        }
        item.update(_inventory_metadata(component_type, row))
        if _clean_string(row.get("name")):
            item["name"] = _clean_string(row.get("name"))
        if _clean_string(row.get("notes")):
            item["notes"] = _clean_string(row.get("notes"))
        inventory.append(item)
        by_inventory_id[inventory_id] = display_number
        by_ref[inventory_id] = inventory_id
        by_hardware_id[component_id] = display_number

    return inventory, {"by_inventory_id": by_inventory_id, "by_ref": by_ref, "by_hardware_id": by_hardware_id}


def _resolve_graph_component(
    ref_key: str,
    ref_id: str,
    *,
    source_lookup: dict[str, dict[str, Any]],
    element_lookup: dict[str, dict[str, Any]],
    endpoint_lookup: dict[str, dict[str, Any]],
    inventory_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    component_type = "source" if ref_key == "source_id" else "endpoint" if ref_key == "endpoint_id" else "optical_path_element"
    if component_type == "source":
        row = source_lookup.get(ref_id) or {}
    elif component_type == "endpoint":
        row = endpoint_lookup.get(ref_id) or {}
    else:
        row = element_lookup.get(ref_id) or {}
    inventory_id = _component_inventory_key(component_type, ref_id)
    inventory_item = inventory_lookup.get(inventory_id) or {}
    resolved = {
        "kind": component_type,
        "id": ref_id,
        "hardware_inventory_id": inventory_id if inventory_item else "",
        "display_label": inventory_item.get("display_label") or _component_display_label(component_type, row) or ref_id,
        "display_number": inventory_item.get("display_number"),
        "inventory_display_number": inventory_item.get("display_number"),
        "inventory_identity": json.loads(json.dumps(inventory_item.get("inventory_identity") or {})),
        "modalities": inventory_item.get("modalities") or _normalize_modalities(row.get("modalities") or row.get("path") or row.get("routes")),
    }
    if component_type == "optical_path_element":
        resolved["stage_role"] = _clean_string(row.get("stage_role") or row.get("element_type")).lower()
        resolved["element_type"] = _clean_string(row.get("element_type") or row.get("type"))
    if component_type == "endpoint":
        resolved["endpoint_type"] = _normalize_endpoint_type(row.get("endpoint_type") or row.get("type") or row.get("kind"))
    if component_type == "source":
        resolved["role"] = _clean_string(row.get("role")).lower()
    return resolved


def _build_route_steps(
    illumination_traversal: list[dict[str, Any]],
    detection_traversal: list[dict[str, Any]],
    *,
    source_lookup: dict[str, dict[str, Any]],
    element_lookup: dict[str, dict[str, Any]],
    endpoint_lookup: dict[str, dict[str, Any]],
    inventory_lookup: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Build the authoritative ordered route-step contract.

    Combines illumination traversal, a sample step, and detection traversal
    into a single ordered list.  Each step carries its phase, kind, component
    identity, authored metadata, and parser-computed spectral_ops so the
    browser runtime never needs to infer optical meaning.

    Returns ``(steps, warnings)`` where *warnings* lists any issues discovered
    while building the contract.
    """
    steps: list[dict[str, Any]] = []
    warnings: list[str] = []
    order = 0

    def _step_kind(entry: dict[str, Any]) -> str:
        kind = entry.get("kind", "")
        if kind == "source":
            return "source"
        if kind == "endpoint":
            return "detector"
        if kind == "branch_block":
            return "routing_component"
        return "optical_component"

    def _component_metadata(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "manufacturer": _clean_string(row.get("manufacturer")) or None,
            "model": _clean_string(row.get("model")) or None,
            "product_code": _clean_string(row.get("product_code")) or None,
        }

    def _lookup_row(entry: dict[str, Any]) -> dict[str, Any]:
        ref_id = entry.get("id", "")
        kind = entry.get("kind", "")
        if kind == "source":
            return source_lookup.get(ref_id, {})
        if kind == "endpoint":
            return endpoint_lookup.get(ref_id, {})
        return element_lookup.get(ref_id, {})

    def _resolved_step_payload(entry: dict[str, Any]) -> tuple[dict[str, Any], str | None, str | None, str | None]:
        entry_kind = entry.get("kind", "")
        row = _lookup_row(entry)
        if entry_kind in {"source", "endpoint"}:
            payload = row if isinstance(row, dict) else {}
            return payload, None, None, None

        element_row = row if isinstance(row, dict) else {}
        component_payload, position_id, position_key, position_label = _resolve_positioned_component_from_element(
            element_row,
            position_id=_clean_string(entry.get("position_id")),
        )
        return component_payload, position_id, position_key, position_label

    def _process_entries(entries: list[dict[str, Any]], phase: str) -> None:
        nonlocal order
        def _routing_branch_sequence(sequence: Any) -> list[dict[str, Any]]:
            normalized: list[dict[str, Any]] = []
            for seq_step in sequence or []:
                if not isinstance(seq_step, dict):
                    continue
                seq_kind = _clean_string(seq_step.get("kind")).lower()
                seq_id = _clean_identifier(seq_step.get("id"))
                if seq_kind == "source":
                    normalized.append(
                        {
                            "kind": "source",
                            "source_id": seq_id or None,
                            "component_id": seq_id or None,
                            "display_label": seq_step.get("display_label"),
                        }
                    )
                    continue
                if seq_kind == "endpoint":
                    normalized.append(
                        {
                            "kind": "detector",
                            "detector_id": seq_id or None,
                            "endpoint_id": seq_id or None,
                            "component_id": seq_id or None,
                            "display_label": seq_step.get("display_label"),
                        }
                    )
                    continue
                row = element_lookup.get(seq_id or "", {})
                component_payload, position_id, position_key, position_label = _resolve_positioned_component_from_element(
                    row if isinstance(row, dict) else {},
                    position_id=_clean_string(seq_step.get("position_id")),
                )
                normalized.append(
                    {
                        "kind": "optical_component",
                        "component_id": seq_id or None,
                        "display_label": seq_step.get("display_label"),
                        "position_id": position_id,
                        "position_key": position_key,
                        "position_label": position_label,
                        "spectral_ops": component_payload.get("spectral_ops"),
                        "unsupported_reason": "unsupported_spectral_model" if component_payload.get("_unsupported_spectral_model") else None,
                    }
                )
            return normalized

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            entry_kind = entry.get("kind", "")

            if entry_kind == "branch_block":
                step: dict[str, Any] = {
                    "step_id": f"{phase}-step-{order}",
                    "order": order,
                    "phase": phase,
                    "kind": "routing_component",
                    "component_id": entry.get("id"),
                    "routing": {
                        "selection_mode": entry.get("selection_mode"),
                        "branches": [
                            {
                                "branch_id": br.get("branch_id"),
                                "label": br.get("label"),
                                "mode": br.get("mode"),
                                "sequence": _routing_branch_sequence(br.get("sequence")),
                            }
                            for br in (entry.get("branches") or [])
                            if isinstance(br, dict)
                        ],
                    },
                    "spectral_ops": None,
                    "metadata": {},
                    "unsupported_reason": None,
                }
                steps.append(step)
                order += 1
                continue

            row = _lookup_row(entry)
            inventory_id = entry.get("hardware_inventory_id", "")
            inventory_item = inventory_lookup.get(inventory_id, {})
            component_type = _clean_string(row.get("component_type") or row.get("type") or row.get("element_type") or "").lower()
            stage_role = _clean_string(row.get("stage_role") or row.get("element_type") or "").lower()
            component_payload, position_id, position_key, position_label = _resolved_step_payload(entry)
            selected_component_type = _clean_string(component_payload.get("component_type") or component_payload.get("type")).lower()
            step = {
                "step_id": f"{phase}-step-{order}",
                "order": order,
                "phase": phase,
                "kind": _step_kind(entry),
                "component_id": entry.get("id"),
                "source_id": entry.get("id") if entry_kind == "source" else None,
                "detector_id": entry.get("id") if entry_kind == "endpoint" else None,
                "endpoint_id": entry.get("id") if entry_kind == "endpoint" else None,
                "hardware_inventory_id": inventory_id or None,
                "component_type": selected_component_type or component_type or stage_role or None,
                "stage_role": stage_role or None,
                "display_label": entry.get("display_label"),
                "position_id": position_id,
                "position_key": position_key,
                "position_label": position_label,
                "spectral_ops": component_payload.get("spectral_ops"),
                "routing": None,
                "metadata": _component_metadata(inventory_item) if inventory_item else _component_metadata(row),
                "unsupported_reason": None,
            }
            if entry_kind == "endpoint":
                endpoint_type = _normalize_endpoint_type(row.get("endpoint_type") or row.get("type") or row.get("kind"))
                step["endpoint_type"] = endpoint_type
            if component_payload.get("_unsupported_spectral_model"):
                step["unsupported_reason"] = "unsupported_spectral_model"

            steps.append(step)
            order += 1

    _process_entries(illumination_traversal, "illumination")

    steps.append({
        "step_id": f"sample-step-{order}",
        "order": order,
        "phase": "sample",
        "kind": "sample",
        "component_id": "sample_plane",
        "source_id": None,
        "detector_id": None,
        "endpoint_id": None,
        "position_id": None,
        "position_key": None,
        "position_label": None,
        "component_type": "sample",
        "stage_role": "sample",
        "spectral_ops": None,
        "routing": None,
        "metadata": {},
        "unsupported_reason": None,
    })
    order += 1

    _process_entries(detection_traversal, "detection")

    return steps, warnings


def _build_route_sequences_and_graph(
    route: dict[str, Any],
    *,
    source_lookup: dict[str, dict[str, Any]],
    element_lookup: dict[str, dict[str, Any]],
    endpoint_lookup: dict[str, dict[str, Any]],
    inventory_lookup: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    graph_nodes: list[dict[str, Any]] = []
    graph_edges: list[dict[str, Any]] = []
    usage = {
        "route_id": route.get("id"),
        "route_label": route.get("name"),
        "illumination_hardware_inventory_ids": [],
        "detection_hardware_inventory_ids": [],
        "hardware_inventory_ids": [],
        "endpoint_inventory_ids": [],
        "branch_blocks": [],
    }
    usage_seen: set[str] = set()
    endpoint_seen: set[str] = set()
    node_counter = 0
    edge_counter = 0
    branch_counter = 0

    def register_usage(inventory_id: str, phase: str) -> None:
        if not inventory_id:
            return
        if inventory_id not in usage_seen:
            usage["hardware_inventory_ids"].append(inventory_id)
            usage_seen.add(inventory_id)
        phase_key = "illumination_hardware_inventory_ids" if phase == "illumination" else "detection_hardware_inventory_ids"
        if inventory_id not in usage[phase_key]:
            usage[phase_key].append(inventory_id)
        if inventory_id.startswith("endpoint:") and inventory_id not in endpoint_seen:
            usage["endpoint_inventory_ids"].append(inventory_id)
            endpoint_seen.add(inventory_id)

    def add_graph_node(resolved: dict[str, Any], *, phase: str, column: int, lane: int) -> str:
        nonlocal node_counter
        node_counter += 1
        node_id = f"{route['id']}_{phase}_{node_counter}"
        graph_nodes.append(
            {
                "id": node_id,
                "route_id": route["id"],
                "phase": phase,
                "component_kind": resolved.get("kind"),
                "hardware_inventory_id": resolved.get("hardware_inventory_id") or None,
                "hardware_id": resolved.get("id"),
                "label": resolved.get("display_label"),
                "display_number": resolved.get("display_number"),
                "inventory_display_number": resolved.get("inventory_display_number"),
                "inventory_identity": json.loads(json.dumps(resolved.get("inventory_identity") or {})),
                "graph_occurrence": {
                    "node_id": node_id,
                    "route_id": route["id"],
                    "phase": phase,
                    "column": column,
                    "lane": lane,
                },
                "stage_role": resolved.get("stage_role"),
                "endpoint_type": resolved.get("endpoint_type"),
                "column": column,
                "lane": lane,
            }
        )
        register_usage(resolved.get("hardware_inventory_id") or "", phase)
        return node_id

    def add_graph_edge(source_id: str, target_id: str, *, branch_id: str = "", label: str = "") -> None:
        nonlocal edge_counter
        edge_counter += 1
        graph_edges.append(
            {
                "id": f"{route['id']}_edge_{edge_counter}",
                "route_id": route["id"],
                "source": source_id,
                "target": target_id,
                "branch_id": branch_id or None,
                "label": label,
            }
        )

    def resolve_step(step: dict[str, Any]) -> dict[str, Any]:
        if step.get("source_id"):
            return _resolve_graph_component(
                "source_id",
                _clean_identifier(step.get("source_id")),
                source_lookup=source_lookup,
                element_lookup=element_lookup,
                endpoint_lookup=endpoint_lookup,
                inventory_lookup=inventory_lookup,
            )
        if step.get("endpoint_id"):
            return _resolve_graph_component(
                "endpoint_id",
                _clean_identifier(step.get("endpoint_id")),
                source_lookup=source_lookup,
                element_lookup=element_lookup,
                endpoint_lookup=endpoint_lookup,
                inventory_lookup=inventory_lookup,
            )
        return _resolve_graph_component(
            "optical_path_element_id",
            _clean_identifier(step.get("optical_path_element_id")),
            source_lookup=source_lookup,
            element_lookup=element_lookup,
            endpoint_lookup=endpoint_lookup,
            inventory_lookup=inventory_lookup,
        )

    def walk_sequence(
        sequence: list[dict[str, Any]],
        *,
        phase: str,
        prev_node_id: str | None,
        column: int,
        lane: int,
    ) -> tuple[list[dict[str, Any]], str | None, int]:
        nonlocal branch_counter
        resolved_steps: list[dict[str, Any]] = []
        current_prev = prev_node_id
        current_column = column
        for step in sequence:
            if not isinstance(step, dict):
                continue
            branch_block = step.get("branches")
            if isinstance(branch_block, dict):
                branch_counter += 1
                branch_block_id = f"{route['id']}_branch_block_{branch_counter}"
                resolved_branches: list[dict[str, Any]] = []
                branch_columns: list[int] = [current_column]
                for branch_index, branch in enumerate(branch_block.get("items") or [], start=1):
                    if not isinstance(branch, dict):
                        continue
                    branch_id = _clean_identifier(branch.get("branch_id")) or f"branch_{branch_index}"
                    branch_label = _clean_string(branch.get("label")) or _resolve_route_label(branch_id)
                    branch_sequence, branch_tail_id, branch_column = walk_sequence(
                        branch.get("sequence") or [],
                        phase=phase,
                        prev_node_id=current_prev,
                        column=current_column + 1,
                        lane=lane + branch_index - 1,
                    )
                    branch_columns.append(branch_column)
                    branch_inventory_ids = [
                        item.get("hardware_inventory_id")
                        for item in branch_sequence
                        if isinstance(item, dict) and item.get("hardware_inventory_id")
                    ]
                    branch_endpoint_ids = [
                        item.get("hardware_inventory_id")
                        for item in branch_sequence
                        if isinstance(item, dict) and item.get("kind") == "endpoint" and item.get("hardware_inventory_id")
                    ]
                    resolved_branches.append(
                        {
                            "branch_id": branch_id,
                            "label": branch_label,
                            "mode": _clean_string(branch.get("mode")).lower() or None,
                            "sequence": branch_sequence,
                            "tail_node_id": branch_tail_id,
                            "hardware_inventory_ids": branch_inventory_ids,
                            "endpoint_inventory_ids": branch_endpoint_ids,
                        }
                    )
                usage["branch_blocks"].append(
                    {
                        "id": branch_block_id,
                        "selection_mode": _clean_string(branch_block.get("selection_mode")).lower() or "exclusive",
                        "branches": [
                            {
                                "branch_id": branch["branch_id"],
                                "label": branch["label"],
                                "mode": branch.get("mode"),
                                "hardware_inventory_ids": list(branch.get("hardware_inventory_ids") or []),
                                "endpoint_inventory_ids": list(branch.get("endpoint_inventory_ids") or []),
                            }
                            for branch in resolved_branches
                        ],
                    }
                )
                resolved_steps.append(
                    {
                        "kind": "branch_block",
                        "id": branch_block_id,
                        "selection_mode": _clean_string(branch_block.get("selection_mode")).lower() or "exclusive",
                        "branches": resolved_branches,
                        "hardware_inventory_ids": sorted(
                            {
                                hardware_id
                                for branch in resolved_branches
                                for hardware_id in (branch.get("hardware_inventory_ids") or [])
                            }
                        ),
                        "endpoint_inventory_ids": sorted(
                            {
                                endpoint_id
                                for branch in resolved_branches
                                for endpoint_id in (branch.get("endpoint_inventory_ids") or [])
                            }
                        ),
                    }
                )
                current_column = max(branch_columns) if branch_columns else current_column
                continue

            ref_key = next((candidate for candidate in ("source_id", "optical_path_element_id", "endpoint_id") if step.get(candidate)), "")
            if not ref_key:
                continue
            resolved = resolve_step(step)
            if ref_key == "optical_path_element_id":
                element_id = _clean_identifier(step.get("optical_path_element_id"))
                element_row = element_lookup.get(element_id, {})
                component_payload, position_id, position_key, position_label = _resolve_positioned_component_from_element(
                    element_row if isinstance(element_row, dict) else {},
                    position_id=_clean_string(step.get("position_id")),
                )
                if position_id:
                    resolved["position_id"] = position_id
                if position_key:
                    resolved["position_key"] = position_key
                if position_label:
                    resolved["position_label"] = position_label
                if component_payload.get("spectral_ops") is not None:
                    resolved["spectral_ops"] = component_payload.get("spectral_ops")
                if component_payload.get("_unsupported_spectral_model"):
                    resolved["_unsupported_spectral_model"] = True
                if _clean_string(component_payload.get("component_type")):
                    resolved["component_type"] = _clean_string(component_payload.get("component_type")).lower()
            node_id = add_graph_node(resolved, phase=phase, column=current_column, lane=lane)
            if current_prev:
                add_graph_edge(current_prev, node_id)
            sequence_ref = {ref_key: resolved.get("id")}
            if ref_key == "optical_path_element_id" and _clean_string(step.get("position_id")):
                sequence_ref["position_id"] = _clean_string(step.get("position_id"))
            resolved_steps.append({**resolved, "node_id": node_id, "sequence_ref": sequence_ref})
            current_prev = node_id
            current_column += 1
        return resolved_steps, current_prev, current_column

    illumination_sequence, illumination_tail, next_column = walk_sequence(
        route.get("illumination_sequence") or [],
        phase="illumination",
        prev_node_id=None,
        column=0,
        lane=0,
    )
    sample_node_id = f"{route['id']}_sample"
    graph_nodes.append(
        {
            "id": sample_node_id,
            "route_id": route["id"],
            "phase": "sample",
            "component_kind": "sample",
            "hardware_inventory_id": None,
            "hardware_id": "sample_plane",
            "label": "Objective / Sample Plane",
            "display_number": None,
            "column": next_column,
            "lane": 0,
        }
    )
    if illumination_tail:
        add_graph_edge(illumination_tail, sample_node_id)
    detection_sequence, _, _ = walk_sequence(
        route.get("detection_sequence") or [],
        phase="detection",
        prev_node_id=sample_node_id,
        column=next_column + 1,
        lane=0,
    )

    route_modalities = _normalize_modalities(route.get("modalities") or route.get("routes") or route.get("path")) or [route.get("id")]
    route_steps, route_warnings = _build_route_steps(
        illumination_sequence,
        detection_sequence,
        source_lookup=source_lookup,
        element_lookup=element_lookup,
        endpoint_lookup=endpoint_lookup,
        inventory_lookup=inventory_lookup,
    )
    resolved_route = {
        **route,
        "route_identity": {
            "id": route.get("id"),
            "name": route.get("name"),
            "modality": route_modalities[0],
            "modalities": route_modalities,
        },
        "illumination_mode": route_modalities[0],
        "modalities": route_modalities,
        "illumination_traversal": illumination_sequence,
        "detection_traversal": detection_sequence,
        "route_steps": route_steps,
        "selected_execution": {
            "contract_version": "selected_execution.v1",
            "steps": json.loads(json.dumps(route_steps)),
            "warnings": list(route_warnings),
            "illumination_traversal": json.loads(json.dumps(illumination_sequence)),
            "detection_traversal": json.loads(json.dumps(detection_sequence)),
        },
        "route_warnings": route_warnings,
        "branch_blocks": list(usage["branch_blocks"]),
        "endpoints": list(usage["endpoint_inventory_ids"]),
        "hardware_inventory_ids": list(usage["hardware_inventory_ids"]),
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
        "graph_tree": {
            "illumination": illumination_sequence,
            "sample": {"node_id": sample_node_id, "label": "Objective / Sample Plane"},
            "detection": detection_sequence,
        },
    }
    return resolved_route, usage


def generate_virtual_microscope_payload(instrument_dict: dict, *, include_inferred_terminals: bool = False, vocab: VocabLookup | None = None) -> dict:
    """Build the authoritative canonical DTO plus explicit downstream projections.

    Top-level DTO fields are the canonical contract consumed across the repository:
    - sources
    - optical_path_elements
    - endpoints (unified normalized endpoint registry)
    - light_paths

    Runtime/UI convenience structures remain available only under
    ``projections.virtual_microscope`` so legacy-style stage buckets and splitter
    renderables are clearly derived adapters rather than co-equal topology truth.
    """
    global _active_vocab
    _prev_vocab = _active_vocab
    _active_vocab = vocab
    try:
        return _generate_virtual_microscope_payload_inner(instrument_dict, include_inferred_terminals=include_inferred_terminals)
    finally:
        _active_vocab = _prev_vocab


def _generate_virtual_microscope_payload_inner(instrument_dict: dict, *, include_inferred_terminals: bool = False) -> dict:
    """Inner implementation — always runs within a vocab context set by the public wrapper."""
    canonical = canonicalize_light_path_model(instrument_dict if isinstance(instrument_dict, dict) else {})
    hardware = instrument_dict.get("hardware") if isinstance(instrument_dict.get("hardware"), dict) else {}
    sources = canonical["sources"]
    elements = canonical["optical_path_elements"]
    endpoints = canonical["endpoints"]
    raw_light_paths = canonical["light_paths"]
    hardware_inventory, hardware_index_map = _build_hardware_inventory(sources, elements, endpoints)
    inventory_lookup = {item["id"]: item for item in hardware_inventory if isinstance(item, dict) and item.get("id")}
    source_lookup = {entry.get("id"): entry for entry in sources if isinstance(entry, dict) and entry.get("id")}
    element_lookup = {entry.get("id"): entry for entry in elements if isinstance(entry, dict) and entry.get("id")}
    endpoint_lookup = {entry.get("id"): entry for entry in endpoints if isinstance(entry, dict) and entry.get("id")}
    light_paths: list[dict[str, Any]] = []
    route_hardware_usage: list[dict[str, Any]] = []
    for route in raw_light_paths:
        if not isinstance(route, dict):
            continue
        resolved_route, usage = _build_route_sequences_and_graph(
            route,
            source_lookup=source_lookup,
            element_lookup=element_lookup,
            endpoint_lookup=endpoint_lookup,
            inventory_lookup=inventory_lookup,
        )
        light_paths.append(resolved_route)
        route_hardware_usage.append(usage)
    route_usage_by_inventory_id: dict[str, list[str]] = {}
    for usage in route_hardware_usage:
        route_id = _clean_string(usage.get("route_id"))
        for inventory_id in usage.get("hardware_inventory_ids") or []:
            route_usage_by_inventory_id.setdefault(inventory_id, [])
            if route_id and route_id not in route_usage_by_inventory_id[inventory_id]:
                route_usage_by_inventory_id[inventory_id].append(route_id)
    for item in hardware_inventory:
        inventory_id = item.get("id")
        if inventory_id:
            item["route_usage_summary"] = route_usage_by_inventory_id.get(inventory_id, [])

    stage_mappings = {"excitation": [], "dichroic": [], "emission": [], "cube": [], "analyzer": []}
    prefix_mappings = {"excitation": "exc", "dichroic": "dichroic", "emission": "em", "cube": "cube", "analyzer": "analyzer"}

    payload: dict[str, Any] = {
        "dto_schema": "light_paths_v2",
        "metadata": {
            "wavelength_grid": {"min_nm": 350, "max_nm": 1700, "step_nm": 2},
            "yaml_source_of_truth": True,
            "topology_contract": "schema -> validator -> canonical dto -> derived adapters -> consumers",
            "authoritative_contract": "canonical_v2_only",
            "selected_execution_contract": "light_paths[].selected_execution",
            "topology_truth": "light_paths",
            "hardware_contract": "hardware_inventory",
            "primary_rendering_contract": {
                "routes": "light_paths",
                "hardware_inventory": "hardware_inventory",
                "hardware_index_map": "hardware_index_map",
                "route_hardware_usage": "route_hardware_usage",
                "normalized_endpoints": "normalized_endpoints",
                "graph_fields": ["graph_nodes", "graph_edges"],
            },
            "graph_incomplete": False,
        },
        "sources": json.loads(json.dumps(sources)),
        "optical_path_elements": json.loads(json.dumps(elements)),
        "endpoints": json.loads(json.dumps(endpoints)),
        "normalized_endpoints": json.loads(json.dumps(endpoints)),
        "hardware_inventory": json.loads(json.dumps(hardware_inventory)),
        "hardware_index_map": json.loads(json.dumps(hardware_index_map)),
        "route_hardware_usage": json.loads(json.dumps(route_hardware_usage)),
        "light_paths": json.loads(json.dumps(light_paths)),
        "light_sources": [],
        "detectors": [],
        "terminals": [],
        "stages": {"excitation": [], "dichroic": [], "emission": [], "cube": []},
        "splitters": [],
        "valid_paths": [],
        "available_routes": [{"id": route["id"], "label": route.get("name") or _resolve_route_label(route["id"])} for route in light_paths],
        "default_route": light_paths[0]["id"] if light_paths else None,
    }

    positions = {}
    for idx, src in enumerate(sources, start=1):
        positions[idx] = _source_position(idx, src)
        src_modalities = _normalize_modalities(src.get("modalities") or src.get("path") or src.get("routes"))
        if src_modalities:
            positions[idx]["routes"] = src_modalities
            positions[idx]["path"] = src_modalities[0]
    if positions:
        payload["light_sources"].append({
            "id": "light_sources_0",
            "name": "Sources",
            "display_label": "Sources",
            "type": "light_source_group",
            "control_kind": "checkboxes",
            "selection_mode": "multi",
            "positions": positions,
            "options": [{"slot": slot, "display_label": entry.get("display_label"), "value": entry} for slot, entry in sorted(positions.items())],
        })

    def terminal_from_endpoint(endpoint: dict[str, Any], index: int) -> dict[str, Any]:
        payload_row = _terminal_payload_from_endpoint(index, endpoint)
        modalities = _normalize_modalities(endpoint.get("modalities") or endpoint.get("path") or endpoint.get("routes"))
        if modalities:
            payload_row["routes"] = modalities
            payload_row["path"] = modalities[0]
        return payload_row

    explicit_endpoints = endpoints
    for idx, endpoint in enumerate(explicit_endpoints, start=1):
        terminal = terminal_from_endpoint(endpoint, idx)
        payload["terminals"].append(terminal)
        if _normalize_endpoint_type(endpoint.get("endpoint_type") or endpoint.get("type") or endpoint.get("kind")) != "detector":
            continue
        mechanism_id = _clean_identifier(endpoint.get("id")) or f"detector_{idx}"
        detector_group = {
            "id": mechanism_id,
            "name": terminal.get("channel_name") or terminal.get("display_label"),
            "display_label": terminal.get("display_label"),
            "type": "detector_group",
            "control_kind": "detector_toggle",
            "selection_mode": "multi",
            "positions": {1: dict(terminal)},
            "options": [{"slot": 1, "display_label": terminal.get("display_label"), "value": dict(terminal)}],
        }
        if terminal.get("routes"):
            detector_group["routes"] = terminal.get("routes")
            detector_group["path"] = terminal.get("path")
        payload["detectors"].append(detector_group)

    if include_inferred_terminals:
        payload["metadata"]["uses_inferred_terminals"] = True

    payload["metadata"]["graph_incomplete"] = len(payload["terminals"]) == 0

    derived_route_splitters = _collect_route_owned_splitters(light_paths, elements, endpoints)

    def splitter_payload_from_legacy_element(element: dict[str, Any], index: int) -> dict[str, Any]:
        routes = _normalize_modalities(element.get("modalities") or element.get("path") or element.get("routes"))
        candidate_terminals = _candidate_terminals_for_routes(payload["terminals"], routes)
        raw_splitter = {
            "name": element.get("name") or element.get("display_label") or f"Splitter {index + 1}",
            "path": routes[0] if routes else element.get("path"),
            "routes": routes,
            "selection_mode": element.get("selection_mode"),
            "dichroic": element.get("dichroic") if isinstance(element.get("dichroic"), dict) else {},
            "branches": [],
        }
        for branch in element.get("branches") or []:
            if not isinstance(branch, dict):
                continue
            raw_splitter["branches"].append({
                "id": branch.get("id"),
                "label": branch.get("label") or branch.get("name"),
                "mode": branch.get("mode"),
                "component": branch.get("component") if isinstance(branch.get("component"), dict) else {},
                "target_ids": _resolve_target_ids(branch.get("target_ids") or [], candidate_terminals or payload["terminals"]),
            })
        splitter_payload = _splitter_payload(index, raw_splitter, payload["terminals"])
        splitter_payload["id"] = element.get("id") or splitter_payload.get("id")
        if routes:
            splitter_payload["routes"] = routes
            splitter_payload["path"] = routes[0]
        if any(not branch.get("target_ids") for branch in splitter_payload.get("branches", [])):
            payload["metadata"]["graph_incomplete"] = True
        return splitter_payload

    def splitter_payload_from_route_splitter(splitter: dict[str, Any], index: int) -> dict[str, Any]:
        routes = _normalize_modalities(splitter.get("routes") or splitter.get("__routes") or splitter.get("path"))
        candidate_terminals = _candidate_terminals_for_routes(payload["terminals"], routes)
        raw_splitter = {
            "name": splitter.get("name") or splitter.get("display_label") or f"Splitter {index + 1}",
            "path": routes[0] if routes else splitter.get("path"),
            "routes": routes,
            "selection_mode": splitter.get("selection_mode"),
            "branches": [],
        }
        for branch in splitter.get("branches") or []:
            if not isinstance(branch, dict):
                continue
            raw_splitter["branches"].append({
                "id": branch.get("id"),
                "label": branch.get("label") or branch.get("name"),
                "mode": branch.get("mode"),
                "component": branch.get("component") if isinstance(branch.get("component"), dict) else {},
                "sequence": json.loads(json.dumps(branch.get("sequence") or [])),
                "target_ids": _resolve_target_ids(branch.get("target_ids") or [], candidate_terminals or payload["terminals"]),
                "__routes": list(branch.get("__routes") or []),
            })
        splitter_payload = _splitter_payload(index, raw_splitter, payload["terminals"])
        splitter_payload["id"] = splitter.get("id") or splitter_payload.get("id")
        splitter_payload["branch_selection_required"] = splitter.get("selection_mode") == "exclusive" and len(splitter_payload.get("branches", [])) > 1
        for branch_index, branch in enumerate(splitter_payload.get("branches", [])):
            source_branch = (splitter.get("branches") or [])[branch_index] if branch_index < len(splitter.get("branches") or []) else {}
            if isinstance(source_branch, dict):
                branch["sequence"] = json.loads(json.dumps(source_branch.get("sequence") or []))
                if source_branch.get("__routes"):
                    branch["__routes"] = list(source_branch.get("__routes") or [])
        if routes:
            splitter_payload["routes"] = routes
            splitter_payload["path"] = routes[0]
        if any(not branch.get("target_ids") for branch in splitter_payload.get("branches", [])):
            payload["metadata"]["graph_incomplete"] = True
        return splitter_payload

    stage_indices = {"excitation": 0, "dichroic": 0, "emission": 0, "cube": 0, "analyzer": 0}
    for element in elements:
        stage_role = element.get("stage_role")
        if stage_role == "splitter":
            continue
        if stage_role not in stage_mappings:
            continue
        index = stage_indices[stage_role]
        if stage_role == "cube":
            stage_mappings[stage_role].append(_cube_mechanism_payload(index, element))
        else:
            stage_mappings[stage_role].append(_mechanism_payload(prefix_mappings[stage_role], index, element))
        stage_indices[stage_role] += 1
    for splitter_index, splitter in enumerate(derived_route_splitters):
        payload["splitters"].append(splitter_payload_from_route_splitter(splitter, splitter_index))
    represented_splitter_ids = {splitter.get("id") for splitter in derived_route_splitters if splitter.get("id")}
    for element in elements:
        if element.get("stage_role") != "splitter":
            continue
        if element.get("id") in represented_splitter_ids:
            continue
        payload["splitters"].append(splitter_payload_from_legacy_element(element, len(payload["splitters"])))
    payload["stages"] = stage_mappings
    payload["valid_paths"] = calculate_valid_paths(payload)

    runtime_projection = {
        "light_sources": json.loads(json.dumps(payload["light_sources"])),
        "detectors": json.loads(json.dumps(payload["detectors"])),
        "terminals": json.loads(json.dumps(payload["terminals"])),
        "stages": json.loads(json.dumps(payload["stages"])),
        "splitters": json.loads(json.dumps(payload["splitters"])),
        "valid_paths": json.loads(json.dumps(payload["valid_paths"])),
        "available_routes": json.loads(json.dumps(payload["available_routes"])),
        "default_route": payload["default_route"],
        "route_hardware_usage": json.loads(json.dumps(payload["route_hardware_usage"])),
    }

    canonical_payload = {
        "dto_schema": payload["dto_schema"],
        "metadata": {
            **json.loads(json.dumps(payload["metadata"])),
            "derived_adapters": ["virtual_microscope"],
        },
        "simulation": {
            "wavelength_grid": json.loads(json.dumps(payload["metadata"]["wavelength_grid"])),
            "graph_incomplete": payload["metadata"].get("graph_incomplete", False),
            "uses_inferred_terminals": payload["metadata"].get("uses_inferred_terminals", False),
            "default_route": payload["default_route"],
            "route_catalog": json.loads(json.dumps(payload["available_routes"])),
        },
        "sources": json.loads(json.dumps(payload["sources"])),
        "optical_path_elements": json.loads(json.dumps(payload["optical_path_elements"])),
        "endpoints": json.loads(json.dumps(payload["endpoints"])),
        "normalized_endpoints": json.loads(json.dumps(payload["normalized_endpoints"])),
        "hardware_inventory": json.loads(json.dumps(payload["hardware_inventory"])),
        "hardware_index_map": json.loads(json.dumps(payload["hardware_index_map"])),
        "route_hardware_usage": json.loads(json.dumps(payload["route_hardware_usage"])),
        "light_paths": json.loads(json.dumps(payload["light_paths"])),
        "projections": {
            "virtual_microscope": runtime_projection,
        },
    }
    return json.loads(json.dumps(canonical_payload))
