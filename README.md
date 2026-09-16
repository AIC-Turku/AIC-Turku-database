# AIC microscopy database and planning tools

This repository contains the structured instrument database and public dashboard for the Cell Imaging and Cytometry Core (AIC) in Turku.

**Public dashboard:** https://aic-turku.github.io/AIC-Turku-database/

The project combines four related functions:

1. versioned YAML records for microscopes, QC, maintenance, and controlled vocabularies;
2. a searchable public instrument dashboard;
3. a browser-based Virtual Microscope for inspecting optical routes and first-order spectral propagation;
4. tools for experiment planning and microscopy methods reporting.

The YAML records are the authored source of truth. Generated pages and browser tools use validated, normalized representations of those records and do not fill missing hardware metadata by assumption.

## Public tools

### Instrument catalogue

The dashboard lists active microscopes, recorded capabilities, objectives, instrument status, and QC/maintenance history. Missing metadata are shown as missing rather than inferred.

### Objectives catalogue

The **Objectives** page combines objectives attached to microscopes with the separate spare pool. Installation, condition, and availability are represented separately. Optional objectives are not treated as shared spares unless the source data say so.

### Virtual Microscope

The Virtual Microscope lets users inspect the recorded optical routes of a microscope and compare excitation/emission spectra against the configured sources, filters, splitters, and detectors.

It is a planning and visualization tool, not a calibrated photon-budget model. It does not claim absolute photon counts, measured system throughput, or detector performance that is not present in the source data.

### Methods generator

The methods generator builds a reviewable draft from the microscope inventory. Users state the imaging method they used, confirm the physical light path the record associates with it, then select the hardware and acquisition actions on that path before adding acquisition-specific settings for publication.

The generated text is intended as a reporting aid and is structured around QUAREP-LiMi reporting recommendations. It does not reconstruct historical configurations or replace acquisition metadata.

### Experiment planning

The experiment-planning page provides a structured inventory export that can be attached to an AI assistant. The accompanying prompt tells the assistant to use the inventory as its hardware source, preserve explicit unknowns, and identify details that still need confirmation with facility staff.

## Repository structure

- `facility.yaml` — facility identity, public URLs, acknowledgements, branding, page-level defaults, and the instrument records withheld from the public site.
- `instruments/*.yaml` — active instrument records.
- `instruments/retired/*.yaml` — retired instruments.
- `qc/sessions/**` — QC records.
- `maintenance/events/**` — maintenance records.
- `vocab/*.yaml` — controlled vocabularies.
- `schema/instrument_policy.yaml` — instrument metadata policy.
- `scripts/build_context.py` — canonical build context and DTO transfer hub.
- `scripts/validation/*` — validation and completeness logic.
- `scripts/lightpath/*` — optical-path normalization and route logic.
- `scripts/dashboard/*` — dashboard generation and exports.
- `scripts/planning_eval.py` — offline grounding check for saved planning answers.
- `scripts/templates/*` — public page templates and browser runtime.
- `docs/dataflow_contract.md` — production data-flow and module contract.
- `docs/ledger_gaps.md` — generated list of the facts the instrument records do not yet hold, and the questions they raise for facility staff.
- `docs/light_path_model.md` — canonical light-path authoring model.
- `docs/objective_pool.md` — objective catalogue source boundaries and maintenance notes.
- `docs/portability.md` — what another facility must edit to reuse this project.
- `docs/planning_grounding.md` — what the planning export establishes, and how to check an assistant's answer.

Compatibility entry points such as `scripts/validate.py`, `scripts/light_path_parser.py`, and `scripts/dashboard_builder.py` remain available for existing workflows.

## Data flow

The intended production flow is:

`YAML records -> validation/completeness -> normalized hardware -> canonical DTOs/exports -> public tools`

Key rules:

- YAML remains the authored source of truth.
- Canonical DTOs are the downstream source of truth.
- Missing required canonical fields produce diagnostics rather than silent defaults.
- Optical-route topology comes from validated route data, not browser-side inference.
- Controlled vocabulary lives in `vocab/*.yaml` rather than duplicated private mappings.
- Legacy adapters are compatibility or migration paths, not alternative canonical models.

## Canonical light-path model

The current authoring structure is documented in `docs/light_path_model.md` and uses:

