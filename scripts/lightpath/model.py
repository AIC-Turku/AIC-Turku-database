"""Shared light-path parser model constants and low-level helpers.

This module contains only:
- parser-wide constants
- vocabulary display-label context helpers
- primitive string/number/list normalization helpers
- simple route/modality helpers

It must not import scripts.light_path_parser.
It must not contain canonical parsing, legacy import, route graph building,
selected execution, validation, spectral operations, or VM payload generation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.display_labels import (
    VocabLookup,
    resolve_component_type_label,
    resolve_light_source_kind_label,
    resolve_route_label,
)


DICHROIC_TYPES = {"dichroic", "multiband_dichroic", "polychroic"}
NO_WAVELENGTH_TYPES = {
    "empty",
    "mirror",
    "block",
    "passthrough",
    "neutral_density",
}
CUBE_FILTER_COMPONENT_TYPES = {
    "bandpass",
    "multiband_bandpass",
    "longpass",
    "shortpass",
    "notch",
    "tunable",
}
CUBE_LINK_KEYS = (
    "excitation_filter",
    "dichroic",
    "emission_filter",
)
POWER_VALUE_RE = re.compile(r"(\d+(?:\.\d+)?)")
CANONICAL_ENDPOINT_COLLECTION_KEYS = (
    "endpoints",
    "terminals",
    "detection_endpoints",
)
ENDPOINT_CAPABLE_INVENTORY_KEYS = (
    "detectors",
    "eyepieces",
)
SEQUENCE_TOPOLOGY_KEYS = (
    "source_id",
    "optical_path_element_id",
    "endpoint_id",
    "branches",
)

# Module-level vocabulary context set by generate_virtual_microscope_payload()
# or equivalent orchestration so deeply nested helpers can resolve vocab-backed
# display labels without requiring every internal function to accept a vocab parameter.
_active_vocab: VocabLookup | None = None


def set_active_vocab(vocab: VocabLookup | None) -> None:
    """Set module-level vocabulary context for label resolution.

    This preserves the monolith behavior where nested helpers can resolve labels
    through a shared active vocabulary context.
    """
    global _active_vocab
    _active_vocab = vocab


def get_active_vocab() -> VocabLookup | None:
    """Return the active vocabulary context."""
    return _active_vocab


def _resolve_route_label(route_id: str, explicit_name: str | None = None) -> str:
    """Resolve a display label for a route id using explicit DTO name/vocab/ID."""
    if explicit_name:
        return explicit_name
    if _active_vocab is not None:
        return resolve_route_label(route_id, _active_vocab)
    return route_id


def _resolve_component_type_label(component_type: str) -> str:
    """Resolve a display label for a component type via vocab or fallback."""
    if _active_vocab is not None:
        return resolve_component_type_label(component_type, _active_vocab)
    return component_type.replace("_", " ").title()


def _resolve_light_source_kind(kind: str) -> str:
    """Resolve a display label for a light source kind via vocab or fallback."""
    if _active_vocab is not None:
        return resolve_light_source_kind_label(kind, _active_vocab)
    return kind.replace("_", " ")


_CUBE_LINK_LABELS = {
    "excitation_filter": "Excitation Filter",
    "dichroic": "Dichroic",
    "emission_filter": "Emission Filter",
}


def _resolve_cube_link_label(link_key: str) -> str:
    """Resolve a display label for a filter cube link key."""
    return _CUBE_LINK_LABELS.get(link_key, link_key.replace("_", " ").title())


def _is_positive_number(value: Any) -> bool:
    """Return True for positive int/float values, excluding bool."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value > 0
    )


