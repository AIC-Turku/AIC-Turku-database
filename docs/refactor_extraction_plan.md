# Refactor Extraction Plan (Pre-cleanup Audit)

## Scope and evidence
Audited primary monoliths and adjacent modules for production logic placement and wrapper status.

Line counts:
- `scripts/dashboard_builder.py` — 3504
- `scripts/light_path_parser.py` — 4380
- `scripts/validate.py` — 2237
- `scripts/full_audit.py` — 1057
- `scripts/templates/virtual_microscope_runtime.js` — 3355
- `scripts/templates/virtual_microscope_app.js` — 4154
- `assets/javascripts/methods_generator_app.js` — 762
- `scripts/templates/methods_generator.md.j2` — 109

---

## Task 1 — Function inventory summary

> Note: Full top-level inventories are very large; this section classifies all top-level symbols by responsibility groups with representative anchors and ranges. No cleanup moves are executed in this step.

### `scripts/dashboard_builder.py`
- **dashboard view/export logic**: `build_optical_path_view_dto`, `build_optical_path_dto`, `build_hardware_dto`, `build_instrument_mega_dto`, `build_dashboard_instrument_view`, `hardware_renderables_from_inventory`.
- **methods export logic**: `build_methods_generator_page_config`, `build_methods_generator_instrument_export`.
- **LLM export logic**: `build_llm_inventory_payload`, `_build_hardware_focus_summary`, `_build_route_planning_summary`.
- **production orchestration / CLI**: `main`, `_parse_args`, `load_instruments`, `validated_instrument_selection`, page rendering and file-writing block.
- **display/template helpers**: large helper set (`clean_text`, `_spec_lines`, DTO row formatters).
- **risk**: mixed core derivation + rendering + CLI in one file.

### `scripts/light_path_parser.py`
- **canonical parser logic**: canonical parsing, normalization, graph construction, route steps, selected execution, VM payload assembly (`parse_canonical_light_path_model`, `_build_route_steps`, `_build_selected_route_steps`, `_build_route_sequences_and_graph`, `generate_virtual_microscope_payload`).
- **validation logic**: `validate_light_path*`, `validate_light_path_diagnostics`.
- **migration-only legacy logic**: `import_legacy_light_path_model`, `migrate_instrument_to_light_path_v2`, legacy import helpers.
- **risk**: production parser + validation + legacy migration in same monolith.

### `scripts/validate.py`
- **validation logic**: policy/vocab classes, instrument/event validation, completeness reports.
- **production orchestration / CLI**: `main`.
- **legacy detection logic**: `_legacy_instrument_topology_paths`, canonical overlay for checks.
- **risk**: policy engine + file I/O + CLI + event/instrument concerns in one file.

### `scripts/full_audit.py`
- **audit-only logic**: VM audit, runtime audit, report generation.
- **production orchestration / CLI**: `main`, argument parsing.
- **risk**: mixed audit domains (yaml load, VM contract, JS authority, report rendering) in one file.

### `scripts/templates/virtual_microscope_runtime.js`
- **VM runtime logic** only, but highly mixed responsibilities:
  - contract normalization
  - route/traversal materialization
  - spectral ops + simulation
  - optimization
  - FPbase/local spectra normalization
- **risk**: oversized runtime with multiple separable subdomains.

### `scripts/templates/virtual_microscope_app.js`
- **VM app logic** only, but mixed:
  - state/store
  - route/topology controls
  - source/splitter/detector controls
  - charts and rendering
  - search/fetch integration
  - selection export
- **risk**: oversized UI app with tightly coupled concerns.

### `assets/javascripts/methods_generator_app.js`
- **methods export rendering/generation logic** (client-side), includes selection filtering and prose generation.
- **risk**: state + rendering + prose generation in one file (near split threshold).

### `scripts/templates/methods_generator.md.j2`
- **display/template helper** (page shell only). Low split urgency.

---

## Task 2 — Module destination map (production logic still in monoliths)

