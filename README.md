# Microscopy database, virtual microscope, methods generator, and AI planning exports

This repository is a YAML-driven source tree for a microscopy facility dashboard.

It does four things:

1. stores instrument, QC, maintenance, vocabulary, and policy data as versioned YAML,
2. builds a documentation site and per-instrument spec pages,
3. generates a browser-based virtual microscope for first-order light-path planning,
4. exports structured JSON for a methods generator page and an LLM-assisted experiment-planning workflow.

The generated site is built from repository data. The browser UI does not invent hardware that is not present upstream.

## What lives where

- `facility.yaml` — facility/site identity, public URLs, acknowledgements, branding, and small page-level defaults.
- `instruments/*.yaml` — active instrument ledgers.
- `instruments/retired/*.yaml` — retired instruments.
- `qc/sessions/**` — QC ledgers.
- `maintenance/events/**` — maintenance ledgers.
- `vocab/*.yaml` — controlled vocabularies.
- `schema/instrument_policy.yaml` — policy for required / conditional / optional instrument metadata.
- `scripts/validate.py` — schema + vocabulary validation and completeness auditing.
- `scripts/light_path_parser.py` — normalized light-path to virtual-microscope payload builder.
- `scripts/dashboard_builder.py` — site builder and JSON export generator.
- `docs/light_path_v2_migration.md` — canonical v2 light-path architecture and migration contract.
- `scripts/templates/virtual_microscope.html.j2` — virtual microscope page shell.
- `scripts/templates/virtual_microscope_app.js` — browser app logic.
- `scripts/templates/virtual_microscope_runtime.js` — route normalization, spectra handling, and propagation model.
- `scripts/templates/methods_generator.md.j2` — methods generator page.
- `scripts/templates/plan_experiments.md.j2` — LLM planning/export page.
- `dashboard_docs/assets/instruments_data.json` — browser-facing methods-generator export.
- `dashboard_docs/assets/llm_inventory.json` — LLM-facing inventory export.

## Data flow

The intended flow is:

`YAML ledgers -> validation / completeness audit -> normalized hardware -> DTO / JSON exports -> browser runtime`

Important consequences:

- route choice in the virtual microscope is driven by validated payload data, not by ad hoc browser inference,
- methods-generator blockers are derived from policy-driven completeness metadata,
- LLM planning exports include explicit known-vs-missing inventory metadata,
- vocabularies live in `vocab/*.yaml` and are referenced from policy rather than duplicated in multiple places.

### Canonical light-path architecture

The repository's canonical light-path authoring model is now documented in `docs/light_path_v2_migration.md`.

Canonical authoring structure:

- `hardware.sources`
- `hardware.optical_path_elements`
- `hardware.endpoints`
- `light_paths[]`
  - `id`
  - `name`
  - `illumination_sequence[]`
  - `detection_sequence[]`

Interpretation rules:

- ordered sequences are the primary topology source of truth,
- `modalities` on sources/elements/endpoints are validation aids only,
- branching/selectors/splitters must remain explicitly representable through `YAML -> schema/validator -> DTO -> consumers`,
- legacy `hardware.light_path.*` structures are migration-only compatibility layers, not canonical authoring targets.

## Virtual microscope

The virtual microscope is a planning tool for fluorescence microscopy. It is not a calibrated photon-budget engine.

### What it models

- configured excitation sources,
- route-tagged optical components,
- filter / cube / splitter choices,
- detector routing,
- fluorophore excitation and emission spectra,
- first-order propagated excitation and emission through the selected light path.

### What it does not claim

- absolute detected photon counts,
- microscope-specific calibration,
- detector gain behavior as a physically meaningful sensitivity knob,
- exact throughput without full measured vendor/filter data.

### Optical route selection

If a microscope exposes more than one valid optical route, for example confocal and epi, the UI now shows an explicit route selector.

That selector is populated from the validated / normalized payload (`available_routes`, `default_route`). The selected route controls:

- source availability,
- visible route-relevant optical components,
- detector routing,
- propagated spectra and simulation results.

If only one route is available, the selector stays hidden.

### Runtime strictness vs simulator approximations

The runtime now distinguishes between:

- **Strict hardware-truth mode (default):** honors only explicit validated graph data from canonical `light_paths` traversal, including route-owned `branches` blocks, explicit branch-local endpoint sequences, explicit route catalogs, and explicit detector selections. In this mode the runtime/UI do **not** auto-select missing routes, invent detector targets, create virtual detectors, or auto-repair blocked paths.
- **Approximation mode (explicit opt-in):** keeps usability-oriented simulator fallbacks for exploratory workflows (for example inferred route catalog fallback, default branch/target conveniences, and blocked-path auto-repair in the app).

Approximation behavior is non-authoritative by design and should not be interpreted as hardware source-of-truth.

### FPbase integration

Fluorophore spectra are loaded in this order:

1. FPbase detail payload spectra when present,
2. FPbase spectra API payloads when present,
3. bundled fallback records shipped with the runtime,
4. synthetic spectra generated from maxima only when no real spectrum is available.

The runtime keeps the spectrum provenance explicit. Examples include:

- `api`
- `detail`
- `bundled_cache`
- `synthetic`
- mixed labels such as `detail+synthetic`

Synthetic spectra are no longer presented as if they were FPbase spectra. Real FPbase or bundled spectra are used for overlap and propagation whenever available.

### Virtual microscope layout

The page now shows:

- route selection near the experiment controls,
- source controls in a compact row layout,
- a top-to-bottom propagated-path panel,
- propagated light beside the reference spectra panel for easier comparison.

### Dichroic spectral windows (preferred model)

For `multiband_dichroic` / `polychroic` components, the preferred representation is explicit
`transmission_bands` and/or `reflection_bands` (`center_nm` + `width_nm`).

