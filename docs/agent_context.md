# AIC-Turku Database: Agent Context (Current Snapshot)

This document is for automated agents working in this repository.
It intentionally describes only what exists **today** in this checkout.

## 1) Project purpose

This repository is the GitOps source of truth for AIC-Turku microscopy operations.
State is stored as YAML and rendered into a static dashboard.

Primary record classes:

- Instrument registry entries (`instruments/*.yaml`)
- QC session ledgers (`qc/sessions/**/<year>/*.yaml`)
- Maintenance event ledgers (`maintenance/events/**/<year>/*.yaml`)

## 2) Current repository structure (authoritative)

- `README.md` — human-facing workflow + conventions overview.
- `instruments/` — active instrument records.
- `instruments/retired/` — retired instrument records.
- `qc/sessions/` — QC session YAML files grouped by instrument + year.
- `maintenance/events/` — maintenance event YAML files grouped by instrument + year.
- `templates/` — source templates for new records:
  - `microscope_template.yaml`
  - `QC_template.yaml`
  - `maintenance_template.yaml`
- `scripts/dashboard_builder.py` — dashboard generation logic.
- `scripts/validate.py` — ledger validation helpers.
- `scripts/templates/` — Jinja templates used by dashboard generation.
- `mkdocs.yml` + `assets/` — MkDocs configuration and static assets.

## 3) What is authoritative right now

When instructions conflict, use this precedence order:

1. Actual repository contents and code behavior.
2. Template files in `templates/` for record shape.
3. Validation/build scripts in `scripts/` for enforced constraints.
4. `README.md` for workflow guidance.
5. This file (`docs/agent_context.md`) as orientation only.

## 4) Practical agent rules for this snapshot

- Do **not** assume directories that are not present (for example, no `notebooks/` and no `src/`).
- Do **not** reference `docs/current_project_stage.md` (it is absent).
- For new ledger entries, copy from templates and keep existing key style/ordering when possible.
- Keep edits small and diff-friendly; avoid broad YAML rewrites.
- Treat `instrument.instrument_id` in instrument YAML files as the routing key used across ledgers.
- Ensure `microscope` in QC/maintenance ledgers maps to a known instrument ID.

## 5) Scope note

This context file is intentionally minimal and snapshot-specific.
If the repository layout changes, update this file in the same PR to prevent stale agent guidance.
