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
    print_validation_report,
    validate_event_ledgers,
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


def slugify(value: str) -> str:
    s = value.lower().strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


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
                        "version": clean_text(item.get("version") or ""),
                        "url": clean_text(item.get("url") or ""),
                    }
                )
        return [r for r in rows if any(r.values())]

    if isinstance(raw, dict):
        for component, payload in raw.items():
            if isinstance(payload, dict):
                rows.append(
                    {
                        "component": clean_text(component),
                        "name": clean_text(payload.get("name")),
                        "version": clean_text(payload.get("version")),
                        "url": clean_text(payload.get("url")),
                    }
                )
            elif isinstance(payload, str):
                rows.append({"component": clean_text(component), "name": clean_text(payload), "version": "", "url": ""})
        return [r for r in rows if any(r.values())]

    if isinstance(raw, str) and raw.strip():
        return [{"component": "software", "name": clean_text(raw), "version": "", "url": ""}]

    return []


def get_all_instrument_logs(
    log_base_dir: str, instrument_id: str, load_errors: list[YamlLoadError] | None = None
) -> list[dict[str, Any]]:
    if not instrument_id or not instrument_id.strip():
        return []

    base_path = Path(log_base_dir)
    target_id = instrument_id.strip()
    candidates: list[tuple[datetime, Path, dict[str, Any]]] = []

    for yaml_file in _iter_yaml_files(base_path):
        payload = _load_yaml_file(yaml_file, load_errors=load_errors)
        if payload is None:
            continue

        payload_instrument = payload.get("microscope")
        if not isinstance(payload_instrument, str):
            payload_instrument = payload.get("instrument_id")

        if payload_instrument != target_id:
            continue

        sort_dt = _parse_iso_datetime(payload.get("started_utc"))
        if sort_dt is None:
            sort_dt = _timestamp_from_filename(yaml_file)
        if sort_dt is None:
            sort_dt = datetime.min.replace(tzinfo=timezone.utc)

        candidates.append((sort_dt, yaml_file, payload))

    candidates.sort(key=lambda item: (item[0], item[1].as_posix()))

    return [
        {"source_path": path.as_posix(), "filename": path.name, "data": payload}
        for _, path, payload in candidates
    ]


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

        for key in ("reason_details", "action"):
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
    instruments_dir: str = "instruments", load_errors: list[YamlLoadError] | None = None
) -> list[dict[str, Any]]:
    base = Path(instruments_dir)
    instruments: list[dict[str, Any]] = []

    for yaml_file in _iter_yaml_files(base):
        # Skip retired instruments (residing in a 'retired' directory)
        if "retired" in yaml_file.parts:
            continue

        payload = _load_yaml_file(yaml_file, load_errors=load_errors)
        if payload is None:
            continue

        inst_section = payload.get("instrument")
        if not isinstance(inst_section, dict):
            inst_section = {}

        display_name = clean_text(inst_section.get("display_name")) or yaml_file.stem
        raw_instrument_id = inst_section.get("instrument_id")

        if not isinstance(raw_instrument_id, str) or not raw_instrument_id.strip():
            if load_errors is not None:
                load_errors.append(
                    YamlLoadError(
                        path=yaml_file.as_posix(),
                        message="Missing required instrument.instrument_id (must be a non-empty string).",
                    )
                )
            continue

        instrument_id = slugify(raw_instrument_id)

        manufacturer = clean_text(inst_section.get("manufacturer"))
        model = clean_text(inst_section.get("model"))
        year = clean_text(inst_section.get("year_of_purchase"))
        funding = clean_text(inst_section.get("funding"))
        stand = clean_text(inst_section.get("stand_orientation"))
        notes_raw = clean_text(inst_section.get("notes"))
        notes_parsed = parse_notes_compact(notes_raw) if notes_raw else {}
        location = extract_instrument_location(inst_section.get("location"), notes_raw)

        modalities = payload.get("modalities")
        if not isinstance(modalities, list):
            modalities = []
        modalities = [clean_text(m) for m in modalities if isinstance(m, str) and clean_text(m)]

        # Handle both legacy string modules and new object-based modules
        raw_modules = payload.get("modules") or []
        modules = []
        for m in raw_modules:
            if isinstance(m, dict):
                modules.append({
                    "name": clean_text(m.get("name")),
                    "notes": clean_text(m.get("notes")),
                    "url": clean_text(m.get("url"))
                })
            elif isinstance(m, str):
                modules.append({"name": clean_text(m), "notes": "", "url": ""})

        software = normalize_software(payload.get("software"))
        hardware = payload.get("hardware") or {}

        instruments.append(
            {
                "id": instrument_id,
                "display_name": display_name,
                "manufacturer": manufacturer,
                "model": model,
                "year_of_purchase": year,
                "funding": funding,
                "stand_orientation": stand,
                "location": location,
                "notes_raw": notes_raw,
                "notes": notes_parsed,
                "modalities": modalities,
                "modules": modules,
                "software": software,
                "hardware": hardware,
                "image_filename": _discover_image_filename(instrument_id),
                "url": clean_text(inst_section.get("url")),
            }
        )

    instruments.sort(key=lambda x: x["id"])
    return instruments


