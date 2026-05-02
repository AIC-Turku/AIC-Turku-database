"""Central per-instrument build context for canonical and derived DTO flows.

Downstream exporters/views must consume canonical and/or derived DTO data from this
context. Production consumers should not re-read or reinterpret raw YAML when the
needed information already exists in canonical DTO fields.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.lightpath.vm_payload import generate_virtual_microscope_payload
from scripts.lightpath.parse_canonical import canonicalize_light_path_model_strict
from scripts.validate import build_instrument_completeness_report


@dataclass
class InstrumentBuildContext:
    """Single source build context for one instrument.

    Fields are intentionally separated between canonical DTOs, derived view DTOs,
    export payloads, and diagnostics.
    """

    instrument_id: str
    source_path: str
    raw_yaml: dict[str, Any]
    validated_yaml: dict[str, Any]
    validation_diagnostics: list[dict[str, Any]]
    canonical_instrument_dto: dict[str, Any]
    canonical_lightpath_dto: dict[str, Any]
    dashboard_view_dto: dict[str, Any]
    methods_export_dto: dict[str, Any]
    methods_view_dto: dict[str, Any]
    llm_inventory_record: dict[str, Any]
    vm_payload: dict[str, Any]
    diagnostics: list[dict[str, str]]


def _diag(*, severity: str, code: str, path: str, message: str, source: str, affected_export: str) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "path": path,
        "message": message,
        "source": source,
        "affected_export": affected_export,
    }


def _build_vm_payload_from_canonical_lightpath(
    canonical_lightpath_dto: dict[str, Any],
    diagnostics: list[dict[str, str]],
) -> dict[str, Any]:
    """Build VM export payload strictly from canonical light-path DTO.

    VM payload source-of-truth is canonical light-path DTO only. Dashboard optical
    path view DTOs (`hardware.optical_path`, `route_renderables`, etc.) are
    display-only and must never be used as VM export authority.
    """
    vm_payload = copy.deepcopy(canonical_lightpath_dto if isinstance(canonical_lightpath_dto, dict) else {})
    for key in ("sources", "optical_path_elements", "endpoints", "light_paths"):
        if key not in vm_payload:
            diagnostics.append(_diag(
                severity="error",
                code="missing_vm_canonical_key",
                path=f"canonical_lightpath_dto.{key}",
                message=f"Missing canonical VM payload key: {key}",
                source="canonical_lightpath_dto",
                affected_export="vm",
            ))
    return vm_payload




def build_instrument_context(
    inst: dict[str, Any],
    *,
    vocabulary: Any,
    build_dashboard_view_dto,
    build_methods_view_dto,
    build_llm_inventory_record,
) -> InstrumentBuildContext:
    """Construct a single build context for one already-validated instrument.

    The context is built once and may be passed to dashboard rendering, methods
    export, LLM export, VM export, and audit/report code to avoid divergent data
    paths across consumers.
    """

    diagnostics: list[dict[str, str]] = []

    source_path = str(inst.get("source_file") or "")
    source_payload = copy.deepcopy(inst.get("source_payload") or {})
    canonical_payload = copy.deepcopy(inst.get("canonical") or {})
    policy = ((inst.get("canonical") or {}).get("policy") or {}) if isinstance(inst, dict) else {}
    validation_diagnostics = copy.deepcopy([
        *(((policy.get("missing_required") if isinstance(policy.get("missing_required"), list) else []) or [])),
        *(((policy.get("missing_conditional") if isinstance(policy.get("missing_conditional"), list) else []) or [])),
    ])

    if not canonical_payload:
        diagnostics.append(_diag(severity="error", code="missing_canonical", path="canonical", message="Instrument canonical DTO is missing.", source="build_context", affected_export="all"))

    try:
        canonicalize_light_path_model_strict(canonical_payload if isinstance(canonical_payload, dict) else {})
        canonical_lightpath_dto = generate_virtual_microscope_payload(
            canonical_payload if isinstance(canonical_payload, dict) else {"hardware": {}},
            include_inferred_terminals=False,
            vocab=vocabulary,
        )
    except Exception as exc:  # diagnostics must be captured, not swallowed
        canonical_lightpath_dto = {}
        diagnostics.append(_diag(severity="error", code="lightpath_payload_error", path="canonical.light_paths", message=str(exc), source="build_context", affected_export="all"))

    build_input = copy.deepcopy(inst)
    build_input["canonical"] = copy.deepcopy(canonical_payload if isinstance(canonical_payload, dict) else {})
    build_input["lightpath_dto"] = copy.deepcopy(canonical_lightpath_dto if isinstance(canonical_lightpath_dto, dict) else {})

    dashboard_view_dto = build_dashboard_view_dto(vocabulary, build_input, build_input["lightpath_dto"])
    build_input["dto"] = copy.deepcopy(dashboard_view_dto if isinstance(dashboard_view_dto, dict) else {})
    # Propagate authoritative_route_contract from dashboard view into lightpath_dto.projections.llm
    # so LLM and methods exports can access it from a consistent location without re-reading the dashboard view.
    if isinstance(dashboard_view_dto, dict) and isinstance(build_input.get("lightpath_dto"), dict):
        _optical_path = ((dashboard_view_dto.get("hardware") or {}).get("optical_path") or {}) if isinstance((dashboard_view_dto.get("hardware") or {}).get("optical_path"), dict) else {}
        _arc = _optical_path.get("authoritative_route_contract") if isinstance(_optical_path.get("authoritative_route_contract"), dict) else None
        if _arc:
            build_input["lightpath_dto"].setdefault("projections", {}).setdefault("llm", {})["authoritative_route_contract"] = copy.deepcopy(_arc)
    methods_export_dto = build_methods_view_dto(build_input)
    llm_inventory_record = build_llm_inventory_record(build_input)

    # VM payload must consume the canonical parser DTO directly. Dashboard view DTOs
    # are display-only and must not be used as VM authority.
    vm_payload = _build_vm_payload_from_canonical_lightpath(canonical_lightpath_dto, diagnostics)
    # Inject instrument identity so downstream code can identify the source instrument.
    if isinstance(vm_payload, dict) and isinstance(canonical_payload.get("instrument"), dict):
        vm_payload["instrument"] = copy.deepcopy(canonical_payload["instrument"])
    light_paths = vm_payload.get("light_paths") if isinstance(vm_payload.get("light_paths"), list) else []
    for index, route in enumerate(light_paths):
        if not isinstance(route, dict):
            continue
        if not isinstance(route.get("selected_execution"), dict):
            diagnostics.append(_diag(
                severity="error",
                code="missing_selected_execution",
                path=f"light_paths[{index}].selected_execution",
                message="Missing required selected_execution for route.",
                source="canonical_lightpath_dto",
                affected_export="vm",
            ))
    if not vm_payload:
        diagnostics.append(_diag(severity="warning", code="missing_vm_payload", path="canonical_lightpath_dto", message="missing in DTO: canonical_lightpath_dto", source="build_context", affected_export="vm"))
    blocking_error = any(item.get("severity") == "error" for item in diagnostics)
    if any(item.get("severity") == "error" and item.get("affected_export") in {"vm", "all"} for item in diagnostics):
        vm_payload = {"export_diagnostics": copy.deepcopy(diagnostics)}
    if blocking_error:
        dashboard_view_dto = {"export_diagnostics": copy.deepcopy(diagnostics)}
        methods_export_dto = {"export_diagnostics": copy.deepcopy(diagnostics)}
        llm_inventory_record = {"export_diagnostics": copy.deepcopy(diagnostics)}

    return InstrumentBuildContext(
        instrument_id=str(inst.get("id") or ""),
        source_path=source_path,
        raw_yaml=source_payload if isinstance(source_payload, dict) else {},
        validated_yaml=copy.deepcopy(inst),
        validation_diagnostics=validation_diagnostics if isinstance(validation_diagnostics, list) else [],
        canonical_instrument_dto=canonical_payload if isinstance(canonical_payload, dict) else {},
        canonical_lightpath_dto=canonical_lightpath_dto if isinstance(canonical_lightpath_dto, dict) else {},
        dashboard_view_dto=dashboard_view_dto if isinstance(dashboard_view_dto, dict) else {},
        methods_export_dto=methods_export_dto if isinstance(methods_export_dto, dict) else {},
        methods_view_dto=methods_export_dto if isinstance(methods_export_dto, dict) else {},
        llm_inventory_record=llm_inventory_record if isinstance(llm_inventory_record, dict) else {},
        vm_payload=vm_payload,
        diagnostics=diagnostics,
    )


def _normalized_light_source_payload(light_source: dict[str, Any], get_val: Any) -> dict[str, Any]:
    return {
        "id": get_val(light_source, "id"),
        "kind": get_val(light_source, "kind", "type"),
        "manufacturer": get_val(light_source, "manufacturer"),
        "model": get_val(light_source, "model"),
        "product_code": get_val(light_source, "product_code"),
        "technology": get_val(light_source, "technology"),
        "wavelength_nm": get_val(light_source, "wavelength_nm", "wavelength"),
        "width_nm": get_val(light_source, "width_nm", "bandwidth_nm"),
        "tunable_min_nm": get_val(light_source, "tunable_min_nm"),
        "tunable_max_nm": get_val(light_source, "tunable_max_nm"),
        "simultaneous_lines_max": get_val(light_source, "simultaneous_lines_max"),
        "power": get_val(light_source, "power"),
        "path": get_val(light_source, "path"),
        "role": get_val(light_source, "role"),
        "timing_mode": get_val(light_source, "timing_mode"),
        "pulse_width_ps": get_val(light_source, "pulse_width_ps"),
        "repetition_rate_mhz": get_val(light_source, "repetition_rate_mhz"),
        "depletion_targets_nm": get_val(light_source, "depletion_targets_nm"),
        "notes": get_val(light_source, "notes"),
        "url": get_val(light_source, "url"),
    }


def _normalized_detector_payload(detector: dict[str, Any], get_val: Any) -> dict[str, Any]:
    return {
        "id": get_val(detector, "id"),
        "kind": get_val(detector, "kind", "type"),
        "manufacturer": get_val(detector, "manufacturer"),
        "model": get_val(detector, "model"),
        "product_code": get_val(detector, "product_code"),
        "channel_name": get_val(detector, "channel_name", "channel", "name"),
        "path": get_val(detector, "path"),
        "pixel_pitch_um": get_val(detector, "pixel_pitch_um", "pixel_size_um"),
        "sensor_format_px": get_val(detector, "sensor_format_px"),
        "binning": get_val(detector, "binning"),
        "bit_depth": get_val(detector, "bit_depth"),
        "qe_peak_pct": get_val(detector, "qe_peak_pct"),
        "read_noise_e": get_val(detector, "read_noise_e"),
        "supports_time_gating": get_val(detector, "supports_time_gating"),
        "default_gating_delay_ns": get_val(detector, "default_gating_delay_ns"),
        "default_gate_width_ns": get_val(detector, "default_gate_width_ns"),
        "collection_min_nm": get_val(detector, "collection_min_nm", "min_nm"),
        "collection_max_nm": get_val(detector, "collection_max_nm", "max_nm"),
        "collection_center_nm": get_val(detector, "collection_center_nm", "channel_center_nm"),
        "collection_width_nm": get_val(detector, "collection_width_nm", "bandwidth_nm"),
        "channel_center_nm": get_val(detector, "channel_center_nm"),
        "bandwidth_nm": get_val(detector, "bandwidth_nm"),
        "min_nm": get_val(detector, "min_nm"),
        "max_nm": get_val(detector, "max_nm"),
        "notes": get_val(detector, "notes"),
        "url": get_val(detector, "url"),
    }


def clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    # Remove common double-decoding artifacts (UTF-8 NBSP rendered as "Â ")
    s = value.replace("\u00c2\u00a0", " ").replace("\u00a0", " ")
    s = s.replace("Â\u00a0", " ").replace("Â ", " ")
    return s.strip()


INSTRUMENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_valid_instrument_id(value: str) -> bool:
    return bool(INSTRUMENT_ID_PATTERN.fullmatch(value))


def strip_empty_values(data: Any) -> Any:
    """Recursively remove empty optional values while preserving False/0."""

    def is_empty(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value == ""
        if isinstance(value, list):
            return len(value) == 0
        if isinstance(value, dict):
            return len(value) == 0
        return False

    if isinstance(data, dict):
        pruned: dict[str, Any] = {}
        for key, value in data.items():
            cleaned = strip_empty_values(value)
            if not is_empty(cleaned):
                pruned[key] = cleaned
        return pruned

    if isinstance(data, list):
        pruned_list = []
        for item in data:
            cleaned = strip_empty_values(item)
            if not is_empty(cleaned):
                pruned_list.append(cleaned)
        return pruned_list

    return data


def normalize_software(raw: Any) -> list[dict[str, str]]:
    """Normalize software metadata to schema-native `software[]` role rows."""
    allowed_roles = {"acquisition", "processing", "analysis", "hardware_control", "other"}
    legacy_role_map = {
        "acquisition": "acquisition",
        "analysis": "analysis",
        "deconvolution": "processing",
        "reconstruction": "processing",
        "post_processing": "processing",
        "flim": "analysis",
        "control": "hardware_control",
        "hardware_control": "hardware_control",
    }

    def normalize_role(value: Any, fallback: str = "other") -> str:
        role = clean_text(value).lower()
        if role in allowed_roles:
            return role
        if role in legacy_role_map:
            return legacy_role_map[role]
        return fallback

    rows: list[dict[str, str]] = []

    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "role": normalize_role(item.get("role") or item.get("component") or item.get("type")),
                    "name": clean_text(item.get("name") or ""),
                    "version": clean_text(item.get("version") or ""),
                    "developer": clean_text(item.get("developer") or item.get("manufacturer") or ""),
                    "notes": clean_text(item.get("notes") or ""),
                    "url": clean_text(item.get("url") or ""),
                }
            )
        cleaned_rows = [strip_empty_values(r) for r in rows]
    if isinstance(raw, dict):
        for role_or_name, payload in raw.items():
            normalized_role = normalize_role(role_or_name)
            if isinstance(payload, dict):
                rows.append(
                    {
                        "role": normalized_role,
                        "name": clean_text(payload.get("name") or ""),
                        "version": clean_text(payload.get("version") or ""),
                        "developer": clean_text(payload.get("developer") or payload.get("manufacturer") or ""),
                        "notes": clean_text(payload.get("notes") or ""),
                        "url": clean_text(payload.get("url") or ""),
                    }
                )
            elif isinstance(payload, str):
                rows.append({"role": normalized_role, "name": clean_text(payload), "version": "", "developer": "", "notes": "", "url": ""})
        cleaned_rows = [strip_empty_values(r) for r in rows]
        return [r for r in cleaned_rows if isinstance(r, dict) and r]

    if isinstance(raw, str) and raw.strip():
        cleaned_row = strip_empty_values({"role": "other", "name": clean_text(raw), "version": "", "developer": "", "notes": "", "url": ""})
        return [cleaned_row] if isinstance(cleaned_row, dict) and cleaned_row else []

    return []


def normalize_software_status(raw: Any) -> str:
    value = clean_text(raw).lower()
    if value in {"documented", "not_applicable", "unknown"}:
        return value
    return ""


def normalize_hardware(raw: Any) -> dict[str, Any]:
    """Normalize hardware into schema-native canonical keys and strip empty values."""
    if not isinstance(raw, dict):
        return {}

    def get_val(data: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in data:
                return data.get(key)
        return None

    hw: dict[str, Any] = {}

    scanner = raw.get("scanner")
    if isinstance(scanner, dict):
        hw["scanner"] = {
            "type": get_val(scanner, "type", "id"),
            "name": get_val(scanner, "name"),
            "manufacturer": get_val(scanner, "manufacturer"),
            "model": get_val(scanner, "model"),
            "product_code": get_val(scanner, "product_code"),
            "line_rate_hz": get_val(scanner, "line_rate_hz"),
            "pinhole_um": get_val(scanner, "pinhole_um"),
            "light_sheet_type": get_val(scanner, "light_sheet_type"),
            "notes": get_val(scanner, "notes"),
            "url": get_val(scanner, "url"),
        }

    sources_raw = raw.get("sources") or raw.get("light_sources")
    if isinstance(sources_raw, list):
        normalized_sources = [
            _normalized_light_source_payload(light_source, get_val)
            for light_source in sources_raw
            if isinstance(light_source, dict)
        ]
        hw["sources"] = normalized_sources
        hw["light_sources"] = normalized_sources

    optical_path_elements_raw = raw.get("optical_path_elements")
    if isinstance(optical_path_elements_raw, list):
        hw["optical_path_elements"] = [copy.deepcopy(element) for element in optical_path_elements_raw if isinstance(element, dict)]

    detectors_raw = raw.get("detectors")
    if isinstance(detectors_raw, list):
        hw["detectors"] = [
            _normalized_detector_payload(detector, get_val)
            for detector in detectors_raw
            if isinstance(detector, dict)
        ]

    eyepieces_raw = raw.get("eyepieces")
    if isinstance(eyepieces_raw, list):
        hw["eyepieces"] = [copy.deepcopy(eyepiece) for eyepiece in eyepieces_raw if isinstance(eyepiece, dict)]

    endpoint_rows = raw.get("endpoints") or raw.get("terminals") or raw.get("detection_endpoints")
    if isinstance(endpoint_rows, list):
        hw["endpoints"] = [copy.deepcopy(endpoint) for endpoint in endpoint_rows if isinstance(endpoint, dict)]

    objectives_raw = raw.get("objectives")
    if isinstance(objectives_raw, list):
        hw["objectives"] = [
            {
                "id": get_val(objective, "id"),
                "manufacturer": get_val(objective, "manufacturer"),
                "model": get_val(objective, "model", "name"),
                "product_code": get_val(objective, "product_code"),
                "magnification": get_val(objective, "magnification"),
                "numerical_aperture": get_val(objective, "numerical_aperture", "na"),
                "working_distance": get_val(objective, "working_distance", "wd"),
                "immersion": get_val(objective, "immersion"),
                "correction": get_val(objective, "correction", "correction_class"),
                "afc_compatible": get_val(objective, "afc_compatible", "afc"),
                "is_installed": get_val(objective, "is_installed"),
                "specialties": get_val(objective, "specialties"),
                "notes": get_val(objective, "notes"),
                "url": get_val(objective, "url"),
            }
            for objective in objectives_raw
            if isinstance(objective, dict)
        ]

    passthrough_keys = [
        "magnification_changers",
        "environment",
        "stages",
        "hardware_autofocus",
        "triggering",
        "optical_modulators",
        "illumination_logic",
    ]
    for key in passthrough_keys:
        if key in raw:
            hw[key] = raw.get(key)

    cleaned = strip_empty_values(hw)
    return cleaned if isinstance(cleaned, dict) else {}




def _derive_capabilities_from_legacy_modalities(modalities: list[str]) -> dict[str, list[str]]:
    imaging = {'confocal_point','confocal_spinning_disk','widefield_fluorescence','tirf','multiphoton','light_sheet','sim','sted','resolft','smlm','ism'}
    contrast = {'transmitted_brightfield','reflected_brightfield','phase_contrast','dic','darkfield','polarized_light','optical_sectioning'}
    readouts = {'spectral_imaging','flim','fcs','fret'}
    workflows = {'live_cell_imaging'}
    assay = {'frap','photoactivation'}
    non_opt = {'afm','impedance_cytometry'}
    out={'imaging_modes':[], 'contrast_methods':[], 'readouts':[], 'workflows':[], 'assay_operations':[], 'non_optical':[]}
    for m in modalities:
        if m in imaging: out['imaging_modes'].append(m)
        elif m in contrast: out['contrast_methods'].append(m)
        elif m in readouts: out['readouts'].append(m)
        elif m in workflows: out['workflows'].append(m)
        elif m in assay: out['assay_operations'].append(m)
        elif m in non_opt: out['non_optical'].append(m)
    return out


def _normalize_light_paths(light_paths_raw: Any) -> list[dict[str, Any]]:
    routes=[]
    if not isinstance(light_paths_raw,list):
        return routes
    for lp in light_paths_raw:
        if not isinstance(lp,dict):
            continue
        route_id=clean_text(lp.get('id'))
        route_type=clean_text(lp.get('route_type')) or route_id
        readouts=[clean_text(v) for v in (lp.get('readouts') or []) if isinstance(v,str) and clean_text(v)]
        route=copy.deepcopy(lp)
        route['id']=route_id
        route['route_type']=route_type
        route['readouts']=readouts
        routes.append(route)
    return routes
def normalize_instrument_dto(payload: dict[str, Any], source_file: Path, *, retired: bool) -> dict[str, Any] | None:
    """Build canonical instrument DTO used by dashboard templates and exports."""
    inst_section = payload.get("instrument")
    if not isinstance(inst_section, dict):
        inst_section = {}

    display_name = clean_text(inst_section.get("display_name")) or source_file.stem
    raw_instrument_id = inst_section.get("instrument_id")
    if not isinstance(raw_instrument_id, str) or not raw_instrument_id.strip():
        return None

    instrument_id = raw_instrument_id.strip()
    if not is_valid_instrument_id(instrument_id):
        return None

    notes_raw = clean_text(inst_section.get("notes"))

    raw_modules = payload.get("modules") or []
    modules = []
    for m in raw_modules:
        if isinstance(m, dict):
            modules.append(
                {
                    "type": clean_text(m.get("type") or m.get("name")),
                    "name": clean_text(m.get("name")),
                    "manufacturer": clean_text(m.get("manufacturer")),
                    "model": clean_text(m.get("model")),
                    "product_code": clean_text(m.get("product_code")),
                    "notes": clean_text(m.get("notes")),
                    "url": clean_text(m.get("url")),
                }
            )
        elif isinstance(m, str):
            modules.append({"type": clean_text(m), "name": "", "manufacturer": "", "model": "", "notes": "", "url": ""})

    modalities = payload.get("modalities")
    if not isinstance(modalities, list):
        modalities = []
    modalities = [clean_text(m) for m in modalities if isinstance(m, str) and clean_text(m)]

    capabilities_raw = payload.get("capabilities") if isinstance(payload.get("capabilities"), dict) else {}
    capabilities = {
        "imaging_modes": [clean_text(v) for v in (capabilities_raw.get("imaging_modes") or []) if isinstance(v, str) and clean_text(v)],
        "contrast_methods": [clean_text(v) for v in (capabilities_raw.get("contrast_methods") or []) if isinstance(v, str) and clean_text(v)],
        "readouts": [clean_text(v) for v in (capabilities_raw.get("readouts") or []) if isinstance(v, str) and clean_text(v)],
        "workflows": [clean_text(v) for v in (capabilities_raw.get("workflows") or []) if isinstance(v, str) and clean_text(v)],
        "assay_operations": [clean_text(v) for v in (capabilities_raw.get("assay_operations") or []) if isinstance(v, str) and clean_text(v)],
        "non_optical": [clean_text(v) for v in (capabilities_raw.get("non_optical") or []) if isinstance(v, str) and clean_text(v)],
    }
    if not any(capabilities.values()):
        import warnings as _warnings_mod
        _warnings_mod.warn(
            f"Instrument '{source_file.stem}': no canonical capabilities object found; "
            "deriving capabilities from legacy modalities. "
            "Add explicit capabilities.* axes to the instrument YAML to avoid this fallback.",
            UserWarning,
            stacklevel=2,
        )
        capabilities = _derive_capabilities_from_legacy_modalities(modalities)


    software = strip_empty_values(normalize_software(payload.get("software")))
    software_status = normalize_software_status(payload.get("software_status"))
    raw_hardware = payload.get("hardware") or {}
    if not isinstance(raw_hardware, dict):
        raw_hardware = {}

    legacy_top_level_objectives_used = False
    # DEPRECATED compatibility path: some legacy YAML files declared objectives at top level.
    # Canonical contract location is hardware.objectives; production YAML should migrate.
    if "objectives" not in raw_hardware and isinstance(payload.get("objectives"), list):
        raw_hardware = {**raw_hardware, "objectives": payload.get("objectives")}
        legacy_top_level_objectives_used = True

    hardware = strip_empty_values(normalize_hardware(raw_hardware))
    policy = build_instrument_completeness_report(payload)

    software_roles = ("acquisition", "processing", "analysis", "hardware_control", "other")

    software_by_role: dict[str, dict[str, Any]] = {}
    for role in software_roles:
        role_payload = next(
            (
                sw
                for sw in software
                if isinstance(sw, dict) and clean_text(sw.get("role")).lower() == role
            ),
            {},
        )
        role_name = clean_text(role_payload.get("name"))
        role_version = clean_text(role_payload.get("version"))
        software_by_role[role] = {
            "present": bool(role_payload),
            "name": role_name,
            "version": role_version,
            "is_complete": bool(role_name and role_version),
        }

    missing_entries = [*policy.missing_required, *policy.missing_conditional]
    methods_blockers: list[dict[str, str]] = []
    for entry in missing_entries:
        used_by = entry.get("used_by") if isinstance(entry, dict) else None
        if not isinstance(used_by, list) or "method_generator" not in used_by:
            continue

        path = clean_text(entry.get("path"))
        if not path:
            continue

        role = ""
        if path.startswith("software[") and isinstance(entry, dict):
            role = clean_text(entry.get("role"))

        methods_blockers.append(
            {
                "path": path,
                "title": clean_text(entry.get("title")) or path,
                "role": role,
                "kind": "instrument_metadata",
            }
        )

    methods_generation = {
        "is_blocked": bool(methods_blockers),
        "blockers": methods_blockers,
        "software_by_role": software_by_role,
    }

    canonical = {
        "instrument": {
            "display_name": display_name,
            "instrument_id": instrument_id,
            "manufacturer": clean_text(inst_section.get("manufacturer")),
            "model": clean_text(inst_section.get("model")),
            "year_of_purchase": clean_text(inst_section.get("year_of_purchase")),
            "funding": clean_text(inst_section.get("funding")),
            "stand_orientation": clean_text(inst_section.get("stand_orientation")),
            "ocular_availability": clean_text(inst_section.get("ocular_availability")),
            "location": clean_text(inst_section.get("location")),
            "notes": notes_raw,
            "url": clean_text(inst_section.get("url")),
        },
        "modalities": copy.deepcopy(modalities),
        "capabilities": copy.deepcopy(capabilities),
        "modules": copy.deepcopy(modules),
        "notes": notes_raw,
        "software": software,
        "software_status": software_status,
        "hardware": hardware,
        "light_paths": _normalize_light_paths(payload.get("light_paths") or []),
        "policy": {
            "sections": policy.sections,
            "missing_required": policy.missing_required,
            "missing_conditional": policy.missing_conditional,
            "alias_fallbacks": policy.alias_fallbacks,
        },
        "provenance": {
            "source_contract": "validated_canonical_yaml",
            "deprecated_compatibility": {
                "top_level_objectives_to_hardware_objectives": legacy_top_level_objectives_used,
            },
        },
    }

    canonical_instrument = canonical["instrument"]
    return {
        "retired": retired,
        "id": instrument_id,
        "display_name": canonical_instrument["display_name"],
        "manufacturer": canonical_instrument["manufacturer"],
        "model": canonical_instrument["model"],
        "year_of_purchase": canonical_instrument["year_of_purchase"],
        "funding": canonical_instrument["funding"],
        "stand_orientation": canonical_instrument["stand_orientation"],
        "ocular_availability": canonical_instrument["ocular_availability"],
        "location": canonical_instrument["location"],
        "notes_raw": notes_raw,
        "notes": notes_raw,
        "modalities": copy.deepcopy(canonical["modalities"]),
        "capabilities": copy.deepcopy(canonical.get("capabilities") or {}),
        "modules": copy.deepcopy(canonical["modules"]),
        "software": copy.deepcopy(canonical["software"]),
        "software_status": canonical.get("software_status", ""),
        "image_filename": _discover_image_filename(instrument_id),
        "url": canonical_instrument["url"],
        "canonical": canonical,
        "methods_generation": methods_generation,
    }


def _discover_image_filename(instrument_id: str) -> str:
    # prefer local jpg/png assets if present
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".svg"):
        candidate = Path("assets/images") / f"{instrument_id}{ext}"
        if candidate.exists():
            return candidate.name
    return "placeholder.svg"

discover_image_filename = _discover_image_filename
