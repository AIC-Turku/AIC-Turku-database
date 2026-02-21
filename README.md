# AIC Turku Microscopy Dashboard

This repo is the single source of truth for the AIC microscopy facility dashboard:

- `instruments/*.yaml` — instrument registry (metadata shown in the UI)
- `qc/sessions/**/<year>/*.yaml` — QC session ledgers
- `maintenance/events/**/<year>/*.yaml` — maintenance event ledgers
- `scripts/dashboard_builder.py` — builds MkDocs Material pages into `dashboard_docs/`

## Key conventions

- **Stable routing ID:** `instrument.instrument_id` is a URL-safe slug (lowercase + hyphens).
  - It defines URLs: `instruments/<instrument_id>/...`
  - It must match log entries: `microscope: <instrument_id>`

## Local build

```bash
pip install -r requirements-docs.txt
python scripts/dashboard_builder.py
mkdocs serve
```

## Adding a new microscope

1. Copy `templates/microscope_template.yaml` into `instruments/<something>.yaml`
2. Fill in metadata, especially `instrument.instrument_id`
3. Optional: add an image at `assets/images/<instrument_id>.jpg`

