"""Compatibility shim for legacy light-path parser imports.

All active implementations now live under ``scripts.lightpath.*`` modules.
This module intentionally re-exports compatibility symbols only.
"""

from scripts.lightpath.legacy_import import (
    has_legacy_light_path_input,
    import_legacy_light_path_model,
    migrate_instrument_to_light_path_v2,
)
from scripts.lightpath.parse_canonical import (
    canonicalize_light_path_model,
    canonicalize_light_path_model_strict,
    parse_canonical_light_path_model,
    parse_strict_canonical_light_path_model,
)
from scripts.lightpath.route_graph import calculate_valid_paths
from scripts.lightpath.spectral_ops import infer_light_source_role
from scripts.lightpath.validate_contract import (
    validate_filter_cube_warnings,
    validate_light_path,
    validate_light_path_diagnostics,
    validate_light_path_warnings,
)
from scripts.lightpath.vm_payload import generate_virtual_microscope_payload

__all__ = [
    "generate_virtual_microscope_payload",
    "validate_light_path",
    "validate_light_path_warnings",
    "validate_filter_cube_warnings",
    "validate_light_path_diagnostics",
    "canonicalize_light_path_model",
    "canonicalize_light_path_model_strict",
    "parse_canonical_light_path_model",
    "parse_strict_canonical_light_path_model",
    "has_legacy_light_path_input",
    "import_legacy_light_path_model",
    "migrate_instrument_to_light_path_v2",
    "calculate_valid_paths",
    "infer_light_source_role",
]
