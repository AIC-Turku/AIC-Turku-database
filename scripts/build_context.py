"""Central per-instrument build context for canonical and derived DTO flows.

Downstream exporters/views must consume canonical and/or derived DTO data from this
context. Production consumers should not re-read or reinterpret raw YAML when the
needed information already exists in canonical DTO fields.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from scripts.light_path_parser import generate_virtual_microscope_payload, canonicalize_light_path_model_strict


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
    methods_export_dto = build_methods_view_dto(build_input)
    llm_inventory_record = build_llm_inventory_record(build_input)

    # VM payload must consume the canonical parser DTO directly. Dashboard view DTOs
    # are display-only and must not be used as VM authority.
    vm_payload = _build_vm_payload_from_canonical_lightpath(canonical_lightpath_dto, diagnostics)
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