Legacy `cutoffs_nm` remains supported for simple single-edge dichroics and backward-compatible
fallbacks, but should not be treated as the authoritative model for modern spinning-disk multiband
dichroics.

See `docs/dichroic_migration_note.md` for migration guidance and compatibility details.

## Methods generator

The methods generator consumes `dashboard_docs/assets/instruments_data.json` and builds deterministic, reviewable draft text from the exported DTO.

### Current behavior

- blocks generation when policy-critical metadata required for trustworthy method text is missing,
- hides empty hardware sections for the currently selected instrument,
- renders option details inline with the checkbox label when compact explanatory text is available,
- deduplicates repeated add-clicks for the same instrument/selection signature,
- groups some repeated hardware categories into cleaner sentences,
- appends acknowledgements from config,
- adds the xCELLigence acknowledgement when an xCELLigence instrument was actually used.

### Safety and robustness changes

- Jinja-to-JavaScript string injection was replaced with JSON config payloads embedded in `<script type="application/json">`.
- Config JSON is serialized safely for inline embedding.
- Instrument fetch failures now produce a user-facing message instead of a silent broken page.
- The methods page reads `methods_generation` blockers directly from the exported instrument JSON.

## LLM planning / file-generation workflow

The experiment-planning page is driven by `dashboard_docs/assets/llm_inventory.json`.

That export is designed to reduce ungrounded recommendations by including:

- facility identity,
- active microscopes only,
- structured instrument DTO data,
- `hardware_focus_summary` for quick hardware-first screening,
- null/missing-field inventory completeness,
- policy-derived missing required fields,
- policy-derived missing conditional fields,
- alias-fallback audit metadata.

The planning prompt instructs downstream assistants to use only the attached JSON as ground truth and to treat missing fields as unknown.

The page-level facility strings are injected through a JSON config block rather than raw string interpolation inside JavaScript.

## Validation and completeness auditing

`python scripts/validate.py` and the builder use `schema/instrument_policy.yaml` plus `vocab/*.yaml`.

The completeness audit is intended to report what is missing, not just fail without context. Missing entries now carry audit metadata such as:

- `path`
- `title`
- `section_id`
- `section_title`
- `used_by`
- alias information
- conditional-trigger state

That metadata is reused by the methods generator and LLM inventory export.

Repository-wide audit output can also be generated with:

```bash
PYTHONPATH=. python scripts/full_audit.py --repo-root . --json-out audit.json --markdown-out audit.md
```

That report summarizes:

- top missing required policy fields,
- top missing conditional policy fields,
- common alias-fallback paths,
- fields currently blocking trustworthy methods generation,
- virtual microscope readiness,
- FPbase/browser runtime contract health.

## Reusing this repository as a template

A new facility should usually only need to edit a small set of YAML/config files.

### Files to change first

1. `facility.yaml`
   - facility name
   - site URL
   - contact URL
   - acknowledgements
   - branding asset paths
   - optional page-level config such as methods-generator JSON URL or LLM inventory URL

2. `instruments/*.yaml`
   - instrument inventory and hardware metadata

3. `vocab/*.yaml`
   - only if your facility uses different canonical terms or additional controlled terms

4. `schema/instrument_policy.yaml`
   - only if your facility has a different completeness policy

5. `acknowledgements.yaml` (optional override)
   - only if acknowledgements should be maintained separately from `facility.yaml`

### What should not need editing for a new site

- virtual microscope browser logic,
- methods generator logic,
- builder logic,
- FPbase runtime logic.

If you find yourself editing application JavaScript just to change facility identity or acknowledgements, that is the wrong layer.

## Build and local development

Install the Python dependencies used by the builder and docs site.

```bash
pip install -r requirements-docs.txt
```

Build the dashboard and exports:

```bash
PYTHONPATH=. python scripts/dashboard_builder.py --no-strict
```

Use `--strict` when you want the build to exit non-zero on YAML / validation errors:

```bash
PYTHONPATH=. python scripts/dashboard_builder.py --strict
```

Serve the generated site locally:

```bash
mkdocs serve
```

Regenerate starter templates from policy files when schema/policy changes:

```bash
python scripts/generate_templates.py
```

## Tests

Run the full test suite:

```bash
PYTHONPATH=. pytest -q
```

The current suite covers:

- validation / completeness audit behavior,
- light-path parsing and route export,
- virtual microscope runtime propagation and FPbase spectrum provenance,
- methods generator browser behavior for acknowledgements, deduplication, and fetch failures,
- JSON script-config serialization safety,
- DTO export helpers used by the builder.

## Important limitations

### Upstream metadata limitations

The repository can still contain instruments or event ledgers with incomplete or legacy metadata. Those are surfaced by validation and completeness audits. They are not automatically invented away by the browser tools.

### Modeling limitations

The virtual microscope is a first-order planning simulator. It supports sensible relative comparisons and route-aware path checks, but it is not a substitute for calibrated transmission curves, detector characterization, or instrument-specific acceptance measurements.

### FPbase limitations

FPbase coverage is not complete for every fluorophore or state. When no real spectrum is available, the runtime falls back to a synthetic spectrum derived from maxima and labels that provenance explicitly.

### Builder strictness

`--strict` is useful for CI and policy cleanup. On repositories with legacy maintenance/QC ledgers, it may still fail until those ledgers are migrated to current policy.

## Notes for maintainers

- Keep vocab additions in `vocab/*.yaml` and reference them from policy.
- Prefer fixing payload/data-flow problems upstream instead of adding browser-only exceptions.
- Keep facility/site strings in `facility.yaml` or other small config files, not hardcoded in JavaScript.
- Treat generated methods text and LLM recommendations as assisted drafts that still require microscopy review.
