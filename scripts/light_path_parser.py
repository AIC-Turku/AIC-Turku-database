"""Utilities for validating and serializing microscope light-path definitions."""

from __future__ import annotations

import json
from itertools import product
from typing import Any


DISCRETE_MECHANISM_TYPES = {"filter_wheel", "slider", "turret"}
CONTINUOUS_MECHANISM_TYPES = {"tunable", "fixed", "spectral_slider"}
DICHROIC_TYPES = {"dichroic", "multiband_dichroic", "polychroic"}
NO_WAVELENGTH_TYPES = {"empty", "mirror", "block"}
CUBE_LINK_KEYS = ("excitation_filter", "dichroic", "emission_filter")


def _is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _iter_mechanisms(light_path: dict[str, Any], stage_key: str) -> list[dict[str, Any]]:
    raw_mechanisms = light_path.get(stage_key, [])
    if isinstance(raw_mechanisms, list):
        return [entry for entry in raw_mechanisms if isinstance(entry, dict)]
    if isinstance(raw_mechanisms, dict):
        return [entry for _, entry in sorted(raw_mechanisms.items(), key=lambda item: str(item[0])) if isinstance(entry, dict)]
    return []


def _require_positive_number(component: dict[str, Any], field: str, errors: list[str], context: str) -> None:
    if not _is_positive_number(component.get(field)):
        errors.append(f"{context}: component_type requires positive `{field}`.")


def _validate_optional_path(item: dict[str, Any], errors: list[str], context: str) -> None:
    path = item.get("path")
    if path is not None and (not isinstance(path, str) or not path.strip()):
        errors.append(f"{context}: `path` must be a non-empty string when provided.")


def _validate_spectral_array(mechanism: dict[str, Any], errors: list[str], context: str) -> None:
    min_nm = mechanism.get("min_nm")
    if not _is_positive_number(min_nm):
        min_nm = mechanism.get("band_min_nm")
    if not _is_positive_number(min_nm):
        errors.append(f"{context}: spectral_array requires positive `min_nm` (or `band_min_nm`).")

    max_nm = mechanism.get("max_nm")
    if not _is_positive_number(max_nm):
        max_nm = mechanism.get("band_max_nm")
    if not _is_positive_number(max_nm):
        errors.append(f"{context}: spectral_array requires positive `max_nm` (or `band_max_nm`).")

    bands = mechanism.get("bands")
    if not _is_positive_number(bands):
        bands = mechanism.get("max_bands")
    if not _is_positive_number(bands):
        errors.append(f"{context}: spectral_array requires positive `bands` (or `max_bands`).")

    if _is_positive_number(min_nm) and _is_positive_number(max_nm) and min_nm >= max_nm:
        errors.append(f"{context}: spectral_array requires `max_nm` to be greater than `min_nm`.")


def _validate_component(component: dict[str, Any], errors: list[str], context: str) -> None:
    component_type = component.get("component_type")
    if not isinstance(component_type, str) or not component_type:
        errors.append(f"{context}: missing or invalid `component_type`.")
        return

    if component_type in {"bandpass", "notch"}:
        _require_positive_number(component, "center_nm", errors, context)
        _require_positive_number(component, "width_nm", errors, context)
    elif component_type == "longpass":
        _require_positive_number(component, "cut_on_nm", errors, context)
    elif component_type == "shortpass":
        _require_positive_number(component, "cut_off_nm", errors, context)
    elif component_type in DICHROIC_TYPES:
        cutoffs = component.get("cutoffs_nm")
        if not isinstance(cutoffs, list) or not cutoffs or not all(_is_positive_number(item) for item in cutoffs):
            errors.append(f"{context}: component_type requires `cutoffs_nm` as a list of positive numbers.")
    elif component_type in NO_WAVELENGTH_TYPES:
        return


