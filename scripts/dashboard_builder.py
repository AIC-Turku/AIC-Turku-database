"""Build MkDocs Material dashboard pages from YAML ledgers.

Pipeline
- instruments/*.yaml           -> instrument registry
- qc/sessions/**/<year>/*.yaml -> QC sessions
- maintenance/events/**/*.yaml -> maintenance events

The script normalizes metadata, fixes routing (stable slug IDs), renders pages via
Jinja2 templates, and writes a complete mkdocs.yml for GitHub Pages builds.
"""

from __future__ import annotations

import os
import re
import shutil
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader


METRIC_NAMES: dict[str, str] = {
    "psf.fwhm_x_um": "PSF lateral FWHM (X, µm)",
    "psf.fwhm_y_um": "PSF lateral FWHM (Y, µm)",
    "psf.fwhm_z_um": "PSF axial FWHM (Z, µm)",
    "psf.fit_r2": "PSF fit R²",
    "coreg.distance_488_561_um": "Co-registration (488↔561, µm)",
    "stage.repeatability_sigma_x_um": "Stage repeatability σ (X, µm)",
    "stage.repeatability_sigma_y_um": "Stage repeatability σ (Y, µm)",
    "laser.power_mw_405": "Laser power (405 nm, mW)",
    "laser.power_mw_488": "Laser power (488 nm, mW)",
    "laser.power_mw_561": "Laser power (561 nm, mW)",
    "laser.power_mw_640": "Laser power (640 nm, mW)",
    "laser.short_term_stability_delta_percent_488": "Laser stability Δ% (488 nm)",
    "laser.long_term_stability_delta_percent_488": "Laser long-term stability Δ% (488 nm)",
    "illumination.uniformity_percent": "Illumination uniformity (%)",
    "detector.dark_noise_electrons": "Detector dark noise (e⁻)",
}

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".svg")


# -----------------------------------------------------------------------------
# YAML + datetime helpers
# -----------------------------------------------------------------------------

def _iter_yaml_files(base_dir: Path):
    """Yield YAML files under ``base_dir`` in deterministic order."""
    if not base_dir.exists() or not base_dir.is_dir():
        return

    for candidate in sorted(base_dir.rglob("*")):
        if candidate.is_file() and candidate.suffix.lower() in {".yaml", ".yml"}:
            yield candidate


def _load_yaml_file(path: Path) -> dict[str, Any] | None:
    """Safely load a YAML mapping from disk and return ``None`` on invalid data."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            parsed = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError):
        return None

    return parsed if isinstance(parsed, dict) else None


def _parse_iso_datetime(raw_value: Any) -> datetime | None:
    """Parse an ISO-like datetime string and normalize to UTC-aware datetime."""
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None

    normalized = raw_value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed


def _timestamp_from_filename(path: Path) -> datetime | None:
    """Extract a date/time from a ledger filename stem."""
    stem = path.stem
    first_chunk = stem.split("_", 1)[0]

    full_ts = first_chunk.replace("Z", "+00:00")
    if "T" in full_ts:
        date_part, time_part = full_ts.split("T", 1)
        if "+" not in time_part and "-" in time_part and time_part.count("-") >= 2:
            parts = time_part.split("-")
            if len(parts) >= 3:
                time_part = ":".join(parts[:3])
                full_ts = f"{date_part}T{time_part}"

    parsed = _parse_iso_datetime(full_ts)
    if parsed:
        return parsed

    try:
        return datetime.strptime(first_chunk, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _extract_log_date(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return ""

    for key in ("started_utc", "timestamp_utc", "date"):
        parsed = _parse_iso_datetime(payload.get(key))
        if parsed is not None:
            return parsed.date().isoformat()

    return ""


# -----------------------------------------------------------------------------
# Instrument normalization
# -----------------------------------------------------------------------------

def slugify(text: str) -> str:
    """ASCII + URL-safe slug (lowercase, hyphen-separated)."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "scope"


def _format_location(raw_location: Any) -> str:
    if isinstance(raw_location, str) and raw_location.strip():
        return raw_location.strip()

    if isinstance(raw_location, dict):
        parts: list[str] = []
        for key in ("site", "building", "room"):
            val = raw_location.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val.strip())
        return " · ".join(parts)

    return ""


