"""Derived dashboard views for validated QC measurement ledgers.

QC YAML remains the authored source of truth. This module only normalizes the
three policy-defined metric sections into a display/trending DTO; it does not
mutate ledgers or promote human measurements to computed metrics.
"""

from __future__ import annotations

import re
from typing import Any


_POSITION_IDS = {
    "at_objective": "at_obj",
    "pre_objective": "pre_obj",
    "fiber_output": "fiber_output",
}

_POSITION_LABELS = {
    "at_objective": "at objective",
    "pre_objective": "pre-objective",
    "fiber_output": "fiber output",
}

_WORD_LABELS = {
    "a": "A",
    "fwhm": "FWHM",
    "h": "h",
    "mw": "mW",
    "nm": "nm",
    "pct": "%",
    "pm": "PM",
    "psf": "PSF",
    "px": "px",
    "r2": "R²",
    "snr": "SNR",
    "x": "X",
    "xy": "XY",
    "y": "Y",
    "z": "Z",
}


def _mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _number_text(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _slug_token(value: Any, fallback: str = "unspecified") -> str:
    raw = _number_text(value).strip().lower()
    raw = raw.replace("µ", "u").replace("%", "pct").replace("²", "2")
    token = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return token or fallback


def _unit_for_display(unit: Any) -> str:
    value = _text(unit)
    return "" if value.lower() == "unitless" else value


def _display_value(value: Any, unit: Any) -> str:
    rendered = _number_text(value)
    rendered_unit = _unit_for_display(unit)
    return f"{rendered} {rendered_unit}" if rendered_unit else rendered


def _segment_label(segment: str) -> str:
    words = segment.split("_")
    return " ".join(
        _WORD_LABELS.get(word.lower(), word.capitalize())
        for word in words
        if word
    )


def humanize_metric_id(metric_id: str) -> str:
    """Return a readable fallback label without changing the canonical ID."""
    return " · ".join(_segment_label(segment) for segment in metric_id.split("."))


def _position_parts(laser_inputs: dict[str, Any]) -> tuple[str, str]:
    position = _text(laser_inputs.get("measurement_position"))
    position_id = _POSITION_IDS.get(position, _slug_token(position))
    position_label = _POSITION_LABELS.get(
        position,
        position.replace("_", " ") if position else "unspecified position",
    )
    return position_id, position_label


def _setpoint_parts(value: Any, units: Any) -> tuple[str, str]:
    unit = _text(units)
    value_text = _number_text(value)
    value_token = _slug_token(value)
    if unit == "percent":
        return f"{value_token}pct", f"{value_text}%"
    if unit == "mW_setpoint":
        return f"{value_token}mw_setpoint", f"{value_text} mW setpoint"
    if unit:
        return f"{value_token}{_slug_token(unit)}", f"{value_text} {unit}"
    return value_token, value_text


def _laser_label(laser: Any) -> str:
    value = _text(laser) or _number_text(laser)
    try:
        float(value)
    except (TypeError, ValueError):
        return value or "Unspecified laser"
    return f"{value} nm"


def _metric_entry(
    *,
    metric_id: Any,
    value: Any,
    unit: Any = "",
    details: Any = "",
    metric_class: Any = "",
    source: str,
    label: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(metric_id, str) or not metric_id.strip() or value is None:
        return None

    clean_id = metric_id.strip()
    clean_unit = _text(unit)
    return {
        "metric_id": clean_id,
        "metric_class": _text(metric_class),
        "value": value,
        "unit": clean_unit,
        "details": _text(details),
        "source": source,
        "label": label or humanize_metric_id(clean_id),
        "display_value": _display_value(value, clean_unit),
    }


def _modern_laser_entry(
    measurement: dict[str, Any],
    laser_inputs: dict[str, Any],
    *,
    source: str,
    details: Any = "",
    time_s: Any | None = None,
) -> dict[str, Any] | None:
    laser = measurement.get("laser")
    setpoint = measurement.get("setpoint")
    power = measurement.get("power")
    if laser is None or setpoint is None or power is None:
        return None

    position_id, position_label = _position_parts(laser_inputs)
    position_phrase = (
        position_label if position_label.startswith("at ") else f"at {position_label}"
    )
    setpoint_id, setpoint_label = _setpoint_parts(
        setpoint,
        measurement.get("setpoint_units"),
    )
    power_units = _text(measurement.get("power_units"))
    unit_id = _slug_token(power_units, "value")
    metric_id = (
        f"laser.{position_id}.{_slug_token(laser)}.{setpoint_id}.power_{unit_id}"
    )
    label = (
        f"{_laser_label(laser)} laser power {position_phrase} "
        f"({setpoint_label})"
    )
    if time_s is not None:
        time_id = _slug_token(time_s)
        metric_id = (
            f"laser.{position_id}.{_slug_token(laser)}.{setpoint_id}."
            f"stability_t{time_id}s.power_{unit_id}"
        )
        label += f" at t={_number_text(time_s)} s"

    return _metric_entry(
        metric_id=metric_id,
        metric_class="laser_power",
        value=power,
        unit=power_units,
        details=details,
        source=source,
        label=label,
    )


def _legacy_laser_entry(measurement: dict[str, Any]) -> dict[str, Any] | None:
    wavelength = measurement.get("wavelength_nm")
    power = measurement.get("measured_power_mw")
    if wavelength is None or power is None:
        return None

    location = _text(measurement.get("location"))
    location_id = _slug_token(location)
    location_label = location.replace("_", " ") if location else "unspecified position"
    return _metric_entry(
        metric_id=f"laser.{location_id}.{_slug_token(wavelength)}.power_mw",
        metric_class="laser_power",
        value=power,
        unit="mW",
        details=measurement.get("details"),
        source="Laser input",
        label=f"{_laser_label(wavelength)} laser power at {location_label}",
    )


def build_qc_metric_view(
    payload: dict[str, Any],
    *,
    include_series: bool = True,
) -> list[dict[str, Any]]:
    """Build one provenance-preserving measurement list for dashboard consumers.

    Later sources replace identical metric IDs. This keeps structured laser
    single-point entries from duplicating matching series points, and lets a
    provenance-backed computed value supersede its raw counterpart for display.
    """
    if not isinstance(payload, dict):
        return []

    by_id: dict[str, dict[str, Any]] = {}
    laser_inputs = payload.get("laser_inputs_human")
    laser_inputs = laser_inputs if isinstance(laser_inputs, dict) else {}

    if include_series:
        for series in _mappings(laser_inputs.get("linearity_series")):
            for point in _mappings(series.get("points")):
                measurement = {
                    "laser": series.get("laser"),
                    "setpoint": point.get("setpoint"),
                    "setpoint_units": series.get("setpoint_units"),
                    "power": point.get("power"),
                    "power_units": series.get("power_units"),
                }
                entry = _modern_laser_entry(
                    measurement,
                    laser_inputs,
                    source="Laser linearity input",
                    details=series.get("details"),
                )
                if entry:
                    by_id[entry["metric_id"]] = entry

        for series in _mappings(laser_inputs.get("stability_series")):
            for point in _mappings(series.get("timepoints")):
                measurement = {
                    "laser": series.get("laser"),
                    "setpoint": series.get("setpoint"),
                    "setpoint_units": series.get("setpoint_units"),
                    "power": point.get("power"),
                    "power_units": series.get("power_units"),
                }
                details = _text(series.get("details"))
                sampling = _text(series.get("sampling"))
                if sampling:
                    details = f"{details} Sampling: {sampling}".strip()
                entry = _modern_laser_entry(
                    measurement,
                    laser_inputs,
                    source="Laser stability input",
                    details=details,
                    time_s=point.get("t_s"),
                )
                if entry:
                    by_id[entry["metric_id"]] = entry

    for item in _mappings(payload.get("inputs_human")):
        entry = _metric_entry(
            metric_id=item.get("metric_id"),
            metric_class=item.get("metric_class"),
            value=item.get("value"),
            unit=item.get("unit"),
            details=item.get("details"),
            source="Human input",
        )
        if entry:
            by_id[entry["metric_id"]] = entry

    for measurement in _mappings(laser_inputs.get("single_point_measurements")):
        if "laser" in measurement or "power" in measurement:
            entry = _modern_laser_entry(
                measurement,
                laser_inputs,
                source="Laser input",
                details=measurement.get("details"),
            )
        else:
            entry = _legacy_laser_entry(measurement)
        if entry:
            by_id[entry["metric_id"]] = entry

    for item in _mappings(payload.get("metrics_computed")):
        entry = _metric_entry(
            metric_id=item.get("metric_id"),
            metric_class=item.get("metric_class"),
            value=item.get("value"),
            unit=item.get("unit"),
            details=item.get("details"),
            source="Computed metric",
        )
        if entry:
            by_id[entry["metric_id"]] = entry

    return list(by_id.values())


def build_qc_laser_context_view(payload: dict[str, Any]) -> list[dict[str, str]]:
    """Build dashboard rows for laser measurement setup metadata."""
    laser_inputs = payload.get("laser_inputs_human") if isinstance(payload, dict) else None
    if not isinstance(laser_inputs, dict):
        return []

    rows: list[dict[str, str]] = []

    def add_row(label: str, value: Any) -> None:
        clean_value = _text(value)
        if clean_value:
            rows.append({"label": label, "value": clean_value})

    position = _text(laser_inputs.get("measurement_position"))
    if position:
        add_row("Measurement position", _POSITION_LABELS.get(position, position.replace("_", " ")))
    add_row("Position details", laser_inputs.get("measurement_position_details"))

    power_meter = laser_inputs.get("power_meter")
    if isinstance(power_meter, dict):
        add_row("Power meter", power_meter.get("model"))
        add_row("Power meter serial", power_meter.get("serial"))
        add_row("Calibration due", power_meter.get("calibration_due"))
        integration = power_meter.get("integration_time_s")
        if isinstance(integration, (int, float)) and not isinstance(integration, bool):
            rows.append(
                {
                    "label": "Integration time",
                    "value": f"{_number_text(integration)} s",
                }
            )
        add_row("Power meter notes", power_meter.get("notes"))

    return rows


def metric_raw_lookup(payload: dict[str, Any]) -> dict[str, Any]:
    """Return normalized metric IDs mapped to raw values for charting."""
    return {
        item["metric_id"]: item["value"]
        for item in build_qc_metric_view(payload)
    }


def metric_display_lookup(payload: dict[str, Any]) -> dict[str, str]:
    """Return normalized metric IDs mapped to unit-aware display values."""
    return {
        item["metric_id"]: item["display_value"]
        for item in build_qc_metric_view(payload)
    }


def metric_name_lookup(payload: dict[str, Any]) -> dict[str, str]:
    """Return normalized metric IDs mapped to readable dashboard labels."""
    return {
        item["metric_id"]: item["label"]
        for item in build_qc_metric_view(payload)
    }
