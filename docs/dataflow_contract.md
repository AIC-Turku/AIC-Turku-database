# Dataflow Contract

## Authoritative dataflow

```text
YAML instrument specs
-> schema/policy validation
-> canonical instrument DTO
-> canonical light-path DTO
-> derived view/export DTOs
-> dashboard display / LLM inventory / methods export / VM export / audit reporting
```

## Production module map

### Dashboard

| Module | Role |
|---|---|
| `scripts/dashboard_builder.py` | CLI entrypoint / compatibility shim only |
| `scripts/dashboard/loaders.py` | loading, validation adapters, instrument status |
| `scripts/dashboard/instrument_view.py` | dashboard instrument DTOs |
| `scripts/dashboard/optical_path_view.py` | optical-path dashboard DTOs |
| `scripts/dashboard/llm_export.py` | LLM inventory export |
| `scripts/dashboard/methods_export.py` | methods export DTOs |
| `scripts/dashboard/vm_export.py` | VM aggregation adapters |
| `scripts/dashboard/site_render.py` | site rendering / MkDocs orchestration |
| `scripts/build_context.py` | canonical build context and DTO transfer hub |

### Lightpath

| Module | Role |
|---|---|
| `scripts/light_path_parser.py` | compatibility shim only |
| `scripts/lightpath/model.py` | constants and primitive helpers |
| `scripts/lightpath/parse_canonical.py` | canonical v2 parsing and strict/non-strict canonicalizers |
| `scripts/lightpath/legacy_import.py` | legacy import adapter (migration/audit tooling only) |
| `scripts/lightpath/route_graph.py` | hardware inventory, graph nodes/edges, route usage |
| `scripts/lightpath/selected_execution.py` | selected route execution projection |
| `scripts/lightpath/spectral_ops.py` | component payloads and spectral ops |
| `scripts/lightpath/validate_contract.py` | contract validation |
| `scripts/lightpath/vm_payload.py` | VM payload assembly |

### Validation

| Module | Role |
|---|---|
| `scripts/validate.py` | CLI / compatibility façade only |
| `scripts/validation/model.py` | datamodels |
| `scripts/validation/vocabulary.py` | vocabulary |
| `scripts/validation/io.py` | YAML/file helpers |
| `scripts/validation/policy.py` | policy loading and rule resolution |
| `scripts/validation/events.py` | event-ledger validation |
| `scripts/validation/instrument.py` | instrument-ledger validation and completeness |
| `scripts/validation/reporting.py` | report printing and CLI orchestration |

## Canonical DTOs

- `inst["canonical"]` — instrument canonical DTO
- `inst["lightpath_dto"]` — canonical parser payload from `generate_virtual_microscope_payload`
- strict production gate: `canonicalize_light_path_model_strict(...)`

## Derived DTOs (non-authoritative)

- Dashboard display DTO: `inst["dto"]`
- Optical-path view DTO: `build_optical_path_view_dto(...)`
- Methods export view DTO: `methods_view_dto`
- LLM derived summaries: `llm_context.derived_summaries`

## Downstream product inputs

- Dashboard pages: `inst["dto"]` (derived from canonical DTOs)
- LLM inventory: canonical instrument DTO + canonical lightpath DTO + explicitly derived summaries
- Methods page data: methods export DTO built from canonical hardware/software/lightpath
- Virtual microscope export: deep copy of canonical light-path DTO (`context.vm_payload`)
- Audit/reporting: validator-gated instruments + explicit compatibility checks

## Diagnostics behavior

Shared diagnostics shape:
- `severity`
- `code`
- `path`
- `message`
- `source`
- `affected_export`

Rules:
- Missing required production data => `error` and export blocking for affected export.
- Missing optional display data => `warning`.
- No authoritative fallback via generic labels such as `Unknown`.

## Prohibited patterns (audit)

- `yaml.safe_load` in validator/loaders/import scripts: **allowed** (canonical parsing).
- `legacy` references in `light_path_parser.py`, `validate.py`, `migrate_light_paths.py`, `full_audit.py`: **allowed** (legacy compatibility/audit only).
- `fallback` in display labels and simulator-only role helpers: **allowed** (non-authoritative, display-only).
- VM export from dashboard DTO: **forbidden** (VM export uses canonical lightpath DTO).
- LLM/methods export from VM payload: **forbidden** (not present in production builders).
- Hardcoded route sort priority in production: **forbidden**.

## Adding new routes/modalities/components without downstream code changes

1. Author IDs and metadata in YAML under canonical schema fields.
2. Validate with policy/schema (validator catches legacy and missing required fields).
3. Ensure canonical parser emits route/component in `lightpath_dto`.
4. Downstream consumers carry IDs/order from canonical DTOs automatically.
5. Add/extend vocab entries for labels; do not add hardcoded ID maps in downstream code.

## Legacy and compatibility policy

- Legacy importers/adapters are scoped to `scripts/migrate_light_paths.py`,
  `scripts/lightpath/legacy_import.py`, and audit/validation checks
  (`scripts/full_audit.py`, `scripts/validate.py`).
- Production dashboard/LLM/methods/VM build paths must use strict canonical DTO flow
  and must not import legacy adapters.
- Legacy fixtures remain only for backward-compatibility and negative tests.
- VM runtime JS contains compatibility logic for broader payload tolerance; this is
  non-authoritative and must not be extended as a canonical data path.

## Critical contract notes

- LLM inventory records must carry canonical instrument and canonical lightpath context,
  not only dashboard DTO.
- Methods export must expose frontend-consumed top-level keys and `methods_view_dto`.
- VM branch auto-defaults are derived runtime initial state and must be marked
  non-authoritative.
- Canonical `light_paths` remain topology truth.
- Compatibility entrypoints are retained for CI/API compatibility, not implementation
  ownership.

## Software metadata semantics

- `software_status` is an optional canonical instrument field with supported values:
  - `documented`: software entries are expected in `software[]`.
  - `not_applicable`: no acquisition/control software applies (manual/standalone instrument).
  - `unknown`: software applicability has not yet been curated.
- Backward compatibility: if `software_status` is omitted, existing `software[]`-driven behavior remains unchanged.
- Use `not_applicable` only when instrument records confirm manual/standalone usage with no acquisition/control software workflow.
- Use `unknown` when applicability is not yet curated; do not treat it as `not_applicable`.
- `software[]` entries still follow existing conditional requirements (`role`, `name`, `version`).