- `hardware.sources`
- `hardware.optical_path_elements`
- `hardware.endpoints`
- `light_paths[]`
  - `id`
  - `name`
  - `illumination_sequence[]`
  - `detection_sequence[]`

Ordered route sequences are the primary topology source. Branches, splitters, and selectors remain explicit through the YAML, validation, DTO, and browser layers.

For multiband dichroics and polychroics, describe the windows explicitly with `transmission_bands` and, where known, `reflection_bands`; each band is a `{center_nm, width_nm}` object. Explicit bands are authoritative wherever they are present.

Legacy encodings still parse. A single-edge dichroic remains valid through `cut_on_nm` or a single-value `cutoffs_nm`. A multiband dichroic given only `cutoffs_nm` is simulated by alternating pass/stop bands at each cutoff, which is an approximation: real multiband transmission is not a square wave between edges, so cutoff-only multiband records should be replaced with explicit bands rather than relied on.

## Virtual Microscope model

The simulator can use:

- configured excitation sources;
- route-owned optical components;
- filter, cube, and splitter positions;
- detector routing;
- fluorophore excitation and emission spectra;
- first-order spectral propagation through the selected path.

The default runtime follows explicit validated route data. Approximation behavior, where available, is non-authoritative and must be explicitly enabled.

Fluorophore spectra can come from FPbase, bundled records, or synthetic spectra derived from maxima when no measured spectrum is available. Spectrum provenance remains explicit so synthetic curves are not presented as measured FPbase spectra.

## Methods reporting

The methods generator consumes `dashboard_docs/assets/instruments_data.json` and builds deterministic draft text from the exported instrument DTOs.

It follows the order an acquisition actually has:

`method used -> the physical light path that implements it -> hardware recorded on that path -> Methods prose`

The imaging method is asked first, because it is the thing a user reliably knows.
The instrument record states which light path implements each method, so choosing
a method reveals only the compatible path (or, where several are recorded, asks
which one was used). Route-specific sources, filters, splitters and detectors stay
hidden until that decision is made, and changing the method or the path clears
route-specific selections so stale hardware cannot follow into the next entry.
One acquisition travels one path.

It can:

- flag missing policy-critical metadata;
- show only hardware recorded for the selected instrument and the chosen light path;
- include confirmed acquisition actions and reviewed simulator configurations;
- preserve separate acquisition references for repeated use of the same microscope;
- add configured facility acknowledgements.

A method is never inferred from a route family: `confocal_point` does not imply
STED, and `widefield_fluorescence` does not imply TIRF. See
`docs/light_path_model.md` for the authoring rules and the validation
codes that enforce them.

The user remains responsible for checking acquisition-specific settings and placeholders before publication.

## Assistant-ready inventory export

`dashboard_docs/assets/llm_inventory.json` contains an assistant-ready view of the active instrument inventory. It includes structured hardware, route data, operational status, and completeness information.

The planning workflow is designed so that missing fields remain unknown. The prompt asks downstream assistants to recommend only recorded instruments and routes and to separate known facts from assumptions and caveats.

The export opens with a `planning_contract` block stating which lists are complete enumerations (so a component absent from a route is not on that route), that no booking or training availability is recorded at all, what an instrument status is derived from, and that objectives are recorded per instrument rather than per route. `route_family_coverage` and each instrument's `capability_route_reconciliation` relate capability terms such as `tirf` or `sted` to the route families that record them, so a planner does not have to invent a route type that the vocabulary does not contain. Within that block, `methods_by_recorded_light_path` gives the stronger, authored statement: the specific light path the facility records as implementing each method. Prefer it over family coverage, which says only that a method is compatible with a family.

A saved assistant answer can be checked offline against the inventory:

```bash
PYTHONPATH=. python -m scripts.planning_eval \
    --inventory dashboard_docs/assets/llm_inventory.json \
    --response saved_answer.md
```

It reports instrument or component IDs that are not recorded, components attached to a route they are not on, simultaneous use of mutually exclusive detection branches, and availability claims the inventory cannot ground. It calls no model and no network. See `docs/planning_grounding.md`.

## Validation and completeness

Run validation with:

```bash
python -m scripts.validate
```

The validator uses repository policy and controlled vocabularies to check authored data and report missing or inconsistent metadata.

A repository-wide audit can be generated when needed with:

