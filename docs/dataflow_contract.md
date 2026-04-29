# Dataflow Contract (Final Audit)

## Authoritative dataflow

```text
YAML instrument specs
-> schema/policy validation
-> canonical instrument DTO
-> canonical light-path DTO
-> derived view/export DTOs
-> dashboard display / LLM inventory / methods export / VM export / audit reporting
```

## Canonical DTOs

- `inst["canonical"]` (instrument canonical DTO)
- `inst["lightpath_dto"]` (canonical parser payload from `generate_virtual_microscope_payload`)
- strict production gate: `canonicalize_light_path_model_strict(...)`

## Derived DTOs (non-authoritative)

- Dashboard display DTO: `inst["dto"]`
- Optical-path view DTO: `build_optical_path_view_dto(...)`
- Methods export view DTO: `methods_view_dto`
- LLM derived summaries: `llm_context.derived_summaries`

## Downstream product inputs

- Dashboard pages: `inst["dto"]` (derived from canonical DTOs)
- LLM inventory: canonical/derived instrument DTO + canonical route contract from lightpath projections
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

## Final occurrence classification (audit)

- `yaml.safe_load` in validator/loaders/migration/import scripts: **allowed canonical parsing/migration**.
- `legacy` references in `light_path_parser.py`, `validate.py`, `migrate_light_paths.py`, `full_audit.py`: **allowed migration/audit**.
- `fallback` in display labels and simulator-only role helpers: **allowed display-only/simulator compatibility** (non-authoritative).
- VM export from dashboard DTO: **forbidden** (fixed; VM export uses canonical lightpath DTO).
- LLM/methods export from VM payload: **forbidden** (not present in production builders).
- hardcoded route sort priority in production: **forbidden** (removed).

## Adding new routes/modalities/components without downstream code changes

1. Author IDs and metadata in YAML under canonical schema fields.
2. Validate with policy/schema (validator catches legacy and missing required fields).
3. Ensure canonical parser emits route/component in `lightpath_dto`.
4. Downstream consumers will carry IDs/order from canonical DTOs automatically.
5. Add/extend vocab entries for labels; do not add hardcoded ID maps in downstream code.

## Remaining risks

- VM runtime JS still contains compatibility logic for broader payload tolerance.
- Legacy importer remains available by design for migration/audit tooling and must stay excluded from strict production paths.


## Legacy policy

- Legacy importers/adapters are quarantined to migration (`scripts/migrate_light_paths.py`, `scripts/lightpath/legacy_import.py`) and audit/validation checks (`scripts/full_audit.py`, `scripts/validate.py`).
- Production dashboard/LLM/methods/VM build paths must use strict canonical DTO flow and must not import legacy adapters.
- Legacy fixtures remain only for migration/negative tests and documentation.
