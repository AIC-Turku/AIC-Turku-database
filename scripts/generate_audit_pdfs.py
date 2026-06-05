"""Generate per-instrument audit PDFs from the HTML audit template.

This is an auxiliary audit-only reporting script (not the primary production site build),
but it now consumes the same validator-selected authoritative instrument set as the dashboard flow.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import CSS, HTML

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.audit_packet import StaffValidationPacketDTO, build_staff_validation_packet
from scripts.build_context import InstrumentBuildContext, build_instrument_context
from scripts.dashboard.instrument_view import build_instrument_mega_dto
from scripts.dashboard.loaders import (
    load_facility_config,
    load_instruments,
    validated_instrument_selection,
)
from scripts.dashboard.methods_export import build_methods_generator_instrument_export
from scripts.dashboard.site_render import (
    _build_llm_inventory_record_from_build_input,
    _build_vocabulary,
)


SECTION_DEFINITIONS = {
    "general": "General Identity",
    "capabilities": "Capabilities",
    "modalities": "Imaging Modalities",
    "software": "Software Configuration",
    "modules": "Modules",
    "scanner": "Scanner",
    "objectives": "Objectives",
    "filters": "Filters",
    "splitters": "Splitters",
    "magnification_changers": "Magnification Changers",
    "light_sources": "Light Sources",
    "detectors": "Detectors",
    "endpoints": "Endpoints",
    "optical_path_elements": "Optical Path Elements",
    "light_paths": "Light Paths",
    "environment": "Environmental Control",
    "stages": "Stages & Focus Drives",
    "autofocus": "Hardware Autofocus",
    "triggering": "Triggering & Synchronization",
    "policy": "Policy Details",
    "provenance": "Provenance",
    "canonical_dto_coverage": "Canonical DTO Coverage",
}


def _selected_sections() -> list[dict[str, str]]:
    """Resolve which report sections to include via AUDIT_PDF_SECTIONS.

    By default the staff audit includes every currently implemented section.
    Set AUDIT_PDF_SECTIONS to a comma-separated subset, or to ``all``, to
    override the default order explicitly.
    """
    raw = os.getenv("AUDIT_PDF_SECTIONS")
    if raw is None or raw.strip().lower() == "all":
        keys = list(SECTION_DEFINITIONS)
    else:
        requested = [part.strip() for part in raw.split(",") if part.strip()]
        keys = requested or list(SECTION_DEFINITIONS)
    return [
        {"key": key, "title": SECTION_DEFINITIONS[key]}
        for key in keys
        if key in SECTION_DEFINITIONS
    ]


CSV_FIELDNAMES = [
    "instrument_id",
    "display_name",
    "section",
    "label",
    "value",
    "source_dto",
    "source_path",
    "is_missing",
    "is_warning",
    "is_optional",
    "diagnostic_codes",
    "diagnostic_messages",
    "reviewer_status",
    "reviewer_comment",
    "corrected_value",
]


def _json_default(value: object) -> object:
    """JSON serializer for paths and other simple non-JSON objects."""
    if isinstance(value, Path):
        return value.as_posix()
    return str(value)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            default=_json_default,
        ),
        encoding="utf-8",
    )


def _csv_value(value: object) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=_json_default)


def _packet_csv_rows(packet: StaffValidationPacketDTO) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in packet.rows:
        diagnostics = row.diagnostics if isinstance(row.diagnostics, list) else []
        rows.append(
            {
                "instrument_id": packet.instrument_id,
                "display_name": packet.display_name,
                "section": row.section,
                "label": row.label,
                "value": _csv_value(row.value),
                "source_dto": row.source_dto,
                "source_path": row.source_path,
                "is_missing": "yes" if row.is_missing else "no",
                "is_warning": "yes" if row.is_warning else "no",
                "is_optional": "yes" if row.is_optional else "no",
                "diagnostic_codes": "; ".join(
                    str(item.get("code") or item.get("title") or "diagnostic")
                    for item in diagnostics
                    if isinstance(item, dict)
                ),
                "diagnostic_messages": "; ".join(
                    str(item.get("message") or item.get("title") or "")
                    for item in diagnostics
                    if isinstance(item, dict)
                ),
                "reviewer_status": "",
                "reviewer_comment": "",
                "corrected_value": "",
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _traceability_payload(
    context: InstrumentBuildContext,
    packet: StaffValidationPacketDTO,
) -> dict[str, object]:
    """Collect full DTO traceability payloads for one instrument."""
    return {
        "instrument_id": context.instrument_id,
        "source_path": context.source_path,
        "canonical_instrument_dto": context.canonical_instrument_dto,
        "canonical_lightpath_dto": context.canonical_lightpath_dto,
        "dashboard_view_dto": context.dashboard_view_dto,
        "methods_export_dto": context.methods_export_dto,
        "llm_inventory_record": context.llm_inventory_record,
        "vm_payload": context.vm_payload,
        "validation_diagnostics": context.validation_diagnostics,
        "build_diagnostics": context.diagnostics,
        "staff_validation_packet": packet.as_dict(),
    }


def _prepare_output_dirs(output_dir: Path) -> tuple[Path, Path, Path]:
    """Create a clean audit artifact directory tree."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    pdf_dir = output_dir / "pdf"
    csv_dir = output_dir / "csv"
    json_dir = output_dir / "json"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    return pdf_dir, csv_dir, json_dir


