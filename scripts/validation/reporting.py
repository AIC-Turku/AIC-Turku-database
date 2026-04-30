from __future__ import annotations

import sys

from scripts.validation.events import validate_event_ledgers
from scripts.validation.instrument import validate_instrument_ledgers
from scripts.validation.model import ValidationIssue


def print_validation_report(issues: list[ValidationIssue], *, report_name: str = "failures") -> None:
    if not issues:
        return

    print(f"\nValidation {report_name} detected:", file=sys.stderr)
    for index, issue in enumerate(issues, start=1):
        print(f"  {index}. [{issue.code}] {issue.path}", file=sys.stderr)
        print(f"     {issue.message}", file=sys.stderr)
    print(f"\nTotal validation {report_name}: {len(issues)}", file=sys.stderr)


def main() -> int:
    instrument_ids, issues, warnings = validate_instrument_ledgers()
    event_report = validate_event_ledgers(instrument_ids=instrument_ids)
    issues.extend(event_report.errors)
    warnings.extend(event_report.warnings)

    if warnings:
        print_validation_report(warnings, report_name="warnings")

    if event_report.migration_notices:
        print_validation_report(event_report.migration_notices, report_name='migration notices')

    if issues:
        print_validation_report(issues)
        return 1

    print("Validation passed.")
    return 0
