"""Canonical light-path v2 parser.

This module owns the canonical YAML-first parser for light-path topology.

Canonical input contract:
- hardware.sources[]
- hardware.optical_path_elements[]
- endpoint-capable rows from hardware.endpoints[], hardware.terminals[],
  hardware.detection_endpoints[], hardware.detectors[], and hardware.eyepieces[]
- light_paths[].illumination_sequence[]
- light_paths[].detection_sequence[]

Legacy import is not performed at module import time. The non-strict
canonicalize_light_path_model() entry point lazily imports legacy_import only
when canonical v2 input is absent.
"""

from __future__ import annotations

from typing import Any

from scripts.lightpath.model import (
    CANONICAL_ENDPOINT_COLLECTION_KEYS,
    CUBE_LINK_KEYS,
    ENDPOINT_CAPABLE_INVENTORY_KEYS,
    SEQUENCE_TOPOLOGY_KEYS,
    _as_list,
    _clean_identifier,
    _clean_string,
    _copy_mapping,
    _modality_match,
    _normalize_endpoint_type,
    _normalize_modalities,
    _resolve_route_label,
)


def _collect_splitters(
    hardware: dict[str, Any],
    light_path: dict[str, Any],
) -> list[dict[str, Any]]:
    """Collect legacy splitter declarations from nested and top-level locations.

    This helper is shared with the legacy importer while legacy support remains.
    """
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


def _collect_endpoint_rows(
    hardware: dict[str, Any],
    light_path: dict[str, Any],
) -> list[dict[str, Any]]:
    """Collect explicit endpoint rows from canonical and legacy locations."""
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


