"""VM export adapter.

VM payload authority comes from canonical light-path DTO in build context.
"""

from scripts.build_context import build_instrument_context


def build_vm_payload_from_context(inst: dict, *, vocabulary, build_dashboard_view_dto, build_methods_view_dto, build_llm_inventory_record) -> dict:
    context = build_instrument_context(
        inst,
        vocabulary=vocabulary,
        build_dashboard_view_dto=build_dashboard_view_dto,
        build_methods_view_dto=build_methods_view_dto,
        build_llm_inventory_record=build_llm_inventory_record,
    )
    return context.vm_payload


__all__ = ["build_vm_payload_from_context"]
