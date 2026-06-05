"""Audit-only staff validation packet DTOs built from canonical build context.

The audit PDF/reporting path consumes :class:`InstrumentBuildContext` rather than
raw YAML so staff-facing validation packets stay downstream of the canonical DTO
pipeline used by dashboard, LLM inventory, methods, and virtual microscope
exports.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any

from scripts.build_context import InstrumentBuildContext, clean_text


@dataclass(frozen=True)
class StaffValidationRowDTO:
    """One flattened staff-validation row with DTO provenance."""

    section: str
    label: str
    value: Any
    source_dto: str
    source_path: str
    is_missing: bool = False
    is_warning: bool = False
    warning_message: str = ""
    is_optional: bool = False
    diagnostics: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """Return a serializable DTO row dictionary."""
        return {
            "section": self.section,
            "label": self.label,
            "value": "" if self.value is None else self.value,
            "source_dto": self.source_dto,
            "source_path": self.source_path,
            "is_missing": self.is_missing,
            "is_warning": self.is_warning,
            "warning_message": self.warning_message,
            "is_optional": self.is_optional,
            "diagnostics": copy.deepcopy(self.diagnostics),
        }

    def as_template_entry(self) -> dict[str, Any]:
        """Return the row shape consumed by the audit PDF Jinja template."""
        row = self.as_dict()
        row.pop("section", None)
        return row


@dataclass(frozen=True)
class StaffValidationPacketDTO:
    """Audit-only derived DTO for manual staff validation."""

    instrument_id: str
    display_name: str
    source_path: str
    rows: list[StaffValidationRowDTO]
    diagnostics: list[dict[str, Any]]
    schema_errors: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        """Return the full packet as a serializable derived DTO."""
        return {
            "instrument_id": self.instrument_id,
            "display_name": self.display_name,
            "source_path": self.source_path,
            "rows": [row.as_dict() for row in self.rows],
            "diagnostics": copy.deepcopy(self.diagnostics),
            "schema_errors": copy.deepcopy(self.schema_errors),
        }

    def section_entries(self) -> dict[str, list[dict[str, Any]]]:
        """Group flattened rows by PDF section key."""
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in self.rows:
            grouped.setdefault(row.section, []).append(row.as_template_entry())
        return grouped

    def as_template_context(self) -> dict[str, Any]:
        """Return a dictionary compatible with the existing audit PDF template."""
        grouped = self.section_entries()
        grouped["schema_errors"] = copy.deepcopy(self.schema_errors)
        grouped["packet_diagnostics"] = copy.deepcopy(self.diagnostics)
        grouped["staff_validation_packet"] = {
            "instrument_id": self.instrument_id,
            "display_name": self.display_name,
            "source_path": self.source_path,
            "row_count": len(self.rows),
        }
        return grouped


SECTION_SOURCES: dict[str, tuple[str, str, str]] = {
    "general": ("canonical_instrument_dto", "instrument", "Instrument"),
    "capabilities": ("canonical_instrument_dto", "capabilities", "Capabilities"),
    "modalities": ("canonical_instrument_dto", "modalities", "Modalities"),
    "software": ("canonical_instrument_dto", "software", "Software"),
    "modules": ("canonical_instrument_dto", "modules", "Module"),
    "scanner": ("canonical_instrument_dto", "hardware.scanner", "Scanner"),
    "objectives": ("canonical_instrument_dto", "hardware.objectives", "Objective"),
    "filters": ("canonical_instrument_dto", "hardware.filters", "Filter"),
    "splitters": ("canonical_instrument_dto", "hardware.splitters", "Splitter"),
    "magnification_changers": (
        "canonical_instrument_dto",
        "hardware.magnification_changers",
        "Magnification Changer",
    ),
    "light_sources": ("canonical_instrument_dto", "hardware.sources", "Light Source"),
    "detectors": ("canonical_instrument_dto", "hardware.detectors", "Detector"),
    "endpoints": ("canonical_lightpath_dto", "endpoints", "Endpoint"),
    "optical_path_elements": (
        "canonical_lightpath_dto",
        "optical_path_elements",
        "Optical Path Element",
    ),
    "light_paths": ("canonical_lightpath_dto", "light_paths", "Light Path"),
    "environment": ("canonical_instrument_dto", "hardware.environment", "Environment"),
    "stages": ("canonical_instrument_dto", "hardware.stages", "Stage"),
    "autofocus": ("canonical_instrument_dto", "hardware.hardware_autofocus", "Autofocus"),
    "triggering": ("canonical_instrument_dto", "hardware.triggering", "Triggering"),
    "policy": ("canonical_instrument_dto", "policy", "Policy"),
    "provenance": ("canonical_instrument_dto", "provenance", "Provenance"),
}


def _top_level_coverage_rows(
    *,
    section: str,
    source_dto: str,
    payload: dict[str, Any],
    label_prefix: str,
    diagnostics: list[dict[str, Any]],
) -> list[StaffValidationRowDTO]:
    rows: list[StaffValidationRowDTO] = []
    for key in sorted(payload):
        value = payload.get(key)
        if isinstance(value, dict):
            display_value: Any = {"key_count": len(value), "keys": sorted(str(k) for k in value)}
        elif isinstance(value, list):
            display_value = {"count": len(value)}
        else:
            display_value = value
        source_path = f"{source_dto}.{key}"
        row_diagnostics = _row_diagnostics(diagnostics, source_path)
        rows.append(
            StaffValidationRowDTO(
                section=section,
                label=f"{label_prefix} {_humanize_key(str(key))}",
                value=_coerce_display_value(display_value),
                source_dto=source_dto,
                source_path=source_path,
                is_missing=_is_missing(value),
                is_warning=any(
                    str(item.get("severity", "")).lower() == "warning"
                    for item in row_diagnostics
                ),
                warning_message="; ".join(
                    clean_text(item.get("message"))
                    for item in row_diagnostics
                    if clean_text(item.get("message"))
                ),
                is_optional=False,
                diagnostics=row_diagnostics,
            )
        )
    return rows


def _humanize_key(value: str) -> str:
    return str(value).replace("_", " ").replace("-", " ").title()


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return clean_text(value) == ""
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _coerce_display_value(value: Any) -> Any:
    if value is None:
        return ""
    if _is_scalar(value):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _get_path(payload: Any, dotted_path: str) -> Any:
    current = payload
    if not dotted_path:
        return current
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _summarize_large_value(value: Any) -> Any:
    """Keep staff PDF rows useful when canonical DTO branches are large."""
    if isinstance(value, list):
        identifiers = [
            item.get("id")
            or item.get("branch_id")
            or item.get("endpoint_id")
            or item.get("source_id")
            for item in value
            if isinstance(item, dict)
        ]
        return {
            "count": len(value),
            "ids": [identifier for identifier in identifiers if identifier],
        }

    if not isinstance(value, dict):
        return value

    summary: dict[str, Any] = {}
    for key in (
        "contract_version",
        "selection_state",
        "execution_summary",
    ):
        if key in value:
            summary[key] = value[key]

    for key in ("selected_route_steps", "route_steps", "steps"):
        if isinstance(value.get(key), list):
            summary[f"{key}_count"] = len(value[key])

    for key in ("routing_branch_optics", "branches"):
        if key in value:
            branch_value = value[key]
            summary[key] = (
                {"count": len(branch_value)}
                if isinstance(branch_value, list)
                else branch_value
            )

    return summary or {
        "key_count": len(value),
        "keys": sorted(str(key) for key in value),
    }


def _policy_summary(policy: Any) -> dict[str, Any]:
    if not isinstance(policy, dict):
        return {}

    sections = policy.get("sections") if isinstance(policy.get("sections"), list) else []
    missing_required = (
        policy.get("missing_required")
        if isinstance(policy.get("missing_required"), list)
        else []
    )
    missing_conditional = (
        policy.get("missing_conditional")
        if isinstance(policy.get("missing_conditional"), list)
        else []
    )
    alias_fallbacks = (
        policy.get("alias_fallbacks")
        if isinstance(policy.get("alias_fallbacks"), list)
        else []
    )

    section_summaries = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        rules = section.get("rules") if isinstance(section.get("rules"), list) else []
        section_summaries.append(
            {
                "id": section.get("id"),
                "title": section.get("title"),
                "rule_count": len(rules),
                "missing_rule_count": len(
                    [r for r in rules if isinstance(r, dict) and r.get("missing")]
                ),
            }
        )

    return {
        "section_count": len(sections),
        "sections": section_summaries,
        "missing_required_count": len(missing_required),
        "missing_required": missing_required,
        "missing_conditional_count": len(missing_conditional),
        "missing_conditional": missing_conditional,
        "alias_fallback_count": len(alias_fallbacks),
        "alias_fallbacks": alias_fallbacks,
    }


def _dto_payload(context: InstrumentBuildContext, source_dto: str) -> dict[str, Any]:
    payload = getattr(context, source_dto, {})
    return payload if isinstance(payload, dict) else {}


def _diagnostic_matches_path(diagnostic: dict[str, Any], source_path: str) -> bool:
    diag_path = clean_text(diagnostic.get("path"))
    if not diag_path:
        return False
    normalized = source_path
    for prefix in (
        "canonical_instrument_dto.",
        "canonical_lightpath_dto.",
        "canonical.",
        "lightpath_dto.",
    ):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    return (
        diag_path == normalized
        or diag_path.startswith(f"{normalized}.")
        or normalized.startswith(diag_path)
    )


def _row_diagnostics(
    diagnostics: list[dict[str, Any]],
    source_path: str,
) -> list[dict[str, Any]]:
    return [
        copy.deepcopy(item)
        for item in diagnostics
        if isinstance(item, dict) and _diagnostic_matches_path(item, source_path)
    ]


def _flatten_rows(
    *,
    section: str,
    label: str,
    value: Any,
    source_dto: str,
    source_path: str,
    diagnostics: list[dict[str, Any]],
    is_optional: bool,
    compact_keys: set[str] | None = None,
) -> list[StaffValidationRowDTO]:
    rows: list[StaffValidationRowDTO] = []
    compact_keys = compact_keys or set()

    def add_row(current_label: str, current_value: Any, current_path: str) -> None:
        row_diagnostics = _row_diagnostics(diagnostics, current_path)
        is_warning = any(
            str(item.get("severity", "")).lower() == "warning"
            for item in row_diagnostics
        )
        warning_message = "; ".join(
            clean_text(item.get("message"))
            for item in row_diagnostics
            if clean_text(item.get("message"))
        )
        rows.append(
            StaffValidationRowDTO(
                section=section,
                label=current_label,
                value=_coerce_display_value(current_value),
                source_dto=source_dto,
                source_path=current_path,
                is_missing=_is_missing(current_value),
                is_warning=is_warning,
                warning_message=warning_message,
                is_optional=is_optional,
                diagnostics=row_diagnostics,
            )
        )

    def walk(current_label: str, current_value: Any, current_path: str) -> None:
        path_key = current_path.rsplit(".", 1)[-1]
        if "[" in path_key:
            path_key = path_key.rsplit("]", 1)[-1].lstrip(".") or path_key

        if path_key in compact_keys:
            add_row(current_label, _summarize_large_value(current_value), current_path)
            return

        if isinstance(current_value, dict):
            if not current_value:
                add_row(current_label, current_value, current_path)
                return
            for key, nested_value in current_value.items():
                walk(
                    f"{current_label} {_humanize_key(str(key))}",
                    nested_value,
                    f"{current_path}.{key}" if current_path else str(key),
                )
            return

        if isinstance(current_value, list):
            if not current_value:
                add_row(current_label, current_value, current_path)
                return
            if all(_is_scalar(item) for item in current_value):
                add_row(current_label, current_value, current_path)
                return
            for index, item in enumerate(current_value):
                display_index = index + 1
                item_label = f"{current_label} {display_index}"
                item_path = f"{current_path}[{index}]"
                if isinstance(item, dict):
                    for key, nested_value in item.items():
                        walk(
                            f"{item_label} {_humanize_key(str(key))}",
                            nested_value,
                            f"{item_path}.{key}",
                        )
                else:
                    add_row(item_label, item, item_path)
            return

        add_row(current_label, current_value, current_path)

    walk(label, value, source_path)
    return rows


def _packet_diagnostics(context: InstrumentBuildContext) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for item in [*context.validation_diagnostics, *context.diagnostics]:
        if isinstance(item, dict):
            diagnostics.append(copy.deepcopy(item))
    return diagnostics


def _schema_errors(context: InstrumentBuildContext) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for item in context.validation_diagnostics:
        if not isinstance(item, dict):
            continue
        errors.append(
            {
                "level": (
                    clean_text(item.get("status"))
                    or clean_text(item.get("level"))
                    or "Required"
                ),
                "path": clean_text(item.get("path")),
                "title": clean_text(item.get("title")) or clean_text(item.get("path")),
            }
        )
    return errors


def build_staff_validation_packet(
    context: InstrumentBuildContext,
    *,
    section_sources: dict[str, tuple[str, str, str]] | None = None,
) -> StaffValidationPacketDTO:
    """Build the staff validation packet from a canonical build context."""
    source_map = section_sources or SECTION_SOURCES
    diagnostics = _packet_diagnostics(context)
    rows: list[StaffValidationRowDTO] = []

    for section, (source_dto, dto_path, label) in source_map.items():
        payload = _dto_payload(context, source_dto)
        value = _get_path(payload, dto_path)
        if section == "policy":
            value = _policy_summary(value)
        source_path = f"{source_dto}.{dto_path}" if dto_path else source_dto
        compact_keys = (
            {
                "selected_execution",
                "route_steps",
                "illumination_traversal",
                "detection_traversal",
                "graph_nodes",
                "graph_edges",
                "graph_tree",
                "branch_blocks",
                "hardware_inventory_ids",
            }
            if section == "light_paths"
            else set()
        )
        rows.extend(
            _flatten_rows(
                section=section,
                label=label,
                value=value,
                source_dto=source_dto,
                source_path=source_path,
                diagnostics=diagnostics,
                is_optional=section not in {"general", "capabilities", "objectives"},
                compact_keys=compact_keys,
            )
        )

    rows.extend(
        _top_level_coverage_rows(
            section="canonical_dto_coverage",
            source_dto="canonical_instrument_dto",
            payload=context.canonical_instrument_dto,
            label_prefix="Canonical Instrument DTO",
            diagnostics=diagnostics,
        )
    )
    rows.extend(
        _top_level_coverage_rows(
            section="canonical_dto_coverage",
            source_dto="canonical_lightpath_dto",
            payload=context.canonical_lightpath_dto,
            label_prefix="Canonical Lightpath DTO",
            diagnostics=diagnostics,
        )
    )

    canonical_instrument = context.canonical_instrument_dto.get("instrument")
    if not isinstance(canonical_instrument, dict):
        canonical_instrument = {}

    return StaffValidationPacketDTO(
        instrument_id=context.instrument_id,
        display_name=clean_text(canonical_instrument.get("display_name")) or context.instrument_id,
        source_path=context.source_path,
        rows=rows,
        diagnostics=diagnostics,
        schema_errors=_schema_errors(context),
    )


__all__ = [
    "SECTION_SOURCES",
    "StaffValidationPacketDTO",
    "StaffValidationRowDTO",
    "build_staff_validation_packet",
]
