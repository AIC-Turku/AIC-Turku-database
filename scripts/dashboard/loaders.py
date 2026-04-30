"""Loading helpers for dashboard build inputs (YAML + validator selection).

These functions are production entry points; they select validated YAML inputs
before canonical/derived DTO construction.

Implementation moved from scripts/dashboard_builder.py.
"""

from __future__ import annotations

import copy
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import yaml

from scripts.validate import (
    build_instrument_completeness_report,
    validate_instrument_ledgers,
)
from scripts.dashboard.common import (
    clean_text,
    strip_empty_values,
)


# ---------------------------------------------------------------------------
# YAML load helpers
# ---------------------------------------------------------------------------

@dataclass
class YamlLoadError:
    path: str
    message: str


def _iter_yaml_files(base_dir: Path) -> Iterable[Path]:
    if not base_dir.exists() or not base_dir.is_dir():
        return []
    return [p for p in sorted(base_dir.rglob("*")) if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}]


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


# ---------------------------------------------------------------------------
# Facility config
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Instrument DTO normalisation helpers
# ---------------------------------------------------------------------------

INSTRUMENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_valid_instrument_id(value: str) -> bool:
    return bool(INSTRUMENT_ID_PATTERN.fullmatch(value))


def _discover_image_filename(instrument_id: str) -> str:
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".svg"):
        candidate = Path("assets/images") / f"{instrument_id}{ext}"
        if candidate.exists():
            return candidate.name
    return "placeholder.svg"


def _normalized_light_source_payload(light_source: dict[str, Any], get_val: Any) -> dict[str, Any]:
    return {
        "id": get_val(light_source, "id"),
        "kind": get_val(light_source, "kind", "type"),
        "manufacturer": get_val(light_source, "manufacturer"),
        "model": get_val(light_source, "model"),
        "product_code": get_val(light_source, "product_code"),
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
        "product_code": get_val(detector, "product_code"),
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
            "name": get_val(scanner, "name"),
            "manufacturer": get_val(scanner, "manufacturer"),
            "model": get_val(scanner, "model"),
            "product_code": get_val(scanner, "product_code"),
            "line_rate_hz": get_val(scanner, "line_rate_hz"),
            "pinhole_um": get_val(scanner, "pinhole_um"),
            "light_sheet_type": get_val(scanner, "light_sheet_type"),
            "notes": get_val(scanner, "notes"),
            "url": get_val(scanner, "url"),
        }

    sources_raw = raw.get("sources") or raw.get("light_sources")
    if isinstance(sources_raw, list):
        normalized_sources = [
            _normalized_light_source_payload(light_source, get_val)
            for light_source in sources_raw
            if isinstance(light_source, dict)
        ]
        hw["sources"] = normalized_sources
        hw["light_sources"] = normalized_sources

    optical_path_elements_raw = raw.get("optical_path_elements")
    if isinstance(optical_path_elements_raw, list):
        hw["optical_path_elements"] = [copy.deepcopy(element) for element in optical_path_elements_raw if isinstance(element, dict)]

    detectors_raw = raw.get("detectors")
    if isinstance(detectors_raw, list):
        hw["detectors"] = [
            _normalized_detector_payload(detector, get_val)
            for detector in detectors_raw
            if isinstance(detector, dict)
        ]

    eyepieces_raw = raw.get("eyepieces")
    if isinstance(eyepieces_raw, list):
        hw["eyepieces"] = [copy.deepcopy(eyepiece) for eyepiece in eyepieces_raw if isinstance(eyepiece, dict)]

    endpoint_rows = raw.get("endpoints") or raw.get("terminals") or raw.get("detection_endpoints")
    if isinstance(endpoint_rows, list):
        hw["endpoints"] = [copy.deepcopy(endpoint) for endpoint in endpoint_rows if isinstance(endpoint, dict)]

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
                    "type": clean_text(m.get("type") or m.get("name")),
                    "name": clean_text(m.get("name")),
                    "manufacturer": clean_text(m.get("manufacturer")),
                    "model": clean_text(m.get("model")),
                    "product_code": clean_text(m.get("product_code")),
                    "notes": clean_text(m.get("notes")),
                    "url": clean_text(m.get("url")),
                }
            )
        elif isinstance(m, str):
            modules.append({"type": clean_text(m), "name": "", "manufacturer": "", "model": "", "notes": "", "url": ""})

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
        "light_paths": copy.deepcopy(payload.get("light_paths") or []),
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


# ---------------------------------------------------------------------------
# Load instruments
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Navigation builder
# ---------------------------------------------------------------------------

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


__all__ = [
    "YamlLoadError",
    "load_facility_config",
    "load_vocabularies",
    "_iter_yaml_files",
    "_load_yaml_file",
    "_print_yaml_error_report",
    "_print_agent_fix_prompt",
    "load_instruments",
    "validated_instrument_selection",
    "build_nav",
    "normalize_instrument_dto",
    "normalize_hardware",
    "normalize_software",
    "is_valid_instrument_id",
    "INSTRUMENT_ID_PATTERN",
]