def _format_contacts(raw_contacts: Any) -> list[str]:
    """Return a compact list of contact strings for display."""
    out: list[str] = []
    if isinstance(raw_contacts, list):
        for item in raw_contacts:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict):
                name = (item.get("name") or "").strip() if isinstance(item.get("name"), str) else ""
                email = (item.get("email") or "").strip() if isinstance(item.get("email"), str) else ""
                role = (item.get("role") or "").strip() if isinstance(item.get("role"), str) else ""

                label = name or email
                if not label:
                    continue

                if email and name:
                    label = f"{name} <{email}>"
                if role:
                    label = f"{label} ({role})"
                out.append(label)
    elif isinstance(raw_contacts, dict):
        # Single contact object
        out.extend(_format_contacts([raw_contacts]))

    return out


def _normalize_software(raw_software: Any) -> list[dict[str, str]]:
    """Normalize arbitrary software layouts to a simple list."""
    out: list[dict[str, str]] = []

    def add(component: str, entry: Any):
        if isinstance(entry, dict):
            name = entry.get("name")
            version = entry.get("version")
            if isinstance(name, str) and name.strip():
                out.append(
                    {
                        "component": component,
                        "name": name.strip(),
                        "version": (version.strip() if isinstance(version, str) else ""),
                    }
                )
        elif isinstance(entry, str) and entry.strip():
            out.append({"component": component, "name": entry.strip(), "version": ""})

    if isinstance(raw_software, dict):
        for component, entry in raw_software.items():
            if isinstance(entry, list):
                for item in entry:
                    add(str(component), item)
            else:
                add(str(component), entry)
    elif isinstance(raw_software, list):
        for item in raw_software:
            if isinstance(item, dict):
                component = item.get("component") if isinstance(item.get("component"), str) else "software"
                add(component, item)

    return out


def _find_image_filename(assets_images_dir: Path, instrument_id: str) -> str:
    for ext in IMAGE_EXTS:
        candidate = assets_images_dir / f"{instrument_id}{ext}"
        if candidate.exists():
            return candidate.name
    return "placeholder.svg"


def normalize_instrument(payload: dict[str, Any], source_path: Path, assets_images_dir: Path) -> dict[str, Any]:
    instrument_section = payload.get("instrument") if isinstance(payload.get("instrument"), dict) else {}

    display_name = instrument_section.get("display_name")
    if not isinstance(display_name, str) or not display_name.strip():
        display_name = source_path.stem

    instrument_id = instrument_section.get("instrument_id")
    if not isinstance(instrument_id, str) or not instrument_id.strip():
        # Robust fallback (should not happen if instruments are maintained correctly)
        instrument_id = f"scope-{slugify(display_name)}"

    manufacturer = instrument_section.get("manufacturer")
    model = instrument_section.get("model")
    stand_orientation = instrument_section.get("stand_orientation")
    notes = instrument_section.get("notes")

    location = _format_location(instrument_section.get("location"))

    booking_url = instrument_section.get("booking_url")
    if not (isinstance(booking_url, str) and booking_url.strip()):
        booking = instrument_section.get("booking")
        if isinstance(booking, dict) and isinstance(booking.get("url"), str):
            booking_url = booking.get("url")

    contacts = _format_contacts(instrument_section.get("contacts"))

    modalities = payload.get("modalities") if isinstance(payload.get("modalities"), list) else []
    modalities = [m for m in modalities if isinstance(m, str) and m.strip()]

    modules = payload.get("modules") if isinstance(payload.get("modules"), list) else []
    modules = [m for m in modules if isinstance(m, str) and m.strip()]

    software = _normalize_software(payload.get("software"))

    hardware = payload.get("hardware") if isinstance(payload.get("hardware"), dict) else {}

    image_filename = _find_image_filename(assets_images_dir, instrument_id)

    return {
        "id": instrument_id,
        "instrument_id": instrument_id,
        "display_name": display_name,
        "manufacturer": manufacturer.strip() if isinstance(manufacturer, str) else "",
        "model": model.strip() if isinstance(model, str) else "",
        "stand_orientation": stand_orientation.strip() if isinstance(stand_orientation, str) else "",
        "notes": notes.strip() if isinstance(notes, str) else "",
        "location": location,
        "booking_url": booking_url.strip() if isinstance(booking_url, str) else "",
        "contacts": contacts,
        "modalities": modalities,
        "modules": modules,
        "software": software,
        "hardware": hardware,
        "image_filename": image_filename,
        # Filled later:
        "status": {},
        "latest_metrics": [],
        "latest_qc_overall": "",
        "charts_data": {},
    }


