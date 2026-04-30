"""VM export adapter boundary.

Production VM payload must be a deep copy of canonical light-path DTO from
build context. Dashboard view DTO optical-path data is non-authoritative and
must never be used as VM export source-of-truth.
"""

import copy

from scripts.build_context import build_instrument_context


def build_vm_payload_from_context(inst: dict, *, vocabulary, build_dashboard_view_dto, build_methods_view_dto, build_llm_inventory_record) -> dict:
    context = build_instrument_context(
        inst,
        vocabulary=vocabulary,
        build_dashboard_view_dto=build_dashboard_view_dto,
        build_methods_view_dto=build_methods_view_dto,
        build_llm_inventory_record=build_llm_inventory_record,
    )
    return copy.deepcopy(context.vm_payload if isinstance(context.vm_payload, dict) else {})


__all__ = ["build_vm_payload_from_context"]
