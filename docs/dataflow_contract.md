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
6. A scientific relationship between two vocabularies is authored as a tag on the
   term that owns it and exported through the DTO, never restated downstream. The
   three the Methods generator needs are:
   - `vocab/modules.yaml` `tags.provides_capability` — which technique a module
     implements, exported on `modules[].provides_capability`;
   - `vocab/imaging_modes.yaml` `tags.requires_source_role` — the source role a
     technique cannot be performed without, exported on
     `route_identity.imaging_modes[].requires_source_role`;
   - `vocab/light_source_roles.yaml` `tags.forms_imaging_channel` — whether a
     source in that role produces an image channel, exported on the source's
     `forms_imaging_channel`.
   Each of these was once a table in browser JavaScript, and each had drifted from
   the vocabulary it copied: one carried module ids no record uses and missed one
   that a record does, another required a depletion beam for STED but not for
   RESOLFT, which use the same beam.

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
- Method-to-path association is authored, never inferred. `capabilities.*`
  declares what an instrument can do; `light_paths[].imaging_modes` and
  `light_paths[].contrast_methods` declare which physical path implements each
  method. `route_type` is the route family and must not be read as a method by
  any consumer, including settings/reporting prompts.
- `vocab/optical_routes.yaml` `covers` is a compatibility gate consumed by
  validation only. It never supplies a missing mapping, and an axis a term does
  not mention is unknown rather than empty.
- `hardware.sources[].role` is a property of the source on the light path, and it
  is instrument-global: one role per source, not one per method or per path. The
  role records what the beam does — excites, depletes, illuminates — and the method
  records the mechanism by which it does it. The Abberior's 775 nm beam is
  `depletion` under both STED and RESOLFT, because it depletes in both; that
  stimulated emission does the depleting under one and reversible photoswitching
  under the other is a fact about the technique, not about the laser.
  Consequently no publication sentence built from a role may name a mechanism:
  "Depletion was provided by ..." is correct for both, "Stimulated-emission
  depletion was provided by ..." was correct for neither, and the technique is
  named by the opening sentence the selected method produces. A path- or
  method-scoped role was considered and rejected: it would invalidate every role
  already recorded to fix prose that mechanism-neutral wording fixes on its own.
- An acquisition is one image set, and it may travel more than one physical light
  path: a brightfield overview and a fluorescence channel of the same field are one
  acquisition with two paths. The Methods Generator therefore offers methods, paths
  and filter positions as multi-select controls, describes each path in its own
  sentence rather than merging them, and asks the author to confirm a second path
  that no selected method explains.
- A configuration the record says the instrument cannot produce is questioned,
  never asserted and never silently allowed. The checks are computed from recorded
  values only: a filter position is not offered on a route whose recorded positions
  could not serve it, a source whose recorded emission cannot pass a selected
  filter's recorded excitation window is queried, a splitter recorded as feeding
  its branches at once is queried when fewer detectors are reported than it feeds,
  and a specialist module is withdrawn when the technique its vocabulary record
  says it provides is no longer selected. None of them decides on the author's
  behalf; each asks, or declines to offer an answer that cannot be right.
- Acquisition state is scoped to the acquisition. Starting another acquisition,
  naming a different acquisition reference, or changing the imaging method clears
  the hardware selections, the confirmed actions and any reviewed runtime plan, so
  nothing carries into the next entry unstated.
- A fact confirmed by checkbox is a real choice, never a repeat of one already
  made. A recorded light path is asked as a visible question only when the
  selected method is genuinely recorded on two or more physically different
  paths with different hardware - in the current catalogue this never happens,
  so the control stays hidden and the path is confirmed silently, the way a
  method recorded on exactly one path always was. A record with no
  imaging-method control at all still asks explicitly, because the path is then
  the only thing left to state. The same rule applies to acquisition software:
  one recorded row could not have produced an image any other way and is
  reported without confirmation; two or more rows - several LAS X modules, a
  camera suite alongside a separate control package - is a real question about
  which one this acquisition used, and stays a checkbox.
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
