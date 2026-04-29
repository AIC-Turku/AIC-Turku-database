"""Explicit legacy compatibility and migration APIs.

Use only for migration/audit compatibility paths, not strict production DTO flow.
"""
from scripts.light_path_parser import import_legacy_light_path_model, migrate_instrument_to_light_path_v2, has_legacy_light_path_input
__all__ = ["import_legacy_light_path_model", "migrate_instrument_to_light_path_v2", "has_legacy_light_path_input"]
