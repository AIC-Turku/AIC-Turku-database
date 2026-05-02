from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import re

from scripts.validation.events import YEAR_PATTERN
from scripts.validation.model import InstrumentCompletenessReport, PolicyRule, ValidationIssue
from scripts.lightpath.parse_canonical import canonicalize_light_path_model
from scripts.lightpath.validate_contract import validate_filter_cube_warnings, validate_light_path, validate_light_path_warnings
from scripts.validation.io import _iter_yaml_files, _is_non_empty_string, _is_number, _load_yaml
from scripts.validation.policy import (
    _build_item_field_vocab_index,
    _context_item_alias_present,
    _evaluate_required_if,
    _get_software_roles,
    _list_context_path,
    _load_instrument_policy,
    _nodes_have_present_value,
    _resolve_rule_nodes,
    _resolve_path_nodes,
)
from scripts.validation.vocabulary import Vocabulary

INSTRUMENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")


def _is_valid_instrument_id(value: str) -> bool:
    return bool(INSTRUMENT_ID_PATTERN.fullmatch(value))



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
    item_field_vocab_index = _build_item_field_vocab_index(policy.rules)
    sections: dict[tuple[str | None, str | None], list[dict[str, Any]]] = {}
    missing_required: list[dict[str, Any]] = []
    missing_conditional: list[dict[str, Any]] = []
    alias_fallbacks: list[dict[str, Any]] = []

    def _missing_entry(rule: PolicyRule, *, alias_hits: list[str] | None = None, condition_triggered: bool = False) -> dict[str, Any]:
        return {
            'path': rule.path,
            'title': rule.title or rule.path,
            'status': rule.status,
            'section_id': rule.section_id,
            'section_title': rule.section_title or rule.section_id or 'Section',
            'used_by': list(rule.used_by) if rule.used_by is not None else [],
            'aliases': list(rule.aliases) if rule.aliases is not None else [],
            'alias_used': bool(alias_hits),
            'condition_triggered': condition_triggered,
        }

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
                missing_required.append(_missing_entry(rule, alias_hits=alias_hits))
        elif rule.status == 'conditional' and rule.required_if is not None:
            condition_triggered = _evaluate_required_if(
                rule.required_if,
                payload=payload,
                item_context=None,
                vocabulary=vocabulary,
                item_field_vocabs=item_field_vocab_index.get(_list_context_path(rule.path) or ''),
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
                        item_field_vocabs=item_field_vocab_index.get(_list_context_path(rule.path) or ''),
                    ):
                        missing = True
                        break
            if missing:
                missing_conditional.append(_missing_entry(rule, alias_hits=alias_hits, condition_triggered=condition_triggered))

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



_NAME_MODEL_REDUNDANCY_PATHS: tuple[str, ...] = (
    'hardware.sources',
    'hardware.detectors',
    'hardware.objectives',
    'hardware.optical_modulators',
    'hardware.illumination_logic',
    'hardware.magnification_changers',
    'hardware.stages',
    'hardware.endpoints',
    'hardware.optical_path_elements',
)

_PRODUCT_CODE_REDUNDANCY_PATHS: tuple[str, ...] = (
    'hardware.sources',
    'hardware.detectors',
    'hardware.objectives',
    'hardware.optical_path_elements',
)

_LEGACY_INSTRUMENT_TOPOLOGY_PATHS: tuple[str, ...] = (
    'hardware.light_sources',
    'hardware.light_path.endpoints',
    'hardware.light_path.splitters',
    'hardware.light_path.cube_mechanisms',
    'hardware.light_path.excitation_mechanisms',
    'hardware.light_path.dichroic_mechanisms',
    'hardware.light_path.emission_mechanisms',
)

