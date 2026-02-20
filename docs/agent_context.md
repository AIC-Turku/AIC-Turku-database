# AIC-Chronicle: Agent Context and Build Spec

## Project identity and end state

**Repo role:** “single source of truth” for a microscopy facility using a **GitOps** approach: all *state* that matters for operations (instrument config snapshots, QC results, maintenance history, benchmarks/thresholds) is stored as text in Git and evolves through PRs.

**End state goals**

1. **Inventory/registry:** Each microscope has a structured YAML description of configuration (modalities, hardware, objectives, detectors, lasers, software).
2. **QC ledger:** Each QC run creates a *self-contained* YAML file that:

   * records human inputs (e.g., power meter readings),
   * references raw artifacts in OMERO,
   * stores computed metrics (added later by scripts),
   * stores CI evaluation results (added by GitHub Actions comparing metrics to benchmarks).
3. **Maintenance ledger:** Each maintenance/service event creates a simple YAML record with minimal vocabulary + rich free text.
4. **Automation:** CI validates YAML structure and evaluates QC metrics against benchmarks.
5. **User interfaces:**

   * Jupyter notebooks for data entry + analysis pipelines.
   * (Later) a Streamlit UI for browsing instruments, plotting QC trends, and viewing maintenance timelines.

**Non-goals**

* GitHub is **not** the primary store for large binary QC datasets. Raw images and large logs belong in OMERO (or other object storage). Git stores pointers + derived metrics + small previews.

---

## 1) Repository structure (current and planned)

### Current (observed in repo)

* `instruments/` — instrument YAML files (one per microscope).
* `templates/` — microscope YAML template(s) (and eventually QC/maintenance templates).
* `qc/` — QC template(s) and eventually QC session YAMLs.
* `maintenance/` — maintenance template(s) and eventually maintenance event YAMLs.
* `notebooks/` — example notebook(s) for instrument management and GitHub pushing.
* `src/` — code used by notebooks
* `docs/` — stage notes and design docs.

### Planned conventions (agents should follow)

* `qc/sessions/<microscope>/<YYYY>/<qc_id>.yaml`
* `maintenance/events/<microscope>/<YYYY>/<maintenance_id>.yaml`
* `benchmarks/<microscope>.yaml` (thresholds per instrument) OR `benchmarks/<platform>.yaml` (shared thresholds) with optional overrides.

IDs should be stable and filesystem-safe:

* `microscope`: existing instrument identifier (the repo’s canonical ID).
* `qc_id`: `qc_<microscope>_<YYYYMMDDThhmmZ>_<suite>`
* `maintenance_id`: `maint_<microscope>_<YYYYMMDD>_<short_slug>`

---

## 2) Data model: what lives where

### 2.1 Instrument YAML (registry)

Authoritative description of microscope configuration. Created/edited via an instrument-management notebook (already present as an example) using a form-like UI. Instrument files live in `instruments/`.

**Agents:** Do not invent schema—use the repo templates as authoritative.

### 2.2 QC session YAML (ledger)

A QC session is **one run** of a QC suite (laser power, PSF, alignment, stage repeatability, etc.). One YAML per session.

QC YAML must support incremental enrichment:

* Humans enter **context** + **manual measurements**.
* Scripts later add **computed metrics**.
* CI later adds **evaluation**.

**Hard requirement:** humans do **not** manually assign pass/fail. CI does.

QC sessions reference raw artifacts stored externally (OMERO), plus optional previews stored in repo.

### 2.3 Maintenance YAML (ledger)

One YAML per service/maintenance intervention. Minimal vocabulary (reason/action/service_provider) + free-text details and follow-up.

**Hard requirement:** keep maintenance schema simple and diff-friendly.

---

## 3) External artifact strategy (OMERO-first)

### 3.1 Why OMERO

QC datasets are large: PSF z-stacks, multicolor bead stacks, stage repeatability series, laser stability logs, etc. GitHub is the wrong place for these. OMERO is the primary store for:

* raw images (OME-TIFF / vendor formats as appropriate),
* large time-series logs,
* analysis-ready intermediate products if large.

Git stores:

* YAML session metadata,
* computed scalar metrics,
* small previews (PNG), small plots.

### 3.2 Artifact referencing conventions

In QC YAML, `artifacts` is a list of objects:

* `artifact_id` (stable local key)
* `role` (raw_image / table / preview / report / other)
* `uri` (e.g., `omero://.../image/<id>`, `omero://.../dataset/<id>/file/<name>`, or repo-relative path)
* `description`
* optional checksums (`checksum_sha256`) for provenance.

Agents should implement helpers:

* `resolve_artifact_uri(...)` → fetches artifact (OMERO download / local file).
* `push_preview_to_repo(...)` → writes small images/plots into repo paths.

---

## 4) QC: what we measure (domains and minimal metric outputs)

**QC domains to support early**

1. **Laser power**

   * manual series: setpoint → power (linearity) and power-over-time (stability)
   * computed metrics: linearity regression, stability delta %, drift slope, etc.
2. **PSF / resolution**

   * computed metrics: FWHM x/y/z, fit quality (R²), optional SNR/SBR, bead selection notes.
