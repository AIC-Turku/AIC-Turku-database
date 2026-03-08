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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from validate import (
    DEFAULT_ALLOWED_RECORD_TYPES,
    Vocabulary,
    build_instrument_completeness_report,
    load_policy,
    print_validation_report,
    validate_event_ledgers,
    validate_instrument_ledgers,
)

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
            "short_name": "AIC Turku",
            "full_name": "Advanced Imaging Core Facility at Turku Bioscience Centre",
            "site_name": "AIC Microscopy Dashboard",
            "public_site_url": "https://aic-turku.github.io/AIC-Turku-database/",
            "contact_url": "https://bioscience.fi/aic/",
            "organization_url": "https://bioscience.fi/aic/",
            "acknowledgements": {
                "standard": "Imaging was performed at the Advanced Imaging Core Facility at Turku Bioscience Centre, supported by Biocentre Finland, the Finnish Advanced Microscopy Node of Euro-BioImaging Finland (Turku, Finland), and Turku Bioimaging. This work was supported by the Research Council of Finland, FIRI 2023 grant decision numbers 359073 and 358879, and FIRI 2024 grant decision numbers 367582 and 367577.",
                "xcelligence_addition": "Testament funds from Henna Ruusunen also supported this work.",
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
    print("3. Re-run: python scripts/dashboard_builder.py --strict", file=sys.stderr)
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


def slugify(value: str) -> str:
    s = value.lower().strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


INSTRUMENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_valid_instrument_id(value: str) -> bool:
    return bool(INSTRUMENT_ID_PATTERN.fullmatch(value))


def parse_notes_compact(notes: str) -> dict[str, Any]:
    """Parse legacy notes strings like: 'type: "..." | filters: [..] | imaging_modes: [...]'."""
    notes = clean_text(notes)
    if "|" not in notes or ":" not in notes:
        return {"raw": notes} if notes else {}

    out: dict[str, Any] = {}
    parts = [p.strip() for p in notes.split("|") if p.strip()]

    for part in parts:
        if ":" not in part:
            continue
        key, raw_val = part.split(":", 1)
        key = key.strip().lower().replace(" ", "_")
        raw_val = raw_val.strip()

        # Try to parse list-ish values safely.
        if raw_val.startswith("[") and raw_val.endswith("]"):
            try:
                parsed = yaml.safe_load(raw_val)
                if isinstance(parsed, list):
                    out[key] = [clean_text(x) for x in parsed]
                    continue
            except yaml.YAMLError:
                pass

        # Unquote a simple quoted string
        if (raw_val.startswith('"') and raw_val.endswith('"')) or (raw_val.startswith("'") and raw_val.endswith("'")):
            raw_val = raw_val[1:-1]

        out[key] = clean_text(raw_val)

    if not out and notes:
        out["raw"] = notes

    return out


def extract_instrument_location(raw_location: str, notes: str) -> str:
    """Return microscope location from dedicated field or note text fallback."""
    location = clean_text(raw_location)
    if location:
        return location

    cleaned_notes = clean_text(notes)
    if not cleaned_notes:
        return ""

    match = re.search(r"\blocation\s*:\s*([^|\n\r]+)", cleaned_notes, flags=re.IGNORECASE)
    if not match:
        return ""

    extracted = match.group(1).strip().rstrip(". ")
    return clean_text(extracted)


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
    """Normalize software sections into a list of rows, including URLs."""
    rows: list[dict[str, str]] = []

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                rows.append(
                    {
                        "component": clean_text(item.get("component") or item.get("type") or ""),
                        "name": clean_text(item.get("name") or ""),
                        "developer": clean_text(item.get("developer") or item.get("manufacturer") or ""),
                        "version": clean_text(item.get("version") or ""),
                        "url": clean_text(item.get("url") or ""),
                    }
                )
        cleaned_rows = [strip_empty_values(r) for r in rows]
        return [r for r in cleaned_rows if isinstance(r, dict) and r]

    if isinstance(raw, dict):
        for component, payload in raw.items():
            if isinstance(payload, dict):
                rows.append(
                    {
                        "component": clean_text(component),
                        "name": clean_text(payload.get("name")),
                        "developer": clean_text(payload.get("developer") or payload.get("manufacturer")),
                        "version": clean_text(payload.get("version")),
                        "url": clean_text(payload.get("url")),
                    }
                )
            elif isinstance(payload, str):
                rows.append({"component": clean_text(component), "name": clean_text(payload), "developer": "", "version": "", "url": ""})
        cleaned_rows = [strip_empty_values(r) for r in rows]
        return [r for r in cleaned_rows if isinstance(r, dict) and r]

    if isinstance(raw, str) and raw.strip():
        cleaned_row = strip_empty_values({"component": "software", "name": clean_text(raw), "developer": "", "version": "", "url": ""})
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
            {
                "kind": get_val(light_source, "kind", "type"),
                "manufacturer": get_val(light_source, "manufacturer"),
                "model": get_val(light_source, "model", "name"),
                "technology": get_val(light_source, "technology"),
                "wavelength_nm": get_val(light_source, "wavelength_nm", "wavelength"),
                "power": get_val(light_source, "power"),
                "notes": get_val(light_source, "notes"),
                "url": get_val(light_source, "url"),
            }
            for light_source in light_sources_raw
            if isinstance(light_source, dict)
        ]

    detectors_raw = raw.get("detectors")
    if isinstance(detectors_raw, list):
        hw["detectors"] = [
            {
                "kind": get_val(detector, "kind", "type"),
                "manufacturer": get_val(detector, "manufacturer", "name"),
                "model": get_val(detector, "model"),
                "pixel_pitch_um": get_val(detector, "pixel_pitch_um", "pixel_size_um"),
                "sensor_format_px": get_val(detector, "sensor_format_px"),
                "binning": get_val(detector, "binning"),
                "bit_depth": get_val(detector, "bit_depth"),
                "qe_peak_pct": get_val(detector, "qe_peak_pct"),
                "read_noise_e": get_val(detector, "read_noise_e"),
                "notes": get_val(detector, "notes"),
                "url": get_val(detector, "url"),
            }
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
        "filters",
        "splitters",
        "magnification_changers",
        "environment",
        "stages",
        "hardware_autofocus",
        "triggering",
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
    notes_parsed = parse_notes_compact(notes_raw) if notes_raw else {}

    raw_modules = payload.get("modules") or []
    modules = []
    for m in raw_modules:
        if isinstance(m, dict):
            modules.append({"name": clean_text(m.get("name")), "notes": clean_text(m.get("notes")), "url": clean_text(m.get("url"))})
        elif isinstance(m, str):
            modules.append({"name": clean_text(m), "notes": "", "url": ""})

    modalities = payload.get("modalities")
    if not isinstance(modalities, list):
        modalities = []

    software_raw = payload.get("software") if isinstance(payload.get("software"), dict) else {}
    software = strip_empty_values(normalize_software(payload.get("software")))
    hardware = strip_empty_values(normalize_hardware(payload.get("hardware") or {}))
    policy = build_instrument_completeness_report(payload)

    software_roles = ("acquisition", "analysis", "deconvolution", "flim")

    software_by_role: dict[str, dict[str, Any]] = {}
    for role in software_roles:
        role_payload = software_raw.get(role) if isinstance(software_raw, dict) and isinstance(software_raw.get(role), dict) else {}
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
        if path.startswith("software."):
            role = path.split(".")[1]

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

    return {
        "retired": retired,
        "id": instrument_id,
        "display_name": display_name,
        "manufacturer": clean_text(inst_section.get("manufacturer")),
        "model": clean_text(inst_section.get("model")),
        "year_of_purchase": clean_text(inst_section.get("year_of_purchase")),
        "funding": clean_text(inst_section.get("funding")),
        "stand_orientation": clean_text(inst_section.get("stand_orientation")),
        "location": extract_instrument_location(inst_section.get("location"), notes_raw),
        "notes_raw": notes_raw,
        "notes": notes_parsed,
        "modalities": [clean_text(m) for m in modalities if isinstance(m, str) and clean_text(m)],
        "modules": modules,
        "software": software,
        "image_filename": _discover_image_filename(instrument_id),
        "url": clean_text(inst_section.get("url")),
        "canonical": {
            "notes": notes_parsed,
            "software": software,
            "hardware": hardware,
            "policy": {
                "sections": policy.sections,
                "missing_required": policy.missing_required,
                "missing_conditional": policy.missing_conditional,
                "alias_fallbacks": policy.alias_fallbacks,
            },
        },
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


def load_instruments(
    instruments_dir: str = "instruments",
    load_errors: list[YamlLoadError] | None = None,
    include_retired: bool = False,
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
    instruments = load_instruments("instruments", load_errors=load_errors)
    retired_instruments = load_instruments("instruments", load_errors=load_errors, include_retired=True)

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

    qc_logs_by_instrument = index_instrument_logs("qc/sessions", load_errors=load_errors)
    maint_logs_by_instrument = index_instrument_logs("maintenance/events", load_errors=load_errors)

    validated_instrument_ids, instrument_validation_issues, instrument_validation_warnings = validate_instrument_ledgers()
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
        
        canonical = inst.get("canonical") if isinstance(inst.get("canonical"), dict) else {}
        canonical_hardware = canonical.get("hardware") if isinstance(canonical.get("hardware"), dict) else {}

        light_sources = canonical_hardware.get("light_sources", [])
        detectors = canonical_hardware.get("detectors", [])
        objectives = canonical_hardware.get("objectives", [])
        splitters = canonical_hardware.get("splitters", [])
        filters = canonical_hardware.get("filters", [])
        magnification_changers = canonical_hardware.get("magnification_changers", [])
        environment = canonical_hardware.get("environment") if isinstance(canonical_hardware.get("environment"), dict) else {}
        stages = canonical_hardware.get("stages", [])
        hardware_autofocus = canonical_hardware.get("hardware_autofocus") if isinstance(canonical_hardware.get("hardware_autofocus"), dict) else {}
        triggering = canonical_hardware.get("triggering") if isinstance(canonical_hardware.get("triggering"), dict) else {}
        scanner = canonical_hardware.get("scanner") if isinstance(canonical_hardware.get("scanner"), dict) else {}

        inst["processed_hardware"] = {
            "modalities": [clean_text(m) for m in inst.get("modalities", []) if clean_text(m)],
            "modules": [
                {
                    "name": clean_text(module.get("name")),
                    "notes": clean_text(module.get("notes")),
                    "url": clean_text(module.get("url")),
                }
                for module in inst.get("modules", [])
                if isinstance(module, dict) and clean_text(module.get("name"))
            ],
            "scanner": {
                "type": clean_text(scanner.get("type")),
                "line_rate_hz": scanner.get("line_rate_hz"),
                "pinhole_um": scanner.get("pinhole_um"),
                "light_sheet_type": clean_text(scanner.get("light_sheet_type")),
                "notes": clean_text(scanner.get("notes")),
                "url": clean_text(scanner.get("url")),
            },
            "light_sources": [
                {
                    "name": clean_text(src.get("model")),
                    "type": clean_text(src.get("kind")),
                    "wavelength": src.get("wavelength_nm"),
                    "power": clean_text(src.get("power")),
                    "manufacturer": clean_text(src.get("manufacturer")),
                    "technology": clean_text(src.get("technology")),
                    "notes": clean_text(src.get("notes")),
                    "url": clean_text(src.get("url")),
                }
                for src in light_sources
                if isinstance(src, dict)
            ],
            "detectors": [
                {
                    "name": clean_text(det.get("manufacturer")),
                    "model": clean_text(det.get("model")),
                    "type": clean_text(det.get("kind")),
                    "pixel_pitch_um": det.get("pixel_pitch_um") or det.get("pixel_size_um"),
                    "sensor_format_px": clean_text(det.get("sensor_format_px")),
                    "binning": clean_text(det.get("binning")),
                    "bit_depth": det.get("bit_depth"),
                    "qe_peak_pct": det.get("qe_peak_pct"),
                    "read_noise_e": det.get("read_noise_e"),
                    "notes": clean_text(det.get("notes")),
                    "url": clean_text(det.get("url")),
                }
                for det in detectors
                if isinstance(det, dict)
            ],
            "objectives": [
                {
                    "id": clean_text(obj.get("id")),
                    "name": clean_text(obj.get("model")),
                    "manufacturer": clean_text(obj.get("manufacturer")),
                    "product_code": clean_text(obj.get("product_code")),
                    "magnification": obj.get("magnification"),
                    "na": obj.get("numerical_aperture"),
                    "wd": clean_text(obj.get("working_distance")),
                    "immersion": clean_text(obj.get("immersion")),
                    "correction": clean_text(obj.get("correction")),
                    "afc": obj.get("afc_compatible"),
                    "is_installed": obj.get("is_installed"),
                    "specialties": clean_string_list(obj.get("specialties")),
                    "notes": clean_text(obj.get("notes")),
                    "url": clean_text(obj.get("url")),
                }
                for obj in objectives
                if isinstance(obj, dict)
            ],
            "splitters": splitters,
            "filters": filters,
            "magnification_changers": magnification_changers,
            "environment": {
                "temperature_control": normalize_optional_bool(environment.get("temperature_control")),
                "temperature_range": clean_text(environment.get("temperature_range")),
                "co2_control": normalize_optional_bool(environment.get("co2_control")),
                "co2_range": clean_text(environment.get("co2_range")),
                "o2_control": normalize_optional_bool(environment.get("o2_control")),
                "o2_range": clean_text(environment.get("o2_range")),
                "humidity_control": normalize_optional_bool(environment.get("humidity_control")),
                "notes": clean_text(environment.get("notes")),
            },
            "stages": [
                {
                    "type": clean_text(stage.get("type")),
                    "manufacturer": clean_text(stage.get("manufacturer")),
                    "model": clean_text(stage.get("model")),
                    "step_size_um": stage.get("step_size_um"),
                }
                for stage in stages
                if isinstance(stage, dict)
            ],
            "hardware_autofocus": {
                "is_installed": normalize_optional_bool(hardware_autofocus.get("is_installed")),
                "type": clean_text(hardware_autofocus.get("type")),
            },
            "triggering": {
                "primary_mode": clean_text(triggering.get("primary_mode")),
                "notes": clean_text(triggering.get("notes")),
            },
        }

        instrument_dir = docs_root / "instruments" / instrument_id
        instrument_dir.mkdir(parents=True, exist_ok=True)

        # Render Overview
        overview_md = tpl_spec.render(
            instrument=inst,
            charts_json=charts_json,
            latest_metrics=latest_metrics,
            metric_names=METRIC_NAMES,
        )
        (instrument_dir / "index.md").write_text(overview_md, encoding="utf-8")

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

    # Fleet + status pages
    index_md = tpl_index.render(instruments=instruments, all_modalities=all_modalities, counts=fleet_counts)
    (docs_root / "index.md").write_text(index_md, encoding="utf-8")

    # Export active + retired instruments to JSON for the Methods Generator
    json_path = docs_root / "assets" / "instruments_data.json"
    json_path.parent.mkdir(parents=True, exist_ok=True) 
    vocabularies_payload = {
        vocab_name: [
            {
                "id": term.id,
                "label": term.label,
                "description": term.description,
                "synonyms": term.synonyms,
            }
            for term in sorted(terms.values(), key=lambda t: t.id)
        ]
        for vocab_name, terms in sorted(vocabulary.terms_by_vocab.items())
    }
    json_payload = {
        "instruments": sorted([*instruments, *retired_instruments], key=lambda inst: inst.get("id", "")),
        "vocabularies": vocabularies_payload,
    }
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")

    # Export AI/LLM Optimized Decision-Support Inventory
    llm_inventory_path = docs_root / "assets" / "llm_inventory.json"
    llm_payload = {
        "facility_name": str(facility.get("short_name", "AIC Turku")),
        "policy": {
            "intent": "LLM-safe experiment planning inventory",
            "grounding_requirement": "Only use fields explicitly present in this JSON file.",
            "do_not_infer_constraints": [
                "Do not invent hardware specifications, accessories, wavelengths, objectives, detector performance, or automation features that are not explicitly listed.",
                "Treat null values and listed missing fields as unknown. Unknown does not mean available.",
                "When required details are missing, ask follow-up questions or clearly state uncertainty.",
            ],
        },
        "vocabulary_definitions": vocabularies_payload,
        "active_microscopes": [],
    }

    def none_if_empty(value: Any) -> Any:
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed if trimmed else None
        return value

    def collect_known_missing_paths(value: Any, prefix: str = "") -> tuple[list[str], list[str]]:
        known_fields: list[str] = []
        missing_fields: list[str] = []

        if isinstance(value, dict):
            for key, child in value.items():
                child_prefix = f"{prefix}.{key}" if prefix else str(key)
                child_known, child_missing = collect_known_missing_paths(child, child_prefix)
                known_fields.extend(child_known)
                missing_fields.extend(child_missing)
            return known_fields, missing_fields

        if isinstance(value, list):
            if not value:
                known_fields.append(prefix)
                return known_fields, missing_fields
            for index, child in enumerate(value):
                child_prefix = f"{prefix}[{index}]"
                child_known, child_missing = collect_known_missing_paths(child, child_prefix)
                known_fields.extend(child_known)
                missing_fields.extend(child_missing)
            return known_fields, missing_fields

        if value is None:
            missing_fields.append(prefix)
        else:
            known_fields.append(prefix)

        return known_fields, missing_fields

    for inst in instruments:
        status = inst.get("status", {})
        canonical = inst.get("canonical") if isinstance(inst.get("canonical"), dict) else {}
        canonical_hardware = canonical.get("hardware") if isinstance(canonical.get("hardware"), dict) else {}
        hw = inst.get("processed_hardware", {}) if isinstance(inst.get("processed_hardware"), dict) else {}

        def pick_summary_value(canonical_value: Any, processed_value: Any, fallback: Any) -> Any:
            if canonical_value not in (None, "", []):
                return canonical_value
            if processed_value not in (None, "", []):
                return processed_value
            return fallback

        # 1. Parse Operational Status
        raw_badge = status.get("badge", "Unknown").lower()
        if "online" in raw_badge:
            overall_status = "online"
        elif "warning" in raw_badge:
            overall_status = "warning"
        elif "offline" in raw_badge or "out of service" in raw_badge:
            overall_status = "offline"
        else:
            overall_status = "unknown"

        raw_reason = none_if_empty(status.get("reason"))
        issues = []
        if overall_status in ["warning", "offline"] and raw_reason and "operational" not in raw_reason.lower():
            issues.append({"severity": overall_status, "description": raw_reason})

        # 2. Parse Environment & Incubation
        live_cell_modules = {
            "incubation",
            "environmental_enclosure",
            "environmental_tolerance",
            "temperature_control",
        }
        is_live_cell = False
        temp_ctrl, co2_ctrl, hum_ctrl = False, False, False

        for m in hw.get("modules", []):
            m_name = m.get("name", "").lower()
            if m_name in live_cell_modules:
                is_live_cell = True
            notes = m.get("notes", "").lower()
            if "temp" in notes or "t/" in notes or "37c" in notes or "37 c" in notes or m_name == "temperature_control":
                temp_ctrl = True
            if "co2" in notes or "c/" in notes:
                co2_ctrl = True
            if "humidity" in notes or "h/" in notes:
                hum_ctrl = True

        env_control = {
            "temperature_control": temp_ctrl,
            "co2_control": co2_ctrl,
            "humidity_control": hum_ctrl,
        } if is_live_cell else None

        # 3. Guidance keeps only direct readiness/control metadata (no derived best/avoid tags)
        # Normalize Helper
        def norm_id(val):
            return str(val).lower().replace(" ", "_").replace("(", "").replace(")", "") if val else None

        def norm_str(val):
            return str(val).lower().replace(" ", "_").replace("(", "").replace(")", "") if val else None

        microscope_payload = {
            "id": inst.get("id"),
            "canonical": {
                "software": copy.deepcopy(canonical.get("software") if isinstance(canonical.get("software"), list) else []),
                "hardware": copy.deepcopy(canonical_hardware),
                "policy": copy.deepcopy(canonical.get("policy") if isinstance(canonical.get("policy"), dict) else {
                    "missing_required": [],
                    "missing_conditional": [],
                    "alias_fallbacks": [],
                }),
            },
            "identity": {
                "display_name": none_if_empty(inst.get("display_name")),
                "manufacturer": none_if_empty(inst.get("manufacturer")),
                "model": none_if_empty(inst.get("model")),
                "stand_orientation": none_if_empty(inst.get("stand_orientation")),
            },
            "operational_status": {
                "overall_status": overall_status,
                "issues": issues,
                "status_note": raw_reason if overall_status == "online" and raw_reason and "operational" not in raw_reason.lower() else None,
                "last_qc_date": none_if_empty(status.get("last_qc_date", None)) or None,
                "last_maintenance_date": none_if_empty(status.get("last_maint_date", None)) or None,
            },
            "capabilities": {
                "modalities": pick_summary_value(canonical_hardware.get("modalities"), hw.get("modalities", []), []),
                "scanner": {
                    "type": none_if_empty(pick_summary_value(canonical_hardware.get("scanner", {}).get("type"), hw.get("scanner", {}).get("type", None), None)) or None,
                    "line_rate_hz": pick_summary_value(canonical_hardware.get("scanner", {}).get("line_rate_hz"), hw.get("scanner", {}).get("line_rate_hz"), None),
                    "pinhole_um": pick_summary_value(canonical_hardware.get("scanner", {}).get("pinhole_um"), hw.get("scanner", {}).get("pinhole_um"), None),
                    "notes": none_if_empty(pick_summary_value(canonical_hardware.get("scanner", {}).get("notes"), hw.get("scanner", {}).get("notes", None), None)) or None,
                },
                "modules": [
                    {"name": none_if_empty(m.get("name")), "notes": none_if_empty(m.get("notes")) or None}
                    for m in pick_summary_value(canonical_hardware.get("modules"), hw.get("modules", []), [])
                    if isinstance(m, dict)
                ],
                "objectives": [
                    {
                        "magnification": obj.get("magnification"),
                        "numerical_aperture": pick_summary_value(obj.get("numerical_aperture"), obj.get("na"), None),
                        "immersion": norm_id(obj.get("immersion")),
                        "correction_class": norm_id(pick_summary_value(obj.get("correction_class"), obj.get("correction"), None)),
                        "working_distance": none_if_empty(pick_summary_value(obj.get("working_distance"), obj.get("wd"), None)) or None,
                        "specialties": obj.get("specialties", []),
                        "notes": none_if_empty(obj.get("notes")) or None,
                    }
                    for obj in pick_summary_value(canonical_hardware.get("objectives"), hw.get("objectives", []), [])
                    if isinstance(obj, dict)
                ],
                "light_sources": [
                    {
                        "type": norm_str(pick_summary_value(ls.get("type"), ls.get("kind"), None)),
                        "manufacturer": none_if_empty(ls.get("manufacturer")) or None,
                        "wavelength": none_if_empty(pick_summary_value(ls.get("wavelength_nm"), ls.get("wavelength"), None)) or None,
                        "technology": none_if_empty(ls.get("technology")) or None,
                        "model": none_if_empty(pick_summary_value(ls.get("model"), ls.get("name"), None)) or None,
                        "notes": none_if_empty(ls.get("notes")) or None,
                    }
                    for ls in pick_summary_value(canonical_hardware.get("light_sources"), hw.get("light_sources", []), [])
                    if isinstance(ls, dict)
                ],
                "filters": [
                    {
                        "name": none_if_empty(f.get("name")) or None,
                        "excitation": none_if_empty(f.get("excitation")) or None,
                        "emission": none_if_empty(f.get("emission")) or None,
                        "dichroic": none_if_empty(f.get("dichroic")) or None,
                    }
                    for f in pick_summary_value(canonical_hardware.get("filters"), hw.get("filters", []), [])
                    if isinstance(f, dict)
                ],
                "detectors": [
                    {
                        "type": norm_id(pick_summary_value(det.get("kind"), det.get("type"), None)),
                        "model": none_if_empty(det.get("model")) or None,
                        "pixel_pitch_um": pick_summary_value(det.get("pixel_pitch_um"), det.get("pixel_size_um"), None),
                        "sensor_format_px": none_if_empty(det.get("sensor_format_px")) or None,
                        "binning": none_if_empty(det.get("binning")) or None,
                        "bit_depth": det.get("bit_depth"),
                        "qe_peak_pct": det.get("qe_peak_pct"),
                        "read_noise_e": det.get("read_noise_e"),
                        "notes": none_if_empty(det.get("notes")) or None,
                    }
                    for det in pick_summary_value(canonical_hardware.get("detectors"), hw.get("detectors", []), [])
                    if isinstance(det, dict)
                ],
            },
            "experiment_guidance": {
                "live_cell_ready": is_live_cell,
                "environment_control": env_control,
                "general_notes_and_recommendations": none_if_empty(inst.get("notes_raw", None)) or None,
            },
        }

        known_fields, missing_fields = collect_known_missing_paths(microscope_payload)
        microscope_payload["inventory_completeness"] = {
            "known_fields": sorted(known_fields),
            "missing_fields": sorted(missing_fields),
            "known_field_count": len(known_fields),
            "missing_field_count": len(missing_fields),
            "uncertainty_note": "Missing fields are unknown and must not be assumed.",
        }

        llm_payload["active_microscopes"].append(microscope_payload)

    llm_inventory_path.write_text(json.dumps(llm_payload, indent=2), encoding="utf-8")

    # Render Methods Generator page
    acknowledgements_path = repo_root / "acknowledgements.yaml"
    facility_ack = facility.get("acknowledgements", {}) if isinstance(facility.get("acknowledgements"), dict) else {}
    ack_data = {
        "standard": str(facility_ack.get("standard", "")),
        "xcelligence_addition": str(facility_ack.get("xcelligence_addition", "")),
    }
    if acknowledgements_path.exists():
        ack_loaded = yaml.safe_load(acknowledgements_path.read_text(encoding="utf-8"))
        if isinstance(ack_loaded, dict):
            ack_data = {
                "standard": str(ack_loaded.get("standard", ack_data["standard"])),
                "xcelligence_addition": str(ack_loaded.get("xcelligence_addition", ack_data["xcelligence_addition"])),
            }

    methods_md = tpl_methods.render(
        ack_standard=json.dumps(ack_data.get("standard", "")),
        ack_xcelligence=json.dumps(ack_data.get("xcelligence_addition", "")),
    )
    (docs_root / "methods_generator.md").write_text(methods_md, encoding="utf-8")

    plan_md = tpl_plan.render(
        facility_short_name=str(facility.get("short_name", "Core")),
        facility_contact_url=str(facility.get("contact_url", "#")),
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
