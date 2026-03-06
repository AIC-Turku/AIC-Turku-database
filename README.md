# AIC-Turku Microscopy Database & Dashboard

Welcome to the **AIC-Turku Microscopy Database**. This repository serves as the single source of truth for the Advanced Imaging Core (AIC) microscopy facility using a strict GitOps approach. All operational state—including instrument configurations, controlled vocabularies, QC results, and maintenance history—is stored here as YAML ledgers and evolves through Pull Requests.

### 🌐 Live Dashboard
**Access the live database and health dashboard:** [https://aic-turku.github.io/AIC-Turku-database/](https://aic-turku.github.io/AIC-Turku-database/)

---

## About the Advanced Imaging Core (AIC)

The [Advanced Imaging Core at Turku Bioscience Centre](https://bioscience.fi/aic/) is a centralized, open-access service platform dedicated to supporting conventional and advanced light microscopy. 

**Our Mission:** To enhance the research environment in Turku by providing state-of-the-art instrumentation and technical expertise to researchers from academia and industry. We cooperate with Euro-BioImaging ERIC and Turku BioImaging as part of the Finnish Euro-BioImaging Node.

Whether you need consultation on choosing an appropriate microscope, training, or access to data analysis tools, our team is ready to support your projects at all levels.

---

## Repository Structure & Data Model

This repository is strictly structured to support automated validation and static site generation.

- `instruments/` — **Instrument Registry:** Authoritative YAML descriptions of active microscope configurations (modalities, hardware, objectives, detectors, etc.). Includes a `retired/` subdirectory for decommissioned systems.
- `qc/sessions/**/<year>/` — **QC Ledgers:** Self-contained records of quality control runs, containing human measurements, OMERO artifact pointers, and computed metrics.
- `maintenance/events/**/<year>/` — **Maintenance Ledgers:** Records of service interventions (repairs, PMs, upgrades) utilizing strict maintenance action/reason vocabularies.
- `vocab/` — **Controlled Vocabularies:** The single source of truth for allowed terms (e.g., modalities, detectors, objective immersions). These enforce consistency across the database.
- `scripts/` — **Pipeline Scripts:** - `validate.py`: Enforces schema, ensures relationships, and validates terms against the `vocab/` dictionaries.
  - `dashboard_builder.py`: The primary build engine. Parses ledgers to build the MkDocs Material dashboard into `dashboard_docs/`, complete with JSON metrics and LLM-ready inventories.
- `templates/` — **Templates:** Starter YAML templates for creating new instruments, QC sessions, and maintenance events.

### Key Conventions
- **Stable Routing ID:** The `instrument.instrument_id` parameter is a URL-safe slug (e.g., `scope-zeiss-lsm-880`).
  - It dictates routing URLs: `instruments/<instrument_id>/...`
  - It must strictly match log entries under the key: `microscope: <instrument_id>`
  - Missing or malformed IDs will cause the `dashboard_builder.py` script to fail.

---

## Facility Workflows

### 1. Adding or Modifying an Instrument
1. Copy `templates/microscope_template.yaml` into `instruments/<instrument_id>.yaml`.
2. Fill in metadata, strictly using canonical IDs from the [Vocabulary Dictionary](https://aic-turku.github.io/AIC-Turku-database/vocabulary_dictionary.md).
3. *(Optional)* Add a representative image at `assets/images/<instrument_id>.jpg`.

### 2. Logging a QC Session
1. Copy `templates/QC_template.yaml` into `qc/sessions/<instrument_id>/<YYYY>/`.
2. Save it using a stable timestamp format: `qc_<instrument_id>_<YYYYMMDDThhmmZ>_<suite>.yaml`.
3. Fill in human contexts and metrics. The build pipeline will automatically extract metric data points to populate longitudinal tracking charts on the dashboard.

### 3. Logging a Maintenance Event
1. Copy `templates/maintenance_template.yaml` into `maintenance/events/<instrument_id>/<YYYY>/`.
2. Save it using: `maint_<instrument_id>_<YYYYMMDD>_<short_slug>.yaml`.
3. Map the event using the allowed `maintenance_reason` and `maintenance_action` vocabularies, and provide free-text notes.

---

## AI & LLM Integrations

This repository is designed to be fully consumable by Large Language Models (LLMs) and automated agents:
- **`llm_inventory.json`**: The build script dynamically compiles an AI-optimized representation of the facility's inventory, status, and environmental controls into `dashboard_docs/assets/llm_inventory.json`. 
- **Agent Context**: See `docs/agent_context.md` for strict instructions tailored for GitOps AI coding assistants operating within this repository.
- **Vocabulary Dictionary (dynamic)**: The dashboard build now generates the vocabulary dictionary page directly from `vocab/` during site generation, so no standalone committed markdown dictionary is maintained in `docs/`.

---

## Local Development & Building

To validate records and preview the dashboard locally:

```bash
# 1. Install dependencies
pip install pyyaml jinja2 mkdocs-material 

# 2. Run the validation and dashboard generation script strictly
python scripts/dashboard_builder.py --strict

# 3. Serve the generated documentation locally
mkdocs serve
