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


DICHROIC_TYPES = {"dichroic", "multiband_dichroic", "polychroic"}
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
POWER_VALUE_RE = re.compile(r"(\d+(?:\.\d+)?)")

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



def validate_light_path(instrument_dict: dict) -> list[str]:
    """Validate light-path mechanisms and optical components in an instrument record."""
    errors: list[str] = []
    hardware = instrument_dict.get("hardware", {})
    light_path = hardware.get("light_path", {})
    if not isinstance(light_path, dict):
        return ["hardware.light_path must be a mapping/object."]

    def branch_targets(raw_branch: dict[str, Any]) -> list[str]:
        raw_targets = (
            raw_branch.get("targets")
            or raw_branch.get("target_ids")
            or raw_branch.get("terminal_ids")
            or raw_branch.get("endpoint_ids")
            or raw_branch.get("target")
            or raw_branch.get("endpoint")
        )
        values = raw_targets if isinstance(raw_targets, list) else [raw_targets]
        normalized: list[str] = []
        for value in values:
            identifier = _clean_identifier(value)
            if identifier and identifier not in normalized:
                normalized.append(identifier)
        return normalized

    known_target_ids: set[str] = set()
    explicit_endpoint_ids: dict[str, int] = {}

    for det_index, detector in enumerate(hardware.get("detectors", [])):
        if isinstance(detector, dict):
            for candidate in (
                detector.get("id"),
                detector.get("channel_name"),
                detector.get("channel"),
                detector.get("name"),
                detector.get("display_label"),
            ):
                normalized_candidate = _clean_identifier(candidate)
                if normalized_candidate:
                    known_target_ids.add(normalized_candidate)

    endpoint_rows = _collect_endpoint_rows(hardware, light_path)
    for endpoint_index, endpoint in enumerate(endpoint_rows):
        if not isinstance(endpoint, dict):
            continue
        explicit_id = _clean_identifier(endpoint.get("id"))
        if explicit_id:
            if explicit_id in explicit_endpoint_ids:
                errors.append(
                    f"endpoints[{endpoint_index}]: duplicate endpoint id `{endpoint.get('id')}` already declared in endpoints[{explicit_endpoint_ids[explicit_id]}]."
                )
            else:
                explicit_endpoint_ids[explicit_id] = endpoint_index
        for candidate in (
            endpoint.get("id"),
            endpoint.get("terminal_id"),
            endpoint.get("name"),
            endpoint.get("display_label"),
        ):
            normalized_candidate = _clean_identifier(candidate)
            if normalized_candidate:
                known_target_ids.add(normalized_candidate)

    for split_idx, splitter in enumerate(_collect_splitters(hardware, light_path)):
        split_ctx = f"splitters[{split_idx}]"
        if isinstance(splitter.get("path_1"), dict):
            _validate_splitter_branch(splitter["path_1"], errors, f"{split_ctx}.path_1")
            if known_target_ids:
                for target_id in branch_targets(splitter["path_1"]):
                    if target_id not in known_target_ids:
                        errors.append(f"{split_ctx}.path_1: target `{target_id}` does not match any declared detector or endpoint.")

        if isinstance(splitter.get("path_2"), dict):
            _validate_splitter_branch(splitter["path_2"], errors, f"{split_ctx}.path_2")
            if known_target_ids:
                for target_id in branch_targets(splitter["path_2"]):
                    if target_id not in known_target_ids:
                        errors.append(f"{split_ctx}.path_2: target `{target_id}` does not match any declared detector or endpoint.")

        if isinstance(splitter.get("branches"), list):
            for branch_index, branch in enumerate(splitter.get("branches") or []):
                if not isinstance(branch, dict):
                    errors.append(f"{split_ctx}.branches[{branch_index}]: branch entry must be an object.")
                    continue
                _validate_splitter_branch(branch, errors, f"{split_ctx}.branches[{branch_index}]")
                if known_target_ids:
                    for target_id in branch_targets(branch):
                        if target_id not in known_target_ids:
                            errors.append(
                                f"{split_ctx}.branches[{branch_index}]: target `{target_id}` does not match any declared detector or endpoint."
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
    return " ".join(part for part in [prefix, kind, manufacturer, model] if part).strip() or model or kind.title() or "Light Source"



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
        "qe_peak_pct": endpoint.get("qe_peak_pct"),
        "read_noise_e": endpoint.get("read_noise_e"),
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



def generate_virtual_microscope_payload(instrument_dict: dict, *, include_inferred_terminals: bool = False) -> dict:
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
        "terminals": [],
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
            mechanism_id = f"detector_{idx}"
            position = _detector_position(idx, det, mechanism_id=mechanism_id)
            payload["terminals"].append(dict(position))
            payload["detectors"].append(
                {
                    "id": mechanism_id,
                    "name": position.get("channel_name") or position.get("display_label"),
                    "display_label": position.get("display_label"),
                    "type": "detector_group",
                    "control_kind": "detector_toggle",
                    "selection_mode": "multi",
                    "positions": {1: position},
                    "options": [{"slot": 1, "display_label": position.get("display_label"), "value": position}],
                }
            )

    explicit_endpoints = _collect_endpoint_rows(hardware, light_path)
    for idx, endpoint in enumerate(explicit_endpoints, start=1):
        payload["terminals"].append(_terminal_payload_from_endpoint(idx, endpoint))

    splitters_raw = _collect_splitters(hardware, light_path)
    if include_inferred_terminals:
        _infer_default_terminals(instrument_dict, splitters_raw, payload["terminals"])
        payload["metadata"]["uses_inferred_terminals"] = True

    splitters_with_missing_branches = [
        splitter
        for splitter in splitters_raw
        if isinstance(splitter, dict) and not isinstance(splitter.get("branches"), list)
    ]
    payload["metadata"]["graph_incomplete"] = (
        len(payload["terminals"]) == 0
        or bool(splitters_with_missing_branches)
    )

    for terminal_index, terminal in enumerate(payload["terminals"], start=1):
        if terminal.get("endpoint_type") == "detector":
            continue
        payload["detectors"].append(_terminal_mechanism_payload(terminal_index, terminal))

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

    for index, splitter in enumerate(splitters_raw):
        payload["splitters"].append(_splitter_payload(index, splitter, payload["terminals"]))

    if any(
        not branch.get("target_ids")
        for splitter in payload["splitters"]
        if isinstance(splitter, dict)
        for branch in splitter.get("branches", [])
        if isinstance(branch, dict)
    ):
        payload["metadata"]["graph_incomplete"] = True

    payload["valid_paths"] = calculate_valid_paths(payload)
    payload["available_routes"] = _route_catalog_entries(payload)
    if payload["available_routes"]:
        payload["default_route"] = payload["available_routes"][0]["id"]
    return json.loads(json.dumps(payload))
