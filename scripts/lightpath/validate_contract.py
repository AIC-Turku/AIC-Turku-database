"""Light-path contract validation.

This module owns validation diagnostics for canonical light-path topology.

Responsibilities:
- validate canonical light-path route/sequence shape
- validate endpoint collisions
- validate branch blocks
- validate explicit endpoint termination
- validate filter-cube structured spectral authoring
- surface parse warnings as hard validation errors

It must not import scripts.light_path_parser.
It should not own canonical parsing, legacy import, route graph construction,
selected_execution projection, spectral-op derivation, or VM payload assembly.
"""

from __future__ import annotations

from typing import Any

from scripts.lightpath.model import (
    CUBE_FILTER_COMPONENT_TYPES,
    CUBE_LINK_KEYS,
    DICHROIC_TYPES,
    SEQUENCE_TOPOLOGY_KEYS,
    _as_list,
    _clean_identifier,
    _clean_string,
    _coerce_number,
    _normalize_modalities,
)
from scripts.lightpath.parse_canonical import (
    _collect_splitters,
    _has_canonical_light_path_input,
    _normalized_endpoint_inventory,
    canonicalize_light_path_model,
)
from scripts.lightpath.route_graph import (
    _build_hardware_inventory,
    _build_route_sequences_and_graph,
    _position_id_matches_element,
)
from scripts.lightpath.spectral_ops import (
    _component_payload,
)


def validate_light_path(instrument_dict: dict) -> list[str]:
    """Return hard validation errors for a light-path payload."""
    errors, _, _ = validate_light_path_diagnostics(instrument_dict)
    return errors


def validate_light_path_warnings(instrument_dict: dict) -> list[str]:
    """Return non-fatal light-path validation warnings."""
    _, warnings, _ = validate_light_path_diagnostics(instrument_dict)
    return warnings


def validate_filter_cube_warnings(instrument_dict: dict) -> list[str]:
    """Return warnings specific to degraded/non-authoritative filter-cube positions."""
    _, _, cube_warnings = validate_light_path_diagnostics(instrument_dict)
    return cube_warnings


def _sequence_terminates_with_explicit_endpoint(sequence: Any) -> bool:
    """Return True when a sequence or all branch-local sequences end at endpoint_id."""
    if not isinstance(sequence, list):
        return False

    for item in reversed(sequence):
        if not isinstance(item, dict):
            continue

        branch_block = item.get("branches")
        if isinstance(branch_block, dict):
            branches = [
                branch
                for branch in branch_block.get("items") or []
                if isinstance(branch, dict)
            ]
            return bool(branches) and all(
                _sequence_terminates_with_explicit_endpoint(branch.get("sequence"))
                for branch in branches
            )

        if _clean_identifier(item.get("endpoint_id")):
            return True

        if (
            _clean_identifier(item.get("optical_path_element_id"))
            or _clean_identifier(item.get("source_id"))
        ):
            return False

    return False


def _sequence_item_allowed_keys(
    sequence_key: str,
    *,
    allow_branches: bool,
) -> tuple[str, ...]:
    """Return the allowed discriminated-union keys for a sequence item."""
    reference_keys = (
        ("source_id", "optical_path_element_id")
        if sequence_key.startswith("illumination_sequence")
        else ("optical_path_element_id", "endpoint_id")
    )

    return reference_keys + (("branches",) if allow_branches else ())


def _sequence_item_union_message(
    sequence_key: str,
    *,
    allow_branches: bool,
) -> str:
    """Build a human-readable sequence item union validation message."""
    allowed_keys = _sequence_item_allowed_keys(
        sequence_key,
        allow_branches=allow_branches,
    )

    if sequence_key.startswith("illumination_sequence"):
        context = "illumination sequence item"
    elif sequence_key.startswith("detection_sequence"):
        context = (
            "detection sequence item"
            if allow_branches
            else "branch-local detection sequence item"
        )
    else:
        context = "sequence item"

    if (
        sequence_key.startswith("illumination_sequence")
        and ".branches.items[" in sequence_key
    ):
        context = "branch-local illumination sequence item"

    if len(allowed_keys) > 1:
        return (
            f"{context} must declare exactly one of "
            f"{', '.join(allowed_keys[:-1])}, or {allowed_keys[-1]}."
        )

    return f"{context} must declare {allowed_keys[0]}."


