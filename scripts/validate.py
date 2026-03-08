"""Validation helpers and CLI for dashboard source ledgers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Any, Iterable

import yaml

DEFAULT_ALLOWED_RECORD_TYPES: tuple[str, ...] = ("qc_session", "maintenance_event")
INSTRUMENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
YEAR_PATTERN = re.compile(r"^\d{4}$")
ISO_YEAR_PATTERN = re.compile(r"^(\d{4})-")
FILENAME_DATE_PATTERN = re.compile(r"^(\d{4})-\d{2}-\d{2}(?:_|$)")


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


class Vocabulary:
    """Loads vocabulary files and validates values against canonical IDs/synonyms."""

    def __init__(
        self,
        vocab_dir: Path = Path("vocab"),
        vocab_registry: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.vocab_dir = vocab_dir
        self.vocab_registry = vocab_registry
        self.terms_by_vocab: dict[str, dict[str, VocabularyTerm]] = {}
        self.valid_ids_by_vocab: dict[str, set[str]] = {}
        self.synonyms_by_vocab: dict[str, dict[str, str]] = {}
        self._load_all()

    @staticmethod
    def _normalize(value: str) -> str:
        return value.strip()

    def _load_all(self) -> None:
        if self.vocab_registry:
            vocab_items = []
            for vocab_name, vocab_spec in self.vocab_registry.items():
                if not isinstance(vocab_spec, dict):
                    continue
                inline_allowed = vocab_spec.get("allowed_values")
                if vocab_spec.get("source") == "inline" and isinstance(inline_allowed, list):
                    self.terms_by_vocab[vocab_name] = {
                        value: VocabularyTerm(
                            id=value,
                            label=value,
                            description="",
                            synonyms=[],
                            metadata={},
                        )
                        for value in [str(item).strip() for item in inline_allowed if str(item).strip()]
                    }
                    self.valid_ids_by_vocab[vocab_name] = set(self.terms_by_vocab[vocab_name].keys())
                    self.synonyms_by_vocab[vocab_name] = {}
                    continue

                raw_file = vocab_spec.get("file") or vocab_spec.get("path")
                if not isinstance(raw_file, str) or not raw_file.strip():
                    continue
                vocab_items.append((vocab_name, Path(raw_file.strip())))
        else:
            vocab_items = [(vocab_file.stem, vocab_file) for vocab_file in sorted(self.vocab_dir.glob("*.yaml"))]

        for vocab_name, vocab_file in vocab_items:
            payload, load_error = _load_yaml(vocab_file)
            if load_error is not None or payload is None:
                continue

            raw_terms = payload.get("terms")
            if not isinstance(raw_terms, list):
                continue

            terms: dict[str, VocabularyTerm] = {}
            valid_ids: set[str] = set()
            synonym_lookup: dict[str, str] = {}
            for raw_term in raw_terms:
                if not isinstance(raw_term, dict):
                    continue

                raw_id = raw_term.get("id")
                if not isinstance(raw_id, str) or not raw_id.strip():
                    continue

                canonical_id = raw_id.strip()
                label = raw_term.get("label")
                description = raw_term.get("description")
                raw_synonyms = raw_term.get("synonyms")
                term_synonyms = [
                    synonym.strip()
                    for synonym in (raw_synonyms if isinstance(raw_synonyms, list) else [])
                    if isinstance(synonym, str) and synonym.strip()
                ]

                terms[canonical_id] = VocabularyTerm(
                    id=canonical_id,
                    label=label.strip() if isinstance(label, str) else canonical_id,
                    description=description.strip() if isinstance(description, str) else "",
                    synonyms=term_synonyms,
                    metadata={
                        key: value
                        for key, value in raw_term.items()
                        if key not in {"id", "label", "description", "synonyms"}
                    },
                )
                valid_ids.add(canonical_id)

                for synonym in term_synonyms:
                    synonym_lookup[synonym.casefold()] = canonical_id

            self.terms_by_vocab[vocab_name] = terms
            self.valid_ids_by_vocab[vocab_name] = valid_ids
            self.synonyms_by_vocab[vocab_name] = synonym_lookup

    def check(self, vocab_name: str, value: Any) -> tuple[bool, str | None]:
        if not isinstance(value, str):
            return False, None

        cleaned = self._normalize(value)
        if not cleaned:
            return False, None

        if cleaned in self.valid_ids_by_vocab.get(vocab_name, set()):
            return True, None

        canonical = self.synonyms_by_vocab.get(vocab_name, {}).get(cleaned.casefold())
        if canonical is not None:
            return False, canonical

        return False, None

    def resolve_canonical(self, vocab_name: str, value: Any) -> str | None:
        if not isinstance(value, str):
            return None

        cleaned = self._normalize(value)
        if not cleaned:
            return None

        if cleaned in self.valid_ids_by_vocab.get(vocab_name, set()):
            return cleaned

        return self.synonyms_by_vocab.get(vocab_name, {}).get(cleaned.casefold())

    def get_term(self, vocab_name: str, canonical_id: str) -> VocabularyTerm | None:
        return self.terms_by_vocab.get(vocab_name, {}).get(canonical_id)


def _iter_yaml_files(base_dir: Path) -> Iterable[Path]:
    if not base_dir.exists() or not base_dir.is_dir():
        return []
    return [p for p in sorted(base_dir.rglob("*")) if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}]


def _load_yaml(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return None, str(exc)

    if payload is None:
        return None, "YAML document is empty."
    if not isinstance(payload, dict):
        return None, f"Expected YAML mapping/object at top level, found {type(payload).__name__}."

    return payload, None


def _is_valid_instrument_id(value: str) -> bool:
    return bool(INSTRUMENT_ID_PATTERN.fullmatch(value))


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_numeric_string(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"\d+(?:\.\d+)?", value.strip()))


def _is_positive_number(value: Any) -> bool:
    return _is_number(value) and value > 0


def _is_positive_number_or_numeric_string(value: Any) -> bool:
    if _is_positive_number(value):
        return True
    if _is_numeric_string(value):
        return float(str(value).strip()) > 0
    return False


def _is_valid_wavelength(value: Any) -> bool:
    if _is_number(value):
        return value > 0

    if not isinstance(value, str):
        return False

    cleaned = value.strip()
    if not cleaned:
        return False

    if _is_numeric_string(cleaned):
        return float(cleaned) > 0

    return bool(re.fullmatch(r"\d+(?:\.\d+)?/\d+(?:\.\d+)?", cleaned))


def _is_descriptive_wavelength(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not _is_valid_wavelength(value)


def _get_started_year(payload: dict[str, Any], event_file: Path) -> str | None:
    started_utc = payload.get("started_utc")
    if isinstance(started_utc, str):
        started_match = ISO_YEAR_PATTERN.match(started_utc.strip())
        if started_match:
            return started_match.group(1)

    filename_match = FILENAME_DATE_PATTERN.match(event_file.stem)
    if filename_match:
        return filename_match.group(1)

    return None


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
    missing_required: list[dict[str, str]]
    missing_conditional: list[dict[str, str]]
    alias_fallbacks: list[dict[str, str]]


def load_policy(policy_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw_text = policy_path.read_text(encoding='utf-8')
    except OSError as exc:
        return None, f"Failed loading policy '{policy_path.as_posix()}': {exc}"

    try:
        payload = yaml.safe_load(raw_text)
    except yaml.YAMLError:
        try:
            payload = yaml.safe_load(_sanitize_policy_yaml(raw_text))
        except yaml.YAMLError as exc:
            return None, f"Failed loading policy '{policy_path.as_posix()}': {exc}"

    if payload is None:
        return None, f"Failed loading policy '{policy_path.as_posix()}': YAML document is empty."
    if not isinstance(payload, dict):
        return None, (
            f"Failed loading policy '{policy_path.as_posix()}': expected YAML mapping/object at top level, "
            f"found {type(payload).__name__}."
        )
    return payload, None


def _sanitize_policy_yaml(raw_text: str) -> str:
    """Normalize known non-YAML inline path list syntax used in policy drafts."""

    sanitized = raw_text
    sanitized = re.sub(
        r"^(\s*aliases:\s*)\[([A-Za-z0-9_.\[\]-]+)\]\s*$",
        lambda m: f"{m.group(1)}['{m.group(2)}']",
        sanitized,
        flags=re.MULTILINE,
    )
    return sanitized


def _load_instrument_policy(
    policy_path: Path = Path('instrument_metadata_policy.yaml'),
) -> tuple[InstrumentPolicy | None, str | None]:
    candidate_paths = [policy_path, Path('schema/instrument_policy.yaml')]
    selected: Path | None = None
    payload: dict[str, Any] | None = None

    for candidate in candidate_paths:
        if not candidate.exists():
            continue

        loaded_payload, load_error = load_policy(candidate)
        if load_error is not None or loaded_payload is None:
            return None, load_error

        payload = loaded_payload
        selected = candidate
        break

    if selected is None or payload is None:
        return None, 'Missing instrument metadata policy file (expected instrument_metadata_policy.yaml or schema/instrument_policy.yaml).'

    vocab_registry = payload.get('vocab_registry')
    if not isinstance(vocab_registry, dict):
        return None, f"Policy '{selected.as_posix()}' missing mapping key 'vocab_registry'."

    raw_sections = payload.get('sections')
    if not isinstance(raw_sections, list):
        return None, f"Policy '{selected.as_posix()}' missing list key 'sections'."

    rules: list[PolicyRule] = []
    for section in raw_sections:
        if not isinstance(section, dict):
            continue
        section_id = section.get('id') if isinstance(section.get('id'), str) else None
        section_title = section.get('title') if isinstance(section.get('title'), str) else None
        for raw_rule in section.get('rules', []):
            if not isinstance(raw_rule, dict):
                continue
            path_value = raw_rule.get('path')
            status = raw_rule.get('status')
            field_type = raw_rule.get('type')
            if not isinstance(path_value, str) or not path_value.strip():
                continue
            if not isinstance(status, str) or not status.strip():
                continue
            if not isinstance(field_type, str) or not field_type.strip():
                continue
            rules.append(
                PolicyRule(
                    path=path_value.strip(),
                    status=status.strip(),
                    field_type=field_type.strip(),
                    section_id=section_id,
                    section_title=section_title,
                    title=raw_rule.get('title') if isinstance(raw_rule.get('title'), str) else None,
                    validation=raw_rule.get('validation') if isinstance(raw_rule.get('validation'), dict) else None,
                    vocab=raw_rule.get('vocab') if isinstance(raw_rule.get('vocab'), str) else None,
                    required_if=raw_rule.get('required_if') if isinstance(raw_rule.get('required_if'), dict) else None,
                    aliases=raw_rule.get('aliases') if isinstance(raw_rule.get('aliases'), list) else None,
                    superseded_by=raw_rule.get('superseded_by') if isinstance(raw_rule.get('superseded_by'), str) else None,
                    min_items=raw_rule.get('min_items') if isinstance(raw_rule.get('min_items'), int) else None,
                    used_by=[str(v).strip() for v in raw_rule.get('used_by') if isinstance(v, str)]
                    if isinstance(raw_rule.get('used_by'), list)
                    else None,
                )
            )

    return InstrumentPolicy(policy_path=selected, vocab_registry=vocab_registry, rules=rules), None


def _resolve_path_nodes(payload: dict[str, Any], dotted_path: str) -> list[ResolvedNode]:
    segments = dotted_path.split('.') if dotted_path else []
    nodes: list[ResolvedNode] = [ResolvedNode(value=payload, path='', context_item=None)]

    for segment in segments:
        is_list = segment.endswith('[]')
        key = segment[:-2] if is_list else segment
        next_nodes: list[ResolvedNode] = []
        for node in nodes:
            current = node.value
            base_path = node.path
            if not isinstance(current, dict) or key not in current:
                continue

            child = current.get(key)
            child_path = f"{base_path}.{key}" if base_path else key
            if is_list:
                if not isinstance(child, list):
                    continue
                for idx, item in enumerate(child):
                    ctx = item if isinstance(item, dict) else None
                    next_nodes.append(ResolvedNode(value=item, path=f"{child_path}[{idx}]", context_item=ctx))
            else:
                ctx = node.context_item if node.context_item is not None else (child if isinstance(child, dict) else None)
                next_nodes.append(ResolvedNode(value=child, path=child_path, context_item=ctx))

        nodes = next_nodes
        if not nodes:
            break

    return nodes


def _resolve_rule_nodes(payload: dict[str, Any], dotted_path: str) -> list[ResolvedNode]:
    """Resolve policy rule nodes while emitting missing leaf nodes for existing parent items."""
    if not dotted_path:
        return [ResolvedNode(value=payload, path='', context_item=None)]

    segments = dotted_path.split('.')
    if len(segments) == 1:
        nodes = _resolve_path_nodes(payload, dotted_path)
        if nodes:
            return nodes
        key = segments[0][:-2] if segments[0].endswith('[]') else segments[0]
        return [ResolvedNode(value=None, path=key, context_item=None)]

    parent_nodes = _resolve_path_nodes(payload, '.'.join(segments[:-1]))
    if not parent_nodes:
        return []

    leaf_segment = segments[-1]
    is_leaf_list = leaf_segment.endswith('[]')
    leaf_key = leaf_segment[:-2] if is_leaf_list else leaf_segment
    resolved_nodes: list[ResolvedNode] = []
    for parent in parent_nodes:
        if not isinstance(parent.value, dict):
            continue

        child_path = f"{parent.path}.{leaf_key}" if parent.path else leaf_key
        if leaf_key not in parent.value:
            resolved_nodes.append(
                ResolvedNode(
                    value=None,
                    path=child_path,
                    context_item=parent.context_item if parent.context_item is not None else parent.value,
                )
            )
            continue

        child = parent.value.get(leaf_key)
        if is_leaf_list:
            if not isinstance(child, list):
                resolved_nodes.append(
                    ResolvedNode(
                        value=child,
                        path=child_path,
                        context_item=parent.context_item if parent.context_item is not None else parent.value,
                    )
                )
                continue
            for idx, item in enumerate(child):
                ctx = item if isinstance(item, dict) else None
                resolved_nodes.append(ResolvedNode(value=item, path=f"{child_path}[{idx}]", context_item=ctx))
            continue

        ctx = parent.context_item if parent.context_item is not None else (child if isinstance(child, dict) else None)
        resolved_nodes.append(ResolvedNode(value=child, path=child_path, context_item=ctx))

    return resolved_nodes


def build_instrument_completeness_report(payload: dict[str, Any]) -> InstrumentCompletenessReport:
    """Build policy-driven completeness metadata for a single instrument payload."""
    policy, policy_error = _load_instrument_policy()
    if policy_error is not None or policy is None:
        return InstrumentCompletenessReport(
            sections=[],
            missing_required=[],
            missing_conditional=[],
            alias_fallbacks=[],
        )

    vocabulary = Vocabulary(vocab_registry=policy.vocab_registry)
    sections: dict[tuple[str | None, str | None], list[dict[str, Any]]] = {}
    missing_required: list[dict[str, str]] = []
    missing_conditional: list[dict[str, str]] = []
    alias_fallbacks: list[dict[str, str]] = []

    for rule in policy.rules:
        resolved = _resolve_rule_nodes(payload, rule.path)
        alias_hits: list[str] = []
        if rule.aliases:
            for alias in rule.aliases:
                if _resolve_rule_nodes(payload, alias):
                    alias_hits.append(alias)
                    alias_fallbacks.append({
                        'path': rule.path,
                        'alias': alias,
                        'title': rule.title or rule.path,
                    })

        present = bool(any(node.value not in (None, '') for node in resolved) or alias_hits)
        condition_triggered = False
        missing = False

        if rule.status == 'required':
            missing = not present or any(node.value in (None, '') for node in resolved)
            if missing:
                missing_required.append({'path': rule.path, 'title': rule.title or rule.path})
        elif rule.status == 'conditional' and rule.required_if is not None:
            condition_triggered = _evaluate_required_if(
                rule.required_if,
                payload=payload,
                item_context=None,
                vocabulary=vocabulary,
            )
            if condition_triggered and not present:
                missing = True
            else:
                for node in resolved:
                    if node.value in (None, '') and _evaluate_required_if(
                        rule.required_if,
                        payload=payload,
                        item_context=node.context_item,
                        vocabulary=vocabulary,
                    ):
                        missing = True
                        break
            if missing:
                missing_conditional.append({'path': rule.path, 'title': rule.title or rule.path})

        section_key = (rule.section_id, rule.section_title)
        sections.setdefault(section_key, []).append(
            {
                'path': rule.path,
                'title': rule.title or rule.path,
                'status': rule.status,
                'present': present,
                'missing': missing,
                'condition_triggered': condition_triggered,
                'alias_used': bool(alias_hits),
                'aliases': alias_hits,
                'used_by': list(rule.used_by) if rule.used_by is not None else [],
            }
        )

    section_entries = [
        {
            'id': section_id,
            'title': section_title or section_id or 'Section',
            'rules': rules,
        }
        for (section_id, section_title), rules in sections.items()
    ]

    return InstrumentCompletenessReport(
        sections=section_entries,
        missing_required=missing_required,
        missing_conditional=missing_conditional,
        alias_fallbacks=alias_fallbacks,
    )


def _check_type(value: Any, field_type: str) -> bool:
    if field_type in {'string', 'text'}:
        return isinstance(value, str)
    if field_type == 'string_or_empty':
        return isinstance(value, str)
    if field_type == 'positive_number':
        return _is_positive_number_or_numeric_string(value)
    if field_type == 'boolean':
        return isinstance(value, bool)
    if field_type == 'slug':
        return isinstance(value, str) and _is_valid_instrument_id(value.strip())
    if field_type == 'url':
        if not isinstance(value, str) or not value.strip():
            return False
        return bool(re.match(r'^https?://', value.strip()))
    if field_type == 'list':
        return isinstance(value, list)
    if field_type == 'year_or_empty':
        return value in (None, '') or (isinstance(value, str) and bool(YEAR_PATTERN.fullmatch(value.strip())))
    if field_type == 'spectral_descriptor':
        return _is_valid_wavelength(value) or _is_descriptive_wavelength(value)
    return True


def _coerce_number(value: Any) -> float | None:
    if _is_number(value):
        return float(value)
    if _is_numeric_string(value):
        return float(str(value).strip())
    return None


def _check_rule_validation(value: Any, rule: PolicyRule) -> str | None:
    if rule.validation is None:
        return None

    pattern = rule.validation.get('pattern')
    if isinstance(pattern, str) and isinstance(value, str) and not re.fullmatch(pattern, value.strip()):
        return f"does not match required pattern '{pattern}'"

    min_value = rule.validation.get('min')
    if isinstance(min_value, (int, float)):
        numeric = _coerce_number(value)
        if numeric is None or numeric < float(min_value):
            return f"must be >= {min_value}"

    max_value = rule.validation.get('max')
    if isinstance(max_value, (int, float)):
        numeric = _coerce_number(value)
        if numeric is None or numeric > float(max_value):
            return f"must be <= {max_value}"

    accepted_examples = rule.validation.get('accepted_examples')
    if isinstance(accepted_examples, list) and value is not None:
        normalized_examples = {str(v).strip() for v in accepted_examples if isinstance(v, (str, int, float))}
        if isinstance(value, str) and value.strip() and value.strip() not in normalized_examples:
            if rule.field_type == 'spectral_descriptor' and not _is_valid_wavelength(value):
                return (
                    'is not a recognized spectral descriptor example; accepted examples include '
                    + ', '.join(sorted(normalized_examples))
                )

    return None


def _parent_path_from_list_path(path: str) -> str:
    return path.replace('[]', '')


def _evaluate_required_if(
    required_if: dict[str, Any],
    *,
    payload: dict[str, Any],
    item_context: dict[str, Any] | None,
    vocabulary: Vocabulary,
) -> bool:
    def _evaluate_simple_conditions(condition_spec: dict[str, Any]) -> bool:
        conditions: list[bool] = []

        parent_present = condition_spec.get('parent_present')
        if isinstance(parent_present, str):
            parent_nodes = _resolve_path_nodes(payload, parent_present)
            conditions.append(bool(parent_nodes))

        modalities_any_of = condition_spec.get('modalities_any_of')
        if isinstance(modalities_any_of, list):
            modality_values = _resolve_path_nodes(payload, 'modalities')
            has_match = False
            if modality_values and isinstance(modality_values[0].value, list):
                modality_ids = {
                    canonical
                    for value in modality_values[0].value
                    for canonical in [vocabulary.resolve_canonical('modalities', value) or value if isinstance(value, str) else None]
                    if isinstance(canonical, str)
                }
                targets = {str(v).strip() for v in modalities_any_of if isinstance(v, str)}
                has_match = bool(modality_ids & targets)
            conditions.append(has_match)

        scanner_type_in = condition_spec.get('scanner_type_in')
        if isinstance(scanner_type_in, list):
            scanner_nodes = _resolve_path_nodes(payload, 'hardware.scanner.type')
            scanner_type = scanner_nodes[0].value if scanner_nodes else None
            conditions.append(
                isinstance(scanner_type, str)
                and scanner_type in {str(v).strip() for v in scanner_type_in if isinstance(v, str)}
            )

        item_kind_in = condition_spec.get('item_kind_in')
        if isinstance(item_kind_in, list):
            kind = item_context.get('kind') if isinstance(item_context, dict) else None
            conditions.append(
                isinstance(kind, str)
                and kind in {str(v).strip() for v in item_kind_in if isinstance(v, str)}
            )

        modules_any_of = condition_spec.get('modules_any_of')
        if isinstance(modules_any_of, list):
            module_nodes = _resolve_path_nodes(payload, 'modules')
            has_module_match = False
            if module_nodes and isinstance(module_nodes[0].value, list):
                module_ids = {
                    canonical
                    for module in module_nodes[0].value
                    for raw_name in [module.get('name') if isinstance(module, dict) else None]
                    for canonical in [vocabulary.resolve_canonical('modules', raw_name) or raw_name if isinstance(raw_name, str) else None]
                    if isinstance(canonical, str)
                }
                targets = {str(v).strip() for v in modules_any_of if isinstance(v, str)}
                has_module_match = bool(module_ids & targets)
            conditions.append(has_module_match)

        detector_kinds_any_of = condition_spec.get('detector_kinds_any_of')
        if isinstance(detector_kinds_any_of, list):
            detector_nodes = _resolve_path_nodes(payload, 'hardware.detectors')
            has_detector_match = False
            if detector_nodes and isinstance(detector_nodes[0].value, list):
                detector_kinds = {
                    canonical
                    for detector in detector_nodes[0].value
                    for raw_kind in [detector.get('kind') if isinstance(detector, dict) else None]
                    for canonical in [vocabulary.resolve_canonical('detector_kinds', raw_kind) or raw_kind if isinstance(raw_kind, str) else None]
                    if isinstance(canonical, str)
                }
                targets = {str(v).strip() for v in detector_kinds_any_of if isinstance(v, str)}
                has_detector_match = bool(detector_kinds & targets)
            conditions.append(has_detector_match)

        if not conditions:
            return False
        return all(conditions)

    all_of = required_if.get('all_of')
    if isinstance(all_of, list):
        all_of_results = [
            _evaluate_required_if(condition, payload=payload, item_context=item_context, vocabulary=vocabulary)
            for condition in all_of
            if isinstance(condition, dict)
        ]
        if not all_of_results:
            return False
        if not all(all_of_results):
            return False

    any_of = required_if.get('any_of')
    if isinstance(any_of, list):
        any_of_results = [
            _evaluate_required_if(condition, payload=payload, item_context=item_context, vocabulary=vocabulary)
            for condition in any_of
            if isinstance(condition, dict)
        ]
        if not any_of_results or not any(any_of_results):
            return False

    simple_result = _evaluate_simple_conditions(required_if)
    has_simple_conditions = any(
        key in required_if
        for key in (
            'parent_present',
            'modalities_any_of',
            'scanner_type_in',
            'item_kind_in',
            'modules_any_of',
            'detector_kinds_any_of',
        )
    )

    if has_simple_conditions:
        return simple_result
    return isinstance(all_of, list) or isinstance(any_of, list)


def _evaluate_event_required_if(
    required_if: dict[str, Any],
    *,
    payload: dict[str, Any],
    item_context: dict[str, Any] | None,
) -> tuple[bool | None, str | None]:
    supported_keys = {
        'performed_contains_qc_type',
        'service_provider_in',
        'missing_legacy_event_id',
        'no_stability_series',
        'no_linearity_series',
        'missing_csv_artifact',
        'metrics_computed_present',
        'evaluation_present',
        'evaluation_computed_provenance_present',
    }
    unknown = [key for key in required_if if key not in supported_keys]
    if unknown:
        return None, f"Unsupported required_if condition(s): {', '.join(sorted(unknown))}."

    conditions: list[bool] = []

    if 'performed_contains_qc_type' in required_if:
        expected = required_if.get('performed_contains_qc_type')
        performed_nodes = _resolve_path_nodes(payload, 'performed[]')
        found = {
            item.value.get('qc_type')
            for item in performed_nodes
            if isinstance(item.value, dict) and isinstance(item.value.get('qc_type'), str)
        }
        conditions.append(isinstance(expected, str) and expected in found)

    if 'service_provider_in' in required_if:
        allowed = required_if.get('service_provider_in')
        provider = payload.get('service_provider')
        if not isinstance(allowed, list):
            return None, "Condition 'service_provider_in' must be a list."
        conditions.append(isinstance(provider, str) and provider in {str(v).strip() for v in allowed if isinstance(v, str)})

    if required_if.get('missing_legacy_event_id') is True:
        conditions.append(not _is_non_empty_string(payload.get('event_id')))

    if required_if.get('no_stability_series') is True:
        nodes = _resolve_path_nodes(payload, 'laser_inputs_human.stability_series')
        has_stability = bool(nodes and isinstance(nodes[0].value, list) and len(nodes[0].value) > 0)
        conditions.append(not has_stability)

    if required_if.get('no_linearity_series') is True:
        nodes = _resolve_path_nodes(payload, 'laser_inputs_human.linearity_series')
        has_linearity = bool(nodes and isinstance(nodes[0].value, list) and len(nodes[0].value) > 0)
        conditions.append(not has_linearity)

    if required_if.get('missing_csv_artifact') is True:
        if not isinstance(item_context, dict):
            conditions.append(False)
        else:
            csv_artifact = item_context.get('csv_artifact')
            conditions.append(not _is_non_empty_string(csv_artifact))

    if required_if.get('metrics_computed_present') is True:
        metrics_nodes = _resolve_path_nodes(payload, 'metrics_computed')
        has_metrics = bool(metrics_nodes and isinstance(metrics_nodes[0].value, list) and len(metrics_nodes[0].value) > 0)
        conditions.append(has_metrics)

    if required_if.get('evaluation_present') is True:
        evaluation_nodes = _resolve_path_nodes(payload, 'evaluation')
        has_evaluation = bool(evaluation_nodes and isinstance(evaluation_nodes[0].value, dict))
        conditions.append(has_evaluation)

    if required_if.get('evaluation_computed_provenance_present') is True:
        provenance_nodes = _resolve_path_nodes(payload, 'evaluation.computed_provenance')
        has_provenance = bool(provenance_nodes and isinstance(provenance_nodes[0].value, dict))
        conditions.append(has_provenance)

    if not conditions:
        return False, None

    return all(conditions), None


def _check_event_type(value: Any, field_type: str) -> bool:
    if field_type in {'string', 'text'}:
        return isinstance(value, str)
    if field_type == 'integer':
        return isinstance(value, int) and not isinstance(value, bool)
    if field_type == 'number':
        return _is_number(value)
    if field_type == 'scalar':
        return isinstance(value, (str, int, float, bool))
    if field_type == 'list':
        return isinstance(value, list)
    if field_type == 'mapping':
        return isinstance(value, dict)
    if field_type == 'enum':
        return _is_non_empty_string(value)
    if field_type == 'instrument_id':
        return _is_non_empty_string(value)
    if field_type == 'datetime_utc':
        return isinstance(value, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value.strip()))
    if field_type == 'date':
        return isinstance(value, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()))
    if field_type == 'date_or_text':
        return isinstance(value, str)
    if field_type in {'artifact_id', 'qc_id', 'maintenance_id', 'uri_or_repo_path'}:
        return _is_non_empty_string(value)
    return False


def _load_event_policy(policy_path: Path) -> tuple[EventPolicy | None, str | None]:
    payload, load_error = load_policy(policy_path)
    if load_error is not None or payload is None:
        return None, load_error

    record_type = payload.get('record_type')
    if not isinstance(record_type, str) or not record_type.strip():
        return None, f"Policy '{policy_path.as_posix()}' missing required string 'record_type'."

    field_rules = payload.get('field_rules')
    if not isinstance(field_rules, list):
        return None, f"Policy '{policy_path.as_posix()}' missing required list 'field_rules'."

    vocab_registry = payload.get('vocab_registry')
    if not isinstance(vocab_registry, dict):
        vocab_registry = {}

    legacy_rules = payload.get('legacy_and_migration_rules')
    if not isinstance(legacy_rules, list):
        legacy_rules = []
    cross_rules = payload.get('cross_field_rules')
    if not isinstance(cross_rules, list):
        cross_rules = []

    return EventPolicy(
        policy_path=policy_path,
        record_type=record_type.strip(),
        vocab_registry=vocab_registry,
        field_rules=[r for r in field_rules if isinstance(r, dict)],
        legacy_and_migration_rules=[r for r in legacy_rules if isinstance(r, dict)],
        cross_field_rules=[r for r in cross_rules if isinstance(r, dict)],
    ), None


def validate_instrument_ledgers(
    *,
    instruments_dir: Path = Path('instruments'),
) -> tuple[set[str], list[ValidationIssue], list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    instrument_ids: set[str] = set()
    instrument_id_to_files: dict[str, list[str]] = {}

    policy, policy_error = _load_instrument_policy()
    if policy_error is not None or policy is None:
        issues.append(
            ValidationIssue(
                code='instrument_policy_load_error',
                path='instrument_metadata_policy.yaml',
                message=policy_error or 'Unknown instrument policy loading error.',
            )
        )
        return instrument_ids, issues, warnings

    vocabulary = Vocabulary(vocab_registry=policy.vocab_registry)

    for instrument_file in _iter_yaml_files(instruments_dir):
        is_retired_instrument = 'retired' in instrument_file.parts

        payload, load_error = _load_yaml(instrument_file)
        if load_error is not None:
            issues.append(ValidationIssue(code='yaml_parse_error', path=instrument_file.as_posix(), message=load_error))
            continue
        if payload is None:
            continue

        for rule in policy.rules:
            resolved = _resolve_rule_nodes(payload, rule.path)

            if rule.aliases:
                for alias in rule.aliases:
                    alias_resolved = _resolve_rule_nodes(payload, alias)
                    if alias_resolved and not resolved:
                        warnings.append(
                            ValidationIssue(
                                code='field_alias_used',
                                path=f"{instrument_file.as_posix()}:{alias}",
                                message=f"Field '{alias}' is legacy alias for '{rule.path}'. Prefer canonical field.",
                            )
                        )

            if rule.superseded_by and resolved:
                warnings.append(
                    ValidationIssue(
                        code='field_superseded',
                        path=f"{instrument_file.as_posix()}:{rule.path}",
                        message=f"Field '{rule.path}' is superseded by '{rule.superseded_by}'. Please migrate.",
                    )
                )

            status = rule.status
            is_required = status == 'required'
            if status == 'conditional' and rule.required_if is not None:
                is_required = _evaluate_required_if(
                    rule.required_if,
                    payload=payload,
                    item_context=None,
                    vocabulary=vocabulary,
                )

            if is_required and not resolved:
                if is_retired_instrument:
                    continue
                warnings.append(
                    ValidationIssue(
                        code='missing_required_field',
                        path=f"{instrument_file.as_posix()}:{rule.path}",
                        message=f"Missing required field '{rule.path}' (reported for audit follow-up).",
                    )
                )
                continue

            if not resolved:
                continue

            for node in resolved:
                value = node.value
                full_path = f"{instrument_file.as_posix()}:{node.path}"

                if status == 'conditional' and rule.required_if is not None:
                    required_for_item = _evaluate_required_if(
                        rule.required_if,
                        payload=payload,
                        item_context=node.context_item,
                        vocabulary=vocabulary,
                    )
                    if required_for_item and value in (None, ''):
                        warnings.append(
                            ValidationIssue(
                                code='missing_conditional_field',
                                path=full_path,
                                message=(
                                    f"Field '{rule.path}' is required under current conditions "
                                    "(reported for audit follow-up)."
                                ),
                            )
                        )
                        continue

                if value in (None, ''):
                    continue

                if not _check_type(value, rule.field_type):
                    issues.append(
                        ValidationIssue(
                            code='invalid_field_type',
                            path=full_path,
                            message=f"Invalid type/content for '{rule.path}'. Expected {rule.field_type}.",
                        )
                    )
                    continue

                if rule.field_type == 'list' and isinstance(value, list) and isinstance(rule.min_items, int):
                    if len(value) < rule.min_items:
                        warnings.append(
                            ValidationIssue(
                                code='list_too_short',
                                path=full_path,
                                message=(
                                    f"List '{rule.path}' should contain at least {rule.min_items} item(s) "
                                    "(reported for audit follow-up)."
                                ),
                            )
                        )

                validation_error = _check_rule_validation(value, rule)
                if validation_error is not None:
                    warnings.append(
                        ValidationIssue(
                            code='validation_constraint_failed',
                            path=full_path,
                            message=(
                                f"Field '{rule.path}' {validation_error} "
                                "(reported for audit follow-up)."
                            ),
                        )
                    )

                if rule.vocab is not None:
                    vocab_values: list[tuple[Any, str]]
                    if isinstance(value, list):
                        vocab_values = [
                            (item, f"{full_path}[{index}]")
                            for index, item in enumerate(value)
                        ]
                    else:
                        vocab_values = [(value, full_path)]

                    for vocab_value, vocab_path in vocab_values:
                        is_match, suggestion = vocabulary.check(rule.vocab, vocab_value)
                        if is_match:
                            continue
                        if suggestion is not None:
                            warnings.append(
                                ValidationIssue(
                                    code='vocab_synonym_used',
                                    path=vocab_path,
                                    message=(
                                        f"Value '{vocab_value}' is a synonym in '{rule.vocab}'. Prefer canonical id '{suggestion}'."
                                    ),
                                )
                            )
                        else:
                            known = ', '.join(sorted(vocabulary.terms_by_vocab.get(rule.vocab, {}).keys()))
                            issues.append(
                                ValidationIssue(
                                    code='unknown_vocab_term',
                                    path=vocab_path,
                                    message=(
                                        f"Unknown value '{vocab_value}' for vocabulary '{rule.vocab}'. Use one of: {known}."
                                    ),
                                )
                            )

        instrument_section = payload.get('instrument')
        if not isinstance(instrument_section, dict):
            if is_retired_instrument:
                continue
            issues.append(
                ValidationIssue(
                    code='missing_instrument_section',
                    path=instrument_file.as_posix(),
                    message="Missing required top-level mapping key 'instrument'.",
                )
            )
            continue

        instrument_id = instrument_section.get('instrument_id')
        if not isinstance(instrument_id, str) or not instrument_id.strip():
            if is_retired_instrument:
                continue
            issues.append(
                ValidationIssue(
                    code='missing_instrument_id',
                    path=instrument_file.as_posix(),
                    message='Missing required instrument.instrument_id (must be a non-empty string).',
                )
            )
            continue

        instrument_id = instrument_id.strip()
        if not _is_valid_instrument_id(instrument_id):
            if is_retired_instrument:
                continue
            issues.append(
                ValidationIssue(
                    code='invalid_instrument_id',
                    path=instrument_file.as_posix(),
                    message=(
                        'Invalid instrument.instrument_id; expected URL-safe slug '
                        '(lowercase letters, numbers, and single hyphens only).'
                    ),
                )
            )
            continue

        instrument_ids.add(instrument_id)
        instrument_id_to_files.setdefault(instrument_id, []).append(instrument_file.as_posix())

    for instrument_id, source_files in sorted(instrument_id_to_files.items()):
        if len(source_files) <= 1:
            continue
        source_list = ', '.join(sorted(source_files))
        issues.append(
            ValidationIssue(
                code='duplicate_instrument_id',
                path=instrument_id,
                message=f"Duplicate instrument.instrument_id '{instrument_id}' defined in: {source_list}.",
            )
        )

    return instrument_ids, issues, warnings


def validate_event_ledgers(
    *,
    instrument_ids: set[str],
    qc_base_dir: Path = Path("qc/sessions"),
    maintenance_base_dir: Path = Path("maintenance/events"),
    allowed_record_types: Iterable[str] = DEFAULT_ALLOWED_RECORD_TYPES,
) -> EventValidationReport:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    migration_notices: list[ValidationIssue] = []
    event_output_to_sources: dict[str, list[str]] = {}
    allowed_types = {value.strip() for value in allowed_record_types if isinstance(value, str) and value.strip()}
    event_policies: dict[str, EventPolicy] = {}
    combined_registry: dict[str, dict[str, Any]] = {}
    for policy_path in (Path("schema/QC_policy.yaml"), Path("schema/maintenance_policy.yaml")):
        policy, policy_error = _load_event_policy(policy_path)
        if policy_error is not None or policy is None:
            errors.append(ValidationIssue(code='event_policy_load_error', path=policy_path.as_posix(), message=policy_error or 'Unknown event policy load error.'))
            continue
        event_policies[policy.record_type] = policy
        combined_registry.update(policy.vocab_registry)

    vocabulary = Vocabulary(vocab_registry=combined_registry or None)

    event_sources = [
        (qc_base_dir, "qc_session"),
        (maintenance_base_dir, "maintenance_event"),
    ]

    for base_dir, expected_type in event_sources:
        for event_file in _iter_yaml_files(base_dir):
            try:
                rel_parts = event_file.relative_to(base_dir).parts
            except ValueError:
                rel_parts = ()

            payload, load_error = _load_yaml(event_file)
            if load_error is not None:
                errors.append(
                    ValidationIssue(
                        code="yaml_parse_error",
                        path=event_file.as_posix(),
                        message=load_error,
                    )
                )
                continue

            if payload is None:
                continue

            microscope = payload.get("microscope")
            if not isinstance(microscope, str) or not microscope.strip():
                errors.append(
                    ValidationIssue(
                        code="missing_microscope",
                        path=event_file.as_posix(),
                        message="Missing required 'microscope' field.",
                    )
                )
                continue

            if microscope not in instrument_ids:
                known = ", ".join(sorted(instrument_ids))
                errors.append(
                    ValidationIssue(
                        code="unknown_microscope",
                        path=event_file.as_posix(),
                        message=(
                            f"Unknown microscope '{microscope}'. "
                            f"Expected one of instrument IDs in registry: {known}."
                        ),
                    )
                )

            if len(rel_parts) < 3:
                errors.append(
                    ValidationIssue(
                        code="invalid_event_path_structure",
                        path=event_file.as_posix(),
                        message=(
                            f"Expected event path under '{base_dir.as_posix()}' to follow "
                            "'<microscope>/<YYYY>/<file>.yaml'."
                        ),
                    )
                )
            else:
                path_microscope = rel_parts[0]
                path_year = rel_parts[1]

                if microscope != path_microscope:
                    errors.append(
                        ValidationIssue(
                            code="microscope_mismatch_with_path",
                            path=event_file.as_posix(),
                            message=(
                                f"Path microscope '{path_microscope}' does not match payload "
                                f"microscope '{microscope}'."
                            ),
                        )
                    )

                if not YEAR_PATTERN.fullmatch(path_year):
                    errors.append(
                        ValidationIssue(
                            code="invalid_event_year_folder",
                            path=event_file.as_posix(),
                            message=(
                                f"Invalid year folder '{path_year}'. Expected a 4-digit year "
                                "like '2026'."
                            ),
                        )
                    )
                else:
                    event_year = _get_started_year(payload, event_file)
                    if event_year is None:
                        errors.append(
                            ValidationIssue(
                                code="missing_event_year_source",
                                path=event_file.as_posix(),
                                message=(
                                    "Could not derive event year from payload.started_utc or "
                                    "filename date prefix (YYYY-MM-DD_...)."
                                ),
                            )
                        )
                    elif path_year != event_year:
                        errors.append(
                            ValidationIssue(
                                code="year_mismatch_with_path",
                                path=event_file.as_posix(),
                                message=(
                                    f"Path year '{path_year}' does not match derived event "
                                    f"year '{event_year}' from started_utc/filename."
                                ),
                            )
                        )

            record_type = payload.get("record_type")
            if not isinstance(record_type, str) or not record_type.strip():
                errors.append(
                    ValidationIssue(
                        code="missing_record_type",
                        path=event_file.as_posix(),
                        message="Missing required 'record_type' field.",
                    )
                )
            elif record_type not in allowed_types:
                allowed = ", ".join(sorted(allowed_types))
                errors.append(
                    ValidationIssue(
                        code="invalid_record_type",
                        path=event_file.as_posix(),
                        message=f"Invalid record_type '{record_type}'. Allowed values: {allowed}.",
                    )
                )
            elif record_type != expected_type:
                errors.append(
                    ValidationIssue(
                        code="unexpected_record_type_for_location",
                        path=event_file.as_posix(),
                        message=(
                            f"record_type '{record_type}' does not match expected value "
                            f"'{expected_type}' for files under '{base_dir.as_posix()}'."
                        ),
                    )
                )

            policy = event_policies.get(record_type) if isinstance(record_type, str) else None
            if policy is None:
                errors.append(ValidationIssue(code='missing_policy_for_record_type', path=event_file.as_posix(), message=f"No event policy loaded for record_type '{record_type}'."))
                continue

            allowed_roots = set()
            for rule in policy.field_rules:
                path_value = rule.get('path')
                if isinstance(path_value, str) and path_value:
                    allowed_roots.add(path_value.split('.')[0].replace('[]', ''))
            for legacy in policy.legacy_and_migration_rules:
                legacy_path = legacy.get('path')
                if isinstance(legacy_path, str) and legacy_path:
                    allowed_roots.add(legacy_path.split('.')[0])
            for top_key in payload:
                if top_key not in allowed_roots:
                    warnings.append(ValidationIssue(code='unsupported_event_field', path=f"{event_file.as_posix()}:{top_key}", message=f"Field '{top_key}' is not declared in policy '{policy.policy_path.as_posix()}'."))

            for rule in policy.field_rules:
                path_value = rule.get('path')
                status = rule.get('status')
                field_type = rule.get('type')
                if not isinstance(path_value, str) or not isinstance(status, str) or not isinstance(field_type, str):
                    warnings.append(ValidationIssue(code='invalid_policy_field_rule', path=policy.policy_path.as_posix(), message=f"Invalid field rule entry: {rule}."))
                    continue

                resolved = _resolve_path_nodes(payload, path_value)
                required = status == 'required'
                if status == 'conditionally_required':
                    required_if = rule.get('required_if')
                    if not isinstance(required_if, dict):
                        warnings.append(ValidationIssue(code='unsupported_required_if_condition', path=policy.policy_path.as_posix(), message=f"Conditionally required rule '{path_value}' is missing required_if mapping."))
                        continue
                    required_eval, condition_error = _evaluate_event_required_if(required_if, payload=payload, item_context=None)
                    if condition_error is not None or required_eval is None:
                        warnings.append(ValidationIssue(code='unsupported_required_if_condition', path=policy.policy_path.as_posix(), message=condition_error or f"Unsupported required_if for '{path_value}'."))
                        continue
                    required = required_eval
                elif status not in {'required', 'optional', 'legacy_alias'}:
                    warnings.append(ValidationIssue(code='unsupported_field_status', path=policy.policy_path.as_posix(), message=f"Unsupported field status '{status}' for path '{path_value}'."))
                    continue

                if required and not resolved:
                    parent_path = path_value.rsplit('.', 1)[0] if '.' in path_value else ''
                    if parent_path:
                        parent_nodes = _resolve_path_nodes(payload, parent_path)
                        if not parent_nodes:
                            continue
                    warnings.append(ValidationIssue(code='missing_required_field', path=f"{event_file.as_posix()}:{path_value}", message=f"Missing required field '{path_value}'."))
                    continue

                allowed_values = rule.get('allowed_values')
                pattern = rule.get('pattern')
                min_items = rule.get('min_items') if isinstance(rule.get('min_items'), int) else None
                vocab_name = rule.get('vocab') if isinstance(rule.get('vocab'), str) else None
                for node in resolved:
                    full_path = f"{event_file.as_posix()}:{node.path}"
                    if not _check_event_type(node.value, field_type):
                        warnings.append(ValidationIssue(code='invalid_field_type', path=full_path, message=f"Invalid value for '{path_value}'. Expected type '{field_type}'."))
                        continue
                    if isinstance(allowed_values, list) and node.value not in allowed_values:
                        warnings.append(ValidationIssue(code='invalid_allowed_value', path=full_path, message=f"Value '{node.value}' is not in allowed_values for '{path_value}'."))
                    if isinstance(pattern, str) and isinstance(node.value, str) and not re.fullmatch(pattern, node.value.strip()):
                        warnings.append(ValidationIssue(code='invalid_pattern', path=full_path, message=f"Value '{node.value}' does not match pattern for '{path_value}'."))
                    if isinstance(min_items, int) and isinstance(node.value, list) and len(node.value) < min_items:
                        warnings.append(ValidationIssue(code='list_too_short', path=full_path, message=f"List '{path_value}' must have at least {min_items} item(s)."))
                    if vocab_name is not None:
                        values = node.value if isinstance(node.value, list) else [node.value]
                        for vocab_value in values:
                            is_match, suggestion = vocabulary.check(vocab_name, vocab_value)
                            if is_match:
                                continue
                            if suggestion is not None:
                                warnings.append(ValidationIssue(code='vocab_synonym_used', path=full_path, message=f"Value '{vocab_value}' maps to canonical '{suggestion}' in vocab '{vocab_name}'."))
                            else:
                                warnings.append(ValidationIssue(code='unknown_vocab_term', path=full_path, message=f"Unknown value '{vocab_value}' for vocabulary '{vocab_name}'."))

            for legacy_rule in policy.legacy_and_migration_rules:
                legacy_path = legacy_rule.get('path')
                if not isinstance(legacy_path, str):
                    continue
                if _resolve_path_nodes(payload, legacy_path):
                    replacement = legacy_rule.get('migrate_to') or legacy_rule.get('replacement')
                    message = legacy_rule.get('migration_prompt') if isinstance(legacy_rule.get('migration_prompt'), str) else None
                    default_message = f"Legacy field '{legacy_path}' is present." + (f" Migrate to '{replacement}'." if isinstance(replacement, str) else "")
                    migration_notices.append(ValidationIssue(code='legacy_field_present', path=f"{event_file.as_posix()}:{legacy_path}", message=message or default_message))

            for cross_rule in policy.cross_field_rules:
                rule_id = cross_rule.get('id')
                if not isinstance(rule_id, str):
                    continue
                if rule_id.endswith('_path_consistency'):
                    if len(rel_parts) >= 1 and microscope != rel_parts[0]:
                        warnings.append(ValidationIssue(code='cross_field_rule_failed', path=event_file.as_posix(), message=f"Cross-field rule '{rule_id}' failed: microscope/path mismatch."))
                elif rule_id.endswith('_year_consistency'):
                    if len(rel_parts) >= 2 and YEAR_PATTERN.fullmatch(rel_parts[1]):
                        event_year = _get_started_year(payload, event_file)
                        if event_year is not None and rel_parts[1] != event_year:
                            warnings.append(ValidationIssue(code='cross_field_rule_failed', path=event_file.as_posix(), message=f"Cross-field rule '{rule_id}' failed: year mismatch."))
                elif rule_id == 'exactly_one_primary_id':
                    if (_is_non_empty_string(payload.get('maintenance_id')) + _is_non_empty_string(payload.get('event_id'))) != 1:
                        warnings.append(ValidationIssue(code='cross_field_rule_failed', path=event_file.as_posix(), message="Cross-field rule 'exactly_one_primary_id' failed."))
                elif rule_id == 'external_provider_requires_company':
                    if payload.get('service_provider') in {'vendor', 'distributor', 'third_party'} and not _is_non_empty_string(payload.get('company')):
                        warnings.append(ValidationIssue(code='cross_field_rule_failed', path=event_file.as_posix(), message="Cross-field rule 'external_provider_requires_company' failed."))
                elif rule_id == 'laser_qc_requires_structured_series':
                    performed_types = {
                        item.value.get('qc_type')
                        for item in _resolve_path_nodes(payload, 'performed[]')
                        if isinstance(item.value, dict) and isinstance(item.value.get('qc_type'), str)
                    }
                    if 'laser_power' in performed_types:
                        series_paths = (
                            'laser_inputs_human.linearity_series',
                            'laser_inputs_human.stability_series',
                            'laser_inputs_human.single_point_measurements',
                        )
                        has_data = False
                        for series_path in series_paths:
                            nodes = _resolve_path_nodes(payload, series_path)
                            if nodes and isinstance(nodes[0].value, list) and nodes[0].value:
                                has_data = True
                                break
                        if not has_data:
                            warnings.append(ValidationIssue(code='cross_field_rule_failed', path=event_file.as_posix(), message="Cross-field rule 'laser_qc_requires_structured_series' failed."))
                elif rule_id == 'artifacts_should_resolve':
                    artifact_ids = {
                        item.value
                        for item in _resolve_path_nodes(payload, 'artifacts[].artifact_id')
                        if isinstance(item.value, str) and item.value.strip()
                    }
                    ref_paths = [
                        'performed[].artifacts[]',
                        'laser_inputs_human.linearity_series[].csv_artifact',
                        'laser_inputs_human.stability_series[].csv_artifact',
                    ]
                    for ref_path in ref_paths:
                        for ref_node in _resolve_path_nodes(payload, ref_path):
                            if isinstance(ref_node.value, str) and ref_node.value.strip() and ref_node.value not in artifact_ids:
                                warnings.append(ValidationIssue(code='cross_field_rule_failed', path=f"{event_file.as_posix()}:{ref_node.path}", message=f"Cross-field rule 'artifacts_should_resolve' failed: unknown artifact id '{ref_node.value}'."))
                elif rule_id == 'related_qc_should_reference_existing_sessions':
                    for related_node in _resolve_path_nodes(payload, 'related_qc[]'):
                        if isinstance(related_node.value, str) and related_node.value.strip() and related_node.value.startswith('qc_'):
                            continue
                        warnings.append(ValidationIssue(code='cross_field_rule_failed', path=f"{event_file.as_posix()}:{related_node.path}", message="Cross-field rule 'related_qc_should_reference_existing_sessions' failed."))
                elif rule_id == 'next_due_date_should_pair_with_followup':
                    has_followup = _is_non_empty_string(payload.get('followup'))
                    has_next_due = _is_non_empty_string(payload.get('next_due_date'))
                    if has_followup and not has_next_due:
                        warnings.append(ValidationIssue(code='cross_field_rule_warning', path=event_file.as_posix(), message="Cross-field rule 'next_due_date_should_pair_with_followup': next_due_date is recommended when followup is present."))
                elif rule_id == 'metric_class_matches_id_pattern':
                    # Ensures the assigned metric_class logically matches the metric_id text.
                    for section in ('inputs_human', 'metrics_computed'):
                        nodes = _resolve_path_nodes(payload, f"{section}[]")
                        for node in nodes:
                            if not isinstance(node.value, dict):
                                continue
                            m_id = str(node.value.get('metric_id', '')).lower()
                            m_class = str(node.value.get('metric_class', ''))

                            mismatches = [
                                (m_class == 'fwhm_lateral' and 'power' in m_id),
                                (m_class == 'laser_power' and 'fwhm' in m_id),
                                (m_class == 'stage_repeatability' and 'noise' in m_id),
                            ]
                            if any(mismatches):
                                warnings.append(
                                    ValidationIssue(
                                        code='metric_class_pattern_mismatch',
                                        path=f"{event_file.as_posix()}:{node.path}",
                                        message=(
                                            f"Cross-field rule '{rule_id}' failed: metric_class "
                                            f"'{m_class}' contradicts metric_id '{m_id}'."
                                        ),
                                    )
                                )
                elif rule_id == 'evaluation_is_machine_written':
                    # Supported rule with no machine-author metadata available in ledgers yet.
                    continue
                else:
                    warnings.append(ValidationIssue(code='unsupported_cross_field_rule', path=policy.policy_path.as_posix(), message=f"Unsupported cross_field_rules id '{rule_id}'."))

            output_rel_path = f"events/{microscope}/{event_file.stem}.md"
            event_output_to_sources.setdefault(output_rel_path, []).append(event_file.as_posix())

    for output_rel_path, source_files in sorted(event_output_to_sources.items()):
        if len(source_files) <= 1:
            continue
        source_list = ", ".join(sorted(source_files))
        errors.append(
            ValidationIssue(
                code="duplicate_event_output_path",
                path=output_rel_path,
                message=f"Duplicate generated event path '{output_rel_path}' from: {source_list}.",
            )
        )

    return EventValidationReport(errors=errors, warnings=warnings, migration_notices=migration_notices)


def print_validation_report(issues: list[ValidationIssue], *, report_name: str = "failures") -> None:
    if not issues:
        return

    print(f"\nValidation {report_name} detected:", file=sys.stderr)
    for index, issue in enumerate(issues, start=1):
        print(f"  {index}. [{issue.code}] {issue.path}", file=sys.stderr)
        print(f"     {issue.message}", file=sys.stderr)
    print(f"\nTotal validation {report_name}: {len(issues)}", file=sys.stderr)


def main() -> int:
    instrument_ids, issues, warnings = validate_instrument_ledgers()
    event_report = validate_event_ledgers(instrument_ids=instrument_ids)
    issues.extend(event_report.errors)
    warnings.extend(event_report.warnings)

    if warnings:
        print_validation_report(warnings, report_name="warnings")

    if event_report.migration_notices:
        print_validation_report(event_report.migration_notices, report_name='migration notices')

    if issues:
        print_validation_report(issues)
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
