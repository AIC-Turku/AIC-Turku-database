# AIC-Turku Microscopy Dashboard

Welcome to the **AIC-Turku Microscopy Dashboard** repository. This project serves as the single source of truth for the microscopy facility using a GitOps approach. All operational state—including instrument configurations, QC results, and maintenance history—is stored here as text and evolves through Pull Requests.

### 🌐 Live Dashboard
**Access the live database and health dashboard:** [https://aic-turku.github.io/AIC-Turku-database/](https://aic-turku.github.io/AIC-Turku-database/)

---

## About the Advanced Imaging Core (AIC)

The [Advanced Imaging Core at Turku Bioscience Centre](https://bioscience.fi/aic/) is a centralized, open-access service platform dedicated to supporting conventional and advanced light microscopy. 

**Our Mission:** To enhance the research environment in Turku by providing state-of-the-art instrumentation and technical expertise to researchers from both academia and industry. We proudly cooperate with Euro-BioImaging ERIC and Turku BioImaging as part of the Finnish Euro-BioImaging Node, improving the accessibility of imaging technologies nationally and internationally. 

Whether you need consultation on choosing an appropriate microscope, training on specific instruments, or access to data analysis tools, our team is ready to support your projects at all levels.

---

## Repository Structure & Data Model

- `instruments/*.yaml` — **Instrument Registry:** Authoritative descriptions of microscope configurations (modalities, hardware, objectives, detectors, software).
- `qc/sessions/**/<year>/*.yaml` — **QC Ledgers:** Self-contained records of QC runs. These contain human inputs (e.g., power meter readings), OMERO artifact pointers, computed metrics, and CI evaluation results.
- `maintenance/events/**/<year>/*.yaml` — **Maintenance Ledgers:** Records of service and maintenance interventions with minimal vocabulary and free-text details.
- `scripts/dashboard_builder.py` — **Build Script:** Parses the YAML ledgers and builds the MkDocs Material dashboard into `dashboard_docs/`.

### Key Conventions
- **Stable Routing ID:** The `instrument.instrument_id` parameter is a URL-safe slug (lowercase + hyphens).
  - It defines routing URLs: `instruments/<instrument_id>/...`
  - It must strictly match log entries under the key: `microscope: <instrument_id>`

---

## Facility Workflows

### 1. Adding a New Microscope

1. Copy `templates/microscope_template.yaml` into `instruments/<something>.yaml`.
2. Fill in the metadata, paying special attention to `instrument.instrument_id`.
3. *(Optional)* Add a representative image at `assets/images/<instrument_id>.jpg`.

### 2. Logging a QC Session

1. Copy `templates/QC_template.yaml` into `qc/sessions/<instrument_id>/<YYYY>/`.
2. Save it using a stable and filesystem-safe ID format (e.g., `qc_<microscope>_<YYYYMMDDThhmmZ>_<suite>.yaml`).
3. Fill in human contexts and manual measurements. *(Note: Scripts will compute the final metrics, and GitHub Actions CI will write the evaluation pass/fail block automatically).*

### 3. Logging a Maintenance Event

1. Copy `templates/maintenance_template.yaml` into `maintenance/events/<instrument_id>/<YYYY>/`.
2. Save it using the appropriate ID format (e.g., `maint_<microscope>_<YYYYMMDD>_<short_slug>.yaml`).
3. Add minimal vocabulary details (reason/action/service provider) and document the service notes.

---
