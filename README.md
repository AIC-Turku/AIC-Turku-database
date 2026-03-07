# AIC Turku Microscopy Database & Dashboard

Welcome to the **AIC Turku Microscopy Database & Dashboard** repository. This repository is the operational source of truth for the **Advanced Imaging Core Facility at Turku Bioscience Centre** and tracks instrument configurations, controlled vocabularies, QC outcomes, and maintenance history as versioned YAML ledgers.

➡️ **Generated dashboard:** https://aic-turku.github.io/AIC-Turku-database/

---

## Facility Identity & Configuration

Facility-specific branding and user-facing copy are centralized in `facility.yaml`.

This includes:
- facility naming (`short_name`, `full_name`, `site_name`)
- public URLs (`public_site_url`, `contact_url`, `organization_url`)
- default acknowledgements text
- visual branding assets (`logo`, `favicon`)

For AIC Turku deployments, keep `facility.yaml` as the canonical location for names, links, and acknowledgements. If this repository is reused for another facility, update `facility.yaml` and run:

```bash
python scripts/dashboard_builder.py --strict
```

---

## Repository Structure & Data Model

- `instruments/` — Authoritative YAML descriptions of active microscope configurations (with `instruments/retired/` for decommissioned systems).
- `qc/sessions/**/<year>/` — QC ledgers with human measurements, artifact pointers, and derived metrics.
- `maintenance/events/**/<year>/` — Maintenance ledgers for repairs, preventive maintenance, and upgrades.
- `vocab/` — Controlled vocabularies defining canonical terms used across records.
- `scripts/`
  - `validate.py` — Schema and vocabulary validation.
  - `dashboard_builder.py` — Build engine that renders dashboard pages and JSON exports.
- `scripts/templates/` — Jinja templates used by the dashboard builder.
- `templates/` — Starter YAML templates for new instrument, QC, and maintenance records.

### Key Conventions

- **Stable routing ID**: `instrument.instrument_id` must be URL-safe and consistent with `microscope: <instrument_id>` references in ledgers.
- Invalid or inconsistent IDs can cause strict validation/build failures.

---

## AIC Turku Workflows

### 1. Add or Modify an Instrument
1. Copy `templates/microscope_template.yaml` into `instruments/<instrument_id>.yaml`.
2. Fill metadata using canonical IDs from the generated vocabulary dictionary page.
3. *(Optional)* Add `assets/images/<instrument_id>.jpg`.

### 2. Log a QC Session
1. Copy `templates/QC_template.yaml` into `qc/sessions/<instrument_id>/<YYYY>/`.
2. Name it `qc_<instrument_id>_<YYYYMMDDThhmmZ>_<suite>.yaml`.
3. Populate context + metrics.

### 3. Log a Maintenance Event
1. Copy `templates/maintenance_template.yaml` into `maintenance/events/<instrument_id>/<YYYY>/`.
2. Name it `maint_<instrument_id>_<YYYYMMDD>_<short_slug>.yaml`.
3. Use allowed maintenance vocab IDs and include free-text notes.

---

## AI & LLM Integrations

- `dashboard_docs/assets/llm_inventory.json` is generated for AI-assisted experiment planning.
- Vocabulary dictionary content is generated from `vocab/*.yaml` during dashboard build.
- Agent guidance is documented in `docs/agent_context.md`.

---

## Local Development


> [!IMPORTANT]
> This project currently targets **MkDocs 1.x**. If you see warnings about MkDocs 2.0 when running `mkdocs build --strict`, reinstall pinned docs dependencies:
>
> ```bash
> pip install --upgrade -r requirements-docs.txt
> ```

```bash
# 1. Install dependencies
pip install pyyaml jinja2 -r requirements-docs.txt

# 2. Validate + build
python scripts/dashboard_builder.py --strict

# 3. Serve locally
mkdocs serve
```

---

## About AIC Turku

The Advanced Imaging Core Facility (AIC Turku) at Turku Bioscience Centre supports microscopy and imaging workflows for researchers and maintains this ledger-driven dashboard to provide transparent instrument status, QC history, and maintenance documentation.
