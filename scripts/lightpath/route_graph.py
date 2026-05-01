"""Route graph and hardware-inventory builders for light-path DTOs.

This module owns route-local graph construction and the route execution contract:
- hardware_inventory / hardware_index_map
- route_hardware_usage
- graph_nodes / graph_edges
- route_steps
- selected_execution

It must not import scripts.light_path_parser.
It should not perform canonical parsing, legacy import, validation diagnostics,
or VM payload rendering.
"""

from __future__ import annotations

import json
from copy import deepcopy
from itertools import product
from typing import Any

from scripts.lightpath.model import (
    CUBE_LINK_KEYS,
    _clean_identifier,
    _clean_string,
    _coerce_slot_key,
    _format_numeric,
    _normalize_endpoint_type,
    _normalize_modalities,
    _normalize_routes,
    _resolve_cube_link_label,
    _resolve_route_label,
)
from scripts.lightpath.spectral_ops import (
    _build_details,
    _component_payload,
    _cube_spectral_ops,
)

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
    constrained = {tag for tag in route_tags if isinstance(tag, str) and tag.strip()}
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


def _resolve_position_candidate_payload(
    position: dict[str, Any],
    *,
    parent_element: dict[str, Any],
    fallback_key: str | None = None,
    fallback_slot: int | None = None,
) -> tuple[dict[str, Any], str | None, str | None, str | None]:
    """Resolve one authored position object into a parser-authoritative payload."""
    if not isinstance(position, dict):
        return {}, None, None, None

    default_name = (
        _clean_string(parent_element.get("name"))
        or _clean_string(parent_element.get("display_label"))
        or _clean_string(parent_element.get("id"))
        or ""
    )

    if isinstance(position.get("component"), dict):
        component_payload = _component_payload(
            position["component"],
            default_name=default_name,
        )
    elif any(isinstance(position.get(link_key), dict) for link_key in CUBE_LINK_KEYS):
        linked_components: dict[str, dict[str, Any]] = {}
        for link_key in CUBE_LINK_KEYS:
            raw_link = position.get(link_key)
            if isinstance(raw_link, dict):
                linked_components[link_key] = _component_payload(
                    raw_link,
                    default_name=_resolve_cube_link_label(link_key),
                )

        component_payload = dict(position)
        component_payload.setdefault("component_type", "filter_cube")
        component_payload.setdefault("type", component_payload.get("component_type"))
        component_payload.setdefault("name", _clean_string(position.get("name")) or default_name)
        component_payload.setdefault(
            "label",
            _clean_string(position.get("label") or position.get("name") or default_name),
        )
        component_payload.setdefault(
            "display_label",
            _clean_string(position.get("display_label") or position.get("label") or position.get("name") or default_name),
        )
        component_payload.setdefault("details", _build_details(position))
        component_payload["linked_components"] = linked_components
        for link_key, linked_component in linked_components.items():
            component_payload[link_key] = linked_component

        routes = _normalize_routes(
            position.get("path")
            or position.get("paths")
            or position.get("route")
            or position.get("routes")
            or parent_element.get("path")
            or parent_element.get("routes")
        )
        if routes:
            component_payload["routes"] = routes
            component_payload["path"] = routes[0]

        if linked_components and any(k not in linked_components for k in CUBE_LINK_KEYS):
            component_payload.setdefault("_cube_incomplete", True)
            component_payload.setdefault("_unsupported_spectral_model", True)

        component_payload["spectral_ops"] = _cube_spectral_ops(component_payload)
    else:
        component_payload = _component_payload(position, default_name=default_name)

    position_key = _clean_string(position.get("position_key")) or (_clean_string(fallback_key) or None)

    authored_position_id = (
        _clean_string(position.get("id"))
        or position_key
        or (str(fallback_slot) if fallback_slot is not None else None)
    )

    position_label = (
        _clean_string(position.get("display_label"))
        or _clean_string(position.get("label"))
        or _clean_string(position.get("name"))
        or _clean_string(component_payload.get("display_label"))
        or _clean_string(component_payload.get("label"))
        or position_key
        or (str(fallback_slot) if fallback_slot is not None else None)
    )

    return (
        component_payload,
        authored_position_id or None,
        position_key or None,
        position_label or None,
    )


