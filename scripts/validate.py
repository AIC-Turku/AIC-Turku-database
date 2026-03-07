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
                raw_file = vocab_spec.get("file")
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
    title: str | None = None
    validation: dict[str, Any] | None = None
    vocab: str | None = None
    required_if: dict[str, Any] | None = None
    aliases: list[str] | None = None
    superseded_by: str | None = None
    min_items: int | None = None


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

        try:
            raw_text = candidate.read_text(encoding='utf-8')
        except OSError as exc:
            return None, f"Failed loading policy '{candidate.as_posix()}': {exc}"

        try:
            loaded_payload = yaml.safe_load(raw_text)
        except yaml.YAMLError:
            try:
                loaded_payload = yaml.safe_load(_sanitize_policy_yaml(raw_text))
            except yaml.YAMLError as exc:
                return None, f"Failed loading policy '{candidate.as_posix()}': {exc}"

        if loaded_payload is None:
            return None, f"Failed loading policy '{candidate.as_posix()}': YAML document is empty."
        if not isinstance(loaded_payload, dict):
            return None, (
                f"Failed loading policy '{candidate.as_posix()}': expected YAML mapping/object at top level, "
                f"found {type(loaded_payload).__name__}."
            )

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
                    title=raw_rule.get('title') if isinstance(raw_rule.get('title'), str) else None,
                    validation=raw_rule.get('validation') if isinstance(raw_rule.get('validation'), dict) else None,
                    vocab=raw_rule.get('vocab') if isinstance(raw_rule.get('vocab'), str) else None,
                    required_if=raw_rule.get('required_if') if isinstance(raw_rule.get('required_if'), dict) else None,
                    aliases=raw_rule.get('aliases') if isinstance(raw_rule.get('aliases'), list) else None,
                    superseded_by=raw_rule.get('superseded_by') if isinstance(raw_rule.get('superseded_by'), str) else None,
                    min_items=raw_rule.get('min_items') if isinstance(raw_rule.get('min_items'), int) else None,
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


