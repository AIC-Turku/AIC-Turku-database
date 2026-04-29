"""Dashboard package.

This package separates dashboard production concerns:
- canonical/build orchestration (shared build context)
- derived dashboard view DTOs
- downstream export adapters (LLM, methods, VM)
"""

from .loaders import load_instruments, validated_instrument_selection
from .instrument_view import build_instrument_mega_dto, build_hardware_dto
from .optical_path_view import build_optical_path_view_dto, build_optical_path_dto
from .llm_export import build_llm_inventory_payload
from .methods_export import build_methods_generator_instrument_export

__all__ = [
    "load_instruments",
    "validated_instrument_selection",
    "build_instrument_mega_dto",
    "build_hardware_dto",
    "build_optical_path_view_dto",
    "build_optical_path_dto",
    "build_llm_inventory_payload",
    "build_methods_generator_instrument_export",
]
