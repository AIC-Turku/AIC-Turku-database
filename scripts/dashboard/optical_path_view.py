"""Derived optical-path view DTO builders.

Implementation moved from scripts/dashboard_builder.py.
The canonical light-path DTO (from scripts.build_context) is the authoritative
source; these functions build display-oriented derived view DTOs from it.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.validate import Vocabulary
from scripts.display_labels import (
    resolve_stage_role_label,
    resolve_element_type_label,
    resolve_endpoint_type_label,
    resolve_inventory_class_label,
    resolve_component_type_label,
)
from scripts.dashboard.common import (
    clean_text,
    _spec_lines,
    _compact_join,
    _human_list,
)


# ---------------------------------------------------------------------------
# Position / element helpers
# ---------------------------------------------------------------------------

def _first_component_label(position: Any) -> str:
    if not isinstance(position, dict):
        return ""
    linked = position.get("linked_components") if isinstance(position.get("linked_components"), dict) else {}
    if linked:
        labels = []
        for key in ("excitation_filter", "dichroic", "emission_filter"):
            label = clean_text(((linked.get(key) or {}).get("label")))
            if label:
                labels.append(label)
        if labels:
            return " / ".join(labels)
    return clean_text(position.get("display_label") or position.get("label") or position.get("name"))


def _mechanism_preview(mechanisms: Any) -> "tuple[int, list[str]]":
    if not isinstance(mechanisms, list):
        return 0, []
    previews: "list[str]" = []
    total_positions = 0
    for mechanism in mechanisms:
        if not isinstance(mechanism, dict):
            continue
        positions = mechanism.get("positions")
        if isinstance(positions, dict):
            total_positions += len(positions)
            iterable = [positions[key] for key in sorted(positions)]
        elif isinstance(positions, list):
            total_positions += len(positions)
            iterable = positions
        else:
            iterable = []
        for position in iterable:
            label = _first_component_label(position)
            if label and label not in previews:
                previews.append(label)
            if len(previews) >= 4:
                break
        if len(previews) >= 4:
            break
    return total_positions, previews[:4]


def _format_position_value(pos: "dict[str, Any]", vocabulary: Any = None) -> str:
    """Format a single optical path element position (filter/cube/dichroic) into a compact display string."""
    name = clean_text(pos.get("name") or pos.get("display_label") or pos.get("label"))
    if not name:
        raw_component_type = clean_text(pos.get("component_type"))
        if raw_component_type and vocabulary:
            name = resolve_component_type_label(raw_component_type, vocabulary)
        elif raw_component_type:
            name = raw_component_type.replace("_", " ").title()
    product_code = clean_text(pos.get("product_code"))
    if not name and product_code:
        name = product_code
        product_code = ""
    if not name:
        return ""
    bands = pos.get("bands")
    notes = clean_text(pos.get("notes"))
    parts: "list[str]" = [name]
    if product_code:
        parts.append(f"({product_code})")
    if isinstance(bands, list) and bands:
        band_strs = []
        for band in bands:
            if isinstance(band, dict):
                center = band.get("center_nm")
                width = band.get("width_nm")
                if center is not None and width is not None:
                    band_strs.append(f"{center}/{width} nm")
                elif center is not None:
                    band_strs.append(f"{center} nm")
        if band_strs:
            parts.append(f"\u2014 emission {', '.join(band_strs)}")
    if notes:
        parts.append(f"\u2014 {notes}")
    return " ".join(parts)


def _optical_element_position_pairs(element: "dict[str, Any]", vocabulary: Any = None) -> "list[tuple[str, str]]":
    """Return (label, value) pairs for each named position of an optical path element."""
    positions = element.get("positions")
    pairs: "list[tuple[str, str]]" = []
    if isinstance(positions, dict):
        for key in sorted(positions):
            pos = positions[key]
            if not isinstance(pos, dict):
                continue
            value = _format_position_value(pos, vocabulary)
            if value:
                label = key.replace("_", " ").title()
                pairs.append((label, value))
    elif isinstance(positions, list):
        for i, pos in enumerate(positions):
            if not isinstance(pos, dict):
                continue
            value = _format_position_value(pos, vocabulary)
            if value:
                pairs.append((f"Pos {i + 1}", value))
    return pairs


def _terminal_summary(terminal: "dict[str, Any]", vocabulary: "Vocabulary | None" = None) -> str:
    raw_endpoint_type = clean_text(terminal.get("endpoint_type") or terminal.get("type") or terminal.get("kind"))
    endpoint_type = resolve_endpoint_type_label(raw_endpoint_type, vocabulary) if vocabulary else raw_endpoint_type.replace("_", " ").title()
    route_text = ", ".join(terminal.get("routes") or []) if isinstance(terminal.get("routes"), list) else clean_text(terminal.get("path"))
    return _compact_join([endpoint_type, route_text])


def hardware_renderables_from_inventory(
    inventory_renderables: "list[dict[str, Any]]",
    hardware_ids: "set[str]",
    *inventory_classes: str,
) -> "list[dict[str, Any]]":
    allowed = set(inventory_classes)
    rows: "list[dict[str, Any]]" = []
    for item in inventory_renderables:
        if clean_text(item.get("id")) not in hardware_ids:
            continue
        if allowed and clean_text(item.get("inventory_class")) not in allowed:
            continue
        rows.append(copy.deepcopy(item))
    return rows


# ---------------------------------------------------------------------------
# Route analysis helpers
# ---------------------------------------------------------------------------

def _inventory_display_number(
    inventory_id: str,
    inventory_lookup: "dict[str, dict[str, Any]]",
    hardware_index_map: "dict[str, Any]",
) -> "int | None":
    item = inventory_lookup.get(inventory_id) or {}
    display_number = item.get("display_number")
    if isinstance(display_number, int):
        return display_number
    by_inventory_id = hardware_index_map.get("by_inventory_id") if isinstance(hardware_index_map.get("by_inventory_id"), dict) else {}
    value = by_inventory_id.get(inventory_id)
    return value if isinstance(value, int) else None


def _normalized_hardware_index_map(hardware_inventory: "list[dict[str, Any]]", raw_index_map: "dict[str, Any]") -> "dict[str, Any]":
    by_inventory_id = copy.deepcopy(raw_index_map.get("by_inventory_id") or {}) if isinstance(raw_index_map, dict) else {}
    by_ref = copy.deepcopy(raw_index_map.get("by_ref") or {}) if isinstance(raw_index_map, dict) else {}
    by_hardware_id = copy.deepcopy(raw_index_map.get("by_hardware_id") or {}) if isinstance(raw_index_map, dict) else {}

    for item in hardware_inventory:
        if not isinstance(item, dict):
            continue
        inventory_id = clean_text(item.get("id"))
        hardware_id = clean_text(item.get("hardware_id"))
        display_number = item.get("display_number")
        if inventory_id and isinstance(display_number, int):
            by_inventory_id.setdefault(inventory_id, display_number)
        if inventory_id:
            by_ref.setdefault(inventory_id, inventory_id)
        if hardware_id and isinstance(display_number, int):
            by_hardware_id.setdefault(hardware_id, display_number)

    return {
        "by_inventory_id": by_inventory_id,
        "by_ref": by_ref,
        "by_hardware_id": by_hardware_id,
    }


def _normalized_hardware_inventory(
    hardware_inventory: "list[dict[str, Any]]",
    hardware_index_map: "dict[str, Any]",
) -> "list[dict[str, Any]]":
    normalized: "list[dict[str, Any]]" = []
    for item in hardware_inventory:
        if not isinstance(item, dict):
            continue
        inventory_id = clean_text(item.get("id"))
        hardware_id = clean_text(item.get("hardware_id"))
        normalized.append({
            **copy.deepcopy(item),
            "display_number": item.get("display_number") or _inventory_display_number(inventory_id, {inventory_id: item}, hardware_index_map),
            "inventory_identity": copy.deepcopy(item.get("inventory_identity") or {
                "inventory_id": inventory_id,
                "hardware_id": hardware_id,
                "component_type": clean_text(item.get("component_type")),
            }),
        })
    return normalized


def _route_endpoint_summary(
    usage: "dict[str, Any]",
    inventory_lookup: "dict[str, dict[str, Any]]",
) -> "dict[str, Any]":
    endpoint_ids = [clean_text(item) for item in (usage.get("endpoint_inventory_ids") or []) if clean_text(item)]
    endpoint_items = [copy.deepcopy(inventory_lookup[item_id]) for item_id in endpoint_ids if item_id in inventory_lookup]
    return {
        "count": len(endpoint_items),
        "inventory_ids": endpoint_ids,
        "labels": [clean_text(item.get("display_label") or item.get("id")) for item in endpoint_items if clean_text(item.get("display_label") or item.get("id"))],
        "items": endpoint_items,
    }


def _route_branch_summary(route: "dict[str, Any]", usage: "dict[str, Any]") -> "dict[str, Any]":
    branch_blocks = [copy.deepcopy(item) for item in (usage.get("branch_blocks") or route.get("branch_blocks") or []) if isinstance(item, dict)]
    branches: "list[dict[str, Any]]" = []
    selection_modes: "list[str]" = []
    for block in branch_blocks:
        selection_mode = clean_text(block.get("selection_mode"))
        if selection_mode and selection_mode not in selection_modes:
            selection_modes.append(selection_mode)
        for branch in block.get("branches") or []:
            if not isinstance(branch, dict):
                continue
            branches.append({
                "block_id": clean_text(block.get("id")),
                "selection_mode": selection_mode,
                "branch_id": clean_text(branch.get("branch_id") or branch.get("id")),
                "label": clean_text(branch.get("label") or branch.get("branch_id") or branch.get("id")),
                "mode": clean_text(branch.get("mode")),
                "hardware_inventory_ids": [clean_text(item) for item in (branch.get("hardware_inventory_ids") or []) if clean_text(item)],
                "endpoint_inventory_ids": [clean_text(item) for item in (branch.get("endpoint_inventory_ids") or []) if clean_text(item)],
            })
    return {
        "has_branches": bool(branch_blocks),
        "count": len(branches),
        "selection_modes": selection_modes,
        "branch_blocks": branch_blocks,
        "branches": branches,
    }


def _build_route_optical_facts(selected_execution: "dict[str, Any]") -> "dict[str, Any]":
    fact_keys = [
        "selected_or_selectable_sources",
        "selected_or_selectable_excitation_filters",
        "selected_or_selectable_dichroics",
        "selected_or_selectable_emission_filters",
        "selected_or_selectable_splitters",
        "selected_or_selectable_endpoints",
        "selected_or_selectable_modulators",
        "selected_or_selectable_branch_selectors",
    ]
    selected_route_steps = (
        selected_execution.get("selected_route_steps")
        if isinstance(selected_execution.get("selected_route_steps"), list)
        else []
    )

    facts: "dict[str, list[Any]]" = {key: [] for key in fact_keys}
    seen_serializations: "dict[str, set[str]]" = {key: set() for key in fact_keys}

    for step in selected_route_steps:
        if not isinstance(step, dict):
            continue
        for fact_key in fact_keys:
            raw_value = step.get(fact_key)
            if raw_value is None:
                continue
            candidate_rows = raw_value if isinstance(raw_value, list) else [raw_value]
            for candidate in candidate_rows:
                if candidate is None:
                    continue
                serialized = json.dumps(candidate, sort_keys=True, default=str)
                if serialized in seen_serializations[fact_key]:
                    continue
                seen_serializations[fact_key].add(serialized)
                facts[fact_key].append(copy.deepcopy(candidate))

    return {
        "contract_version": "route_optical_facts.v1",
        "selected_route_step_count": len(selected_route_steps),
        **facts,
    }


# ---------------------------------------------------------------------------
# Main optical-path view DTO builder
# ---------------------------------------------------------------------------

def build_optical_path_view_dto(lightpath_dto: "dict[str, Any]", raw_hardware: "dict[str, Any] | None" = None, vocabulary: "Vocabulary | None" = None) -> "dict[str, Any]":
    """
    Build the downstream optical-path DTO.

    Authoritative downstream contract:
    - hardware_inventory / hardware_index_map
    - light_paths (one canonical graph-backed route record per route)
    - authoritative_route_contract (compact route-planning contract for UIs/LLMs)

    Derived-only compatibility helpers:
    - sections / renderables / splitters / methods_route_views
    - runtime_splitters and other adapter/card-style projections
    """
    optical_elements = [item for item in (lightpath_dto.get("optical_path_elements") or []) if isinstance(item, dict)] if isinstance(lightpath_dto, dict) else []
    endpoints_raw = [item for item in (lightpath_dto.get("normalized_endpoints") or lightpath_dto.get("endpoints") or []) if isinstance(item, dict)] if isinstance(lightpath_dto, dict) else []
    light_paths = [item for item in (lightpath_dto.get("light_paths") or []) if isinstance(item, dict)] if isinstance(lightpath_dto, dict) else []
    raw_hardware_inventory = [item for item in (lightpath_dto.get("hardware_inventory") or []) if isinstance(item, dict)] if isinstance(lightpath_dto, dict) else []
    hardware_index_map = _normalized_hardware_index_map(
        raw_hardware_inventory,
        copy.deepcopy(lightpath_dto.get("hardware_index_map") or {}) if isinstance(lightpath_dto, dict) else {},
    )
    hardware_inventory = _normalized_hardware_inventory(raw_hardware_inventory, hardware_index_map)
    route_hardware_usage = [item for item in (lightpath_dto.get("route_hardware_usage") or []) if isinstance(item, dict)] if isinstance(lightpath_dto, dict) else []
    projection_root = (
        ((lightpath_dto.get("projections") or {}).get("virtual_microscope") or {})
        if isinstance(lightpath_dto, dict)
        else {}
    )
    legacy_splitters = [item for item in (projection_root.get("splitters") or lightpath_dto.get("splitters") or []) if isinstance(item, dict)] if isinstance(lightpath_dto, dict) else []

    # Everything in this block is a derived summary/helper layer built on top of
    # the authoritative inventory + per-route graph data below.
    derived_optical_element_cards: "list[dict[str, Any]]" = []
    derived_splitter_cards: "list[dict[str, Any]]" = []
    derived_endpoint_cards: "list[dict[str, Any]]" = []
    derived_sections: "list[dict[str, Any]]" = []

    element_items: "list[dict[str, Any]]" = []
    for element in optical_elements:
        raw_stage_role = clean_text(element.get("stage_role") or element.get("element_type") or element.get("type"))
        stage_role = resolve_stage_role_label(raw_stage_role, vocabulary) if vocabulary else raw_stage_role.replace("_", " ").title()
        if clean_text(element.get("stage_role")).lower() == "splitter":
            derived_splitter_cards.append({
                "id": clean_text(element.get("id")),
                "display_label": clean_text(element.get("name") or element.get("display_label") or element.get("id")),
                "display_subtitle": stage_role or "Splitter",
                "spec_lines": _spec_lines(("Selection mode", clean_text(element.get("selection_mode"))), ("Supported branch modes", ", ".join(element.get("supported_branch_modes") or [])), ("Supported branch count", clean_text(element.get("supported_branch_count")))),
                "method_sentence": f"Downstream routing may traverse {clean_text(element.get('name') or element.get('id'))}; explicit branch truth is declared on route-owned branch blocks.",
            })
        else:
            position_pairs = _optical_element_position_pairs(element, vocabulary)
            raw_element_type = clean_text(element.get("element_type") or element.get("type"))
            if vocabulary:
                element_type_label = resolve_element_type_label(raw_element_type, vocabulary)
            elif raw_element_type:
                element_type_label = raw_element_type.replace("_", " ").title()
            else:
                element_type_label = ""
            element_items.append({
                "id": clean_text(element.get("id")),
                "display_label": clean_text(element.get("name") or element.get("display_label") or element.get("id")),
                "display_subtitle": stage_role or "Optical path element",
                "spec_lines": _spec_lines(
                    ("Element type", element_type_label),
                    ("Details", clean_text(element.get("notes"))),
                    *position_pairs,
                ),
                "method_sentence": f"The optical path includes {clean_text(element.get('name') or element.get('id'))}.",
            })
    if element_items:
        derived_optical_element_cards.extend(element_items)
        derived_sections.append({"id": "optical_path_elements", "display_label": "Optical Path Elements", "items": element_items})
    route_splitters = [item for item in legacy_splitters if isinstance(item, dict)]
    if route_splitters:
        derived_splitter_cards = [
            {
                "id": clean_text(splitter.get("id") or splitter.get("name")),
                "display_label": clean_text(splitter.get("display_label") or splitter.get("name")),
                "display_subtitle": "Route-owned branch block",
                "spec_lines": _spec_lines(("Selection mode", clean_text(splitter.get("selection_mode"))), ("Branches", " \u2022 ".join(clean_text(branch.get("label") or branch.get("id")) for branch in splitter.get("branches", []) if isinstance(branch, dict)))),
                "method_sentence": f"Explicit route traversal branches through {clean_text(splitter.get('name') or splitter.get('display_label'))}.",
            }
            for splitter in route_splitters
        ]
    if derived_splitter_cards:
        derived_sections.append({"id": "splitters", "display_label": "Splitters / Selectors", "items": derived_splitter_cards})

    for idx, terminal in enumerate(endpoints_raw):
        raw_endpoint_type = clean_text(terminal.get("endpoint_type") or terminal.get("type") or terminal.get("kind"))
        endpoint_type = resolve_endpoint_type_label(raw_endpoint_type, vocabulary) if vocabulary else raw_endpoint_type.replace("_", " ").title()
        display_label = clean_text(terminal.get("display_label") or terminal.get("name") or terminal.get("id")) or f"Endpoint {idx + 1}"
        derived_endpoint_cards.append({
            "id": clean_text(terminal.get("id")) or f"endpoint_{idx}",
            "display_label": display_label,
            "display_subtitle": endpoint_type or "Endpoint",
            "spec_lines": _spec_lines(("Endpoint type", endpoint_type), ("Details", clean_text(terminal.get("details") or terminal.get("notes")))),
            "method_sentence": f"Detected or observed light can terminate at {display_label}.",
        })
    derived_sections.append({"id": "terminals", "display_label": "Detection Endpoints", "items": derived_endpoint_cards or [{"id": "no_explicit_terminals", "display_label": "No normalized detection endpoints available", "display_subtitle": "Structured topology incomplete", "spec_lines": ["**Action needed:** add endpoint-capable inventory rows (for example hardware.detectors[], hardware.eyepieces[], or hardware.endpoints[]) and terminate routes with explicit endpoint_id values."], "method_sentence": ""}]})

    derived_inventory_cards: "list[dict[str, Any]]" = []
    inventory_lookup = {item.get("id"): item for item in hardware_inventory if item.get("id")}
    for item in hardware_inventory:
        inventory_class = clean_text(item.get("inventory_class"))
        role = clean_text(((item.get("source_metadata") or {}) if isinstance(item.get("source_metadata"), dict) else {}).get("role"))
        manufacturer = clean_text(item.get("manufacturer"))
        model = clean_text(item.get("model"))
        product_code = clean_text(item.get("product_code"))
        method_sentence = ""
        if inventory_class == "light_source":
            method_sentence = f"Excitation was provided by {clean_text(item.get('display_label'))}."
        elif inventory_class in {"endpoint", "camera_port", "eyepiece"}:
            method_sentence = f"Detected or observed light terminated at {clean_text(item.get('display_label'))}."
        elif inventory_class == "splitter":
            method_sentence = f"The active route traversed {clean_text(item.get('display_label'))} as an explicit selector."
        elif inventory_class == "optical_element":
            method_sentence = f"The optical path included {clean_text(item.get('display_label'))}."
        derived_inventory_cards.append({
            **copy.deepcopy(item),
            "id": clean_text(item.get("id")),
            "display_number": item.get("display_number"),
            "display_label": clean_text(item.get("display_label") or item.get("id")),
            "display_subtitle": resolve_inventory_class_label(inventory_class, vocabulary) if vocabulary else inventory_class.replace("_", " ").title(),
            "spec_lines": _spec_lines(
                ("Number", f"`{item.get('display_number')}`" if item.get("display_number") else None),
                ("Manufacturer", clean_text(item.get("manufacturer"))),
                ("Model", clean_text(item.get("model"))),
                ("Product code", f"`{clean_text(item.get('product_code'))}`" if clean_text(item.get("product_code")) else None),
                ("Used in routes", ", ".join(item.get("route_usage_summary") or [])),
            ),
            "role": role,
            "method_sentence": method_sentence,
        })
    if derived_inventory_cards:
        derived_sections.insert(0, {"id": "hardware_inventory", "display_label": "Hardware Inventory", "items": derived_inventory_cards})

    route_usage_map = {clean_text(item.get("route_id")): item for item in route_hardware_usage if clean_text(item.get("route_id"))}
    runtime_splitters = copy.deepcopy(projection_root.get("splitters", lightpath_dto.get("splitters", []))) if isinstance(lightpath_dto, dict) else []

    canonical_light_paths: "list[dict[str, Any]]" = []
    derived_route_summary_cards: "list[dict[str, Any]]" = []
    derived_methods_route_views = []
    derived_branch_summary_cards: "list[dict[str, Any]]" = []

    for route in light_paths:
        route_id = clean_text(route.get("id"))
        usage = copy.deepcopy(route_usage_map.get(route_id, {}))
        hardware_ids = [clean_text(item) for item in (usage.get("hardware_inventory_ids") or route.get("hardware_inventory_ids") or []) if clean_text(item)]
        endpoint_summary = _route_endpoint_summary(usage, inventory_lookup)
        branch_summary = _route_branch_summary(route, usage)
        route_hardware_items = [
            copy.deepcopy(inventory_lookup[item_id])
            for item_id in hardware_ids
            if item_id in inventory_lookup
        ]
        graph_nodes = []
        for node in route.get("graph_nodes") or []:
            if not isinstance(node, dict):
                continue
            inventory_id = clean_text(node.get("hardware_inventory_id"))
            inventory_item = inventory_lookup.get(inventory_id) or {}
            graph_nodes.append({
                **copy.deepcopy(node),
                "display_number": node.get("inventory_display_number") or node.get("display_number") or _inventory_display_number(inventory_id, inventory_lookup, hardware_index_map),
                "inventory_display_number": node.get("inventory_display_number") or node.get("display_number") or _inventory_display_number(inventory_id, inventory_lookup, hardware_index_map),
                "inventory_item": copy.deepcopy(inventory_item) if inventory_item else None,
                "inventory_label": clean_text(inventory_item.get("display_label") or node.get("label")),
                "inventory_class": clean_text(inventory_item.get("inventory_class")),
                "inventory_identity": copy.deepcopy(node.get("inventory_identity") or inventory_item.get("inventory_identity") or {}),
                "route_usage": {
                    "route_id": route_id,
                    "phase": clean_text(node.get("phase")),
                },
                "graph_occurrence": copy.deepcopy(node.get("graph_occurrence") or {
                    "node_id": clean_text(node.get("id")),
                    "route_id": route_id,
                    "phase": clean_text(node.get("phase")),
                    "column": node.get("column"),
                    "lane": node.get("lane"),
                }),
            })
        graph_edges = [copy.deepcopy(edge) for edge in (route.get("graph_edges") or []) if isinstance(edge, dict)]
        graph_node_lookup = {clean_text(item.get("id")): item for item in graph_nodes if clean_text(item.get("id"))}
        graph_edges = [
            {
                **edge,
                "source_display_number": (graph_node_lookup.get(clean_text(edge.get("source"))) or {}).get("display_number"),
                "target_display_number": (graph_node_lookup.get(clean_text(edge.get("target"))) or {}).get("display_number"),
            }
            for edge in graph_edges
        ]

        canonical_route = {
            "id": route_id,
            "name": clean_text(route.get("name") or route.get("id")),
            "route_identity": copy.deepcopy(route.get("route_identity") or {}),
            "graph_nodes": graph_nodes,
            "graph_edges": graph_edges,
            "route_hardware_usage": usage,
            "route_local_hardware_usage": {
                "inventory_ids": hardware_ids,
                "items": route_hardware_items,
            },
            "endpoint_summary": endpoint_summary,
            "branch_summary": branch_summary,
            "illumination_traversal": copy.deepcopy(route.get("illumination_traversal") or []),
            "detection_traversal": copy.deepcopy(route.get("detection_traversal") or []),
            "route_steps": copy.deepcopy(route.get("route_steps") or []),
            "selected_execution": copy.deepcopy(route.get("selected_execution") or {}),
            "route_warnings": copy.deepcopy(route.get("route_warnings") or []),
            "illumination_sequence": copy.deepcopy(route.get("illumination_sequence") or []),
            "detection_sequence": copy.deepcopy(route.get("detection_sequence") or []),
        }

        route_hw_id_set = set(hardware_ids)
        route_light_sentences = [
            clean_text(item.get("method_sentence"))
            for item in hardware_renderables_from_inventory(derived_inventory_cards, route_hw_id_set, "light_source")
            if clean_text(item.get("method_sentence"))
        ]
        route_filter_sentences = [
            clean_text(item.get("method_sentence"))
            for item in hardware_renderables_from_inventory(derived_inventory_cards, route_hw_id_set, "optical_element")
            if clean_text(item.get("method_sentence"))
        ]
        route_splitter_sentences = [
            clean_text(item.get("method_sentence"))
            for item in hardware_renderables_from_inventory(derived_inventory_cards, route_hw_id_set, "splitter")
            if clean_text(item.get("method_sentence"))
        ]
        route_detector_sentences = [
            clean_text(item.get("method_sentence"))
            for item in hardware_renderables_from_inventory(derived_inventory_cards, route_hw_id_set, "endpoint", "camera_port", "eyepiece")
            if clean_text(item.get("method_sentence"))
        ]
        route_method_paragraph = " ".join(
            route_light_sentences + route_filter_sentences + route_splitter_sentences + route_detector_sentences
        )
        canonical_route["route_method_paragraph"] = route_method_paragraph

        canonical_light_paths.append(canonical_route)

        hardware_labels = [clean_text(item.get("display_label") or item.get("id")) for item in route_hardware_items if clean_text(item.get("display_label") or item.get("id"))]
        derived_route_summary_cards.append({
            "id": route_id,
            "display_label": canonical_route["name"],
            "display_subtitle": "Route-owned DTO graph",
            "spec_lines": _spec_lines(
                ("Graph nodes", len(graph_nodes)),
                ("Graph edges", len(graph_edges)),
                ("Hardware used", _human_list(hardware_labels[:6]) if hardware_labels else None),
                ("Endpoints", _human_list(endpoint_summary.get("labels") or [])),
                ("Branching", f"{branch_summary['count']} branch path(s) across {len(branch_summary['branch_blocks'])} block(s)" if branch_summary.get("has_branches") else "No explicit branch blocks"),
            ),
            "method_sentence": f"The {canonical_route['name']} route is rendered directly from DTO graph nodes and edges.",
        })
        derived_methods_route_views.append({
            "id": route_id,
            "display_label": canonical_route["name"],
            "route_method_paragraph": route_method_paragraph,
            "light_sources": [item for item in hardware_renderables_from_inventory(derived_inventory_cards, set(hardware_ids), "light_source")],
            "filters": [item for item in hardware_renderables_from_inventory(derived_inventory_cards, set(hardware_ids), "optical_element")],
            "splitters": [item for item in hardware_renderables_from_inventory(derived_inventory_cards, set(hardware_ids), "splitter")],
            "detectors": [item for item in hardware_renderables_from_inventory(derived_inventory_cards, set(hardware_ids), "endpoint", "camera_port", "eyepiece")],
            "endpoints": copy.deepcopy(endpoint_summary.get("items") or []),
            "route_hardware_usage": copy.deepcopy(usage),
            "graph_nodes": copy.deepcopy(graph_nodes),
            "graph_edges": copy.deepcopy(graph_edges),
            "branch_summary": copy.deepcopy(branch_summary),
        })
        if branch_summary.get("has_branches"):
            derived_branch_summary_cards.append({
                "id": route_id,
                "display_label": canonical_route["name"],
                "display_subtitle": "Route-owned branch summary",
                "spec_lines": _spec_lines(
                    ("Selection modes", ", ".join(branch_summary.get("selection_modes") or [])),
                    ("Branches", " \u2022 ".join(branch.get("label") or branch.get("branch_id") for branch in branch_summary.get("branches") or [] if clean_text(branch.get("label") or branch.get("branch_id")))),
                    ("Endpoints", _human_list(endpoint_summary.get("labels") or [])),
                ),
                "method_sentence": f"Explicit route traversal branches are declared directly on the {canonical_route['name']} route.",
            })

    if derived_route_summary_cards:
        derived_sections.append({"id": "light_paths", "display_label": "Light Paths", "items": derived_route_summary_cards})
    if derived_branch_summary_cards:
        derived_splitter_cards = derived_branch_summary_cards
    derived_renderables = [*derived_inventory_cards, *derived_route_summary_cards, *derived_optical_element_cards, *derived_splitter_cards, *derived_endpoint_cards]

    authoritative_route_contract_routes: "list[dict[str, Any]]" = []
    compact_hardware_inventory = [
        {
            "id": clean_text(item.get("id")),
            "display_label": clean_text(item.get("display_label") or item.get("id")),
            "display_number": item.get("display_number"),
            "inventory_class": clean_text(item.get("inventory_class")),
            "route_usage_summary": list(item.get("route_usage_summary") or []),
            "modalities": list(item.get("modalities") or []),
            "manufacturer": clean_text(item.get("manufacturer")),
            "model": clean_text(item.get("model")),
            "endpoint_type": clean_text(item.get("endpoint_type")),
        }
        for item in hardware_inventory
        if isinstance(item, dict)
    ]
    compact_normalized_endpoints = [
        {
            "id": clean_text(endpoint.get("id")),
            "display_label": clean_text(endpoint.get("display_label") or endpoint.get("channel_name") or endpoint.get("name") or endpoint.get("id")),
            "endpoint_type": clean_text(endpoint.get("endpoint_type") or endpoint.get("kind") or endpoint.get("type")),
            "source_section": clean_text(endpoint.get("source_section")),
            "modalities": list(endpoint.get("modalities") or []),
        }
        for endpoint in endpoints_raw
        if isinstance(endpoint, dict)
    ]

    for route_renderable in canonical_light_paths:
        route_id = clean_text(route_renderable.get("id"))
        route_usage = route_renderable.get("route_hardware_usage") if isinstance(route_renderable.get("route_hardware_usage"), dict) else {}
        route_inventory_ids = [
            clean_text(item)
            for item in (
                route_usage.get("hardware_inventory_ids")
                or ((route_renderable.get("route_local_hardware_usage") or {}).get("inventory_ids") if isinstance(route_renderable.get("route_local_hardware_usage"), dict) else [])
                or []
            )
            if clean_text(item)
        ]
        route_inventory_items = [
            copy.deepcopy(inventory_lookup[item_id])
            for item_id in route_inventory_ids
            if item_id in inventory_lookup
        ]

        def summarize_inventory_items(*classes: str) -> "list[dict[str, Any]]":
            class_set = {clean_text(value) for value in classes if clean_text(value)}
            return [
                {
                    "id": clean_text(item.get("id")),
                    "display_label": clean_text(item.get("display_label") or item.get("id")),
                    "display_number": item.get("display_number"),
                    "inventory_class": clean_text(item.get("inventory_class")),
                    "route_usage_summary": list(item.get("route_usage_summary") or []),
                    "modalities": list(item.get("modalities") or []),
                    "endpoint_type": clean_text(item.get("endpoint_type")),
                    "manufacturer": clean_text(item.get("manufacturer")),
                    "model": clean_text(item.get("model")),
                }
                for item in route_inventory_items
                if clean_text(item.get("inventory_class")) in class_set
            ]

        route_identity = route_renderable.get("route_identity") if isinstance(route_renderable.get("route_identity"), dict) else {}
        route_label = clean_text(route_renderable.get("name") or route_renderable.get("id"))
        illumination_mode = clean_text(route_identity.get("modality") or route_id)
        selected_execution = copy.deepcopy(route_renderable.get("selected_execution") or {})
        authoritative_route_contract_routes.append({
            "id": route_id,
            "display_label": route_label,
            "illumination_mode": illumination_mode,
            "route_identity": copy.deepcopy(route_identity),
            "route_hardware_usage": {
                "hardware_inventory_ids": route_inventory_ids,
                "endpoint_inventory_ids": list(route_usage.get("endpoint_inventory_ids") or []),
                "illumination_hardware_inventory_ids": list(route_usage.get("illumination_hardware_inventory_ids") or []),
                "detection_hardware_inventory_ids": list(route_usage.get("detection_hardware_inventory_ids") or []),
            },
            "relevant_hardware": {
                "sources": summarize_inventory_items("light_source"),
                "filters": summarize_inventory_items("optical_element"),
                "splitters": summarize_inventory_items("splitter"),
                "endpoints": summarize_inventory_items("endpoint", "camera_port", "eyepiece"),
            },
            "endpoint_summary": copy.deepcopy(route_renderable.get("endpoint_summary") or {}),
            "branch_summary": copy.deepcopy(route_renderable.get("branch_summary") or {}),
            "topology": {
                "graph_nodes": [
                    {
                        "id": clean_text(node.get("id")),
                        "label": clean_text(node.get("label") or node.get("inventory_label") or node.get("id")),
                        "component_kind": clean_text(node.get("component_kind") or node.get("stage_role") or node.get("endpoint_type")),
                        "phase": clean_text(node.get("phase")),
                        "hardware_inventory_id": clean_text(node.get("hardware_inventory_id")),
                        "display_number": node.get("inventory_display_number") or node.get("display_number"),
                        "column": node.get("column"),
                        "lane": node.get("lane"),
                        "endpoint_type": clean_text(node.get("endpoint_type")),
                    }
                    for node in (route_renderable.get("graph_nodes") or [])
                    if isinstance(node, dict)
                ],
                "graph_edges": [
                    {
                        "source": clean_text(edge.get("source")),
                        "target": clean_text(edge.get("target")),
                        "label": clean_text(edge.get("label") or edge.get("branch_id")),
                    }
                    for edge in (route_renderable.get("graph_edges") or [])
                    if isinstance(edge, dict)
                ],
            },
            "selected_execution": selected_execution,
            "route_optical_facts": _build_route_optical_facts(selected_execution),
            "method_sentence": (
                f"The {route_label} illumination mode / route was used."
                if route_label
                else ""
            ),
            "route_method_paragraph": clean_text(route_renderable.get("route_method_paragraph") or ""),
        })

    view_diagnostics: "list[dict[str, str]]" = []
    if not hardware_inventory:
        view_diagnostics.append({"severity": "warning", "code": "missing_hardware_inventory", "message": "missing in DTO: hardware_inventory"})
    if not canonical_light_paths:
        view_diagnostics.append({"severity": "warning", "code": "missing_light_paths", "message": "missing in DTO: light_paths"})

    return {
        **copy.deepcopy(lightpath_dto),
        "runtime_splitters": runtime_splitters,
        "hardware_inventory": copy.deepcopy(hardware_inventory),
        "hardware_index_map": copy.deepcopy(hardware_index_map),
        "light_paths": canonical_light_paths,
        "route_renderables": canonical_light_paths,
        "routes": canonical_light_paths,
        "filters": derived_optical_element_cards,
        "splitters": derived_splitter_cards,
        "terminal_renderables": derived_endpoint_cards,
        "hardware_inventory_renderables": derived_inventory_cards,
        "methods_route_options": [
            {
                "id": item["id"],
                "label": item["display_label"],
                "display_label": item["display_label"],
                "method_sentence": item.get("route_method_paragraph", ""),
            }
            for item in derived_methods_route_views
        ],
        "methods_route_views": derived_methods_route_views,
        "sections": derived_sections,
        "renderables": derived_renderables,
        "primary_rendering_contract": {
            "routes": "light_paths",
            "hardware_inventory": "hardware_inventory",
            "hardware_index_map": "hardware_index_map",
            "graph_fields": ["graph_nodes", "graph_edges"],
        },
        "derived_projection_contract": {
            "sections": "sections",
            "splitter_summaries": "splitters",
            "inventory_cards": "hardware_inventory_renderables",
            "route_summary_cards": "renderables/light_paths",
            "methods_route_views": "methods_route_views",
        },
        "authoritative_route_contract": {
            "contract_version": "authoritative_route_contract.v1",
            "primary_rendering_contract": {
                "routes": "light_paths",
                "hardware_inventory": "hardware_inventory",
                "route_hardware_usage": "route_hardware_usage",
                "normalized_endpoints": "normalized_endpoints",
                "graph_fields": ["graph_nodes", "graph_edges"],
            },
            "available_routes": [
                {
                    "id": clean_text(item.get("id")),
                    "display_label": clean_text(item.get("display_label") or item.get("label") or item.get("id")),
                }
                for item in derived_methods_route_views
                if isinstance(item, dict)
            ],
            "hardware_inventory": compact_hardware_inventory,
            "normalized_endpoints": compact_normalized_endpoints,
            "route_hardware_usage": copy.deepcopy(route_hardware_usage),
            "routes": authoritative_route_contract_routes,
        },
        "view_diagnostics": view_diagnostics,
    }


def build_optical_path_dto(lightpath_dto: "dict[str, Any]", raw_hardware: "dict[str, Any] | None" = None, vocabulary: "Vocabulary | None" = None) -> "dict[str, Any]":
    """Backward-compatible alias for build_optical_path_view_dto."""
    return build_optical_path_view_dto(lightpath_dto, raw_hardware=raw_hardware, vocabulary=vocabulary)


__all__ = [
    "build_optical_path_view_dto",
    "build_optical_path_dto",
    "hardware_renderables_from_inventory",
    "_route_endpoint_summary",
    "_route_branch_summary",
    "_build_route_optical_facts",
    "_terminal_summary",
    "_mechanism_preview",
    "_format_position_value",
    "_optical_element_position_pairs",
    "_first_component_label",
]
