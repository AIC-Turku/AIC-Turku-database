"""Dashboard instrument view DTO builders.

This module owns the instrument-page view projection derived from canonical
instrument DTOs and canonical light-path DTOs. It must not import
scripts.dashboard_builder.
"""

from __future__ import annotations

import copy
from typing import Any, Iterable

from scripts.build_context import clean_text
from scripts.dashboard.optical_path_view import build_optical_path_view_dto
from scripts.display_labels import resolve_endpoint_type_label
from scripts.validate import Vocabulary

def vocab_label(vocabulary: Vocabulary, vocab_name: str, term_id: str) -> str:
    """Return a friendly vocabulary label for a canonical ID."""
    term = vocabulary.terms_by_vocab.get(vocab_name, {}).get(term_id)
    return term.label if term else term_id


def normalize_optional_bool(value: Any) -> bool | None:
    """Normalize YAML-style booleans while preserving missing values as None."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "y", "1"}:
            return True
        if normalized in {"false", "no", "n", "0"}:
            return False
    return None


def _fmt_num(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _format_wavelength_label(value: Any) -> str:
    wavelength = _fmt_num(value)
    if not wavelength:
        return ""
    normalized = wavelength.strip().lower()
    if normalized.endswith("nm"):
        return wavelength.strip()
    try:
        float(normalized)
    except (TypeError, ValueError):
        return wavelength.strip()
    return f"{wavelength} nm"


def _bool_display(value: Any) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "—"


def clean_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [cleaned for item in values if (cleaned := clean_text(item))]


def _human_list(items: list[str]) -> str:
    cleaned = [clean_text(item) for item in items if clean_text(item)]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"


def _component_reference(manufacturer: Any, model: Any, fallback: str) -> str:
    manufacturer_text = clean_text(manufacturer)
    model_text = clean_text(model)
    if manufacturer_text and model_text:
        return f"{manufacturer_text} {model_text}"
    if model_text:
        return model_text
    if manufacturer_text:
        return manufacturer_text
    return fallback


def _quarep_value(value: Any) -> str:
    cleaned = clean_text(value)
    return cleaned or "missing (ask staff)"


def _quarep_specs_clause(
    manufacturer: Any,
    model: Any,
    product_code: Any,
    *,
    extras: Iterable[str] | None = None,
) -> str:
    parts = [
        f"Manufacturer: {_quarep_value(manufacturer)}",
        f"Model: {_quarep_value(model)}",
        f"Product code: {_quarep_value(product_code)}",
    ]
    for part in extras or []:
        cleaned = clean_text(part)
        if cleaned:
            parts.append(cleaned)
    return "; ".join(parts)


def _append_quarep_specs(
    sentence: Any,
    manufacturer: Any,
    model: Any,
    product_code: Any,
    *,
    extras: Iterable[str] | None = None,
) -> str:
    base = clean_text(sentence).rstrip()
    if base.endswith('.'):
        base = base[:-1]
    specs = _quarep_specs_clause(manufacturer, model, product_code, extras=extras)
    return f"{base} ({specs})." if base else f"{specs}."


def _inventory_method_extras(item: dict[str, Any]) -> list[str]:
    extras: list[str] = []
    source_meta = item.get("source_metadata") if isinstance(item.get("source_metadata"), dict) else {}
    optical_meta = item.get("optical_element_metadata") if isinstance(item.get("optical_element_metadata"), dict) else {}
    endpoint_meta = item.get("endpoint_metadata") if isinstance(item.get("endpoint_metadata"), dict) else {}

    wavelength = _format_wavelength_label(source_meta.get("wavelength_nm"))
    if wavelength:
        extras.append(f"Wavelength: {wavelength}")
    tunable_min = _fmt_num(source_meta.get("tunable_min_nm"))
    tunable_max = _fmt_num(source_meta.get("tunable_max_nm"))
    if tunable_min and tunable_max:
        extras.append(f"Tunable range: {tunable_min}-{tunable_max} nm")
    power = clean_text(source_meta.get("power"))
    if power:
        extras.append(f"Power: {power}")
    timing = clean_text(source_meta.get("timing_mode"))
    if timing:
        extras.append(f"Timing mode: {timing}")

    center = _fmt_num(optical_meta.get("center_nm"))
    width = _fmt_num(optical_meta.get("width_nm"))
    if center and width:
        extras.append(f"Band: {center}/{width} nm")
    elif center:
        extras.append(f"Center: {center} nm")
    cut_on = _fmt_num(optical_meta.get("cut_on_nm"))
    if cut_on:
        extras.append(f"Cut-on: {cut_on} nm")
    cut_off = _fmt_num(optical_meta.get("cut_off_nm"))
    if cut_off:
        extras.append(f"Cut-off: {cut_off} nm")

    def _band_summary(bands: Any, label: str) -> str:
        summaries: list[str] = []
        for band in bands if isinstance(bands, list) else []:
            if not isinstance(band, dict):
                continue
            band_center = _fmt_num(band.get("center_nm"))
            band_width = _fmt_num(band.get("width_nm"))
            if band_center and band_width:
                summaries.append(f"{band_center}/{band_width} nm")
            elif band_center:
                summaries.append(f"{band_center} nm")
        return f"{label}: {', '.join(summaries)}" if summaries else ""

    for label, key in (("Bands", "bands"), ("Transmission", "transmission_bands"), ("Reflection", "reflection_bands")):
        summary = _band_summary(optical_meta.get(key), label)
        if summary:
            extras.append(summary)

    collection_min = _fmt_num(endpoint_meta.get("collection_min_nm") or endpoint_meta.get("min_nm"))
    collection_max = _fmt_num(endpoint_meta.get("collection_max_nm") or endpoint_meta.get("max_nm"))
    if collection_min and collection_max:
        extras.append(f"Collection range: {collection_min}-{collection_max} nm")
    channel_name = clean_text(endpoint_meta.get("channel_name"))
    if channel_name:
        extras.append(f"Channel: {channel_name}")

    return extras


def _spec_lines(*pairs: tuple[str, Any]) -> list[str]:
    lines: list[str] = []
    for label, raw_value in pairs:
        if raw_value in (None, "", [], {}):
            continue
        lines.append(f"**{label}:** {raw_value}")
    return lines


def _vocab_display(vocabulary: Vocabulary, vocab_name: str, value: Any) -> str:
    raw = clean_text(value)
    if not raw:
        return ""
    return vocab_label(vocabulary, vocab_name, raw)


def _objective_display_label(vocabulary: Vocabulary, obj: dict[str, Any]) -> str:
    model = clean_text(obj.get("model"))
    instance_name = clean_text(obj.get("name"))
    mag = _fmt_num(obj.get("magnification") or obj.get("mag"))
    na = _fmt_num(obj.get("numerical_aperture") or obj.get("na"))
    immersion = _vocab_display(vocabulary, "objective_immersion", obj.get("immersion"))
    identity_label = instance_name or model
    parts = [identity_label, f"{mag}x/{na}" if mag and na else f"{mag}x" if mag else "", immersion.upper() if immersion else ""]
    return " ".join(part for part in parts if part).strip() or identity_label or "Objective"


def build_objective_dto(vocabulary: Vocabulary, obj: dict[str, Any]) -> dict[str, Any]:
    manufacturer = clean_text(obj.get("manufacturer"))
    model = clean_text(obj.get("model"))
    product_code = clean_text(obj.get("product_code"))
    immersion = _vocab_display(vocabulary, "objective_immersion", obj.get("immersion"))
    correction = _vocab_display(vocabulary, "objective_corrections", obj.get("correction") or obj.get("correction_class"))
    mag = _fmt_num(obj.get("magnification") or obj.get("mag"))
    na = _fmt_num(obj.get("numerical_aperture") or obj.get("na"))
    wd = clean_text(obj.get("working_distance") or obj.get("wd"))
    display_label = _objective_display_label(vocabulary, obj)
    method_core = " ".join(part for part in [f"{mag}x/{na}" if mag and na else f"{mag}x" if mag else "", immersion, "objective"] if part).strip()
    objective_reference = _component_reference(manufacturer, model, "objective")
    method_meta = ", ".join(part for part in [objective_reference, product_code] if part)
    method_sentence = (
        f"Images were acquired using a {method_core} ({method_meta})."
        if method_core and method_meta
        else f"Images were acquired using a {method_core}." if method_core
        else ""
    )
    method_sentence = _append_quarep_specs(method_sentence, manufacturer, model, product_code)
    spec_lines = _spec_lines(
        ("Model", model),
        ("Magnification / NA", f"`{mag}x/{na}`" if mag and na else None),
        ("Immersion", immersion),
        ("Correction", correction),
        ("Working distance", f"`{wd}`" if wd else None),
        ("Product code", f"`{product_code}`" if product_code else None),
        ("AFC compatible", _bool_display(obj.get("afc_compatible") if "afc_compatible" in obj else obj.get("afc")) if (obj.get("afc_compatible") is not None or obj.get("afc") is not None) else None),
        ("Installed", _bool_display(obj.get("is_installed")) if obj.get("is_installed") is not None else None),
        ("Specialties", ", ".join(clean_string_list(obj.get("specialties"))) or None),
        ("Notes", clean_text(obj.get("notes"))),
    )
    return {
        **copy.deepcopy(obj),
        "display_label": display_label,
        "display_subtitle": manufacturer,
        "spec_lines": spec_lines,
        "method_sentence": method_sentence,
    }


def build_detector_dto(vocabulary: Vocabulary, det: dict[str, Any]) -> dict[str, Any]:
    manufacturer = clean_text(det.get("manufacturer"))
    model = clean_text(det.get("model"))
    product_code = clean_text(det.get("product_code"))
    kind_label = _vocab_display(vocabulary, "detector_kinds", det.get("kind") or det.get("type"))
    route_label = _vocab_display(vocabulary, "optical_routes", det.get("path") or det.get("route"))
    pixel_pitch = _fmt_num(det.get("pixel_pitch_um") or det.get("pixel_size_um"))
    sensor_format = clean_text(det.get("sensor_format_px"))
    binning = clean_text(det.get("binning"))
    bit_depth = _fmt_num(det.get("bit_depth"))
    supports_time_gating = normalize_optional_bool(det.get("supports_time_gating"))
    gating_delay_ns = _fmt_num(det.get("default_gating_delay_ns"))
    gate_width_ns = _fmt_num(det.get("default_gate_width_ns"))
    display_label = " ".join(part for part in [manufacturer, model] if part).strip() or kind_label or "Detector"
    sensor_detail_parts = []
    if sensor_format:
        sensor_detail_parts.append(f"sensor: {sensor_format}")
    if pixel_pitch:
        sensor_detail_parts.append(f"pixel pitch: {pixel_pitch} µm")
    if bit_depth:
        sensor_detail_parts.append(f"{bit_depth}-bit")
    sensor_clause = f" ({', '.join(sensor_detail_parts)})" if sensor_detail_parts else ""
    kind_clause = f" {kind_label}" if kind_label else ""
    base_detection = f"Detection was performed using a {display_label}{kind_clause}{sensor_clause}"
    if supports_time_gating is True:
        gating_phrase = ""
        if gating_delay_ns and gate_width_ns:
            gating_phrase = f" using default gating delay {gating_delay_ns} ns and gate width {gate_width_ns} ns"
        elif gating_delay_ns:
            gating_phrase = f" using default gating delay {gating_delay_ns} ns"
        elif gate_width_ns:
            gating_phrase = f" using default gate width {gate_width_ns} ns"
        method_sentence = f"{base_detection}, configured for time-gated acquisition{gating_phrase}."
    else:
        method_sentence = f"{base_detection}."
    method_sentence = _append_quarep_specs(method_sentence, manufacturer, model, product_code)
    spec_lines = _spec_lines(
        ("Type", kind_label),
        ("Optical route", route_label),
        ("Supports time gating", _bool_display(supports_time_gating) if supports_time_gating is not None else None),
        ("Default gating delay", f"`{gating_delay_ns} ns`" if gating_delay_ns else None),
        ("Default gate width", f"`{gate_width_ns} ns`" if gate_width_ns else None),
        ("Pixel pitch", f"`{pixel_pitch} µm`" if pixel_pitch else None),
        ("Sensor format", f"`{sensor_format}`" if sensor_format else None),
        ("Binning", f"`{binning}`" if binning else None),
        ("Bit depth", f"`{bit_depth}`" if bit_depth else None),
        ("QE peak", f"`{_fmt_num(det.get('qe_peak_pct'))}%`" if det.get("qe_peak_pct") not in (None, "") else None),
        ("Read noise", f"`{_fmt_num(det.get('read_noise_e'))} e-`" if det.get("read_noise_e") not in (None, "") else None),
        ("Product code", f"`{product_code}`" if product_code else None),
        ("Notes", clean_text(det.get("notes"))),
    )
    return {
        **copy.deepcopy(det),
        "display_label": display_label,
        "display_subtitle": kind_label,
        "kind_label": kind_label,
        "route_label": route_label,
        "spec_lines": spec_lines,
        "method_sentence": method_sentence,
    }


def build_light_source_dto(vocabulary: Vocabulary, src: dict[str, Any]) -> dict[str, Any]:
    raw_timing_mode = clean_text(src.get("timing_mode")).lower()

    normalized_role = clean_text(src.get("role")).lower()

    normalized_timing_mode = raw_timing_mode

    manufacturer = clean_text(src.get("manufacturer"))
    model = clean_text(src.get("model"))
    kind_label = _vocab_display(vocabulary, "light_source_kinds", src.get("kind") or src.get("type"))
    role_label = _vocab_display(vocabulary, "light_source_roles", normalized_role)
    timing_mode_label = _vocab_display(vocabulary, "light_source_timing_modes", normalized_timing_mode)
    route_label = _vocab_display(vocabulary, "optical_routes", src.get("path") or src.get("route"))
    pulse_width_ps = _fmt_num(src.get("pulse_width_ps"))
    repetition_rate_mhz = _fmt_num(src.get("repetition_rate_mhz"))
    depletion_targets_nm = [_fmt_num(item) for item in (src.get("depletion_targets_nm") or []) if _fmt_num(item)] if isinstance(src.get("depletion_targets_nm"), list) else []
    wavelength = _fmt_num(src.get("wavelength_nm") or src.get("wavelength"))
    wavelength_label = _format_wavelength_label(src.get("wavelength_nm") or src.get("wavelength"))
    technology = clean_text(src.get("technology"))
    product_code = clean_text(src.get("product_code"))
    power = clean_text(src.get("power"))

    normalized_model = model.lower()
    normalized_wavelength_markers = {
        marker.lower()
        for marker in [f"{wavelength}", f"{wavelength}nm", f"{wavelength} nm"]
        if wavelength
    }
    deduplicated_model = model if normalized_model not in normalized_wavelength_markers else ""

    display_label = " ".join(
        part
        for part in [
            wavelength_label,
            kind_label,
            manufacturer,
            deduplicated_model,
        ]
        if part
    ).strip() or model or kind_label or "Light source"
    tech_power_parts = [part for part in [technology, power] if part]
    tech_power_clause = f" ({', '.join(tech_power_parts)})" if tech_power_parts else ""
    if normalized_role == "depletion":
        pulse_details = []
        if pulse_width_ps:
            pulse_details.append(f"{pulse_width_ps} ps pulse width")
        if repetition_rate_mhz:
            pulse_details.append(f"{repetition_rate_mhz} MHz repetition rate")
        targets_clause = f" targeting {_human_list([f'{item} nm' for item in depletion_targets_nm])}" if depletion_targets_nm else ""
        depletion_descriptor = "pulsed depletion laser" if normalized_timing_mode == "pulsed" else "depletion laser"
        method_sentence = f"STED depletion was delivered by a {depletion_descriptor} ({', '.join(pulse_details)}){targets_clause}." if pulse_details else f"STED depletion was delivered by a {depletion_descriptor}{targets_clause}."
    elif normalized_role == "transmitted_illumination":
        method_sentence = f"Transmitted illumination was provided by {display_label}{tech_power_clause}."
    elif normalized_role == "excitation":
        method_sentence = f"Excitation was provided by {display_label}{tech_power_clause}."
    else:
        method_sentence = f"Light source in use: {display_label}{tech_power_clause}."
    spec_lines = _spec_lines(
        ("Type", kind_label),
        ("Role", role_label),
        ("Optical route", route_label),
        ("Timing mode", timing_mode_label),
        ("Pulse width", f"`{pulse_width_ps} ps`" if pulse_width_ps else None),
        ("Repetition rate", f"`{repetition_rate_mhz} MHz`" if repetition_rate_mhz else None),
        ("Depletion targets", ", ".join(f"`{item} nm`" for item in depletion_targets_nm) if depletion_targets_nm else None),
        ("Technology", technology),
        ("Wavelength", f"`{wavelength_label}`" if wavelength_label else None),
        ("Power", f"`{power}`" if power else None),
        ("Product code", f"`{product_code}`" if product_code else None),
        ("Notes", clean_text(src.get("notes"))),
    )
    return {
        **copy.deepcopy(src),
        "display_label": display_label,
        "display_subtitle": manufacturer,
        "kind_label": kind_label,
        "role_label": role_label,
        "timing_mode_label": timing_mode_label,
        "route_label": route_label,
        "spec_lines": spec_lines,
        "method_sentence": method_sentence,
        "role": normalized_role,
        "timing_mode": normalized_timing_mode,
    }


def build_optical_modulator_dto(vocabulary: Vocabulary, modulator: dict[str, Any]) -> dict[str, Any]:
    modulator_type = clean_text(modulator.get("type"))
    type_label = _vocab_display(vocabulary, "optical_modulator_types", modulator_type)
    supported_masks = [
        _vocab_display(vocabulary, "phase_mask_types", item) or clean_text(item)
        for item in (modulator.get("supported_phase_masks") or [])
        if clean_text(item)
    ] if isinstance(modulator.get("supported_phase_masks"), list) else []
    manufacturer = clean_text(modulator.get("manufacturer"))
    model = clean_text(modulator.get("model"))
    instance_name = clean_text(modulator.get("name"))
    component_reference = _component_reference(manufacturer, model, type_label or "optical modulator")
    display_label = type_label or instance_name or model or "Optical Modulator"
    product_code = clean_text(modulator.get("product_code"))
    method_sentence = f"Beam shaping used {component_reference} optics{f' with {_human_list(supported_masks)} phase mask support' if supported_masks else ''}."
    if modulator_type in {"slm", "phase_plate", "vortex_plate"}:
        method_sentence = f"STED beam shaping was configured with {component_reference}{f' using {_human_list(supported_masks)} phase mask profiles' if supported_masks else ''}."
    method_sentence = _append_quarep_specs(method_sentence, manufacturer, model, product_code)
    return {
        **copy.deepcopy(modulator),
        "display_label": display_label,
        "display_subtitle": manufacturer,
        "spec_lines": _spec_lines(
            ("Type", type_label),
            ("Supported phase masks", ", ".join(f"`{item}`" for item in supported_masks) if supported_masks else None),
            ("Notes", clean_text(modulator.get("notes"))),
        ),
        "method_sentence": method_sentence,
    }


def build_illumination_logic_dto(vocabulary: Vocabulary, logic: dict[str, Any]) -> dict[str, Any]:
    method_id = clean_text(logic.get("method"))
    method_label = _vocab_display(vocabulary, "adaptive_illumination_methods", method_id)
    default_enabled = normalize_optional_bool(logic.get("default_enabled"))
    manufacturer = clean_text(logic.get("manufacturer"))
    model = clean_text(logic.get("model"))
    instance_name = clean_text(logic.get("name"))
    component_reference = _component_reference(manufacturer, model, method_label or "adaptive illumination logic")
    display_label = method_label or instance_name or model or "Illumination Logic"
    product_code = clean_text(logic.get("product_code"))
    method_sentence = f"Adaptive illumination used {component_reference}{', enabled by default' if default_enabled is True else ''}."
    method_sentence = _append_quarep_specs(method_sentence, manufacturer, model, product_code)
    return {
        **copy.deepcopy(logic),
        "display_label": display_label,
        "display_subtitle": "Adaptive illumination" if method_label else "",
        "spec_lines": _spec_lines(
            ("Method", method_label),
            ("Default enabled", _bool_display(default_enabled) if default_enabled is not None else None),
            ("Notes", clean_text(logic.get("notes"))),
        ),
        "method_sentence": method_sentence,
    }


def build_scanner_dto(vocabulary: Vocabulary, scanner: dict[str, Any]) -> dict[str, Any]:
    scanner_type = _vocab_display(vocabulary, "scanner_types", scanner.get("type"))
    manufacturer = clean_text(scanner.get("manufacturer"))
    model = clean_text(scanner.get("model"))
    instance_name = clean_text(scanner.get("name"))
    light_sheet_type = clean_text(scanner.get("light_sheet_type"))
    line_rate = _fmt_num(scanner.get("line_rate_hz"))
    pinhole = _fmt_num(scanner.get("pinhole_um"))
    product_code = clean_text(scanner.get("product_code"))
    spec_lines = _spec_lines(
        ("Type", scanner_type),
        ("Manufacturer", manufacturer),
        ("Model", model),
        ("Product code", f"`{product_code}`" if product_code else None),
        ("Light-sheet type", light_sheet_type),
        ("Line rate", f"`{line_rate} Hz`" if line_rate else None),
        ("Pinhole", f"`{pinhole} µm`" if pinhole else None),
        ("Notes", clean_text(scanner.get("notes"))),
    )
    detail_bits = [f"line rate {line_rate} Hz" if line_rate else "", f"pinhole {pinhole} µm" if pinhole else ""]
    detail_text = ", ".join(bit for bit in detail_bits if bit)
    component_reference = _component_reference(manufacturer, model, f"{scanner_type} scanner" if scanner_type else "scanner")
    method_sentence = (
        f"The microscope used {component_reference} ({detail_text})."
        if scanner_type and scanner_type != "No Scanner" and detail_text
        else f"The microscope used {component_reference}." if scanner_type and scanner_type != "No Scanner"
        else ""
    )
    if method_sentence:
        method_sentence = _append_quarep_specs(method_sentence, manufacturer, model, product_code)
    return {
        **copy.deepcopy(scanner),
        "display_label": scanner_type or instance_name or model or "No Scanner",
        "display_subtitle": " ".join(part for part in [manufacturer, model] if part).strip(),
        "spec_lines": spec_lines,
        "method_sentence": method_sentence,
        "present": bool(scanner_type and scanner_type != "No Scanner"),
    }


def build_environment_dto(environment: dict[str, Any]) -> dict[str, Any]:
    clauses: list[str] = []
    spec_lines = _spec_lines(
        ("Temperature control", _bool_display(environment.get("temperature_control")) if environment.get("temperature_control") is not None else None),
        ("Temperature range", f"`{clean_text(environment.get('temperature_range'))}`" if clean_text(environment.get("temperature_range")) else None),
        ("CO2 control", _bool_display(environment.get("co2_control")) if environment.get("co2_control") is not None else None),
        ("CO2 range", f"`{clean_text(environment.get('co2_range'))}`" if clean_text(environment.get("co2_range")) else None),
        ("O2 control", _bool_display(environment.get("o2_control")) if environment.get("o2_control") is not None else None),
        ("O2 range", f"`{clean_text(environment.get('o2_range'))}`" if clean_text(environment.get("o2_range")) else None),
        ("Humidity control", _bool_display(environment.get("humidity_control")) if environment.get("humidity_control") is not None else None),
        ("Notes", clean_text(environment.get("notes"))),
    )
    if environment.get("temperature_control") is True:
        clauses.append(clean_text(environment.get("temperature_range")) or "controlled temperature")
    if environment.get("co2_control") is True:
        clauses.append(f"{clean_text(environment.get('co2_range'))} CO2" if clean_text(environment.get("co2_range")) else "controlled CO2")
    if environment.get("o2_control") is True:
        clauses.append(f"{clean_text(environment.get('o2_range'))} O2" if clean_text(environment.get("o2_range")) else "controlled O2")
    if environment.get("humidity_control") is True:
        clauses.append("controlled humidity")
    method_sentence = f"Live-cell imaging was performed using an environmental chamber maintaining {_human_list(clauses)}." if clauses else ""
    return {
        **copy.deepcopy(environment),
        "display_label": "Environmental Control",
        "display_subtitle": ", ".join(clauses),
        "spec_lines": spec_lines,
        "method_sentence": method_sentence,
        "present": bool(spec_lines),
    }


def build_stage_dto(vocabulary: Vocabulary, stage: dict[str, Any]) -> dict[str, Any]:
    stage_type = _vocab_display(vocabulary, "stage_types", stage.get("type"))
    manufacturer = clean_text(stage.get("manufacturer"))
    model = clean_text(stage.get("model"))
    step = _fmt_num(stage.get("step_size_um"))
    display_label = " — ".join(part for part in [stage_type, " ".join(part for part in [manufacturer, model] if part).strip()] if part).strip(" —")
    method_sentence = ""
    if clean_text(stage.get("type")).lower() == "z_piezo":
        stage_name = " ".join(part for part in [manufacturer, model] if part).strip()
        method_sentence = f"Z-stacks were acquired using a {stage_name} piezo stage." if stage_name else "Z-stacks were acquired using a piezo stage."
    spec_lines = _spec_lines(
        ("Type", stage_type),
        ("Step size", f"`{step} µm`" if step else None),
    )
    return {
        **copy.deepcopy(stage),
        "display_label": display_label or stage_type or "Stage",
        "display_subtitle": manufacturer,
        "spec_lines": spec_lines,
        "method_sentence": method_sentence,
    }


def build_magnification_changer_dto(changer: dict[str, Any]) -> dict[str, Any]:
    manufacturer = clean_text(changer.get("manufacturer"))
    model = clean_text(changer.get("model"))
    instance_name = clean_text(changer.get("name"))
    magnification = _fmt_num(changer.get("magnification"))
    component_reference = _component_reference(manufacturer, model, "magnification changer")
    display_label = instance_name or model or "Magnification Changer"
    product_code = clean_text(changer.get("product_code"))
    spec_lines = _spec_lines(
        ("Manufacturer", manufacturer),
        ("Model", model),
        ("Product code", f"`{product_code}`" if product_code else None),
        ("Magnification", f"`{magnification}x`" if magnification else None),
        ("Notes", clean_text(changer.get("notes"))),
    )
    method_sentence = (
        f"An intermediate magnification changer ({component_reference}, {magnification}x) was used."
        if component_reference and magnification
        else f"An intermediate magnification changer ({component_reference}) was used."
        if component_reference
        else ""
    )
    method_sentence = _append_quarep_specs(method_sentence, manufacturer, model, product_code)
    return {
        **copy.deepcopy(changer),
        "display_label": display_label,
        "display_subtitle": manufacturer,
        "spec_lines": spec_lines,
        "method_sentence": method_sentence,
    }


def build_software_dto(vocabulary: Vocabulary, software: dict[str, Any]) -> dict[str, Any]:
    role_label = _vocab_display(vocabulary, "software_roles", software.get("role"))
    name = clean_text(software.get("name"))
    version = clean_text(software.get("version"))
    developer = clean_text(software.get("developer"))
    display_label = f"{name} (v{version})" if name and version else name or role_label or "Software"
    method_sentence = ""
    role_id = clean_text(software.get("role")).lower()
    if role_id == "acquisition" and display_label:
        method_sentence = f"Instrument control and image acquisition were performed using {display_label}."
    elif role_id in {"processing", "analysis"} and display_label:
        method_sentence = f"Post-acquisition processing and analysis were performed using {display_label}."
    spec_lines = _spec_lines(
        ("Role", role_label),
        ("Developer", developer),
        ("Version", f"`{version}`" if version else None),
        ("Notes", clean_text(software.get("notes"))),
    )
    return {
        **copy.deepcopy(software),
        "display_label": display_label,
        "display_subtitle": role_label,
        "spec_lines": spec_lines,
        "method_sentence": method_sentence,
    }


def build_hardware_dto(vocabulary: Vocabulary, inst: dict[str, Any], lightpath_dto: dict[str, Any]) -> dict[str, Any]:
    canonical_hardware = ((inst.get("canonical") or {}).get("hardware") or {})
    scanner = canonical_hardware.get("scanner") or {}
    environment = canonical_hardware.get("environment") or {}
    hardware_autofocus = canonical_hardware.get("hardware_autofocus") or {}
    triggering = canonical_hardware.get("triggering") or {}

    autofocus_label = _vocab_display(vocabulary, "autofocus_types", hardware_autofocus.get("type"))
    triggering_label = _vocab_display(vocabulary, "triggering_modes", triggering.get("primary_mode"))

    autofocus_sentence = ""
    if hardware_autofocus.get("is_installed") is True:
        autofocus_sentence = f"Focal drift was minimized using a {autofocus_label or 'hardware autofocus'} system."

    triggering_sentence = ""
    if triggering_label and clean_text(triggering.get("notes")):
        triggering_sentence = f"Acquisition used {triggering_label.lower()} triggering ({clean_text(triggering.get('notes'))})."
    elif triggering_label:
        triggering_sentence = f"Acquisition used {triggering_label.lower()} triggering."

    endpoint_rows = [item for item in (lightpath_dto.get("endpoints") or []) if isinstance(item, dict)] if isinstance(lightpath_dto, dict) else []
    endpoint_renderables = [
        {
            **copy.deepcopy(endpoint),
            "display_label": clean_text(endpoint.get("display_label") or endpoint.get("channel_name") or endpoint.get("name") or endpoint.get("id")) or "Endpoint",
            "display_subtitle": resolve_endpoint_type_label(clean_text(endpoint.get("endpoint_type") or endpoint.get("kind") or endpoint.get("type")), vocabulary) or "Endpoint",
            "spec_lines": _spec_lines(
                ("Endpoint type", resolve_endpoint_type_label(clean_text(endpoint.get("endpoint_type") or endpoint.get("kind") or endpoint.get("type")), vocabulary)),
                ("Source section", clean_text(endpoint.get("source_section"))),
                ("Model", clean_text(endpoint.get("model"))),
                ("Notes", clean_text(endpoint.get("notes"))),
            ),
            "method_sentence": (
                f"Detected or observed light can terminate at {clean_text(endpoint.get('display_label') or endpoint.get('channel_name') or endpoint.get('name') or endpoint.get('id'))}."
                if clean_text(endpoint.get("display_label") or endpoint.get("channel_name") or endpoint.get("name") or endpoint.get("id"))
                else ""
            ),
        }
        for endpoint in endpoint_rows
    ]

    source_rows = [build_light_source_dto(vocabulary, src) for src in (canonical_hardware.get("sources") or canonical_hardware.get("light_sources") or []) if isinstance(src, dict)]

    return {
        "sources": source_rows,
        "light_sources": copy.deepcopy(source_rows),
        "scanner": build_scanner_dto(vocabulary, scanner),
        "detectors": [build_detector_dto(vocabulary, det) for det in canonical_hardware.get("detectors", []) if isinstance(det, dict)],
        "endpoints": endpoint_renderables,
        "optical_modulators": [build_optical_modulator_dto(vocabulary, mod) for mod in canonical_hardware.get("optical_modulators", []) if isinstance(mod, dict)],
        "illumination_logic": [build_illumination_logic_dto(vocabulary, logic) for logic in canonical_hardware.get("illumination_logic", []) if isinstance(logic, dict)],
        "objectives": [build_objective_dto(vocabulary, obj) for obj in canonical_hardware.get("objectives", []) if isinstance(obj, dict)],
        "magnification_changers": [
            build_magnification_changer_dto(item)
            for item in canonical_hardware.get("magnification_changers", [])
            if isinstance(item, dict)
        ],
        "environment": build_environment_dto(environment),
        "stages": [build_stage_dto(vocabulary, stage) for stage in canonical_hardware.get("stages", []) if isinstance(stage, dict)],
        "hardware_autofocus": {
            **copy.deepcopy(hardware_autofocus),
            "display_label": autofocus_label or "Hardware Autofocus",
            "spec_lines": _spec_lines(
                ("Installed", _bool_display(hardware_autofocus.get("is_installed")) if hardware_autofocus.get("is_installed") is not None else None),
                ("Type", autofocus_label),
            ),
            "method_sentence": autofocus_sentence,
            "present": bool(hardware_autofocus),
        },
        "triggering": {
            **copy.deepcopy(triggering),
            "display_label": triggering_label or "Triggering",
            "spec_lines": _spec_lines(
                ("Primary mode", triggering_label),
                ("Notes", clean_text(triggering.get("notes"))),
            ),
            "method_sentence": triggering_sentence,
            "present": bool(triggering_label or clean_text(triggering.get("notes"))),
        },
        "optical_path": build_optical_path_view_dto(lightpath_dto, raw_hardware=canonical_hardware, vocabulary=vocabulary),
    }


def build_instrument_mega_dto(vocabulary: Vocabulary, inst: dict[str, Any], lightpath_dto: dict[str, Any]) -> dict[str, Any]:
    canonical = inst.get("canonical") if isinstance(inst.get("canonical"), dict) else {}
    canonical_instrument = canonical.get("instrument") if isinstance(canonical.get("instrument"), dict) else {}
    canonical_software = canonical.get("software") if isinstance(canonical.get("software"), list) else []
    software_status = clean_text(canonical.get("software_status")).lower()
    canonical_modalities = canonical.get("modalities") if isinstance(canonical.get("modalities"), list) else []
    canonical_modules = canonical.get("modules") if isinstance(canonical.get("modules"), list) else []
    canonical_capabilities = canonical.get("capabilities") if isinstance(canonical.get("capabilities"), dict) else {}

    software_rows = [build_software_dto(vocabulary, sw) for sw in canonical_software if isinstance(sw, dict)]
    hardware_dto = build_hardware_dto(vocabulary, inst, lightpath_dto)
    modalities = [
        {
            "id": modality_id,
            "display_label": _vocab_display(vocabulary, "modalities", modality_id),
            "method_sentence": f"{_vocab_display(vocabulary, 'modalities', modality_id)} imaging was performed." if _vocab_display(vocabulary, 'modalities', modality_id) else "",
        }
        for modality_id in canonical_modalities
    ]
    capabilities = {
        "imaging_modes": [
            {"id": m, "display_label": _vocab_display(vocabulary, "imaging_modes", m)}
            for m in (canonical_capabilities.get("imaging_modes") or [])
        ],
        "contrast_methods": [
            {"id": m, "display_label": _vocab_display(vocabulary, "contrast_methods", m)}
            for m in (canonical_capabilities.get("contrast_methods") or [])
        ],
        "readouts": [
            {"id": m, "display_label": _vocab_display(vocabulary, "measurement_readouts", m)}
            for m in (canonical_capabilities.get("readouts") or [])
        ],
        "workflows": [
            {"id": m, "display_label": _vocab_display(vocabulary, "workflow_tags", m)}
            for m in (canonical_capabilities.get("workflows") or [])
        ],
        "assay_operations": [
            {"id": m, "display_label": _vocab_display(vocabulary, "assay_operations", m)}
            for m in (canonical_capabilities.get("assay_operations") or [])
        ],
        "non_optical": [
            {"id": m, "display_label": _vocab_display(vocabulary, "non_optical_capabilities", m)}
            for m in (canonical_capabilities.get("non_optical") or [])
        ],
    }

    capabilities_flat = []
    seen_capability_ids = set()
    for axis_key in ("imaging_modes", "contrast_methods", "readouts", "workflows", "assay_operations", "non_optical"):
        for entry in capabilities.get(axis_key, []):
            cid = clean_text(entry.get("id"))
            if not cid or cid in seen_capability_ids:
                continue
            seen_capability_ids.add(cid)
            capabilities_flat.append({"id": cid, "display_label": clean_text(entry.get("display_label")) or cid})

    modules = []
    for module in canonical_modules:
        if not isinstance(module, dict):
            continue
        module_id = clean_text(module.get("type") or module.get("name"))
        module_name = clean_text(module.get("display_name")) or _vocab_display(vocabulary, "modules", module_id) or module_id
        manufacturer = clean_text(module.get("manufacturer"))
        model = clean_text(module.get("model"))
        product_code = clean_text(module.get("product_code"))
        notes = clean_text(module.get("notes"))
        provenance = " ".join(part for part in [manufacturer, model] if part).strip()
        modules.append(
            {
                **copy.deepcopy(module),
                "display_label": module_name,
                "display_subtitle": provenance,
                "display_notes": notes,
                "method_sentence": _append_quarep_specs(f"The {module_name} module was used." if module_name else "", manufacturer, model, product_code),
            }
        )

    acquisition_software = next((row["display_label"] for row in software_rows if clean_text(row.get("role")).lower() == "acquisition" and clean_text(row.get("display_label"))), "[MISSING ACQUISITION SOFTWARE NAME AND VERSION]")
    if software_status == "not_applicable":
        acquisition_software = "no acquisition/control software (manual or standalone system)"
    elif software_status == "unknown":
        acquisition_software = "software applicability not yet curated"
    microscope_identity = " ".join(part for part in [clean_text(canonical_instrument.get("manufacturer")), clean_text(canonical_instrument.get("model"))] if part).strip()
    stand = clean_text(canonical_instrument.get("stand_orientation"))
    stand_label = _vocab_display(vocabulary, "stand_orientations", stand) if stand else stand
    base_sentence = f"Images were acquired using the {microscope_identity} {stand_label.lower()} microscope, controlled by {acquisition_software}." if microscope_identity and stand_label else f"Images were acquired using the {microscope_identity} microscope, controlled by {acquisition_software}."
    route_contract = (
        hardware_dto["optical_path"].get("authoritative_route_contract")
        if isinstance(hardware_dto["optical_path"].get("authoritative_route_contract"), dict)
        else {}
    )
    route_rows = route_contract.get("routes") if isinstance(route_contract.get("routes"), list) else []

    def _route_optics_quarep_recommendation(routes: list[dict[str, Any]]) -> tuple[bool, str]:
        if not routes:
            return (
                True,
                "[PLEASE VERIFY: Route-specific optical selections are missing; report each filter, dichroic, splitter, and modulator (manufacturer + model/catalog number) used for acquisition].",
            )

        saw_any_route_facts = False
        saw_incomplete_or_unsupported = False
        saw_unresolved_selectors = False
        for route in routes:
            if not isinstance(route, dict):
                continue
            route_facts = route.get("route_optical_facts") if isinstance(route.get("route_optical_facts"), dict) else {}
            fact_rows = []
            for key in (
                "selected_or_selectable_sources",
                "selected_or_selectable_excitation_filters",
                "selected_or_selectable_dichroics",
                "selected_or_selectable_emission_filters",
                "selected_or_selectable_splitters",
                "selected_or_selectable_endpoints",
                "selected_or_selectable_modulators",
                "selected_or_selectable_branch_selectors",
            ):
                value = route_facts.get(key)
                if isinstance(value, list):
                    fact_rows.extend(item for item in value if isinstance(item, dict))

            if fact_rows:
                saw_any_route_facts = True

            for row in fact_rows:
                if row.get("_cube_incomplete") or row.get("_unsupported_spectral_model"):
                    saw_incomplete_or_unsupported = True
                selection_state = clean_text(row.get("selection_state")).lower()
                if selection_state in {"unresolved", "selectable"}:
                    saw_unresolved_selectors = True
                if isinstance(row.get("available_positions"), list) and len(row.get("available_positions")) > 1 and not clean_text(row.get("selected_position_key") or row.get("position_key")):
                    saw_unresolved_selectors = True

        if saw_incomplete_or_unsupported:
            return (
                True,
                "[CAVEAT: Some route-specific optics are incomplete or use an unsupported spectral model (for example flattened cubes); report known channel labels/positions and confirm uncertain cube internals].",
            )
        if saw_unresolved_selectors:
            return (
                True,
                "[PLEASE VERIFY: Some route selectors remain unresolved; report the exact selected wheel/turret/splitter positions used for acquisition].",
            )
        if saw_any_route_facts:
            return (False, "")
        return (
            True,
            "[PLEASE VERIFY: Route-specific optical selections are missing; report each filter, dichroic, splitter, and modulator (manufacturer + model/catalog number) used for acquisition].",
        )

    quarep_recommendation_needed, quarep_recommendation_text = _route_optics_quarep_recommendation(route_rows)

    dto = {
        "retired": bool(inst.get("retired")),
        "id": inst.get("id"),
        "display_name": inst.get("display_name"),
        "image_filename": inst.get("image_filename"),
        "url": inst.get("url"),
        "status": copy.deepcopy(inst.get("status") or {}),
        "identity": {
            "id": clean_text(inst.get("id")),
            "display_name": clean_text(inst.get("display_name")),
            "url": clean_text(inst.get("url")),
            "image_filename": clean_text(inst.get("image_filename")),
            "manufacturer": clean_text(canonical_instrument.get("manufacturer")),
            "model": clean_text(canonical_instrument.get("model")),
            "stand_orientation": {
                "id": stand,
                "display_label": stand_label,
            },
            "ocular_availability": {
                "id": clean_text(canonical_instrument.get("ocular_availability")),
                "display_label": _vocab_display(vocabulary, "ocular_availability", canonical_instrument.get("ocular_availability")),
            },
            "year_of_purchase": clean_text(canonical_instrument.get("year_of_purchase")),
            "funding": clean_text(canonical_instrument.get("funding")),
            "location": clean_text(canonical_instrument.get("location")),
        },
        "modalities": modalities,
        "capabilities": capabilities,
        "capabilities_flat": capabilities_flat,
        "modules": modules,
        "software": software_rows,
        "software_status": software_status,
        "software_status_message": (
            "No acquisition/control software — manual or standalone system."
            if software_status == "not_applicable"
            else "Software applicability has not yet been curated."
            if software_status == "unknown"
            else ""
        ),
        "hardware": hardware_dto,
        "llm_context": {
            "hardware_inventory": copy.deepcopy(hardware_dto["optical_path"].get("hardware_inventory") or []),
            "route_summaries": copy.deepcopy(
                (
                    hardware_dto["optical_path"].get("authoritative_route_contract", {})
                    if isinstance(hardware_dto["optical_path"].get("authoritative_route_contract"), dict)
                    else {}
                ).get("routes")
                or []
            ),
        },
        "methods": {
            "base_sentence": base_sentence,
            "environment_sentence": hardware_dto["environment"].get("method_sentence", ""),
            "autofocus_sentence": hardware_dto["hardware_autofocus"].get("method_sentence", ""),
            "triggering_sentence": hardware_dto["triggering"].get("method_sentence", ""),
            "stage_sentences": [stage["method_sentence"] for stage in hardware_dto["stages"] if clean_text(stage.get("method_sentence"))],
            "magnification_changer_sentences": [
                row["method_sentence"]
                for row in hardware_dto["magnification_changers"]
                if clean_text(row.get("method_sentence"))
            ],
            "optical_modulator_sentences": [
                row["method_sentence"]
                for row in hardware_dto["optical_modulators"]
                if clean_text(row.get("method_sentence"))
            ],
            "illumination_logic_sentences": [
                row["method_sentence"]
                for row in hardware_dto["illumination_logic"]
                if clean_text(row.get("method_sentence"))
            ],
            "processing_sentences": [row["method_sentence"] for row in software_rows if clean_text(row.get("method_sentence")) and clean_text(row.get("role")).lower() in {"processing", "analysis"}],
            "quarep_light_path_recommendation_needed": quarep_recommendation_needed,
            "quarep_light_path_recommendation": quarep_recommendation_text,
            "specimen_preparation_recommendation": "[PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)].",
            "acquisition_settings_recommendation": "[PLEASE SPECIFY: Exposure time(s), excitation power(s), detector gain/offset, camera binning, zoom, line/frame averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable].",
            "nyquist_recommendation": "Acquisition parameters should satisfy Nyquist sampling for the selected objective(s) and fluorophore emission profile.",
            "data_deposition_recommendation": "[DATA AVAILABILITY]: The raw microscopy image files (.nd2/.czi/.lif) generated in this study should be deposited in BioImage Archive or Zenodo to support Open Science and reproducibility; include the accession number or DOI in the final manuscript.",
        },
    }
    return dto


def build_dashboard_instrument_view(vocabulary: Vocabulary, inst: dict[str, Any], lightpath_dto: dict[str, Any]) -> dict[str, Any]:
    """Explicitly named dashboard view DTO builder derived from canonical DTOs."""
    return build_instrument_mega_dto(vocabulary, inst, lightpath_dto)
