"""Virtual-microscope payload assembly.

This module owns the downstream virtual-microscope projection generated from
canonical light-path DTOs.

Responsibilities:
- generate_virtual_microscope_payload()
- canonical DTO + derived virtual_microscope projection assembly
- runtime stage/source/detector/splitter projection
- route catalog projection

Non-responsibilities:
- canonical YAML parsing implementation
- legacy light-path import
- validation diagnostics
- route graph construction
- selected_execution construction
- spectral operation derivation

It must not import scripts.light_path_parser.
"""

from __future__ import annotations

import json
from typing import Any

from scripts.display_labels import VocabLookup
from scripts.lightpath.model import (
    _clean_identifier,
    _clean_string,
    _normalize_endpoint_type,
    _normalize_modalities,
    _normalize_routes,
    _resolve_route_label,
    set_active_vocab,
    get_active_vocab,
)
from scripts.lightpath.parse_canonical import (
    canonicalize_light_path_model,
    parse_strict_canonical_light_path_model,
)
from scripts.lightpath.route_graph import (
    _build_hardware_inventory,
    _build_route_sequences_and_graph,
    _choice_positions,
    _collect_route_owned_splitters,
    calculate_valid_paths,
)
from scripts.lightpath.spectral_ops import (
    _candidate_terminals_for_routes,
    _cube_mechanism_payload,
    _infer_default_terminals,
    _mechanism_payload,
    _resolve_target_ids,
    _source_position,
    _splitter_payload,
    _terminal_payload_from_endpoint,
)


def _json_clone(value: Any) -> Any:
    """Return a JSON-compatible deep copy matching the monolith behavior."""
    return json.loads(json.dumps(value))


def _route_catalog_entries(payload: dict[str, Any]) -> list[dict[str, str]]:
    """Build route catalog entries discovered from derived runtime controls.

    This is a derived runtime convenience. Canonical route truth remains
    payload["light_paths"].
    """
    constrained_routes: list[str] = []

    def collect_from_component(component: Any) -> None:
        if not isinstance(component, dict):
            return

        for route in _normalize_routes(
            component.get("routes")
            or component.get("path")
            or component.get("paths")
            or component.get("route")
        ):
            if isinstance(route, str) and route and route not in constrained_routes:
                constrained_routes.append(route)

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
        for route_id in constrained_routes
    ]


def generate_virtual_microscope_payload(
    instrument_dict: dict,
    *,
    include_inferred_terminals: bool = False,
    vocab: VocabLookup | None = None,
    compatibility_mode: bool = False,
) -> dict:
    """Build the authoritative canonical DTO plus explicit downstream projections.

    Top-level DTO fields are the canonical contract consumed across the
    repository:
    - sources
    - optical_path_elements
    - endpoints / normalized_endpoints
    - hardware_inventory / hardware_index_map
    - route_hardware_usage
    - light_paths

    Runtime/UI convenience structures remain available only under
    projections.virtual_microscope, so legacy-style stage buckets and splitter
    renderables are clearly derived adapters rather than co-equal topology truth.
    """
    previous_vocab = get_active_vocab()
    set_active_vocab(vocab)

    try:
        return _generate_virtual_microscope_payload_inner(
            instrument_dict,
            include_inferred_terminals=include_inferred_terminals,
            compatibility_mode=compatibility_mode,
        )
    finally:
        set_active_vocab(previous_vocab)


