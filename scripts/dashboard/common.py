"""Shared formatting and helper utilities for dashboard modules.

All helpers here are pure functions with no dashboard-module dependencies.
Domain modules (loaders, instrument_view, optical_path_view, …) import from
this module; this module never imports from them.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Text / string helpers
# ---------------------------------------------------------------------------

def clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    # Remove common double-decoding artifacts (UTF-8 NBSP rendered as "Â ")
    s = value.replace("\u00c2\u00a0", " ").replace("\u00a0", " ")
    s = s.replace("Â\u00a0", " ").replace("Â ", " ")
    return s.strip()


def clean_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [clean_text(item) for item in value if clean_text(item)]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def _fmt_num(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _format_wavelength_label(value: Any) -> str:
    wavelength = _fmt_num(value)
    if not wavelength:
        return ""
    normalized = wavelength.strip().lower()
    if normalized.endswith("nm"):
        return wavelength.strip()
    try:
        float(normalized)
    except (TypeError, ValueError):
        return wavelength.strip()
    return f"{wavelength} nm"


def _bool_display(value: Any) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "—"


def _human_list(items: list[str]) -> str:
    cleaned = [clean_text(item) for item in items if clean_text(item)]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"


def _compact_join(parts: Iterable[str]) -> str:
    return ", ".join(part for part in parts if isinstance(part, str) and part.strip())


def slugify(value: str) -> str:
    s = value.lower().strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def strip_empty_values(data: Any) -> Any:
    """Recursively remove empty optional values while preserving False/0."""

    def is_empty(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value == ""
        if isinstance(value, list):
            return len(value) == 0
        if isinstance(value, dict):
            return len(value) == 0
        return False

    if isinstance(data, dict):
        pruned: dict[str, Any] = {}
        for key, value in data.items():
            cleaned = strip_empty_values(value)
            if not is_empty(cleaned):
                pruned[key] = cleaned
        return pruned

    if isinstance(data, list):
        pruned_list = []
        for item in data:
            cleaned = strip_empty_values(item)
            if not is_empty(cleaned):
                pruned_list.append(cleaned)
        return pruned_list

    return data


def normalize_optional_bool(value: Any) -> bool | None:
    """Normalize YAML-style booleans while preserving missing values as None."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "y", "1"}:
            return True
        if normalized in {"false", "no", "n", "0"}:
            return False
    return None


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------

