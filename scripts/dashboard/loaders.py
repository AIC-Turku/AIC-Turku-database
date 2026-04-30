"""Dashboard repository/YAML loaders.

This module owns filesystem and YAML loading concerns for the dashboard build.

It must not import scripts.dashboard_builder.

Responsibilities:
- facility.yaml loading
- vocabulary YAML loading for frontend assets
- generic YAML file discovery/loading
- instrument ledger loading after strict validation has selected valid IDs
- QC/maintenance event log indexing
- small date/status helpers needed by log loading and status derivation

It should not contain:
- dashboard page rendering
- canonical DTO construction internals
- LLM exports
- methods exports
- optical-path view DTO rendering
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

from scripts.validate import (
    DEFAULT_ALLOWED_RECORD_TYPES,
    validate_instrument_ledgers,
)

from scripts.build_context import (
    clean_text,
    normalize_instrument_dto,
)


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
    """Load vocabulary YAML files for JSON export to dashboard assets."""
    vocabs: dict[str, dict[str, Any]] = {}

    if not vocab_dir.exists():
        return vocabs

    for yaml_file in vocab_dir.glob("*.yaml"):
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if data and "terms" in data:
                vocabs[yaml_file.stem] = {term["id"]: term for term in data["terms"]}
        except Exception:
            # Keep the historical dashboard behavior: vocabulary export is best-effort.
            pass

    return vocabs


def _iter_yaml_files(base_dir: Path) -> Iterable[Path]:
    """Yield YAML/YML files below a directory in deterministic order."""
    if not base_dir.exists() or not base_dir.is_dir():
        return []

    return [
        path
        for path in sorted(base_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in {".yaml", ".yml"}
    ]


@dataclass
class YamlLoadError:
    path: str
    message: str


def _load_yaml_file(
    path: Path,
    load_errors: list[YamlLoadError] | None = None,
) -> dict[str, Any] | None:
    """Load a YAML file as a top-level mapping."""
    try:
        raw = path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(raw)
    except (OSError, yaml.YAMLError) as exc:
        if load_errors is not None:
            load_errors.append(YamlLoadError(path=path.as_posix(), message=str(exc)))
        return None

    return parsed if isinstance(parsed, dict) else None


def _print_yaml_error_report(load_errors: list[YamlLoadError]) -> None:
    """Print a compact, de-duplicated YAML load error report."""
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


def _print_agent_fix_prompt(
    load_errors: list[YamlLoadError],
    validation_issues: list[Any],
) -> None:
    """Print an agent-ready remediation prompt when build validation fails."""
    if not load_errors and not validation_issues:
        return

    print("\n=== AGENT_FIX_PROMPT_BEGIN ===", file=sys.stderr)
    print("You are fixing YAML validation/build failures in this repository.", file=sys.stderr)
    print("Tasks:", file=sys.stderr)
    print(
        "1. Repair malformed YAML files reported below so they parse as top-level mappings.",
        file=sys.stderr,
    )
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
    """Parse an ISO datetime and normalize it to UTC."""
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
    """Extract a best-effort UTC timestamp from a dated event filename."""
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
    """Extract YYYY-MM-DD from a QC/maintenance event payload."""
    if not isinstance(log_entry, dict):
        return ""

    for key in ("started_utc", "timestamp_utc", "date"):
        parsed = _parse_iso_datetime(log_entry.get(key))
        if parsed is not None:
            return parsed.date().isoformat()

    return ""


def validated_instrument_selection(
    instruments_dir: str | Path = "instruments",
) -> tuple[set[str], list[Any], list[Any]]:
    """Resolve authoritative instrument IDs from validator output.

    Only instruments accepted by strict validation should enter downstream
    canonicalization and DTO/export production.
    """
    return validate_instrument_ledgers(instruments_dir=Path(instruments_dir))


def load_instruments(
    instruments_dir: str = "instruments",
    load_errors: list[YamlLoadError] | None = None,
    include_retired: bool = False,
    allowed_instrument_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Load instrument YAML files into canonical instrument records.

    `allowed_instrument_ids` is the validation gate. When provided, only IDs
    accepted by strict validation are loaded.
    """
    base = Path(instruments_dir)
    instruments: list[dict[str, Any]] = []

    for yaml_file in _iter_yaml_files(base):
        is_retired = "retired" in yaml_file.parts
        if is_retired != include_retired:
            continue

        payload = _load_yaml_file(yaml_file, load_errors=load_errors)
        if payload is None:
            continue

        normalized = normalize_instrument_dto(
            payload,
            yaml_file,
            retired=is_retired,
        )

        if normalized is None:
            if load_errors is not None:
                load_errors.append(
                    YamlLoadError(
                        path=yaml_file.as_posix(),
                        message=(
                            "Missing or invalid instrument.instrument_id "
                            "(must be URL-safe slug)."
                        ),
                    )
                )
            continue

        if allowed_instrument_ids is not None and normalized["id"] not in allowed_instrument_ids:
            continue

        instruments.append(normalized)

    instruments.sort(key=lambda item: item["id"])
    return instruments


def get_all_instrument_logs(
    log_base_dir: str,
    instrument_id: str,
    load_errors: list[YamlLoadError] | None = None,
    preindexed_logs: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Return all event logs for one instrument."""
    if not instrument_id or not instrument_id.strip():
        return []

    target_id = instrument_id.strip()

    if preindexed_logs is not None:
        return list(preindexed_logs.get(target_id, []))

    return list(
        index_instrument_logs(
            log_base_dir,
            load_errors=load_errors,
        ).get(target_id, [])
    )


def index_instrument_logs(
    log_base_dir: str,
    load_errors: list[YamlLoadError] | None = None,
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

        grouped_candidates.setdefault(instrument_id, []).append(
            (sort_dt, yaml_file, payload)
        )

    indexed_logs: dict[str, list[dict[str, Any]]] = {}

    for instrument_id, candidates in grouped_candidates.items():
        candidates.sort(key=lambda item: (item[0], item[1].as_posix()))

        indexed_logs[instrument_id] = [
            {
                "source_path": path.as_posix(),
                "filename": path.name,
                "data": payload,
            }
            for _, path, payload in candidates
        ]

    return indexed_logs


def evaluate_instrument_status(
    latest_qc: dict[str, Any] | None,
    latest_maint: dict[str, Any] | None,
) -> dict[str, str]:
    """Evaluate dashboard status from latest QC and maintenance event payloads."""
    last_qc_date = _extract_log_date(latest_qc)
    last_maint_date = _extract_log_date(latest_maint)

    maint_status = ""
    maint_reason = ""

    if isinstance(latest_maint, dict):
        raw_maint_status = latest_maint.get("microscope_status_after")
        if isinstance(raw_maint_status, str):
            maint_status = raw_maint_status.strip().lower()

        for key in (
            "status_notes",
            "reason_details",
            "action",
            "action_details",
            "reason",
        ):
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


def _allowed_record_types_from_arg(raw: str | None) -> tuple[str, ...]:
    """Parse CLI allowed record types."""
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


__all__ = [
    "YamlLoadError",
    "load_facility_config",
    "load_vocabularies",
    "_iter_yaml_files",
    "_load_yaml_file",
    "_print_yaml_error_report",
    "_print_agent_fix_prompt",
    "_parse_iso_datetime",
    "_timestamp_from_filename",
    "_extract_log_date",
    "validated_instrument_selection",
    "load_instruments",
    "get_all_instrument_logs",
    "index_instrument_logs",
    "evaluate_instrument_status",
    "_allowed_record_types_from_arg",
    "_event_output_instrument",
]
