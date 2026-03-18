"""Repository-wide audit entrypoint for YAML, schema, DTO, and virtual microscope readiness.

This script is intentionally conservative:
- it reuses the existing validation pipeline instead of re-implementing schema logic
- it audits the validated/normalized DTO path consumed by the virtual microscope
- it emits both machine-readable JSON and a concise Markdown report

The audit is designed to answer four questions:
1. Do repository YAML files parse and validate?
2. Where are the main policy/completeness gaps?
3. Does the virtual microscope payload preserve the metadata required by the simulator?
4. Is the FPbase/browser runtime contract healthy enough to render usable fluorophore spectra?
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import textwrap
from collections import Counter
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.dashboard_builder import YamlLoadError, load_instruments, validated_instrument_selection
from scripts.light_path_parser import canonicalize_light_path_model, generate_virtual_microscope_payload, infer_light_source_role
from scripts.validate import (
    DEFAULT_ALLOWED_RECORD_TYPES,
    build_instrument_completeness_report,
    validate_event_ledgers,
    validate_instrument_ledgers,
)


POINT_DETECTOR_KINDS = {"pmt", "gaasp_pmt", "hyd", "apd", "spad"}


def _as_serializable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _as_serializable(subvalue) for key, subvalue in value.items()}
    if isinstance(value, (list, tuple)):
        return [_as_serializable(item) for item in value]
    return value


def _collect_yaml_error_dicts(load_errors: list[YamlLoadError]) -> list[dict[str, str]]:
    return [{"path": item.path, "message": item.message} for item in load_errors]


def _issue_dict(issue: Any) -> dict[str, str]:
    return {
        "code": getattr(issue, "code", "unknown"),
        "path": getattr(issue, "path", ""),
        "message": getattr(issue, "message", ""),
    }


def _issue_counter(issues: list[Any]) -> dict[str, int]:
    counter = Counter(getattr(issue, "code", "unknown") for issue in issues)
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def _top_items(counter_map: Counter | dict[str, int], limit: int = 10) -> list[dict[str, Any]]:
    counter = Counter(counter_map)
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


def _coerce_component_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _coerce_mechanism_list(light_path: dict[str, Any], key: str) -> list[dict[str, Any]]:
    if not isinstance(light_path, dict):
        return []
    value = light_path.get(key)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _splitter_count(hardware: dict[str, Any], light_path: dict[str, Any]) -> dict[str, int]:
    top_level = len(_coerce_component_list(hardware.get("splitters")))
    nested = len(_coerce_component_list(light_path.get("splitters"))) if isinstance(light_path, dict) else 0
    return {
        "top_level": top_level,
        "light_path": nested,
        "total_distinct_entries": top_level + nested,
    }


def _source_readiness_issue(index: int, source: dict[str, Any]) -> list[dict[str, str]]:
    label = source.get("model") or source.get("manufacturer") or source.get("name") or f"source_{index + 1}"
    issues: list[dict[str, str]] = []
    if not source.get("kind"):
        issues.append({"severity": "warning", "field": "kind", "message": f"Light source '{label}' is missing kind/type metadata."})
    role = source.get("role")
    if not role:
        inferred_role = infer_light_source_role(source)
        if inferred_role == "depletion":
            issues.append({
                "severity": "warning",
                "field": "role",
                "message": f"Light source '{label}' is missing explicit source role metadata; runtime inferred depletion from free text. Encode role='depletion' in YAML.",
            })
        else:
            pretty_role = inferred_role.replace('_', ' ')
            issues.append({
                "severity": "info",
                "field": "role",
                "message": f"Light source '{label}' is missing explicit source role metadata; runtime will treat it as {pretty_role}.",
            })
    wave = source.get("wavelength_nm")
    tunable_min = source.get("tunable_min_nm")
    tunable_max = source.get("tunable_max_nm")
    if wave in (None, "") and (tunable_min in (None, "") or tunable_max in (None, "")):
        issues.append(
            {
                "severity": "warning",
                "field": "wavelength",
                "message": f"Light source '{label}' has neither a fixed wavelength nor a tunable wavelength range.",
            }
        )
    if role == "depletion" and not source.get("depletion_targets_nm"):
        issues.append(
            {
                "severity": "warning",
                "field": "depletion_targets_nm",
                "message": f"Depletion source '{label}' is missing depletion target metadata.",
            }
        )
    return issues


def _detector_readiness_issue(index: int, detector: dict[str, Any]) -> list[dict[str, str]]:
    label = detector.get("model") or detector.get("manufacturer") or detector.get("name") or f"detector_{index + 1}"
    issues: list[dict[str, str]] = []
    if not detector.get("kind"):
        issues.append({"severity": "warning", "field": "kind", "message": f"Detector '{label}' is missing kind/type metadata."})
    if not detector.get("channel_name") and not detector.get("path"):
        issues.append(
            {
                "severity": "info",
                "field": "channel_name",
                "message": f"Detector '{label}' has no explicit channel/path label; UI routing may be less clear.",
            }
        )
    if detector.get("kind") in POINT_DETECTOR_KINDS and detector.get("supports_time_gating") is None:
        issues.append(
            {
                "severity": "info",
                "field": "supports_time_gating",
                "message": f"Point detector '{label}' has no explicit time-gating capability metadata.",
            }
        )
    return issues


def audit_virtual_microscope_instrument(instrument: dict[str, Any]) -> dict[str, Any]:
    canonical = instrument.get("canonical") if isinstance(instrument.get("canonical"), dict) else {}
    hardware = canonical.get("hardware") if isinstance(canonical.get("hardware"), dict) else {}
    light_path = hardware.get("light_path") if isinstance(hardware.get("light_path"), dict) else {}
    payload = generate_virtual_microscope_payload(canonical)
    canonical_model = canonicalize_light_path_model(canonical)

    source_rows = _coerce_component_list(hardware.get("sources")) or _coerce_component_list(hardware.get("light_sources"))
    source_count = len(source_rows)
    detector_count = len(_coerce_component_list(hardware.get("detectors")))
    payload_source_count = sum(len(group.get("positions", {})) for group in payload.get("light_sources", []) if isinstance(group, dict))
    payload_detector_count = len([item for item in payload.get("detectors", []) if isinstance(item, dict)])
    raw_splitters = {"total_distinct_entries": len([item for item in canonical_model.get("optical_path_elements", []) if item.get("stage_role") == "splitter"])}
    payload_splitter_count = len(payload.get("splitters", []))

    issues: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    infos: list[dict[str, str]] = []

    for index, source in enumerate(source_rows):
        for issue in _source_readiness_issue(index, source):
            if issue["severity"] == "warning":
                warnings.append(issue)
            else:
                infos.append(issue)

    for index, detector in enumerate(_coerce_component_list(hardware.get("detectors"))):
        for issue in _detector_readiness_issue(index, detector):
            if issue["severity"] == "warning":
                warnings.append(issue)
            else:
                infos.append(issue)

    if source_count != payload_source_count:
        issues.append(
            {
                "severity": "error",
                "field": "light_sources",
                "message": f"Virtual microscope payload source count mismatch: hardware={source_count}, payload={payload_source_count}.",
            }
        )
    if detector_count != payload_detector_count:
        issues.append(
            {
                "severity": "error",
                "field": "detectors",
                "message": f"Virtual microscope payload detector count mismatch: hardware={detector_count}, payload={payload_detector_count}.",
            }
        )
    if raw_splitters["total_distinct_entries"] != payload_splitter_count:
        issues.append(
            {
                "severity": "error",
                "field": "splitters",
                "message": (
                    "Virtual microscope payload splitter count mismatch: "
                    f"raw_total={raw_splitters['total_distinct_entries']}, payload={payload_splitter_count}."
                ),
            }
        )

    stage_counts = Counter(item.get("stage_role") for item in canonical_model.get("optical_path_elements", []) if isinstance(item, dict))
    payload_stage_counts = {
        stage_name: len(items) if isinstance(items, list) else 0
        for stage_name, items in (payload.get("stages") or {}).items()
    }
    for stage_name, count in stage_counts.items():
        if stage_name == "splitter":
            continue
        if payload_stage_counts.get(stage_name, 0) != count:
            issues.append(
                {
                    "severity": "error",
                    "field": f"stages.{stage_name}",
                    "message": (
                        f"Stage payload mismatch for '{stage_name}': "
                        f"hardware={count}, payload={payload_stage_counts.get(stage_name, 0)}."
                    ),
                }
            )

    mechanism_total = sum(stage_counts.values())
    if mechanism_total and not payload.get("valid_paths"):
        warnings.append(
            {
                "severity": "warning",
                "field": "valid_paths",
                "message": "Light-path mechanisms exist but the payload exposes no valid_paths combinations.",
            }
        )

    if payload.get("metadata", {}).get("wavelength_grid") in (None, {}):
        issues.append(
            {
                "severity": "error",
                "field": "metadata.wavelength_grid",
                "message": "Virtual microscope payload is missing wavelength grid metadata.",
            }
        )

    return {
        "instrument_id": instrument.get("id"),
        "display_name": instrument.get("display_name"),
        "counts": {
            "hardware_sources": source_count,
            "payload_sources": payload_source_count,
            "hardware_detectors": detector_count,
            "payload_detectors": payload_detector_count,
            "raw_splitters": raw_splitters,
            "payload_splitters": payload_splitter_count,
            "hardware_stage_mechanisms": stage_counts,
            "payload_stage_mechanisms": payload_stage_counts,
            "valid_paths": len(payload.get("valid_paths", [])),
        },
        "issues": issues,
        "warnings": warnings,
        "info": infos,
        "readiness": "error" if issues else ("warning" if warnings else "ok"),
    }


def audit_fpbase_runtime_contract(repo_root: Path) -> dict[str, Any]:
    runtime_path = repo_root / "scripts" / "templates" / "virtual_microscope_runtime.js"
    fixture_path = repo_root / "tests" / "fixtures" / "fpbase_mcherry_bundle.json"
    if not runtime_path.exists():
        return {
            "status": "error",
            "message": "virtual_microscope_runtime.js is missing.",
        }
    if not fixture_path.exists():
        return {
            "status": "warning",
            "message": "FPbase mCherry fixture is missing; runtime contract check skipped.",
        }
    if shutil.which("node") is None:
        return {
            "status": "warning",
            "message": "Node.js is not available; FPbase runtime contract check skipped.",
        }

    script = textwrap.dedent(
        """
        const fs = require('fs');
        const path = require('path');
        const rt = require('./scripts/templates/virtual_microscope_runtime.js');
        const bundle = JSON.parse(fs.readFileSync(path.join('tests', 'fixtures', 'fpbase_mcherry_bundle.json'), 'utf8'));
        const summary = rt.normalizeFPbaseSearchResults(bundle.search)[0] || {};
        const fluor = rt.normalizeFluorophoreDetail(bundle.detail, summary, bundle.spectra);
        const result = {
          summaryName: summary.name || '',
          fluorName: fluor.name || '',
          spectraSource: fluor.spectraSource || '',
          exPoints: Array.isArray(fluor.spectra && fluor.spectra.ex1p) ? fluor.spectra.ex1p.length : 0,
          emPoints: Array.isArray(fluor.spectra && fluor.spectra.em) ? fluor.spectra.em.length : 0,
          activeStateName: fluor.activeStateName || '',
          exMax: fluor.exMax ?? null,
          emMax: fluor.emMax ?? null,
        };
        console.log(JSON.stringify(result));
        """
    )
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {
            "status": "error",
            "message": "Node runtime contract check failed.",
            "stderr": proc.stderr.strip(),
        }
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "message": f"Failed to decode Node runtime contract output: {exc}",
            "stdout": proc.stdout,
        }

    ok = payload.get("summaryName") == "mCherry" and payload.get("fluorName") == "mCherry" and payload.get("exPoints", 0) > 0 and payload.get("emPoints", 0) > 0
    return {
        "status": "ok" if ok else "error",
        "message": "mCherry runtime contract passed." if ok else "mCherry runtime contract failed.",
        "result": payload,
    }


def generate_full_audit(
    repo_root: Path,
    *,
    include_retired: bool = True,
    allowed_record_types: tuple[str, ...] = DEFAULT_ALLOWED_RECORD_TYPES,
) -> dict[str, Any]:
    cwd_before = Path.cwd()
    repo_root = repo_root.resolve()
    try:
        # Existing validation helpers resolve repo-relative schema paths from the CWD.
        # Switching CWD here keeps the audit aligned with the repository's own CLI assumptions.
        import os
        os.chdir(repo_root)

        active_load_errors: list[YamlLoadError] = []
        retired_load_errors: list[YamlLoadError] = []
        # Authoritative selection boundary: only validator-selected instruments enter audit DTO checks.
        instrument_ids, instrument_errors, instrument_warnings = validated_instrument_selection("instruments")
        instruments = load_instruments(
            "instruments",
            load_errors=active_load_errors,
            include_retired=False,
            allowed_instrument_ids=instrument_ids,
        )
        retired_instruments = (
            load_instruments(
                "instruments",
                load_errors=retired_load_errors,
                include_retired=True,
                allowed_instrument_ids=instrument_ids,
            )
            if include_retired
            else []
        )

        event_report = validate_event_ledgers(
            instrument_ids=instrument_ids,
            allowed_record_types=allowed_record_types,
        )

        completeness_rows: list[dict[str, Any]] = []
        missing_required_counter: Counter[str] = Counter()
        missing_conditional_counter: Counter[str] = Counter()
        alias_counter: Counter[str] = Counter()
        methods_blocker_counter: Counter[str] = Counter()
        for instrument in [*instruments, *retired_instruments]:
            report = build_instrument_completeness_report(instrument.get("canonical") or {})
            methods_blockers = [
                entry
                for entry in [*report.missing_required, *report.missing_conditional]
                if isinstance(entry, dict) and isinstance(entry.get("used_by"), list) and "method_generator" in entry.get("used_by")
            ]
            completeness_rows.append(
                {
                    "instrument_id": instrument.get("id"),
                    "display_name": instrument.get("display_name"),
                    "missing_required_count": len(report.missing_required),
                    "missing_conditional_count": len(report.missing_conditional),
                    "alias_fallback_count": len(report.alias_fallbacks),
                    "methods_blocker_count": len(methods_blockers),
                    "missing_required": report.missing_required,
                    "missing_conditional": report.missing_conditional,
                    "alias_fallbacks": report.alias_fallbacks,
                    "methods_blockers": methods_blockers,
                }
            )
            missing_required_counter.update(entry.get("path") for entry in report.missing_required if entry.get("path"))
            missing_conditional_counter.update(entry.get("path") for entry in report.missing_conditional if entry.get("path"))
            alias_counter.update(entry.get("path") for entry in report.alias_fallbacks if entry.get("path"))
            methods_blocker_counter.update(entry.get("path") for entry in methods_blockers if entry.get("path"))

        vm_rows = [audit_virtual_microscope_instrument(instrument) for instrument in [*instruments, *retired_instruments]]
        vm_readiness_counter = Counter(row.get("readiness", "unknown") for row in vm_rows)

        inventory = {
            "active_instruments": len(instruments),
            "retired_instruments": len(retired_instruments),
            "instrument_ids": sorted(instrument_ids),
            "yaml_load_failures_active": len(active_load_errors),
            "yaml_load_failures_retired": len(retired_load_errors),
        }

        report = {
            "repo_root": repo_root.as_posix(),
            "inventory": inventory,
            "yaml_loading": {
                "active": _collect_yaml_error_dicts(active_load_errors),
                "retired": _collect_yaml_error_dicts(retired_load_errors),
            },
            "validation": {
                "instrument_errors": {
                    "count": len(instrument_errors),
                    "by_code": _issue_counter(instrument_errors),
                    "items": [_issue_dict(item) for item in instrument_errors],
                },
                "instrument_warnings": {
                    "count": len(instrument_warnings),
                    "by_code": _issue_counter(instrument_warnings),
                    "items": [_issue_dict(item) for item in instrument_warnings],
                },
                "event_errors": {
                    "count": len(event_report.errors),
                    "by_code": _issue_counter(event_report.errors),
                    "items": [_issue_dict(item) for item in event_report.errors],
                },
                "event_warnings": {
                    "count": len(event_report.warnings),
                    "by_code": _issue_counter(event_report.warnings),
                    "items": [_issue_dict(item) for item in event_report.warnings],
                },
                "event_migration_notices": {
                    "count": len(event_report.migration_notices),
                    "by_code": _issue_counter(event_report.migration_notices),
                    "items": [_issue_dict(item) for item in event_report.migration_notices],
                },
            },
            "completeness": {
                "top_missing_required_paths": _top_items(missing_required_counter),
                "top_missing_conditional_paths": _top_items(missing_conditional_counter),
                "top_alias_fallback_paths": _top_items(alias_counter),
                "top_methods_blocker_paths": _top_items(methods_blocker_counter),
                "instruments": completeness_rows,
            },
            "virtual_microscope": {
                "readiness_counts": dict(sorted(vm_readiness_counter.items())),
                "instruments": vm_rows,
            },
            "fpbase_runtime": audit_fpbase_runtime_contract(repo_root),
        }

        total_error_count = (
            len(active_load_errors)
            + len(retired_load_errors)
            + len(instrument_errors)
            + len(event_report.errors)
            + sum(len(row.get("issues", [])) for row in vm_rows)
            + (1 if report["fpbase_runtime"].get("status") == "error" else 0)
        )
        total_warning_count = (
            len(instrument_warnings)
            + len(event_report.warnings)
            + sum(len(row.get("warnings", [])) for row in vm_rows)
            + (1 if report["fpbase_runtime"].get("status") == "warning" else 0)
        )
        report["summary"] = {
            "errors": total_error_count,
            "warnings": total_warning_count,
            "status": "fail" if total_error_count else ("warn" if total_warning_count else "ok"),
        }
        return _as_serializable(report)
    finally:
        import os
        os.chdir(cwd_before)


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Repository Audit",
        "",
        f"- Status: **{report['summary']['status']}**",
        f"- Errors: **{report['summary']['errors']}**",
        f"- Warnings: **{report['summary']['warnings']}**",
        "",
        "## Inventory",
        "",
        f"- Active instruments: {report['inventory']['active_instruments']}",
        f"- Retired instruments: {report['inventory']['retired_instruments']}",
        f"- Active YAML load failures: {report['inventory']['yaml_load_failures_active']}",
        f"- Retired YAML load failures: {report['inventory']['yaml_load_failures_retired']}",
        "",
        "## Validation",
        "",
        f"- Instrument errors: {report['validation']['instrument_errors']['count']}",
        f"- Instrument warnings: {report['validation']['instrument_warnings']['count']}",
        f"- Event errors: {report['validation']['event_errors']['count']}",
        f"- Event warnings: {report['validation']['event_warnings']['count']}",
        "",
        "### Most common missing required instrument-policy fields",
        "",
    ]
    top_required = report["completeness"]["top_missing_required_paths"]
    if top_required:
        for item in top_required:
            lines.append(f"- `{item['name']}` — {item['count']}")
    else:
        lines.append("- None")

    lines.extend([
        "",
        "### Most common missing conditional instrument-policy fields",
        "",
    ])
    top_conditional = report["completeness"].get("top_missing_conditional_paths", [])
    if top_conditional:
        for item in top_conditional:
            lines.append(f"- `{item['name']}` — {item['count']}")
    else:
        lines.append("- None")

    lines.extend([
        "",
        "### Common alias fallback paths",
        "",
    ])
    top_aliases = report["completeness"].get("top_alias_fallback_paths", [])
    if top_aliases:
        for item in top_aliases:
            lines.append(f"- `{item['name']}` — {item['count']}")
    else:
        lines.append("- None")

    lines.extend([
        "",
        "### Fields currently blocking trustworthy methods generation",
        "",
    ])
    top_methods = report["completeness"].get("top_methods_blocker_paths", [])
    if top_methods:
        for item in top_methods:
            lines.append(f"- `{item['name']}` — {item['count']}")
    else:
        lines.append("- None")

    lines.extend([
        "",
        "### Virtual microscope readiness",
        "",
    ])
    readiness_counts = report["virtual_microscope"].get("readiness_counts", {})
    if readiness_counts:
        for key in sorted(readiness_counts):
            lines.append(f"- {key}: {readiness_counts[key]}")
    else:
        lines.append("- No virtual microscope audit rows generated.")

    fpbase = report.get("fpbase_runtime", {})
    lines.extend([
        "",
        "### FPbase/browser runtime contract",
        "",
        f"- Status: {fpbase.get('status', 'unknown')}",
        f"- {fpbase.get('message', 'No message')}",
        "",
        "## Highest-priority virtual microscope issues",
        "",
    ])
    vm_rows = report["virtual_microscope"].get("instruments", [])
    ranked = sorted(vm_rows, key=lambda row: (len(row.get("issues", [])), len(row.get("warnings", []))), reverse=True)
    if ranked:
        for row in ranked[:10]:
            if not row.get("issues") and not row.get("warnings"):
                continue
            lines.append(f"### {row.get('display_name') or row.get('instrument_id')}")
            for issue in row.get("issues", [])[:5]:
                lines.append(f"- ERROR: {issue.get('message')}")
            for warning in row.get("warnings", [])[:5]:
                lines.append(f"- Warning: {warning.get('message')}")
            lines.append("")
    else:
        lines.append("- None")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a full repository audit.")
    parser.add_argument("--repo-root", default=".", help="Repository root to audit.")
    parser.add_argument("--json-out", default="audit/full_audit.json", help="Path for JSON audit output, relative to repo root unless absolute.")
    parser.add_argument("--markdown-out", default="audit/full_audit.md", help="Path for Markdown audit output, relative to repo root unless absolute.")
    parser.add_argument("--skip-retired", action="store_true", help="Skip retired instrument YAML files.")
    parser.add_argument(
        "--allowed-record-types",
        default=",".join(DEFAULT_ALLOWED_RECORD_TYPES),
        help="Comma-separated record types passed through to event validation.",
    )
    return parser.parse_args(argv)


def _resolve_output_path(repo_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    allowed_record_types = tuple(item.strip() for item in args.allowed_record_types.split(",") if item.strip()) or DEFAULT_ALLOWED_RECORD_TYPES
    report = generate_full_audit(
        repo_root,
        include_retired=not args.skip_retired,
        allowed_record_types=allowed_record_types,
    )

    json_out = _resolve_output_path(repo_root, args.json_out)
    markdown_out = _resolve_output_path(repo_root, args.markdown_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    markdown_out.write_text(render_markdown_report(report), encoding="utf-8")

    print(f"Audit JSON written to {json_out}")
    print(f"Audit Markdown written to {markdown_out}")
    print(f"Status={report['summary']['status']} errors={report['summary']['errors']} warnings={report['summary']['warnings']}")
    return 1 if report["summary"]["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
