"""Analyze instrument metadata completeness for audit report generation."""

from __future__ import annotations

from typing import Any
import re

from dashboard_builder import load_instruments


_WAVELENGTH_BAND_PATTERN = re.compile(r"^\d+(?:\.\d+)?/\d+(?:\.\d+)?$")
_NUMERIC_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")


def _wavelength_requires_review(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value <= 0
    if not isinstance(value, str):
        return True
    cleaned = value.strip()
    if not cleaned:
        return False
    if _NUMERIC_PATTERN.fullmatch(cleaned):
        return float(cleaned) <= 0
    return _WAVELENGTH_BAND_PATTERN.fullmatch(cleaned) is None


def _na_requires_review(value: Any) -> bool:
    if value in (None, ""):
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return not (0 < value <= 1.7)
    if isinstance(value, str) and _NUMERIC_PATTERN.fullmatch(value.strip()):
        return not (0 < float(value.strip()) <= 1.7)
    return True


def _is_empty(value: Any) -> bool:
    """Return True when a value should be treated as missing."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, list):
        return len(value) == 0
    return False


def _entry(
    label: str,
    value: Any,
    is_missing: bool | None = None,
    *,
    is_warning: bool = False,
    warning_message: str = "",
    is_optional: bool = False,
) -> dict[str, Any]:
    """Create a template-friendly completeness entry."""
    missing = _is_empty(value) if is_missing is None else is_missing
    normalized_value = "" if value is None else value
    return {
        "label": label,
        "value": normalized_value,
        "is_missing": missing,
        "is_warning": is_warning,
        "warning_message": warning_message,
        "is_optional": is_optional,
    }


def _component_kind(component: dict[str, Any]) -> Any:
    """Extract a component kind using either the ``kind`` or ``type`` field."""
    return component.get("kind") if component.get("kind") is not None else component.get("type")


def analyze_instrument_completeness(instrument: dict[str, Any]) -> dict[str, Any]:
    """Return completeness details for an instrument payload from ``load_instruments``."""
    canonical = instrument.get("canonical") or {}
    hardware = canonical.get("hardware") or {}
    policy = canonical.get("policy") or {}

    # 1. Extract Strict Schema Violations
    missing_required = policy.get("missing_required", [])
    missing_conditional = policy.get("missing_conditional", [])
    
    schema_errors = []
    for req in missing_required:
        schema_errors.append({"level": "Required", "path": req.get("path"), "title": req.get("title")})
    for cond in missing_conditional:
        schema_errors.append({"level": "Conditional", "path": cond.get("path"), "title": cond.get("title")})

    # 2. Build Structural Blocks for the Audit Template
    general = [
        _entry("Display Name", instrument.get("display_name")),
        _entry("Manufacturer", instrument.get("manufacturer")),
        _entry("Model", instrument.get("model")),
        _entry("Stand Orientation", instrument.get("stand_orientation")),
        _entry("Location", instrument.get("location")),
        _entry("Year of Purchase", instrument.get("year_of_purchase"), is_optional=True),
        _entry("Funding", instrument.get("funding"), is_optional=True),
    ]

    modalities = instrument.get("modalities")
    modalities_entries = [_entry("Modalities", modalities)]

    software = instrument.get("software")
    software_entries: list[dict[str, Any]] = []
    if not isinstance(software, list) or len(software) == 0:
        software_entries.append(_entry("Software", software if software is not None else [], True))
    else:
        for idx, software_item in enumerate(software, start=1):
            if not isinstance(software_item, dict):
                software_entries.append(_entry(f"Software {idx}", software_item, True))
                continue
            software_entries.extend(
                [
                    _entry(f"Software {idx} Role", software_item.get("role") or software_item.get("component")),
                    _entry(f"Software {idx} Name", software_item.get("name")),
                    _entry(f"Software {idx} Version", software_item.get("version")),
                    _entry(f"Software {idx} Developer", software_item.get("developer"), is_optional=True),
                ]
            )

    scanner = hardware.get("scanner") or {}
    scanner_entries = [
        _entry("Scanner Type", scanner.get("type")),
        _entry("Scanner Line Rate (Hz)", scanner.get("line_rate_hz")),
        _entry("Scanner Pinhole (µm)", scanner.get("pinhole_um")),
    ]

    objectives = hardware.get("objectives")
    objectives_entries: list[dict[str, Any]] = []
    if not isinstance(objectives, list) or len(objectives) == 0:
        objectives_entries.append(_entry("Objectives", objectives if objectives is not None else [], True))
    else:
        for idx, objective in enumerate(objectives, start=1):
            if not isinstance(objective, dict):
                objectives_entries.append(_entry(f"Objective {idx}", objective, True))
                continue
            
            is_installed_val = objective.get("is_installed")
            if is_installed_val is None:
                installed_text = None
            else:
                installed_text = "Yes" if is_installed_val in (True, "true", "True") else "No"
            
            objectives_entries.extend(
                [
                    _entry(f"Objective {idx} Manufacturer", objective.get("manufacturer")),
                    _entry(f"Objective {idx} Model", objective.get("model")),
                    _entry(f"Objective {idx} Company Code", objective.get("product_code")),
                    _entry(f"Objective {idx} Magnification", objective.get("magnification")),
                    _entry(
                        f"Objective {idx} Numerical Aperture",
                        objective.get("numerical_aperture"),
                        is_warning=_na_requires_review(objective.get("numerical_aperture")),
                        warning_message="NA is missing or non-numeric; verify against manufacturer specs.",
                    ),
                    _entry(f"Objective {idx} Immersion", objective.get("immersion")),
                    _entry(f"Objective {idx} Correction", objective.get("correction")),
                    _entry(f"Objective {idx} Working Distance", objective.get("working_distance"), is_optional=True),
                    _entry(
                        f"Objective {idx} Is Installed", 
                        installed_text,
                    ),
                ]
            )

    filters = hardware.get("filters")
    filter_entries: list[dict[str, Any]] = []
    if not isinstance(filters, list) or len(filters) == 0:
        filter_entries.append(_entry("Filters", filters if filters is not None else [], True))
    else:
        for idx, component in enumerate(filters, start=1):
            if not isinstance(component, dict):
                filter_entries.append(_entry(f"Filter {idx}", component, True))
                continue
            filter_entries.extend(
                [
                    _entry(f"Filter {idx} Manufacturer", component.get("manufacturer")),
                    _entry(f"Filter {idx} Model", component.get("model")),
                    _entry(f"Filter {idx} Wavelength (nm)", component.get("wavelength_nm"), is_optional=True),
                    _entry(f"Filter {idx} Numerical Aperture", component.get("numerical_aperture"), is_optional=True),
                    _entry(f"Filter {idx} Working Distance", component.get("working_distance"), is_optional=True),
                ]
            )

    splitters = hardware.get("splitters")
    splitter_entries: list[dict[str, Any]] = []
    if not isinstance(splitters, list) or len(splitters) == 0:
        splitter_entries.append(_entry("Splitters", splitters if splitters is not None else [], True))
    else:
        for idx, component in enumerate(splitters, start=1):
            if not isinstance(component, dict):
                splitter_entries.append(_entry(f"Splitter {idx}", component, True))
                continue
            splitter_entries.extend(
                [
                    _entry(f"Splitter {idx} Manufacturer", component.get("manufacturer")),
                    _entry(f"Splitter {idx} Model", component.get("model")),
                    _entry(f"Splitter {idx} Wavelength (nm)", component.get("wavelength_nm"), is_optional=True),
                    _entry(f"Splitter {idx} Numerical Aperture", component.get("numerical_aperture"), is_optional=True),
                    _entry(f"Splitter {idx} Working Distance", component.get("working_distance"), is_optional=True),
                ]
            )

    magnification_changers = hardware.get("magnification_changers")
    magnification_changer_entries: list[dict[str, Any]] = []
    if not isinstance(magnification_changers, list) or len(magnification_changers) == 0:
        magnification_changer_entries.append(
            _entry("Magnification Changers", magnification_changers if magnification_changers is not None else [], True)
        )
    else:
        for idx, component in enumerate(magnification_changers, start=1):
            if not isinstance(component, dict):
                magnification_changer_entries.append(_entry(f"Magnification Changer {idx}", component, True))
                continue
            magnification_changer_entries.extend(
                [
                    _entry(f"Magnification Changer {idx} Manufacturer", component.get("manufacturer")),
                    _entry(f"Magnification Changer {idx} Model", component.get("model")),
                    _entry(
                        f"Magnification Changer {idx} Wavelength (nm)",
                        component.get("wavelength_nm"),
                        is_optional=True,
                    ),
                    _entry(
                        f"Magnification Changer {idx} Numerical Aperture",
                        component.get("numerical_aperture"),
                        is_optional=True,
                    ),
                    _entry(
                        f"Magnification Changer {idx} Working Distance",
                        component.get("working_distance"),
                        is_optional=True,
                    ),
                ]
            )

    light_sources = hardware.get("light_sources")
    light_source_entries: list[dict[str, Any]] = []
    if not isinstance(light_sources, list) or len(light_sources) == 0:
        light_source_entries.append(_entry("Light Sources", light_sources if light_sources is not None else [], True))
    else:
        for idx, source in enumerate(light_sources, start=1):
            if not isinstance(source, dict):
                light_source_entries.append(_entry(f"Light Source {idx}", source, True))
                continue
            light_source_entries.extend(
                [
                    _entry(f"Light Source {idx} Manufacturer", source.get("manufacturer")),
                    _entry(f"Light Source {idx} Model", source.get("model")),
                    _entry(f"Light Source {idx} Kind/Type", _component_kind(source)),
                    _entry(
                        f"Light Source {idx} Wavelength (nm)",
                        source.get("wavelength_nm"),
                        is_warning=_wavelength_requires_review(source.get("wavelength_nm")),
                        warning_message="Wavelength is descriptive; provide numeric value when available.",
                    ),
                    _entry(f"Light Source {idx} Power", source.get("power"), is_optional=True),
                ]
            )

    detectors = hardware.get("detectors")
    modules = instrument.get("modules")
    module_names = {
        module.get("name")
        for module in modules
        if isinstance(module, dict) and module.get("name")
    } if isinstance(modules, list) else set()

    detector_entries: list[dict[str, Any]] = []
    if not isinstance(detectors, list) or len(detectors) == 0:
        if "camera_port" in module_names:
            detector_entries.append(
                _entry("Detector Capabilities", "External Camera Port Available", is_optional=True)
            )
        else:
            detector_entries.append(
                _entry("Detector Capabilities", "Manual Observation Only", is_optional=True)
            )
    else:
        for idx, detector in enumerate(detectors, start=1):
            if not isinstance(detector, dict):
                detector_entries.append(_entry(f"Detector {idx}", detector, True))
                continue
            detector_entries.extend(
                [
                    _entry(f"Detector {idx} Kind/Type", _component_kind(detector)),
                    _entry(f"Detector {idx} Manufacturer", detector.get("manufacturer")),
                    _entry(f"Detector {idx} Model", detector.get("model")),
                    _entry(f"Detector {idx} Pixel Pitch (µm)", detector.get("pixel_pitch_um")),
                    _entry(f"Detector {idx} Sensor Format (px)", detector.get("sensor_format_px"), is_optional=True),
                    _entry(f"Detector {idx} Binning", detector.get("binning"), is_optional=True),
                    _entry(f"Detector {idx} Bit Depth", detector.get("bit_depth"), is_optional=True),
                    _entry(f"Detector {idx} QE Peak (%)", detector.get("qe_peak_pct"), is_optional=True),
                    _entry(f"Detector {idx} Read Noise (e-)", detector.get("read_noise_e"), is_optional=True),
                ]
            )


    def _yes_no(value: Any) -> str | None:
        if value is None:
            return None
        return "Yes" if value is True else "No"

    environment = hardware.get("environment") or {}
    environment_entries = [
        _entry("Temperature Control", _yes_no(environment.get("temperature_control")), is_optional=True),
        _entry("Temperature Range", environment.get("temperature_range"), is_optional=True),
        _entry("CO2 Control", _yes_no(environment.get("co2_control")), is_optional=True),
        _entry("CO2 Range", environment.get("co2_range"), is_optional=True),
        _entry("O2 Control", _yes_no(environment.get("o2_control")), is_optional=True),
        _entry("O2 Range", environment.get("o2_range"), is_optional=True),
        _entry("Humidity Control", _yes_no(environment.get("humidity_control")), is_optional=True),
        _entry("Notes", environment.get("notes"), is_optional=True),
    ]

    stages = hardware.get("stages")
    stages_entries: list[dict[str, Any]] = []
    if not isinstance(stages, list) or len(stages) == 0:
        stages_entries.append(_entry("Stages", stages if stages is not None else [], True, is_optional=True))
    else:
        for idx, stage in enumerate(stages, start=1):
            if not isinstance(stage, dict):
                stages_entries.append(_entry(f"Stage {idx}", stage, True, is_optional=True))
                continue
            stages_entries.extend(
                [
                    _entry(f"Stage {idx} Type", stage.get("type"), is_optional=True),
                    _entry(f"Stage {idx} Manufacturer", stage.get("manufacturer"), is_optional=True),
                    _entry(f"Stage {idx} Model", stage.get("model"), is_optional=True),
                    _entry(f"Stage {idx} Step Size (µm)", stage.get("step_size_um"), is_optional=True),
                ]
            )

    hardware_autofocus = hardware.get("hardware_autofocus") or {}
    autofocus_entries = [
        _entry("Installed", _yes_no(hardware_autofocus.get("is_installed")), is_optional=True),
        _entry("Type", hardware_autofocus.get("type"), is_optional=True),
    ]

    triggering = hardware.get("triggering") or {}
    triggering_entries = [
        _entry("Primary Mode", triggering.get("primary_mode"), is_optional=True),
        _entry("Notes", triggering.get("notes"), is_optional=True),
    ]

    return {
        "schema_errors": schema_errors,
        "general": general,
        "modalities": modalities_entries,
        "software": software_entries,
        "scanner": scanner_entries,
        "objectives": objectives_entries,
        "filters": filter_entries,
        "splitters": splitter_entries,
        "magnification_changers": magnification_changer_entries,
        "light_sources": light_source_entries,
        "detectors": detector_entries,
        "environment": environment_entries,
        "stages": stages_entries,
        "autofocus": autofocus_entries,
        "triggering": triggering_entries,
    }

__all__ = ["load_instruments", "analyze_instrument_completeness"]
