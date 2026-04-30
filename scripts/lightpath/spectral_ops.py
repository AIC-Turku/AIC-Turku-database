"""Spectral operation and component-payload helpers for light-path parsing.

This module owns parser-authoritative component serialization and spectral
operation derivation.

It must not import scripts.light_path_parser.

Responsibilities:
- normalize component numeric fields
- build component labels/details/render kinds
- derive spectral_ops for components and filter cubes
- build light-source / detector / terminal / mechanism payloads

Non-responsibilities:
- canonical YAML parsing
- legacy import
- contract validation
- route graph construction
- selected_execution projection
- VM payload aggregation
"""

from __future__ import annotations

from typing import Any

from scripts.display_labels import resolve_stage_role_label
from scripts.lightpath.model import (
    DICHROIC_TYPES,
    NO_WAVELENGTH_TYPES,
    CUBE_LINK_KEYS,
    _clean_identifier,
    _clean_string,
    _coerce_number,
    _coerce_slot_key,
    _detector_class,
    _format_numeric,
    _is_positive_number,
    _normalize_endpoint_type,
    _normalize_light_source_kind,
    _normalize_power_weight,
    _normalize_routes,
    _resolve_component_type_label,
    _resolve_cube_link_label,
    _resolve_light_source_kind,
    get_active_vocab,
)


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


def _band_strings(component: dict[str, Any], key: str) -> list[str]:
    raw_bands = component.get(key)
    if not isinstance(raw_bands, list):
        return []

    rendered: list[str] = []
    for band in raw_bands:
        if not isinstance(band, dict):
            continue

        center = _coerce_number(band.get("center_nm"))
        width = _coerce_number(band.get("width_nm"))

        if _is_positive_number(center) and _is_positive_number(width):
            rendered.append(f"{_format_numeric(center)}/{_format_numeric(width)}")

    return rendered


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
                    band_strings.append(
                        f"{_format_numeric(center)}/{_format_numeric(width)}"
                    )

            if band_strings:
                return " + ".join(band_strings)

        center = component.get("center_nm")
        width = component.get("width_nm")
        if _is_positive_number(center) and _is_positive_number(width):
            return f"{_format_numeric(center)}/{_format_numeric(width)}"

        return _resolve_component_type_label(str(component_type))

    if component_type == "longpass":
        cut_on = component.get("cut_on_nm")
        return (
            f"LP {_format_numeric(cut_on)}"
            if _is_positive_number(cut_on)
            else "Longpass"
        )

    if component_type == "shortpass":
        cut_off = component.get("cut_off_nm")
        return (
            f"SP {_format_numeric(cut_off)}"
            if _is_positive_number(cut_off)
            else "Shortpass"
        )

    if component_type in DICHROIC_TYPES:
        if component_type in {"multiband_dichroic", "polychroic"}:
            transmission = _band_strings(component, "transmission_bands")
            reflection = _band_strings(component, "reflection_bands")

            if transmission or reflection:
                parts: list[str] = []
                if transmission:
                    parts.append(f"T[{ ' + '.join(transmission) }]")
                if reflection:
                    parts.append(f"R[{ ' + '.join(reflection) }]")
                return f"Dichroic {' | '.join(parts)}"

        cutoffs = component.get("cutoffs_nm")
        if isinstance(cutoffs, list) and cutoffs:
            rendered = ", ".join(_format_numeric(value) for value in cutoffs)
            return f"Dichroic [{rendered}]"

        transmission = _band_strings(component, "transmission_bands")
        reflection = _band_strings(component, "reflection_bands")
        if transmission or reflection:
            parts: list[str] = []
            if transmission:
                parts.append(f"T[{ ' + '.join(transmission) }]")
            if reflection:
                parts.append(f"R[{ ' + '.join(reflection) }]")
            return f"Dichroic {' | '.join(parts)}"

        return "Dichroic"

    if component_type in NO_WAVELENGTH_TYPES:
        return _resolve_component_type_label(str(component_type))

    return _resolve_component_type_label(str(component_type))


def _render_kind(component: dict[str, Any]) -> str:
    component_type = str(component.get("component_type", "unknown")).lower()

    if component_type in {"laser", "light_source", "led"}:
        return "source"
    if component_type in {"detector"}:
        return "detector"
    if component_type in {"bandpass", "notch", "multiband_bandpass", "filter_cube"}:
        return "band"
    if component_type in {"longpass"}:
        return "longpass"
    if component_type in {"shortpass"}:
        return "shortpass"
    if component_type in {"tunable"}:
        return "tunable"
    if component_type in NO_WAVELENGTH_TYPES:
        return "empty"
    if component_type in DICHROIC_TYPES:
        return "dichroic"
    if component_type in {"analyzer"}:
        return "analyzer"

    return "other"


def _build_details(component: dict[str, Any]) -> str:
    manufacturer = component.get("manufacturer")
    model = component.get("model")
    product_code = component.get("product_code")
    notes = component.get("notes")

    parts = [
        str(part).strip()
        for part in (manufacturer, model, product_code, notes)
        if isinstance(part, str) and part.strip()
    ]

    return " | ".join(parts)


