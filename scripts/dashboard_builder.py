"""Build MkDocs Material dashboard pages from YAML ledgers.

Pipeline
--------
- instruments/*.yaml
- qc/sessions/**.yaml
- maintenance/events/**.yaml

Produces:
- dashboard_docs/index.md (fleet)
- dashboard_docs/status.md (system health)
- dashboard_docs/instruments/<instrument_id>/index.md (overview)
- dashboard_docs/instruments/<instrument_id>/history.md
- dashboard_docs/events/<instrument_id>/<event_id>.md
- mkdocs.yml (auto-generated)

The builder is intentionally deterministic: same inputs -> same output tree.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import sys
from html import escape
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate import (
    DEFAULT_ALLOWED_RECORD_TYPES,
    Vocabulary,
    build_instrument_completeness_report,
    load_policy,
    print_validation_report,
    validate_event_ledgers,
    validate_instrument_ledgers,
)
from scripts.light_path_parser import generate_virtual_microscope_payload

import yaml
from jinja2 import Environment, FileSystemLoader

METRIC_NAMES: dict[str, str] = {
    "laser.488.linearity_r2": "Laser Linearity 488nm (R²)",
    "laser.488.stability_long_delta_pct": "Laser Stability 488nm (Δ%)",
    "psf.60x_oil.525.fwhm_xy_max_nm": "PSF XY Max FWHM (60x Oil, 525nm)",
    "psf.60x_oil.525.fwhm_xy_min_nm": "PSF XY Min FWHM (60x Oil, 525nm)",
    "psf.60x_oil.525.fwhm_z_nm": "PSF Z FWHM (60x Oil, 525nm)",
    "chromatic_shift.60x_oil.561_to_488.dist_nm": "Chromatic Shift 561→488 (60x Oil, nm)",
    "stage.repeatability_sigma_x_nm": "Stage Repeatability σX (nm)",
    "stage.repeatability_sigma_y_nm": "Stage Repeatability σY (nm)",

    # Legacy metric IDs kept for backward compatibility in older ledgers.
    "psf.fwhm_x_um": "PSF Lateral FWHM X (µm)",
    "psf.fwhm_y_um": "PSF Lateral FWHM Y (µm)",
    "psf.fwhm_z_um": "PSF Axial FWHM Z (µm)",
    "laser.power_mw_405": "Laser Power: 405nm (mW)",
    "laser.power_mw_488": "Laser Power: 488nm (mW)",
    "laser.power_mw_561": "Laser Power: 561nm (mW)",
    "laser.power_mw_640": "Laser Power: 640nm (mW)",
    "laser.short_term_stability_delta_percent_488": "Laser Stability 488nm (Δ%)",
    "illumination.uniformity_percent": "Illumination Uniformity (%)",
    "detector.dark_noise_electrons": "Detector Dark Noise (e-)",
}


def load_facility_config(repo_root: Path) -> dict[str, Any]:
    """Load repository-level facility branding and copy settings."""
    default_config: dict[str, Any] = {
        "facility": {
            "short_name": "Core Imaging Facility",
            "full_name": "Core Imaging Facility",
            "site_name": "Microscopy Dashboard",
            "public_site_url": "",
            "contact_url": "#",
            "organization_url": "#",
            "acknowledgements": {
                "standard": "",
                "xcelligence_addition": "",
            },
        },
        "branding": {
            "logo": "assets/images/logo.svg",
            "favicon": "assets/images/favicon.svg",
        },
    }

    cfg_path = repo_root / "facility.yaml"
    if not cfg_path.exists():
        return default_config

    loaded = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return default_config

    def merged_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = merged_dict(merged[key], value)
            else:
                merged[key] = value
        return merged

    return merged_dict(default_config, loaded)


def load_vocabularies(vocab_dir: Path) -> dict[str, dict[str, Any]]:
    vocabs: dict[str, dict[str, Any]] = {}
    if not vocab_dir.exists():
        return vocabs
    for yaml_file in vocab_dir.glob("*.yaml"):
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if data and "terms" in data:
                vocabs[yaml_file.stem] = {t["id"]: t for t in data["terms"]}
        except Exception:
            pass
    return vocabs


def json_script_data(payload: Any) -> str:
    """Serialize data safely for embedding inside a <script type="application/json"> tag."""
    return (
        json.dumps(payload, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _collect_known_missing_paths(value: Any, prefix: str = "") -> tuple[list[str], list[str]]:
    known_fields: list[str] = []
    missing_fields: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            child_known, child_missing = _collect_known_missing_paths(child, child_prefix)
            known_fields.extend(child_known)
            missing_fields.extend(child_missing)
        return known_fields, missing_fields

    if isinstance(value, list):
        if not value:
            known_fields.append(prefix)
            return known_fields, missing_fields
        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]"
            child_known, child_missing = _collect_known_missing_paths(child, child_prefix)
            known_fields.extend(child_known)
            missing_fields.extend(child_missing)
        return known_fields, missing_fields

    if value is None:
        missing_fields.append(prefix)
    else:
        known_fields.append(prefix)

    return known_fields, missing_fields


def build_methods_generator_page_config(facility: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    facility_ack = facility.get("acknowledgements", {}) if isinstance(facility.get("acknowledgements"), dict) else {}
    ack_data = {
        "standard": str(facility_ack.get("standard", "")),
        "xcelligence_addition": str(facility_ack.get("xcelligence_addition", "")),
    }

    acknowledgements_path = repo_root / "acknowledgements.yaml"
    if acknowledgements_path.exists():
        ack_loaded = yaml.safe_load(acknowledgements_path.read_text(encoding="utf-8"))
        if isinstance(ack_loaded, dict):
            ack_data = {
                "standard": str(ack_loaded.get("standard", ack_data["standard"])),
                "xcelligence_addition": str(ack_loaded.get("xcelligence_addition", ack_data["xcelligence_addition"])),
            }

    methods_config = facility.get("methods_generator", {}) if isinstance(facility.get("methods_generator"), dict) else {}
    return {
        "output_title": str(methods_config.get("output_title", "Light Microscopy Methods")),
        "instrument_data_url": str(methods_config.get("instrument_data_url", "../assets/instruments_data.json")),
        "acknowledgements": ack_data,
    }


def build_plan_experiments_page_config(facility: dict[str, Any]) -> dict[str, Any]:
    planner_config = facility.get("plan_experiments", {}) if isinstance(facility.get("plan_experiments"), dict) else {}
    facility_short_name = str(facility.get("short_name") or facility.get("full_name") or "Core Imaging Facility")
    facility_contact_url = str(facility.get("contact_url", "#"))
    return {
        "facility_short_name": facility_short_name,
        "facility_contact_url": facility_contact_url,
        "facility_contact_label": str(planner_config.get("contact_button_label", f"Contact {facility_short_name} Staff")),
        "llm_inventory_asset_url": str(planner_config.get("llm_inventory_asset_url", "assets/llm_inventory.json")),
    }


def build_methods_generator_instrument_export(inst: dict[str, Any]) -> dict[str, Any]:
    dto = copy.deepcopy(inst.get("dto") or {})
    dto["methods_generation"] = copy.deepcopy(inst.get("methods_generation") or {})
    return dto


def _display_labels(rows: Any, *, installed_only: bool = False) -> list[str]:
    labels: list[str] = []
    if not isinstance(rows, list):
        return labels
    for row in rows:
        if not isinstance(row, dict):
            continue
        if installed_only and row.get("is_installed") is False:
            continue
        label = clean_text(row.get("display_label") or row.get("name") or row.get("model") or row.get("id"))
        if label:
            labels.append(label)
    return labels



def _build_hardware_focus_summary(dto: dict[str, Any]) -> dict[str, Any]:
    hardware = dto.get("hardware") if isinstance(dto.get("hardware"), dict) else {}
    optical_path = hardware.get("optical_path") if isinstance(hardware.get("optical_path"), dict) else {}
    route_rows = optical_path.get("available_routes") if isinstance(optical_path.get("available_routes"), list) else []
    if not route_rows and isinstance(dto.get("available_routes"), list):
        route_rows = dto.get("available_routes")
    route_labels = [
        clean_text(route.get("label") or route.get("display_label") or route.get("id"))
        for route in route_rows
        if isinstance(route, dict) and clean_text(route.get("label") or route.get("display_label") or route.get("id"))
    ]

    supporting_features: list[str] = []
    environment = hardware.get("environment") if isinstance(hardware.get("environment"), dict) else {}
    if environment.get("present"):
        supporting_features.append("environmental control")
    hardware_autofocus = hardware.get("hardware_autofocus") if isinstance(hardware.get("hardware_autofocus"), dict) else {}
    if hardware_autofocus.get("present"):
        supporting_features.append("hardware autofocus")
    triggering = hardware.get("triggering") if isinstance(hardware.get("triggering"), dict) else {}
    if triggering.get("present"):
        supporting_features.append("hardware triggering")
    if _display_labels(hardware.get("optical_modulators")):
        supporting_features.append("optical modulation")
    if _display_labels(hardware.get("illumination_logic")):
        supporting_features.append("adaptive illumination")
    if _display_labels(hardware.get("magnification_changers")):
        supporting_features.append("magnification changer")

    completeness = dto.get("inventory_completeness") if isinstance(dto.get("inventory_completeness"), dict) else {}
    policy_missing_required = completeness.get("policy_missing_required") if isinstance(completeness.get("policy_missing_required"), list) else []
    policy_missing_conditional = completeness.get("policy_missing_conditional") if isinstance(completeness.get("policy_missing_conditional"), list) else []
    caveat_titles = [
        clean_text(entry.get("title") or entry.get("path"))
        for entry in [*policy_missing_required, *policy_missing_conditional]
        if isinstance(entry, dict) and clean_text(entry.get("title") or entry.get("path"))
    ]

    return {
        "modality_labels": _display_labels(dto.get("modalities")),
        "route_labels": route_labels,
        "installed_objective_labels": _display_labels(hardware.get("objectives"), installed_only=True),
        "light_source_labels": _display_labels(hardware.get("light_sources")),
        "detector_labels": _display_labels(hardware.get("detectors")),
        "supporting_feature_labels": sorted(dict.fromkeys(supporting_features)),
        "planning_caveat_labels": caveat_titles[:8],
        "status": copy.deepcopy(dto.get("status") or {}),
    }



def build_llm_inventory_payload(facility: dict[str, Any], instruments: list[dict[str, Any]]) -> dict[str, Any]:
    llm_payload = {
        "facility_name": str(facility.get("short_name") or facility.get("full_name") or "Core Imaging Facility"),
        "facility_contact_url": str(facility.get("contact_url", "")),
        "public_site_url": str(facility.get("public_site_url", "")),
        "policy": {
            "intent": "LLM-safe experiment planning inventory",
            "grounding_requirement": "Only use fields explicitly present in this JSON file.",
            "llm_usage_note": "Use hardware_focus_summary for quick screening, but cite raw hardware fields when recommending routes, optics, sources, and detectors.",
            "do_not_infer_constraints": [
                "Do not invent hardware specifications, accessories, wavelengths, objectives, detector performance, or automation features that are not explicitly listed.",
                "Treat null values and listed missing fields as unknown. Unknown does not mean available.",
                "When required details are missing, ask follow-up questions or clearly state uncertainty.",
            ],
        },
        "active_microscopes": [],
    }

    for inst in instruments:
        dto = copy.deepcopy(inst["dto"])
        known_fields, missing_fields = _collect_known_missing_paths(dto)
        policy = ((inst.get("canonical") or {}).get("policy") or {}) if isinstance(inst, dict) else {}
        dto["inventory_completeness"] = {
            "known_fields": sorted(known_fields),
            "missing_fields": sorted(missing_fields),
            "known_field_count": len(known_fields),
            "missing_field_count": len(missing_fields),
            "policy_missing_required": copy.deepcopy(policy.get("missing_required") or []),
            "policy_missing_conditional": copy.deepcopy(policy.get("missing_conditional") or []),
            "alias_fallbacks": copy.deepcopy(policy.get("alias_fallbacks") or []),
            "uncertainty_note": "Missing fields are unknown and must not be assumed.",
        }
        dto["hardware_focus_summary"] = _build_hardware_focus_summary(dto)
        llm_payload["active_microscopes"].append(dto)

    return llm_payload


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




def _normalized_light_source_payload(light_source: dict[str, Any], get_val: Any) -> dict[str, Any]:
    return {
        "kind": get_val(light_source, "kind", "type"),
        "manufacturer": get_val(light_source, "manufacturer"),
        "model": get_val(light_source, "model"),
        "technology": get_val(light_source, "technology"),
        "wavelength_nm": get_val(light_source, "wavelength_nm", "wavelength"),
        "width_nm": get_val(light_source, "width_nm", "bandwidth_nm"),
        "tunable_min_nm": get_val(light_source, "tunable_min_nm"),
        "tunable_max_nm": get_val(light_source, "tunable_max_nm"),
        "simultaneous_lines_max": get_val(light_source, "simultaneous_lines_max"),
        "power": get_val(light_source, "power"),
        "path": get_val(light_source, "path"),
        "role": get_val(light_source, "role"),
        "timing_mode": get_val(light_source, "timing_mode"),
        "pulse_width_ps": get_val(light_source, "pulse_width_ps"),
        "repetition_rate_mhz": get_val(light_source, "repetition_rate_mhz"),
        "depletion_targets_nm": get_val(light_source, "depletion_targets_nm"),
        "notes": get_val(light_source, "notes"),
        "url": get_val(light_source, "url"),
    }


def _normalized_detector_payload(detector: dict[str, Any], get_val: Any) -> dict[str, Any]:
    return {
        "id": get_val(detector, "id"),
        "kind": get_val(detector, "kind", "type"),
        "manufacturer": get_val(detector, "manufacturer"),
        "model": get_val(detector, "model"),
        "channel_name": get_val(detector, "channel_name", "channel", "name"),
        "path": get_val(detector, "path"),
        "pixel_pitch_um": get_val(detector, "pixel_pitch_um", "pixel_size_um"),
        "sensor_format_px": get_val(detector, "sensor_format_px"),
        "binning": get_val(detector, "binning"),
        "bit_depth": get_val(detector, "bit_depth"),
        "qe_peak_pct": get_val(detector, "qe_peak_pct"),
        "read_noise_e": get_val(detector, "read_noise_e"),
        "supports_time_gating": get_val(detector, "supports_time_gating"),
        "default_gating_delay_ns": get_val(detector, "default_gating_delay_ns"),
        "default_gate_width_ns": get_val(detector, "default_gate_width_ns"),
        "collection_min_nm": get_val(detector, "collection_min_nm", "min_nm"),
        "collection_max_nm": get_val(detector, "collection_max_nm", "max_nm"),
        "collection_center_nm": get_val(detector, "collection_center_nm", "channel_center_nm"),
        "collection_width_nm": get_val(detector, "collection_width_nm", "bandwidth_nm"),
        "channel_center_nm": get_val(detector, "channel_center_nm"),
        "bandwidth_nm": get_val(detector, "bandwidth_nm"),
        "min_nm": get_val(detector, "min_nm"),
        "max_nm": get_val(detector, "max_nm"),
        "notes": get_val(detector, "notes"),
        "url": get_val(detector, "url"),
    }

def _iter_yaml_files(base_dir: Path) -> Iterable[Path]:
    if not base_dir.exists() or not base_dir.is_dir():
        return []
    return [p for p in sorted(base_dir.rglob("*")) if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}]


@dataclass
class YamlLoadError:
    path: str
    message: str


def _load_yaml_file(path: Path, load_errors: list[YamlLoadError] | None = None) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(raw)
    except (OSError, yaml.YAMLError) as exc:
        if load_errors is not None:
            load_errors.append(YamlLoadError(path=path.as_posix(), message=str(exc)))
        return None
    return parsed if isinstance(parsed, dict) else None


def _print_yaml_error_report(load_errors: list[YamlLoadError]) -> None:
    if not load_errors:
        return

    unique_errors: list[YamlLoadError] = []
    seen: set[tuple[str, str]] = set()
    for err in load_errors:
        key = (err.path, err.message)
        if key in seen:
            continue
        seen.add(key)
        unique_errors.append(err)

    print("\nYAML load failures detected:", file=sys.stderr)
    for index, err in enumerate(unique_errors, start=1):
        print(f"  {index}. {err.path}", file=sys.stderr)
        print(f"     {err.message}", file=sys.stderr)
    print(f"\nTotal YAML failures: {len(unique_errors)}", file=sys.stderr)


def _print_agent_fix_prompt(load_errors: list[YamlLoadError], validation_issues: list[Any]) -> None:
    """Print an agent-ready remediation prompt when build validation fails."""
    if not load_errors and not validation_issues:
        return

    print("\n=== AGENT_FIX_PROMPT_BEGIN ===", file=sys.stderr)
    print("You are fixing YAML validation/build failures in this repository.", file=sys.stderr)
    print("Tasks:", file=sys.stderr)
    print("1. Repair malformed YAML files reported below so they parse as top-level mappings.", file=sys.stderr)
    print("2. Resolve validation issues while preserving domain intent.", file=sys.stderr)
    print("3. Re-run: python -m scripts.dashboard_builder --strict", file=sys.stderr)
    print("4. Stop only when the command exits 0.", file=sys.stderr)

    if load_errors:
        print("\nYAML load errors:", file=sys.stderr)
        for err in load_errors:
            print(f"- path: {err.path}", file=sys.stderr)
            print(f"  error: {err.message}", file=sys.stderr)

    if validation_issues:
        print("\nValidation issues:", file=sys.stderr)
        for issue in validation_issues:
            code = getattr(issue, "code", "unknown")
            issue_path = getattr(issue, "path", "")
            message = getattr(issue, "message", "")
            print(f"- code: {code}", file=sys.stderr)
            print(f"  path: {issue_path}", file=sys.stderr)
            print(f"  message: {message}", file=sys.stderr)

    print("=== AGENT_FIX_PROMPT_END ===", file=sys.stderr)

def _parse_iso_datetime(raw_value: Any) -> datetime | None:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None

    normalized = raw_value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed


def _timestamp_from_filename(path: Path) -> datetime | None:
    stem = path.stem
    first_chunk = stem.split("_", 1)[0]

    full_ts = first_chunk.replace("Z", "+00:00")
    if "T" in full_ts:
        date_part, time_part = full_ts.split("T", 1)
        if "+" not in time_part and "-" in time_part and time_part.count("-") >= 2:
            time_tokens = time_part.split("-")
            if len(time_tokens) >= 3:
                time_part = ":".join(time_tokens[:3])
                full_ts = f"{date_part}T{time_part}"

    parsed = _parse_iso_datetime(full_ts)
    if parsed:
        return parsed

    try:
        return datetime.strptime(first_chunk, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _extract_log_date(log_entry: dict[str, Any] | None) -> str:
    if not isinstance(log_entry, dict):
        return ""

    for key in ("started_utc", "timestamp_utc", "date"):
        parsed = _parse_iso_datetime(log_entry.get(key))
        if parsed is not None:
            return parsed.date().isoformat()
    return ""


def clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    # Remove common double-decoding artifacts (UTF-8 NBSP rendered as "Â ")
    s = value.replace("\u00c2\u00a0", " ").replace("\u00a0", " ")
    s = s.replace("Â\u00a0", " ").replace("Â ", " ")
    return s.strip()


def clean_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [clean_text(item) for item in value if clean_text(item)]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


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
    model = clean_text(obj.get("model") or obj.get("name"))
    mag = _fmt_num(obj.get("magnification") or obj.get("mag"))
    na = _fmt_num(obj.get("numerical_aperture") or obj.get("na"))
    immersion = _vocab_display(vocabulary, "objective_immersion", obj.get("immersion"))
    parts = [model, f"{mag}x/{na}" if mag and na else f"{mag}x" if mag else "", immersion.upper() if immersion else ""]
    return " ".join(part for part in parts if part).strip() or model or "Objective"


def build_objective_dto(vocabulary: Vocabulary, obj: dict[str, Any]) -> dict[str, Any]:
    manufacturer = clean_text(obj.get("manufacturer"))
    model = clean_text(obj.get("model") or obj.get("name"))
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
    if supports_time_gating is True:
        gating_phrase = ""
        if gating_delay_ns and gate_width_ns:
            gating_phrase = f" using default gating delay {gating_delay_ns} ns and gate width {gate_width_ns} ns"
        elif gating_delay_ns:
            gating_phrase = f" using default gating delay {gating_delay_ns} ns"
        elif gate_width_ns:
            gating_phrase = f" using default gate width {gate_width_ns} ns"
        method_sentence = f"Detection was performed using {display_label}{f' ({kind_label})' if kind_label else ''}, configured for time-gated acquisition{gating_phrase}."
    else:
        method_sentence = f"Detection was performed using {display_label}{f' ({kind_label})' if kind_label else ''}."
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
        ("Notes", clean_text(det.get("notes"))),
    )
    return {
        **copy.deepcopy(det),
        "display_label": display_label,
        "display_subtitle": kind_label,
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
        method_sentence = f"Transmitted illumination was provided by {display_label}."
    elif normalized_role == "excitation":
        method_sentence = f"Excitation was provided by {display_label}."
    else:
        method_sentence = f"Light source in use: {display_label}."
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
        ("Notes", clean_text(src.get("notes"))),
    )
    return {
        **copy.deepcopy(src),
        "display_label": display_label,
        "display_subtitle": manufacturer,
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
    model = clean_text(modulator.get("model") or modulator.get("name"))
    component_reference = _component_reference(manufacturer, model, type_label or "optical modulator")
    display_label = type_label or model or "Optical Modulator"
    method_sentence = f"Beam shaping used {component_reference} optics{f' with {_human_list(supported_masks)} phase mask support' if supported_masks else ''}."
    if modulator_type in {"slm", "phase_plate", "vortex_plate"}:
        method_sentence = f"STED beam shaping was configured with {component_reference}{f' using {_human_list(supported_masks)} phase mask profiles' if supported_masks else ''}."
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
    model = clean_text(logic.get("model") or logic.get("name"))
    component_reference = _component_reference(manufacturer, model, method_label or "adaptive illumination logic")
    display_label = method_label or model or "Illumination Logic"
    method_sentence = f"Adaptive illumination used {component_reference}{', enabled by default' if default_enabled is True else ''}."
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
    model = clean_text(scanner.get("model") or scanner.get("name"))
    light_sheet_type = clean_text(scanner.get("light_sheet_type"))
    line_rate = _fmt_num(scanner.get("line_rate_hz"))
    pinhole = _fmt_num(scanner.get("pinhole_um"))
    spec_lines = _spec_lines(
        ("Type", scanner_type),
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
    return {
        **copy.deepcopy(scanner),
        "display_label": scanner_type or "No Scanner",
        "display_subtitle": " ".join(part for part in [manufacturer, model] if part).strip() or clean_text(scanner.get("notes")),
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
    model = clean_text(changer.get("model") or changer.get("name"))
    magnification = _fmt_num(changer.get("magnification"))
    component_reference = _component_reference(manufacturer, model, "magnification changer")
    display_label = model or "Magnification Changer"
    spec_lines = _spec_lines(
        ("Manufacturer", manufacturer),
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


def _compact_join(parts: Iterable[str]) -> str:
    return ", ".join(part for part in parts if isinstance(part, str) and part.strip())


def _first_component_label(position: Any) -> str:
    if not isinstance(position, dict):
        return ""
    linked = position.get("linked_components") if isinstance(position.get("linked_components"), dict) else {}
    if linked:
        labels = []
        for key in ("excitation_filter", "dichroic", "emission_filter"):
            label = clean_text(((linked.get(key) or {}).get("label")))
            if label:
                labels.append(label)
        if labels:
            return " / ".join(labels)
    return clean_text(position.get("display_label") or position.get("label") or position.get("name"))


def _mechanism_preview(mechanisms: Any) -> tuple[int, list[str]]:
    if not isinstance(mechanisms, list):
        return 0, []
    previews: list[str] = []
    total_positions = 0
    for mechanism in mechanisms:
        if not isinstance(mechanism, dict):
            continue
        positions = mechanism.get("positions")
        if isinstance(positions, dict):
            total_positions += len(positions)
            iterable = [positions[key] for key in sorted(positions)]
        elif isinstance(positions, list):
            total_positions += len(positions)
            iterable = positions
        else:
            iterable = []
        for position in iterable:
            label = _first_component_label(position)
            if label and label not in previews:
                previews.append(label)
            if len(previews) >= 4:
                break
        if len(previews) >= 4:
            break
    return total_positions, previews[:4]


def _terminal_summary(terminal: dict[str, Any]) -> str:
    endpoint_type = clean_text(terminal.get("endpoint_type") or terminal.get("type") or terminal.get("kind")).replace("_", " ").title()
    route_text = ", ".join(terminal.get("routes") or []) if isinstance(terminal.get("routes"), list) else clean_text(terminal.get("path"))
    return _compact_join([endpoint_type, route_text])


def _svg_text(text: str, limit: int = 32) -> str:
    value = clean_text(text)
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def _build_static_light_path_graph(lightpath_dto: dict[str, Any], raw_hardware: dict[str, Any] | None = None) -> dict[str, Any]:
    stages = lightpath_dto.get("stages") if isinstance(lightpath_dto, dict) else {}
    splitters_raw = lightpath_dto.get("splitters") if isinstance(lightpath_dto, dict) else []
    terminals_raw = lightpath_dto.get("terminals") if isinstance(lightpath_dto, dict) else []
    light_sources_raw = lightpath_dto.get("light_sources") if isinstance(lightpath_dto, dict) else []
    raw_hardware = raw_hardware or {}
    raw_light_path = raw_hardware.get("light_path") if isinstance(raw_hardware.get("light_path"), dict) else {}

    graph_nodes: list[dict[str, Any]] = []
    ordered_nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    def add_node(node_key: str, title: str, category: str, yaml_path: str, items: list[str] | None = None, notes: str = "", xcol: int = 0, y: int = 220) -> dict[str, Any]:
        node = {
            "key": node_key,
            "title": title,
            "category": category,
            "yaml_path": yaml_path,
            "items": items or [],
            "notes": notes,
            "xcol": xcol,
            "y": y,
        }
        ordered_nodes.append(node)
        return node

    column = 0
    sources_preview: list[str] = []
    source_count = 0
    if isinstance(light_sources_raw, list):
        for source_group in light_sources_raw:
            if not isinstance(source_group, dict):
                continue
            positions = source_group.get("positions")
            if isinstance(positions, dict):
                source_count += len(positions)
                for slot in sorted(positions):
                    label = clean_text((positions.get(slot) or {}).get("display_label") or (positions.get(slot) or {}).get("label"))
                    if label and label not in sources_preview:
                        sources_preview.append(label)
                    if len(sources_preview) >= 4:
                        break
    if source_count:
        add_node(
            "sources",
            "Illumination Sources",
            "source",
            "hardware.light_sources",
            items=sources_preview[:4],
            notes=f"{source_count} installed source{'s' if source_count != 1 else ''}",
            xcol=column,
        )
        column += 1

    stage_definitions = [
        ("excitation", "Excitation Optics", "hardware.light_path.excitation_mechanisms", "stage"),
        ("cube", "Filter Cubes", "hardware.light_path.cube_mechanisms", "stage"),
        ("dichroic", "Primary Dichroics", "hardware.light_path.dichroic_mechanisms", "stage"),
    ]
    for stage_key, title, yaml_path, category in stage_definitions:
        mechanisms = stages.get(stage_key, []) if isinstance(stages, dict) else []
        total_positions, previews = _mechanism_preview(mechanisms)
        if total_positions:
            add_node(
                stage_key,
                title,
                category,
                yaml_path,
                items=previews,
                notes=f"{len(mechanisms)} mechanism{'s' if len(mechanisms) != 1 else ''}, {total_positions} selectable position{'s' if total_positions != 1 else ''}",
                xcol=column,
            )
            column += 1

    add_node(
        "sample",
        "Objective / Sample Plane",
        "sample",
        "hardware.objectives",
        items=[],
        notes="Physical crossover between excitation delivery and emitted light collection",
        xcol=column,
    )
    column += 1

    emission_mechanisms = stages.get("emission", []) if isinstance(stages, dict) else []
    emission_positions, emission_previews = _mechanism_preview(emission_mechanisms)
    if emission_positions:
        add_node(
            "emission",
            "Emission Optics",
            "stage",
            "hardware.light_path.emission_mechanisms",
            items=emission_previews,
            notes=f"{len(emission_mechanisms)} mechanism{'s' if len(emission_mechanisms) != 1 else ''}, {emission_positions} selectable position{'s' if emission_positions != 1 else ''}",
            xcol=column,
        )
        column += 1

    splitter_nodes: list[dict[str, Any]] = []
    if isinstance(splitters_raw, list):
        for splitter_index, splitter in enumerate(splitters_raw, start=1):
            if not isinstance(splitter, dict):
                continue
            branch_items = []
            for branch in splitter.get("branches", []) if isinstance(splitter.get("branches"), list) else []:
                if not isinstance(branch, dict):
                    continue
                branch_label = clean_text(branch.get("label") or branch.get("name") or branch.get("id"))
                component_label = clean_text(((branch.get("component") or {}).get("label")))
                target_ids = branch.get("target_ids") if isinstance(branch.get("target_ids"), list) else []
                branch_summary = " → ".join(part for part in [branch_label, component_label, ", ".join(target_ids)] if part)
                if branch_summary:
                    branch_items.append(branch_summary)
            node = add_node(
                f"splitter_{splitter_index}",
                clean_text(splitter.get("name")) or f"Splitter {splitter_index}",
                "splitter",
                f"hardware.light_path.splitters[{splitter_index - 1}]",
                items=branch_items[:4],
                notes=(
                    "Explicit branch targets declared"
                    if not splitter.get("branch_selection_required")
                    else "Branch target selection still required at runtime"
                ),
                xcol=column,
            )
            splitter_nodes.append(node)
            column += 1

    terminals: list[dict[str, Any]] = []
    if isinstance(terminals_raw, list):
        for terminal in terminals_raw:
            if isinstance(terminal, dict) and clean_text(terminal.get("id") or terminal.get("name") or terminal.get("display_label")):
                terminals.append(terminal)

    endpoint_column = max(column, 2)
    endpoint_count = len(terminals)
    endpoint_spacing = 102
    endpoint_top = 220 if endpoint_count <= 1 else 90
    terminal_nodes: dict[str, dict[str, Any]] = {}
    for idx, terminal in enumerate(terminals, start=1):
        y = endpoint_top if endpoint_count <= 1 else endpoint_top + (idx - 1) * endpoint_spacing
        endpoint_type = clean_text(terminal.get("endpoint_type") or terminal.get("type") or terminal.get("kind")).lower()
        terminal_nodes[clean_text(terminal.get("id")) or f"terminal_{idx}"] = add_node(
            clean_text(terminal.get("id")) or f"terminal_{idx}",
            clean_text(terminal.get("display_label") or terminal.get("name")) or f"Endpoint {idx}",
            "endpoint-visual" if endpoint_type == "eyepiece" else "endpoint-camera" if endpoint_type == "camera_port" else "endpoint-detector",
            f"hardware.light_path.endpoints[{idx - 1}]" if raw_light_path.get("endpoints") else "hardware.detectors / hardware.light_path.endpoints",
            items=[],
            notes=_terminal_summary(terminal),
            xcol=endpoint_column,
            y=y,
        )

    main_nodes = [node for node in ordered_nodes if node["category"] not in {"endpoint-detector", "endpoint-visual", "endpoint-camera"}]
    for previous, current in zip(main_nodes, main_nodes[1:]):
        edges.append({"from": previous["key"], "to": current["key"], "label": ""})

    branch_anchor = splitter_nodes[-1]["key"] if splitter_nodes else (main_nodes[-1]["key"] if main_nodes else "")
    splitter_lookup = {node["key"]: node for node in splitter_nodes}

    if splitter_nodes:
        for splitter_index, splitter in enumerate(splitters_raw, start=1):
            if not isinstance(splitter, dict):
                continue
            splitter_key = f"splitter_{splitter_index}"
            for branch in splitter.get("branches", []) if isinstance(splitter.get("branches"), list) else []:
                if not isinstance(branch, dict):
                    continue
                label = clean_text(branch.get("label") or branch.get("name") or branch.get("id"))
                targets = branch.get("target_ids") if isinstance(branch.get("target_ids"), list) else []
                if not targets:
                    continue
                for target_id in targets:
                    normalized = clean_text(target_id)
                    if normalized in terminal_nodes:
                        edges.append({"from": splitter_key, "to": normalized, "label": label})
    else:
        for idx, terminal in enumerate(terminals, start=1):
            target_key = clean_text(terminal.get("id")) or f"terminal_{idx}"
            if branch_anchor:
                edges.append({"from": branch_anchor, "to": target_key, "label": clean_text(terminal.get("endpoint_type") or terminal.get("type") or terminal.get("kind"))})

    recommendations: list[str] = []
    schema_notes: list[str] = [
        "Schema already supports graph-native light-path documentation via `hardware.light_path.splitters[].branches[].target_ids` and `hardware.light_path.endpoints[]`. No schema change is required for numbered static graphs.",
    ]

    raw_splitters = raw_light_path.get("splitters") if isinstance(raw_light_path.get("splitters"), list) else []
    if raw_splitters:
        if any(isinstance(splitter, dict) and not isinstance(splitter.get("branches"), list) for splitter in raw_splitters):
            recommendations.append("Migrate legacy splitter definitions that only use `path_1` / `path_2` to explicit `branches[]` entries so each branch can be numbered and routed deterministically.")
        if any(
            isinstance(splitter, dict) and isinstance(splitter.get("branches"), list) and any(
                isinstance(branch, dict) and not (branch.get("target_ids") or branch.get("targets") or branch.get("endpoint_ids") or branch.get("terminal_ids"))
                for branch in splitter.get("branches")
            )
            for splitter in raw_splitters
        ):
            recommendations.append("Add `target_ids` to every splitter branch in YAML. That is what lets the static graph and simulator show exact downstream endpoints without manual branch picking.")
    elif splitters_raw:
        recommendations.append("Declare explicit `hardware.light_path.splitters[].branches[]` in YAML so static graph routing remains deterministic.")

    explicit_endpoints = raw_light_path.get("endpoints") if isinstance(raw_light_path.get("endpoints"), list) else []
    if not explicit_endpoints:
        recommendations.append("Declare `hardware.light_path.endpoints[]` explicitly for eyepieces, camera ports, and detector terminals; topology is not reconstructed when endpoints are missing.")
    else:
        detector_endpoints = [endpoint for endpoint in explicit_endpoints if isinstance(endpoint, dict) and clean_text(endpoint.get("endpoint_type")).lower() == "detector"]
        if isinstance(raw_hardware.get("detectors"), list) and raw_hardware.get("detectors") and not detector_endpoints:
            recommendations.append("Consider adding detector-class endpoints in `hardware.light_path.endpoints[]` even when `hardware.detectors[]` exists, so the static graph can reference every detector branch by a stable endpoint ID.")

    recommendations = list(dict.fromkeys(recommendations))

    for index, node in enumerate(ordered_nodes, start=1):
        node["number"] = index
        if node["items"]:
            item_preview = "; ".join(node["items"][:3])
            if len(node["items"]) > 3:
                item_preview += "; …"
        else:
            item_preview = ""
        downstream = [edge["to"] for edge in edges if edge["from"] == node["key"]]
        downstream_labels = []
        for target_key in downstream:
            target_node = next((candidate for candidate in ordered_nodes if candidate["key"] == target_key), None)
            if target_node:
                downstream_labels.append(target_node["title"])
        graph_nodes.append({
            "number": index,
            "title": node["title"],
            "category": node["category"],
            "yaml_path": node["yaml_path"],
            "item_preview": item_preview,
            "notes": node["notes"],
            "downstream": ", ".join(downstream_labels),
        })

    color_map = {
        "source": ("#e0f2fe", "#0284c7"),
        "stage": ("#ede9fe", "#7c3aed"),
        "sample": ("#fef3c7", "#d97706"),
        "splitter": ("#dcfce7", "#16a34a"),
        "endpoint-detector": ("#fee2e2", "#dc2626"),
        "endpoint-camera": ("#cffafe", "#0891b2"),
        "endpoint-visual": ("#fce7f3", "#db2777"),
    }
    box_w = 168
    box_h = 84
    start_x = 56
    col_gap = 188
    width = max(980, start_x + (endpoint_column + 1) * col_gap + 220)
    endpoint_positions = [node["y"] for node in ordered_nodes if node["category"].startswith("endpoint-")]
    max_y = max(endpoint_positions + [220])
    height = max(420, max_y + 120)

    for node in ordered_nodes:
        node["x"] = start_x + node["xcol"] * col_gap

    node_lookup = {node["key"]: node for node in ordered_nodes}

    svg_parts = [
        f'<svg class="aic-lightpath-graph" viewBox="0 0 {width} {height}" role="img" aria-label="Logical light path graph">',
        '<defs>',
        '<marker id="aic-arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">',
        '<path d="M0,0 L10,3 L0,6 z" fill="#64748b"></path>',
        '</marker>',
        '</defs>',
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="24" fill="#ffffff"></rect>',
    ]

    for edge in edges:
        source = node_lookup.get(edge["from"])
        target = node_lookup.get(edge["to"])
        if not source or not target:
            continue
        start_y = source["y"] + box_h / 2
        end_y = target["y"] + box_h / 2
        start_x_edge = source["x"] + box_w
        end_x_edge = target["x"]
        ctrl_dx = max(48, (end_x_edge - start_x_edge) / 2)
        path = f"M {start_x_edge:.1f} {start_y:.1f} C {start_x_edge + ctrl_dx:.1f} {start_y:.1f}, {end_x_edge - ctrl_dx:.1f} {end_y:.1f}, {end_x_edge:.1f} {end_y:.1f}"
        svg_parts.append(f'<path d="{path}" fill="none" stroke="#94a3b8" stroke-width="3" marker-end="url(#aic-arrow)"></path>')
        if edge.get("label"):
            label_x = (start_x_edge + end_x_edge) / 2
            label_y = min(start_y, end_y) - 10 if abs(end_y - start_y) < 24 else (start_y + end_y) / 2 - 8
            svg_parts.append(f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle" font-size="12" font-weight="600" fill="#475569">{escape(_svg_text(edge["label"], 24))}</text>')

    for node in ordered_nodes:
        fill, stroke = color_map.get(node["category"], ("#f8fafc", "#475569"))
        x = node["x"]
        y = node["y"]
        svg_parts.extend([
            f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="20" fill="{fill}" stroke="{stroke}" stroke-width="2.2"></rect>',
            f'<circle cx="{x + 18}" cy="{y + 18}" r="12" fill="{stroke}"></circle>',
            f'<text x="{x + 18}" y="{y + 22}" text-anchor="middle" font-size="12" font-weight="700" fill="#ffffff">{node["number"]}</text>',
            f'<text x="{x + 40}" y="{y + 24}" font-size="15" font-weight="700" fill="#0f172a">{escape(_svg_text(node["title"], 28))}</text>',
        ])
        note_line = _svg_text(node.get("notes") or "", 34)
        if note_line:
            svg_parts.append(f'<text x="{x + 16}" y="{y + 48}" font-size="12" fill="#334155">{escape(note_line)}</text>')
        item_line = _svg_text(" · ".join(node.get("items") or []), 36)
        if item_line:
            svg_parts.append(f'<text x="{x + 16}" y="{y + 66}" font-size="11" fill="#475569">{escape(item_line)}</text>')

    svg_parts.append('</svg>')

    return {
        "svg": "".join(svg_parts),
        "nodes": graph_nodes,
        "recommendations": recommendations,
        "schema_notes": schema_notes,
    }


def build_optical_path_dto(lightpath_dto: dict[str, Any], raw_hardware: dict[str, Any] | None = None) -> dict[str, Any]:
    stages = lightpath_dto.get("stages") if isinstance(lightpath_dto, dict) else {}
    splitters_raw = lightpath_dto.get("splitters") if isinstance(lightpath_dto, dict) else []
    terminals_raw = (lightpath_dto.get("terminals") or []) if isinstance(lightpath_dto, dict) else []

    filters: list[dict[str, Any]] = []
    splitters: list[dict[str, Any]] = []
    terminals: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []

    for stage_key, stage_title in [
        ("cube", "Filter Cubes"),
        ("excitation", "Excitation Filters"),
        ("dichroic", "Dichroics"),
        ("emission", "Emission Filters"),
    ]:
        mechanisms = stages.get(stage_key, []) if isinstance(stages, dict) else []
        section_items: list[dict[str, Any]] = []

        for mechanism in mechanisms:
            mech_name = clean_text(mechanism.get("name"))
            for pos in mechanism.get("positions", []):
                if not isinstance(pos, dict):
                    continue

                if stage_key == "cube":
                    linked = pos.get("linked_components") or {}
                    ex_label = clean_text(((linked.get("excitation_filter") or {}).get("label")))
                    di_label = clean_text(((linked.get("dichroic") or {}).get("label")))
                    em_label = clean_text(((linked.get("emission_filter") or {}).get("label")))
                    display_label = clean_text(pos.get("label")) or f"{mech_name} slot {pos.get('slot')}"
                    spec_lines = _spec_lines(
                        ("Mechanism", mech_name),
                        ("Slot", pos.get("slot")),
                        ("Excitation", ex_label),
                        ("Dichroic", di_label),
                        ("Emission", em_label),
                        ("Details", clean_text(pos.get("details"))),
                    )
                    method_sentence = (
                        f"The optical path used the {display_label} filter cube "
                        f"(excitation {ex_label}, dichroic {di_label}, emission {em_label})."
                        if display_label and (ex_label or di_label or em_label)
                        else ""
                    )
                else:
                    display_label = clean_text(pos.get("display_label") or pos.get("label"))
                    spec_lines = _spec_lines(
                        ("Mechanism", mech_name),
                        ("Slot", pos.get("slot")),
                        ("Details", clean_text(pos.get("details"))),
                    )
                    method_sentence = (
                        f"The {stage_key} stage used {clean_text(pos.get('label'))}."
                        if clean_text(pos.get("label")) else ""
                    )

                item = {
                    "id": f"{stage_key}_{mechanism.get('id')}_{pos.get('slot')}",
                    "display_label": display_label,
                    "display_subtitle": mech_name,
                    "spec_lines": spec_lines,
                    "method_sentence": method_sentence,
                }
                filters.append(item)
                section_items.append(item)

        if section_items:
            sections.append({
                "id": stage_key,
                "display_label": stage_title,
                "items": section_items,
            })

    for idx, splitter in enumerate(splitters_raw):
        if not isinstance(splitter, dict):
            continue

        positions = ((splitter.get("dichroic") or {}).get("positions") or {})
        dichroic_position = positions.get(1) if isinstance(positions, dict) else {}
        di_label = clean_text((dichroic_position or {}).get("label"))

        path1_positions = ((splitter.get("path1") or {}).get("positions") or {})
        path1_position = path1_positions.get(1) if isinstance(path1_positions, dict) else {}
        p1_label = clean_text((path1_position or {}).get("label"))

        path2_positions = ((splitter.get("path2") or {}).get("positions") or {})
        path2_position = path2_positions.get(1) if isinstance(path2_positions, dict) else {}
        p2_label = clean_text((path2_position or {}).get("label"))

        branch_lines = []
        for branch in splitter.get("branches", []) if isinstance(splitter.get("branches"), list) else []:
            if not isinstance(branch, dict):
                continue
            branch_label = clean_text(branch.get("label")) or clean_text(branch.get("name")) or clean_text(branch.get("id"))
            component_label = clean_text(((branch.get("component") or {}).get("label")))
            targets = branch.get("target_ids") if isinstance(branch.get("target_ids"), list) else []
            target_label = ", ".join(clean_text(target) for target in targets if clean_text(target))
            branch_lines.append(" → ".join(part for part in [branch_label, component_label, target_label] if part))

        name = clean_text(splitter.get("name")) or f"Splitter {idx + 1}"
        splitters.append({
            "id": f"splitter_{idx}",
            "display_label": clean_text(splitter.get("display_label")) or name,
            "display_subtitle": name,
            "spec_lines": _spec_lines(
                ("Dichroic", di_label),
                ("Path 1", p1_label),
                ("Path 2", p2_label),
                ("Branches", " • ".join(branch_lines) if branch_lines else None),
            ),
            "method_sentence": (
                f"Emission was routed through {name} (dichroic {di_label}, path 1 {p1_label}, path 2 {p2_label})."
                if (di_label or p1_label or p2_label or branch_lines) else ""
            ),
        })

    for idx, terminal in enumerate(terminals_raw):
        if not isinstance(terminal, dict):
            continue
        endpoint_type = clean_text(terminal.get("endpoint_type") or terminal.get("type") or terminal.get("kind")).replace("_", " ").title()
        display_label = clean_text(terminal.get("display_label") or terminal.get("name")) or f"Endpoint {idx + 1}"
        item = {
            "id": clean_text(terminal.get("id")) or f"terminal_{idx}",
            "display_label": display_label,
            "display_subtitle": endpoint_type or "Detection Endpoint",
            "spec_lines": _spec_lines(
                ("Endpoint type", endpoint_type),
                ("Detector class", clean_text(terminal.get("detector_class"))),
                ("Routes", ", ".join(terminal.get("routes") or []) if isinstance(terminal.get("routes"), list) else clean_text(terminal.get("path"))),
                ("Details", clean_text(terminal.get("details"))),
            ),
            "method_sentence": (
                f"Detected or observed light could terminate at {display_label} ({endpoint_type.lower()})."
                if endpoint_type else f"Detected or observed light could terminate at {display_label}."
            ),
        }
        terminals.append(item)

    if terminals:
        sections.append({
            "id": "terminals",
            "display_label": "Detection Endpoints",
            "items": terminals,
        })
    else:
        sections.append({
            "id": "terminals",
            "display_label": "Detection Endpoints",
            "items": [
                {
                    "id": "no_explicit_terminals",
                    "display_label": "No explicit detection endpoints declared",
                    "display_subtitle": "Structured graph incomplete",
                    "spec_lines": [
                        "**Action needed:** add hardware.light_path.endpoints[] and/or detector IDs to YAML.",
                    ],
                    "method_sentence": "",
                }
            ],
        })

    renderables = [
        *filters,
        *splitters,
        *terminals,
    ]

    runtime_splitters = copy.deepcopy(lightpath_dto.get("splitters", [])) if isinstance(lightpath_dto, dict) else []
    static_graph = _build_static_light_path_graph(lightpath_dto, raw_hardware=raw_hardware)

    return {
        **copy.deepcopy(lightpath_dto),
        "runtime_splitters": runtime_splitters,
        "filters": filters,
        "splitters": splitters,
        "terminal_renderables": terminals,
        "sections": sections,
        "renderables": renderables,
        "static_graph": static_graph,
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

    return {
        "light_sources": [build_light_source_dto(vocabulary, src) for src in canonical_hardware.get("light_sources", []) if isinstance(src, dict)],
        "scanner": build_scanner_dto(vocabulary, scanner),
        "detectors": [build_detector_dto(vocabulary, det) for det in canonical_hardware.get("detectors", []) if isinstance(det, dict)],
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
        "optical_path": build_optical_path_dto(lightpath_dto, raw_hardware=canonical_hardware),
    }


def build_instrument_mega_dto(vocabulary: Vocabulary, inst: dict[str, Any], lightpath_dto: dict[str, Any]) -> dict[str, Any]:
    canonical = inst.get("canonical") if isinstance(inst.get("canonical"), dict) else {}
    canonical_instrument = canonical.get("instrument") if isinstance(canonical.get("instrument"), dict) else {}
    canonical_software = canonical.get("software") if isinstance(canonical.get("software"), list) else []
    canonical_modalities = canonical.get("modalities") if isinstance(canonical.get("modalities"), list) else []
    canonical_modules = canonical.get("modules") if isinstance(canonical.get("modules"), list) else []

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
    modules = []
    for module in canonical_modules:
        if not isinstance(module, dict):
            continue
        module_name = clean_text(module.get("display_name") or module.get("name"))
        manufacturer = clean_text(module.get("manufacturer"))
        model = clean_text(module.get("model"))
        notes = clean_text(module.get("notes"))
        provenance = " ".join(part for part in [manufacturer, model] if part).strip()
        modules.append(
            {
                **copy.deepcopy(module),
                "display_label": module_name,
                "display_subtitle": provenance,
                "display_notes": notes,
                "method_sentence": f"The {module_name} module was used." if module_name else "",
            }
        )

    acquisition_software = next((row["display_label"] for row in software_rows if clean_text(row.get("role")).lower() == "acquisition" and clean_text(row.get("display_label"))), "[MISSING ACQUISITION SOFTWARE NAME AND VERSION]")
    microscope_identity = " ".join(part for part in [clean_text(canonical_instrument.get("manufacturer")), clean_text(canonical_instrument.get("model"))] if part).strip()
    stand = clean_text(canonical_instrument.get("stand_orientation"))
    stand_label = _vocab_display(vocabulary, "stand_orientations", stand) if stand else stand
    base_sentence = f"Images were acquired using the {microscope_identity} {stand_label.lower()} microscope, controlled by {acquisition_software}." if microscope_identity and stand_label else f"Images were acquired using the {microscope_identity} microscope, controlled by {acquisition_software}."

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
        "modules": modules,
        "software": software_rows,
        "hardware": hardware_dto,
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
            "quarep_light_path_recommendation": "[PLEASE VERIFY: For each filter, dichroic, splitter, and modulator, report manufacturer and model/catalog number when available to align with QUAREP-LiMi hardware reporting recommendations].",
            "specimen_preparation_recommendation": "[PLEASE SPECIFY: Specimen preparation metadata (sample type, labeling strategy, cover glass, and mounting medium)].",
            "acquisition_settings_recommendation": "[PLEASE SPECIFY: Exposure time(s), excitation power(s), detector gain/offset, camera binning, zoom, line/frame averaging, pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable].",
            "nyquist_recommendation": "Acquisition parameters should satisfy Nyquist sampling for the selected objective(s) and fluorophore emission profile.",
            "data_deposition_recommendation": "[DATA AVAILABILITY]: The raw microscopy image files (.nd2/.czi/.lif) generated in this study should be deposited in BioImage Archive or Zenodo to support Open Science and reproducibility; include the accession number or DOI in the final manuscript.",
        },
    }
    return dto


def slugify(value: str) -> str:
    s = value.lower().strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


INSTRUMENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_valid_instrument_id(value: str) -> bool:
    return bool(INSTRUMENT_ID_PATTERN.fullmatch(value))


def strip_empty_values(data: Any) -> Any:
    """Recursively remove empty optional values while preserving False/0."""

    def is_empty(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value == ""
        if isinstance(value, list):
            return len(value) == 0
        if isinstance(value, dict):
            return len(value) == 0
        return False

    if isinstance(data, dict):
        pruned: dict[str, Any] = {}
        for key, value in data.items():
            cleaned = strip_empty_values(value)
            if not is_empty(cleaned):
                pruned[key] = cleaned
        return pruned

    if isinstance(data, list):
        pruned_list = []
        for item in data:
            cleaned = strip_empty_values(item)
            if not is_empty(cleaned):
                pruned_list.append(cleaned)
        return pruned_list

    return data


def normalize_software(raw: Any) -> list[dict[str, str]]:
    """Normalize software metadata to schema-native `software[]` role rows."""
    allowed_roles = {"acquisition", "processing", "analysis", "hardware_control", "other"}
    legacy_role_map = {
        "acquisition": "acquisition",
        "analysis": "analysis",
        "deconvolution": "processing",
        "reconstruction": "processing",
        "post_processing": "processing",
        "flim": "analysis",
        "control": "hardware_control",
        "hardware_control": "hardware_control",
    }

    def normalize_role(value: Any, fallback: str = "other") -> str:
        role = clean_text(value).lower()
        if role in allowed_roles:
            return role
        if role in legacy_role_map:
            return legacy_role_map[role]
        return fallback

    rows: list[dict[str, str]] = []

    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "role": normalize_role(item.get("role") or item.get("component") or item.get("type")),
                    "name": clean_text(item.get("name") or ""),
                    "version": clean_text(item.get("version") or ""),
                    "developer": clean_text(item.get("developer") or item.get("manufacturer") or ""),
                    "notes": clean_text(item.get("notes") or ""),
                    "url": clean_text(item.get("url") or ""),
                }
            )
        cleaned_rows = [strip_empty_values(r) for r in rows]
        return [r for r in cleaned_rows if isinstance(r, dict) and r]

    if isinstance(raw, dict):
        for role_or_name, payload in raw.items():
            normalized_role = normalize_role(role_or_name)
            if isinstance(payload, dict):
                rows.append(
                    {
                        "role": normalized_role,
                        "name": clean_text(payload.get("name") or ""),
                        "version": clean_text(payload.get("version") or ""),
                        "developer": clean_text(payload.get("developer") or payload.get("manufacturer") or ""),
                        "notes": clean_text(payload.get("notes") or ""),
                        "url": clean_text(payload.get("url") or ""),
                    }
                )
            elif isinstance(payload, str):
                rows.append({"role": normalized_role, "name": clean_text(payload), "version": "", "developer": "", "notes": "", "url": ""})
        cleaned_rows = [strip_empty_values(r) for r in rows]
        return [r for r in cleaned_rows if isinstance(r, dict) and r]

    if isinstance(raw, str) and raw.strip():
        cleaned_row = strip_empty_values({"role": "other", "name": clean_text(raw), "version": "", "developer": "", "notes": "", "url": ""})
        return [cleaned_row] if isinstance(cleaned_row, dict) and cleaned_row else []

    return []




def normalize_hardware(raw: Any) -> dict[str, Any]:
    """Normalize hardware into schema-native canonical keys and strip empty values."""
    if not isinstance(raw, dict):
        return {}

    def get_val(data: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in data:
                return data.get(key)
        return None

    hw: dict[str, Any] = {}

    scanner = raw.get("scanner")
    if isinstance(scanner, dict):
        hw["scanner"] = {
            "type": get_val(scanner, "type", "id"),
            "line_rate_hz": get_val(scanner, "line_rate_hz"),
            "pinhole_um": get_val(scanner, "pinhole_um"),
            "light_sheet_type": get_val(scanner, "light_sheet_type"),
            "notes": get_val(scanner, "notes"),
            "url": get_val(scanner, "url"),
        }

    light_sources_raw = raw.get("light_sources")
    if isinstance(light_sources_raw, list):
        hw["light_sources"] = [
            _normalized_light_source_payload(light_source, get_val)
            for light_source in light_sources_raw
            if isinstance(light_source, dict)
        ]

    detectors_raw = raw.get("detectors")
    if isinstance(detectors_raw, list):
        hw["detectors"] = [
            _normalized_detector_payload(detector, get_val)
            for detector in detectors_raw
            if isinstance(detector, dict)
        ]

    objectives_raw = raw.get("objectives")
    if isinstance(objectives_raw, list):
        hw["objectives"] = [
            {
                "id": get_val(objective, "id"),
                "manufacturer": get_val(objective, "manufacturer"),
                "model": get_val(objective, "model", "name"),
                "product_code": get_val(objective, "product_code"),
                "magnification": get_val(objective, "magnification"),
                "numerical_aperture": get_val(objective, "numerical_aperture", "na"),
                "working_distance": get_val(objective, "working_distance", "wd"),
                "immersion": get_val(objective, "immersion"),
                "correction": get_val(objective, "correction", "correction_class"),
                "afc_compatible": get_val(objective, "afc_compatible", "afc"),
                "is_installed": get_val(objective, "is_installed"),
                "specialties": get_val(objective, "specialties"),
                "notes": get_val(objective, "notes"),
                "url": get_val(objective, "url"),
            }
            for objective in objectives_raw
            if isinstance(objective, dict)
        ]

    passthrough_keys = [
        "light_path",
        "filters",
        "splitters",
        "magnification_changers",
        "environment",
        "stages",
        "hardware_autofocus",
        "triggering",
        "optical_modulators",
        "illumination_logic",
    ]
    for key in passthrough_keys:
        if key in raw:
            hw[key] = raw.get(key)

    cleaned = strip_empty_values(hw)
    return cleaned if isinstance(cleaned, dict) else {}


def normalize_instrument_dto(payload: dict[str, Any], source_file: Path, *, retired: bool) -> dict[str, Any] | None:
    """Build canonical instrument DTO used by dashboard templates and exports."""
    inst_section = payload.get("instrument")
    if not isinstance(inst_section, dict):
        inst_section = {}

    display_name = clean_text(inst_section.get("display_name")) or source_file.stem
    raw_instrument_id = inst_section.get("instrument_id")
    if not isinstance(raw_instrument_id, str) or not raw_instrument_id.strip():
        return None

    instrument_id = raw_instrument_id.strip()
    if not is_valid_instrument_id(instrument_id):
        return None

    notes_raw = clean_text(inst_section.get("notes"))

    raw_modules = payload.get("modules") or []
    modules = []
    for m in raw_modules:
        if isinstance(m, dict):
            modules.append(
                {
                    "name": clean_text(m.get("name")),
                    "manufacturer": clean_text(m.get("manufacturer")),
                    "model": clean_text(m.get("model")),
                    "notes": clean_text(m.get("notes")),
                    "url": clean_text(m.get("url")),
                }
            )
        elif isinstance(m, str):
            modules.append({"name": clean_text(m), "manufacturer": "", "model": "", "notes": "", "url": ""})

    modalities = payload.get("modalities")
    if not isinstance(modalities, list):
        modalities = []

    software = strip_empty_values(normalize_software(payload.get("software")))
    raw_hardware = payload.get("hardware") or {}
    if not isinstance(raw_hardware, dict):
        raw_hardware = {}

    legacy_top_level_objectives_used = False
    # DEPRECATED compatibility path: some legacy YAML files declared objectives at top level.
    # Canonical contract location is hardware.objectives; production YAML should migrate.
    if "objectives" not in raw_hardware and isinstance(payload.get("objectives"), list):
        raw_hardware = {**raw_hardware, "objectives": payload.get("objectives")}
        legacy_top_level_objectives_used = True

    hardware = strip_empty_values(normalize_hardware(raw_hardware))
    policy = build_instrument_completeness_report(payload)

    software_roles = ("acquisition", "processing", "analysis", "hardware_control", "other")

    software_by_role: dict[str, dict[str, Any]] = {}
    for role in software_roles:
        role_payload = next(
            (
                sw
                for sw in software
                if isinstance(sw, dict) and clean_text(sw.get("role")).lower() == role
            ),
            {},
        )
        role_name = clean_text(role_payload.get("name"))
        role_version = clean_text(role_payload.get("version"))
        software_by_role[role] = {
            "present": bool(role_payload),
            "name": role_name,
            "version": role_version,
            "is_complete": bool(role_name and role_version),
        }

    missing_entries = [*policy.missing_required, *policy.missing_conditional]
    methods_blockers: list[dict[str, str]] = []
    for entry in missing_entries:
        used_by = entry.get("used_by") if isinstance(entry, dict) else None
        if not isinstance(used_by, list) or "method_generator" not in used_by:
            continue

        path = clean_text(entry.get("path"))
        if not path:
            continue

        role = ""
        if path.startswith("software[") and isinstance(entry, dict):
            role = clean_text(entry.get("role"))

        methods_blockers.append(
            {
                "path": path,
                "title": clean_text(entry.get("title")) or path,
                "role": role,
                "kind": "instrument_metadata",
            }
        )

    methods_generation = {
        "is_blocked": bool(methods_blockers),
        "blockers": methods_blockers,
        "software_by_role": software_by_role,
    }

    canonical = {
        "instrument": {
            "display_name": display_name,
            "instrument_id": instrument_id,
            "manufacturer": clean_text(inst_section.get("manufacturer")),
            "model": clean_text(inst_section.get("model")),
            "year_of_purchase": clean_text(inst_section.get("year_of_purchase")),
            "funding": clean_text(inst_section.get("funding")),
            "stand_orientation": clean_text(inst_section.get("stand_orientation")),
            "ocular_availability": clean_text(inst_section.get("ocular_availability")),
            "location": clean_text(inst_section.get("location")),
            "notes": notes_raw,
            "url": clean_text(inst_section.get("url")),
        },
        "modalities": [clean_text(m) for m in modalities if isinstance(m, str) and clean_text(m)],
        "modules": copy.deepcopy(modules),
        "notes": notes_raw,
        "software": software,
        "hardware": hardware,
        "policy": {
            "sections": policy.sections,
            "missing_required": policy.missing_required,
            "missing_conditional": policy.missing_conditional,
            "alias_fallbacks": policy.alias_fallbacks,
        },
        "provenance": {
            "source_contract": "validated_canonical_yaml",
            "deprecated_compatibility": {
                "top_level_objectives_to_hardware_objectives": legacy_top_level_objectives_used,
            },
        },
    }

    canonical_instrument = canonical["instrument"]
    return {
        "retired": retired,
        "id": instrument_id,
        "display_name": canonical_instrument["display_name"],
        "manufacturer": canonical_instrument["manufacturer"],
        "model": canonical_instrument["model"],
        "year_of_purchase": canonical_instrument["year_of_purchase"],
        "funding": canonical_instrument["funding"],
        "stand_orientation": canonical_instrument["stand_orientation"],
        "ocular_availability": canonical_instrument["ocular_availability"],
        "location": canonical_instrument["location"],
        "notes_raw": notes_raw,
        "notes": notes_raw,
        "modalities": copy.deepcopy(canonical["modalities"]),
        "modules": copy.deepcopy(canonical["modules"]),
        "software": copy.deepcopy(canonical["software"]),
        "image_filename": _discover_image_filename(instrument_id),
        "url": canonical_instrument["url"],
        "canonical": canonical,
        "methods_generation": methods_generation,
    }

def get_all_instrument_logs(
    log_base_dir: str,
    instrument_id: str,
    load_errors: list[YamlLoadError] | None = None,
    preindexed_logs: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    if not instrument_id or not instrument_id.strip():
        return []

    target_id = instrument_id.strip()
    if preindexed_logs is not None:
        return list(preindexed_logs.get(target_id, []))

    return list(index_instrument_logs(log_base_dir, load_errors=load_errors).get(target_id, []))


def index_instrument_logs(
    log_base_dir: str, load_errors: list[YamlLoadError] | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Load and index event logs in a single pass grouped by instrument ID."""

    base_path = Path(log_base_dir)
    grouped_candidates: dict[str, list[tuple[datetime, Path, dict[str, Any]]]] = {}

    for yaml_file in _iter_yaml_files(base_path):
        payload = _load_yaml_file(yaml_file, load_errors=load_errors)
        if payload is None:
            continue

        payload_instrument = payload.get("microscope")
        if not isinstance(payload_instrument, str):
            payload_instrument = payload.get("instrument_id")

        if not isinstance(payload_instrument, str):
            continue

        instrument_id = payload_instrument.strip()
        if not instrument_id:
            continue

        sort_dt = _parse_iso_datetime(payload.get("started_utc"))
        if sort_dt is None:
            sort_dt = _timestamp_from_filename(yaml_file)
        if sort_dt is None:
            sort_dt = datetime.min.replace(tzinfo=timezone.utc)

        grouped_candidates.setdefault(instrument_id, []).append((sort_dt, yaml_file, payload))

    indexed_logs: dict[str, list[dict[str, Any]]] = {}
    for instrument_id, candidates in grouped_candidates.items():
        candidates.sort(key=lambda item: (item[0], item[1].as_posix()))

        indexed_logs[instrument_id] = [
            {"source_path": path.as_posix(), "filename": path.name, "data": payload}
            for _, path, payload in candidates
        ]

    return indexed_logs


