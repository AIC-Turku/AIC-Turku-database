"""Dashboard package.

This package separates dashboard production concerns:
- canonical/build orchestration via scripts.build_context
- repository/YAML loading via scripts.dashboard.loaders
- derived dashboard view DTOs via scripts.dashboard.instrument_view
- optical-path view DTOs via scripts.dashboard.optical_path_view
- downstream export adapters via scripts.dashboard.llm_export, methods_export, and vm_export

The package-level exports are intentionally lazy to avoid circular imports during
the dashboard_builder compatibility phase.
"""

from __future__ import annotations

from typing import Any


_EXPORTS: dict[str, tuple[str, str]] = {
    # loaders
    "load_instruments": ("scripts.dashboard.loaders", "load_instruments"),
    "validated_instrument_selection": (
        "scripts.dashboard.loaders",
        "validated_instrument_selection",
    ),

    # dashboard/instrument view
    "build_instrument_mega_dto": (
        "scripts.dashboard.instrument_view",
        "build_instrument_mega_dto",
    ),
    "build_dashboard_instrument_view": (
        "scripts.dashboard.instrument_view",
        "build_dashboard_instrument_view",
    ),
    "build_hardware_dto": (
        "scripts.dashboard.instrument_view",
        "build_hardware_dto",
    ),

    # optical-path view
    "build_optical_path_view_dto": (
        "scripts.dashboard.optical_path_view",
        "build_optical_path_view_dto",
    ),
    "build_optical_path_dto": (
        "scripts.dashboard.optical_path_view",
        "build_optical_path_dto",
    ),

    # LLM export
    "build_llm_inventory_payload": (
        "scripts.dashboard.llm_export",
        "build_llm_inventory_payload",
    ),

    # methods export
    "build_methods_generator_instrument_export": (
        "scripts.dashboard.methods_export",
        "build_methods_generator_instrument_export",
    ),

    # VM export
    "build_vm_payload": (
        "scripts.dashboard.vm_export",
        "build_vm_payload",
    ),
    "build_vm_payloads": (
        "scripts.dashboard.vm_export",
        "build_vm_payloads",
    ),
    "build_virtual_microscope_payload": (
        "scripts.dashboard.vm_export",
        "build_virtual_microscope_payload",
    ),
    "build_virtual_microscope_payloads": (
        "scripts.dashboard.vm_export",
        "build_virtual_microscope_payloads",
    ),

    # site rendering
    "render_site": (
        "scripts.dashboard.site_render",
        "render_site",
    ),
}


__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Lazily resolve package-level compatibility exports."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]

    from importlib import import_module

    module = import_module(module_name)
    value = getattr(module, attr_name)

    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted([*globals(), *_EXPORTS])
