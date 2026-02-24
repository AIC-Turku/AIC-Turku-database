"""Validation helpers and CLI for dashboard source ledgers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Any, Iterable

import yaml

DEFAULT_ALLOWED_RECORD_TYPES: tuple[str, ...] = ("qc_session", "maintenance_event")
ALLOWED_MAINTENANCE_STATUSES: tuple[str, ...] = ("in_service", "limited", "out_of_service")
INSTRUMENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
YEAR_PATTERN = re.compile(r"^\d{4}$")
ISO_YEAR_PATTERN = re.compile(r"^(\d{4})-")
FILENAME_DATE_PATTERN = re.compile(r"^(\d{4})-\d{2}-\d{2}(?:_|$)")


@dataclass
class ValidationIssue:
    code: str
    path: str
    message: str


def _iter_yaml_files(base_dir: Path) -> Iterable[Path]:
    if not base_dir.exists() or not base_dir.is_dir():
        return []
    return [p for p in sorted(base_dir.rglob("*")) if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}]


def _load_yaml(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return None, str(exc)

    if payload is None:
        return None, "YAML document is empty."
    if not isinstance(payload, dict):
        return None, f"Expected YAML mapping/object at top level, found {type(payload).__name__}."

    return payload, None


def _is_valid_instrument_id(value: str) -> bool:
    return bool(INSTRUMENT_ID_PATTERN.fullmatch(value))


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _get_started_year(payload: dict[str, Any], event_file: Path) -> str | None:
    started_utc = payload.get("started_utc")
    if isinstance(started_utc, str):
        started_match = ISO_YEAR_PATTERN.match(started_utc.strip())
        if started_match:
            return started_match.group(1)

    filename_match = FILENAME_DATE_PATTERN.match(event_file.stem)
    if filename_match:
        return filename_match.group(1)

    return None


def validate_instrument_ledgers(
    *,
    instruments_dir: Path = Path("instruments"),
) -> tuple[set[str], list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    instrument_ids: set[str] = set()
    instrument_id_to_files: dict[str, list[str]] = {}

    for instrument_file in _iter_yaml_files(instruments_dir):
        if "retired" in instrument_file.parts:
            continue

        payload, load_error = _load_yaml(instrument_file)
        if load_error is not None:
            issues.append(
                ValidationIssue(
                    code="yaml_parse_error",
                    path=instrument_file.as_posix(),
                    message=load_error,
                )
            )
            continue

        if payload is None:
            continue

        instrument_section = payload.get("instrument")
        if not isinstance(instrument_section, dict):
            issues.append(
                ValidationIssue(
                    code="missing_instrument_section",
                    path=instrument_file.as_posix(),
                    message="Missing required top-level mapping key 'instrument'.",
                )
            )
            continue

        instrument_id = instrument_section.get("instrument_id")
        if not isinstance(instrument_id, str) or not instrument_id.strip():
            issues.append(
                ValidationIssue(
                    code="missing_instrument_id",
                    path=instrument_file.as_posix(),
                    message="Missing required instrument.instrument_id (must be a non-empty string).",
                )
            )
            continue

        instrument_id = instrument_id.strip()
        if not _is_valid_instrument_id(instrument_id):
            issues.append(
                ValidationIssue(
                    code="invalid_instrument_id",
                    path=instrument_file.as_posix(),
                    message=(
                        "Invalid instrument.instrument_id; expected URL-safe slug "
                        "(lowercase letters, numbers, and single hyphens only)."
                    ),
                )
            )
            continue

        instrument_ids.add(instrument_id)
        instrument_id_to_files.setdefault(instrument_id, []).append(instrument_file.as_posix())

    for instrument_id, source_files in sorted(instrument_id_to_files.items()):
        if len(source_files) <= 1:
            continue
        source_list = ", ".join(sorted(source_files))
        issues.append(
            ValidationIssue(
                code="duplicate_instrument_id",
                path=instrument_id,
                message=f"Duplicate instrument.instrument_id '{instrument_id}' defined in: {source_list}.",
            )
        )

    return instrument_ids, issues


def validate_event_ledgers(
    *,
    instrument_ids: set[str],
    qc_base_dir: Path = Path("qc/sessions"),
    maintenance_base_dir: Path = Path("maintenance/events"),
    allowed_record_types: Iterable[str] = DEFAULT_ALLOWED_RECORD_TYPES,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    event_output_to_sources: dict[str, list[str]] = {}
    allowed_types = {value.strip() for value in allowed_record_types if isinstance(value, str) and value.strip()}
    allowed_maintenance_statuses = set(ALLOWED_MAINTENANCE_STATUSES)

    event_sources = [
        (qc_base_dir, "qc_session"),
        (maintenance_base_dir, "maintenance_event"),
    ]

    for base_dir, expected_type in event_sources:
        for event_file in _iter_yaml_files(base_dir):
            try:
                rel_parts = event_file.relative_to(base_dir).parts
            except ValueError:
                rel_parts = ()

            payload, load_error = _load_yaml(event_file)
            if load_error is not None:
                issues.append(
                    ValidationIssue(
                        code="yaml_parse_error",
                        path=event_file.as_posix(),
                        message=load_error,
                    )
                )
                continue

            if payload is None:
                continue

            microscope = payload.get("microscope")
            if not isinstance(microscope, str) or not microscope.strip():
                issues.append(
                    ValidationIssue(
                        code="missing_microscope",
                        path=event_file.as_posix(),
                        message="Missing required 'microscope' field.",
                    )
                )
                continue

            if microscope not in instrument_ids:
                known = ", ".join(sorted(instrument_ids))
                issues.append(
                    ValidationIssue(
                        code="unknown_microscope",
                        path=event_file.as_posix(),
                        message=(
                            f"Unknown microscope '{microscope}'. "
                            f"Expected one of instrument IDs in registry: {known}."
                        ),
                    )
                )

            if len(rel_parts) < 3:
                issues.append(
                    ValidationIssue(
                        code="invalid_event_path_structure",
                        path=event_file.as_posix(),
                        message=(
                            f"Expected event path under '{base_dir.as_posix()}' to follow "
                            "'<microscope>/<YYYY>/<file>.yaml'."
                        ),
                    )
                )
            else:
                path_microscope = rel_parts[0]
                path_year = rel_parts[1]

                if microscope != path_microscope:
                    issues.append(
                        ValidationIssue(
                            code="microscope_mismatch_with_path",
                            path=event_file.as_posix(),
                            message=(
                                f"Path microscope '{path_microscope}' does not match payload "
                                f"microscope '{microscope}'."
                            ),
                        )
                    )

                if not YEAR_PATTERN.fullmatch(path_year):
                    issues.append(
                        ValidationIssue(
                            code="invalid_event_year_folder",
                            path=event_file.as_posix(),
                            message=(
                                f"Invalid year folder '{path_year}'. Expected a 4-digit year "
                                "like '2026'."
                            ),
                        )
                    )
                else:
                    event_year = _get_started_year(payload, event_file)
                    if event_year is None:
                        issues.append(
                            ValidationIssue(
                                code="missing_event_year_source",
                                path=event_file.as_posix(),
                                message=(
                                    "Could not derive event year from payload.started_utc or "
                                    "filename date prefix (YYYY-MM-DD_...)."
                                ),
                            )
                        )
                    elif path_year != event_year:
                        issues.append(
                            ValidationIssue(
                                code="year_mismatch_with_path",
                                path=event_file.as_posix(),
                                message=(
                                    f"Path year '{path_year}' does not match derived event "
                                    f"year '{event_year}' from started_utc/filename."
                                ),
                            )
                        )

            record_type = payload.get("record_type")
            if not isinstance(record_type, str) or not record_type.strip():
                issues.append(
                    ValidationIssue(
                        code="missing_record_type",
                        path=event_file.as_posix(),
                        message="Missing required 'record_type' field.",
                    )
                )
            elif record_type not in allowed_types:
                allowed = ", ".join(sorted(allowed_types))
                issues.append(
                    ValidationIssue(
                        code="invalid_record_type",
                        path=event_file.as_posix(),
                        message=f"Invalid record_type '{record_type}'. Allowed values: {allowed}.",
                    )
                )
            elif record_type != expected_type:
                issues.append(
                    ValidationIssue(
                        code="unexpected_record_type_for_location",
                        path=event_file.as_posix(),
                        message=(
                            f"record_type '{record_type}' does not match expected value "
                            f"'{expected_type}' for files under '{base_dir.as_posix()}'."
                        ),
                    )
                )

            if record_type == "maintenance_event":
                required_maintenance_fields = (
                    "started_utc",
                    "service_provider",
                    "reason_details",
                    "action",
                )
                for field_name in required_maintenance_fields:
                    if _is_non_empty_string(payload.get(field_name)):
                        continue
                    issues.append(
                        ValidationIssue(
                            code="missing_maintenance_field",
                            path=event_file.as_posix(),
                            message=(
                                f"Missing required maintenance field '{field_name}' "
                                "(must be a non-empty string)."
                            ),
                        )
                    )

                has_maintenance_id = _is_non_empty_string(payload.get("maintenance_id"))
                has_event_id = _is_non_empty_string(payload.get("event_id"))
                if has_maintenance_id == has_event_id:
                    issues.append(
                        ValidationIssue(
                            code="invalid_maintenance_id_shape",
                            path=event_file.as_posix(),
                            message=(
                                "Maintenance events must include exactly one ID field: "
                                "either 'maintenance_id' or 'event_id'."
                            ),
                        )
                    )

                for status_key in ("microscope_status_before", "microscope_status_after"):
                    raw_status = payload.get(status_key)
                    if raw_status is None:
                        continue
                    if not _is_non_empty_string(raw_status):
                        issues.append(
                            ValidationIssue(
                                code="invalid_maintenance_status",
                                path=event_file.as_posix(),
                                message=(
                                    f"Invalid {status_key}: expected one of "
                                    f"{', '.join(ALLOWED_MAINTENANCE_STATUSES)}."
                                ),
                            )
                        )
                        continue

                    if raw_status.strip() not in allowed_maintenance_statuses:
                        issues.append(
                            ValidationIssue(
                                code="invalid_maintenance_status",
                                path=event_file.as_posix(),
                                message=(
                                    f"Invalid {status_key} '{raw_status}'. "
                                    "Use normalized lowercase values from: "
                                    f"{', '.join(ALLOWED_MAINTENANCE_STATUSES)}."
                                ),
                            )
                        )

            output_rel_path = f"events/{microscope}/{event_file.stem}.md"
            event_output_to_sources.setdefault(output_rel_path, []).append(event_file.as_posix())

    for output_rel_path, source_files in sorted(event_output_to_sources.items()):
        if len(source_files) <= 1:
            continue
        source_list = ", ".join(sorted(source_files))
        issues.append(
            ValidationIssue(
                code="duplicate_event_output_path",
                path=output_rel_path,
                message=f"Duplicate generated event path '{output_rel_path}' from: {source_list}.",
            )
        )

    return issues


def print_validation_report(issues: list[ValidationIssue]) -> None:
    if not issues:
        return

    print("\nValidation failures detected:", file=sys.stderr)
    for index, issue in enumerate(issues, start=1):
        print(f"  {index}. [{issue.code}] {issue.path}", file=sys.stderr)
        print(f"     {issue.message}", file=sys.stderr)
    print(f"\nTotal validation failures: {len(issues)}", file=sys.stderr)


def main() -> int:
    instrument_ids, issues = validate_instrument_ledgers()
    issues.extend(validate_event_ledgers(instrument_ids=instrument_ids))

    if issues:
        print_validation_report(issues)
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
