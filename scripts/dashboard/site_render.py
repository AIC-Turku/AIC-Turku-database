"""Dashboard site rendering orchestration.

This module owns writing the generated MkDocs dashboard site from already-loaded
and validated canonical inputs.

It must not import scripts.dashboard_builder.

Responsibilities:
- safe JSON embedding for templates
- fleet nav construction
- vocabulary dictionary markdown rendering
- chart JSON derivation for QC history pages
- instrument overview/history/event page rendering
- methods/plan/virtual-microscope page rendering
- JSON asset export for methods and LLM inventory
- mkdocs.yml generation

It should not contain:
- YAML loader implementations
- canonical instrument normalization
- dashboard/instrument DTO implementation bodies
- optical-path DTO implementation bodies
- LLM export implementation bodies
- methods export implementation bodies
"""

from __future__ import annotations

import copy
import json
import os
import shutil
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader

from scripts.build_context import build_instrument_context, clean_text
from scripts.display_labels import resolve_vocab_section_title
from scripts.validate import Vocabulary, load_policy, print_validation_report, validate_event_ledgers

from scripts.dashboard.instrument_view import build_instrument_mega_dto, vocab_label
from scripts.dashboard.llm_export import build_llm_inventory_payload
from scripts.dashboard.loaders import (
    YamlLoadError,
    _event_output_instrument,
    _extract_log_date,
    _parse_iso_datetime,
    _print_agent_fix_prompt,
    _print_yaml_error_report,
    evaluate_instrument_status,
    get_all_instrument_logs,
    index_instrument_logs,
    load_facility_config,
    load_instruments,
    load_vocabularies,
    validated_instrument_selection,
)
from scripts.dashboard.methods_export import (
    build_methods_generator_instrument_export,
    build_methods_generator_page_config,
    build_plan_experiments_page_config,
)


METRIC_NAMES: dict[str, str] = {
    "laser.488.linearity_r2": "Laser Linearity 488nm (R²)",
    "laser.488.stability_long_delta_pct": "Laser Stability 488nm (Δ%)",
    "psf.60x_oil.525.fwhm_xy_max_nm": "PSF XY Max FWHM (60x Oil, 525nm)",
    "psf.60x_oil.525.fwhm_xy_min_nm": "PSF XY Min FWHM (60x Oil, 525nm)",
    "psf.60x_oil.525.fwhm_z_nm": "PSF Z FWHM (60x Oil, 525nm)",
    "chromatic_shift.60x_oil.561_to_488.dist_nm": "Chromatic Shift 561→488 (60x Oil, nm)",
    "stage.repeatability_sigma_x_nm": "Stage Repeatability σX (nm)",
    "stage.repeatability_sigma_y_nm": "Stage Repeatability σY (nm)",

    # Legacy metric IDs kept for backward compatibility in older ledgers.
    "psf.fwhm_x_um": "PSF Lateral FWHM X (µm)",
    "psf.fwhm_y_um": "PSF Lateral FWHM Y (µm)",
    "psf.fwhm_z_um": "PSF Axial FWHM Z (µm)",
    "laser.power_mw_405": "Laser Power: 405nm (mW)",
    "laser.power_mw_488": "Laser Power: 488nm (mW)",
    "laser.power_mw_561": "Laser Power: 561nm (mW)",
    "laser.power_mw_640": "Laser Power: 640nm (mW)",
    "laser.short_term_stability_delta_percent_488": "Laser Stability 488nm (Δ%)",
    "illumination.uniformity_percent": "Illumination Uniformity (%)",
    "detector.dark_noise_electrons": "Detector Dark Noise (e-)",
}


