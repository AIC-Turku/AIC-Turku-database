"""Utilities for validating and serializing microscope light-path definitions."""

from __future__ import annotations

import json
from itertools import product
from typing import Any


DISCRETE_MECHANISM_TYPES = {"filter_wheel", "slider", "turret"}
CONTINUOUS_MECHANISM_TYPES = {"tunable", "fixed", "spectral_slider"}
DICHROIC_TYPES = {"dichroic", "multiband_dichroic", "polychroic"}
NO_WAVELENGTH_TYPES = {"empty", "mirror", "block"}


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

    for stage in ("excitation_mechanisms", "dichroic_mechanisms", "emission_mechanisms"):
        for mech_index, mechanism in enumerate(_iter_mechanisms(light_path, stage)):
            mech_type = mechanism.get("type")
            mech_ctx = f"{stage}[{mech_index}]"

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

                _validate_component(component, errors, pos_ctx)

    return errors


def _format_numeric(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _build_label(component: dict[str, Any]) -> str:
    component_type = component.get("component_type", "unknown")

    if component_type in {"bandpass", "notch"}:
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
                }
            )

    return {
        "id": f"{stage_prefix}_mech_{index}",
        "name": mechanism.get("name") or f"{stage_prefix.replace('_', ' ').title()} {index + 1}",
        "type": mechanism.get("type", "unknown"),
        "positions": positions,
    }


def calculate_valid_paths(payload: dict) -> list[dict]:
    """Calculate all mechanically valid light paths from serialized stage data."""
    stages = payload.get("stages", {})
    if not isinstance(stages, dict):
        return []

    discrete_choices: list[tuple[str, list[dict[str, Any]]]] = []
    for stage_name in ("excitation", "dichroic", "emission"):
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
                    discrete_choices.append((mechanism_id, filtered_positions))

    if not discrete_choices:
        return []

    valid_paths: list[dict[str, int]] = []
    for combination in product(*(choices for _, choices in discrete_choices)):
        if any(str(selection.get("type")) == "block" for selection in combination):
            continue

        valid_paths.append({
            mech_id: int(selection["slot"])
            for (mech_id, _), selection in zip(discrete_choices, combination)
        })

    return valid_paths


def generate_virtual_microscope_payload(instrument_dict: dict) -> dict:
    """Build a frontend-friendly virtual microscope payload from instrument light-path data."""
    light_path = instrument_dict.get("hardware", {}).get("light_path", {})
    if not isinstance(light_path, dict):
        payload = {"stages": {"excitation": [], "dichroic": [], "emission": []}, "valid_paths": []}
        return json.loads(json.dumps(payload))

    stage_mappings = {
        "excitation": "excitation_mechanisms",
        "dichroic": "dichroic_mechanisms",
        "emission": "emission_mechanisms",
    }
    prefix_mappings = {"excitation": "exc", "dichroic": "dichroic", "emission": "em"}

    payload: dict[str, Any] = {"stages": {"excitation": [], "dichroic": [], "emission": []}, "valid_paths": []}

    for stage_name, source_key in stage_mappings.items():
        mechanisms = _iter_mechanisms(light_path, source_key)
        payload["stages"][stage_name] = [
            _mechanism_payload(prefix_mappings[stage_name], index, mechanism)
            for index, mechanism in enumerate(mechanisms)
        ]

    payload["valid_paths"] = calculate_valid_paths(payload)
    return json.loads(json.dumps(payload))