def _position_id_matches_element(element: dict[str, Any], position_id: Any) -> bool:
    """Return True if *position_id* matches an authored position on *element*."""
    requested = _clean_string(position_id)
    if not requested:
        return False

    requested_identifier = _clean_identifier(requested)
    requested_slot = _coerce_slot_key(requested)

    for key_text, slot, position in _iter_element_positions(element):
        if not isinstance(position, dict):
            continue

        authored_id = _clean_string(position.get("id"))
        position_key = _clean_string(position.get("position_key"))

        identifiers = {
            _clean_identifier(key_text),
            _clean_identifier(authored_id),
            _clean_identifier(position_key),
        }

        if (
            requested == key_text
            or requested == authored_id
            or requested == position_key
            or (requested_identifier and requested_identifier in identifiers)
            or (requested_slot is not None and slot == requested_slot)
        ):
            return True

    return False


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
            if not isinstance(position, dict):
                continue

            authored_id = _clean_string(position.get("id"))
            position_key = _clean_string(position.get("position_key"))
            identifiers = {
                _clean_identifier(key_text),
                _clean_identifier(authored_id),
                _clean_identifier(position_key),
            }

            key_matches = (
                requested == key_text
                or requested == authored_id
                or requested == position_key
                or (requested_identifier and requested_identifier in identifiers)
            )
            slot_matches = requested_slot is not None and slot == requested_slot

            if key_matches or slot_matches:
                selected_key = key_text
                selected_slot = slot
                selected_position = position
                break

        # Critical fix:
        # an explicitly authored but invalid position_id must NOT silently fall
        # back to the first position.
        if selected_position is None:
            return {}, None, None, None

    if selected_position is None and position_candidates:
        selected_key, selected_slot, selected_position = position_candidates[0]

    if isinstance(selected_position, dict):
        return _resolve_position_candidate_payload(
            selected_position,
            parent_element=element,
            fallback_key=selected_key,
            fallback_slot=selected_slot,
        )

    component_payload = _component_payload_from_element_reference(
        _clean_identifier(element.get("id")),
        {element.get("id"): element},
    )
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
            default_branch_id = _clean_identifier(branch_block.get("default_branch_id"))
            if default_branch_id:
                splitter["default_branch_id"] = default_branch_id
            branch_index: dict[str, int] = splitter["__branch_index"]
            for branch_position, branch in enumerate(branch_block.get("items") or [], start=1):
                if not isinstance(branch, dict):
                    continue
                branch_id = _clean_identifier(branch.get("branch_id")) or f"branch_{branch_position}"
                dedupe_key = json.dumps(
                    {
                        "branch_id": branch_id,
                        "mode": _clean_string(branch.get("mode")).lower(),
                        "sequence": branch.get("sequence") or [],
                    },
                    sort_keys=True,
                )
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
                    component: dict[str, Any] = {}
                    for step in branch.get("sequence") or []:
                        if not isinstance(step, dict):
                            continue
                        step_element_id = _clean_identifier(step.get("optical_path_element_id"))
                        if not step_element_id or step_element_id not in element_lookup:
                            continue
                        resolved_component, _, _, _ = _resolve_positioned_component_from_element(
                            element_lookup[step_element_id],
                            position_id=_clean_string(step.get("position_id")),
                        )
                        if isinstance(resolved_component, dict) and resolved_component:
                            component = resolved_component
                            break
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
            endpoint_type = _normalize_endpoint_type(
                entry.get("endpoint_type")
                or entry.get("type")
                or entry.get("kind")
            )
            return "detector" if endpoint_type == "detector" else "endpoint"
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
        # If the walk_sequence phase resolved a valid position the entry carries
        # it in "position_id".  When the authored position_id was *invalid*, the
        # walk_sequence critical-fix returns None so "position_id" is absent but
        # "_authored_position_id" is still set.  We must pass the authored value
        # through so that _resolve_positioned_component_from_element can trigger
        # its own invalid-position guard and return ({}, None, None, None) instead
        # of silently falling back to the first available position.
        effective_position_id = _clean_string(entry.get("position_id")) or _clean_string(
            entry.get("_authored_position_id")
        )
        component_payload, position_id, position_key, position_label = _resolve_positioned_component_from_element(
            element_row,
            position_id=effective_position_id,
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
                    endpoint_type = _normalize_endpoint_type(
                        seq_step.get("endpoint_type")
                        or seq_step.get("type")
                        or seq_step.get("kind")
                    )
                    step_kind = "detector" if endpoint_type == "detector" else "endpoint"
                    normalized.append(
                        {
                            "kind": step_kind,
                            "detector_id": seq_id or None if step_kind == "detector" else None,
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
                        "_authored_position_id": seq_step.get("_authored_position_id"),
                    }
                )
            return normalized

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            order += 1
            row = _lookup_row(entry)
            component_payload, position_id, position_key, position_label = _resolved_step_payload(entry)
            kind = _step_kind(entry)
            component_id = entry.get("id") or "sample"
            display_label = entry.get("display_label") or component_payload.get("display_label") or component_payload.get("label") or row.get("display_label") or component_id
            inventory_id = entry.get("hardware_inventory_id") or ""
            inventory_item = inventory_lookup.get(inventory_id, {}) if inventory_id else {}
            metadata = _component_metadata(row if isinstance(row, dict) else {})

            step_payload: dict[str, Any] = {
                "step_id": f"{phase}_{order}_{component_id}",
                "order": order,
                "phase": phase,
                "kind": kind,
                "component_id": component_id,
                "display_label": display_label,
                "hardware_inventory_id": inventory_id or None,
                "hardware_inventory_number": inventory_item.get("display_number") or entry.get("display_number"),
                "metadata": {key: val for key, val in metadata.items() if val is not None},
                "source_ref": deepcopy(inventory_item.get("source_ref")) if inventory_item else None,
                "stage_role": entry.get("stage_role"),
                "endpoint_type": entry.get("endpoint_type"),
                "component_type": _clean_string(component_payload.get("component_type") or component_payload.get("type")).lower() or None,
                "position_id": position_id,
                "position_key": position_key,
                "position_label": position_label,
                "spectral_ops": component_payload.get("spectral_ops"),
                "unsupported_reason": "unsupported_spectral_model" if component_payload.get("_unsupported_spectral_model") else None,
                "route_graph_node_id": entry.get("node_id"),
                "sequence_ref": deepcopy(entry.get("sequence_ref") or {}),
                "_authored_position_id": entry.get("_authored_position_id"),
            }
            if entry.get("kind") == "source":
                step_payload["source_id"] = component_id
            if entry.get("kind") == "endpoint":
                step_payload["detector_id"] = component_id
                step_payload["endpoint_id"] = component_id
            if entry.get("kind") == "branch_block":
                step_payload["routing"] = {
                    "selection_mode": entry.get("selection_mode"),
                    "default_branch_id": entry.get("default_branch_id"),
                    "branches": [
                        {
                            "branch_id": branch.get("branch_id"),
                            "label": branch.get("label"),
                            "mode": branch.get("mode"),
                            "tail_node_id": branch.get("tail_node_id"),
                            "tail_node_ids": branch.get("tail_node_ids") or [],
                            "hardware_inventory_ids": branch.get("hardware_inventory_ids") or [],
                            "endpoint_inventory_ids": branch.get("endpoint_inventory_ids") or [],
                            "sequence": _routing_branch_sequence(branch.get("sequence") or []),
                        }
                        for branch in entry.get("branches", [])
                        if isinstance(branch, dict)
                    ],
                }
                step_payload["component_type"] = "branch_selector"
                step_payload["selection_mode"] = entry.get("selection_mode")
            if kind == "optical_component" and not component_payload and entry.get("_authored_position_id"):
                warnings.append(
                    f"{phase} step `{component_id}` references position_id `{entry.get('_authored_position_id')}` that could not be resolved."
                )
            steps.append(step_payload)

    _process_entries(illumination_traversal, "illumination")
    order += 1
    steps.append(
        {
            "step_id": "sample_plane",
            "order": order,
            "phase": "sample",
            "kind": "sample",
            "component_id": "sample_plane",
            "display_label": "Objective / Sample Plane",
            "hardware_inventory_id": None,
            "metadata": {},
            "spectral_ops": {"illumination": [{"op": "passthrough"}], "detection": [{"op": "passthrough"}]},
        }
    )
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

    def _dedupe_ids(values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

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
        prev_node_ids: list[str],
        column: int,
        lane: int,
    ) -> tuple[list[dict[str, Any]], list[str], int]:
        nonlocal branch_counter
        resolved_steps: list[dict[str, Any]] = []
        current_prev_ids = _dedupe_ids(list(prev_node_ids))
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
                merged_tail_ids: list[str] = []

                for branch_index, branch in enumerate(branch_block.get("items") or [], start=1):
                    if not isinstance(branch, dict):
                        continue

                    branch_id = _clean_identifier(branch.get("branch_id")) or f"branch_{branch_index}"
                    branch_label = _clean_string(branch.get("label")) or _resolve_route_label(branch_id)

                    branch_sequence, branch_tail_ids, branch_column = walk_sequence(
                        branch.get("sequence") or [],
                        phase=phase,
                        prev_node_ids=list(current_prev_ids),
                        column=current_column + 1,
                        lane=lane + branch_index - 1,
                    )
                    branch_columns.append(branch_column)

                    effective_tail_ids = _dedupe_ids(branch_tail_ids or list(current_prev_ids))
                    merged_tail_ids.extend(effective_tail_ids)

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
                            "tail_node_id": effective_tail_ids[0] if len(effective_tail_ids) == 1 else None,
                            "tail_node_ids": effective_tail_ids,
                            "hardware_inventory_ids": branch_inventory_ids,
                            "endpoint_inventory_ids": branch_endpoint_ids,
                        }
                    )

                usage["branch_blocks"].append(
                    {
                        "id": branch_block_id,
                        "selection_mode": _clean_string(branch_block.get("selection_mode")).lower() or "exclusive",
                        "default_branch_id": _clean_identifier(branch_block.get("default_branch_id")) or None,
                        "branches": resolved_branches,
                    }
                )
                block_node_id = f"{route['id']}_{phase}_branch_block_{branch_counter}"
                graph_nodes.append(
                    {
                        "id": block_node_id,
                        "route_id": route["id"],
                        "phase": phase,
                        "component_kind": "branch_block",
                        "hardware_inventory_id": None,
                        "hardware_id": branch_block_id,
                        "label": "Branch selector",
                        "display_number": None,
                        "inventory_display_number": None,
                        "inventory_identity": {},
                        "graph_occurrence": {
                            "node_id": block_node_id,
                            "route_id": route["id"],
                            "phase": phase,
                            "column": current_column,
                            "lane": lane,
                        },
                        "stage_role": "splitter",
                        "endpoint_type": None,
                        "column": current_column,
                        "lane": lane,
                    }
                )
                for prev_id in current_prev_ids:
                    add_graph_edge(prev_id, block_node_id)
                for branch in resolved_branches:
                    for tail_id in branch.get("tail_node_ids") or []:
                        add_graph_edge(block_node_id, tail_id, branch_id=branch.get("branch_id") or "", label=branch.get("label") or "")

                resolved_steps.append(
                    {
                        "kind": "branch_block",
                        "id": branch_block_id,
                        "display_label": "Branch selector",
                        "node_id": block_node_id,
                        "selection_mode": _clean_string(branch_block.get("selection_mode")).lower() or "exclusive",
                        "default_branch_id": _clean_identifier(branch_block.get("default_branch_id")) or None,
                        "branches": resolved_branches,
                    }
                )
                current_prev_ids = _dedupe_ids(merged_tail_ids or [block_node_id])
                current_column = max(branch_columns) + 1
                continue

            resolved = resolve_step(step)
            if not resolved.get("id"):
                continue
            ref_key = "source_id" if step.get("source_id") else "endpoint_id" if step.get("endpoint_id") else "optical_path_element_id"
            if ref_key == "optical_path_element_id":
                element_row = element_lookup.get(resolved.get("id"), {})
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
                resolved["_authored_position_id"] = _clean_string(step.get("position_id")) or None

            node_id = add_graph_node(resolved, phase=phase, column=current_column, lane=lane)
            for prev_id in current_prev_ids:
                add_graph_edge(prev_id, node_id)

            sequence_ref = {ref_key: resolved.get("id")}
            if ref_key == "optical_path_element_id" and _clean_string(step.get("position_id")):
                sequence_ref["position_id"] = _clean_string(step.get("position_id"))

            resolved_steps.append({**resolved, "node_id": node_id, "sequence_ref": sequence_ref})
            current_prev_ids = [node_id]
            current_column += 1

        return resolved_steps, current_prev_ids, current_column

    illumination_sequence, illumination_tail_ids, next_column = walk_sequence(
        route.get("illumination_sequence") or [],
        phase="illumination",
        prev_node_ids=[],
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
    for tail_id in illumination_tail_ids:
        add_graph_edge(tail_id, sample_node_id)

    detection_sequence, _, _ = walk_sequence(
        route.get("detection_sequence") or [],
        phase="detection",
        prev_node_ids=[sample_node_id],
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
    _route_id = route.get("id") or ""
    from scripts.lightpath.selected_execution import _build_selected_route_steps

    selected_route_steps = _build_selected_route_steps(route_steps, _route_id, element_lookup)
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
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
        "route_steps": route_steps,
        "selected_execution": {
            "contract_version": "selected_execution.v2",
            "route_id": route.get("id"),
            "route_label": route.get("name"),
            "selected_route_steps": selected_route_steps,
        },
        "route_warnings": route_warnings,
        "branch_blocks": list(usage["branch_blocks"]),
        "endpoints": list(usage["endpoint_inventory_ids"]),
        "hardware_inventory_ids": list(usage["hardware_inventory_ids"]),
        }
    resolved_route["graph_tree"] = {
        "illumination": illumination_sequence,
        "sample": {"node_id": sample_node_id, "label": "Objective / Sample Plane"},
        "detection": detection_sequence,
    }
    return resolved_route, usage


__all__ = [
    "_route_tags",
    "_routes_compatible",
    "_choice_positions",
    "_endpoint_ids_in_sequence",
    "_component_payload_from_element_reference",
    "_iter_element_positions",
    "_resolve_position_candidate_payload",
    "_position_id_matches_element",
    "_resolve_positioned_component_from_element",
    "_collect_route_owned_splitters",
    "calculate_valid_paths",
    "_component_inventory_key",
    "_component_inventory_class",
    "_component_display_label",
    "_inventory_metadata",
    "_build_hardware_inventory",
    "_resolve_graph_component",
    "_build_route_steps",
    "_build_route_sequences_and_graph",
]