def _generate_virtual_microscope_payload_inner(
    instrument_dict: dict,
    *,
    include_inferred_terminals: bool = False,
    compatibility_mode: bool = False,
) -> dict:
    """Inner implementation; caller is responsible for active vocab context."""
    parser_input = instrument_dict if isinstance(instrument_dict, dict) else {}

    canonical = (
        canonicalize_light_path_model(parser_input)
        if compatibility_mode
        else parse_strict_canonical_light_path_model(parser_input)
    )

    sources = canonical["sources"]
    elements = canonical["optical_path_elements"]
    endpoints = canonical["endpoints"]
    raw_light_paths = canonical["light_paths"]

    hardware_inventory, hardware_index_map = _build_hardware_inventory(
        sources,
        elements,
        endpoints,
    )

    inventory_lookup = {
        item["id"]: item
        for item in hardware_inventory
        if isinstance(item, dict) and item.get("id")
    }
    source_lookup = {
        entry.get("id"): entry
        for entry in sources
        if isinstance(entry, dict) and entry.get("id")
    }
    element_lookup = {
        entry.get("id"): entry
        for entry in elements
        if isinstance(entry, dict) and entry.get("id")
    }
    endpoint_lookup = {
        entry.get("id"): entry
        for entry in endpoints
        if isinstance(entry, dict) and entry.get("id")
    }

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
            item["route_usage_summary"] = route_usage_by_inventory_id.get(
                inventory_id,
                [],
            )

    stage_mappings: dict[str, list[dict[str, Any]]] = {
        "excitation": [],
        "dichroic": [],
        "emission": [],
        "cube": [],
        "analyzer": [],
    }
    prefix_mappings = {
        "excitation": "exc",
        "dichroic": "dichroic",
        "emission": "em",
        "cube": "cube",
        "analyzer": "analyzer",
    }

    payload: dict[str, Any] = {
        "dto_schema": "light_paths_v2",
        "metadata": {
            "wavelength_grid": {
                "min_nm": 350,
                "max_nm": 1700,
                "step_nm": 2,
            },
            "yaml_source_of_truth": True,
            "topology_contract": (
                "schema -> validator -> canonical dto -> derived adapters -> consumers"
            ),
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
        "sources": _json_clone(sources),
        "optical_path_elements": _json_clone(elements),
        "endpoints": _json_clone(endpoints),
        "normalized_endpoints": _json_clone(endpoints),
        "hardware_inventory": _json_clone(hardware_inventory),
        "hardware_index_map": _json_clone(hardware_index_map),
        "route_hardware_usage": _json_clone(route_hardware_usage),
        "light_paths": _json_clone(light_paths),

        # Derived runtime adapter fields.
        "light_sources": [],
        "detectors": [],
        "terminals": [],
        "stages": {
            "excitation": [],
            "dichroic": [],
            "emission": [],
            "cube": [],
        },
        "splitters": [],
        "valid_paths": [],
        "available_routes": [
            {
                "id": route["id"],
                "label": route.get("name") or _resolve_route_label(route["id"]),
            }
            for route in light_paths
        ],
        "default_route": light_paths[0]["id"] if light_paths else None,
    }

    positions: dict[int, dict[str, Any]] = {}
    for idx, src in enumerate(sources, start=1):
        positions[idx] = _source_position(idx, src)

        src_modalities = _normalize_modalities(
            src.get("modalities")
            or src.get("path")
            or src.get("routes")
        )
        if src_modalities:
            positions[idx]["routes"] = src_modalities
            positions[idx]["path"] = src_modalities[0]

    if positions:
        payload["light_sources"].append(
            {
                "id": "light_sources_0",
                "name": "Sources",
                "display_label": "Sources",
                "type": "light_source_group",
                "control_kind": "checkboxes",
                "selection_mode": "multi",
                "positions": positions,
                "options": [
                    {
                        "slot": slot,
                        "display_label": entry.get("display_label"),
                        "value": entry,
                    }
                    for slot, entry in sorted(positions.items())
                ],
            }
        )

    def terminal_from_endpoint(endpoint: dict[str, Any], index: int) -> dict[str, Any]:
        payload_row = _terminal_payload_from_endpoint(index, endpoint)

        modalities = _normalize_modalities(
            endpoint.get("modalities")
            or endpoint.get("path")
            or endpoint.get("routes")
        )
        if modalities:
            payload_row["routes"] = modalities
            payload_row["path"] = modalities[0]

        return payload_row

    explicit_endpoints = endpoints
    for idx, endpoint in enumerate(explicit_endpoints, start=1):
        terminal = terminal_from_endpoint(endpoint, idx)
        payload["terminals"].append(terminal)

        if (
            _normalize_endpoint_type(
                endpoint.get("endpoint_type")
                or endpoint.get("type")
                or endpoint.get("kind")
            )
            != "detector"
        ):
            continue

        mechanism_id = _clean_identifier(endpoint.get("id")) or f"detector_{idx}"
        detector_group: dict[str, Any] = {
            "id": mechanism_id,
            "name": terminal.get("channel_name") or terminal.get("display_label"),
            "display_label": terminal.get("display_label"),
            "type": "detector_group",
            "control_kind": "detector_toggle",
            "selection_mode": "multi",
            "positions": {1: dict(terminal)},
            "options": [
                {
                    "slot": 1,
                    "display_label": terminal.get("display_label"),
                    "value": dict(terminal),
                }
            ],
        }
        if terminal.get("routes"):
            detector_group["routes"] = terminal.get("routes")
            detector_group["path"] = terminal.get("path")

        payload["detectors"].append(detector_group)

    if include_inferred_terminals:
        _infer_default_terminals(
            instrument_dict,
            payload["splitters"],
            payload["terminals"],
        )
        payload["metadata"]["uses_inferred_terminals"] = True

    payload["metadata"]["graph_incomplete"] = (
        len(payload["terminals"]) == 0
        or any(
            not branch.get("target_ids")
            for splitter in payload["splitters"]
            if isinstance(splitter, dict)
            for branch in splitter.get("branches", [])
            if isinstance(branch, dict)
        )
    )

    derived_route_splitters = _collect_route_owned_splitters(
        light_paths,
        elements,
        endpoints,
    )

    def splitter_payload_from_legacy_element(
        element: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        routes = _normalize_modalities(
            element.get("modalities")
            or element.get("path")
            or element.get("routes")
        )
        candidate_terminals = _candidate_terminals_for_routes(
            payload["terminals"],
            routes,
        )
        raw_splitter: dict[str, Any] = {
            "name": element.get("name")
            or element.get("display_label")
            or f"Splitter {index + 1}",
            "path": routes[0] if routes else element.get("path"),
            "routes": routes,
            "selection_mode": element.get("selection_mode"),
            "dichroic": (
                element.get("dichroic")
                if isinstance(element.get("dichroic"), dict)
                else {}
            ),
            "branches": [],
        }

        for branch in element.get("branches") or []:
            if not isinstance(branch, dict):
                continue

            raw_splitter["branches"].append(
                {
                    "id": branch.get("id"),
                    "label": branch.get("label") or branch.get("name"),
                    "mode": branch.get("mode"),
                    "component": (
                        branch.get("component")
                        if isinstance(branch.get("component"), dict)
                        else {}
                    ),
                    "target_ids": _resolve_target_ids(
                        branch.get("target_ids") or [],
                        candidate_terminals or payload["terminals"],
                    ),
                }
            )

        splitter_payload = _splitter_payload(index, raw_splitter, payload["terminals"])
        splitter_payload["id"] = element.get("id") or splitter_payload.get("id")

        if routes:
            splitter_payload["routes"] = routes
            splitter_payload["path"] = routes[0]

        if any(
            not branch.get("target_ids")
            for branch in splitter_payload.get("branches", [])
        ):
            payload["metadata"]["graph_incomplete"] = True

        return splitter_payload

    def splitter_payload_from_route_splitter(
        splitter: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        routes = _normalize_modalities(
            splitter.get("routes")
            or splitter.get("__routes")
            or splitter.get("path")
        )
        candidate_terminals = _candidate_terminals_for_routes(
            payload["terminals"],
            routes,
        )
        raw_splitter: dict[str, Any] = {
            "name": splitter.get("name")
            or splitter.get("display_label")
            or f"Splitter {index + 1}",
            "path": routes[0] if routes else splitter.get("path"),
            "routes": routes,
            "selection_mode": splitter.get("selection_mode"),
            "branches": [],
        }

        for branch in splitter.get("branches") or []:
            if not isinstance(branch, dict):
                continue

            raw_splitter["branches"].append(
                {
                    "id": branch.get("id"),
                    "label": branch.get("label") or branch.get("name"),
                    "mode": branch.get("mode"),
                    "component": (
                        branch.get("component")
                        if isinstance(branch.get("component"), dict)
                        else {}
                    ),
                    "sequence": _json_clone(branch.get("sequence") or []),
                    "target_ids": _resolve_target_ids(
                        branch.get("target_ids") or [],
                        candidate_terminals or payload["terminals"],
                    ),
                    "__routes": list(branch.get("__routes") or []),
                }
            )

        splitter_payload = _splitter_payload(index, raw_splitter, payload["terminals"])
        splitter_payload["id"] = splitter.get("id") or splitter_payload.get("id")
        splitter_payload["branch_selection_required"] = (
            splitter.get("selection_mode") == "exclusive"
            and len(splitter_payload.get("branches", [])) > 1
        )

        for branch_index, branch in enumerate(splitter_payload.get("branches", [])):
            source_branch = (
                (splitter.get("branches") or [])[branch_index]
                if branch_index < len(splitter.get("branches") or [])
                else {}
            )
            if isinstance(source_branch, dict):
                branch["sequence"] = _json_clone(source_branch.get("sequence") or [])
                if source_branch.get("__routes"):
                    branch["__routes"] = list(source_branch.get("__routes") or [])

        if routes:
            splitter_payload["routes"] = routes
            splitter_payload["path"] = routes[0]

        if any(
            not branch.get("target_ids")
            for branch in splitter_payload.get("branches", [])
        ):
            payload["metadata"]["graph_incomplete"] = True

        return splitter_payload

    stage_indices = {
        "excitation": 0,
        "dichroic": 0,
        "emission": 0,
        "cube": 0,
        "analyzer": 0,
    }

    for element in elements:
        stage_role = element.get("stage_role")

        if stage_role == "splitter":
            continue

        if stage_role not in stage_mappings:
            continue

        index = stage_indices[stage_role]

        if stage_role == "cube":
            stage_mappings[stage_role].append(
                _cube_mechanism_payload(index, element)
            )
        else:
            stage_mappings[stage_role].append(
                _mechanism_payload(prefix_mappings[stage_role], index, element)
            )

        stage_indices[stage_role] += 1

    for splitter_index, splitter in enumerate(derived_route_splitters):
        payload["splitters"].append(
            splitter_payload_from_route_splitter(splitter, splitter_index)
        )

    represented_splitter_ids = {
        splitter.get("id")
        for splitter in derived_route_splitters
        if splitter.get("id")
    }

    for element in elements:
        if element.get("stage_role") != "splitter":
            continue
        if element.get("id") in represented_splitter_ids:
            continue

        payload["splitters"].append(
            splitter_payload_from_legacy_element(
                element,
                len(payload["splitters"]),
            )
        )

    payload["stages"] = stage_mappings
    payload["valid_paths"] = calculate_valid_paths(payload)

    # If runtime controls reveal additional constrained routes, preserve the
    # canonical light_paths route catalog as primary but include discovered
    # routes not already represented.
    discovered_routes = _route_catalog_entries(payload)
    known_route_ids = {
        route.get("id")
        for route in payload.get("available_routes", [])
        if isinstance(route, dict)
    }
    for route in discovered_routes:
        route_id = route.get("id")
        if route_id and route_id not in known_route_ids:
            payload["available_routes"].append(route)
            known_route_ids.add(route_id)

    runtime_projection = {
        "light_sources": _json_clone(payload["light_sources"]),
        "detectors": _json_clone(payload["detectors"]),
        "terminals": _json_clone(payload["terminals"]),
        "stages": _json_clone(payload["stages"]),
        "splitters": _json_clone(payload["splitters"]),
        "valid_paths": _json_clone(payload["valid_paths"]),
        "available_routes": _json_clone(payload["available_routes"]),
        "default_route": payload["default_route"],
        "route_hardware_usage": _json_clone(payload["route_hardware_usage"]),
    }

    canonical_payload = {
        "dto_schema": payload["dto_schema"],
        "metadata": {
            **_json_clone(payload["metadata"]),
            "derived_adapters": ["virtual_microscope"],
        },
        "simulation": {
            "wavelength_grid": _json_clone(payload["metadata"]["wavelength_grid"]),
            "graph_incomplete": payload["metadata"].get("graph_incomplete", False),
            "uses_inferred_terminals": payload["metadata"].get(
                "uses_inferred_terminals",
                False,
            ),
            "default_route": payload["default_route"],
            "route_catalog": _json_clone(payload["available_routes"]),
        },
        "sources": _json_clone(payload["sources"]),
        "optical_path_elements": _json_clone(payload["optical_path_elements"]),
        "endpoints": _json_clone(payload["endpoints"]),
        "normalized_endpoints": _json_clone(payload["normalized_endpoints"]),
        "hardware_inventory": _json_clone(payload["hardware_inventory"]),
        "hardware_index_map": _json_clone(payload["hardware_index_map"]),
        "route_hardware_usage": _json_clone(payload["route_hardware_usage"]),
        "light_paths": _json_clone(payload["light_paths"]),
        "projections": {
            "virtual_microscope": runtime_projection,
        },
    }

    return _json_clone(canonical_payload)


__all__ = [
    "generate_virtual_microscope_payload",
    "_generate_virtual_microscope_payload_inner",
    "_route_catalog_entries",
]