def _check_type(value: Any, field_type: str) -> bool:
    if field_type in {'string', 'text'}:
        return _is_non_empty_string(value)
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
    parent_present = required_if.get('parent_present')
    if isinstance(parent_present, str):
        parent_nodes = _resolve_path_nodes(payload, parent_present)
        if parent_nodes:
            return True

    modalities_any_of = required_if.get('modalities_any_of')
    if isinstance(modalities_any_of, list):
        modality_values = _resolve_path_nodes(payload, 'modalities')
        if modality_values and isinstance(modality_values[0].value, list):
            modality_ids = {
                canonical
                for value in modality_values[0].value
                for canonical in [vocabulary.resolve_canonical('modalities', value) or value if isinstance(value, str) else None]
                if isinstance(canonical, str)
            }
            targets = {str(v).strip() for v in modalities_any_of if isinstance(v, str)}
            if modality_ids & targets:
                return True

    scanner_type_in = required_if.get('scanner_type_in')
    if isinstance(scanner_type_in, list):
        scanner_nodes = _resolve_path_nodes(payload, 'hardware.scanner.type')
        scanner_type = scanner_nodes[0].value if scanner_nodes else None
        if isinstance(scanner_type, str) and scanner_type in {str(v).strip() for v in scanner_type_in if isinstance(v, str)}:
            return True

    item_kind_in = required_if.get('item_kind_in')
    if isinstance(item_kind_in, list) and isinstance(item_context, dict):
        kind = item_context.get('kind')
        if isinstance(kind, str) and kind in {str(v).strip() for v in item_kind_in if isinstance(v, str)}:
            return True

    return False


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
            resolved = _resolve_path_nodes(payload, rule.path)

            if rule.aliases:
                for alias in rule.aliases:
                    alias_resolved = _resolve_path_nodes(payload, alias)
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
                        issues.append(
                            ValidationIssue(
                                code='list_too_short',
                                path=full_path,
                                message=f"List '{rule.path}' must contain at least {rule.min_items} item(s).",
                            )
                        )

                validation_error = _check_rule_validation(value, rule)
                if validation_error is not None:
                    issues.append(
                        ValidationIssue(
                            code='validation_constraint_failed',
                            path=full_path,
                            message=f"Field '{rule.path}' {validation_error}.",
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
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    event_output_to_sources: dict[str, list[str]] = {}
    allowed_types = {value.strip() for value in allowed_record_types if isinstance(value, str) and value.strip()}
    vocabulary = Vocabulary()

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
                issues.append(
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
                issues.append(
                    ValidationIssue(
                        code="missing_microscope",
                        path=event_file.as_posix(),
                        message="Missing required 'microscope' field.",
                    )
                )
                continue

            if microscope not in instrument_ids:
                known = ", ".join(sorted(instrument_ids))
                issues.append(
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
                issues.append(
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
                    issues.append(
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
                    issues.append(
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
                        issues.append(
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
                        issues.append(
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
                issues.append(
                    ValidationIssue(
                        code="missing_record_type",
                        path=event_file.as_posix(),
                        message="Missing required 'record_type' field.",
                    )
                )
            elif record_type not in allowed_types:
                allowed = ", ".join(sorted(allowed_types))
                issues.append(
                    ValidationIssue(
                        code="invalid_record_type",
                        path=event_file.as_posix(),
                        message=f"Invalid record_type '{record_type}'. Allowed values: {allowed}.",
                    )
                )
            elif record_type != expected_type:
                issues.append(
                    ValidationIssue(
                        code="unexpected_record_type_for_location",
                        path=event_file.as_posix(),
                        message=(
                            f"record_type '{record_type}' does not match expected value "
                            f"'{expected_type}' for files under '{base_dir.as_posix()}'."
                        ),
                    )
                )

            if record_type == "maintenance_event":
                required_maintenance_fields = (
                    "started_utc",
                    "service_provider",
                    "reason_details",
                    "action",
                )
                for field_name in required_maintenance_fields:
                    if _is_non_empty_string(payload.get(field_name)):
                        continue
                    issues.append(
                        ValidationIssue(
                            code="missing_maintenance_field",
                            path=event_file.as_posix(),
                            message=(
                                f"Missing required maintenance field '{field_name}' "
                                "(must be a non-empty string)."
                            ),
                        )
                    )

                has_maintenance_id = _is_non_empty_string(payload.get("maintenance_id"))
                has_event_id = _is_non_empty_string(payload.get("event_id"))
                if has_maintenance_id == has_event_id:
                    issues.append(
                        ValidationIssue(
                            code="invalid_maintenance_id_shape",
                            path=event_file.as_posix(),
                            message=(
                                "Maintenance events must include exactly one ID field: "
                                "either 'maintenance_id' or 'event_id'."
                            ),
                        )
                    )

                for status_key in ("microscope_status_before", "microscope_status_after"):
                    raw_status = payload.get(status_key)
                    if raw_status is None:
                        continue
                    if not _is_non_empty_string(raw_status):
                        issues.append(
                            ValidationIssue(
                                code="invalid_maintenance_status",
                                path=event_file.as_posix(),
                                message=(
                                    f"Invalid {status_key}: expected a non-empty string from "
                                    "the 'maintenance_status' vocabulary."
                                ),
                            )
                        )
                        continue

                    cleaned_status = raw_status.strip()
                    is_match, suggestion = vocabulary.check("maintenance_status", cleaned_status)
                    if is_match:
                        continue

                    if suggestion is not None:
                        issues.append(
                            ValidationIssue(
                                code="invalid_maintenance_status",
                                path=event_file.as_posix(),
                                message=(
                                    f"Invalid {status_key} '{raw_status}'. "
                                    f"Use canonical value '{suggestion}'."
                                ),
                            )
                        )
                        continue

                    known = ", ".join(sorted(vocabulary.terms_by_vocab.get("maintenance_status", {}).keys()))
                    issues.append(
                        ValidationIssue(
                            code="invalid_maintenance_status",
                            path=event_file.as_posix(),
                            message=(
                                f"Invalid {status_key} '{raw_status}'. "
                                f"Allowed values from maintenance_status vocabulary: {known}."
                            ),
                        )
                    )

            output_rel_path = f"events/{microscope}/{event_file.stem}.md"
            event_output_to_sources.setdefault(output_rel_path, []).append(event_file.as_posix())

    for output_rel_path, source_files in sorted(event_output_to_sources.items()):
        if len(source_files) <= 1:
            continue
        source_list = ", ".join(sorted(source_files))
        issues.append(
            ValidationIssue(
                code="duplicate_event_output_path",
                path=output_rel_path,
                message=f"Duplicate generated event path '{output_rel_path}' from: {source_list}.",
            )
        )

    return issues


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
    issues.extend(validate_event_ledgers(instrument_ids=instrument_ids))

    if warnings:
        print_validation_report(warnings, report_name="warnings")

    if issues:
        print_validation_report(issues)
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
