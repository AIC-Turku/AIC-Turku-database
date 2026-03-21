"""Centralized display-label resolution for vocabulary-backed fields.

Every user-facing label in the project must be resolved through this module so
that raw/internal YAML values are never shown directly to users.  The resolver
checks:

1. An explicit ``display_label`` already provided by the source data / DTO.
2. A vocabulary translation if available.
3. The raw value plus a visible marker ``"(missing vocabulary translation)"``.

The module intentionally does **not** apply ad-hoc prettification such as
``str.title()`` or ``str.replace("_", " ")``.  If a vocabulary entry is
missing, the fallback makes that gap visible and auditable.
"""

from __future__ import annotations

from typing import Any, Protocol


class VocabLookup(Protocol):
    """Minimal interface expected from the ``Vocabulary`` class in *validate.py*."""

    terms_by_vocab: dict[str, dict[str, Any]]


# ---------------------------------------------------------------------------
# Core resolvers
# ---------------------------------------------------------------------------

_MISSING_MARKER = "(missing vocabulary translation)"


def resolve_display_label(
    raw_value: str | None,
    vocab_name: str | None = None,
    vocab: VocabLookup | None = None,
    *,
    explicit_label: str | None = None,
) -> str:
    """Return the best available display label for *raw_value*.

    Lookup order:
    1. *explicit_label* (already attached to the source data / DTO).
    2. Vocabulary translation via *vocab_name* / *vocab*.
    3. *raw_value* with the missing-translation marker.
    """
    if explicit_label:
        return explicit_label

    if raw_value and vocab_name and vocab is not None:
        term = vocab.terms_by_vocab.get(vocab_name, {}).get(raw_value)
        if term is not None:
            label = getattr(term, "label", None)
            if label:
                return label

    if raw_value:
        return f"{raw_value} {_MISSING_MARKER}"

    return ""


def resolve_vocab_label(
    vocab: VocabLookup | None,
    vocab_name: str,
    raw_value: str | None,
) -> str:
    """Shorthand: look up a single vocabulary term and return its label.

    Falls back to the raw value with the missing marker when the vocabulary
    does not contain the term.
    """
    if not raw_value:
        return ""
    return resolve_display_label(raw_value, vocab_name=vocab_name, vocab=vocab)


def resolve_route_label(
    route_id: str,
    vocab: VocabLookup | None = None,
    *,
    explicit_name: str | None = None,
) -> str:
    """Return a display label for a light-path route identifier."""
    return resolve_display_label(
        route_id,
        vocab_name="optical_routes",
        vocab=vocab,
        explicit_label=explicit_name,
    )


def resolve_component_type_label(
    component_type: str,
    vocab: VocabLookup | None = None,
) -> str:
    """Return a display label for an optical component type."""
    return resolve_display_label(
        component_type,
        vocab_name="optical_component_types",
        vocab=vocab,
    )


def resolve_endpoint_type_label(
    endpoint_type: str | None,
    vocab: VocabLookup | None = None,
) -> str:
    """Return a display label for an endpoint type."""
    if not endpoint_type:
        return ""
    return resolve_display_label(
        endpoint_type,
        vocab_name="endpoint_types",
        vocab=vocab,
    )


def resolve_stage_role_label(
    stage_role: str | None,
    vocab: VocabLookup | None = None,
) -> str:
    """Return a display label for an optical path stage role."""
    if not stage_role:
        return ""
    return resolve_display_label(
        stage_role,
        vocab_name="optical_path_stage_roles",
        vocab=vocab,
    )


def resolve_light_source_kind_label(
    kind: str | None,
    vocab: VocabLookup | None = None,
) -> str:
    """Return a display label for a light source kind."""
    if not kind:
        return ""
    return resolve_display_label(
        kind,
        vocab_name="light_source_kinds",
        vocab=vocab,
    )


def resolve_inventory_class_label(
    inventory_class: str | None,
    vocab: VocabLookup | None = None,
) -> str:
    """Return a display label for an inventory class.

    There is no dedicated vocabulary for inventory classes so the resolver
    tries several related vocabularies in order and falls back to the raw
    value with a marker when none match.
    """
    if not inventory_class:
        return ""
    _INVENTORY_VOCAB_MAP: dict[str, str] = {
        "light_source": "light_source_kinds",
        "endpoint": "endpoint_types",
        "camera_port": "endpoint_types",
        "eyepiece": "endpoint_types",
        "optical_element": "optical_path_element_types",
        "splitter": "splitter_types",
    }
    _INVENTORY_STATIC: dict[str, str] = {
        "light_source": "Light Source",
        "endpoint": "Endpoint",
        "camera_port": "Camera Port",
        "eyepiece": "Eyepiece",
        "optical_element": "Optical Element",
        "splitter": "Splitter",
    }
    static = _INVENTORY_STATIC.get(inventory_class)
    if static:
        return static
    mapped_vocab = _INVENTORY_VOCAB_MAP.get(inventory_class)
    if mapped_vocab and vocab is not None:
        term = vocab.terms_by_vocab.get(mapped_vocab, {}).get(inventory_class)
        if term is not None:
            label = getattr(term, "label", None)
            if label:
                return label
    return f"{inventory_class} {_MISSING_MARKER}"


def resolve_vocab_section_title(vocab_name: str) -> str:
    """Return a presentable section title for a vocabulary name.

    Vocabulary *names* are not themselves controlled vocabulary terms, so
    there is no vocab-backed label.  This function converts snake_case
    identifiers to title-case section headers, which is intentional for
    documentation headings – not for controlled-field display values.
    """
    return vocab_name.replace("_", " ").title()
