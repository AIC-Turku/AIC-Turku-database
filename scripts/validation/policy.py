from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import yaml

from scripts.validation.model import EventPolicy, InstrumentPolicy, PolicyRule, ResolvedNode
from scripts.validation.vocabulary import Vocabulary


def load_policy(policy_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw_text = policy_path.read_text(encoding='utf-8')
        payload = yaml.safe_load(raw_text)
    except (OSError, yaml.YAMLError) as exc:
        return None, f"Failed loading policy '{policy_path.as_posix()}': {exc}"

    if payload is None:
        return None, f"Failed loading policy '{policy_path.as_posix()}': YAML document is empty."
    if not isinstance(payload, dict):
        return None, (
            f"Failed loading policy '{policy_path.as_posix()}': expected YAML mapping/object at top level, "
            f"found {type(payload).__name__}."
        )
    return payload, None


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
                    item_type=raw_rule.get('item_type') if isinstance(raw_rule.get('item_type'), str) else None,
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
        is_map = segment.endswith('{}')
        key = segment[:-2] if (is_list or is_map) else segment
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
            elif is_map:
                if not isinstance(child, dict):
                    continue
                for map_key, item in child.items():
                    map_item_path = f"{child_path}.{map_key}"
                    ctx = item if isinstance(item, dict) else None
                    next_nodes.append(ResolvedNode(value=item, path=map_item_path, context_item=ctx))
            else:
                ctx = node.context_item if node.context_item is not None else (child if isinstance(child, dict) else None)
                next_nodes.append(ResolvedNode(value=child, path=child_path, context_item=ctx))
        nodes = next_nodes
        if not nodes:
            break
    return nodes


def _resolve_rule_nodes(payload: dict[str, Any], dotted_path: str) -> list[ResolvedNode]:
    if not dotted_path:
        return [ResolvedNode(value=payload, path='', context_item=None)]
    segments = dotted_path.split('.')
    if len(segments) == 1:
        segment = segments[0]
        if segment.endswith('[]') or segment.endswith('{}'):
            key = segment[:-2]
            if key in payload:
                return [ResolvedNode(value=payload.get(key), path=key, context_item=None)]
            return [ResolvedNode(value=None, path=key, context_item=None)]
        nodes = _resolve_path_nodes(payload, dotted_path)
        if nodes:
            return nodes
        return [ResolvedNode(value=None, path=segment, context_item=None)]

    parent_nodes = _resolve_path_nodes(payload, '.'.join(segments[:-1]))
    if not parent_nodes:
        return []
    leaf_segment = segments[-1]
    is_leaf_list = leaf_segment.endswith('[]')
    is_leaf_map = leaf_segment.endswith('{}')
    leaf_key = leaf_segment[:-2] if (is_leaf_list or is_leaf_map) else leaf_segment
    resolved_nodes: list[ResolvedNode] = []
    for parent in parent_nodes:
        if not isinstance(parent.value, dict):
            continue
        child_path = f"{parent.path}.{leaf_key}" if parent.path else leaf_key
        if leaf_key not in parent.value:
            resolved_nodes.append(ResolvedNode(value=None, path=child_path, context_item=parent.context_item if parent.context_item is not None else parent.value))
            continue
        child = parent.value.get(leaf_key)
        if is_leaf_list:
            if not isinstance(child, list):
                resolved_nodes.append(ResolvedNode(value=child, path=child_path, context_item=parent.context_item if parent.context_item is not None else parent.value))
                continue
            for idx, item in enumerate(child):
                ctx = item if isinstance(item, dict) else None
                resolved_nodes.append(ResolvedNode(value=item, path=f"{child_path}[{idx}]", context_item=ctx))
            continue
        if is_leaf_map:
            if not isinstance(child, dict):
                resolved_nodes.append(ResolvedNode(value=child, path=child_path, context_item=parent.context_item if parent.context_item is not None else parent.value))
                continue
            for map_key, item in child.items():
                item_path = f"{child_path}.{map_key}"
                ctx = item if isinstance(item, dict) else None
                resolved_nodes.append(ResolvedNode(value=item, path=item_path, context_item=ctx))
            continue
        ctx = parent.context_item if parent.context_item is not None else (child if isinstance(child, dict) else None)
        resolved_nodes.append(ResolvedNode(value=child, path=child_path, context_item=ctx))
    return resolved_nodes


def _nodes_have_present_value(nodes: list[ResolvedNode]) -> bool:
    return any(node.value not in (None, '') for node in nodes)


def _context_item_alias_present(rule: PolicyRule, context_item: Any) -> bool:
    if not isinstance(context_item, dict) or not rule.aliases:
        return False
    for alias in rule.aliases:
        if not isinstance(alias, str):
            continue
        leaf = alias.split('.')[-1].replace('[]', '').replace('{}', '')
        value = context_item.get(leaf)
        if isinstance(value, str) and value.strip():
            return True
        if value not in (None, '') and not isinstance(value, str):
            return True
    return False


def _parent_path_from_list_path(path: str) -> str:
    return path.replace('[]', '')


def _list_context_path(path: str) -> str | None:
    parts = [part for part in path.split('.') if part]
    for idx in range(len(parts) - 1, -1, -1):
        if parts[idx].endswith('[]') or parts[idx].endswith('{}'):
            return '.'.join(parts[: idx + 1])
    return None


def _build_item_field_vocab_index(rules: list[PolicyRule]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for rule in rules:
        if not isinstance(rule.vocab, str):
            continue
        list_context = _list_context_path(rule.path)
        if list_context is None:
            continue
        suffix = rule.path[len(list_context):].lstrip('.')
        if not suffix or '[]' in suffix or '.' in suffix:
            continue
        index.setdefault(list_context, {})[suffix] = rule.vocab
    return index


def _get_software_roles(payload: dict[str, Any]) -> set[str]:
    software_nodes = _resolve_path_nodes(payload, 'software')
    roles: set[str] = set()
    for node in software_nodes:
        software_value = node.value
        if isinstance(software_value, list):
            roles.update(str(item.get('role')).strip().lower() for item in software_value if isinstance(item, dict) and isinstance(item.get('role'), str))
        elif isinstance(software_value, dict):
            roles.update(str(role_key).strip().lower() for role_key in software_value.keys() if isinstance(role_key, str))
    return roles


def _evaluate_required_if(required_if: dict[str, Any], *, payload: dict[str, Any], item_context: dict[str, Any] | None, vocabulary: Vocabulary, item_field_vocabs: dict[str, str] | None = None) -> bool:
    def _normalize_scalar(value: Any) -> str | None:
        if isinstance(value, (str, int, float, bool)):
            return str(value).strip().casefold()
        return None
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
                modality_ids = {canonical for value in modality_values[0].value for canonical in [vocabulary.resolve_canonical('modalities', value) or value if isinstance(value, str) else None] if isinstance(canonical, str)}
                targets = {str(v).strip() for v in modalities_any_of if isinstance(v, str)}
                has_match = bool(modality_ids & targets)
            conditions.append(has_match)
        scanner_type_in = condition_spec.get('scanner_type_in')
        if isinstance(scanner_type_in, list):
            scanner_nodes = _resolve_path_nodes(payload, 'hardware.scanner.type')
            scanner_type = scanner_nodes[0].value if scanner_nodes else None
            conditions.append(isinstance(scanner_type, str) and scanner_type in {str(v).strip() for v in scanner_type_in if isinstance(v, str)})
        item_kind_in = condition_spec.get('item_kind_in')
        if isinstance(item_kind_in, list):
            kind = item_context.get('kind') if isinstance(item_context, dict) else None
            conditions.append(isinstance(kind, str) and kind in {str(v).strip() for v in item_kind_in if isinstance(v, str)})
        item_field_in = condition_spec.get('item_field_in')
        if isinstance(item_field_in, dict):
            item_matches = True
            if not isinstance(item_context, dict):
                item_matches = False
            else:
                for field_name, allowed_values in item_field_in.items():
                    if not isinstance(field_name, str) or not isinstance(allowed_values, list):
                        item_matches = False
                        break
                    raw_value = item_context.get(field_name)
                    field_vocab = item_field_vocabs.get(field_name) if isinstance(item_field_vocabs, dict) else None
                    normalized_allowed: set[str] = set()
                    for allowed_value in allowed_values:
                        candidate_value = allowed_value
                        if isinstance(candidate_value, str) and isinstance(field_vocab, str):
                            candidate_value = vocabulary.resolve_canonical(field_vocab, candidate_value) or candidate_value
                        normalized_candidate = _normalize_scalar(candidate_value)
                        if normalized_candidate is not None:
                            normalized_allowed.add(normalized_candidate)
                    if not normalized_allowed:
                        item_matches = False
                        break
                    resolved_raw_value = raw_value
                    if isinstance(resolved_raw_value, str) and isinstance(field_vocab, str):
                        resolved_raw_value = vocabulary.resolve_canonical(field_vocab, resolved_raw_value) or resolved_raw_value
                    normalized_value = _normalize_scalar(resolved_raw_value)
                    if normalized_value is None:
                        item_matches = False
                        break
                    if normalized_value not in normalized_allowed:
                        item_matches = False
                        break
            conditions.append(item_matches)
        any_item_field_in = condition_spec.get('any_item_field_in')
        if isinstance(any_item_field_in, dict):
            list_path = any_item_field_in.get('path'); field_name = any_item_field_in.get('field'); allowed_values = any_item_field_in.get('values')
            if not isinstance(list_path, str) or not isinstance(field_name, str) or not isinstance(allowed_values, list):
                matches = False
            else:
                nodes = _resolve_path_nodes(payload, list_path)
                normalized_allowed = {str(v).strip().casefold() for v in allowed_values if isinstance(v, (str, int, float, bool))}
                matches = False
                for node in nodes:
                    if not isinstance(node.value, dict):
                        continue
                    raw_value = node.value.get(field_name)
                    if isinstance(raw_value, (str, int, float, bool)) and str(raw_value).strip().casefold() in normalized_allowed:
                        matches = True
                        break
            conditions.append(matches)
        any_item_matches = condition_spec.get('any_item_matches')
        if isinstance(any_item_matches, dict):
            list_path = any_item_matches.get('path'); field_in = any_item_matches.get('field_in')
            if not isinstance(list_path, str) or not isinstance(field_in, dict):
                matches = False
            else:
                nodes = _resolve_path_nodes(payload, list_path); matches = False
                for node in nodes:
                    if not isinstance(node.value, dict):
                        continue
                    item_ok = True
                    for field_name, allowed_values in field_in.items():
                        if not isinstance(field_name, str) or not isinstance(allowed_values, list):
                            item_ok = False; break
                        normalized_allowed = {str(v).strip().casefold() for v in allowed_values if isinstance(v, (str, int, float, bool))}
                        raw_value = node.value.get(field_name)
                        if not isinstance(raw_value, (str, int, float, bool)) or str(raw_value).strip().casefold() not in normalized_allowed:
                            item_ok = False; break
                    if item_ok:
                        matches = True; break
            conditions.append(matches)
        field_equals_any = condition_spec.get('field_equals_any')
        if isinstance(field_equals_any, dict):
            field_path = field_equals_any.get('field'); allowed_values = field_equals_any.get('values')
            if not isinstance(field_path, str) or not isinstance(allowed_values, list):
                matches = False
            else:
                nodes = _resolve_path_nodes(payload, field_path)
                normalized_allowed = {str(v).strip().casefold() for v in allowed_values if isinstance(v, (str, int, float, bool))}
                matches = any(isinstance(node.value, (str, int, float, bool)) and str(node.value).strip().casefold() in normalized_allowed for node in nodes)
            conditions.append(matches)
        modules_any_of = condition_spec.get('modules_any_of')
        if isinstance(modules_any_of, list):
            module_nodes = _resolve_path_nodes(payload, 'modules'); has_module_match = False
            if module_nodes and isinstance(module_nodes[0].value, list):
                module_ids = {canonical for module in module_nodes[0].value for raw_name in [module.get('type') or module.get('name') if isinstance(module, dict) else None] for canonical in [vocabulary.resolve_canonical('modules', raw_name) or raw_name if isinstance(raw_name, str) else None] if isinstance(canonical, str)}
                targets = {str(v).strip() for v in modules_any_of if isinstance(v, str)}
                has_module_match = bool(module_ids & targets)
            conditions.append(has_module_match)
        detector_kinds_any_of = condition_spec.get('detector_kinds_any_of')
        if isinstance(detector_kinds_any_of, list):
            detector_nodes = _resolve_path_nodes(payload, 'hardware.detectors'); has_detector_match = False
            if detector_nodes and isinstance(detector_nodes[0].value, list):
                detector_kinds = {canonical for detector in detector_nodes[0].value for raw_kind in [detector.get('kind') if isinstance(detector, dict) else None] for canonical in [vocabulary.resolve_canonical('detector_kinds', raw_kind) or raw_kind if isinstance(raw_kind, str) else None] if isinstance(canonical, str)}
                targets = {str(v).strip() for v in detector_kinds_any_of if isinstance(v, str)}
                has_detector_match = bool(detector_kinds & targets)
            conditions.append(has_detector_match)
        software_roles_any_of = condition_spec.get('software_roles_any_of')
        if isinstance(software_roles_any_of, list):
            present_roles = _get_software_roles(payload); targets = {str(v).strip().lower() for v in software_roles_any_of if isinstance(v, str)}
            conditions.append(bool(present_roles & targets))
        software_roles_none_of = condition_spec.get('software_roles_none_of')
        if isinstance(software_roles_none_of, list):
            present_roles = _get_software_roles(payload); blocked = {str(v).strip().lower() for v in software_roles_none_of if isinstance(v, str)}
            conditions.append(present_roles.isdisjoint(blocked))
        if not conditions:
            return False
        return all(conditions)

    all_of = required_if.get('all_of')
    if isinstance(all_of, list):
        all_of_results = [_evaluate_required_if(condition, payload=payload, item_context=item_context, vocabulary=vocabulary, item_field_vocabs=item_field_vocabs) for condition in all_of if isinstance(condition, dict)]
        if not all_of_results or not all(all_of_results):
            return False
    any_of = required_if.get('any_of')
    if isinstance(any_of, list):
        any_of_results = [_evaluate_required_if(condition, payload=payload, item_context=item_context, vocabulary=vocabulary, item_field_vocabs=item_field_vocabs) for condition in any_of if isinstance(condition, dict)]
        if not any_of_results or not any(any_of_results):
            return False
    simple_result = _evaluate_simple_conditions(required_if)
    has_simple_conditions = any(key in required_if for key in ('parent_present', 'modalities_any_of', 'scanner_type_in', 'item_kind_in', 'modules_any_of', 'detector_kinds_any_of', 'software_roles_any_of', 'software_roles_none_of', 'item_field_in', 'any_item_field_in', 'any_item_matches', 'field_equals_any'))
    if has_simple_conditions:
        return simple_result
    return isinstance(all_of, list) or isinstance(any_of, list)


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _evaluate_event_required_if(required_if: dict[str, Any], *, payload: dict[str, Any], item_context: dict[str, Any] | None) -> tuple[bool | None, str | None]:
    supported_keys = {'performed_contains_qc_type','service_provider_in','missing_legacy_event_id','no_stability_series','no_linearity_series','missing_csv_artifact','metrics_computed_present','evaluation_present','evaluation_computed_provenance_present'}
    unknown = [key for key in required_if if key not in supported_keys]
    if unknown:
        return None, f"Unsupported required_if condition(s): {', '.join(sorted(unknown))}."
    conditions: list[bool] = []
    if 'performed_contains_qc_type' in required_if:
        expected = required_if.get('performed_contains_qc_type')
        performed_nodes = _resolve_path_nodes(payload, 'performed[]')
        found = {item.value.get('qc_type') for item in performed_nodes if isinstance(item.value, dict) and isinstance(item.value.get('qc_type'), str)}
        conditions.append(isinstance(expected, str) and expected in found)
    if 'service_provider_in' in required_if:
        allowed = required_if.get('service_provider_in'); provider = payload.get('service_provider')
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
    return EventPolicy(policy_path=policy_path, record_type=record_type.strip(), vocab_registry=vocab_registry, field_rules=[r for r in field_rules if isinstance(r, dict)], legacy_and_migration_rules=[r for r in legacy_rules if isinstance(r, dict)], cross_field_rules=[r for r in cross_rules if isinstance(r, dict)]), None
