from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ValidationIssue:
    code: str
    path: str
    message: str


@dataclass
class VocabularyTerm:
    id: str
    label: str
    description: str
    synonyms: list[str]
    metadata: dict[str, Any]

    def tags(self) -> dict[str, Any]:
        raw_tags = self.metadata.get("tags")
        if isinstance(raw_tags, dict):
            return raw_tags
        return {}

    def tag_value(self, key: str, default: Any = None) -> Any:
        return self.tags().get(key, default)


@dataclass
class PolicyRule:
    path: str
    status: str
    field_type: str
    section_id: str | None = None
    section_title: str | None = None
    title: str | None = None
    validation: dict[str, Any] | None = None
    vocab: str | None = None
    required_if: dict[str, Any] | None = None
    aliases: list[str] | None = None
    superseded_by: str | None = None
    min_items: int | None = None
    item_type: str | None = None
    used_by: list[str] | None = None


@dataclass
class ResolvedNode:
    value: Any
    path: str
    context_item: dict[str, Any] | None


@dataclass
class InstrumentPolicy:
    policy_path: Path
    vocab_registry: dict[str, dict[str, Any]]
    rules: list[PolicyRule]


@dataclass
class EventPolicy:
    policy_path: Path
    record_type: str
    vocab_registry: dict[str, dict[str, Any]]
    field_rules: list[dict[str, Any]]
    legacy_and_migration_rules: list[dict[str, Any]]
    cross_field_rules: list[dict[str, Any]]


@dataclass
class EventValidationReport:
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    migration_notices: list[ValidationIssue]


@dataclass
class InstrumentCompletenessReport:
    sections: list[dict[str, Any]]
    missing_required: list[dict[str, Any]]
    missing_conditional: list[dict[str, Any]]
    alias_fallbacks: list[dict[str, Any]]