def _append_name_model_redundancy_warnings(
    warnings: list[ValidationIssue],
    payload: dict[str, Any],
    instrument_file: Path,
) -> None:
    """Warn when local display `name` duplicates structured `model`.

    `name` is a local/display label while `model` is the primary structured identity.
    If both are present and identical, `name` is redundant and increases semantic drift.
    """

    for path in _NAME_MODEL_REDUNDANCY_PATHS:
        for node in _resolve_path_nodes(payload, path):
            if not isinstance(node.value, list):
                continue
            for index, item in enumerate(node.value):
                if not isinstance(item, dict):
                    continue
                raw_name = item.get('name')
                raw_model = item.get('model')
                if not (isinstance(raw_name, str) and isinstance(raw_model, str)):
                    continue
                name = raw_name.strip()
                model = raw_model.strip()
                if not name or not model:
                    continue
                if name == model:
                    warnings.append(
                        ValidationIssue(
                            code='redundant_name_model',
                            path=f"{instrument_file.as_posix()}:{node.path}[{index}]",
                            message=(
                                "`name` duplicates `model`. Keep `model` for structured identity and "
                                "omit redundant `name` unless a distinct local display label is needed."
                            ),
                        )
                    )




def _build_canonical_instrument_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Overlay canonical v2 topology onto an instrument payload for cross-field checks."""
    canonical_model = canonicalize_light_path_model(payload if isinstance(payload, dict) else {})
    normalized = json.loads(json.dumps(payload))
    hardware = normalized.setdefault('hardware', {})
    hardware['sources'] = canonical_model['sources']
    hardware['optical_path_elements'] = canonical_model['optical_path_elements']
    hardware['endpoints'] = canonical_model['endpoints']
    normalized['light_paths'] = canonical_model['light_paths']
    return normalized


def _legacy_instrument_topology_paths(payload: dict[str, Any]) -> list[str]:
    return [path for path in _LEGACY_INSTRUMENT_TOPOLOGY_PATHS if _resolve_path_nodes(payload, path)]


def _append_product_code_redundancy_warnings(
    warnings: list[ValidationIssue],
    payload: dict[str, Any],
    instrument_file: Path,
) -> None:
    """Warn when product_code duplicates model or name.

    product_code should be a distinct catalog/SKU/reference code, not a mirror of model/name.
    """

    def _check_mapping(item: dict[str, Any], path: str) -> None:
        product_code = item.get('product_code')
        if not isinstance(product_code, str) or not product_code.strip():
            return
        pc = product_code.strip()
        for field in ('model', 'name'):
            raw = item.get(field)
            if isinstance(raw, str) and raw.strip() and raw.strip() == pc:
                warnings.append(
                    ValidationIssue(
                        code='redundant_product_code',
                        path=f"{instrument_file.as_posix()}:{path}",
                        message=(
                            f"`product_code` duplicates `{field}`. Keep `product_code` only for distinct "
                            "catalog/SKU/reference values."
                        ),
                    )
                )
                return

    for path in _PRODUCT_CODE_REDUNDANCY_PATHS:
        for node in _resolve_path_nodes(payload, path):
            if isinstance(node.value, list):
                for index, item in enumerate(node.value):
                    if isinstance(item, dict):
                        _check_mapping(item, f"{node.path}[{index}]")
            elif isinstance(node.value, dict):
                _check_mapping(node.value, node.path)


def _append_light_path_modality_warnings(
    warnings: list[ValidationIssue],
    payload: dict[str, Any],
    instrument_file: Path,
    vocabulary: Vocabulary,
    canonical_modalities: set[str],
    capabilities: dict[str, set[str]] | None = None,
) -> None:
    light_paths = payload.get('light_paths')
    if not isinstance(light_paths, list) or not light_paths:
        return

    capabilities = capabilities or {}
    required_route_coverage = set(canonical_modalities)
    required_route_coverage.update(capabilities.get('imaging_modes', set()))
    required_route_coverage.update(capabilities.get('contrast_methods', set()))

    covered_route_terms: set[str] = set()
    instrument_readouts = set(capabilities.get('readouts', set()))
    covered_readouts: set[str] = set()

    for index, light_path in enumerate(light_paths):
        if not isinstance(light_path, dict):
            continue

        route_id = light_path.get('id')
        route_label = route_id.strip() if isinstance(route_id, str) and route_id.strip() else f'light_paths[{index}]'
        route_path = f"{instrument_file.as_posix()}:light_paths[{index}]"
        route_type_raw = light_path.get('route_type')
        route_type = route_type_raw.strip() if isinstance(route_type_raw, str) and route_type_raw.strip() else ''
        route_key = route_type or (route_id.strip() if isinstance(route_id, str) and route_id.strip() else '')
        if route_key:
            resolved_route = vocabulary.resolve_canonical('optical_routes', route_key) or route_key
            covered_route_terms.add(resolved_route)

        raw_modalities = light_path.get('modalities')
        if raw_modalities is None:
            if not route_type:
                warnings.append(ValidationIssue(code='light_path_modalities_missing', path=route_path, message=(f"Instrument '{instrument_file.stem}' light path '{route_label}' is missing light_paths[].modalities; add a non-empty canonical modality list for this route or declare route_type.")))
        elif not isinstance(raw_modalities, list) or not raw_modalities:
            warnings.append(ValidationIssue(code='light_path_modalities_empty', path=f"{route_path}:modalities", message=(f"Instrument '{instrument_file.stem}' light path '{route_label}' has an empty or invalid modalities value; route modalities must be a non-empty YAML list.")))
        else:
            seen_modalities: set[str] = set()
            duplicate_modalities: set[str] = set()
            for modality_index, raw_value in enumerate(raw_modalities):
                if not isinstance(raw_value, str) or not raw_value.strip():
                    continue
                resolved_value = vocabulary.resolve_canonical('modalities', raw_value)
                raw_cleaned = raw_value.strip()
                known_modalities = vocabulary.valid_ids_by_vocab.get('modalities', set())
                if resolved_value is None and known_modalities and raw_cleaned not in known_modalities:
                    continue
                canonical_value = (resolved_value or raw_cleaned).strip()
                covered_route_terms.add(canonical_value)
                if canonical_value in seen_modalities:
                    duplicate_modalities.add(canonical_value)
                else:
                    seen_modalities.add(canonical_value)
                if canonical_modalities and canonical_value not in canonical_modalities:
                    warnings.append(ValidationIssue(code='light_path_modality_not_in_instrument', path=f"{route_path}:modalities[{modality_index}]", message=(f"Instrument '{instrument_file.stem}' light path '{route_label}' declares modality '{canonical_value}', but that value is not present in the instrument-level modalities list.")))
            for duplicate_value in sorted(duplicate_modalities):
                warnings.append(ValidationIssue(code='light_path_modalities_duplicate', path=f"{route_path}:modalities", message=(f"Instrument '{instrument_file.stem}' light path '{route_label}' repeats modality '{duplicate_value}' in light_paths[].modalities; keep each route modality only once.")))

        route_readouts = light_path.get('readouts')
        if isinstance(route_readouts, list):
            for readout in route_readouts:
                if isinstance(readout, str) and readout.strip():
                    canonical_readout = vocabulary.resolve_canonical('measurement_readouts', readout) or readout.strip()
                    covered_readouts.add(canonical_readout)

    for modality in sorted(required_route_coverage - covered_route_terms):
        warnings.append(ValidationIssue(code='top_level_modality_uncovered_by_light_paths', path=f"{instrument_file.as_posix()}:modalities", message=(f"Instrument '{instrument_file.stem}' top-level modality/capability '{modality}' is not covered by any light path route_type/id/modalities mapping; add an explicit route mapping or keep this as manual follow-up.")))

    for readout in sorted(instrument_readouts - covered_readouts):
        warnings.append(ValidationIssue(code='instrument_readout_uncovered_by_route_readouts', path=f"{instrument_file.as_posix()}:capabilities.readouts", message=(f"Instrument '{instrument_file.stem}' capability readout '{readout}' is not covered by any light_paths[].readouts entry.")))


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
    item_field_vocab_index = _build_item_field_vocab_index(policy.rules)

    for instrument_file in _iter_yaml_files(instruments_dir):
        file_issue_count_before = len(issues)
        is_retired_instrument = 'retired' in instrument_file.parts

        payload, load_error = _load_yaml(instrument_file)
        if load_error is not None:
            issues.append(ValidationIssue(code='yaml_parse_error', path=instrument_file.as_posix(), message=load_error))
            continue
        if payload is None:
            continue

        canonical_payload = _build_canonical_instrument_payload(payload)
        legacy_topology_paths = _legacy_instrument_topology_paths(payload)

        for legacy_path in legacy_topology_paths:
            warnings.append(
                ValidationIssue(
                    code='legacy_topology_present',
                    path=f"{instrument_file.as_posix()}:{legacy_path}",
                    message=(
                        f"Legacy topology field '{legacy_path}' is migration-only. "
                        "Migrate to canonical 'hardware.sources', "
                        "'hardware.optical_path_elements', 'hardware.endpoints', and 'light_paths'."
                    ),
                )
            )

        _append_name_model_redundancy_warnings(warnings, canonical_payload, instrument_file)
        _append_product_code_redundancy_warnings(warnings, canonical_payload, instrument_file)

        for rule in policy.rules:
            resolved = _resolve_rule_nodes(payload, rule.path)
            resolved_has_value = _nodes_have_present_value(resolved)
            alias_has_value = False

            if rule.aliases:
                for alias in rule.aliases:
                    alias_resolved = _resolve_rule_nodes(payload, alias)
                    alias_present = _nodes_have_present_value(alias_resolved)
                    alias_has_value = alias_has_value or alias_present
                    if alias_present and not resolved_has_value:
                        warnings.append(
                            ValidationIssue(
                                code='field_alias_used',
                                path=f"{instrument_file.as_posix()}:{alias}",
                                message=f"Field '{alias}' is legacy alias for '{rule.path}'. Prefer canonical field.",
                            )
                        )

            if rule.superseded_by and resolved_has_value:
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
                    item_field_vocabs=item_field_vocab_index.get(_list_context_path(rule.path) or ''),
                )

            if is_required and not (resolved_has_value or alias_has_value):
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
                        item_field_vocabs=item_field_vocab_index.get(_list_context_path(rule.path) or ''),
                    )
                    if required_for_item and value in (None, ''):
                        if _context_item_alias_present(rule, node.context_item):
                            continue
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

                if rule.field_type == 'list' and isinstance(value, list) and isinstance(rule.item_type, str):
                    for index, item in enumerate(value):
                        if _check_type(item, rule.item_type):
                            continue
                        issues.append(
                            ValidationIssue(
                                code='invalid_list_item_type',
                                path=f"{full_path}[{index}]",
                                message=(
                                    f"Invalid list item type/content for '{rule.path}'. "
                                    f"Expected item_type {rule.item_type}."
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


        for light_path_error in validate_light_path(payload):
            issues.append(
                ValidationIssue(
                    code='invalid_light_path',
                    path=instrument_file.as_posix(),
                    message=light_path_error,
                )
            )
        for light_path_warning in validate_light_path_warnings(payload):
            warnings.append(
                ValidationIssue(
                    code='light_path_endpoint_warning',
                    path=instrument_file.as_posix(),
                    message=light_path_warning,
                )
            )
        for cube_warning in validate_filter_cube_warnings(payload):
            warnings.append(
                ValidationIssue(
                    code='non_authoritative_filter_cube',
                    path=instrument_file.as_posix(),
                    message=cube_warning,
                )
            )

        detector_nodes = _resolve_path_nodes(canonical_payload, 'hardware.detectors')
        detector_kinds: set[str] = set()
        if detector_nodes and isinstance(detector_nodes[0].value, list):
            detector_kinds = {
                canonical
                for detector in detector_nodes[0].value
                for raw_kind in [detector.get('kind') if isinstance(detector, dict) else None]
                for canonical in [
                    vocabulary.resolve_canonical('detector_kinds', raw_kind) or raw_kind
                    if isinstance(raw_kind, str)
                    else None
                ]
                if isinstance(canonical, str)
            }

        digital_detector_kinds = {'scmos', 'cmos', 'ccd', 'emccd', 'pmt', 'gaasp_pmt', 'hyd', 'apd', 'spad'}
        has_digital_detector = bool(detector_kinds & digital_detector_kinds)

        software_roles = _get_software_roles(canonical_payload)
        software_status = str(canonical_payload.get("software_status") or "").strip().lower()
        software_entries = canonical_payload.get("software")
        has_software_entries = isinstance(software_entries, list) and len(software_entries) > 0

        if software_status == "not_applicable" and has_software_entries:
            warnings.append(
                ValidationIssue(
                    code='software_status_conflict',
                    path=instrument_file.as_posix(),
                    message=(
                        "software_status is 'not_applicable' but software[] contains entries; "
                        "either remove software entries or set software_status to 'documented'."
                    ),
                )
            )
        if software_status == "documented" and not has_software_entries:
            warnings.append(
                ValidationIssue(
                    code='software_status_conflict',
                    path=instrument_file.as_posix(),
                    message=(
                        "software_status is 'documented' but software[] is empty; "
                        "add software entries or set software_status to 'unknown' or 'not_applicable'."
                    ),
                )
            )

        has_acquisition_role = 'acquisition' in software_roles
        allow_not_applicable_without_acquisition = (
            software_status == "not_applicable" and not has_software_entries
        )
        if has_digital_detector and not has_acquisition_role and not allow_not_applicable_without_acquisition:
            if not is_retired_instrument:
                warnings.append(
                    ValidationIssue(
                        code='cross_field_rule_failed',
                        path=instrument_file.as_posix(),
                        message=(
                            "Cross-field rule 'detectors_require_acquisition_software_role' failed: "
                            "at least one software entry with role 'acquisition' is required when "
                            "digital detector kinds are present."
                        ),
                    )
                )

        modality_nodes = _resolve_path_nodes(canonical_payload, 'modalities')
        canonical_modalities: set[str] = set()
        if modality_nodes and isinstance(modality_nodes[0].value, list):
            canonical_modalities = {
                canonical
                for value in modality_nodes[0].value
                for canonical in [
                    vocabulary.resolve_canonical('modalities', value) or value
                    if isinstance(value, str)
                    else None
                ]
                if isinstance(canonical, str)
            }

        capabilities_raw = canonical_payload.get('capabilities') if isinstance(canonical_payload.get('capabilities'), dict) else {}
        policy_declares_capabilities = any(rule.path == 'capabilities' or rule.path.startswith('capabilities.') for rule in policy.rules)
        if policy_declares_capabilities and not is_retired_instrument and not capabilities_raw:
            warnings.append(
                ValidationIssue(
                    code='missing_capabilities_object',
                    path=f"{instrument_file.as_posix()}:capabilities",
                    message="Active instrument is missing canonical capabilities object; add capabilities.* axes explicitly instead of relying on legacy modalities.",
                )
            )
        capability_axes = {
            'imaging_modes': set(),
            'contrast_methods': set(),
            'readouts': set(),
            'workflows': set(),
            'assay_operations': set(),
            'non_optical': set(),
        }
        for axis in capability_axes:
            values = capabilities_raw.get(axis)
            if isinstance(values, list):
                capability_axes[axis] = {
                    (vocabulary.resolve_canonical('measurement_readouts' if axis == 'readouts' else axis if axis not in {'workflows','non_optical'} else ('workflow_tags' if axis=='workflows' else 'non_optical_capabilities'), value) or value)
                    for value in values if isinstance(value, str)
                }

        _append_light_path_modality_warnings(
            warnings=warnings,
            payload=payload,
            instrument_file=instrument_file,
            vocabulary=vocabulary,
            canonical_modalities=canonical_modalities,
            capabilities=capability_axes,
        )

        if 'sted' in canonical_modalities and not is_retired_instrument:
            source_nodes = _resolve_path_nodes(canonical_payload, 'hardware.sources[]')
            depletion_sources = [
                node.value
                for node in source_nodes
                if isinstance(node.value, dict)
                and str(node.value.get('role', '')).strip().casefold() == 'depletion'
            ]
            if not depletion_sources:
                warnings.append(
                    ValidationIssue(
                        code='sted_completeness_gap',
                        path=instrument_file.as_posix(),
                        message="STED completeness check: expected at least one canonical source with role='depletion'.",
                    )
                )
            if depletion_sources and not any(_is_non_empty_string(source.get('timing_mode')) for source in depletion_sources):
                warnings.append(
                    ValidationIssue(
                        code='sted_completeness_gap',
                        path=instrument_file.as_posix(),
                        message="STED completeness check: expected depletion source timing_mode metadata on canonical hardware.sources[].",
                    )
                )
            if not any(
                isinstance(detector, dict) and detector.get('supports_time_gating') is True
                for detector in (detector_nodes[0].value if detector_nodes and isinstance(detector_nodes[0].value, list) else [])
            ):
                warnings.append(
                    ValidationIssue(
                        code='sted_completeness_gap',
                        path=instrument_file.as_posix(),
                        message="STED completeness check: expected at least one detector with supports_time_gating=true.",
                    )
                )

        # Deprecated semantic heuristic removed from production validation flow:
        # do not infer tunable-source requirements from free-text notes.
        # Structured fields are enforced via policy rules (e.g., tunable_min_nm/tunable_max_nm).

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

        if len(issues) > file_issue_count_before:
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
