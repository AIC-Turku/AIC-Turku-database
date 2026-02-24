"""Validation helpers for dashboard source ledgers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Iterable

import yaml

DEFAULT_ALLOWED_RECORD_TYPES: tuple[str, ...] = ("qc_session", "maintenance_event")


@dataclass
class ValidationIssue:
    code: str
    path: str
    message: str


def _iter_yaml_files(base_dir: Path) -> Iterable[Path]:
    if not base_dir.exists() or not base_dir.is_dir():
        return []
    return [p for p in sorted(base_dir.rglob("*")) if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}]


def _load_yaml(path: Path) -> dict[str, Any] | None:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return payload if isinstance(payload, dict) else None


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

    event_sources = [
        (qc_base_dir, "qc_session"),
        (maintenance_base_dir, "maintenance_event"),
    ]

    for base_dir, _expected_type in event_sources:
        for event_file in _iter_yaml_files(base_dir):
            payload = _load_yaml(event_file)
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
