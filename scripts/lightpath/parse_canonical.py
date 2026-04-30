"""Strict canonical parsing boundary.

Production DTO generation should use strict canonical parsing and reject
legacy-only topology.
"""
from scripts.light_path_parser import (
    parse_canonical_light_path_model,
    canonicalize_light_path_model_strict,
    parse_strict_canonical_light_path_model,
)
__all__ = ["parse_canonical_light_path_model", "canonicalize_light_path_model_strict", "parse_strict_canonical_light_path_model"]
