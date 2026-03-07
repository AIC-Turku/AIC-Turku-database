"""Generate per-instrument audit PDFs from the HTML audit template."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import CSS, HTML

from audit_analyzer import analyze_instrument_completeness
from dashboard_builder import load_facility_config, load_instruments


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

    for instrument in instruments:
        audit_data = analyze_instrument_completeness(instrument)
        rendered_html = template.render(
            instrument=instrument,
            audit_data=audit_data,
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
