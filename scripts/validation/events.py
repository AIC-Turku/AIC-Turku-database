from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Iterable

from scripts.validation.io import _iter_yaml_files, _is_non_empty_string, _is_number, _load_yaml
from scripts.validation.model import EventValidationReport, ValidationIssue
from scripts.validation.policy import _evaluate_event_required_if, _load_event_policy, _resolve_path_nodes
from scripts.validation.vocabulary import Vocabulary

DEFAULT_ALLOWED_RECORD_TYPES: tuple[str, ...] = ("qc_session", "maintenance_event")
YEAR_PATTERN = re.compile(r"^\d{4}$")
ISO_YEAR_PATTERN = re.compile(r"^(\d{4})-")
FILENAME_DATE_PATTERN = re.compile(r"^(\d{4})-\d{2}-\d{2}(?:_|$)")


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