def _endpoint_capable_row_id(
    entry: dict[str, Any],
    source_section: str,
    index: int,
) -> str:
    """Build a stable endpoint row id from authored identity fields."""
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
    """Normalize explicit endpoints and endpoint-capable inventory rows."""
    entry = dict(endpoint)
    entry_id = _endpoint_capable_row_id(entry, source_section, index)

    entry["id"] = entry_id
    entry["source_section"] = source_section
    entry["endpoint_origin"] = (
        "inventory"
        if source_section in ENDPOINT_CAPABLE_INVENTORY_KEYS
        else "explicit"
    )

    entry["endpoint_type"] = _normalize_endpoint_type(
        entry.get("endpoint_type")
        or (
            "detector"
            if source_section == "detectors"
            else "eyepiece"
            if source_section == "eyepieces"
            else ""
        )
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
    """Normalize canonical endpoint rows and endpoint-capable inventory rows.

    Returns:
        rows: normalized endpoint records.
        collisions: duplicate normalized endpoint id diagnostics.
    """
    rows: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    collisions: list[str] = []
    sources: list[tuple[str, list[dict[str, Any]]]] = []

    for key in CANONICAL_ENDPOINT_COLLECTION_KEYS:
        raw_rows = hardware.get(key)
        if isinstance(raw_rows, list):
            sources.append((key, [row for row in raw_rows if isinstance(row, dict)]))

    endpoints_already_normalized = any(
        isinstance(row, dict)
        and (
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
            (
                key,
                [
                    row
                    for row in legacy_light_path.get(key, [])
                    if isinstance(row, dict)
                ],
            )
            for key in CANONICAL_ENDPOINT_COLLECTION_KEYS
            if isinstance(legacy_light_path.get(key), list)
        )

    for source_section, collection in sources:
        for index, endpoint in enumerate(collection, start=1):
            entry = _normalize_endpoint_capable_row(
                endpoint,
                source_section=source_section,
                index=index,
            )
            entry_id = entry["id"]

            previous_source = seen.get(entry_id)
            if previous_source is not None:
                collisions.append(
                    f"normalized endpoint id `{entry_id}` is declared in both "
                    f"`{previous_source}` and `{source_section}`."
                )
                continue

            seen[entry_id] = source_section
            rows.append(entry)

    return rows, collisions


def _normalize_canonical_source_rows(raw_sources: Any) -> list[dict[str, Any]]:
    """Normalize canonical hardware.sources[] rows."""
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for index, source in enumerate(raw_sources or [], start=1):
        if not isinstance(source, dict):
            continue

        entry = dict(source)
        base_id = (
            _clean_identifier(
                entry.get("id")
                or entry.get("source_id")
                or entry.get("channel_name")
                or entry.get("name")
                or entry.get("model")
                or f"source_{index}"
            )
            or f"source_{index}"
        )

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
    """Parse canonical hardware.sources[]."""
    raw_sources = hardware.get("sources")
    if not isinstance(raw_sources, list):
        return []

    return _normalize_canonical_source_rows(raw_sources)


def _parse_canonical_endpoint_rows(hardware: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse canonical endpoint rows from explicit and endpoint-capable sections."""
    rows, _ = _normalized_endpoint_inventory(hardware)
    return rows


def _normalize_splitter_branch(
    branch: dict[str, Any],
    *,
    fallback_id: str,
) -> dict[str, Any]:
    """Normalize a branch payload on splitter-like elements.

    This helper preserves legacy/canonical branch spellings for migration and
    validation consumers.
    """
    entry = dict(branch)
    entry["id"] = (
        _clean_identifier(entry.get("id") or entry.get("label") or entry.get("name"))
        or fallback_id
    )

    target_ids = (
        entry.get("target_ids")
        or entry.get("targets")
        or entry.get("terminal_ids")
        or entry.get("endpoint_ids")
        or entry.get("endpoint_id")
        or entry.get("target")
        or entry.get("endpoint")
    )
    entry["target_ids"] = [
        item
        for item in (_clean_identifier(value) for value in _as_list(target_ids))
        if item
    ]

    component = (
        entry.get("component")
        if isinstance(entry.get("component"), dict)
        else entry.get("emission_filter")
    )
    if isinstance(component, dict):
        entry["component"] = dict(component)
    elif isinstance(entry.get("components"), list):
        entry["components"] = [
            dict(item)
            for item in entry.get("components")
            if isinstance(item, dict)
        ]

    return entry


def _stage_role_from_element(entry: dict[str, Any]) -> str | None:
    """Infer an optical path element stage role from authored fields."""
    stage_role = _clean_string(entry.get("stage_role") or entry.get("role")).lower()
    if stage_role:
        return stage_role

    if any(isinstance(entry.get(key), dict) for key in CUBE_LINK_KEYS):
        return "cube"

    positions = entry.get("positions") if isinstance(entry.get("positions"), dict) else {}
    for position in positions.values():
        if isinstance(position, dict) and any(
            isinstance(position.get(key), dict)
            for key in CUBE_LINK_KEYS
        ):
            return "cube"

    element_type = _clean_string(entry.get("element_type") or entry.get("type")).lower()
    if element_type in {
        "selector",
        "splitter",
        "emission_splitter",
        "image_splitter",
        "dual_view",
        "quad_view",
    }:
        return "splitter"

    return None


def _normalize_canonical_optical_path_elements(raw_elements: Any) -> list[dict[str, Any]]:
    """Normalize canonical hardware.optical_path_elements[] rows."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for index, element in enumerate(raw_elements or [], start=1):
        if not isinstance(element, dict):
            continue

        entry = dict(element)
        entry["id"] = (
            _clean_identifier(
                entry.get("id")
                or entry.get("name")
                or entry.get("display_label")
                or entry.get("model")
                or f"optical_path_element_{index}"
            )
            or f"optical_path_element_{index}"
        )

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


def _parse_canonical_optical_path_elements(
    hardware: dict[str, Any],
) -> list[dict[str, Any]]:
    """Parse canonical hardware.optical_path_elements[]."""
    raw_elements = hardware.get("optical_path_elements")
    if not isinstance(raw_elements, list):
        return []

    return _normalize_canonical_optical_path_elements(raw_elements)


def _canonicalize_sequence_item(
    item: Any,
    sources: list[dict[str, Any]],
    elements: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
    *,
    sequence_key: str,
    allow_branches: bool = True,
) -> dict[str, Any] | None:
    """Canonicalize one route sequence item.

    Sequence items must declare exactly one topology reference:
    - source_id
    - optical_path_element_id
    - endpoint_id
    - branches, where allowed
    """
    if not isinstance(item, dict):
        return None

    source_ids = {row.get("id") for row in sources}
    element_ids = {row.get("id") for row in elements}
    endpoint_ids = {row.get("id") for row in endpoints}

    allowed_ref_keys = (
        ("source_id", "optical_path_element_id")
        if sequence_key.startswith("illumination_sequence")
        else ("optical_path_element_id", "endpoint_id")
    )

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

            branch_payload: dict[str, Any] = {
                "branch_id": branch_id,
                "label": _clean_string(branch.get("label"))
                or _resolve_route_label(branch_id),
                "sequence": normalized_sequence,
            }

            if branch.get("mode"):
                branch_payload["mode"] = _clean_string(branch.get("mode")).lower()

            normalized_items.append(branch_payload)

        return {
            "branches": {
                "selection_mode": selection_mode,
                "items": normalized_items,
                **(
                    {"default_branch_id": _clean_identifier(raw_branches.get("default_branch_id"))}
                    if _clean_identifier(raw_branches.get("default_branch_id"))
                    else {}
                ),
            }
        }

    populated_ref_keys = [key for key in allowed_ref_keys if item.get(key)]
    if len(populated_ref_keys) != 1:
        return None

    selected_key = populated_ref_keys[0]

    if any(item.get(key) for key in SEQUENCE_TOPOLOGY_KEYS if key != selected_key):
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


def _parse_canonical_light_paths(
    raw_light_paths: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    elements: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Parse explicit canonical light_paths[]."""
    routes: list[dict[str, Any]] = []
    seen_route_ids: set[str] = set()

    for index, route in enumerate(raw_light_paths, start=1):
        if not isinstance(route, dict):
            continue

        route_id = _clean_identifier(
            route.get("id")
            or route.get("name")
            or f"route_{index}"
        )
        if not route_id:
            continue

        if route_id in seen_route_ids:
            route_id = f"{route_id}_{index}"
        seen_route_ids.add(route_id)

        parse_warnings: list[str] = []

        illumination_sequence: list[dict[str, Any]] = []
        for item_index, item in enumerate(_as_list(route.get("illumination_sequence"))):
            normalized = _canonicalize_sequence_item(
                item,
                sources,
                elements,
                endpoints,
                sequence_key="illumination_sequence",
                allow_branches=False,
            )
            if normalized is None:
                parse_warnings.append(
                    f"light_paths[{index - 1}].illumination_sequence[{item_index}]: "
                    "could not be canonicalized; validation should treat this as an error."
                )
                continue

            illumination_sequence.append(normalized)

        detection_sequence: list[dict[str, Any]] = []
        for item_index, item in enumerate(_as_list(route.get("detection_sequence"))):
            normalized = _canonicalize_sequence_item(
                item,
                sources,
                elements,
                endpoints,
                sequence_key="detection_sequence",
            )
            if normalized is None:
                parse_warnings.append(
                    f"light_paths[{index - 1}].detection_sequence[{item_index}]: "
                    "could not be canonicalized; validation should treat this as an error."
                )
                continue

            detection_sequence.append(normalized)

        route_type = _clean_identifier(route.get("route_type")) or route_id
        legacy_route_modalities = _normalize_modalities(
            route.get("modalities")
            or route.get("routes")
            or route.get("path")
        )

        route_payload: dict[str, Any] = {
            "id": route_id,
            "name": _clean_string(route.get("name")) or _resolve_route_label(route_id),
            "route_type": route_type,
            "readouts": [
                r.strip()
                for r in (route.get("readouts") or [])
                if isinstance(r, str) and r.strip()
            ],
            "illumination_sequence": illumination_sequence,
            "detection_sequence": detection_sequence,
        }
        if legacy_route_modalities:
            route_payload["_legacy_route_modalities"] = legacy_route_modalities

        if parse_warnings:
            route_payload["_parse_warnings"] = parse_warnings

        routes.append(route_payload)

    return routes


def _apply_route_modalities_from_sequences(
    *,
    sources: list[dict[str, Any]],
    elements: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
    light_paths: list[dict[str, Any]],
) -> None:
    """Back-fill row modalities from explicit light-path sequence membership."""
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

        modalities = _normalize_modalities(
            row.get("modalities")
            or row.get("path")
            or row.get("routes")
        )

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
        route_ids = [route.get("route_type") or route.get("id")]
        if route.get("_legacy_route_modalities"):
            route_ids = list(route.get("_legacy_route_modalities") or route_ids)

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
    """Build the canonical v2 light-path model."""
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
    """Return True when canonical v2 authoring is present enough to trust.

    Canonical hardware-only payloads, for example stage fixtures without authored
    light_paths yet, should still parse canonically instead of falling back to
    the legacy importer when no legacy topology exists.
    """
    hardware = (
        instrument_dict.get("hardware")
        if isinstance(instrument_dict.get("hardware"), dict)
        else {}
    )

    raw_light_paths = instrument_dict.get("light_paths")
    if not isinstance(raw_light_paths, list):
        # Some canonical fixtures nest light_paths inside hardware.
        raw_light_paths = hardware.get("light_paths")

    has_light_paths = isinstance(raw_light_paths, list) and bool(raw_light_paths)

    has_sources = isinstance(hardware.get("sources"), list) and bool(hardware.get("sources"))
    has_elements = (
        isinstance(hardware.get("optical_path_elements"), list)
        and bool(hardware.get("optical_path_elements"))
    )
    has_endpoints = any(
        isinstance(hardware.get(key), list) and bool(hardware.get(key))
        for key in CANONICAL_ENDPOINT_COLLECTION_KEYS
    )
    has_any_canonical_hardware = has_sources or has_elements or has_endpoints

    legacy_light_path = hardware.get("light_path")
    has_legacy_light_path = isinstance(legacy_light_path, dict) and bool(legacy_light_path)

    if has_light_paths and has_any_canonical_hardware:
        return True

    # Canonical stage-only fixtures should still parse canonically when there is
    # no legacy topology to import.
    if has_any_canonical_hardware and not has_legacy_light_path:
        return True

    return False


def parse_canonical_light_path_model(
    instrument_dict: dict[str, Any],
) -> dict[str, Any]:
    """Parse the explicit canonical v2 authoring contract only.

    This parser consumes:
    - hardware.sources[]
    - hardware.optical_path_elements[]
    - normalized hardware endpoints synthesized from hardware.endpoints[] and
      endpoint-capable inventories
    - light_paths[].illumination_sequence[]
    - light_paths[].detection_sequence[]

    It intentionally does not inspect or synthesize from legacy light-path
    structures.
    """
    hardware = (
        instrument_dict.get("hardware")
        if isinstance(instrument_dict.get("hardware"), dict)
        else {}
    )

    sources = _parse_canonical_source_rows(hardware)
    elements = _parse_canonical_optical_path_elements(hardware)
    endpoints = _parse_canonical_endpoint_rows(hardware)

    raw_light_paths = (
        instrument_dict.get("light_paths")
        if isinstance(instrument_dict.get("light_paths"), list)
        else []
    )
    if not raw_light_paths:
        # Fallback: some canonical fixtures nest light_paths inside hardware.
        raw_light_paths = (
            hardware.get("light_paths")
            if isinstance(hardware.get("light_paths"), list)
            else []
        )

    light_paths = _parse_canonical_light_paths(
        raw_light_paths,
        sources,
        elements,
        endpoints,
    )

    return _canonical_light_path_model(
        sources=sources,
        optical_path_elements=elements,
        endpoints=endpoints,
        light_paths=light_paths,
    )


def canonicalize_light_path_model(
    instrument_dict: dict[str, Any],
) -> dict[str, Any]:
    """Return canonical v2 light-path data for downstream consumers.

    Canonical v2 input is structurally primary. Legacy support is retained only
    via the explicit import adapter and is imported lazily to avoid circular
    imports.
    """
    payload = instrument_dict if isinstance(instrument_dict, dict) else {}

    if _has_canonical_light_path_input(payload):
        return parse_canonical_light_path_model(payload)

    from scripts.lightpath.legacy_import import import_legacy_light_path_model

    return import_legacy_light_path_model(payload)


def canonicalize_light_path_model_strict(
    instrument_dict: dict[str, Any],
) -> dict[str, Any]:
    """Production strict canonicalizer.

    Only explicit canonical v2 topology is accepted. Legacy topology is for
    migration/audit compatibility tooling only.
    """
    payload = instrument_dict if isinstance(instrument_dict, dict) else {}

    if not _has_canonical_light_path_input(payload):
        raise ValueError("Legacy-only topology is not allowed in strict production mode.")

    return parse_canonical_light_path_model(payload)


def parse_strict_canonical_light_path_model(
    instrument_dict: dict[str, Any],
) -> dict[str, Any]:
    """Strict production parser entry point.

    This is the authoritative parser for production DTO/export flows. It rejects
    legacy-only topology and does not invoke legacy import adapters.
    """
    return canonicalize_light_path_model_strict(instrument_dict)


__all__ = [
    # Shared canonical constants imported from model for compatibility.
    "CANONICAL_ENDPOINT_COLLECTION_KEYS",
    "ENDPOINT_CAPABLE_INVENTORY_KEYS",

    # Endpoint/canonical normalization helpers used by legacy adapter and tests.
    "_collect_splitters",
    "_collect_endpoint_rows",
    "_endpoint_capable_row_id",
    "_normalize_endpoint_capable_row",
    "_normalized_endpoint_inventory",
    "_normalize_canonical_source_rows",
    "_parse_canonical_source_rows",
    "_parse_canonical_endpoint_rows",
    "_normalize_splitter_branch",
    "_stage_role_from_element",
    "_normalize_canonical_optical_path_elements",
    "_parse_canonical_optical_path_elements",
    "_canonicalize_sequence_item",
    "_parse_canonical_light_paths",
    "_apply_route_modalities_from_sequences",
    "_canonical_light_path_model",
    "_has_canonical_light_path_input",

    # Public parser entry points.
    "parse_canonical_light_path_model",
    "canonicalize_light_path_model",
    "canonicalize_light_path_model_strict",
    "parse_strict_canonical_light_path_model",
]
