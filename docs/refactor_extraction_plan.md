# Refactor Extraction Plan (Status Updated)

> Historical note: this document began as a pre-cleanup audit plan. The primary Python refactors are now completed; retained entrypoints are compatibility shims for API/CI stability.

## Current status

Completed splits:

- `scripts/dashboard_builder.py` is now a compatibility/CLI shim.
- `scripts/light_path_parser.py` is now a compatibility shim.
- `scripts/validate.py` is now a compatibility façade with a minimal module execution shim.
- Production implementations live in:
  - `scripts/dashboard/*`
  - `scripts/lightpath/*`
  - `scripts/validation/*`
- No `_impl.py` pattern is used.

Compatibility shims are intentionally retained for GitHub Actions and import/API compatibility while downstream references converge.

## Completed migration summary

- Dashboard view/export/render responsibilities were moved into focused modules under `scripts/dashboard/`.
- Canonical light-path parsing, route graphing, spectral operations, selected execution, and VM payload generation were moved into focused modules under `scripts/lightpath/`.
- Validation policy/vocabulary/instrument/event responsibilities were moved into focused modules under `scripts/validation/`.

## Known optional follow-ups

1. Optional VM legacy splitter parity hardening.
2. Optional production import cleanup from the `scripts.validate` façade.
3. Optional lazy `scripts.validation` package exports.

## Historical planning context

Detailed function-by-function extraction inventories in earlier revisions are retained in git history for provenance. They should not be interpreted as current pending work for the dashboard/lightpath/validation monolith split.