def evaluate_instrument_status(
    latest_qc: dict[str, Any] | None, latest_maint: dict[str, Any] | None
) -> dict[str, str]:
    """Status semantics used by fleet/status pages."""

    last_qc_date = _extract_log_date(latest_qc)
    last_maint_date = _extract_log_date(latest_maint)

    maint_status = ""
    maint_reason = ""
    if isinstance(latest_maint, dict):
        raw_maint_status = latest_maint.get("microscope_status_after")
        if isinstance(raw_maint_status, str):
            maint_status = raw_maint_status.strip().lower()

        for key in ("reason_details", "action", "action_details", "reason"):
            value = latest_maint.get(key)
            if isinstance(value, str) and value.strip():
                maint_reason = clean_text(value)
                break

    qc_status = ""
    qc_reason = ""
    if isinstance(latest_qc, dict):
        evaluation = latest_qc.get("evaluation")
        if isinstance(evaluation, dict):
            raw_qc_status = evaluation.get("overall_status")
            if isinstance(raw_qc_status, str):
                qc_status = raw_qc_status.strip().lower()

            results = evaluation.get("results")
            if isinstance(results, list) and results:
                first_result = results[0]
                if isinstance(first_result, dict):
                    msg = first_result.get("message")
                    if isinstance(msg, str) and msg.strip():
                        qc_reason = clean_text(msg)

    if maint_status == "out_of_service" or qc_status == "fail":
        reason = maint_reason or qc_reason or "Out of service"
        return {
            "color": "red",
            "badge": "🔴 Offline",
            "reason": reason,
            "last_qc_date": last_qc_date,
            "last_maint_date": last_maint_date,
        }

    if maint_status == "limited" or qc_status == "warn":
        reason = maint_reason or qc_reason or "Limited operation"
        return {
            "color": "yellow",
            "badge": "🟡 Warning",
            "reason": reason,
            "last_qc_date": last_qc_date,
            "last_maint_date": last_maint_date,
        }

    return {
        "color": "green",
        "badge": "🟢 Online",
        "reason": "Operational",
        "last_qc_date": last_qc_date,
        "last_maint_date": last_maint_date,
    }