def build_nav(instruments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    microscopes = [{inst["display_name"]: f"instruments/{inst['id']}/index.md"} for inst in instruments]

    return [
        {"Fleet Overview": "index.md"},
        {"System Health": "status.md"},
        {"Microscopes": microscopes},
    ]


def _allowed_record_types_from_arg(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return DEFAULT_ALLOWED_RECORD_TYPES

    values = [item.strip() for item in raw.split(",") if item.strip()]
    return tuple(values) if values else DEFAULT_ALLOWED_RECORD_TYPES


def main(strict: bool = True, allowed_record_types: tuple[str, ...] = DEFAULT_ALLOWED_RECORD_TYPES) -> int:
    repo_root = Path.cwd()
    docs_root = repo_root / "dashboard_docs"

    # Fresh build
    if docs_root.exists():
        shutil.rmtree(docs_root)
    (docs_root / "instruments").mkdir(parents=True, exist_ok=True)
    (docs_root / "events").mkdir(parents=True, exist_ok=True)

    # Copy assets into docs
    if (repo_root / "assets").exists():
        shutil.copytree(repo_root / "assets", docs_root / "assets", dirs_exist_ok=True)

    templates_dir = Path(__file__).resolve().parent / "templates"
    jinja_env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)

    tpl_index = jinja_env.get_template("index.md.j2")
    tpl_status = jinja_env.get_template("status.md.j2")
    tpl_spec = jinja_env.get_template("instrument_spec.md.j2")
    tpl_history = jinja_env.get_template("instrument_history.md.j2")
    tpl_event = jinja_env.get_template("event_detail.md.j2")

    load_errors: list[YamlLoadError] = []
    instruments = load_instruments("instruments", load_errors=load_errors)

    instrument_ids = {inst.get("id") for inst in instruments if isinstance(inst.get("id"), str)}
    validation_issues = validate_event_ledgers(
        instrument_ids=instrument_ids,
        allowed_record_types=allowed_record_types,
    )

    # Aggregations
    all_modalities = sorted({m for inst in instruments for m in inst.get("modalities", []) if isinstance(m, str)})

    fleet_counts = {"total": len(instruments), "green": 0, "yellow": 0, "red": 0}
    flagged: list[dict[str, Any]] = []

    for inst in instruments:
        instrument_id = inst["id"]

        qc_logs = get_all_instrument_logs("qc/sessions", instrument_id, load_errors=load_errors)
        maint_logs = get_all_instrument_logs("maintenance/events", instrument_id, load_errors=load_errors)

        latest_qc = qc_logs[-1]["data"] if qc_logs else None
        latest_maint = maint_logs[-1]["data"] if maint_logs else None

        status = evaluate_instrument_status(latest_qc, latest_maint)
        inst["status"] = status

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
        
        hardware = inst.get("hardware") or {}

        # Light Sources
        light_sources = [
            {
                "name": clean_text(src.get("model")),
                "type": clean_text(src.get("kind")),
                "wavelength": src.get("wavelength_nm"),
                "power": clean_text(src.get("power")),
                "manufacturer": clean_text(src.get("manufacturer")),
                "notes": clean_text(src.get("notes")),
                "url": clean_text(src.get("url")),
            }
            for src in hardware.get("light_sources", [])
            if isinstance(src, dict)
        ]

        # Expanded Detectors
        detectors = [
            {
                "name": clean_text(det.get("manufacturer")),
                "model": clean_text(det.get("model")),
                "type": clean_text(det.get("kind")),
                "notes": clean_text(det.get("notes")),
                "url": clean_text(det.get("url")),
            }
            for det in hardware.get("detectors", [])
            if isinstance(det, dict)
        ]

        # Expanded Objectives (Captures WD, Immersion, Correction, AFC compatibility)
        objectives = [
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
                "specialties": clean_text(obj.get("specialties")),
                "notes": clean_text(obj.get("notes")),
                "url": clean_text(obj.get("url")),
            }
            for obj in hardware.get("objectives", [])
            if isinstance(obj, dict)
        ]

        # New: Splitters
        splitters = [
            {
                "name": clean_text(s.get("name")),
                "type": clean_text(s.get("type")),
                "notes": clean_text(s.get("notes")),
                "url": clean_text(s.get("url")),
            }
            for s in hardware.get("splitters", [])
            if isinstance(s, dict)
        ]

        # New: Filters
        filters = [
            {
                "name": clean_text(f.get("name")),
                "location": clean_text(f.get("location")),
                "product_code": clean_text(f.get("product_code")),
                "excitation": clean_text(f.get("excitation")),
                "dichroic": clean_text(f.get("dichroic")),
                "emission": clean_text(f.get("emission")),
                "notes": clean_text(f.get("notes")),
                "url": clean_text(f.get("url")),
            }
            for f in hardware.get("filters", [])
            if isinstance(f, dict)
        ]

        instrument_dir = docs_root / "instruments" / instrument_id
        instrument_dir.mkdir(parents=True, exist_ok=True)

        # Render Overview
        overview_md = tpl_spec.render(
            instrument=inst,
            charts_json=charts_json,
            latest_metrics=latest_metrics,
            metric_names=METRIC_NAMES,
            light_sources=light_sources,
            detectors=detectors,
            objectives=objectives,
            splitters=splitters,
            filters=filters,
        )
        (instrument_dir / "index.md").write_text(overview_md, encoding="utf-8")