def _normalize_component_numeric_fields(
    component_payload: dict[str, Any],
    source: dict[str, Any],
) -> None:
    for key in (
        "center_nm",
        "width_nm",
        "cut_on_nm",
        "cut_off_nm",
        "wavelength_nm",
        "tunable_min_nm",
        "tunable_max_nm",
        "pulse_width_ps",
        "repetition_rate_mhz",
        "qe_peak_pct",
        "read_noise_e",
        "default_gating_delay_ns",
        "default_gate_width_ns",
        "power_weight",
        "collection_min_nm",
        "collection_max_nm",
        "collection_center_nm",
        "collection_width_nm",
        "channel_center_nm",
        "bandwidth_nm",
        "min_nm",
        "max_nm",
    ):
        if key not in source:
            continue

        numeric = _coerce_number(source.get(key))
        if numeric is not None:
            component_payload[key] = numeric
        elif source.get(key) is not None:
            component_payload[key] = source.get(key)

    cutoffs = source.get("cutoffs_nm")
    if isinstance(cutoffs, list):
        component_payload["cutoffs_nm"] = [
            value
            for value in (_coerce_number(item) for item in cutoffs)
            if value is not None
        ]

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

    for band_key in ("transmission_bands", "reflection_bands"):
        raw_bands = source.get(band_key)
        if not isinstance(raw_bands, list):
            continue

        normalized_bands = []
        for band in raw_bands:
            if not isinstance(band, dict):
                continue

            center = _coerce_number(band.get("center_nm"))
            width = _coerce_number(band.get("width_nm"))
            if center is None or width is None:
                continue

            normalized_bands.append({"center_nm": center, "width_nm": width})

        if normalized_bands:
            component_payload[band_key] = normalized_bands


def _extract_dichroic_spectral_data(component: dict[str, Any]) -> dict[str, Any]:
    """Extract the raw dichroic spectral specification fields from a component."""
    data: dict[str, Any] = {}

    if isinstance(component.get("transmission_bands"), list) and component["transmission_bands"]:
        data["transmission_bands"] = component["transmission_bands"]

    if isinstance(component.get("reflection_bands"), list) and component["reflection_bands"]:
        data["reflection_bands"] = component["reflection_bands"]

    if isinstance(component.get("bands"), list) and component["bands"]:
        data["bands"] = component["bands"]

    cut_on = _coerce_number(component.get("cut_on_nm"))
    if cut_on is not None:
        data["cut_on_nm"] = cut_on

    if isinstance(component.get("cutoffs_nm"), list) and component["cutoffs_nm"]:
        data["cutoffs_nm"] = component["cutoffs_nm"]

    return data