def _metric_lookup(metric_entries: Any) -> dict[str, Any]:
    output: dict[str, Any] = {}
    if not isinstance(metric_entries, list):
        return output
    for item in metric_entries:
        if not isinstance(item, dict):
            continue
        metric_id = item.get("metric_id")
        value = item.get("value")
        if isinstance(metric_id, str):
            output[metric_id] = value
    return output


def _build_all_charts_data(qc_logs: list[dict[str, Any]]) -> str:
    all_metrics: set[str] = set()
    for entry in qc_logs:
        payload = entry.get("data")
        if isinstance(payload, dict):
            metrics = _metric_lookup(payload.get("metrics_computed"))
            all_metrics.update(metrics.keys())

    charts: dict[str, Any] = {}
    for metric_id in sorted(all_metrics):
        labels: list[str] = []
        values: list[Any] = []

        for entry in qc_logs:
            payload = entry.get("data")
            if not isinstance(payload, dict):
                continue

            parsed_started = _parse_iso_datetime(payload.get("started_utc"))
            if parsed_started is None:
                continue

            labels.append(parsed_started.strftime("%Y-%m-%d"))
            metrics = _metric_lookup(payload.get("metrics_computed"))
            val = metrics.get(metric_id)
            values.append(val if isinstance(val, (int, float)) else None)

        if any(v is not None for v in values):
            # Format expected by 'charts.js'
            charts[metric_id] = {
                "labels": labels,
                "values": values,
            }

    return json.dumps(charts)


