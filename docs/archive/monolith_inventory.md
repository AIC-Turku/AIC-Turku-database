# Monolith Inventory — Historical (Pre-refactor Snapshot)

> Historical note: this document reflects the pre-refactor state and is retained only for provenance. The dashboard, lightpath, and validation monoliths have since been split into focused modules; the old entrypoints are compatibility shims.

This file originally tracked large production monoliths pending extraction.
The split work has since been completed for the Python dashboard/lightpath/validation stack.

See `docs/refactor_extraction_plan.md` for current status and follow-up notes.

---

## Current status (post-refactor)

| File | Current role | Status | Implementation location |
|---|---|---|---|
| `scripts/light_path_parser.py` | compatibility shim | split completed | `scripts/lightpath/*` |
| `scripts/dashboard_builder.py` | compatibility/CLI shim | split completed | `scripts/dashboard/*` |
| `scripts/validate.py` | compatibility façade + minimal module execution shim | split completed | `scripts/validation/*` |
| `scripts/templates/virtual_microscope_app.js` | VM app template | separate track | JS/template scope |
| `scripts/templates/virtual_microscope_runtime.js` | VM runtime template | separate track | JS/template scope |
| `scripts/full_audit.py` | audit orchestrator | active | `scripts/audit/*` and audit modules |

---

## Historical extraction notes

The remaining sections in older revisions of this file captured an in-progress plan.
They are now superseded by implemented module boundaries:

- Dashboard implementations: `scripts/dashboard/*`
- Light-path implementations: `scripts/lightpath/*`
- Validation implementations: `scripts/validation/*`

No `_impl.py` pattern is used in these stacks.
