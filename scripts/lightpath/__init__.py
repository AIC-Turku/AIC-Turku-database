"""Light-path package split points.

This package provides stable module boundaries for canonical parsing, legacy
import, validation, route graph execution payload construction, and VM payload
assembly while preserving existing public API behavior.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "parse_canonical_light_path_model": ("scripts.lightpath.parse_canonical", "parse_canonical_light_path_model"),
    "canonicalize_light_path_model": ("scripts.lightpath.parse_canonical", "canonicalize_light_path_model"),
    "canonicalize_light_path_model_strict": ("scripts.lightpath.parse_canonical", "canonicalize_light_path_model_strict"),
    "parse_strict_canonical_light_path_model": ("scripts.lightpath.parse_canonical", "parse_strict_canonical_light_path_model"),
    "has_legacy_light_path_input": ("scripts.lightpath.legacy_import", "has_legacy_light_path_input"),
    "import_legacy_light_path_model": ("scripts.lightpath.legacy_import", "import_legacy_light_path_model"),
    "migrate_instrument_to_light_path_v2": ("scripts.lightpath.legacy_import", "migrate_instrument_to_light_path_v2"),
    "validate_light_path": ("scripts.lightpath.validate_contract", "validate_light_path"),
    "validate_light_path_warnings": ("scripts.lightpath.validate_contract", "validate_light_path_warnings"),
    "validate_filter_cube_warnings": ("scripts.lightpath.validate_contract", "validate_filter_cube_warnings"),
    "validate_light_path_diagnostics": ("scripts.lightpath.validate_contract", "validate_light_path_diagnostics"),
    "generate_virtual_microscope_payload": ("scripts.lightpath.vm_payload", "generate_virtual_microscope_payload"),
    "calculate_valid_paths": ("scripts.lightpath.route_graph", "calculate_valid_paths"),
    "infer_light_source_role": ("scripts.lightpath.spectral_ops", "infer_light_source_role"),
    "set_active_vocab": ("scripts.lightpath.model", "set_active_vocab"),
    "get_active_vocab": ("scripts.lightpath.model", "get_active_vocab"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted([*globals(), *_EXPORTS])