3. **Alignment (multicolor beads)**

   * computed metrics: per channel-pair dx/dy/dz, 3D distance.
4. **Stage repeatability**

   * computed metrics: sigma_x, sigma_y (repeatability), optional drift if supported.

**Metric identifiers**

* Use stable, namespaced IDs: `laser.*`, `psf.*`, `coreg.*`, `stage.*`
* Include wavelength/pair in ID where relevant: `laser.linearity_r2_488`, `coreg.distance_488_561_um`
* Store units separately in `unit`.

---

## 5) QC file logic: human inputs vs computed vs evaluated

### 5.1 Separation of concerns (required)

QC YAML has three different writers:

1. **Human/editor notebook** writes:

   * `performed` narrative
   * `inputs_human` general checks
   * `laser_inputs_human` structured series + measurement position
2. **Analysis notebook / scripts** write:

   * `computed_provenance`
   * `metrics_computed`
3. **CI evaluator** writes:

   * `evaluation` block (overall + per-metric status, thresholds used)

Agents must ensure scripts:

* NEVER overwrite human-entered blocks.
* Only append/update script-owned sections.

### 5.2 Laser input structure (required)

Laser measurements are inherently series-based. YAML must support:

* `measurement_position`: one of `at_objective | pre_objective | fiber_output`
* `linearity_series`: per laser, points or CSV link
* `stability_series`: per laser + setpoint, inline timepoints or CSV link

Analysis derives trendable scalars from those series.

---

## 6) CI and benchmarks

### 6.1 YAML validation (CI job)

GitHub Action validates:

* YAML parses
* required fields exist
* schema_version matches expected
* IDs are unique / correctly formatted
* artifact references have expected shapes

Implementation may use:

* a JSONSchema or Pydantic model
* a lightweight custom validator

### 6.2 Metric evaluation (CI job)

GitHub Action loads:

* QC session YAML (`metrics_computed` + selected `inputs_human` if needed)
* benchmark file(s) (`benchmarks/...yaml`)
  Then writes/updates:
* `evaluation.overall_status`
* `evaluation.results[]` with thresholds used and optional messages

**Important:** evaluation is deterministic and reproducible:

* QC YAML includes `evaluation.benchmark_ref` with git hash/tag.

---

## 7) External Python code package (agents should create)

Create a small package in-repo in src Suggested structure:

`aic_chronicle/`

* `io/`

  * `yaml_io.py` (safe load/dump preserving formatting where possible)
  * `paths.py` (repo path conventions, ID generation)
* `models/`

  * pydantic models (optional) or typed dicts for QC/maintenance/instruments
* `git/`

  * `repo.py` (clone, branch, commit, push, PR helpers)
* `omero/`

  * `client.py` (connect, download, upload, get thumbnails)
* `qc/`

  * `laser.py` (linearity fit, stability delta %, drift slope)
  * `psf.py` (bead detection, PSF fit wrappers)
  * `coreg.py` (multichannel registration metrics)
  * `stage.py` (repeatability calculations)
* `eval/`

  * `benchmarks.py` (load thresholds, apply to metrics)
  * `evaluator.py` (write evaluation block)
* `viz/`

  * plotting utilities for trend charts and thumbnails
* `cli.py` (optional entrypoints for local use)

**Agent rule:** keep the first implementation minimal and testable. Avoid huge frameworks; prefer pure functions with clear I/O.

---

## 8) Implementation constraints and quality bar

### 8.1 Deterministic edits and PR hygiene

* Notebooks and scripts should create changes on a new branch.
* Commit message conventions:

  * `Add QC session <qc_id>`
  * `Compute metrics for <qc_id>`
  * `Add maintenance event <maintenance_id>`
* Avoid rewriting entire YAML files unnecessarily. Keep diffs tight.

### 8.2 Robust YAML handling

* Preserve ordering as much as possible (agents can use `ruamel.yaml` if allowed; otherwise carefully dump with PyYAML).
* Avoid injecting Python-specific tags.
* Keep all timestamps ISO-8601 UTC `...Z`.

### 8.3 Incremental enrichment

* Human notebook writes skeleton QC YAML even if analysis comes later.
* Analyzer can be run repeatedly; it should update computed fields idempotently.
* CI evaluation should be able to re-run without human intervention.

### 8.4 Error handling

* Missing OMERO artifact → write a structured error note in analysis output but don’t corrupt YAML.
* Partial metrics computed → write what is available; leave rest absent.
* Benchmarks missing → CI writes evaluation block stating “no benchmark available” and sets status to `review` or similar (define in schema).

---

## 9) What agents must read before generating code

Agents must ingest, in this order:

1. Repo `README.md` (project statement: GitOps registry of configs/QC/maintenance).
2. Repo templates:

   * instrument template(s) in `templates/`
   * QC template(s) in `qc/` or `templates/`
   * maintenance template(s) in `maintenance/` or `templates/`
3. Example notebook(s) in `notebooks/`:

   * especially patterns for cloning repo, editing YAML, and pushing PRs
4. Current stage doc: `docs/current_project_stage.md`

---
