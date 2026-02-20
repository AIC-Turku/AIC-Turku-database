"""Helpers for building dashboards from instrument and log YAML ledgers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


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
