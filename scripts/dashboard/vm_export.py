"""Virtual microscope dashboard export.

This module owns the virtual-microscope derived export projection.

Authoritative production dataflow:

    YAML
    -> strict validation
    -> canonical build context / canonical DTOs
    -> derived exports:
       dashboard_view
       llm_inventory
       methods_export
       vm_payload

This module must not import scripts.dashboard_builder.

Important:
- The authoritative VM payload is produced by build_context as context.vm_payload.
- This module only normalizes/aggregates those payloads for the frontend.
- display_name is UI metadata only; it must not be treated as route truth.
"""

from __future__ import annotations

import copy
from typing import Any

from scripts.build_context import clean_text


def _context_vm_payload(inst: dict[str, Any]) -> dict[str, Any]:
    """Return context.vm_payload when an instrument already has a build context."""
    context = inst.get("build_context")

    if context is None:
        return {}

    vm_payload = getattr(context, "vm_payload", None)
    if isinstance(vm_payload, dict):
        return copy.deepcopy(vm_payload)

    return {}


def _fallback_vm_payload(inst: dict[str, Any]) -> dict[str, Any]:
    """Best-effort fallback for callers that have not attached build_context.

    This is intentionally conservative. The normal production path should use
    context.vm_payload from scripts.build_context.build_instrument_context.
    """
    canonical_lightpath_dto = copy.deepcopy(
        inst.get("canonical_lightpath_dto")
        or inst.get("lightpath_dto")
        or {}
    )

    if not isinstance(canonical_lightpath_dto, dict):
        canonical_lightpath_dto = {}

    return canonical_lightpath_dto


def build_vm_payload(inst: dict[str, Any]) -> dict[str, Any]:
    """Build one virtual-microscope frontend payload for an instrument.

    The route/topology payload comes from build_context. This function only
    attaches stable frontend identity metadata.

    display_name is non-authoritative UI metadata.
    """
    vm_payload = _context_vm_payload(inst)

    if not vm_payload:
        vm_payload = _fallback_vm_payload(inst)

    dto = inst.get("dto") if isinstance(inst.get("dto"), dict) else {}
    canonical = (
        inst.get("canonical_instrument_dto")
        or inst.get("canonical")
        or {}
    )
    canonical_instrument = (
        canonical.get("instrument")
        if isinstance(canonical, dict) and isinstance(canonical.get("instrument"), dict)
        else {}
    )

    instrument_id = clean_text(
        inst.get("id")
        or canonical_instrument.get("instrument_id")
        or vm_payload.get("id")
        or vm_payload.get("instrument_id")
    )

    display_name = clean_text(
        dto.get("display_name")
        or inst.get("display_name")
        or canonical_instrument.get("display_name")
        or vm_payload.get("display_name")
    )

    if instrument_id:
        vm_payload.setdefault("id", instrument_id)
        vm_payload.setdefault("instrument_id", instrument_id)

    if display_name:
        # Non-authoritative frontend metadata only.
        vm_payload["display_name"] = display_name

    return vm_payload


def build_virtual_microscope_payload(inst: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible explicit alias for build_vm_payload."""
    return build_vm_payload(inst)


def build_vm_payloads(
    instruments: list[dict[str, Any]],
    *,
    include_retired: bool = False,
) -> dict[str, dict[str, Any]]:
    """Build the global virtual-microscope payload map keyed by instrument ID.

    By default retired instruments are excluded, matching the dashboard_builder
    behavior where only active instruments were added to global_vm_payloads.
    """
    payloads: dict[str, dict[str, Any]] = {}

    for inst in instruments:
        if not isinstance(inst, dict):
            continue

        if not include_retired and inst.get("retired"):
            continue

        payload = build_vm_payload(inst)

        instrument_id = clean_text(
            payload.get("instrument_id")
            or payload.get("id")
            or inst.get("id")
        )

        if not instrument_id:
            continue

        payloads[instrument_id] = payload

    return payloads


def build_virtual_microscope_payloads(
    instruments: list[dict[str, Any]],
    *,
    include_retired: bool = False,
) -> dict[str, dict[str, Any]]:
    """Backward-compatible explicit alias for build_vm_payloads."""
    return build_vm_payloads(instruments, include_retired=include_retired)


__all__ = [
    "build_vm_payload",
    "build_vm_payloads",
    "build_virtual_microscope_payload",
    "build_virtual_microscope_payloads",
]
