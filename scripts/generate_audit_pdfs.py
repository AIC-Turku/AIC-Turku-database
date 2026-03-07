"""Generate per-instrument audit PDFs from the HTML audit template."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from audit_analyzer import analyze_instrument_completeness
from dashboard_builder import load_instruments


def main() -> None:
    """Render audit reports and export them as PDF files."""
    template_dir = Path(__file__).parent / "templates"
    output_dir = Path(__file__).resolve().parent.parent / "audit_reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
    template = env.get_template("audit_report.html.j2")

    instruments = load_instruments(include_retired=False)

    for instrument in instruments:
        audit_data = analyze_instrument_completeness(instrument)
        rendered_html = template.render(instrument=instrument, audit_data=audit_data)

        instrument_id = instrument.get("id") or "unknown_instrument"
        output_path = output_dir / f"{instrument_id}_audit.pdf"
        HTML(string=rendered_html).write_pdf(output_path)

        print(f"Generated: {output_path}")

    print(f"Audit PDF generation complete. Reports saved to: {output_dir}")


if __name__ == "__main__":
    main()