def _discover_image_filename(instrument_id: str) -> str:
    # prefer local jpg/png assets if present
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".svg"):
        candidate = Path("assets/images") / f"{instrument_id}{ext}"
        if candidate.exists():
            return candidate.name
    return "placeholder.svg"




def validated_instrument_selection(instruments_dir: str | Path = "instruments") -> tuple[set[str], list[Any], list[Any]]:
    """Resolve authoritative instrument IDs from the validator for downstream DTO/reporting flows."""
    return validate_instrument_ledgers(instruments_dir=Path(instruments_dir))

def load_instruments(
    instruments_dir: str = "instruments",
    load_errors: list[YamlLoadError] | None = None,
    include_retired: bool = False,
    allowed_instrument_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    base = Path(instruments_dir)
    instruments: list[dict[str, Any]] = []

    for yaml_file in _iter_yaml_files(base):
        # Skip retired instruments unless explicitly requested.
        is_retired = "retired" in yaml_file.parts
        if is_retired != include_retired:
            continue

        payload = _load_yaml_file(yaml_file, load_errors=load_errors)
        if payload is None:
            continue

        normalized = normalize_instrument_dto(payload, yaml_file, retired=is_retired)
        if normalized is None:
            if load_errors is not None:
                load_errors.append(
                    YamlLoadError(
                        path=yaml_file.as_posix(),
                        message="Missing or invalid instrument.instrument_id (must be URL-safe slug).",
                    )
                )
            continue

        if allowed_instrument_ids is not None and normalized["id"] not in allowed_instrument_ids:
            continue

        instruments.append(normalized)

    instruments.sort(key=lambda x: x["id"])
    return instruments


def build_nav(instruments: list[dict[str, Any]], retired_instruments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    microscopes = [{inst["display_name"]: f"instruments/{inst['id']}/index.md"} for inst in instruments]
    retired = [{inst["display_name"]: f"instruments/{inst['id']}/index.md"} for inst in retired_instruments]

    return [
        {"Fleet Overview": "index.md"},
        {"System Health": "status.md"},
        {"Microscopes": microscopes},
        {"Plan Your Experiments": "plan_experiments.md"},
        {"Virtual Microscope": "virtual_microscope.md"},
        {"Methods Generator": "methods_generator.md"},
        {"Vocabulary Dictionary": "vocabulary_dictionary.md"},
        {"Retired Instruments": [{"Overview": "retired/index.md"}, *retired]},
    ]


def _allowed_record_types_from_arg(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return DEFAULT_ALLOWED_RECORD_TYPES

    values = [item.strip() for item in raw.split(",") if item.strip()]
    return tuple(values) if values else DEFAULT_ALLOWED_RECORD_TYPES


def _event_output_instrument(payload: dict[str, Any], fallback_instrument: str) -> str:
    """Return the instrument namespace to use for event doc output/links."""
    microscope = payload.get("microscope")
    if isinstance(microscope, str) and microscope.strip():
        return microscope.strip()
    return fallback_instrument


def main(strict: bool = True, allowed_record_types: tuple[str, ...] = DEFAULT_ALLOWED_RECORD_TYPES) -> int:
    repo_root = Path.cwd()
    facility_cfg = load_facility_config(repo_root)
    facility = facility_cfg.get("facility", {}) if isinstance(facility_cfg.get("facility"), dict) else {}
    branding = facility_cfg.get("branding", {}) if isinstance(facility_cfg.get("branding"), dict) else {}
    docs_root = repo_root / "dashboard_docs"

    # Fresh build
    if docs_root.exists():
        shutil.rmtree(docs_root)
    (docs_root / "instruments").mkdir(parents=True, exist_ok=True)
    (docs_root / "events").mkdir(parents=True, exist_ok=True)

    vocabularies = load_vocabularies(repo_root / "vocab")
    vocab_json_path = docs_root / "assets" / "vocabularies.json"
    vocab_json_path.parent.mkdir(parents=True, exist_ok=True)
    vocab_json_path.write_text(json.dumps(vocabularies, indent=2), encoding="utf-8")

    combined_registry: dict[str, dict[str, Any]] = {}
    for policy_file in ("schema/instrument_policy.yaml", "schema/QC_policy.yaml", "schema/maintenance_policy.yaml"):
        policy_path = repo_root / policy_file
        if not policy_path.exists():
            continue
        payload, _ = load_policy(policy_path)
        if not isinstance(payload, dict):
            continue
        vocab_registry = payload.get("vocab_registry")
        if isinstance(vocab_registry, dict):
            combined_registry.update(vocab_registry)

    vocabulary = Vocabulary(repo_root / "vocab", vocab_registry=combined_registry or None)

    load_errors: list[YamlLoadError] = []
    validated_instrument_ids, instrument_validation_issues, instrument_validation_warnings = validated_instrument_selection()

    # Source-of-truth gate: only validated instruments may enter canonicalization/DTO production flow.
    instruments = load_instruments(
        "instruments",
        load_errors=load_errors,
        allowed_instrument_ids=validated_instrument_ids,
    )
    retired_instruments = load_instruments(
        "instruments",
        load_errors=load_errors,
        include_retired=True,
        allowed_instrument_ids=validated_instrument_ids,
    )

    global_vm_payloads: dict[str, dict[str, Any]] = {}

    for inst in [*instruments, *retired_instruments]:
        inst["modalities_display"] = [
            vocab_label(vocabulary, "modalities", modality_id)
            for modality_id in inst.get("modalities", [])
        ]
        for module in inst.get("modules", []):
            module_name = clean_text(module.get("name"))
            module["display_name"] = vocab_label(vocabulary, "modules", module_name)

    # Generate Vocabulary Dictionary Markdown with Tabs
    vocab_md_lines = [
        "---",
        "title: Vocabulary Dictionary",
        "description: Controlled terminology used in the AIC database.",
        "---",
        "",
        "# 📖 Vocabulary Dictionary\n",
        "This page defines the strictly controlled terminology used across the AIC database. Use the **Canonical ID** when writing YAML files, though the validation scripts will gracefully suggest corrections if you use a known **Synonym**.\n",
    ]

    # Group vocabularies into logical categories
    categories = {
        "🔬 Instruments": [
            "modalities",
            "modules",
            "detector_kinds",
            "light_source_kinds",
            "scanner_types",
            "objective_corrections",
            "objective_immersion",
        ],
        "🛠️ Maintenance": ["maintenance_action", "maintenance_reason", "maintenance_status", "service_provider"],
        "✅ Quality Control": [
            "qc_type",
            "qc_metric_classes",
            "qc_evaluation_status",
            "qc_artifact_roles",
            "qc_measurement_positions",
            "qc_setpoint_units",
            "metric_unit",
        ],
    }

    # Keep track of what we've rendered so we can dump uncategorized ones in an "Other" tab
    rendered_vocabs = set()

    for cat_title, expected_vocabs in categories.items():
        vocab_md_lines.append(f'=== "{cat_title}"\n')

        has_content = False
        for vocab_name in expected_vocabs:
            if vocab_name in vocabulary.terms_by_vocab:
                has_content = True
                rendered_vocabs.add(vocab_name)
                title = vocab_name.replace("_", " ").title()
                vocab_md_lines.append(f"    ## {title}\n")
                vocab_md_lines.append("    | Label | Canonical ID | Synonyms | Description |")
                vocab_md_lines.append("    | :--- | :--- | :--- | :--- |")

                for term in sorted(vocabulary.terms_by_vocab[vocab_name].values(), key=lambda t: t.label.lower()):
                    label = f"**{term.label}**"
                    code_id = f"`{term.id}`"
                    syns = ", ".join([f"`{s}`" for s in term.synonyms]) if term.synonyms else "-"
                    desc = term.description.replace("\n", " ").strip() if term.description else "-"
                    vocab_md_lines.append(f"    | {label} | {code_id} | {syns} | {desc} |")
                vocab_md_lines.append("\n")

        if not has_content:
            vocab_md_lines.append("    _No vocabularies currently defined for this category._\n\n")

    # Catch-all for any vocabularies not explicitly categorized above
    other_vocabs = [v for v in vocabulary.terms_by_vocab.keys() if v not in rendered_vocabs]
    if other_vocabs:
        vocab_md_lines.append('=== "📦 Other"\n')
        for vocab_name in sorted(other_vocabs):
            title = vocab_name.replace("_", " ").title()
            vocab_md_lines.append(f"    ## {title}\n")
            vocab_md_lines.append("    | Label | Canonical ID | Synonyms | Description |")
            vocab_md_lines.append("    | :--- | :--- | :--- | :--- |")
            for term in sorted(vocabulary.terms_by_vocab[vocab_name].values(), key=lambda t: t.label.lower()):
                label = f"**{term.label}**"
                code_id = f"`{term.id}`"
                syns = ", ".join([f"`{s}`" for s in term.synonyms]) if term.synonyms else "-"
                desc = term.description.replace("\n", " ").strip() if term.description else "-"
                vocab_md_lines.append(f"    | {label} | {code_id} | {syns} | {desc} |")
            vocab_md_lines.append("\n")

    (docs_root / "vocabulary_dictionary.md").write_text("\n".join(vocab_md_lines), encoding="utf-8")

    # Copy assets into docs
    if (repo_root / "assets").exists():
        shutil.copytree(repo_root / "assets", docs_root / "assets", dirs_exist_ok=True)

    templates_dir = Path(__file__).resolve().parent / "templates"
    jinja_env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)

    tpl_index = jinja_env.get_template("index.md.j2")
    tpl_status = jinja_env.get_template("status.md.j2")
    tpl_retired = jinja_env.get_template("retired_index.md.j2")
    tpl_spec = jinja_env.get_template("instrument_spec.md.j2")
    tpl_history = jinja_env.get_template("instrument_history.md.j2")
    tpl_event = jinja_env.get_template("event_detail.md.j2")
    tpl_plan = jinja_env.get_template("plan_experiments.md.j2")
    tpl_methods = jinja_env.get_template("methods_generator.md.j2")
    tpl_vm = jinja_env.get_template("virtual_microscope.html.j2")

    qc_logs_by_instrument = index_instrument_logs("qc/sessions", load_errors=load_errors)
    maint_logs_by_instrument = index_instrument_logs("maintenance/events", load_errors=load_errors)

    validation_issues = list(instrument_validation_issues)
    event_validation_report = validate_event_ledgers(
        instrument_ids=validated_instrument_ids,
        allowed_record_types=allowed_record_types,
    )
    validation_issues.extend(event_validation_report.errors)
    if instrument_validation_warnings:
        print_validation_report(instrument_validation_warnings, report_name="warnings")
    if event_validation_report.warnings:
        print_validation_report(event_validation_report.warnings, report_name="warnings")
    if event_validation_report.migration_notices:
        print_validation_report(event_validation_report.migration_notices, report_name="migration notices")

    # Aggregations
    all_modality_ids = sorted({m for inst in instruments for m in inst.get("modalities", []) if isinstance(m, str)})
    all_modalities = [
        {"id": modality_id, "label": vocab_label(vocabulary, "modalities", modality_id)}
        for modality_id in all_modality_ids
    ]

    fleet_counts = {"total": len(instruments), "green": 0, "yellow": 0, "red": 0}
    flagged: list[dict[str, Any]] = []

    retired_instrument_ids = {inst["id"] for inst in retired_instruments}

    for inst in [*instruments, *retired_instruments]:
        instrument_id = inst["id"]
        is_retired_instrument = instrument_id in retired_instrument_ids

        qc_logs = get_all_instrument_logs(
            "qc/sessions",
            instrument_id,
            load_errors=load_errors,
            preindexed_logs=qc_logs_by_instrument,
        )
        maint_logs = get_all_instrument_logs(
            "maintenance/events",
            instrument_id,
            load_errors=load_errors,
            preindexed_logs=maint_logs_by_instrument,
        )

        latest_qc = qc_logs[-1]["data"] if qc_logs else None
        latest_maint = maint_logs[-1]["data"] if maint_logs else None

        status = evaluate_instrument_status(latest_qc, latest_maint)
        inst["status"] = status

        if not is_retired_instrument:
            if status["color"] == "green":
                fleet_counts["green"] += 1
            elif status["color"] == "yellow":
                fleet_counts["yellow"] += 1
            else:
                fleet_counts["red"] += 1

            if status["color"] in {"yellow", "red"}:
                flagged.append(inst)

        charts_json = _build_all_charts_data(qc_logs)
        # Roll up metrics chronologically so we always have the latest value for EVERY metric
        latest_metrics = {}
        for log in qc_logs:
            payload = log.get("data")
            if isinstance(payload, dict):
                session_metrics = _metric_lookup(payload.get("metrics_computed"))
                latest_metrics.update(session_metrics)
        
        canonical_payload = inst.get("canonical", {})
        lightpath_dto = generate_virtual_microscope_payload(canonical_payload if isinstance(canonical_payload, dict) else {"hardware": {}}, include_inferred_terminals=False)
        if not isinstance(lightpath_dto, dict):
            lightpath_dto = {}
        inst["lightpath_dto"] = lightpath_dto
        inst["dto"] = build_instrument_mega_dto(vocabulary, inst, lightpath_dto)

        instrument_dir = docs_root / "instruments" / instrument_id
        instrument_dir.mkdir(parents=True, exist_ok=True)

        # Render Overview
        overview_md = tpl_spec.render(
            instrument=inst,
            charts_json=charts_json,
            latest_metrics=latest_metrics,
            metric_names=METRIC_NAMES,
            policy=inst.get("canonical", {}).get("policy", {}),
        )
        (instrument_dir / "index.md").write_text(overview_md, encoding="utf-8")

        if not is_retired_instrument:
            vm_payload = copy.deepcopy(inst["dto"].get("hardware", {}).get("optical_path", {}))
            vm_payload["display_name"] = inst.get("dto", {}).get("display_name")
            global_vm_payloads[instrument_id] = vm_payload

# Format events for the history timeline
        history_events_qc = []
        for log in qc_logs:
            payload = log.get("data") or {}
            event_id = Path(log["source_path"]).stem
            event_instrument = _event_output_instrument(payload, instrument_id)
            history_events_qc.append({
                "date": _extract_log_date(payload),
                "status": payload.get("evaluation", {}).get("overall_status", "completed"),
                "suite": "QC Session",
                "event_id": event_id,
                "event_href": f"../../../events/{event_instrument}/{event_id}/",
            })
            
        history_events_maint = []
        for log in maint_logs:
            payload = log.get("data") or {}
            event_id = Path(log["source_path"]).stem
            event_instrument = _event_output_instrument(payload, instrument_id)
            history_events_maint.append({
                "date": _extract_log_date(payload),
                "status": payload.get("microscope_status_after", "completed"),
                "type": "Maintenance",
                "event_id": event_id,
                "event_href": f"../../../events/{event_instrument}/{event_id}/",
            })

        # Render history page for each instrument
        history_md = tpl_history.render(
            instrument=inst,
            charts_json=charts_json,
            metric_names=METRIC_NAMES,
            qc_events=history_events_qc,
            maintenance_events=history_events_maint
        )
        (instrument_dir / "history.md").write_text(history_md, encoding="utf-8")

        # Event details
        for log_entry in qc_logs + maint_logs:
            source_path = log_entry.get("source_path")
            if not isinstance(source_path, str):
                continue

            source_file = Path(source_path)
            event_id = source_file.stem
            event_payload = log_entry.get("data") if isinstance(log_entry.get("data"), dict) else {}
            event_instrument = _event_output_instrument(event_payload, instrument_id)

            try:
                raw_yaml_text = source_file.read_text(encoding="utf-8")
            except OSError:
                raw_yaml_text = yaml.safe_dump(event_payload, sort_keys=False, allow_unicode=True)

            event_md = tpl_event.render(
                event_id=event_id,
                date=_extract_log_date(event_payload),
                instrument=event_payload.get("microscope"),
                instrument_id=event_instrument,
                operator=event_payload.get("performed_by") or event_payload.get("service_provider"),
                raw_yaml_content=raw_yaml_text,
                payload=event_payload,
            )
            event_dir = docs_root / "events" / event_instrument
            event_dir.mkdir(parents=True, exist_ok=True)
            (event_dir / f"{event_id}.md").write_text(event_md, encoding="utf-8")

    vm_html = tpl_vm.render(lightpath_data_json=json_script_data(global_vm_payloads))
    (docs_root / "virtual_microscope.md").write_text(vm_html, encoding="utf-8")

    # Fleet + status pages
    index_md = tpl_index.render(instruments=instruments, all_modalities=all_modalities, counts=fleet_counts)
    (docs_root / "index.md").write_text(index_md, encoding="utf-8")

    # Export active + retired instruments to JSON for the Methods Generator
    json_path = docs_root / "assets" / "instruments_data.json"
    json_path.parent.mkdir(parents=True, exist_ok=True) 
    json_payload = {
        "instruments": [
            build_methods_generator_instrument_export(inst)
            for inst in sorted([*instruments, *retired_instruments], key=lambda item: item.get("id", ""))
        ],
    }
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")

    # Export AI/LLM Optimized Decision-Support Inventory
    llm_inventory_path = docs_root / "assets" / "llm_inventory.json"
    llm_payload = build_llm_inventory_payload(facility, instruments)
    llm_inventory_path.write_text(json.dumps(llm_payload, indent=2), encoding="utf-8")

    # Render Methods Generator page
    methods_page_config = build_methods_generator_page_config(facility, repo_root)
    methods_md = tpl_methods.render(
        methods_generator_config_json=json_script_data(methods_page_config),
    )
    (docs_root / "methods_generator.md").write_text(methods_md, encoding="utf-8")

    plan_page_config = build_plan_experiments_page_config(facility)
    plan_md = tpl_plan.render(
        plan_experiments_config_json=json_script_data(plan_page_config),
        facility_short_name=plan_page_config["facility_short_name"],
        facility_contact_url=plan_page_config["facility_contact_url"],
        facility_contact_label=plan_page_config["facility_contact_label"],
        llm_inventory_asset_url=plan_page_config["llm_inventory_asset_url"],
    )
    (docs_root / "plan_experiments.md").write_text(plan_md, encoding="utf-8")

    status_md = tpl_status.render(issues=flagged)
    (docs_root / "status.md").write_text(status_md, encoding="utf-8")

    retired_md = tpl_retired.render(retired_instruments=retired_instruments)
    retired_docs_dir = docs_root / "retired"
    retired_docs_dir.mkdir(parents=True, exist_ok=True)
    (retired_docs_dir / "index.md").write_text(retired_md, encoding="utf-8")

    # Extracted site URL into environment variable to prevent hardcoding issues
    site_url = os.getenv("MKDOCS_SITE_URL", str(facility.get("public_site_url", "")))

    # MkDocs config
    mkdocs_config = {
        "site_name": str(facility.get("site_name", "Microscopy Dashboard")),
        "site_url": site_url,
        "use_directory_urls": True,
        "docs_dir": "dashboard_docs",
        "theme": {
            "name": "material",
            "features": [
                "navigation.tabs",
                "navigation.sections",
                "navigation.top",
                "toc.integrate",
                "search.suggest",
                "search.highlight",
                "content.code.copy",
            ],
            "palette": [
                {
                    "scheme": "default",
                    "toggle": {"icon": "material/brightness-7", "name": "Switch to dark mode"},
                },
                {
                    "scheme": "slate",
                    "toggle": {"icon": "material/brightness-4", "name": "Switch to light mode"},
                },
            ],
            "logo": str(branding.get("logo", "assets/images/logo.svg")),
            "favicon": str(branding.get("favicon", "assets/images/favicon.svg")),
        },
        "plugins": ["search"],
        "markdown_extensions": [
            "admonition",
            "attr_list",
            "md_in_html",
            "tables",
            "pymdownx.details",
            "pymdownx.superfences",
            "pymdownx.tabbed",
        ],
        "extra_css": ["assets/stylesheets/dashboard.css"],
        "extra_javascript": [
            "assets/javascripts/dashboard.js",
            "https://cdn.jsdelivr.net/npm/chart.js",
            "assets/javascripts/charts.js",
        ],
        "nav": build_nav(instruments, retired_instruments),
        # Tell MkDocs to ignore unmapped files gracefully (events and history pages)
        "validation": {
            "nav": {"omitted_files": "info"}
        },
    }

    (repo_root / "mkdocs.yml").write_text(yaml.safe_dump(mkdocs_config, sort_keys=False, allow_unicode=True), encoding="utf-8")

    has_failures = False

    if load_errors:
        _print_yaml_error_report(load_errors)
        has_failures = True

    if validation_issues:
        print_validation_report(validation_issues)
        has_failures = True

    if strict and has_failures:
        _print_agent_fix_prompt(load_errors, validation_issues)
        return 1

    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build dashboard docs from YAML ledgers.")
    parser.add_argument(
        "--strict",
        dest="strict",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fail with non-zero exit code if any YAML file cannot be parsed or validation fails (default: strict).",
    )
    parser.add_argument(
        "--allowed-record-types",
        dest="allowed_record_types",
        default=",".join(DEFAULT_ALLOWED_RECORD_TYPES),
        help="Comma-separated allowed event record_type values.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    raise SystemExit(
        main(strict=args.strict, allowed_record_types=_allowed_record_types_from_arg(args.allowed_record_types))
    )
