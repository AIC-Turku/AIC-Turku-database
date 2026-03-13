"""Generate per-instrument audit PDFs from the HTML audit template."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import CSS, HTML

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.audit_analyzer import analyze_instrument_completeness
from scripts.dashboard_builder import load_facility_config, load_instruments


SECTION_DEFINITIONS = {
    "general": "General Identity",
    "modalities": "Imaging Modalities",
    "software": "Software Configuration",
    "scanner": "Scanner",
    "objectives": "Objectives",
    "filters": "Filters",
    "splitters": "Splitters",
    "magnification_changers": "Magnification Changers",
    "light_sources": "Light Sources",
    "detectors": "Detectors",
    "environment": "Environmental Control",
    "stages": "Stages & Focus Drives",
    "autofocus": "Hardware Autofocus",
    "triggering": "Triggering & Synchronization",
}


def _selected_sections() -> list[dict[str, str]]:
    """Resolve which report sections to include via AUDIT_PDF_SECTIONS."""
    raw = os.getenv("AUDIT_PDF_SECTIONS", "objectives")
    requested = [part.strip() for part in raw.split(",") if part.strip()]
    keys = requested or ["objectives"]
    return [
        {"key": key, "title": SECTION_DEFINITIONS[key]}
        for key in keys
        if key in SECTION_DEFINITIONS
    ]


def main() -> None:
    """Render audit reports and export them as PDF files."""
    template_dir = Path(__file__).parent / "templates"
    repo_root = Path(__file__).resolve().parent.parent
    output_dir = repo_root / "audit_reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
    template = env.get_template("audit_report.html.j2")

    facility_config = load_facility_config(repo_root)
    facility = facility_config.get("facility", {})
    branding = facility_config.get("branding", {})

    facility_name = facility.get("full_name") or facility.get("short_name") or ""
    logo_path = branding.get("logo")

    instruments = load_instruments(include_retired=False)
    css_path = repo_root / "assets" / "stylesheets" / "dashboard.css"
    stylesheets = [CSS(filename=css_path)] if css_path.exists() else []
    sections = _selected_sections()

    for instrument in instruments:
        audit_data = analyze_instrument_completeness(instrument)
        rendered_html = template.render(
            instrument=instrument,
            audit_data=audit_data,
            sections=sections,
            facility_name=facility_name,
            facility_logo_path=logo_path,
        )

        instrument_id = instrument.get("id") or "unknown_instrument"
        output_path = output_dir / f"{instrument_id}_audit.pdf"
        HTML(string=rendered_html, base_url=str(repo_root)).write_pdf(
            output_path,
            stylesheets=stylesheets,
        )

        print(f"Generated: {output_path}")

    print(f"Audit PDF generation complete. Reports saved to: {output_dir}")


if __name__ == "__main__":
    main()