### From `scripts/light_path_parser.py`
- `_build_route_steps` → `scripts/lightpath/route_graph.py` (public API: no, priority: high)
- `_build_selected_route_steps` → `scripts/lightpath/selected_execution.py` (public API: no, high)
- `_build_route_sequences_and_graph` → `scripts/lightpath/route_graph.py` (public API: no, high)
- `_spectral_ops_for_component`, `_cube_spectral_ops`, `_extract_dichroic_spectral_data` → `scripts/lightpath/spectral_ops.py` (public API: internal, high)
- `validate_light_path_diagnostics` + validation helpers → `scripts/lightpath/validate_contract.py` (public API: yes, high)
- `generate_virtual_microscope_payload` + `_generate_virtual_microscope_payload_inner` → `scripts/lightpath/vm_payload.py` (public API: yes, high)
- legacy import helpers and adapters stay in `scripts/lightpath/legacy_import.py` (migration/audit only).

### From `scripts/dashboard_builder.py`
- `build_optical_path_view_dto`, `build_optical_path_dto`, inventory renderables → `scripts/dashboard/optical_path_view.py` (real implementation, high)
- `build_hardware_dto`, `build_instrument_mega_dto`, `build_dashboard_instrument_view` → `scripts/dashboard/instrument_view.py` (real implementation, high)
- `build_llm_inventory_payload`, `_build_hardware_focus_summary`, `_build_route_planning_summary` → `scripts/dashboard/llm_export.py` (real implementation, high)
- `build_methods_generator_instrument_export`, page config → `scripts/dashboard/methods_export.py` (real implementation, high)
- orchestration `main` and site file generation → `scripts/dashboard/site_render.py` (public CLI entrypoint preserved, medium)

### From `scripts/validate.py`
- policy models and evaluation → `scripts/validation/policy.py` (high)
- vocabulary + loading → `scripts/validation/vocab.py` (high)
- instrument ledger validation → `scripts/validation/instrument.py` (high)
- events validation → `scripts/validation/events.py` (high)
- strict lightpath gate checks → `scripts/validation/lightpath_gate.py` (medium)

### From `scripts/full_audit.py`
- VM audit → `scripts/audit/vm_audit.py`
- legacy topology audit → `scripts/audit/legacy_audit.py`
- cross-dataflow audit aggregation → `scripts/audit/dataflow_audit.py`
- report rendering → `scripts/audit/report_render.py`

### JS destinations
- `virtual_microscope_runtime.js` split into:
  - `runtime_contract.js`, `runtime_routes.js`, `runtime_traversal.js`, `runtime_spectral_ops.js`, `runtime_simulation.js`, `runtime_optimization.js`
- `virtual_microscope_app.js` split into:
  - `app_state.js`, `app_routes.js`, `app_controls_sources.js`, `app_controls_optics.js`, `app_controls_splitters.js`, `app_controls_detectors.js`, `app_charts.js`, `app_search.js`, `app_selection_export.js`
- `methods_generator_app.js` split into:
  - `methods_state.js`, `methods_render.js`, `methods_generation.js`, `methods_diagnostics.js`

---

## Task 3 — Wrapper audit

### `scripts/lightpath/*`
- `parse_canonical.py` — **thin public facade** (re-export only). Keep temporarily.
- `legacy_import.py` — **thin public facade** (re-export only). Keep temporarily (migration surface).
- `model.py` — **thin public facade** (re-export only). Keep temporarily.
- `vm_payload.py` — **thin public facade** (re-export only). Replace with real implementation module.
- `__init__.py` — **package facade**. Keep temporarily.

### `scripts/dashboard/*`
- `loaders.py` — thin facade.
- `instrument_view.py` — thin facade.
- `optical_path_view.py` — thin facade.
- `llm_export.py` — thin facade.
- `methods_export.py` — thin facade.
- `vm_export.py` — currently small real boundary helper (context call + deepcopy), but still delegates most production logic to monolith.
- `build_context.py` — facade to root build context.

**Verdict:** most new modules are accidental wrappers around monoliths and should be converted to real implementations before cleanup.

---

## Task 4 — Split-candidate audit

