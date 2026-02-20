"""Helpers for building dashboards from instrument and log YAML ledgers."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader


def _iter_yaml_files(base_dir: Path):
    """Yield YAML files under ``base_dir`` in deterministic order."""
    if not base_dir.exists() or not base_dir.is_dir():
        return

    for candidate in sorted(base_dir.rglob("*")):
        if candidate.is_file() and candidate.suffix.lower() in {".yaml", ".yml"}:
            yield candidate


def _load_yaml_file(path: Path) -> dict[str, Any] | None:
    """Safely load a YAML mapping from disk and return ``None`` on invalid data."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            parsed = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError):
        return None

    return parsed if isinstance(parsed, dict) else None


def _parse_iso_datetime(raw_value: Any) -> datetime | None:
    """Parse an ISO-like datetime string and normalize to UTC-aware ``datetime``."""
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
    """Extract a date/time from a ledger filename stem.

    Supports names like ``2026-11-23_post_encoder_repair`` or
    ``2026-11-23T08-20-00Z_event``.
    """
    stem = path.stem
    first_chunk = stem.split("_", 1)[0]

    # Handle filenames that include full timestamps with separator variants.
    full_ts = first_chunk.replace("Z", "+00:00")
    if "T" in full_ts:
        date_part, time_part = full_ts.split("T", 1)
        if "+" not in time_part and "-" in time_part and time_part.count("-") >= 2:
            # Convert HH-MM-SS style to HH:MM:SS (offset part is not expected here).
            time_tokens = time_part.split("-")
            if len(time_tokens) >= 3:
                time_part = ":".join(time_tokens[:3])
                full_ts = f"{date_part}T{time_part}"

    parsed = _parse_iso_datetime(full_ts)
    if parsed:
        return parsed

    # Fallback to date-only filenames.
    try:
        return datetime.strptime(first_chunk, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _extract_instrument_id(data: dict[str, Any], fallback: str) -> str:
    """Get instrument id from common YAML layouts with a safe fallback."""
    raw_id = data.get("instrument_id")
    if isinstance(raw_id, str) and raw_id.strip():
        return raw_id.strip()

    instrument_section = data.get("instrument")
    if isinstance(instrument_section, dict):
        nested_id = instrument_section.get("instrument_id")
        if isinstance(nested_id, str) and nested_id.strip():
            return nested_id.strip()

    return fallback


def get_all_instruments(instruments_dir: str = "instruments") -> dict[str, dict[str, Any]]:
    """Load all instrument YAML files keyed by instrument id.

    Uses ``instrument_id`` from the file content when available. If it is blank or
    missing, the file stem is used.
    """
    result: dict[str, dict[str, Any]] = {}
    base_path = Path(instruments_dir)

    for yaml_file in _iter_yaml_files(base_path):
        payload = _load_yaml_file(yaml_file)
        if payload is None:
            continue

        instrument_id = _extract_instrument_id(payload, fallback=yaml_file.stem)
        result[instrument_id] = payload

    return result


def get_latest_log(log_dir: str, instrument_id: str) -> dict[str, Any] | None:
    """Return the newest parsed log for ``instrument_id`` from ``log_dir``.

    All YAML files in nested year folders are scanned. Logs are sorted by:
    1) ``started_utc`` in file content (preferred)
    2) ISO-like timestamp encoded in filename (fallback)
    """
    if not instrument_id or not instrument_id.strip():
        return None

    all_logs = get_all_instrument_logs(log_dir, instrument_id)
    if not all_logs:
        return None

    return all_logs[-1]["data"]


def get_all_instrument_logs(log_base_dir: str, instrument_id: str) -> list[dict[str, Any]]:
    """Return all logs for ``instrument_id`` under ``log_base_dir`` in time order.

    Every matching YAML file is returned with both path metadata and parsed payload:
    - ``source_path``: path to the YAML file
    - ``filename``: basename of the YAML file
    - ``data``: parsed YAML mapping

    Sorting is oldest -> newest using ``started_utc`` (UTC-normalized). If a file has
    no parseable ``started_utc``, it is placed first and then deterministically ordered
    by path.
    """
    if not instrument_id or not instrument_id.strip():
        return []

    base_path = Path(log_base_dir)
    target_id = instrument_id.strip()
    candidates: list[tuple[datetime, Path, dict[str, Any]]] = []

    for yaml_file in _iter_yaml_files(base_path):
        payload = _load_yaml_file(yaml_file)
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

    if not candidates:
        return []

    candidates.sort(key=lambda item: (item[0], item[1].as_posix()))
    return [
        {
            "source_path": path.as_posix(),
            "filename": path.name,
            "data": payload,
        }
        for _, path, payload in candidates
    ]


def _extract_log_date(log_entry: dict[str, Any] | None) -> str:
    """Extract ``YYYY-MM-DD`` from common timestamp fields in a log entry."""
    if not isinstance(log_entry, dict):
        return ""

    for key in ("started_utc", "timestamp_utc", "date"):
        parsed = _parse_iso_datetime(log_entry.get(key))
        if parsed is not None:
            return parsed.date().isoformat()

    return ""


def evaluate_instrument_status(
    instrument_id: str, latest_qc: dict[str, Any] | None, latest_maint: dict[str, Any] | None
) -> dict[str, str]:
    """Build a fleet-overview status object for one instrument.

    Priority order follows strict UI semantics:
    1) Red (offline): out_of_service maintenance OR QC fail
    2) Yellow (warning): limited maintenance OR QC warn
    3) Green (online): default when no active issues (including missing logs)
    """
    # instrument_id is intentionally part of the signature for UI call sites.
    _ = instrument_id

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
                maint_reason = value.strip()
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
                    message = first_result.get("message")
                    if isinstance(message, str) and message.strip():
                        qc_reason = message.strip()

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
    """Convert ``metrics_computed`` list to ``{metric_id: value}`` mapping."""
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


def _chart_data_json(qc_logs: list[dict[str, Any]]) -> str:
    """Build a Chart.js-compatible JSON string from sorted QC logs."""
    labels: list[str] = []
    values: list[float | int | None] = []
    chosen_metric = "psf.fwhm_z_um"
    fallback_metric = "laser.short_term_stability_delta_percent_488"
    dataset_label = chosen_metric

    for entry in qc_logs:
        payload = entry.get("data") if isinstance(entry, dict) else None
        if not isinstance(payload, dict):
            continue

        started_utc = payload.get("started_utc")
        parsed_started = _parse_iso_datetime(started_utc)
        if parsed_started is None:
            continue

        labels.append(parsed_started.strftime("%Y-%m-%d"))
        metrics = _metric_lookup(payload.get("metrics_computed"))
        point = metrics.get(chosen_metric)
        if point is None:
            point = metrics.get(fallback_metric)
            if point is not None:
                dataset_label = fallback_metric

        if isinstance(point, (int, float)):
            values.append(point)
        else:
            values.append(None)

    chart_payload = {
        "labels": labels,
        "datasets": [
            {
                "label": dataset_label,
                "data": values,
                "borderColor": "rgba(75, 192, 192, 1)",
                "backgroundColor": "rgba(75, 192, 192, 0.2)",
                "spanGaps": True,
                "tension": 0.2,
            }
        ],
    }
    return json.dumps(chart_payload)


if __name__ == "__main__":
    docs_root = Path("docs")
    os.makedirs(docs_root, exist_ok=True)
    os.makedirs(docs_root / "instruments", exist_ok=True)
    os.makedirs(docs_root / "events", exist_ok=True)

    templates_dir = Path(__file__).resolve().parent / "templates"
    jinja_env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)

    instrument_spec_template = jinja_env.get_template("instrument_spec.md.j2")
    instrument_history_template = jinja_env.get_template("instrument_history.md.j2")
    event_detail_template = jinja_env.get_template("event_detail.md.j2")

    instruments = get_all_instruments("instruments")
    nav_instrument_entries: list[dict[str, Any]] = []

    for instrument_id, instrument_payload in sorted(instruments.items(), key=lambda item: item[0]):
        instrument_section = instrument_payload.get("instrument")
        if not isinstance(instrument_section, dict):
            instrument_section = {}
        hardware_section = instrument_payload.get("hardware")
        if not isinstance(hardware_section, dict):
            hardware_section = {}

        display_name = instrument_section.get("display_name") or instrument_id

        qc_logs = get_all_instrument_logs("qc/sessions", instrument_id)
        maintenance_logs = get_all_instrument_logs("maintenance/events", instrument_id)

        chart_data_json = _chart_data_json(qc_logs)

        latest_qc = qc_logs[-1]["data"] if qc_logs else None
        latest_maintenance = maintenance_logs[-1]["data"] if maintenance_logs else None
        status = evaluate_instrument_status(instrument_id, latest_qc, latest_maintenance)

        light_sources = [
            {
                "name": source.get("model"),
                "type": source.get("kind"),
                "wavelength": source.get("wavelength_nm"),
                "notes": source.get("manufacturer"),
            }
            for source in hardware_section.get("light_sources", [])
            if isinstance(source, dict)
        ]
        detectors = [
            {
                "name": detector.get("manufacturer"),
                "type": detector.get("kind"),
                "model": detector.get("model"),
                "notes": "",
            }
            for detector in hardware_section.get("detectors", [])
            if isinstance(detector, dict)
        ]
        objectives = [
            {
                "name": objective.get("model"),
                "magnification": objective.get("magnification"),
                "na": objective.get("numerical_aperture"),
                "notes": objective.get("manufacturer"),
            }
            for objective in hardware_section.get("objectives", [])
            if isinstance(objective, dict)
        ]

        instrument_dir = docs_root / "instruments" / instrument_id
        os.makedirs(instrument_dir, exist_ok=True)

        spec_rendered = instrument_spec_template.render(
            display_name=display_name,
            status_indicator=status.get("badge"),
            light_sources=light_sources,
            detectors=detectors,
            objectives=objectives,
            chart_data_json=chart_data_json,
        )
        (instrument_dir / "spec.md").write_text(spec_rendered, encoding="utf-8")

        qc_events = []
        for qc_log in qc_logs:
            qc_data = qc_log.get("data", {})
            qc_event_id = Path(str(qc_log.get("filename", ""))).stem
            qc_events.append(
                {
                    "event_id": qc_event_id,
                    "date": _extract_log_date(qc_data),
                    "suite": qc_data.get("reason"),
                    "type": qc_data.get("record_type"),
                    "status": ((qc_data.get("evaluation") or {}).get("overall_status") if isinstance(qc_data.get("evaluation"), dict) else ""),
                }
            )

        maintenance_events = []
        for maintenance_log in maintenance_logs:
            maint_data = maintenance_log.get("data", {})
            maint_event_id = Path(str(maintenance_log.get("filename", ""))).stem
            maintenance_events.append(
                {
                    "event_id": maint_event_id,
                    "date": _extract_log_date(maint_data),
                    "suite": maint_data.get("reason"),
                    "type": maint_data.get("record_type"),
                    "status": maint_data.get("microscope_status_after"),
                }
            )

        history_rendered = instrument_history_template.render(
            display_name=display_name,
            qc_events=qc_events,
            maintenance_events=maintenance_events,
            chart_data_json=chart_data_json,
        )
        (instrument_dir / "history.md").write_text(history_rendered, encoding="utf-8")

        for log_entry in qc_logs + maintenance_logs:
            source_path = log_entry.get("source_path")
            if not isinstance(source_path, str):
                continue

            source_file = Path(source_path)
            event_id = source_file.stem
            event_payload = log_entry.get("data") if isinstance(log_entry.get("data"), dict) else {}
            try:
                raw_yaml_text = source_file.read_text(encoding="utf-8")
            except OSError:
                raw_yaml_text = yaml.safe_dump(event_payload, sort_keys=False)

            event_rendered = event_detail_template.render(
                event_id=event_id,
                date=_extract_log_date(event_payload),
                instrument=event_payload.get("microscope"),
                instrument_id=event_payload.get("instrument_id"),
                operator=event_payload.get("performed_by") or event_payload.get("service_provider"),
                raw_yaml_content=raw_yaml_text,
            )
            (docs_root / "events" / f"{event_id}.md").write_text(event_rendered, encoding="utf-8")

        nav_instrument_entries.append(
            {
                display_name: [
                    {"Specs": f"instruments/{instrument_id}/spec.md"},
                    {"History": f"instruments/{instrument_id}/history.md"},
                ]
            }
        )

    mkdocs_path = Path("mkdocs.yml")
    mkdocs_data: dict[str, Any] = {}
    if mkdocs_path.exists():
        try:
            mkdocs_data = yaml.safe_load(mkdocs_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            mkdocs_data = {}

    mkdocs_data["nav"] = [
        {"Home": "index.md"},
        {"System Status": "status.md"},
        {"Instruments": nav_instrument_entries},
    ]
    mkdocs_path.write_text(yaml.safe_dump(mkdocs_data, sort_keys=False, allow_unicode=True), encoding="utf-8")
