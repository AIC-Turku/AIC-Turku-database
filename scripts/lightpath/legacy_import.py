"""Legacy light-path import adapter.

This module is the only allowed place where legacy light-path structures are
converted into the canonical v2 light-path model.

Legacy inputs handled here:
- hardware.light_sources[]
- hardware.light_path.*
- legacy light-path endpoint declarations

Production strict flows should use the canonical parser and must not silently
fall back to this adapter.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from scripts.lightpath.parse_canonical import (
    CANONICAL_ENDPOINT_COLLECTION_KEYS,
    ENDPOINT_CAPABLE_INVENTORY_KEYS,
    _canonical_light_path_model,
    _clean_identifier,
    _collect_splitters,
    _modality_match,
    _normalize_canonical_optical_path_elements,
    _normalize_canonical_source_rows,
    _normalize_endpoint_capable_row,
    _normalize_modalities,
    _normalized_endpoint_inventory,
    _resolve_route_label,
)


def has_legacy_light_path_input(instrument_dict: dict[str, Any]) -> bool:
    """Return True when legacy-only topology structures are present."""
    hardware = (
        instrument_dict.get("hardware")
        if isinstance(instrument_dict.get("hardware"), dict)
        else {}
    )
    legacy_light_path = hardware.get("light_path")
    legacy_light_sources = hardware.get("light_sources")

    return (
        (isinstance(legacy_light_path, dict) and bool(legacy_light_path))
        or (isinstance(legacy_light_sources, list) and bool(legacy_light_sources))
    )


def _import_legacy_source_rows(hardware: dict[str, Any]) -> list[dict[str, Any]]:
    """Import legacy hardware.light_sources[] as canonical hardware.sources[]."""
    raw_sources = hardware.get("light_sources")
    if not isinstance(raw_sources, list):
        return []

    return _normalize_canonical_source_rows(raw_sources)


def _import_legacy_endpoint_rows(
    hardware: dict[str, Any],
    legacy_light_path: dict[str, Any],
) -> list[dict[str, Any]]:
    """Import endpoint-capable legacy rows into canonical endpoint rows."""
    rows, _ = _normalized_endpoint_inventory(hardware, legacy_light_path)
    return rows


def _import_legacy_optical_path_elements(
    hardware: dict[str, Any],
    legacy_light_path: dict[str, Any],
) -> list[dict[str, Any]]:
    """Import legacy mechanism collections into canonical optical_path_elements[]."""
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
        if not isinstance(splitter, dict):
            continue

        cloned = dict(splitter)
        cloned.setdefault("stage_role", "splitter")
        raw_elements.append(cloned)

    return _normalize_canonical_optical_path_elements(raw_elements)


def _import_legacy_light_paths(
    sources: list[dict[str, Any]],
    elements: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Synthesize canonical light_paths[] from legacy route/path tags."""
    route_ids: set[str] = set()

    for collection in (sources, elements, endpoints):
        for row in collection:
            route_ids.update(
                _normalize_modalities(
                    row.get("modalities")
                    or row.get("path")
                    or row.get("routes")
                )
            )

    if not route_ids:
        route_ids = {"epi"}

    ordered_routes = sorted(route_ids)

    routes: list[dict[str, Any]] = []

    stage_order = {
        "illumination": ["excitation", "cube", "dichroic"],
        "detection": ["cube", "dichroic", "emission", "analyzer", "splitter"],
    }

    for route_id in ordered_routes:
        illumination_sequence = [
            {"source_id": source["id"]}
            for source in sources
            if _modality_match(
                _normalize_modalities(
                    source.get("modalities")
                    or source.get("path")
                    or source.get("routes")
                ),
                route_id,
            )
        ]

        for stage_role in stage_order["illumination"]:
            illumination_sequence.extend(
                {"optical_path_element_id": element["id"]}
                for element in elements
                if element.get("stage_role") == stage_role
                and _modality_match(
                    _normalize_modalities(
                        element.get("modalities")
                        or element.get("path")
                        or element.get("routes")
                    ),
                    route_id,
                )
            )

        detection_sequence: list[dict[str, Any]] = []

        for stage_role in stage_order["detection"]:
            detection_sequence.extend(
                {"optical_path_element_id": element["id"]}
                for element in elements
                if element.get("stage_role") == stage_role
                and _modality_match(
                    _normalize_modalities(
                        element.get("modalities")
                        or element.get("path")
                        or element.get("routes")
                    ),
                    route_id,
                )
            )

        has_route_splitter = any(
            element.get("stage_role") == "splitter"
            and _modality_match(
                _normalize_modalities(
                    element.get("modalities")
                    or element.get("path")
                    or element.get("routes")
                ),
                route_id,
            )
            for element in elements
        )

        if not has_route_splitter:
            detection_sequence.extend(
                {"endpoint_id": endpoint["id"]}
                for endpoint in endpoints
                if _modality_match(
                    _normalize_modalities(
                        endpoint.get("modalities")
                        or endpoint.get("path")
                        or endpoint.get("routes")
                    ),
                    route_id,
                )
            )

        if not illumination_sequence and not detection_sequence:
            continue

        routes.append(
            {
                "id": route_id,
                "name": _resolve_route_label(route_id),
                "illumination_sequence": illumination_sequence,
                "detection_sequence": detection_sequence,
            }
        )

    return routes


def import_legacy_light_path_model(instrument_dict: dict[str, Any]) -> dict[str, Any]:
    """Import legacy light-path topology into the canonical v2 shape.

    This adapter is the only place where legacy `hardware.light_path` and
    `hardware.light_sources` structures are converted into canonical v2 data.
    """
    hardware = (
        instrument_dict.get("hardware")
        if isinstance(instrument_dict.get("hardware"), dict)
        else {}
    )
    legacy_light_path = (
        hardware.get("light_path")
        if isinstance(hardware.get("light_path"), dict)
        else {}
    )

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


def migrate_instrument_to_light_path_v2(instrument_dict: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of an instrument payload migrated to canonical light-path v2.

    This is a migration helper. It may use the legacy adapter when the input is
    legacy-only, then writes the canonicalized fields back into a copied payload.
    """
    from scripts.lightpath.parse_canonical import canonicalize_light_path_model

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


__all__ = [
    "has_legacy_light_path_input",
    "import_legacy_light_path_model",
    "migrate_instrument_to_light_path_v2",
    "_import_legacy_source_rows",
    "_import_legacy_endpoint_rows",
    "_import_legacy_optical_path_elements",
    "_import_legacy_light_paths",
]