def _coerce_number(value: Any) -> float | None:
    """Coerce int/float/numeric-string values to float."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None

        try:
            return float(cleaned)
        except ValueError:
            return None

    return None


def _format_numeric(value: Any) -> str:
    """Format numeric values without trailing .0 when integral."""
    numeric = _coerce_number(value)
    if numeric is None:
        return str(value)

    return str(int(numeric)) if float(numeric).is_integer() else str(numeric)


def _clean_string(value: Any) -> str:
    """Normalize strings and safely stringify numeric values.

    YAML integer IDs should not be erased; numeric non-bool values are converted
    to strings before trimming.
    """
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = str(value)

    return value.strip() if isinstance(value, str) else ""


def _clean_identifier(value: Any) -> str:
    """Normalize arbitrary values into lowercase underscore identifiers."""
    cleaned = _clean_string(value).lower()
    if not cleaned:
        return ""

    return re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")


def _coerce_slot_key(value: Any) -> int | None:
    """Normalize mechanism/cube position keys from legacy YAML spellings.

    Existing ledgers use both integer keys and labels such as ``Pos_1``. The
    parser/runtime should preserve mechanical slot order rather than drop these
    positions during normalization.
    """
    if isinstance(value, int) and not isinstance(value, bool):
        return value

    if isinstance(value, float) and value.is_integer():
        return int(value)

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None

        if cleaned.isdigit():
            return int(cleaned)

        match = re.search(r"(\d+)$", cleaned)
        if match:
            return int(match.group(1))

    return None


def _normalize_modalities(value: Any) -> list[str]:
    """Normalize route/modality values into stable lowercase unique strings."""
    items = value if isinstance(value, list) else [value]
    modalities: list[str] = []

    for item in items:
        cleaned = _clean_string(item).lower()
        if cleaned and cleaned not in modalities:
            modalities.append(cleaned)

    return modalities


def _normalize_routes(value: Any) -> list[str]:
    """Normalize route/path values into stable lowercase unique strings."""
    candidates = value if isinstance(value, list) else [value]
    routes: list[str] = []

    for candidate in candidates:
        cleaned = _clean_string(candidate).lower()
        if cleaned and cleaned not in routes:
            routes.append(cleaned)

    return routes


def _routes_overlap(left: list[str], right: list[str]) -> bool:
    """Return True when two route/modality lists share at least one tag."""
    left_set = {tag for tag in left if isinstance(tag, str) and tag.strip()}
    right_set = {tag for tag in right if isinstance(tag, str) and tag.strip()}

    if not left_set or not right_set:
        return False

    return bool(left_set & right_set)


def _modality_match(modalities: list[str], route_id: str) -> bool:
    """Return True when a row with modalities is compatible with a route."""
    return not modalities or route_id in modalities


def _identifier_slug(*parts: Any, fallback: str = "item") -> str:
    """Build a stable underscore identifier from multiple parts."""
    joined = "_".join(
        _clean_identifier(part)
        for part in parts
        if _clean_identifier(part)
    )
    return joined or fallback


def _as_list(value: Any) -> list[Any]:
    """Return value as a list, treating None and empty string as empty."""
    if isinstance(value, list):
        return value

    if value in (None, ""):
        return []

    return [value]


def _copy_mapping(value: Any) -> dict[str, Any]:
    """Return a shallow dict copy when value is a mapping-like dict."""
    return dict(value) if isinstance(value, dict) else {}


def _normalize_power_weight(raw_power: Any) -> float | None:
    """Extract a numeric power weight from a number or string like '10 mW'."""
    if isinstance(raw_power, (int, float)) and not isinstance(raw_power, bool):
        return float(raw_power)

    if not isinstance(raw_power, str):
        return None

    match = POWER_VALUE_RE.search(raw_power)
    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None


_fallback_vocab: Any | None = None


def _vocab_context() -> VocabLookup | Any | None:
    global _fallback_vocab
    if _active_vocab is not None:
        return _active_vocab
    if _fallback_vocab is None:
        # Lazy import avoids validation -> lightpath -> validation import cycles.
        from scripts.validation.vocabulary import build_repository_vocabulary
        _fallback_vocab = build_repository_vocabulary(Path(__file__).resolve().parents[2])
    return _fallback_vocab


def _normalize_light_source_kind(value: Any) -> str:
    raw = _clean_string(value)
    token = _clean_identifier(raw) or "light_source"
    vocabulary = _vocab_context()
    resolver = getattr(vocabulary, "resolve_canonical", None)
    if callable(resolver):
        return resolver("light_source_kinds", raw) or resolver("light_source_kinds", token) or token
    return token


def _detector_class(kind: str) -> str:
    vocabulary = _vocab_context()
    resolver = getattr(vocabulary, "resolve_canonical", None)
    get_term = getattr(vocabulary, "get_term", None)
    canonical = resolver("detector_kinds", kind) if callable(resolver) else None
    canonical = canonical or _clean_identifier(kind)
    term = get_term("detector_kinds", canonical) if callable(get_term) else None
    if term is not None:
        frontend_class = term.tag_value("frontend_class")
        if isinstance(frontend_class, str) and frontend_class.strip():
            return frontend_class.strip()
    return "detector"


def _normalize_endpoint_type(value: Any) -> str:
    raw = _clean_string(value)
    token = _clean_identifier(raw)
    if not raw and not token:
        return "detector"
    vocabulary = _vocab_context()
    resolver = getattr(vocabulary, "resolve_canonical", None)
    if callable(resolver):
        endpoint_type = resolver("endpoint_types", raw) or resolver("endpoint_types", token)
        if endpoint_type:
            return endpoint_type
        if resolver("detector_kinds", raw) or resolver("detector_kinds", token):
            return "detector"
    return token or "detector"


__all__ = [
    # Constants
    "DICHROIC_TYPES",
    "NO_WAVELENGTH_TYPES",
    "CUBE_FILTER_COMPONENT_TYPES",
    "CUBE_LINK_KEYS",
    "POWER_VALUE_RE",
    "CANONICAL_ENDPOINT_COLLECTION_KEYS",
    "ENDPOINT_CAPABLE_INVENTORY_KEYS",
    "SEQUENCE_TOPOLOGY_KEYS",

    # Vocab context
    "set_active_vocab",
    "get_active_vocab",

    # Label helpers
    "_resolve_route_label",
    "_resolve_component_type_label",
    "_resolve_light_source_kind",
    "_resolve_cube_link_label",

    # Primitive helpers
    "_is_positive_number",
    "_coerce_number",
    "_format_numeric",
    "_clean_string",
    "_clean_identifier",
    "_coerce_slot_key",
    "_normalize_modalities",
    "_normalize_routes",
    "_routes_overlap",
    "_modality_match",
    "_identifier_slug",
    "_as_list",
    "_copy_mapping",
    "_normalize_power_weight",
    "_normalize_light_source_kind",
    "_detector_class",
    "_normalize_endpoint_type",
]