def json_script_data(payload: Any) -> str:
    """Serialize data safely for embedding inside a <script type="application/json"> tag."""
    return (
        json.dumps(payload, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


# ---------------------------------------------------------------------------
# Vocabulary helpers
# ---------------------------------------------------------------------------

def vocab_label(vocabulary: Any, vocab_name: str, term_id: str) -> str:
    """Return a friendly vocabulary label for a canonical ID."""
    term = vocabulary.terms_by_vocab.get(vocab_name, {}).get(term_id)
    return term.label if term else term_id


def _vocab_display(vocabulary: Any, vocab_name: str, value: Any) -> str:
    raw = clean_text(value)
    if not raw:
        return ""
    return vocab_label(vocabulary, vocab_name, raw)


# ---------------------------------------------------------------------------
# Display / spec-line helpers
# ---------------------------------------------------------------------------

def _spec_lines(*pairs: tuple[str, Any]) -> list[str]:
    lines: list[str] = []
    for label, raw_value in pairs:
        if raw_value in (None, "", [], {}):
            continue
        lines.append(f"**{label}:** {raw_value}")
    return lines


def _component_reference(manufacturer: Any, model: Any, fallback: str) -> str:
    manufacturer_text = clean_text(manufacturer)
    model_text = clean_text(model)
    if manufacturer_text and model_text:
        return f"{manufacturer_text} {model_text}"
    if model_text:
        return model_text
    if manufacturer_text:
        return manufacturer_text
    return fallback


def _quarep_value(value: Any) -> str:
    cleaned = clean_text(value)
    return cleaned or "missing (ask staff)"


def _quarep_specs_clause(
    manufacturer: Any,
    model: Any,
    product_code: Any,
    *,
    extras: Iterable[str] | None = None,
) -> str:
    parts = [
        f"Manufacturer: {_quarep_value(manufacturer)}",
        f"Model: {_quarep_value(model)}",
        f"Product code: {_quarep_value(product_code)}",
    ]
    for part in extras or []:
        cleaned = clean_text(part)
        if cleaned:
            parts.append(cleaned)
    return "; ".join(parts)


def _append_quarep_specs(
    sentence: Any,
    manufacturer: Any,
    model: Any,
    product_code: Any,
    *,
    extras: Iterable[str] | None = None,
) -> str:
    base = clean_text(sentence).rstrip()
    if base.endswith("."):
        base = base[:-1]
    specs = _quarep_specs_clause(manufacturer, model, product_code, extras=extras)
    return f"{base} ({specs})." if base else f"{specs}."


def _inventory_method_extras(item: dict[str, Any]) -> list[str]:
    extras: list[str] = []
    source_meta = item.get("source_metadata") if isinstance(item.get("source_metadata"), dict) else {}
    optical_meta = item.get("optical_element_metadata") if isinstance(item.get("optical_element_metadata"), dict) else {}
    endpoint_meta = item.get("endpoint_metadata") if isinstance(item.get("endpoint_metadata"), dict) else {}

    wavelength = _format_wavelength_label(source_meta.get("wavelength_nm"))
    if wavelength:
        extras.append(f"Wavelength: {wavelength}")
    tunable_min = _fmt_num(source_meta.get("tunable_min_nm"))
    tunable_max = _fmt_num(source_meta.get("tunable_max_nm"))
    if tunable_min and tunable_max:
        extras.append(f"Tunable range: {tunable_min}-{tunable_max} nm")
    power = clean_text(source_meta.get("power"))
    if power:
        extras.append(f"Power: {power}")
    timing = clean_text(source_meta.get("timing_mode"))
    if timing:
        extras.append(f"Timing mode: {timing}")

    center = _fmt_num(optical_meta.get("center_nm"))
    width = _fmt_num(optical_meta.get("width_nm"))
    if center and width:
        extras.append(f"Band: {center}/{width} nm")
    elif center:
        extras.append(f"Center: {center} nm")
    cut_on = _fmt_num(optical_meta.get("cut_on_nm"))
    if cut_on:
        extras.append(f"Cut-on: {cut_on} nm")
    cut_off = _fmt_num(optical_meta.get("cut_off_nm"))
    if cut_off:
        extras.append(f"Cut-off: {cut_off} nm")

    def _band_summary(bands: Any, label: str) -> str:
        summaries: list[str] = []
        for band in bands if isinstance(bands, list) else []:
            if not isinstance(band, dict):
                continue
            band_center = _fmt_num(band.get("center_nm"))
            band_width = _fmt_num(band.get("width_nm"))
            if band_center and band_width:
                summaries.append(f"{band_center}/{band_width} nm")
            elif band_center:
                summaries.append(f"{band_center} nm")
        return f"{label}: {', '.join(summaries)}" if summaries else ""

    for label, key in (("Bands", "bands"), ("Transmission", "transmission_bands"), ("Reflection", "reflection_bands")):
        summary = _band_summary(optical_meta.get(key), label)
        if summary:
            extras.append(summary)

    collection_min = _fmt_num(endpoint_meta.get("collection_min_nm") or endpoint_meta.get("min_nm"))
    collection_max = _fmt_num(endpoint_meta.get("collection_max_nm") or endpoint_meta.get("max_nm"))
    if collection_min and collection_max:
        extras.append(f"Collection range: {collection_min}-{collection_max} nm")
    channel_name = clean_text(endpoint_meta.get("channel_name"))
    if channel_name:
        extras.append(f"Channel: {channel_name}")

    return extras


def _display_labels(rows: Any, *, installed_only: bool = False) -> list[str]:
    labels: list[str] = []
    if not isinstance(rows, list):
        return labels
    for row in rows:
        if not isinstance(row, dict):
            continue
        if installed_only and row.get("is_installed") is False:
            continue
        label = clean_text(row.get("display_label") or row.get("name") or row.get("model") or row.get("id"))
        if label:
            labels.append(label)
    return labels


def _collect_known_missing_paths(value: Any, prefix: str = "") -> tuple[list[str], list[str]]:
    known_fields: list[str] = []
    missing_fields: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            child_known, child_missing = _collect_known_missing_paths(child, child_prefix)
            known_fields.extend(child_known)
            missing_fields.extend(child_missing)
        return known_fields, missing_fields

    if isinstance(value, list):
        if not value:
            known_fields.append(prefix)
            return known_fields, missing_fields
        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]"
            child_known, child_missing = _collect_known_missing_paths(child, child_prefix)
            known_fields.extend(child_known)
            missing_fields.extend(child_missing)
        return known_fields, missing_fields

    if value is None:
        missing_fields.append(prefix)
    else:
        known_fields.append(prefix)

    return known_fields, missing_fields


__all__ = [
    "clean_text",
    "clean_string_list",
    "_fmt_num",
    "_format_wavelength_label",
    "_bool_display",
    "_human_list",
    "_compact_join",
    "slugify",
    "strip_empty_values",
    "normalize_optional_bool",
    "json_script_data",
    "vocab_label",
    "_vocab_display",
    "_spec_lines",
    "_component_reference",
    "_quarep_value",
    "_quarep_specs_clause",
    "_append_quarep_specs",
    "_inventory_method_extras",
    "_display_labels",
    "_collect_known_missing_paths",
]