def _component_has_valid_band_list(
    component: dict[str, Any],
    field_name: str = "bands",
) -> bool:
    """Return True when a component has usable center/width band records."""
    bands = component.get(field_name)
    if not isinstance(bands, list) or not bands:
        return False

    for band in bands:
        if not isinstance(band, dict):
            return False
        if (
            _coerce_number(band.get("center_nm")) is None
            or _coerce_number(band.get("width_nm")) is None
        ):
            return False

    return True


def _structured_cube_link_errors(
    link_key: str,
    authored_component: dict[str, Any],
) -> list[str]:
    """Validate one structured filter-cube sub-component."""
    component = _component_payload(
        authored_component,
        default_name=link_key.replace("_", " ").title(),
    )
    component_type = (
        _clean_string(component.get("component_type") or component.get("type")).lower()
        or "unknown"
    )
    errors: list[str] = []

    if link_key == "dichroic":
        if component_type not in DICHROIC_TYPES:
            return [
                f"{link_key} must use a dichroic-compatible component_type; "
                f"got '{component_type}'."
            ]

        if not any(
            (
                _component_has_valid_band_list(component, "transmission_bands"),
                _component_has_valid_band_list(component, "reflection_bands"),
                _component_has_valid_band_list(component, "bands"),
                _coerce_number(component.get("cut_on_nm")) is not None,
                isinstance(component.get("cutoffs_nm"), list)
                and bool(component.get("cutoffs_nm")),
            )
        ):
            return [
                f"{link_key} must declare dichroic spectral data via cut_on_nm, "
                "cutoffs_nm, bands, transmission_bands, or reflection_bands."
            ]

        return []

    if component_type not in CUBE_FILTER_COMPONENT_TYPES:
        return [
            f"{link_key} must use a filter-compatible component_type; "
            f"got '{component_type}'."
        ]

    if component_type == "bandpass":
        if (
            _coerce_number(component.get("center_nm")) is not None
            or _coerce_number(component.get("width_nm")) is not None
        ):
            if (
                _coerce_number(component.get("center_nm")) is None
                or _coerce_number(component.get("width_nm")) is None
            ):
                errors.append(
                    f"{link_key} bandpass shape requires both center_nm and width_nm."
                )
        elif not _component_has_valid_band_list(component):
            errors.append(
                f"{link_key} bandpass shape requires center_nm/width_nm or "
                "a bands array with center_nm and width_nm."
            )

    elif component_type == "multiband_bandpass":
        if not _component_has_valid_band_list(component):
            errors.append(
                f"{link_key} multiband_bandpass shape requires a bands array "
                "with center_nm and width_nm in every band."
            )

    elif component_type == "longpass":
        if _coerce_number(component.get("cut_on_nm")) is None:
            errors.append(f"{link_key} longpass shape requires cut_on_nm.")

    elif component_type == "shortpass":
        if _coerce_number(component.get("cut_off_nm")) is None:
            errors.append(f"{link_key} shortpass shape requires cut_off_nm.")

    elif component_type == "notch":
        if (
            _coerce_number(component.get("center_nm")) is None
            or _coerce_number(component.get("width_nm")) is None
        ):
            errors.append(f"{link_key} notch shape requires both center_nm and width_nm.")

    elif component_type == "tunable":
        start = (
            _coerce_number(component.get("band_start_nm"))
            or _coerce_number(component.get("min_nm"))
        )
        end = (
            _coerce_number(component.get("band_end_nm"))
            or _coerce_number(component.get("max_nm"))
        )
        if start is None or end is None:
            errors.append(
                f"{link_key} tunable shape requires band_start_nm/band_end_nm "
                "or min_nm/max_nm."
            )

    return errors


def _validate_splitter_branch(
    branch: dict[str, Any],
    errors: list[str],
    context: str,
) -> None:
    """Validate legacy splitter branch target shape."""
    targets = (
        branch.get("targets")
        or branch.get("target_ids")
        or branch.get("terminal_ids")
        or branch.get("endpoint_ids")
    )

    if targets is not None:
        values = targets if isinstance(targets, list) else [targets]
        if not all(isinstance(item, str) and item.strip() for item in values):
            errors.append(
                f"{context}: targets must be a string or list of non-empty strings "
                "when provided."
            )


