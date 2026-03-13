"""Utilities for validating and serializing microscope light-path definitions.

The virtual microscope consumes a validated, normalized hardware payload generated from
instrument YAML. This module keeps that payload browser-friendly while preserving enough
metadata for route-aware spectral simulation.
"""

from __future__ import annotations

import json
import re
from itertools import product
from typing import Any


DISCRETE_MECHANISM_TYPES = {"filter_wheel", "slider", "turret"}
CONTINUOUS_MECHANISM_TYPES = {"tunable", "fixed", "spectral_slider"}
DICHROIC_TYPES = {"dichroic", "multiband_dichroic", "polychroic"}
MULTIBAND_FILTER_TYPES = {"multiband_bandpass"}
NO_WAVELENGTH_TYPES = {"empty", "mirror", "block", "passthrough", "neutral_density"}
ROUTE_TAGS = {"epi", "tirf", "confocal", "multiphoton", "transmitted", "shared", "all"}
ROUTE_LABELS = {
    "confocal": "Confocal",
    "epi": "Epi-fluorescence",
    "tirf": "TIRF",
    "multiphoton": "Multiphoton",
    "transmitted": "Transmitted light",
}
ROUTE_SORT_ORDER = ("confocal", "epi", "tirf", "multiphoton", "transmitted")
CUBE_LINK_KEYS = ("excitation_filter", "dichroic", "emission_filter")
CAMERA_DETECTOR_KINDS = {"camera", "scmos", "cmos", "ccd", "emccd"}
POINT_DETECTOR_KINDS = {"pmt", "gaasp_pmt", "hyd", "apd", "spad"}
TUNABLE_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|to|–)\s*(\d+(?:\.\d+)?)\s*nm", re.IGNORECASE)
POWER_VALUE_RE = re.compile(r"(\d+(?:\.\d+)?)")
TRANSMITTED_ROLE_HINTS = (
    'transmitted',
    'brightfield',
    'darkfield',
    'phase contrast',
    'phase-contrast',
    'dic',
    'diascopic',
    'dia',
)


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


def _require_positive_number(component: dict[str, Any], field: str, errors: list[str], context: str) -> None:
    if not _is_positive_number(component.get(field)):
        errors.append(f"{context}: component_type requires positive `{field}`.")


def _validate_optional_path(item: dict[str, Any], errors: list[str], context: str) -> None:
    path = item.get("path")
    if path is not None and (not isinstance(path, str) or not path.strip()):
        errors.append(f"{context}: `path` must be a non-empty string when provided.")


def _validate_band_list(component: dict[str, Any], errors: list[str], context: str) -> None:
    bands = component.get("bands")
    if not isinstance(bands, list) or not bands:
        errors.append(f"{context}: component_type requires `bands` as a non-empty list.")
        return

    for band_index, band in enumerate(bands):
        if not isinstance(band, dict):
            errors.append(f"{context}.bands[{band_index}]: band entry must be an object.")
            continue
        if not _is_positive_number(band.get("center_nm")):
            errors.append(f"{context}.bands[{band_index}]: requires positive `center_nm`.")
        if not _is_positive_number(band.get("width_nm")):
            errors.append(f"{context}.bands[{band_index}]: requires positive `width_nm`.")


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
    elif component_type in MULTIBAND_FILTER_TYPES:
        _validate_band_list(component, errors, context)
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
    hardware = instrument_dict.get("hardware", {})
    light_path = hardware.get("light_path", {})
    if not isinstance(light_path, dict):
        return ["hardware.light_path must be a mapping/object."]

    for src_index, source in enumerate(hardware.get("light_sources", [])):
        if isinstance(source, dict):
            _validate_optional_path(source, errors, f"hardware.light_sources[{src_index}]")

    for det_index, detector in enumerate(hardware.get("detectors", [])):
        if isinstance(detector, dict):
            _validate_optional_path(detector, errors, f"hardware.detectors[{det_index}]")

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
                normalized_position_key = _coerce_slot_key(position_key)
                if normalized_position_key is None:
                    errors.append(f"{pos_ctx}: position key must be an integer.")
                    continue
                if slots is not None and (normalized_position_key < 1 or normalized_position_key > slots):
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

    for split_idx, splitter in enumerate(_collect_splitters(hardware, light_path)):
        split_ctx = f"splitters[{split_idx}]"
        _validate_optional_path(splitter, errors, split_ctx)

        if isinstance(splitter.get("dichroic"), dict):
            _validate_component(splitter["dichroic"], errors, f"{split_ctx}.dichroic")

        if isinstance(splitter.get("path_1", {}).get("emission_filter"), dict):
            _validate_component(
                splitter["path_1"]["emission_filter"],
                errors,
                f"{split_ctx}.path_1.emission_filter",
            )

        if isinstance(splitter.get("path_2", {}).get("emission_filter"), dict):
            _validate_component(
                splitter["path_2"]["emission_filter"],
                errors,
                f"{split_ctx}.path_2.emission_filter",
            )

    return errors