def validate_light_path(instrument_dict: dict) -> list[str]:
    """Validate light-path mechanisms and optical components in an instrument record."""
    errors: list[str] = []
    light_path = instrument_dict.get("hardware", {}).get("light_path", {})
    if not isinstance(light_path, dict):
        return ["hardware.light_path must be a mapping/object."]

    for src_index, source in enumerate(instrument_dict.get("hardware", {}).get("light_sources", [])):
        if isinstance(source, dict):
            _validate_optional_path(source, errors, f"hardware.light_sources[{src_index}]")

    for stage in ("excitation_mechanisms", "dichroic_mechanisms", "emission_mechanisms", "cube_mechanisms"):
        for mech_index, mechanism in enumerate(_iter_mechanisms(light_path, stage)):
            mech_type = mechanism.get("type")
            mech_ctx = f"{stage}[{mech_index}]"
            _validate_optional_path(mechanism, errors, mech_ctx)

            if mech_type == "spectral_array":
                _validate_spectral_array(mechanism, errors, mech_ctx)

            if mech_type in DISCRETE_MECHANISM_TYPES:
                slots = mechanism.get("slots")
                if not isinstance(slots, int) or isinstance(slots, bool):
                    errors.append(f"{mech_ctx}: discrete mechanism type `{mech_type}` requires integer `slots`.")
                    continue
            elif mech_type in CONTINUOUS_MECHANISM_TYPES:
                slots = None
            else:
                slots = mechanism.get("slots") if isinstance(mechanism.get("slots"), int) else None

            positions = mechanism.get("positions", {})
            if not isinstance(positions, dict):
                errors.append(f"{mech_ctx}: `positions` must be a mapping/object.")
                continue

            for position_key, component in positions.items():
                pos_ctx = f"{mech_ctx}.positions[{position_key!r}]"
                if not isinstance(position_key, int) or isinstance(position_key, bool):
                    errors.append(f"{pos_ctx}: position key must be an integer.")
                    continue
                if slots is not None and (position_key < 1 or position_key > slots):
                    errors.append(f"{pos_ctx}: position key must be between 1 and {slots}.")

                if not isinstance(component, dict):
                    errors.append(f"{pos_ctx}: position value must be a mapping/object.")
                    continue

                _validate_optional_path(component, errors, pos_ctx)

                if stage == "cube_mechanisms":
                    for link_key in CUBE_LINK_KEYS:
                        linked_component = component.get(link_key)
                        link_ctx = f"{pos_ctx}.{link_key}"
                        if not isinstance(linked_component, dict):
                            errors.append(f"{link_ctx}: missing or invalid linked component mapping/object.")
                            continue
                        _validate_optional_path(linked_component, errors, link_ctx)
                        _validate_component(linked_component, errors, link_ctx)
                else:
                    _validate_component(component, errors, pos_ctx)

    for split_idx, splitter in enumerate(light_path.get("splitters", [])):
        if not isinstance(splitter, dict):
            continue

        if isinstance(splitter.get("dichroic"), dict):
            _validate_component(splitter["dichroic"], errors, f"splitters[{split_idx}].dichroic")

        if isinstance(splitter.get("path_1", {}).get("emission_filter"), dict):
            _validate_component(
                splitter["path_1"]["emission_filter"],
                errors,
                f"splitters[{split_idx}].path_1.emission_filter",
            )

        if isinstance(splitter.get("path_2", {}).get("emission_filter"), dict):
            _validate_component(
                splitter["path_2"]["emission_filter"],
                errors,
                f"splitters[{split_idx}].path_2.emission_filter",
            )

    return errors