def get_all_instruments(instruments_dir: str, assets_images_dir: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    for yaml_file in _iter_yaml_files(Path(instruments_dir)):
        payload = _load_yaml_file(yaml_file)
        if payload is None:
            continue

        inst = normalize_instrument(payload, yaml_file, assets_images_dir)
        if inst["id"] in result:
            # Rare collision -> disambiguate deterministically.
            inst["id"] = f"{inst['id']}-{slugify(yaml_file.stem)}"
            inst["instrument_id"] = inst["id"]
        result[inst["id"]] = inst

    return result


# -----------------------------------------------------------------------------
# Logs + status
# -----------------------------------------------------------------------------

def get_all_instrument_logs(log_base_dir: str, instrument_id: str) -> list[dict[str, Any]]:
    if not instrument_id or not instrument_id.strip():
        return []

    base_path = Path(log_base_dir)
    target_id = instrument_id.strip()
    candidates: list[tuple[datetime, Path, dict[str, Any]]] = []

    for yaml_file in _iter_yaml_files(base_path):
        payload = _load_yaml_file(yaml_file)
        if payload is None:
            continue

        payload_instrument = payload.get("microscope")
        if not isinstance(payload_instrument, str):
            payload_instrument = payload.get("instrument_id")

        if payload_instrument != target_id:
            continue

        sort_dt = _parse_iso_datetime(payload.get("started_utc"))
        if sort_dt is None:
            sort_dt = _timestamp_from_filename(yaml_file)
        if sort_dt is None:
            sort_dt = datetime.min.replace(tzinfo=timezone.utc)

        candidates.append((sort_dt, yaml_file, payload))

    candidates.sort(key=lambda item: (item[0], item[1].as_posix()))
    return [
        {
            "source_path": path.as_posix(),
            "filename": path.name,
            "data": payload,
        }
        for _, path, payload in candidates
    ]


def evaluate_instrument_status(
    latest_qc: dict[str, Any] | None,
    latest_maint: dict[str, Any] | None,
    now_utc: datetime,
    qc_overdue_days: int = 120,
) -> dict[str, str]:
    """Compute UI status from newest QC + maintenance entries."""

    last_qc_dt = _parse_iso_datetime((latest_qc or {}).get("started_utc")) if isinstance(latest_qc, dict) else None
    last_maint_dt = _parse_iso_datetime((latest_maint or {}).get("started_utc")) if isinstance(latest_maint, dict) else None

    last_qc_date = last_qc_dt.date().isoformat() if last_qc_dt else ""
    last_maint_date = last_maint_dt.date().isoformat() if last_maint_dt else ""

    maint_status = ""
    maint_reason = ""
    if isinstance(latest_maint, dict):
        raw = latest_maint.get("microscope_status_after")
        if isinstance(raw, str):
            maint_status = raw.strip().lower()

        for key in ("reason_details", "action_details", "action"):
            v = latest_maint.get(key)
            if isinstance(v, str) and v.strip():
                maint_reason = v.strip()
                break

    qc_status = ""
    qc_reason = ""
    if isinstance(latest_qc, dict):
        evaluation = latest_qc.get("evaluation")
        if isinstance(evaluation, dict):
            raw = evaluation.get("overall_status")
            if isinstance(raw, str):
                qc_status = raw.strip().lower()

            results = evaluation.get("results")
            if isinstance(results, list) and results:
                first = results[0]
                if isinstance(first, dict):
                    msg = first.get("message")
                    if isinstance(msg, str) and msg.strip():
                        qc_reason = msg.strip()

    # Priority: offline -> warning -> ok
    if maint_status == "out_of_service" or qc_status == "fail":
        reason = maint_reason or qc_reason or "Out of service"
        return {
            "color": "red",
            "badge": "🔴 Offline",
            "reason": reason,
            "last_qc_date": last_qc_date,
            "last_maint_date": last_maint_date,
        }

    if maint_status == "limited" or qc_status == "warn":
        reason = maint_reason or qc_reason or "Limited operation"
        return {
            "color": "yellow",
            "badge": "🟡 Warning",
            "reason": reason,
            "last_qc_date": last_qc_date,
            "last_maint_date": last_maint_date,
        }

    # Optional: stale QC can be a soft warning
    if last_qc_dt and last_qc_dt <= now_utc - timedelta(days=qc_overdue_days):
        return {
            "color": "yellow",
            "badge": "🟡 Warning",
            "reason": f"QC overdue (> {qc_overdue_days} days)",
            "last_qc_date": last_qc_date,
            "last_maint_date": last_maint_date,
        }

    return {
        "color": "green",
        "badge": "🟢 Online",
        "reason": "Operational",
        "last_qc_date": last_qc_date,
        "last_maint_date": last_maint_date,
    }


def _metrics_list(metrics_computed: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(metrics_computed, list):
        return out

    for entry in metrics_computed:
        if not isinstance(entry, dict):
            continue
        metric_id = entry.get("metric_id")
        if not isinstance(metric_id, str) or not metric_id.strip():
            continue

        value = entry.get("value")
        unit = entry.get("unit")
        details = entry.get("details")
        out.append(
            {
                "metric_id": metric_id,
                "value": value,
                "unit": unit if isinstance(unit, str) else "",
                "details": details if isinstance(details, str) else "",
            }
        )

    return out


def build_charts_data(qc_logs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return {metric_id: {labels:[...], values:[...]}}."""
    metric_ids: set[str] = set()
    parsed_logs: list[tuple[str, dict[str, Any]]] = []

    for entry in qc_logs:
        payload = entry.get("data")
        if not isinstance(payload, dict):
            continue
        dt = _parse_iso_datetime(payload.get("started_utc"))
        if dt is None:
            continue
        label = dt.strftime("%Y-%m-%d")
        metrics = _metrics_list(payload.get("metrics_computed"))
        for m in metrics:
            metric_ids.add(m["metric_id"])
        parsed_logs.append((label, {m["metric_id"]: m.get("value") for m in metrics}))

    charts: dict[str, dict[str, Any]] = {}
    for metric_id in sorted(metric_ids):
        labels: list[str] = []
        values: list[Any] = []
        for label, metric_map in parsed_logs:
            labels.append(label)
            v = metric_map.get(metric_id)
            values.append(v if isinstance(v, (int, float)) else None)

        if any(v is not None for v in values):
            charts[metric_id] = {"labels": labels, "values": values}

    return charts


# -----------------------------------------------------------------------------
# Build
# -----------------------------------------------------------------------------

def build_mkdocs_nav(instruments: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate MkDocs navigation.

    Requirement: the left sidebar should show **only instrument names** (clickable),
    without nested Overview/History nodes. History remains accessible via internal
    links from each instrument page.
    """

    microscopes_nav: list[dict[str, Any]] = []

    for inst_id, inst in sorted(instruments.items(), key=lambda kv: kv[1]["display_name"].lower()):
        microscopes_nav.append({inst["display_name"]: f"instruments/{inst_id}/index.md"})

    return [
        {"Fleet Overview": "index.md"},
        {"System Health": "status.md"},
        {"Microscopes": microscopes_nav},
    ]



def copy_assets_to_docs(docs_root: Path) -> None:
    src_assets = Path("assets")
    if src_assets.exists() and src_assets.is_dir():
        shutil.copytree(src_assets, docs_root / "assets", dirs_exist_ok=True)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)

    docs_root = Path("dashboard_docs")
    if docs_root.exists():
        shutil.rmtree(docs_root)

    (docs_root / "instruments").mkdir(parents=True, exist_ok=True)
    (docs_root / "events").mkdir(parents=True, exist_ok=True)

    copy_assets_to_docs(docs_root)

    assets_images_dir = repo_root / "assets" / "images"

    templates_dir = Path(__file__).resolve().parent / "templates"
    jinja_env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    index_template = jinja_env.get_template("index.md.j2")
    status_template = jinja_env.get_template("status.md.j2")
    instrument_spec_template = jinja_env.get_template("instrument_spec.md.j2")
    instrument_history_template = jinja_env.get_template("instrument_history.md.j2")
    event_detail_template = jinja_env.get_template("event_detail.md.j2")

    instruments = get_all_instruments("instruments", assets_images_dir)

    now_utc = datetime.now(timezone.utc)

    # Pass 1: attach logs, status, charts
    all_modalities: set[str] = set()
    issues: list[dict[str, Any]] = []

    for inst_id, inst in instruments.items():
        # Modalities set for fleet filter
        for mod in inst.get("modalities", []):
            all_modalities.add(mod)

        qc_logs = get_all_instrument_logs("qc/sessions", inst_id)
        maint_logs = get_all_instrument_logs("maintenance/events", inst_id)

        latest_qc = qc_logs[-1]["data"] if qc_logs else None
        latest_maint = maint_logs[-1]["data"] if maint_logs else None

        inst["status"] = evaluate_instrument_status(latest_qc, latest_maint, now_utc)

        inst["charts_data"] = build_charts_data(qc_logs)
        inst["latest_metrics"] = _metrics_list((latest_qc or {}).get("metrics_computed")) if isinstance(latest_qc, dict) else []

        if isinstance(latest_qc, dict):
            eval_block = latest_qc.get("evaluation")
            if isinstance(eval_block, dict) and isinstance(eval_block.get("overall_status"), str):
                inst["latest_qc_overall"] = eval_block.get("overall_status")

        if inst["status"].get("color") in {"red", "yellow"}:
            issues.append(inst)

        # Render instrument pages
        inst_dir = docs_root / "instruments" / inst_id
        inst_dir.mkdir(parents=True, exist_ok=True)

        hardware = inst.get("hardware") if isinstance(inst.get("hardware"), dict) else {}
        light_sources = [s for s in hardware.get("light_sources", []) if isinstance(s, dict)]
        detectors = [d for d in hardware.get("detectors", []) if isinstance(d, dict)]
        objectives = [o for o in hardware.get("objectives", []) if isinstance(o, dict)]

        spec_rendered = instrument_spec_template.render(
            instrument=inst,
            light_sources=light_sources,
            detectors=detectors,
            objectives=objectives,
            software=inst.get("software", []),
            latest_metrics=inst.get("latest_metrics", []),
            latest_qc_overall=inst.get("latest_qc_overall", ""),
            charts_data=inst.get("charts_data", {}),
            metric_names=METRIC_NAMES,
        )
        (inst_dir / "index.md").write_text(spec_rendered, encoding="utf-8")

        # Build history tables
        qc_events: list[dict[str, Any]] = []
        for qc_log in qc_logs:
            payload = qc_log.get("data") if isinstance(qc_log.get("data"), dict) else {}
            event_id = Path(str(qc_log.get("filename", ""))).stem
            evaluation = payload.get("evaluation") if isinstance(payload.get("evaluation"), dict) else {}
            qc_events.append(
                {
                    "event_id": event_id,
                    "date": _extract_log_date(payload),
                    "reason": payload.get("reason"),
                    "operator": payload.get("performed_by"),
                    "overall_status": evaluation.get("overall_status") if isinstance(evaluation.get("overall_status"), str) else "",
                }
            )

        maint_events: list[dict[str, Any]] = []
        for m_log in maint_logs:
            payload = m_log.get("data") if isinstance(m_log.get("data"), dict) else {}
            event_id = Path(str(m_log.get("filename", ""))).stem
            provider = payload.get("company") or payload.get("service_provider")
            maint_events.append(
                {
                    "event_id": event_id,
                    "date": _extract_log_date(payload),
                    "reason": payload.get("reason"),
                    "provider": provider,
                    "status_after": payload.get("microscope_status_after"),
                }
            )

        history_rendered = instrument_history_template.render(
            instrument=inst,
            qc_events=qc_events,
            maintenance_events=maint_events,
            charts_data=inst.get("charts_data", {}),
            metric_names=METRIC_NAMES,
        )
        (inst_dir / "history.md").write_text(history_rendered, encoding="utf-8")

        # Render event details (QC + maintenance)
        for log_entry in qc_logs + maint_logs:
            source_path = log_entry.get("source_path")
            if not isinstance(source_path, str):
                continue

            source_file = Path(source_path)
            event_id = source_file.stem
            payload = log_entry.get("data") if isinstance(log_entry.get("data"), dict) else {}

            try:
                raw_yaml_text = source_file.read_text(encoding="utf-8")
            except OSError:
                raw_yaml_text = yaml.safe_dump(payload, sort_keys=False)

            record_type = payload.get("record_type") if isinstance(payload.get("record_type"), str) else ""

            event_ctx: dict[str, Any] = {
                "record_type": record_type,
                "date": _extract_log_date(payload),
                "actor": payload.get("performed_by") or payload.get("service_provider") or payload.get("company"),
                "reason": payload.get("reason"),
                "action": payload.get("action"),
                "status_after": payload.get("microscope_status_after"),
                "provider": payload.get("company") or payload.get("service_provider"),
                "summary": payload.get("summary"),
                "overall_status": "",
                "results": [],
            }

            if record_type == "qc_session":
                evaluation = payload.get("evaluation") if isinstance(payload.get("evaluation"), dict) else {}
                overall = evaluation.get("overall_status") if isinstance(evaluation.get("overall_status"), str) else ""
                event_ctx["overall_status"] = overall
                results: list[dict[str, Any]] = []
                raw_results = evaluation.get("results")
                if isinstance(raw_results, list):
                    for r in raw_results:
                        if not isinstance(r, dict):
                            continue
                        mid = r.get("metric_id")
                        stat = r.get("status")
                        if not (isinstance(mid, str) and isinstance(stat, str)):
                            continue
                        results.append(
                            {
                                "metric_id": mid,
                                "status": stat,
                                "threshold": r.get("threshold"),
                                "message": r.get("message"),
                            }
                        )
                event_ctx["results"] = results

            event_rendered = event_detail_template.render(
                event_id=event_id,
                instrument_id=inst_id,
                instrument_display_name=inst.get("display_name"),
                event=event_ctx,
                raw_yaml_content=raw_yaml_text,
            )
            (docs_root / "events" / f"{event_id}.md").write_text(event_rendered, encoding="utf-8")

    # Render fleet pages
    stats = {
        "total": len(instruments),
        "green": sum(1 for i in instruments.values() if i.get("status", {}).get("color") == "green"),
        "yellow": sum(1 for i in instruments.values() if i.get("status", {}).get("color") == "yellow"),
        "red": sum(1 for i in instruments.values() if i.get("status", {}).get("color") == "red"),
    }

    index_rendered = index_template.render(
        instruments=sorted(instruments.values(), key=lambda x: x.get("display_name", "").lower()),
        all_modalities=sorted(all_modalities, key=lambda s: s.lower()),
        stats=stats,
    )
    (docs_root / "index.md").write_text(index_rendered, encoding="utf-8")

    status_rendered = status_template.render(
        issues=sorted(issues, key=lambda x: (x.get("status", {}).get("color", ""), x.get("display_name", "").lower()))
    )
    (docs_root / "status.md").write_text(status_rendered, encoding="utf-8")

    # Write mkdocs.yml (authoritative for the build)
    nav_structure = build_mkdocs_nav(instruments)

    mkdocs_config: dict[str, Any] = {
        "site_name": "AIC Microscopy Dashboard",
        "site_url": "https://aic-turku.github.io/AIC-Turku-database/",
        "docs_dir": "dashboard_docs",
        "use_directory_urls": True,
        "theme": {
            "name": "material",
            "logo": "assets/images/logo.svg",
            "favicon": "assets/images/favicon.svg",
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
                    "toggle": {"icon": "material/brightness-7", "name": "Switch to dark mode"},
                },
                {
                    "scheme": "slate",
                    "toggle": {"icon": "material/brightness-4", "name": "Switch to light mode"},
                },
            ],
        },
        "markdown_extensions": [
            "attr_list",
            "md_in_html",
            "pymdownx.details",
            "pymdownx.superfences",
            {"pymdownx.tabbed": {"alternate_style": True}},
        ],
        "plugins": ["search"],
        "extra_css": ["assets/stylesheets/dashboard.css"],
        "extra_javascript": [
            "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js",
            "assets/javascripts/charts.js",
            "assets/javascripts/dashboard.js",
        ],
        "nav": nav_structure,
    }

    Path("mkdocs.yml").write_text(yaml.safe_dump(mkdocs_config, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