# ---------------------------------------------------------------------------
# Payload serialization helpers
# ---------------------------------------------------------------------------


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



def _render_kind(component: dict[str, Any]) -> str:
    component_type = str(component.get("component_type", "unknown")).lower()
    if component_type in {"laser", "light_source", "led"}:
        return "source"
    if component_type in {"detector"}:
        return "detector"
    if component_type in {"bandpass", "notch", "multiband_bandpass"}:
        return "band"
    if component_type in {"longpass"}:
        return "longpass"
    if component_type in {"tunable"}:
        return "tunable"
    if component_type in NO_WAVELENGTH_TYPES:
        return "empty"
    if component_type in DICHROIC_TYPES:
        return "dichroic"
    return "other"



def _build_details(component: dict[str, Any]) -> str:
    manufacturer = component.get("manufacturer")
    product_code = component.get("product_code")
    notes = component.get("notes")
    parts = [
        str(part).strip()
        for part in (manufacturer, product_code, notes)
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
    return payload



def _light_source_display_label(source: dict[str, Any]) -> str:
    kind = _clean_string(source.get("kind") or source.get("type") or "source").replace("_", " ")
    manufacturer = _clean_string(source.get("manufacturer"))
    model = _clean_string(source.get("model") or source.get("name"))
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
    return " ".join(part for part in [prefix, kind, manufacturer, model] if part).strip() or model or kind.title() or "Light Source"



def infer_light_source_role(source: dict[str, Any]) -> str:
    explicit = _clean_string(source.get("role")).lower()
    if explicit:
        return explicit

    routes = _normalize_routes(source.get("path") or source.get("paths") or source.get("route") or source.get("routes"))
    if "transmitted" in routes:
        return "transmitted_illumination"

    return "excitation"



def _source_role(source: dict[str, Any]) -> str:
    return infer_light_source_role(source)



def _detector_class(kind: str) -> str:
    normalized = kind.lower().strip()
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
        "name": display_label,
        "display_label": display_label,
        "manufacturer": source.get("manufacturer"),
        "product_code": source.get("model") or source.get("name"),
        "model": source.get("model") or source.get("name"),
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



def _detector_position(slot: int, detector: dict[str, Any]) -> dict[str, Any]:
    kind = _clean_string(detector.get("kind") or detector.get("type") or "detector").lower() or "detector"
    manufacturer = _clean_string(detector.get("manufacturer") or detector.get("name"))
    model = _clean_string(detector.get("model"))
    channel_name = _clean_string(detector.get("channel_name") or detector.get("channel") or detector.get("name")) or f"Detector {slot}"
    display_label = " ".join(part for part in [channel_name if channel_name not in {manufacturer, model} else "", manufacturer, model] if part).strip() or channel_name or manufacturer or model or f"Detector {slot}"
    position = {
        "slot": 1,
        "component_type": "detector",
        "render_kind": "detector",
        "type": "detector",
        "kind": kind,
        "detector_class": _detector_class(kind),
        "name": display_label,
        "display_label": display_label,
        "channel_name": channel_name,
        "manufacturer": detector.get("manufacturer") or detector.get("name"),
        "product_code": detector.get("model"),
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
    }
    routes = _normalize_routes(detector.get("path") or detector.get("paths") or detector.get("route") or detector.get("routes"))
    if routes:
        position["routes"] = routes
        position["path"] = routes[0]
    _normalize_component_numeric_fields(position, position)
    return position



def _mechanism_payload(stage_prefix: str, index: int, mechanism: dict[str, Any]) -> dict[str, Any]:
    raw_positions = mechanism.get("positions", {})
    positions: list[dict[str, Any]] = []

    if isinstance(raw_positions, dict):
        normalized_positions = sorted(
            (
                (_coerce_slot_key(slot), component)
                for slot, component in raw_positions.items()
            ),
            key=lambda item: (item[0] is None, item[0]),
        )
        for slot, component in normalized_positions:
            if slot is None or not isinstance(component, dict):
                continue
            component_payload = _component_payload(component)
            component_payload["slot"] = slot
            component_payload["display_label"] = f"Slot {slot}: {component_payload.get('label')}"
            positions.append(component_payload)

    mechanism_payload = {
        "id": f"{stage_prefix}_mech_{index}",
        "name": mechanism.get("name") or f"{stage_prefix.replace('_', ' ').title()} {index + 1}",
        "display_label": mechanism.get("name") or f"{stage_prefix.replace('_', ' ').title()} {index + 1}",
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



def _cube_mechanism_payload(index: int, mechanism: dict[str, Any]) -> dict[str, Any]:
    raw_positions = mechanism.get("positions", {})
    positions: list[dict[str, Any]] = []
    if isinstance(raw_positions, dict):
        normalized_positions = sorted(
            (
                (_coerce_slot_key(slot), cube_position)
                for slot, cube_position in raw_positions.items()
            ),
            key=lambda item: (item[0] is None, item[0]),
        )
        for slot, cube_position in normalized_positions:
            if slot is None or not isinstance(cube_position, dict):
                continue

            linked_components: dict[str, dict[str, Any]] = {}
            for link_key in CUBE_LINK_KEYS:
                component = cube_position.get(link_key)
                if not isinstance(component, dict):
                    continue
                linked_components[link_key] = _component_payload(component, default_name=link_key.replace("_", " ").title())

            position_payload: dict[str, Any] = {
                "slot": slot,
                "type": "cube",
                "label": cube_position.get("name") or f"Cube {slot}",
                "display_label": cube_position.get("name") or f"Cube {slot}",
                "details": _build_details(cube_position),
                "linked_components": linked_components,
                # Backward-compatible direct aliases used by the browser runtime.
                "excitation_filter": linked_components.get("excitation_filter"),
                "dichroic": linked_components.get("dichroic"),
                "emission_filter": linked_components.get("emission_filter"),
            }
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
            "label": ROUTE_LABELS.get(route_id, route_id.replace("_", " ").title()),
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
    for stage_name in ("excitation", "dichroic", "emission", "cube"):
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



def _splitter_payload(index: int, splitter: dict[str, Any]) -> dict[str, Any]:
    name = splitter.get("name", f"Splitter {index + 1}")
    dichroic_component = splitter.get("dichroic", {}).copy() if isinstance(splitter.get("dichroic"), dict) else {}
    if "cut_on_nm" in dichroic_component and "cutoffs_nm" not in dichroic_component:
        dichroic_component["cutoffs_nm"] = [dichroic_component["cut_on_nm"]]

    path_1 = splitter.get("path_1") if isinstance(splitter.get("path_1"), dict) else {}
    path_2 = splitter.get("path_2") if isinstance(splitter.get("path_2"), dict) else {}
    path_1_filter = path_1.get("emission_filter") if isinstance(path_1.get("emission_filter"), dict) else {"component_type": "mirror", "notes": "No branch filter declared."}
    path_2_filter = path_2.get("emission_filter") if isinstance(path_2.get("emission_filter"), dict) else {"component_type": "mirror", "notes": "No branch filter declared."}

    dichroic_pos = _component_payload(dichroic_component, default_name="Splitter Dichroic") if dichroic_component else {}
    path1_pos = _component_payload(path_1_filter, default_name="Path 1 Filter", branch_mode="transmitted")
    path2_pos = _component_payload(path_2_filter, default_name="Path 2 Filter", branch_mode="reflected")

    display_parts = [
        f"Di: {dichroic_pos.get('label')}" if dichroic_pos else "",
        f"P1: {path1_pos.get('label')}" if path1_pos else "",
        f"P2: {path2_pos.get('label')}" if path2_pos else "",
    ]
    routes = _normalize_routes(splitter.get("path") or splitter.get("paths") or splitter.get("route") or splitter.get("routes"))
    branches = [
        {
            "id": f"splitter_{index}_path1",
            "label": _clean_string(path_1.get("name")) or "Path 1",
            "mode": "transmitted",
            "component": path1_pos,
        },
        {
            "id": f"splitter_{index}_path2",
            "label": _clean_string(path_2.get("name")) or "Path 2",
            "mode": "reflected",
            "component": path2_pos,
        },
    ]
    if routes:
        for branch in branches:
            branch["routes"] = list(routes)
            branch["path"] = routes[0]

    splitter_payload = {
        "id": f"splitter_{index}",
        "name": name,
        "display_label": " | ".join(part for part in display_parts if part),
        "dichroic": {
            "name": "Splitter Dichroic",
            "positions": {1: dichroic_pos} if dichroic_pos else {},
        },
        "path1": {
            "name": _clean_string(path_1.get("name")) or "Path 1 (Transmitted)",
            "positions": {1: path1_pos},
        },
        "path2": {
            "name": _clean_string(path_2.get("name")) or "Path 2 (Reflected)",
            "positions": {1: path2_pos},
        },
        "branches": branches,
        "control_kind": "dropdown",
        "control_label": name,
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
                "label": splitter_payload["display_label"] or name,
                "dichroic": splitter_payload["dichroic"],
                "path1": splitter_payload["path1"],
                "path2": splitter_payload["path2"],
                "branches": branches,
            },
        }
    ]
    return splitter_payload



