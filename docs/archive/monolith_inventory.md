# Monolith Inventory — Pending Extraction

This file tracks large production monoliths that contain mixed responsibilities and
are pending extraction into separate focused modules.

See `docs/refactor_extraction_plan.md` for the full staged extraction plan.

---

## Status

| File | Lines | Status | Target modules |
|---|---|---|---|
| `scripts/light_path_parser.py` | ~4380 | **Pending split** | `scripts/lightpath/` (facades in place) |
| `scripts/dashboard_builder.py` | ~3504 | **Pending split** | `scripts/dashboard/` (facades in place) |
| `scripts/templates/virtual_microscope_app.js` | ~4154 | **Pending split** | `assets/javascripts/virtual_microscope/` |
| `scripts/templates/virtual_microscope_runtime.js` | ~3369 | **Pending split** | `assets/javascripts/virtual_microscope/` |
| `scripts/validate.py` | ~2237 | **Pending split** | `scripts/validation/` |
| `scripts/full_audit.py` | ~1057 | **Acceptable** | `scripts/audit/` |

---

## Extraction progress

### `scripts/lightpath/` — partial facade for `light_path_parser.py`

Extracted public API facades (re-export from monolith):

- `scripts/lightpath/__init__.py` — canonical public exports
- `scripts/lightpath/parse_canonical.py` — strict canonical parser API
- `scripts/lightpath/legacy_import.py` — legacy/migration API (audit/migration only)
- `scripts/lightpath/model.py` — DTO model helpers
- `scripts/lightpath/route_graph.py` — route graph helpers
- `scripts/lightpath/selected_execution.py` — selected execution helpers
- `scripts/lightpath/spectral_ops.py` — spectral ops helpers
- `scripts/lightpath/validate_contract.py` — contract validation
- `scripts/lightpath/vm_payload.py` — VM payload assembly

**Status**: Facades in place; monolith still contains all business logic. Next step: move
business logic to these modules and make the monolith a thin re-export wrapper.

### `scripts/dashboard/` — partial facade for `dashboard_builder.py`

Extracted public API facades (re-export from monolith):

- `scripts/dashboard/__init__.py` — canonical public exports
- `scripts/dashboard/instrument_view.py` — dashboard view DTO
- `scripts/dashboard/llm_export.py` — LLM export
- `scripts/dashboard/methods_export.py` — methods export
- `scripts/dashboard/optical_path_view.py` — optical path view DTO
- `scripts/dashboard/vm_export.py` — VM export
- `scripts/dashboard/loaders.py` — instrument loaders
- `scripts/dashboard/site_render.py` — site rendering
- `scripts/dashboard/build_context.py` — build context

**Status**: Facades in place; monolith still contains all business logic. Next step: move
business logic to these modules and make the monolith a thin re-export wrapper.

---

## Rules for monolith files

1. **Do not add new business logic** to monolith files. New logic goes in the extracted modules.
2. **Production callers should prefer** `scripts/lightpath/` and `scripts/dashboard/` over direct
   monolith imports for new code.
3. **Legacy import** (`scripts/lightpath/legacy_import.py`) is migration/audit-only — do not call
   from production dashboard, LLM, methods, or VM export paths.
4. **Strict canonical mode** is the default — compatibility_mode must be explicitly requested and
   is permitted only in audit/migration code.

---

## Next recommended extraction steps (in order)

1. Move `generate_virtual_microscope_payload` and related parser functions from
   `scripts/light_path_parser.py` to `scripts/lightpath/vm_payload.py`.
2. Move `import_legacy_light_path_model` / `migrate_instrument_to_light_path_v2` from
   `scripts/light_path_parser.py` to `scripts/lightpath/legacy_import.py` (currently just
   re-exported).
3. Move `build_llm_inventory_payload` / `_build_hardware_focus_summary` from
   `scripts/dashboard_builder.py` to `scripts/dashboard/llm_export.py`.
4. Move `build_methods_generator_instrument_export` from `scripts/dashboard_builder.py` to
   `scripts/dashboard/methods_export.py`.
5. Move `build_instrument_mega_dto` / `build_hardware_dto` from `scripts/dashboard_builder.py`
   to `scripts/dashboard/instrument_view.py`.
6. Split `scripts/validate.py` into `scripts/validation/policy.py`, `scripts/validation/vocab.py`,
   `scripts/validation/lightpath.py`, and `scripts/validation/events.py`.
7. Split JS monoliths into `assets/javascripts/virtual_microscope/` submodules once Python
   extraction is complete.