def validate_light_path_diagnostics(
    instrument_dict: dict,
) -> tuple[list[str], list[str], list[str]]:
    """Validate canonical YAML-first light-path definitions.

    Canonical schema:
    - hardware.sources[]
    - hardware.optical_path_elements[]
    - unified hardware endpoints normalized from endpoint-capable inventories
    - light_paths[] with illumination_sequence / detection_sequence

    Legacy hardware.light_path structures are normalized through the migration
    layer so validation remains centralized here.

    Returns:
        errors: hard validation errors.
        warnings: general light-path warnings.
        cube_warnings: warnings for degraded/non-authoritative filter cubes.
    """
    errors: list[str] = []
    warnings: list[str] = []
    cube_warnings: list[str] = []

    payload = instrument_dict if isinstance(instrument_dict, dict) else {}

    canonical = canonicalize_light_path_model(payload)
    sources = canonical["sources"]
    elements = canonical["optical_path_elements"]
    endpoints = canonical["endpoints"]
    raw_light_paths = canonical["light_paths"]

    # Canonical parse warnings must be hard validation errors so malformed
    # canonical routes cannot silently degrade into partial payloads.
    for route_index, route in enumerate(raw_light_paths):
        if not isinstance(route, dict):
            continue
        for parse_warning in route.get("_parse_warnings") or []:
            errors.append(parse_warning)

    for element in elements:
        if not isinstance(element, dict):
            continue

        if _clean_string(element.get("stage_role")).lower() != "cube":
            continue

        positions = (
            element.get("positions")
            if isinstance(element.get("positions"), dict)
            else {}
        )
        for position_key, cube_position in positions.items():
            if not isinstance(cube_position, dict):
                continue

            if _clean_string(cube_position.get("component_type")).lower() != "filter_cube":
                continue

            label = (
                _clean_string(cube_position.get("name"))
                or _clean_string(position_key)
                or _clean_string(element.get("name"))
                or "filter_cube"
            )
            element_label = (
                _clean_string(element.get("id"))
                or _clean_string(element.get("name"))
                or "cube"
            )

            authored_links = {
                link_key: cube_position.get(link_key)
                for link_key in CUBE_LINK_KEYS
                if isinstance(cube_position.get(link_key), dict)
            }

            if not authored_links:
                cube_warnings.append(
                    f"hardware.optical_path_elements[{element_label}]"
                    f".positions[{position_key}]: filter_cube '{label}' is flattened "
                    "and will be degraded in exact spectral simulation; author "
                    "explicit excitation_filter, dichroic, and emission_filter for "
                    "authoritative optics."
                )
                continue

            missing_links = [
                link_key
                for link_key in CUBE_LINK_KEYS
                if link_key not in authored_links
            ]
            if missing_links:
                cube_warnings.append(
                    f"hardware.optical_path_elements[{element_label}]"
                    f".positions[{position_key}]: filter_cube '{label}' is missing "
                    f"{', '.join(missing_links)} and will be degraded in exact "
                    "spectral simulation."
                )

            for link_key, authored_component in authored_links.items():
                for cube_error in _structured_cube_link_errors(
                    link_key,
                    authored_component,
                ):
                    errors.append(
                        f"hardware.optical_path_elements[{element_label}]"
                        f".positions[{position_key}].{link_key}: filter_cube "
                        f"'{label}' {cube_error}"
                    )

    hardware_inventory, _hardware_index_map = _build_hardware_inventory(
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

    raw_input_light_paths = (
        payload.get("light_paths")
        if isinstance(payload.get("light_paths"), list)
        else []
    )
    light_paths_for_validation = (
        raw_input_light_paths
        if (_has_canonical_light_path_input(payload) and raw_input_light_paths)
        else light_paths
    )

    source_ids = {entry.get("id") for entry in sources}
    element_ids = {entry.get("id") for entry in elements}
    endpoint_ids = {entry.get("id") for entry in endpoints}

    hardware = payload.get("hardware") if isinstance(payload.get("hardware"), dict) else {}
    legacy_light_path = (
        hardware.get("light_path")
        if isinstance(hardware.get("light_path"), dict)
        else {}
    )

    has_topology = bool(
        sources
        or elements
        or endpoints
        or light_paths
        or _collect_splitters(hardware, legacy_light_path)
    )
    if not has_topology:
        return [], [], []

    if not light_paths_for_validation:
        errors.append(
            "light_paths must declare at least one route with illumination_sequence "
            "and detection_sequence."
        )

    _, endpoint_collisions = _normalized_endpoint_inventory(hardware, legacy_light_path)
    errors.extend(endpoint_collisions)

    raw_elements = (
        hardware.get("optical_path_elements")
        if isinstance(hardware.get("optical_path_elements"), list)
        else []
    )
    for element_index, element in enumerate(raw_elements):
        if not isinstance(element, dict):
            continue
        if not isinstance(element.get("branches"), list):
            continue

        errors.append(
            f"hardware.optical_path_elements[{element_index}].branches: deprecated "
            "hardware-owned routing metadata is not allowed in canonical topology; "
            "move branch routing into light_paths[].detection_sequence[].branches."
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
            local_errors.append(
                f"{route_context}.{sequence_key}[{item_index}]: "
                "sequence item must be an object."
            )
            return previous_element_id, local_errors

        allowed_keys = _sequence_item_allowed_keys(
            sequence_key,
            allow_branches=allow_branches,
        )
        populated_keys = [
            key
            for key in SEQUENCE_TOPOLOGY_KEYS
            if (
                isinstance(item.get("branches"), dict)
                if key == "branches"
                else bool(_clean_identifier(item.get(key)))
            )
        ]

        if len(populated_keys) != 1 or populated_keys[0] not in allowed_keys:
            local_errors.append(
                f"{route_context}.{sequence_key}[{item_index}]: "
                f"{_sequence_item_union_message(sequence_key, allow_branches=allow_branches)}"
            )
            return previous_element_id, local_errors

        branch_block = item.get("branches")
        if isinstance(branch_block, dict):
            if not allow_branches:
                local_errors.append(
                    f"{route_context}.{sequence_key}[{item_index}]: nested branches "
                    "are not supported in branch-local sequences."
                )
                return previous_element_id, local_errors

            if not previous_element_id:
                local_errors.append(
                    f"{route_context}.{sequence_key}[{item_index}]: branches must "
                    "follow an optical_path_element_id so the route fork is explicit."
                )

            selection_mode = _clean_string(branch_block.get("selection_mode")).lower()
            if selection_mode not in {"fixed", "exclusive", "multiple"}:
                local_errors.append(
                    f"{route_context}.{sequence_key}[{item_index}]"
                    ".branches.selection_mode: must be one of fixed, exclusive, multiple."
                )

            items = branch_block.get("items")
            if not isinstance(items, list) or not items:
                local_errors.append(
                    f"{route_context}.{sequence_key}[{item_index}].branches.items: "
                    "must be a non-empty list."
                )
                return previous_element_id, local_errors

            seen_branch_ids: set[str] = set()

            for branch_index, branch in enumerate(items):
                branch_context = (
                    f"{route_context}.{sequence_key}[{item_index}]"
                    f".branches.items[{branch_index}]"
                )

                if not isinstance(branch, dict):
                    local_errors.append(f"{branch_context}: branch item must be an object.")
                    continue

                branch_id = _clean_identifier(branch.get("branch_id") or branch.get("id"))
                if not branch_id:
                    local_errors.append(f"{branch_context}.branch_id: is required.")
                elif branch_id in seen_branch_ids:
                    local_errors.append(
                        f"{branch_context}.branch_id: duplicate branch id "
                        f"`{branch_id}` within the same branch block."
                    )

                seen_branch_ids.add(branch_id)

                branch_sequence = branch.get("sequence")
                if not isinstance(branch_sequence, list) or not branch_sequence:
                    local_errors.append(
                        f"{branch_context}.sequence: must be a non-empty list."
                    )
                    continue

                branch_previous = ""
                for sequence_index, sequence_item in enumerate(branch_sequence):
                    branch_previous, branch_errors = validate_sequence_item(
                        sequence_item,
                        route_context=route_context,
                        route_id=route_id,
                        sequence_key=(
                            f"{sequence_key}[{item_index}]"
                            f".branches.items[{branch_index}].sequence"
                        ),
                        item_index=sequence_index,
                        allow_branches=False,
                        previous_element_id=branch_previous,
                    )
                    local_errors.extend(branch_errors)

            return previous_element_id, local_errors

        source_id = _clean_identifier(item.get("source_id"))
        element_id = _clean_identifier(item.get("optical_path_element_id"))
        endpoint_id = _clean_identifier(item.get("endpoint_id"))

        row: dict[str, Any] | None

        if source_id:
            if source_id not in source_ids:
                local_errors.append(
                    f"{route_context}.{sequence_key}[{item_index}]: "
                    f"unknown source_id `{source_id}`."
                )
            row = next(
                (candidate for candidate in sources if candidate.get("id") == source_id),
                None,
            )
        elif element_id:
            if element_id not in element_ids:
                local_errors.append(
                    f"{route_context}.{sequence_key}[{item_index}]: "
                    f"unknown optical_path_element_id `{element_id}`."
                )
            row = next(
                (candidate for candidate in elements if candidate.get("id") == element_id),
                None,
            )
            previous_element_id = element_id
        else:
            if endpoint_id not in endpoint_ids:
                local_errors.append(
                    f"{route_context}.{sequence_key}[{item_index}]: "
                    f"unknown endpoint_id `{endpoint_id}`."
                )
            row = next(
                (candidate for candidate in endpoints if candidate.get("id") == endpoint_id),
                None,
            )

        if row:
            modalities = _normalize_modalities(
                row.get("modalities")
                or row.get("path")
                or row.get("routes")
            )
            if modalities and route_id not in modalities:
                local_errors.append(
                    f"{route_context}.{sequence_key}[{item_index}]: "
                    f"`{source_id or element_id or endpoint_id}` is declared for "
                    f"modalities {modalities} and does not permit route `{route_id}`."
                )

            if element_id:
                raw_position_id = _clean_string(item.get("position_id"))
                if raw_position_id and not _position_id_matches_element(
                    row,
                    raw_position_id,
                ):
                    local_errors.append(
                        f"{route_context}.{sequence_key}[{item_index}]: "
                        f"unknown position_id `{raw_position_id}` for "
                        f"optical_path_element_id `{element_id}`."
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
                            f"{context}.{sequence_key}[{item_index}]"
                            f".branches.items[{branch_index}].sequence: branch does "
                            "not terminate in a clear explicit endpoint_id."
                        )

                if (
                    len(errors) == sequence_error_count
                    and not _sequence_terminates_with_explicit_endpoint(sequence)
                ):
                    warnings.append(
                        f"{context}.{sequence_key}: route does not terminate in a "
                        "clear explicit endpoint_id; add an endpoint_id or explicit "
                        "branch endpoints."
                    )

    known_target_ids = {
        endpoint.get("id")
        for endpoint in endpoints
        if endpoint.get("id")
    }
    known_target_ids.update(
        _clean_identifier(
            detector.get("id")
            or detector.get("channel_name")
            or detector.get("display_label")
            or detector.get("name")
        )
        for detector in hardware.get("detectors", [])
        if isinstance(detector, dict)
    )

    for split_idx, splitter in enumerate(_collect_splitters(hardware, legacy_light_path)):
        split_ctx = f"splitters[{split_idx}]"
        for key in ("path_1", "path_2"):
            if not isinstance(splitter.get(key), dict):
                continue

            _validate_splitter_branch(splitter[key], errors, f"{split_ctx}.{key}")

            for target in _as_list(
                splitter[key].get("targets")
                or splitter[key].get("target_ids")
                or splitter[key].get("endpoint_ids")
                or splitter[key].get("terminal_ids")
            ):
                normalized = _clean_identifier(target)
                if normalized and normalized not in known_target_ids:
                    errors.append(
                        f"{split_ctx}.{key}: target `{normalized}` does not match "
                        "any declared detector or endpoint."
                    )

    seen_element_ids: set[str] = set()
    for element_index, element in enumerate(elements):
        context = f"hardware.optical_path_elements[{element_index}]"
        element_id = _clean_identifier(element.get("id"))

        if not element_id:
            errors.append(f"{context}: id is required.")
            continue

        if element_id in seen_element_ids:
            errors.append(
                f"{context}: duplicate optical_path_element id `{element_id}`."
            )
        seen_element_ids.add(element_id)

        selection_mode = _clean_string(element.get("selection_mode")).lower()
        if selection_mode and selection_mode not in {"fixed", "exclusive", "multiple"}:
            errors.append(
                f"{context}: selection_mode must be one of fixed, exclusive, multiple."
            )

    return errors, warnings, cube_warnings


__all__ = [
    "validate_light_path",
    "validate_light_path_warnings",
    "validate_filter_cube_warnings",
    "validate_light_path_diagnostics",
    "_sequence_terminates_with_explicit_endpoint",
    "_sequence_item_allowed_keys",
    "_sequence_item_union_message",
    "_component_has_valid_band_list",
    "_structured_cube_link_errors",
    "_validate_splitter_branch",
]
