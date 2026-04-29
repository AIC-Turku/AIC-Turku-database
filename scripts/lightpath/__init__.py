"""Light-path package split points.

This package provides stable module boundaries for canonical parsing, legacy
import, validation, route graph execution payload construction, and VM payload
assembly while preserving existing public API behavior.
"""

from .parse_canonical import parse_canonical_light_path_model, canonicalize_light_path_model_strict
from .legacy_import import import_legacy_light_path_model, migrate_instrument_to_light_path_v2, has_legacy_light_path_input
from .validate_contract import validate_light_path, validate_light_path_warnings, validate_filter_cube_warnings, validate_light_path_diagnostics
from .vm_payload import generate_virtual_microscope_payload
from .model import canonicalize_light_path_model

__all__ = [
    "parse_canonical_light_path_model",
    "canonicalize_light_path_model_strict",
    "import_legacy_light_path_model",
    "migrate_instrument_to_light_path_v2",
    "has_legacy_light_path_input",
    "validate_light_path",
    "validate_light_path_warnings",
    "validate_filter_cube_warnings",
    "validate_light_path_diagnostics",
    "generate_virtual_microscope_payload",
    "canonicalize_light_path_model",
]