def json_script_data(payload: Any) -> str:
    """Serialize data safely for embedding inside a script[type=application/json]."""
    return (
        json.dumps(payload, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _build_llm_inventory_record_from_build_input(instrument: dict[str, Any]) -> dict[str, Any]:
    """Build LLM inventory record from full build input, preserving canonical context."""
    if not isinstance(instrument, dict):
        return {}

    return {
        "id": copy.deepcopy(instrument.get("id")),
        "display_name": copy.deepcopy(instrument.get("display_name")),
        "status": copy.deepcopy(instrument.get("status")),
        "canonical": copy.deepcopy(instrument.get("canonical") or {}),
        "canonical_instrument_dto": copy.deepcopy(
            instrument.get("canonical_instrument_dto")
            or instrument.get("canonical")
            or {}
        ),
        "lightpath_dto": copy.deepcopy(instrument.get("lightpath_dto") or {}),
        "canonical_lightpath_dto": copy.deepcopy(
            instrument.get("canonical_lightpath_dto")
            or instrument.get("lightpath_dto")
            or {}
        ),
        "dto": copy.deepcopy(instrument.get("dto") or {}),
        "diagnostics": copy.deepcopy(instrument.get("diagnostics") or []),
    }


def build_nav(
    instruments: list[dict[str, Any]],
    retired_instruments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build MkDocs navigation for active and retired instruments."""
    microscopes = [
        {inst["display_name"]: f"instruments/{inst['id']}/index.md"}
        for inst in instruments
    ]
    retired = [
        {inst["display_name"]: f"instruments/{inst['id']}/index.md"}
        for inst in retired_instruments
    ]

    return [
        {"Fleet Overview": "index.md"},
        {"System Health": "status.md"},
        {"Microscopes": microscopes},
        {"Plan Your Experiments": "plan_experiments.md"},
        {"Virtual Microscope": "virtual_microscope.md"},
        {"Methods Generator": "methods_generator.md"},
        {"Vocabulary Dictionary": "vocabulary_dictionary.md"},
        {"Retired Instruments": [{"Overview": "retired/index.md"}, *retired]},
    ]


def _metric_lookup(metric_entries: Any) -> dict[str, Any]:
    output: dict[str, Any] = {}
    if not isinstance(metric_entries, list):
        return output

    for item in metric_entries:
        if not isinstance(item, dict):
            continue
        metric_id = item.get("metric_id")
        value = item.get("value")
        if isinstance(metric_id, str):
            output[metric_id] = value

    return output


def _build_all_charts_data(qc_logs: list[dict[str, Any]]) -> str:
    all_metrics: set[str] = set()
    for entry in qc_logs:
        payload = entry.get("data")
        if isinstance(payload, dict):
            metrics = _metric_lookup(payload.get("metrics_computed"))
            all_metrics.update(metrics.keys())

    charts: dict[str, Any] = {}
    for metric_id in sorted(all_metrics):
        labels: list[str] = []
        values: list[Any] = []

        for entry in qc_logs:
            payload = entry.get("data")
            if not isinstance(payload, dict):
                continue

            parsed_started = _parse_iso_datetime(payload.get("started_utc"))
            if parsed_started is None:
                continue

            labels.append(parsed_started.strftime("%Y-%m-%d"))
            metrics = _metric_lookup(payload.get("metrics_computed"))
            val = metrics.get(metric_id)
            values.append(val if isinstance(val, (int, float)) else None)

        if any(value is not None for value in values):
            charts[metric_id] = {
                "labels": labels,
                "values": values,
            }

    return json.dumps(charts)


def build_vocabulary_dictionary_markdown(vocabulary: Vocabulary) -> str:
    """Render the controlled-vocabulary dictionary markdown page."""
    vocab_md_lines = [
        "---",
        "title: Vocabulary Dictionary",
        "description: Controlled terminology used in the AIC database.",
        "---",
        "",
        "# 📖 Vocabulary Dictionary\n",
        (
            "This page defines the strictly controlled terminology used across the AIC database. "
            "Use the **Canonical ID** when writing YAML files, though the validation scripts "
            "will gracefully suggest corrections if you use a known **Synonym**.\n"
        ),
    ]

    categories = {
        "🔬 Instruments": [
            "modalities",
            "modules",
            "detector_kinds",
            "light_source_kinds",
            "scanner_types",
            "objective_corrections",
            "objective_immersion",
        ],
        "🛠️ Maintenance": [
            "maintenance_action",
            "maintenance_reason",
            "maintenance_status",
            "service_provider",
        ],
        "✅ Quality Control": [
            "qc_type",
            "qc_metric_classes",
            "qc_evaluation_status",
            "qc_artifact_roles",
            "qc_measurement_positions",
            "qc_setpoint_units",
            "metric_unit",
        ],
    }

    rendered_vocabs: set[str] = set()

    for cat_title, expected_vocabs in categories.items():
        vocab_md_lines.append(f'=== "{cat_title}"\n')

        has_content = False
        for vocab_name in expected_vocabs:
            if vocab_name not in vocabulary.terms_by_vocab:
                continue

            has_content = True
            rendered_vocabs.add(vocab_name)
            title = resolve_vocab_section_title(vocab_name)
            vocab_md_lines.append(f"    ## {title}\n")
            vocab_md_lines.append("    | Label | Canonical ID | Synonyms | Description |")
            vocab_md_lines.append("    | :--- | :--- | :--- | :--- |")

            for term in sorted(
                vocabulary.terms_by_vocab[vocab_name].values(),
                key=lambda item: item.label.lower(),
            ):
                label = f"**{term.label}**"
                code_id = f"`{term.id}`"
                syns = ", ".join([f"`{synonym}`" for synonym in term.synonyms]) if term.synonyms else "-"
                desc = term.description.replace("\n", " ").strip() if term.description else "-"
                vocab_md_lines.append(f"    | {label} | {code_id} | {syns} | {desc} |")

            vocab_md_lines.append("\n")

        if not has_content:
            vocab_md_lines.append("    _No vocabularies currently defined for this category._\n\n")

    other_vocabs = [
        vocab_name
        for vocab_name in vocabulary.terms_by_vocab.keys()
        if vocab_name not in rendered_vocabs
    ]
    if other_vocabs:
        vocab_md_lines.append('=== "📦 Other"\n')
        for vocab_name in sorted(other_vocabs):
            title = resolve_vocab_section_title(vocab_name)
            vocab_md_lines.append(f"    ## {title}\n")
            vocab_md_lines.append("    | Label | Canonical ID | Synonyms | Description |")
            vocab_md_lines.append("    | :--- | :--- | :--- | :--- |")

            for term in sorted(
                vocabulary.terms_by_vocab[vocab_name].values(),
                key=lambda item: item.label.lower(),
            ):
                label = f"**{term.label}**"
                code_id = f"`{term.id}`"
                syns = ", ".join([f"`{synonym}`" for synonym in term.synonyms]) if term.synonyms else "-"
                desc = term.description.replace("\n", " ").strip() if term.description else "-"
                vocab_md_lines.append(f"    | {label} | {code_id} | {syns} | {desc} |")

            vocab_md_lines.append("\n")

    return "\n".join(vocab_md_lines)


def build_mkdocs_config(
    *,
    facility: dict[str, Any],
    branding: dict[str, Any],
    instruments: list[dict[str, Any]],
    retired_instruments: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build mkdocs.yml content."""
    site_url = os.getenv("MKDOCS_SITE_URL", str(facility.get("public_site_url", "")))

    return {
        "site_name": str(facility.get("site_name", "Microscopy Dashboard")),
        "site_url": site_url,
        "use_directory_urls": True,
        "docs_dir": "dashboard_docs",
        "theme": {
            "name": "material",
            "features": [
                "navigation.tabs",
                "navigation.sections",
                "navigation.top",
                "toc.integrate",
                "search.suggest",
                "search.highlight",
                "content.code.copy",
            ],
            "palette": [
                {
                    "scheme": "default",
                    "toggle": {
                        "icon": "material/brightness-7",
                        "name": "Switch to dark mode",
                    },
                },
                {
                    "scheme": "slate",
                    "toggle": {
                        "icon": "material/brightness-4",
                        "name": "Switch to light mode",
                    },
                },
            ],
            "logo": str(branding.get("logo", "assets/images/logo.svg")),
            "favicon": str(branding.get("favicon", "assets/images/favicon.svg")),
        },
        "plugins": ["search"],
        "markdown_extensions": [
            "admonition",
            "attr_list",
            "md_in_html",
            "tables",
            "pymdownx.details",
            "pymdownx.superfences",
            "pymdownx.tabbed",
        ],
        "extra_css": ["assets/stylesheets/dashboard.css"],
        "extra_javascript": [
            "assets/javascripts/dashboard.js",
            "https://cdn.jsdelivr.net/npm/chart.js",
            "assets/javascripts/charts.js",
        ],
        "nav": build_nav(instruments, retired_instruments),
        "validation": {
            "nav": {"omitted_files": "info"},
        },
    }


def _build_vocabulary(repo_root: Path) -> Vocabulary:
    """Build the Vocabulary object with all policy vocab registries merged."""
    combined_registry: dict[str, dict[str, Any]] = {}

    for policy_file in (
        "schema/instrument_policy.yaml",
        "schema/QC_policy.yaml",
        "schema/maintenance_policy.yaml",
    ):
        policy_path = repo_root / policy_file
        if not policy_path.exists():
            continue

        payload, _ = load_policy(policy_path)
        if not isinstance(payload, dict):
            continue

        vocab_registry = payload.get("vocab_registry")
        if isinstance(vocab_registry, dict):
            combined_registry.update(vocab_registry)

    return Vocabulary(repo_root / "vocab", vocab_registry=combined_registry or None)


def _annotate_display_labels(
    instruments: list[dict[str, Any]],
    retired_instruments: list[dict[str, Any]],
    vocabulary: Vocabulary,
) -> None:
    """Attach display labels used by templates to loaded instrument records."""
    for inst in [*instruments, *retired_instruments]:
        inst["modalities_display"] = [
            vocab_label(vocabulary, "modalities", modality_id)
            for modality_id in inst.get("modalities", [])
        ]
        caps = inst.get("capabilities") if isinstance(inst.get("capabilities"), dict) else {}
        axis_vocab = {
            "imaging_modes": "imaging_modes",
            "contrast_methods": "contrast_methods",
            "readouts": "measurement_readouts",
            "workflows": "workflow_tags",
            "assay_operations": "assay_operations",
            "non_optical": "non_optical_capabilities",
        }
        primary = []
        for axis, vocab_name in axis_vocab.items():
            values = caps.get(axis) if isinstance(caps.get(axis), list) else []
            for value in values:
                primary.append({"axis": axis, "id": value, "label": vocab_label(vocabulary, vocab_name, value)})
        inst["capabilities_primary"] = primary
        inst["capabilities_primary_ids"] = [f"{item['axis']}:{item['id']}".lower() for item in primary]
        for module in inst.get("modules", []):
            module_name = clean_text(module.get("type") or module.get("name"))
            module["display_name"] = vocab_label(vocabulary, "modules", module_name)


def render_site(
    *,
    strict: bool = True,
    allowed_record_types: tuple[str, ...],
    repo_root: Path | None = None,
) -> int:
    """Render the complete dashboard site and return a process-style exit code."""
    repo_root = repo_root or Path.cwd()
    facility_cfg = load_facility_config(repo_root)
    facility = facility_cfg.get("facility", {}) if isinstance(facility_cfg.get("facility"), dict) else {}
    branding = facility_cfg.get("branding", {}) if isinstance(facility_cfg.get("branding"), dict) else {}
    docs_root = repo_root / "dashboard_docs"

    if docs_root.exists():
        shutil.rmtree(docs_root)
    (docs_root / "instruments").mkdir(parents=True, exist_ok=True)
    (docs_root / "events").mkdir(parents=True, exist_ok=True)

    vocabularies = load_vocabularies(repo_root / "vocab")
    vocab_json_path = docs_root / "assets" / "vocabularies.json"
    vocab_json_path.parent.mkdir(parents=True, exist_ok=True)
    vocab_json_path.write_text(json.dumps(vocabularies, indent=2), encoding="utf-8")

    vocabulary = _build_vocabulary(repo_root)

    load_errors: list[YamlLoadError] = []
    (
        validated_instrument_ids,
        instrument_validation_issues,
        instrument_validation_warnings,
    ) = validated_instrument_selection()

    instruments = load_instruments(
        "instruments",
        load_errors=load_errors,
        allowed_instrument_ids=validated_instrument_ids,
    )
    retired_instruments = load_instruments(
        "instruments",
        load_errors=load_errors,
        include_retired=True,
        allowed_instrument_ids=validated_instrument_ids,
    )

    _annotate_display_labels(instruments, retired_instruments, vocabulary)

    (docs_root / "vocabulary_dictionary.md").write_text(
        build_vocabulary_dictionary_markdown(vocabulary),
        encoding="utf-8",
    )

    assets_root = repo_root / "assets"
    if assets_root.exists():
        shutil.copytree(assets_root, docs_root / "assets", dirs_exist_ok=True)

    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    jinja_env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)

    tpl_index = jinja_env.get_template("index.md.j2")
    tpl_status = jinja_env.get_template("status.md.j2")
    tpl_retired = jinja_env.get_template("retired_index.md.j2")
    tpl_spec = jinja_env.get_template("instrument_spec.md.j2")
    tpl_history = jinja_env.get_template("instrument_history.md.j2")
    tpl_event = jinja_env.get_template("event_detail.md.j2")
    tpl_plan = jinja_env.get_template("plan_experiments.md.j2")
    tpl_methods = jinja_env.get_template("methods_generator.md.j2")
    tpl_vm = jinja_env.get_template("virtual_microscope.html.j2")

    qc_logs_by_instrument = index_instrument_logs("qc/sessions", load_errors=load_errors)
    maint_logs_by_instrument = index_instrument_logs("maintenance/events", load_errors=load_errors)

    validation_issues = list(instrument_validation_issues)
    event_validation_report = validate_event_ledgers(
        instrument_ids=validated_instrument_ids,
        allowed_record_types=allowed_record_types,
    )
    validation_issues.extend(event_validation_report.errors)

    if instrument_validation_warnings:
        print_validation_report(instrument_validation_warnings, report_name="warnings")
    if event_validation_report.warnings:
        print_validation_report(event_validation_report.warnings, report_name="warnings")
    if event_validation_report.migration_notices:
        print_validation_report(
            event_validation_report.migration_notices,
            report_name="migration notices",
        )

    all_capability_ids = sorted({cid for inst in instruments for cid in (inst.get("capabilities_primary_ids") or []) if isinstance(cid, str)})
    capability_filter_options = []
    axis_vocab = {"imaging_modes": "imaging_modes", "contrast_methods": "contrast_methods", "readouts": "measurement_readouts", "workflows": "workflow_tags", "assay_operations": "assay_operations", "non_optical": "non_optical_capabilities"}
    axis_labels = {"imaging_modes":"Imaging", "contrast_methods":"Contrast", "readouts":"Readout", "workflows":"Workflow", "assay_operations":"Assay", "non_optical":"Non-optical"}
    for cid in all_capability_ids:
        axis, _, term = cid.partition(":")
        human_term = vocab_label(vocabulary, axis_vocab.get(axis, ""), term) if axis in axis_vocab else term
        capability_filter_options.append({"id": cid, "label": f"{axis_labels.get(axis, axis)}: {human_term}"})

    fleet_counts = {"total": len(instruments), "green": 0, "yellow": 0, "red": 0}
    flagged: list[dict[str, Any]] = []
    retired_instrument_ids = {inst["id"] for inst in retired_instruments}
    global_vm_payloads: dict[str, dict[str, Any]] = {}

    for inst in [*instruments, *retired_instruments]:
        instrument_id = inst["id"]
        is_retired_instrument = instrument_id in retired_instrument_ids

        qc_logs = get_all_instrument_logs(
            "qc/sessions",
            instrument_id,
            load_errors=load_errors,
            preindexed_logs=qc_logs_by_instrument,
        )
        maint_logs = get_all_instrument_logs(
            "maintenance/events",
            instrument_id,
            load_errors=load_errors,
            preindexed_logs=maint_logs_by_instrument,
        )

        latest_qc = qc_logs[-1]["data"] if qc_logs else None
        latest_maint = maint_logs[-1]["data"] if maint_logs else None

        status = evaluate_instrument_status(latest_qc, latest_maint)
        inst["status"] = status

        if not is_retired_instrument:
            if status["color"] == "green":
                fleet_counts["green"] += 1
            elif status["color"] == "yellow":
                fleet_counts["yellow"] += 1
            else:
                fleet_counts["red"] += 1

            if status["color"] in {"yellow", "red"}:
                flagged.append(inst)

        charts_json = _build_all_charts_data(qc_logs)

        latest_metrics: dict[str, Any] = {}
        for log in qc_logs:
            payload = log.get("data")
            if isinstance(payload, dict):
                session_metrics = _metric_lookup(payload.get("metrics_computed"))
                latest_metrics.update(session_metrics)

        context = build_instrument_context(
            inst,
            vocabulary=vocabulary,
            build_dashboard_view_dto=build_instrument_mega_dto,
            build_methods_view_dto=build_methods_generator_instrument_export,
            build_llm_inventory_record=_build_llm_inventory_record_from_build_input,
        )
        inst["build_context"] = context
        inst["lightpath_dto"] = context.canonical_lightpath_dto
        inst["dto"] = context.dashboard_view_dto
        inst["dto"]["diagnostics"] = copy.deepcopy(context.diagnostics)

        instrument_dir = docs_root / "instruments" / instrument_id
        instrument_dir.mkdir(parents=True, exist_ok=True)

        overview_md = tpl_spec.render(
            instrument=inst,
            charts_json=charts_json,
            latest_metrics=latest_metrics,
            metric_names=METRIC_NAMES,
            policy=inst.get("canonical", {}).get("policy", {}),
        )
        (instrument_dir / "index.md").write_text(overview_md, encoding="utf-8")

        if not is_retired_instrument:
            vm_payload = copy.deepcopy(context.vm_payload)
            vm_payload["display_name"] = inst.get("dto", {}).get("display_name")
            global_vm_payloads[instrument_id] = vm_payload

        history_events_qc = []
        for log in qc_logs:
            payload = log.get("data") or {}
            event_id = Path(log["source_path"]).stem
            event_instrument = _event_output_instrument(payload, instrument_id)
            history_events_qc.append(
                {
                    "date": _extract_log_date(payload),
                    "status": payload.get("evaluation", {}).get("overall_status", "completed"),
                    "suite": "QC Session",
                    "event_id": event_id,
                    "event_href": f"../../../events/{event_instrument}/{event_id}/",
                }
            )

        history_events_maint = []
        for log in maint_logs:
            payload = log.get("data") or {}
            event_id = Path(log["source_path"]).stem
            event_instrument = _event_output_instrument(payload, instrument_id)
            history_events_maint.append(
                {
                    "date": _extract_log_date(payload),
                    "status": payload.get("microscope_status_after", "completed"),
                    "type": "Maintenance",
                    "event_id": event_id,
                    "event_href": f"../../../events/{event_instrument}/{event_id}/",
                }
            )

        history_md = tpl_history.render(
            instrument=inst,
            charts_json=charts_json,
            metric_names=METRIC_NAMES,
            qc_events=history_events_qc,
            maintenance_events=history_events_maint,
        )
        (instrument_dir / "history.md").write_text(history_md, encoding="utf-8")

        for log_entry in qc_logs + maint_logs:
            source_path = log_entry.get("source_path")
            if not isinstance(source_path, str):
                continue

            source_file = Path(source_path)
            event_id = source_file.stem
            event_payload = log_entry.get("data") if isinstance(log_entry.get("data"), dict) else {}
            event_instrument = _event_output_instrument(event_payload, instrument_id)

            try:
                raw_yaml_text = source_file.read_text(encoding="utf-8")
            except OSError:
                raw_yaml_text = yaml.safe_dump(
                    event_payload,
                    sort_keys=False,
                    allow_unicode=True,
                )

            event_md = tpl_event.render(
                event_id=event_id,
                date=_extract_log_date(event_payload),
                instrument=event_payload.get("microscope"),
                instrument_id=event_instrument,
                operator=event_payload.get("performed_by") or event_payload.get("service_provider"),
                raw_yaml_content=raw_yaml_text,
                payload=event_payload,
            )
            event_dir = docs_root / "events" / event_instrument
            event_dir.mkdir(parents=True, exist_ok=True)
            (event_dir / f"{event_id}.md").write_text(event_md, encoding="utf-8")

    vm_html = tpl_vm.render(lightpath_data_json=json_script_data(global_vm_payloads))
    (docs_root / "virtual_microscope.md").write_text(vm_html, encoding="utf-8")

    index_md = tpl_index.render(
        instruments=instruments,
        capability_filter_options=capability_filter_options,
        counts=fleet_counts,
    )
    (docs_root / "index.md").write_text(index_md, encoding="utf-8")

    json_path = docs_root / "assets" / "instruments_data.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_payload = {
        "instruments": [
            copy.deepcopy(
                inst.get("build_context").methods_export_dto
                if inst.get("build_context")
                else build_methods_generator_instrument_export(inst)
            )
            for inst in sorted(
                [*instruments, *retired_instruments],
                key=lambda item: item.get("id", ""),
            )
        ],
    }
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")

    llm_inventory_path = docs_root / "assets" / "llm_inventory.json"
    llm_records = []
    for inst in instruments:
        context = inst.get("build_context")
        if context and isinstance(context.llm_inventory_record, dict) and context.llm_inventory_record:
            llm_records.append(copy.deepcopy(context.llm_inventory_record))
        else:
            llm_records.append(copy.deepcopy(inst))
    llm_payload = build_llm_inventory_payload(facility, llm_records)
    llm_inventory_path.write_text(json.dumps(llm_payload, indent=2), encoding="utf-8")

    methods_page_config = build_methods_generator_page_config(facility, repo_root)
    methods_md = tpl_methods.render(
        methods_generator_config_json=json_script_data(methods_page_config),
    )
    (docs_root / "methods_generator.md").write_text(methods_md, encoding="utf-8")

    plan_page_config = build_plan_experiments_page_config(facility)
    plan_md = tpl_plan.render(
        plan_experiments_config_json=json_script_data(plan_page_config),
        facility_short_name=plan_page_config["facility_short_name"],
        facility_contact_url=plan_page_config["facility_contact_url"],
        facility_contact_label=plan_page_config["facility_contact_label"],
        llm_inventory_asset_url=plan_page_config["llm_inventory_asset_url"],
    )
    (docs_root / "plan_experiments.md").write_text(plan_md, encoding="utf-8")

    status_md = tpl_status.render(issues=flagged)
    (docs_root / "status.md").write_text(status_md, encoding="utf-8")

    retired_md = tpl_retired.render(retired_instruments=retired_instruments)
    retired_docs_dir = docs_root / "retired"
    retired_docs_dir.mkdir(parents=True, exist_ok=True)
    (retired_docs_dir / "index.md").write_text(retired_md, encoding="utf-8")

    mkdocs_config = build_mkdocs_config(
        facility=facility,
        branding=branding,
        instruments=instruments,
        retired_instruments=retired_instruments,
    )
    (repo_root / "mkdocs.yml").write_text(
        yaml.safe_dump(mkdocs_config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    has_failures = False

    if load_errors:
        _print_yaml_error_report(load_errors)
        has_failures = True

    if validation_issues:
        print_validation_report(validation_issues)
        has_failures = True

    if strict and has_failures:
        _print_agent_fix_prompt(load_errors, validation_issues)
        return 1

    return 0


__all__ = [
    "METRIC_NAMES",
    "json_script_data",
    "build_nav",
    "_build_llm_inventory_record_from_build_input",
    "build_vocabulary_dictionary_markdown",
    "build_mkdocs_config",
    "render_site",
    "_metric_lookup",
    "_build_all_charts_data",
]