def _format_numeric(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


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
        return str(component_type).title()
    if component_type == "longpass":
        cut_on = component.get("cut_on_nm")
        return f"LP {_format_numeric(cut_on)}" if _is_positive_number(cut_on) else "Longpass"
    if component_type == "shortpass":
        cut_off = component.get("cut_off_nm")
        return f"SP {_format_numeric(cut_off)}" if _is_positive_number(cut_off) else "Shortpass"
    if component_type in DICHROIC_TYPES:
        cutoffs = component.get("cutoffs_nm")
        if isinstance(cutoffs, list) and cutoffs:
            rendered = ", ".join(_format_numeric(value) for value in cutoffs)
            return f"Dichroic [{rendered}]"
        return "Dichroic"
    if component_type in NO_WAVELENGTH_TYPES:
        return str(component_type).title()

    return str(component_type).replace("_", " ").title()


def _build_details(component: dict[str, Any]) -> str:
    manufacturer = component.get("manufacturer")
    product_code = component.get("product_code")
    parts = [str(part).strip() for part in (manufacturer, product_code) if isinstance(part, str) and part.strip()]
    return " ".join(parts)


def _mechanism_payload(stage_prefix: str, index: int, mechanism: dict[str, Any]) -> dict[str, Any]:
    raw_positions = mechanism.get("positions", {})
    positions: list[dict[str, Any]] = []

    if isinstance(raw_positions, dict):
        for slot in sorted(raw_positions):
            component = raw_positions.get(slot)
            if not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(component, dict):
                continue
            component_type = str(component.get("component_type", "unknown"))
            positions.append(
                {
                    "slot": slot,
                    "type": component_type,
                    "label": _build_label(component),
                    "details": _build_details(component),
                    **({"path": component.get("path")} if isinstance(component.get("path"), str) else {}),
                }
            )

    mechanism_payload = {
        "id": f"{stage_prefix}_mech_{index}",
        "name": mechanism.get("name") or f"{stage_prefix.replace('_', ' ').title()} {index + 1}",
        "type": mechanism.get("type", "unknown"),
        "positions": positions,
    }
    if isinstance(mechanism.get("path"), str):
        mechanism_payload["path"] = mechanism["path"]

    if mechanism.get("type") == "spectral_array":
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


def _cube_mechanism_payload(index: int, mechanism: dict[str, Any]) -> dict[str, Any]:
    raw_positions = mechanism.get("positions", {})
    positions: list[dict[str, Any]] = []
    if isinstance(raw_positions, dict):
        for slot in sorted(raw_positions):
            cube_position = raw_positions.get(slot)
            if not isinstance(slot, int) or isinstance(slot, bool) or not isinstance(cube_position, dict):
                continue

            linked_components: dict[str, dict[str, Any]] = {}
            for link_key in CUBE_LINK_KEYS:
                component = cube_position.get(link_key)
                if not isinstance(component, dict):
                    continue
                component_payload: dict[str, Any] = {
                    **component,
                    "type": str(component.get("component_type", "unknown")),
                    "label": _build_label(component),
                    "details": _build_details(component),
                }
                if isinstance(component.get("path"), str):
                    component_payload["path"] = component["path"]
                linked_components[link_key] = component_payload

            position_payload: dict[str, Any] = {
                "slot": slot,
                "type": "cube",
                "label": cube_position.get("name") or f"Cube {slot}",
                "details": _build_details(cube_position),
                "linked_components": linked_components,
            }
            if isinstance(cube_position.get("path"), str):
                position_payload["path"] = cube_position["path"]
            positions.append(position_payload)

    mechanism_payload: dict[str, Any] = {
        "id": f"cube_mech_{index}",
        "name": mechanism.get("name") or f"Cube {index + 1}",
        "type": mechanism.get("type", "unknown"),
        "positions": positions,
    }
    if isinstance(mechanism.get("path"), str):
        mechanism_payload["path"] = mechanism["path"]
    return mechanism_payload


def _route_tags(selection: dict[str, Any]) -> set[str]:
    tags: set[str] = set()
    path = selection.get("path")
    if isinstance(path, str) and path.strip():
        tags.add(path.strip().lower())

    linked_components = selection.get("linked_components")
    if isinstance(linked_components, dict):
        for linked in linked_components.values():
            if isinstance(linked, dict):
                linked_path = linked.get("path")
                if isinstance(linked_path, str) and linked_path.strip():
                    tags.add(linked_path.strip().lower())
    return tags


def _routes_compatible(route_tags: set[str]) -> bool:
    constrained = {tag for tag in route_tags if tag not in {"all", "shared"}}
    return len(constrained) <= 1


def calculate_valid_paths(payload: dict) -> list[dict]:
    """Calculate all mechanically valid light paths from serialized stage data."""
    stages = payload.get("stages", {})
    if not isinstance(stages, dict):
        return []

    discrete_choices: list[tuple[str, str, list[dict[str, Any]]]] = []
    for stage_name in ("excitation", "dichroic", "emission", "cube"):
        mechanisms = stages.get(stage_name, [])
        if not isinstance(mechanisms, list):
            continue

        for mechanism in mechanisms:
            if not isinstance(mechanism, dict):
                continue
            mechanism_id = mechanism.get("id")
            positions = mechanism.get("positions", [])
            if isinstance(mechanism_id, str) and isinstance(positions, list) and positions:
                filtered_positions = [pos for pos in positions if isinstance(pos, dict) and isinstance(pos.get("slot"), int)]
                if filtered_positions:
                    discrete_choices.append((stage_name, mechanism_id, filtered_positions))

    light_source_groups = payload.get("light_sources", [])
    if isinstance(light_source_groups, list):
        for source_group in light_source_groups:
            if not isinstance(source_group, dict):
                continue
            source_group_id = source_group.get("id")
            source_positions = source_group.get("positions")
            if not isinstance(source_group_id, str) or not isinstance(source_positions, dict):
                continue
            normalized_positions = []
            for slot, source in source_positions.items():
                if isinstance(slot, int) and not isinstance(slot, bool) and isinstance(source, dict):
                    normalized_positions.append({"slot": slot, **source})
            if normalized_positions:
                discrete_choices.append(("light_sources", source_group_id, normalized_positions))

    if not discrete_choices:
        return []

    valid_paths: list[dict[str, int]] = []
    for combination in product(*(choices for _, _, choices in discrete_choices)):
        if any(str(selection.get("type")) == "block" for selection in combination):
            continue

        light_source_routes: set[str] = set()
        for (stage_name, _, _), selection in zip(discrete_choices, combination):
            if stage_name == "light_sources":
                light_source_routes.update(_route_tags(selection))
        constrained_sources = {tag for tag in light_source_routes if tag not in {"all", "shared"}}
        bypass_excitation_for_tirf = constrained_sources == {"tirf"}

        combined_routes: set[str] = set()
        for (stage_name, _, _), selection in zip(discrete_choices, combination):
            if bypass_excitation_for_tirf and stage_name == "excitation":
                continue
            combined_routes.update(_route_tags(selection))

        if not _routes_compatible(combined_routes):
            continue

        valid_paths.append({
            mech_id: int(selection["slot"])
            for (_, mech_id, _), selection in zip(discrete_choices, combination)
        })

    return valid_paths


def generate_virtual_microscope_payload(instrument_dict: dict) -> dict:
    """Build a frontend-friendly virtual microscope payload from instrument light-path data."""
    hardware = instrument_dict.get("hardware", {})
    light_path = hardware.get("light_path", {})
    if not isinstance(light_path, dict):
        light_path = {}

    stage_mappings = {
        "excitation": "excitation_mechanisms",
        "dichroic": "dichroic_mechanisms",
        "emission": "emission_mechanisms",
        "cube": "cube_mechanisms",
    }
    prefix_mappings = {"excitation": "exc", "dichroic": "dichroic", "emission": "em", "cube": "cube"}

    payload: dict[str, Any] = {
        "light_sources": [],
        "detectors": [],
        "stages": {"excitation": [], "dichroic": [], "emission": [], "cube": []},
        "splitters": [],
        "valid_paths": [],
    }

    raw_sources = hardware.get("light_sources", [])
    if isinstance(raw_sources, list) and raw_sources:
        positions = {}
        for idx, src in enumerate(raw_sources):
            if not isinstance(src, dict):
                continue
            wl = src.get("wavelength_nm")
            kind = src.get("kind", "light_source")
            positions[idx + 1] = {
                "component_type": "laser" if kind in ["laser", "white_light_laser"] else "light_source",
                "name": f"{src.get('manufacturer', '')} {src.get('model', '')} {wl or ''}".strip(),
                "wavelength_nm": wl,
                "manufacturer": src.get("manufacturer"),
                "product_code": src.get("model"),
                **({"path": src.get("path")} if isinstance(src.get("path"), str) else {}),
            }
        if positions:
            payload["light_sources"].append(
                {
                    "id": "light_sources_0",
                    "name": "Light Sources / Lasers",
                    "type": "light_source_group",
                    "positions": positions,
                }
            )

    raw_detectors = hardware.get("detectors", [])
    if isinstance(raw_detectors, list) and raw_detectors:
        positions = {}
        for idx, det in enumerate(raw_detectors):
            if not isinstance(det, dict):
                continue
            positions[idx + 1] = {
                "component_type": "detector",
                "name": f"{det.get('manufacturer', '')} {det.get('model', '')}".strip(),
                "manufacturer": det.get("manufacturer"),
                "product_code": det.get("model"),
            }
        if positions:
            payload["detectors"].append(
                {
                    "id": "detectors_0",
                    "name": "Detectors / Cameras",
                    "type": "detector_group",
                    "positions": positions,
                }
            )

    for stage_name, source_key in stage_mappings.items():
        mechanisms = _iter_mechanisms(light_path, source_key)
        if stage_name == "cube":
            payload["stages"][stage_name] = [_cube_mechanism_payload(index, mechanism) for index, mechanism in enumerate(mechanisms)]
        else:
            payload["stages"][stage_name] = [
                _mechanism_payload(prefix_mappings[stage_name], index, mechanism)
                for index, mechanism in enumerate(mechanisms)
            ]

    raw_splitters = light_path.get("splitters", [])
    if isinstance(raw_splitters, list):
        for index, splitter in enumerate(raw_splitters):
            if not isinstance(splitter, dict):
                continue

            dichroic_component = splitter.get("dichroic", {}).copy() if isinstance(splitter.get("dichroic"), dict) else {}
            if "cut_on_nm" in dichroic_component and "cutoffs_nm" not in dichroic_component:
                dichroic_component["cutoffs_nm"] = [dichroic_component["cut_on_nm"]]

            path_1 = splitter.get("path_1") if isinstance(splitter.get("path_1"), dict) else {}
            path_2 = splitter.get("path_2") if isinstance(splitter.get("path_2"), dict) else {}
            path_1_filter = path_1.get("emission_filter") if isinstance(path_1.get("emission_filter"), dict) else {}
            path_2_filter = path_2.get("emission_filter") if isinstance(path_2.get("emission_filter"), dict) else {}

            payload["splitters"].append(
                {
                    "name": splitter.get("name", f"Splitter {index + 1}"),
                    "dichroic": {
                        "name": "Splitter Dichroic",
                        "positions": {1: dichroic_component} if dichroic_component else {},
                    },
                    "path1": {
                        "name": "Path 1 (Transmitted)",
                        "positions": {1: path_1_filter} if path_1_filter else {},
                    },
                    "path2": {
                        "name": "Path 2 (Reflected)",
                        "positions": {1: path_2_filter} if path_2_filter else {},
                    },
                }
            )

    payload["valid_paths"] = calculate_valid_paths(payload)
    return json.loads(json.dumps(payload))