def _write_instrument_artifacts(
    *,
    instrument_id: str,
    rendered_html: str,
    repo_root: Path,
    stylesheets: list[CSS],
    pdf_dir: Path,
    csv_dir: Path,
    json_dir: Path,
    build_context: InstrumentBuildContext,
    staff_validation_packet: StaffValidationPacketDTO,
) -> dict[str, object]:
    """Write one instrument's PDF, CSV, and JSON audit artifacts."""
    pdf_path = pdf_dir / f"{instrument_id}_audit.pdf"
    HTML(string=rendered_html, base_url=str(repo_root)).write_pdf(
        pdf_path,
        stylesheets=stylesheets,
    )

    packet_csv_rows = _packet_csv_rows(staff_validation_packet)
    instrument_csv_path = csv_dir / f"{instrument_id}_validation_rows.csv"
    _write_csv(instrument_csv_path, packet_csv_rows)

    traceability_path = json_dir / f"{instrument_id}_traceability.json"
    _write_json(
        traceability_path,
        _traceability_payload(build_context, staff_validation_packet),
    )

    return {
        "pdf_path": pdf_path,
        "csv_path": instrument_csv_path,
        "json_path": traceability_path,
        "csv_rows": packet_csv_rows,
    }


def main() -> None:
    """Render audit reports and export them as PDF files."""
    template_dir = Path(__file__).parent / "templates"
    repo_root = Path(__file__).resolve().parent.parent
    output_dir = repo_root / "audit_reports"
    pdf_dir, csv_dir, json_dir = _prepare_output_dirs(output_dir)

    env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
    template = env.get_template("audit_report.html.j2")

    facility_config = load_facility_config(repo_root)
    facility = facility_config.get("facility", {})
    branding = facility_config.get("branding", {})

    facility_name = facility.get("full_name") or facility.get("short_name") or ""
    logo_path = branding.get("logo")

    # Auxiliary audit output still follows the same validator-selected boundary as dashboard generation.
    validated_instrument_ids, _, _ = validated_instrument_selection("instruments")
    instruments = load_instruments(include_retired=False, allowed_instrument_ids=validated_instrument_ids)
    vocabulary = _build_vocabulary(repo_root)
    css_path = repo_root / "assets" / "stylesheets" / "dashboard.css"
    stylesheets = [CSS(filename=css_path)] if css_path.exists() else []
    sections = _selected_sections()

    all_csv_rows: list[dict[str, str]] = []

    for instrument in instruments:
        build_context = build_instrument_context(
            instrument,
            vocabulary=vocabulary,
            build_dashboard_view_dto=build_instrument_mega_dto,
            build_methods_view_dto=build_methods_generator_instrument_export,
            build_llm_inventory_record=_build_llm_inventory_record_from_build_input,
        )
        staff_validation_packet = build_staff_validation_packet(build_context)
        audit_data = staff_validation_packet.as_template_context()
        rendered_html = template.render(
            instrument=instrument,
            audit_data=audit_data,
            sections=sections,
            facility_name=facility_name,
            facility_logo_path=logo_path,
        )

        instrument_id = instrument.get("id") or "unknown_instrument"
        artifact_paths = _write_instrument_artifacts(
            instrument_id=instrument_id,
            rendered_html=rendered_html,
            repo_root=repo_root,
            stylesheets=stylesheets,
            pdf_dir=pdf_dir,
            csv_dir=csv_dir,
            json_dir=json_dir,
            build_context=build_context,
            staff_validation_packet=staff_validation_packet,
        )
        all_csv_rows.extend(artifact_paths["csv_rows"])

        print(f"Generated: {artifact_paths['pdf_path']}")
        print(f"Generated: {artifact_paths['csv_path']}")
        print(f"Generated: {artifact_paths['json_path']}")

    all_csv_path = csv_dir / "all_instruments_validation_rows.csv"
    _write_csv(all_csv_path, all_csv_rows)
    print(f"Generated: {all_csv_path}")
    print(f"Audit artifact generation complete. Reports saved to: {output_dir}")


if __name__ == "__main__":
    main()