def generate_virtual_microscope_payload(instrument_dict: dict) -> dict:
    """Build a frontend-friendly virtual microscope payload from normalized hardware data."""
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
        "metadata": {
            "wavelength_grid": {"min_nm": 350, "max_nm": 1700, "step_nm": 2},
        },
        "light_sources": [],
        "detectors": [],
        "stages": {"excitation": [], "dichroic": [], "emission": [], "cube": []},
        "splitters": [],
        "valid_paths": [],
        "available_routes": [],
        "default_route": None,
    }

    raw_sources = hardware.get("light_sources", [])
    if isinstance(raw_sources, list) and raw_sources:
        positions = {}
        for idx, src in enumerate(raw_sources, start=1):
            if not isinstance(src, dict):
                continue
            positions[idx] = _source_position(idx, src)
        if positions:
            payload["light_sources"].append(
                {
                    "id": "light_sources_0",
                    "name": "Light Sources / Lasers",
                    "display_label": "Light Sources / Lasers",
                    "type": "light_source_group",
                    "control_kind": "checkboxes",
                    "selection_mode": "multi",
                    "positions": positions,
                    "options": [
                        {"slot": slot, "display_label": entry.get("display_label"), "value": entry}
                        for slot, entry in sorted(positions.items())
                    ],
                }
            )

    raw_detectors = hardware.get("detectors", [])
    if isinstance(raw_detectors, list) and raw_detectors:
        for idx, det in enumerate(raw_detectors, start=1):
            if not isinstance(det, dict):
                continue
            position = _detector_position(idx, det)
            payload["detectors"].append(
                {
                    "id": f"detector_{idx}",
                    "name": position.get("channel_name") or position.get("display_label"),
                    "display_label": position.get("display_label"),
                    "type": "detector_group",
                    "control_kind": "detector_toggle",
                    "selection_mode": "multi",
                    "positions": {1: position},
                    "options": [{"slot": 1, "display_label": position.get("display_label"), "value": position}],
                }
            )

    for stage_name, source_key in stage_mappings.items():
        mechanisms = _iter_mechanisms(light_path, source_key)
        if stage_name == "cube":
            payload["stages"][stage_name] = [
                _cube_mechanism_payload(index, mechanism)
                for index, mechanism in enumerate(mechanisms)
            ]
        else:
            payload["stages"][stage_name] = [
                _mechanism_payload(prefix_mappings[stage_name], index, mechanism)
                for index, mechanism in enumerate(mechanisms)
            ]

    for index, splitter in enumerate(_collect_splitters(hardware, light_path)):
        payload["splitters"].append(_splitter_payload(index, splitter))

    payload["valid_paths"] = calculate_valid_paths(payload)
    payload["available_routes"] = _route_catalog_entries(payload)
    if payload["available_routes"]:
        payload["default_route"] = payload["available_routes"][0]["id"]
    return json.loads(json.dumps(payload))