def _spectral_ops_for_component(component: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Compute parser-authoritative spectral operations keyed by phase.

    Every mechanism position and component payload receives this field so the
    browser runtime never has to interpret component types to decide spectral
    behavior. The runtime becomes a pure executor of these pre-computed ops.

    Returns:
        {"illumination": [...], "detection": [...]}
    """
    ctype = _clean_string(
        component.get("component_type")
        or component.get("type")
    ).lower()

    passthrough: list[dict[str, Any]] = [{"op": "passthrough"}]

    if not ctype or ctype in {"mirror", "empty", "passthrough", "neutral_density"}:
        return {"illumination": list(passthrough), "detection": list(passthrough)}

    if ctype in {"block", "blocker"}:
        both: list[dict[str, Any]] = [{"op": "block"}]
        return {"illumination": list(both), "detection": list(both)}

    if ctype == "analyzer":
        both = [
            {
                "op": "passthrough",
                "unsupported_reason": "polarization_not_modeled",
            }
        ]
        return {"illumination": list(both), "detection": list(both)}

    if ctype == "bandpass":
        center = _coerce_number(component.get("center_nm"))
        width = _coerce_number(component.get("width_nm"))

        if center is not None and width is not None:
            op: dict[str, Any] = {
                "op": "bandpass",
                "center_nm": center,
                "width_nm": width,
            }
        else:
            bands = component.get("bands")
            if isinstance(bands, list) and bands:
                normalized = [
                    b
                    for b in (
                        {
                            "center_nm": _coerce_number(b.get("center_nm")),
                            "width_nm": _coerce_number(b.get("width_nm")),
                        }
                        for b in bands
                        if isinstance(b, dict)
                    )
                    if b.get("center_nm") is not None
                ]
                if normalized:
                    op = {"op": "multiband_bandpass", "bands": normalized}
                else:
                    op = {
                        "op": "passthrough",
                        "unsupported_reason": "bandpass missing usable spectral data",
                    }
            else:
                op = {
                    "op": "passthrough",
                    "unsupported_reason": (
                        "bandpass missing center_nm/width_nm and no bands"
                    ),
                }

        return {"illumination": [op], "detection": [op]}

    if ctype == "multiband_bandpass":
        bands = component.get("bands")
        if isinstance(bands, list) and bands:
            normalized = [
                b
                for b in (
                    {
                        "center_nm": _coerce_number(b.get("center_nm")),
                        "width_nm": _coerce_number(b.get("width_nm")),
                    }
                    for b in bands
                    if isinstance(b, dict)
                )
                if b.get("center_nm") is not None
            ]
            if normalized:
                op = {"op": "multiband_bandpass", "bands": normalized}
            else:
                op = {
                    "op": "passthrough",
                    "unsupported_reason": "multiband_bandpass bands are invalid",
                }
        else:
            op = {
                "op": "passthrough",
                "unsupported_reason": "multiband_bandpass missing bands",
            }

        return {"illumination": [op], "detection": [op]}

    if ctype == "longpass":
        cut_on = _coerce_number(component.get("cut_on_nm"))
        if cut_on is not None:
            op = {"op": "longpass", "cut_on_nm": cut_on}
        else:
            op = {
                "op": "passthrough",
                "unsupported_reason": "longpass missing cut_on_nm",
            }

        return {"illumination": [op], "detection": [op]}

    if ctype == "shortpass":
        cut_off = _coerce_number(component.get("cut_off_nm"))
        if cut_off is not None:
            op = {"op": "shortpass", "cut_off_nm": cut_off}
        else:
            op = {
                "op": "passthrough",
                "unsupported_reason": "shortpass missing cut_off_nm",
            }

        return {"illumination": [op], "detection": [op]}

    if ctype == "notch":
        center = _coerce_number(component.get("center_nm"))
        width = _coerce_number(component.get("width_nm"))
        if center is not None and width is not None:
            op = {"op": "notch", "center_nm": center, "width_nm": width}
        else:
            op = {
                "op": "passthrough",
                "unsupported_reason": "notch missing center_nm or width_nm",
            }

        return {"illumination": [op], "detection": [op]}

    if ctype == "tunable":
        start = (
            _coerce_number(component.get("band_start_nm"))
            or _coerce_number(component.get("min_nm"))
        )
        end = (
            _coerce_number(component.get("band_end_nm"))
            or _coerce_number(component.get("max_nm"))
        )
        if start is not None and end is not None:
            op = {
                "op": "tunable_bandpass",
                "start_nm": start,
                "end_nm": end,
            }
        else:
            op = {
                "op": "passthrough",
                "unsupported_reason": "tunable missing start/end bounds",
            }

        return {"illumination": [op], "detection": [op]}

    if ctype in DICHROIC_TYPES:
        dichroic_data = _extract_dichroic_spectral_data(component)
        if not any(
            key in dichroic_data
            for key in (
                "transmission_bands",
                "reflection_bands",
                "bands",
                "cut_on_nm",
                "cutoffs_nm",
            )
        ):
            op = {
                "op": "passthrough",
                "unsupported_reason": (
                    "dichroic requires transmission_bands, reflection_bands, "
                    "bands, or cut_on_nm"
                ),
            }
            return {"illumination": [op], "detection": [op]}

        return {
            "illumination": [{"op": "dichroic_reflect", **dichroic_data}],
            "detection": [{"op": "dichroic_transmit", **dichroic_data}],
        }

    if ctype == "filter_cube":
        return _cube_spectral_ops(component)

    return {
        "illumination": [
            {
                "op": "passthrough",
                "unsupported_reason": f"unknown component type '{ctype}'",
            }
        ],
        "detection": [
            {
                "op": "passthrough",
                "unsupported_reason": f"unknown component type '{ctype}'",
            }
        ],
    }


def _cube_spectral_ops(component: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Compute phase-aware spectral ops for a filter cube.

    In illumination:
    - excitation_filter
    - dichroic in reflection mode

    In detection:
    - dichroic in transmission mode
    - emission_filter
    """
    exc = (
        component.get("excitation_filter")
        or component.get("excitation")
        or component.get("ex")
    )
    di = (
        component.get("dichroic")
        or component.get("dichroic_filter")
        or component.get("di")
    )
    em = (
        component.get("emission_filter")
        or component.get("emission")
        or component.get("em")
    )

    linked_components = component.get("linked_components")
    if not isinstance(linked_components, dict):
        linked_components = {}

    if isinstance(exc, dict):
        linked_components.setdefault("excitation_filter", exc)
    if isinstance(di, dict):
        linked_components.setdefault("dichroic", di)
    if isinstance(em, dict):
        linked_components.setdefault("emission_filter", em)

    if linked_components:
        component["linked_components"] = linked_components

    if component.get("_cube_incomplete"):
        reason = "filter_cube_incomplete_reconstruction"
        return {
            "illumination": [
                {
                    "op": "passthrough",
                    "unsupported_reason": reason,
                }
            ],
            "detection": [
                {
                    "op": "passthrough",
                    "unsupported_reason": reason,
                }
            ],
        }

    illumination: list[dict[str, Any]] = []
    detection: list[dict[str, Any]] = []

    if isinstance(exc, dict):
        exc_ops = _spectral_ops_for_component(exc)
        for op in exc_ops.get("illumination", []):
            illumination.append({**op, "sub_role": "excitation_filter"})

    if isinstance(di, dict):
        di_data = _extract_dichroic_spectral_data(di)
        illumination.append(
            {
                "op": "dichroic_reflect",
                "sub_role": "dichroic",
                **di_data,
            }
        )
        detection.append(
            {
                "op": "dichroic_transmit",
                "sub_role": "dichroic",
                **di_data,
            }
        )

    if isinstance(em, dict):
        em_ops = _spectral_ops_for_component(em)
        for op in em_ops.get("detection", []):
            detection.append({**op, "sub_role": "emission_filter"})

    if not illumination:
        illumination = [
            {
                "op": "passthrough",
                "unsupported_reason": "filter_cube missing excitation/dichroic data",
            }
        ]

    if not detection:
        detection = [
            {
                "op": "passthrough",
                "unsupported_reason": "filter_cube missing dichroic/emission data",
            }
        ]

    return {"illumination": illumination, "detection": detection}


def _component_payload(
    component: dict[str, Any],
    *,
    default_name: str = "",
    branch_mode: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = dict(component)

    component_type = _clean_string(component.get("component_type")).lower()

    # Infer omitted component types based on optical properties to prevent
    # filter cube internals from resolving to "unknown" and bypassing the
    # simulator.
    if not component_type:
        if "center_nm" in component and "width_nm" in component:
            component_type = "bandpass"
        elif "cut_on_nm" in component and "bands" not in component:
            component_type = "longpass"
        elif "cut_off_nm" in component:
            component_type = "shortpass"
        elif "cutoffs_nm" in component or "transmission_bands" in component:
            component_type = "dichroic"
        else:
            component_type = "unknown"

    payload["component_type"] = component_type
    payload["type"] = component_type
    payload["label"] = _build_label(component)
    payload["display_label"] = payload.get("label")
    payload["details"] = _build_details(component)
    payload["render_kind"] = _render_kind(component)

    if default_name and not _clean_string(payload.get("name")):
        payload["name"] = default_name

    routes = _normalize_routes(
        component.get("path")
        or component.get("paths")
        or component.get("route")
        or component.get("routes")
    )
    if routes:
        payload["routes"] = routes
        payload["path"] = routes[0]

    if branch_mode:
        payload["branch_mode"] = branch_mode

    _normalize_component_numeric_fields(payload, component)

    if component_type == "analyzer":
        payload["_unsupported_spectral_model"] = True

    payload["spectral_ops"] = _spectral_ops_for_component(payload)
    return payload


def _light_source_display_label(source: dict[str, Any]) -> str:
    raw_kind = _normalize_light_source_kind(
        source.get("kind")
        or source.get("type")
        or "source"
    )
    kind = _resolve_light_source_kind(raw_kind)

    manufacturer = _clean_string(source.get("manufacturer"))
    model = _clean_string(source.get("model"))
    wavelength = source.get("wavelength_nm")
    tunable_min = source.get("tunable_min_nm")
    tunable_max = source.get("tunable_max_nm")

    prefix = ""
    if _coerce_number(wavelength) is not None:
        prefix = f"{_format_numeric(wavelength)} nm"
    elif (
        _coerce_number(tunable_min) is not None
        and _coerce_number(tunable_max) is not None
    ):
        prefix = f"{_format_numeric(tunable_min)}-{_format_numeric(tunable_max)} nm"
    elif isinstance(wavelength, str) and wavelength.strip():
        prefix = wavelength.strip()

    return (
        " ".join(part for part in [prefix, kind, manufacturer, model] if part).strip()
        or model
        or _resolve_light_source_kind(raw_kind)
        or "Light Source"
    )


def infer_light_source_role(source: dict[str, Any]) -> str:
    """SIMULATOR-ONLY fallback role inference.

    This helper is intentionally non-authoritative and must not be used to
    populate canonical/production role fields. Canonical role must come from
    explicit YAML `role`.
    """
    explicit = _clean_string(source.get("role")).lower()
    if explicit:
        return explicit

    routes = _normalize_routes(
        source.get("path")
        or source.get("paths")
        or source.get("route")
        or source.get("routes")
    )
    if "transmitted" in routes:
        return "transmitted_illumination"

    return "excitation"


def _source_role(source: dict[str, Any]) -> str:
    return _clean_string(source.get("role")).lower()


def _source_spectral_mode(
    kind: str,
    wavelength: Any,
    width_nm: Any,
    tunable_min_nm: Any,
    tunable_max_nm: Any,
) -> str:
    if (
        _coerce_number(tunable_min_nm) is not None
        and _coerce_number(tunable_max_nm) is not None
    ):
        if kind in {
            "laser",
            "white_light_laser",
            "multiphoton_laser",
            "supercontinuum",
        }:
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
    kind = _normalize_light_source_kind(source.get("kind") or source.get("type") or "light_source")

    display_label = _light_source_display_label(
        {
            **source,
            "tunable_min_nm": tunable_min,
            "tunable_max_nm": tunable_max,
        }
    )
    role = _source_role(source)

    position: dict[str, Any] = {
        "slot": slot,
        "component_type": (
            "laser"
            if kind in {
                "laser",
                "white_light_laser",
                "multiphoton_laser",
                "supercontinuum",
            }
            else "light_source"
        ),
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
        "spectral_mode": _source_spectral_mode(
            kind,
            wavelength,
            width_nm,
            tunable_min,
            tunable_max,
        ),
        "timing_mode": source.get("timing_mode"),
        "pulse_width_ps": source.get("pulse_width_ps"),
        "repetition_rate_mhz": source.get("repetition_rate_mhz"),
        "depletion_targets_nm": (
            source.get("depletion_targets_nm")
            if isinstance(source.get("depletion_targets_nm"), list)
            else []
        ),
        "power": source.get("power"),
        "power_weight": _normalize_power_weight(source.get("power")),
        "details": _build_details(source),
        "notes": source.get("notes"),
    }

    routes = _normalize_routes(
        source.get("path")
        or source.get("paths")
        or source.get("route")
        or source.get("routes")
    )
    if routes:
        position["routes"] = routes
        position["path"] = routes[0]

    _normalize_component_numeric_fields(position, position)
    return position


def _detector_position(
    slot: int,
    detector: dict[str, Any],
    *,
    terminal_id: str | None = None,
    mechanism_id: str | None = None,
) -> dict[str, Any]:
    kind = _clean_string(detector.get("kind") or detector.get("type") or "detector").lower() or "detector"
    manufacturer = _clean_string(detector.get("manufacturer"))
    model = _clean_string(detector.get("model"))

    channel_name = (
        _clean_string(
            detector.get("channel_name")
            or detector.get("channel")
            or detector.get("name")
        )
        or f"Detector {slot}"
    )
    display_label = (
        " ".join(
            part
            for part in [
                channel_name if channel_name not in {manufacturer, model} else "",
                manufacturer,
                model,
            ]
            if part
        ).strip()
        or channel_name
        or manufacturer
        or model
        or f"Detector {slot}"
    )

    resolved_terminal_id = (
        terminal_id
        or _clean_identifier(detector.get("id"))
        or f"terminal_detector_{slot}"
    )

    position: dict[str, Any] = {
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
        "default_enabled": (
            detector.get("default_enabled")
            if isinstance(detector.get("default_enabled"), bool)
            else True
        ),
        "is_digital": True,
    }

    routes = _normalize_routes(
        detector.get("path")
        or detector.get("paths")
        or detector.get("route")
        or detector.get("routes")
    )
    if routes:
        position["routes"] = routes
        position["path"] = routes[0]

    _normalize_component_numeric_fields(position, position)
    return position


def _terminal_payload_from_endpoint(
    index: int,
    endpoint: dict[str, Any],
    *,
    default_name: str | None = None,
) -> dict[str, Any]:
    endpoint_type = _normalize_endpoint_type(
        endpoint.get("endpoint_type")
        or endpoint.get("type")
        or endpoint.get("kind")
        or endpoint.get("name")
    )
    terminal_id = _clean_identifier(endpoint.get("id")) or f"terminal_{endpoint_type}_{index}"
    kind = _clean_string(endpoint.get("kind") or endpoint_type).lower() or endpoint_type

    default_labels = {
        "eyepiece": "Eyepieces",
        "camera_port": "Camera Port",
        "detector": f"Endpoint {index}",
    }
    display_label = (
        _clean_string(endpoint.get("display_label") or endpoint.get("name") or default_name)
        or default_labels.get(endpoint_type, f"Endpoint {index}")
    )

    payload: dict[str, Any] = {
        "id": terminal_id,
        "terminal_id": terminal_id,
        "slot": 1,
        "component_type": "detector",
        "render_kind": "detector",
        "type": endpoint_type,
        "endpoint_type": endpoint_type,
        "kind": kind if endpoint_type == "detector" else endpoint_type,
        "detector_class": (
            endpoint_type
            if endpoint_type in {"eyepiece", "camera_port"}
            else _detector_class(kind)
        ),
        "name": display_label,
        "display_label": display_label,
        "channel_name": display_label,
        "manufacturer": endpoint.get("manufacturer"),
        "product_code": endpoint.get("product_code"),
        "model": endpoint.get("model"),
        "pixel_pitch_um": endpoint.get("pixel_pitch_um") or endpoint.get("pixel_size_um"),
        "sensor_format_px": endpoint.get("sensor_format_px"),
        "binning": endpoint.get("binning"),
        "bit_depth": endpoint.get("bit_depth"),
        "qe_peak_pct": endpoint.get("qe_peak_pct"),
        "read_noise_e": endpoint.get("read_noise_e"),
        "supports_time_gating": endpoint.get("supports_time_gating"),
        "default_gating_delay_ns": endpoint.get("default_gating_delay_ns"),
        "default_gate_width_ns": endpoint.get("default_gate_width_ns"),
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
        "default_enabled": (
            endpoint.get("default_enabled")
            if isinstance(endpoint.get("default_enabled"), bool)
            else False
        ),
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

    routes = _normalize_routes(
        endpoint.get("path")
        or endpoint.get("paths")
        or endpoint.get("route")
        or endpoint.get("routes")
    )
    if routes:
        payload["routes"] = routes
        payload["path"] = routes[0]

    _normalize_component_numeric_fields(payload, payload)
    return payload


def _terminal_mechanism_payload(index: int, terminal: dict[str, Any]) -> dict[str, Any]:
    mechanism_payload: dict[str, Any] = {
        "id": f"endpoint_{_clean_identifier(terminal.get('id')) or index}",
        "name": terminal.get("display_label")
        or terminal.get("name")
        or f"Endpoint {index}",
        "display_label": terminal.get("display_label")
        or terminal.get("name")
        or f"Endpoint {index}",
        "type": "endpoint_group",
        "control_kind": "detector_toggle",
        "selection_mode": "multi",
        "positions": {1: dict(terminal)},
        "options": [
            {
                "slot": 1,
                "display_label": terminal.get("display_label") or terminal.get("name"),
                "value": dict(terminal),
            }
        ],
    }

    routes = _normalize_routes(terminal.get("routes") or terminal.get("path"))
    if routes:
        mechanism_payload["routes"] = routes
        mechanism_payload["path"] = routes[0]

    return mechanism_payload


def _candidate_terminals_for_routes(
    terminals: list[dict[str, Any]],
    routes: list[str],
) -> list[dict[str, Any]]:
    from scripts.lightpath.model import _routes_overlap

    return [
        terminal
        for terminal in terminals
        if _routes_overlap(
            routes,
            (
                terminal.get("routes")
                if isinstance(terminal.get("routes"), list)
                else _normalize_routes(terminal.get("path"))
            ),
        )
    ]


def _resolve_target_ids(
    raw_targets: Any,
    terminals: list[dict[str, Any]],
) -> list[str]:
    values = raw_targets if isinstance(raw_targets, list) else [raw_targets]

    terminals_by_id: dict[str, str] = {}
    for terminal in terminals:
        if not isinstance(terminal, dict):
            continue

        for key in ("id", "terminal_id"):
            identifier = _clean_identifier(terminal.get(key))
            if (
                identifier
                and identifier not in terminals_by_id
                and isinstance(terminal.get("id"), str)
            ):
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


def _append_inferred_terminal(
    terminals: list[dict[str, Any]],
    endpoint_type: str,
    *,
    name: str,
    path: str | None = None,
    default_enabled: bool = False,
) -> None:
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
    instrument_meta = (
        instrument_dict.get("instrument", {})
        if isinstance(instrument_dict.get("instrument"), dict)
        else {}
    )
    ocular = _clean_string(instrument_meta.get("ocular_availability")).lower()
    has_digital = any(bool(terminal.get("is_digital")) for terminal in terminals)

    def has_endpoint(endpoint_type: str) -> bool:
        return any(
            _normalize_endpoint_type(
                terminal.get("endpoint_type")
                or terminal.get("type")
                or terminal.get("kind")
            )
            == endpoint_type
            for terminal in terminals
        )

    default_enable = not has_digital

    if ocular in {"binocular", "trinocular"} and not has_endpoint("eyepiece"):
        _append_inferred_terminal(
            terminals,
            "eyepiece",
            name="Eyepieces",
            path="shared",
            default_enabled=default_enable,
        )

    if ocular in {"trinocular", "camera_only"} and not has_endpoint("camera_port"):
        _append_inferred_terminal(
            terminals,
            "camera_port",
            name="Camera Port",
            path="shared",
            default_enabled=default_enable,
        )

    for splitter in splitters:
        text = " ".join(
            part
            for part in (
                _clean_string(splitter.get("name")),
                _clean_string(splitter.get("notes")),
            )
            if part
        ).lower()
        routes = _normalize_routes(
            splitter.get("path")
            or splitter.get("paths")
            or splitter.get("route")
            or splitter.get("routes")
        )
        route_hint = routes[0] if routes else "shared"

        if "camera" in text and "port" in text and not has_endpoint("camera_port"):
            _append_inferred_terminal(
                terminals,
                "camera_port",
                name="Camera Port",
                path=route_hint,
                default_enabled=default_enable,
            )

        if (
            any(keyword in text for keyword in ("eyepiece", "ocular"))
            and not has_endpoint("eyepiece")
        ):
            _append_inferred_terminal(
                terminals,
                "eyepiece",
                name="Eyepieces",
                path=route_hint,
                default_enabled=default_enable,
            )


def _mechanism_payload(
    stage_prefix: str,
    index: int,
    mechanism: dict[str, Any],
) -> dict[str, Any]:
    from scripts.lightpath.route_graph import _iter_element_positions, _resolve_position_candidate_payload

    positions: list[dict[str, Any]] = []

    for key_text, slot, position in _iter_element_positions(mechanism):
        if slot is None or not isinstance(position, dict):
            continue

        (
            component_payload,
            authored_position_id,
            position_key,
            position_label,
        ) = _resolve_position_candidate_payload(
            position,
            parent_element=mechanism,
            fallback_key=key_text,
            fallback_slot=slot,
        )
        if not component_payload:
            continue

        component_payload["slot"] = slot
        component_payload["position_key"] = position_key or key_text or str(slot)
        if authored_position_id:
            component_payload["id"] = authored_position_id
            component_payload["position_id"] = authored_position_id

        component_payload["display_label"] = (
            f"Slot {slot}: "
            f"{position_label or component_payload.get('label') or component_payload.get('display_label') or key_text or str(slot)}"
        )
        positions.append(component_payload)

    stage_label_key = {"exc": "excitation", "em": "emission"}.get(
        stage_prefix,
        stage_prefix,
    )
    default_stage_labels = {
        "exc": "Exc",
        "em": "Em",
        "dichroic": "Dichroic",
        "cube": "Cube",
        "analyzer": "Analyzer",
    }

    if get_active_vocab() is not None:
        stage_label = resolve_stage_role_label(stage_label_key)
    else:
        stage_label = default_stage_labels.get(
            stage_prefix,
            stage_label_key.replace("_", " ").title(),
        )

    mechanism_id = _clean_identifier(mechanism.get("id")) or f"{stage_prefix}_mech_{index}"

    mechanism_payload: dict[str, Any] = {
        "id": mechanism_id,
        "name": mechanism.get("name")
        or mechanism.get("display_label")
        or f"{stage_label} {index + 1}",
        "display_label": mechanism.get("display_label")
        or mechanism.get("name")
        or f"{stage_label} {index + 1}",
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

    routes = _normalize_routes(
        mechanism.get("path")
        or mechanism.get("paths")
        or mechanism.get("route")
        or mechanism.get("routes")
    )
    if routes:
        mechanism_payload["routes"] = routes
        mechanism_payload["path"] = routes[0]

    if isinstance(mechanism.get("notes"), str) and mechanism["notes"].strip():
        mechanism_payload["notes"] = mechanism["notes"].strip()

    if mechanism.get("type") == "spectral_array":
        mechanism_payload["control_kind"] = "spectral_array"
        min_nm = (
            mechanism.get("min_nm")
            if _is_positive_number(mechanism.get("min_nm"))
            else mechanism.get("band_min_nm")
        )
        max_nm = (
            mechanism.get("max_nm")
            if _is_positive_number(mechanism.get("max_nm"))
            else mechanism.get("band_max_nm")
        )
        bands = (
            mechanism.get("bands")
            if _is_positive_number(mechanism.get("bands"))
            else mechanism.get("max_bands")
        )

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


def _estimate_dichroic_cut_on(
    bands: Any,
    cut_on_nm: Any,
) -> float | None:
    """Estimate a dichroic cut-on wavelength from emission band data.

    For a single-band cube the dichroic is placed ~20 nm below the lower edge
    of the emission band. For multiband cubes the lowest band edge is used.
    When only a longpass cut_on_nm is present the dichroic is placed 20 nm
    below that cut-on.
    """
    if isinstance(bands, list) and bands:
        edges: list[float] = []
        for band in bands:
            if not isinstance(band, dict):
                continue

            center = _coerce_number(band.get("center_nm"))
            width = _coerce_number(band.get("width_nm"))
            if center is not None and width is not None and width > 0:
                edges.append(center - width / 2)

        if edges:
            return round(min(edges) - 20, 1)

    raw = cut_on_nm
    if isinstance(raw, list) and raw:
        raw = raw[0]

    coerced = _coerce_number(raw)
    if coerced is not None:
        return round(coerced - 20, 1)

    return None


def _cube_mechanism_payload(index: int, mechanism: dict[str, Any]) -> dict[str, Any]:
    from scripts.lightpath.route_graph import _iter_element_positions

    positions: list[dict[str, Any]] = []

    for key_text, slot, cube_position in _iter_element_positions(mechanism):
        if slot is None or not isinstance(cube_position, dict):
            continue

        linked_components: dict[str, dict[str, Any]] = {}
        for link_key in CUBE_LINK_KEYS:
            component = cube_position.get(link_key)
            if not isinstance(component, dict):
                continue

            linked_components[link_key] = _component_payload(
                component,
                default_name=_resolve_cube_link_label(link_key),
            )

        cube_label = cube_position.get("name") or f"Cube {slot}"

        if (
            not linked_components
            and _clean_string(cube_position.get("component_type")).lower() == "filter_cube"
        ):
            bands = cube_position.get("bands")
            cut_on_nm = cube_position.get("cut_on_nm")
            synth: dict[str, Any] = {"name": cube_label}

            if isinstance(bands, list) and len(bands) > 1:
                synth["component_type"] = "multiband_bandpass"
                synth["bands"] = bands
            elif isinstance(bands, list) and len(bands) == 1:
                synth["component_type"] = "bandpass"
                synth["bands"] = bands
                band = bands[0]
                if isinstance(band, dict):
                    if band.get("center_nm") is not None:
                        synth["center_nm"] = band["center_nm"]
                    if band.get("width_nm") is not None:
                        synth["width_nm"] = band["width_nm"]
            elif isinstance(cut_on_nm, list) and cut_on_nm:
                synth["component_type"] = "longpass"
                synth["cut_on_nm"] = _coerce_number(cut_on_nm[0])
            elif _coerce_number(cut_on_nm) is not None:
                synth["component_type"] = "longpass"
                synth["cut_on_nm"] = _coerce_number(cut_on_nm)
            else:
                synth["component_type"] = "bandpass"

            if synth.get("component_type"):
                linked_components["emission_filter"] = _component_payload(
                    synth,
                    default_name=cube_label,
                )

            dichroic_cut_on = _estimate_dichroic_cut_on(bands, cut_on_nm)
            if dichroic_cut_on is not None:
                linked_components["dichroic"] = _component_payload(
                    {
                        "name": f"{cube_label} (dichroic)",
                        "component_type": "dichroic",
                        "cut_on_nm": dichroic_cut_on,
                    },
                    default_name=f"{cube_label} (dichroic)",
                )

        authored_position_id = (
            _clean_string(cube_position.get("id"))
            or _clean_string(cube_position.get("position_key"))
            or key_text
            or str(slot)
        )

        position_payload: dict[str, Any] = {
            "id": authored_position_id,
            "position_id": authored_position_id,
            "slot": slot,
            "position_key": _clean_string(cube_position.get("position_key"))
            or key_text
            or str(slot),
            "type": "cube",
            "component_type": "filter_cube",
            "label": cube_label,
            "display_label": cube_label,
            "details": _build_details(cube_position),
            "linked_components": linked_components,
            "excitation_filter": linked_components.get("excitation_filter"),
            "dichroic": linked_components.get("dichroic"),
            "emission_filter": linked_components.get("emission_filter"),
        }

        if linked_components and any(k not in linked_components for k in CUBE_LINK_KEYS):
            position_payload["_cube_incomplete"] = True
            position_payload["_unsupported_spectral_model"] = True

        position_payload["spectral_ops"] = _cube_spectral_ops(position_payload)

        routes = _normalize_routes(
            cube_position.get("path")
            or cube_position.get("paths")
            or cube_position.get("route")
            or cube_position.get("routes")
            or mechanism.get("path")
        )
        if routes:
            position_payload["routes"] = routes
            position_payload["path"] = routes[0]

        positions.append(position_payload)

    mechanism_id = _clean_identifier(mechanism.get("id")) or f"cube_mech_{index}"

    mechanism_payload: dict[str, Any] = {
        "id": mechanism_id,
        "name": mechanism.get("name") or f"Cube {index + 1}",
        "display_label": mechanism.get("display_label")
        or mechanism.get("name")
        or f"Cube {index + 1}",
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

    routes = _normalize_routes(
        mechanism.get("path")
        or mechanism.get("paths")
        or mechanism.get("route")
        or mechanism.get("routes")
    )
    if routes:
        mechanism_payload["routes"] = routes
        mechanism_payload["path"] = routes[0]

    if isinstance(mechanism.get("notes"), str) and mechanism["notes"].strip():
        mechanism_payload["notes"] = mechanism["notes"].strip()

    return mechanism_payload


def _splitter_payload(
    index: int,
    splitter: dict[str, Any],
    terminals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    name = splitter.get("name", f"Splitter {index + 1}")
    dichroic_component = (
        splitter.get("dichroic", {}).copy()
        if isinstance(splitter.get("dichroic"), dict)
        else {}
    )
    if "cut_on_nm" in dichroic_component and "cutoffs_nm" not in dichroic_component:
        dichroic_component["cutoffs_nm"] = [dichroic_component["cut_on_nm"]]

    routes = _normalize_routes(
        splitter.get("path")
        or splitter.get("paths")
        or splitter.get("route")
        or splitter.get("routes")
    )
    candidate_terminals = _candidate_terminals_for_routes(terminals or [], routes)

    dichroic_pos = (
        _component_payload(dichroic_component, default_name="Splitter Dichroic")
        if dichroic_component
        else {}
    )

    def branch_component(
        raw_branch: dict[str, Any],
        *,
        default_name: str,
        branch_mode: str,
    ) -> dict[str, Any]:
        component = (
            raw_branch.get("emission_filter")
            if isinstance(raw_branch.get("emission_filter"), dict)
            else raw_branch.get("component")
        )
        if not isinstance(component, dict):
            component = {}

        return _component_payload(
            component,
            default_name=default_name,
            branch_mode=branch_mode,
        )

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

            mode = (
                _clean_string(raw_branch.get("mode")).lower()
                or ("transmitted" if branch_index == 1 else "reflected")
            )
            component = branch_component(
                raw_branch,
                default_name=f"Branch {branch_index} Filter",
                branch_mode=mode,
            )
            branch_payload: dict[str, Any] = {
                "id": _clean_identifier(raw_branch.get("id"))
                or f"splitter_{index}_branch_{branch_index}",
                "label": _clean_string(raw_branch.get("name") or raw_branch.get("label"))
                or f"Branch {branch_index}",
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
        branch_label = (
            branch.get("component", {}).get("label")
            if isinstance(branch.get("component"), dict)
            else ""
        )
        if branch_label:
            display_parts.append(f"{branch.get('label')}: {branch_label}")

    # path1/path2 remain only as a compatibility adapter for older runtime/app
    # consumers. Canonical authoring truth lives in branches plus ordered routes.
    path1_pos = branches[0].get("component") if branches else {}
    path2_pos = branches[1].get("component") if len(branches) > 1 else {}

    splitter_payload: dict[str, Any] = {
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
        "branch_selection_required": (
            any(not branch.get("target_ids") for branch in branches)
            and len(branches) > 1
        ),
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


__all__ = [
    "_band_strings",
    "_build_label",
    "_render_kind",
    "_build_details",
    "_normalize_component_numeric_fields",
    "_extract_dichroic_spectral_data",
    "_spectral_ops_for_component",
    "_cube_spectral_ops",
    "_component_payload",
    "_light_source_display_label",
    "infer_light_source_role",
    "_source_role",
    "_source_spectral_mode",
    "_source_position",
    "_detector_position",
    "_terminal_payload_from_endpoint",
    "_terminal_mechanism_payload",
    "_candidate_terminals_for_routes",
    "_resolve_target_ids",
    "_append_inferred_terminal",
    "_infer_default_terminals",
    "_mechanism_payload",
    "_estimate_dichroic_cut_on",
    "_cube_mechanism_payload",
    "_splitter_payload",
]