# Format events for the history timeline
        history_events_qc = []
        for log in qc_logs:
            payload = log.get("data") or {}
            event_id = Path(log["source_path"]).stem
            history_events_qc.append({
                "date": _extract_log_date(payload),
                "status": payload.get("evaluation", {}).get("overall_status", "completed"),
                "suite": "QC Session",
                "event_id": event_id,
                "event_href": f"../../../events/{instrument_id}/{event_id}/",
            })
            
        history_events_maint = []
        for log in maint_logs:
            payload = log.get("data") or {}
            event_id = Path(log["source_path"]).stem
            history_events_maint.append({
                "date": _extract_log_date(payload),
                "status": payload.get("microscope_status_after", "completed"),
                "type": "Maintenance",
                "event_id": event_id,
                "event_href": f"../../../events/{instrument_id}/{event_id}/",
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

            try:
                raw_yaml_text = source_file.read_text(encoding="utf-8")
            except OSError:
                raw_yaml_text = yaml.safe_dump(event_payload, sort_keys=False, allow_unicode=True)

            event_md = tpl_event.render(
                event_id=event_id,
                date=_extract_log_date(event_payload),
                instrument=event_payload.get("microscope"),
                instrument_id=instrument_id,
                operator=event_payload.get("performed_by") or event_payload.get("service_provider"),
                raw_yaml_content=raw_yaml_text,
                payload=event_payload,
            )
            event_dir = docs_root / "events" / instrument_id
            event_dir.mkdir(parents=True, exist_ok=True)
            (event_dir / f"{event_id}.md").write_text(event_md, encoding="utf-8")

    # Fleet + status pages
    index_md = tpl_index.render(instruments=instruments, all_modalities=all_modalities, counts=fleet_counts)
    (docs_root / "index.md").write_text(index_md, encoding="utf-8")

    status_md = tpl_status.render(issues=flagged)
    (docs_root / "status.md").write_text(status_md, encoding="utf-8")

    # Extracted site URL into environment variable to prevent hardcoding issues
    site_url = os.getenv("MKDOCS_SITE_URL", "https://aic-turku.github.io/AIC-Turku-database/")

    # MkDocs config
    mkdocs_config = {
        "site_name": "AIC Microscopy Dashboard",
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
        "nav": build_nav(instruments),
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