| current file | line count | mixed responsibilities | proposed split | priority | split risk | tests required before split |
|---|---:|---|---|---|---|---|
| scripts/light_path_parser.py | 4380 | canonical parser + legacy migration + validation + vm payload | lightpath/* family above | High | High (deep call graph) | parser contract tests, selected_execution tests, VM payload contract tests |
| scripts/dashboard_builder.py | 3504 | view derivation + methods + llm + site rendering + CLI | dashboard/* + site_render.py | High | High | dashboard DTO tests, methods export tests, llm export tests, static source-of-truth tests |
| scripts/templates/virtual_microscope_app.js | 4154 | state + controls + charts + search + export | assets/javascripts/virtual_microscope/app_* | High | Medium/High | VM app template tests, runtime integration smoke tests |
| scripts/templates/virtual_microscope_runtime.js | 3355 | contract + traversal + spectral + simulation + optimization | runtime_* modules | High | High | VM runtime tests (splitter/route/execution/simulation) |
| scripts/validate.py | 2237 | policy engine + vocab + file I/O + CLI + events | validation/* | Medium/High | Medium | instrument/event validation suites |
| scripts/full_audit.py | 1057 | multiple audit domains + report rendering + CLI | audit/* | Medium | Medium | full_audit tests + report rendering checks |
| assets/javascripts/methods_generator_app.js | 762 | state + filtering + prose generation | methods/* | Medium | Low/Medium | methods template/app tests |

---

## Task 5 — Cleanup readiness verdict

| file | current role | target role | production logic remaining? | can delete now? | can shrink to facade now? | blockers | required next step |
|---|---|---|---|---|---|---|---|
| scripts/dashboard_builder.py | monolith | thin facade + moved impl | Yes (substantial) | No | Not yet | huge call graph | extract llm/methods/view/site modules with tests |
| scripts/light_path_parser.py | monolith | thin facade + moved impl | Yes (substantial) | No | Not yet | parser/runtime dependency web | extract parser core + selected_execution + vm_payload impl |
| scripts/validate.py | monolith | module family + CLI | Yes | No | Not yet | shared policy helpers | split validation modules first |
| scripts/full_audit.py | monolith | audit orchestrator over audit/* | Yes | No | Eventually | mixed responsibilities | extract vm/legacy/report modules |
| scripts/templates/virtual_microscope_runtime.js | monolith runtime | runtime_* modules | Yes | No | No | no module boundaries | split by contract/traversal/simulation |
| scripts/templates/virtual_microscope_app.js | monolith app | app_* modules | Yes | No | No | tightly coupled DOM/state | split controls/charts/search/export/state |
| assets/javascripts/methods_generator_app.js | medium monolith | methods_* modules | Yes | No | Possibly | limited tests for split boundaries | split state/render/generation |
| scripts/templates/methods_generator.md.j2 | template | template shell | Minimal | No | N/A | low priority | keep as shell template |

**Overall verdict:** cleanup is **not ready**. Production logic remains in major monoliths; wrappers are mostly facades, not true extracted implementations.

---

## Task 6 — Staged migration plan

### Stage 1 — Move high-risk production logic out
1. Extract canonical parser internals (`route_graph`, `selected_execution`, `spectral_ops`, `vm_payload`) from `light_path_parser.py`.
2. Extract dashboard production derivations (`instrument_view`, `optical_path_view`, `methods_export`, `llm_export`) from `dashboard_builder.py`.

### Stage 2 — Update imports/callers
1. Monolith files call extracted modules.
2. Keep existing public APIs stable through temporary facades.

### Stage 3 — Add import compatibility tests
1. Verify public imports still resolve (`scripts.dashboard`, `scripts.lightpath`).
2. Add contract tests asserting source-of-truth boundaries (no dashboard DTO authority in VM/LLM/methods).

### Stage 4 — Quarantine obsolete functions
1. Mark moved monolith functions as deprecated internal shims.
2. Ensure no active dual production implementations.

### Stage 5 — Shrink monolith to facade/CLI
1. `dashboard_builder.py` retains CLI/site render orchestration only.
2. `light_path_parser.py` retains legacy migration and compatibility entrypoints only (or move to dedicated module and facade).
3. `validate.py` and `full_audit.py` become orchestrators over split modules.

### Stage 6 — Delete facades only after proof
1. Remove temporary facades only when imports/docs/CI no longer depend on them.
2. Keep migration/audit sidecars explicit and isolated.

---

## Tests needed before deletion
- Parser contract tests (canonical + selected execution + splitter behavior)
- VM payload contract + runtime strictness tests
- Dashboard view DTO derivation tests (counts/routes/diagnostics)
- LLM export canonical-boundary tests
- Methods export canonical-boundary tests
- Static source-of-truth/fallback guard tests
- Import-graph stability tests for `scripts.dashboard` and `scripts.lightpath`