```bash
PYTHONPATH=. python scripts/full_audit.py --repo-root . --json-out audit.json --markdown-out audit.md
```

Generated audit output is intended for local/CI review and should not be committed as permanent project documentation unless it documents an enduring contract.

## Build locally

Install the documentation dependencies:

```bash
pip install -r requirements-docs.txt
```

Build the dashboard and exports:

```bash
PYTHONPATH=. python scripts/dashboard_builder.py --no-strict
```

For CI/policy work, use the strict build:

```bash
PYTHONPATH=. python scripts/dashboard_builder.py --strict
```

Serve the generated site:

```bash
mkdocs serve
```

Regenerate starter templates after policy/schema changes with:

```bash
python scripts/generate_templates.py
```

## Tests

Install the test dependencies and Chromium, then run:

```bash
pip install -r requirements-test.txt
python -m playwright install chromium
PYTHONPATH=. pytest -q
```

The suite covers validation, completeness, canonical route export, browser propagation, spectrum provenance, methods-generator behavior, config serialization, and dashboard/DTO contracts.

## Withholding a record from the public site

Some ledger records exist for testing rather than for researchers. List their IDs
under `facility.non_public_instrument_ids` to keep them out of the generated site:

```yaml
facility:
  non_public_instrument_ids: [scope-testx1]
```

Withheld records are still loaded, validated, and available to the test suite. They
are removed from navigation, generated instrument/history/event pages, the site
search index, the objective catalogue, the Methods generator inventory, and the
Virtual Microscope. IDs must be explicit, unique, and known: a renamed or deleted
record fails the build rather than silently reappearing on the public site.
Exclusions are never inferred from display names, notes, or manufacturers.

This is the single authored list for withholding a record. `objective_catalogue.
exclude_instrument_ids` remains available for the narrower case of dropping an
instrument's objectives from the catalogue while the instrument itself stays
published.

## Reusing the project for another facility

A new facility should normally start by changing:

1. `facility.yaml` for facility identity, links, acknowledgements, and branding;
2. `instruments/*.yaml` for the local microscope inventory;
3. `inventory/objective_pool.yaml` for the local spare pool — this file is required, and the build fails before writing any page if it is missing or invalid;
4. `vocab/*.yaml` only when additional controlled terms are required;
5. `schema/instrument_policy.yaml` only when the local completeness policy differs;
6. `facility.non_public_instrument_ids` for any local fixture records that must not be published.

Facility identity and data belong in configuration/YAML. A new deployment should not need browser-code changes simply to rename the facility or change acknowledgements.

`mkdocs.yml` is generated by the dashboard build from `facility.yaml` and the instrument ledger, so site name, site URL, branding and navigation follow configuration rather than being edited by hand.

Pages that address visitors — "contact ... staff", "microscopes available at ..." — use `facility.short_name` (falling back to `full_name`). Acknowledgements that apply to one instrument are declared under `facility.acknowledgements.additional[]` and bound to recorded instrument IDs:

```yaml
facility:
  acknowledgements:
    standard: "Imaging was performed at ..."
    additional:
      - text: "Testament funds from Henna Ruusunen also supported this work."
        instrument_ids: [scope-agilent-rtca-esight]
```

An unknown instrument ID fails the build rather than silently dropping the acknowledgement.

`docs/portability.md` records the complete minimum-edit list, what is reused unchanged, and the AIC-specific assumptions that intentionally remain. `tests/test_facility_portability.py` builds a synthetic second facility end to end and asserts that no generated page names AIC.

## Limitations

- Some legacy instrument and event records may still have incomplete metadata; validation reports these gaps rather than filling them automatically.
- The Virtual Microscope supports route-aware, first-order comparison but is not a substitute for measured transmission curves, detector characterization, or system calibration.
- FPbase coverage is not complete for every fluorophore or state; fallback spectra retain explicit provenance.
- Strict builds may surface legacy QC or maintenance records that still need migration.

## Maintainer principles

- Add vocabulary terms in `vocab/*.yaml` rather than private downstream mappings.
- Fix data-flow problems upstream instead of adding browser-only exceptions.
- Keep facility/site strings in `facility.yaml` or other small configuration files.
- Preserve explicit unknowns.
- Treat methods text and assistant recommendations as drafts that require microscopy review.
