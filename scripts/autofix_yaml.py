"""Conservative vocabulary and declared-migration autofixer.

The validator/policy/vocabulary modules are authoritative. Default mode is
read-only; writes require ``--write``. Broader classifications are never rewritten.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from scripts.validation.events import validate_event_ledgers
from scripts.validation.instrument import validate_instrument_ledgers
from scripts.validation.io import _iter_yaml_files, _load_yaml
from scripts.validation.model import EventPolicy, InstrumentPolicy, PolicyRule
from scripts.validation.policy import _load_event_policy, _load_instrument_policy, _resolve_path_nodes
from scripts.validation.vocabulary import Vocabulary


@dataclass
class AutofixSpec:
    target_dir: Path
    vocabulary: Vocabulary
    rules: list[tuple[str, str]]
    legacy_rules: list[dict[str, Any]]


def get_base_path() -> Path:
    return Path.cwd().resolve()


def _rule_pairs_from_instrument(policy: InstrumentPolicy) -> list[tuple[str, str]]:
    return [(rule.path, rule.vocab) for rule in policy.rules if isinstance(rule, PolicyRule) and isinstance(rule.vocab, str) and rule.vocab]


def _rule_pairs_from_event(policy: EventPolicy) -> list[tuple[str, str]]:
    return [(rule['path'], rule['vocab']) for rule in policy.field_rules if isinstance(rule.get('path'), str) and isinstance(rule.get('vocab'), str)]


def build_specs(base: Path) -> list[AutofixSpec]:
    instrument_policy, instrument_error = _load_instrument_policy(base / 'schema' / 'instrument_policy.yaml')
    if instrument_error is not None or instrument_policy is None:
        raise RuntimeError(instrument_error or 'Could not load instrument policy.')
    specs = [AutofixSpec(base / 'instruments', Vocabulary(base / 'vocab', vocab_registry=instrument_policy.vocab_registry), _rule_pairs_from_instrument(instrument_policy), [])]
    for target, policy_name in (('qc/sessions', 'QC_policy.yaml'), ('maintenance/events', 'maintenance_policy.yaml')):
        policy, error = _load_event_policy(base / 'schema' / policy_name)
        if error is not None or policy is None:
            raise RuntimeError(error or f'Could not load {policy_name}.')
        specs.append(AutofixSpec(base / target, Vocabulary(base / 'vocab', vocab_registry=policy.vocab_registry), _rule_pairs_from_event(policy), list(policy.legacy_and_migration_rules)))
    return specs


def _canonical_value(value: Any, vocab_name: str, vocabulary: Vocabulary) -> Any:
    if isinstance(value, list):
        return [vocabulary.resolve_canonical(vocab_name, item) or item if isinstance(item, str) else item for item in value]
    if isinstance(value, str):
        return vocabulary.resolve_canonical(vocab_name, value) or value
    return value


def _parse_concrete_path(path: str) -> list[tuple[str, int | None]]:
    tokens: list[tuple[str, int | None]] = []
    for segment in path.split('.'):
        match = re.fullmatch(r'([^\[]+)(?:\[(\d+)\])?', segment)
        if match is None:
            raise ValueError(f'Unsupported concrete path segment: {segment}')
        tokens.append((match.group(1), int(match.group(2)) if match.group(2) is not None else None))
    return tokens


def _set_concrete_path(data: Any, path: str, value: Any) -> None:
    current = data
    tokens = _parse_concrete_path(path)
    for key, index in tokens[:-1]:
        current = current[key]
        if index is not None:
            current = current[index]
    key, index = tokens[-1]
    if index is None:
        current[key] = value
    else:
        current[key][index] = value


def _canonicalize_rule_values(data: dict[str, Any], rules: list[tuple[str, str]], vocabulary: Vocabulary) -> int:
    replacements = 0
    for path, vocab_name in rules:
        for node in _resolve_path_nodes(data, path):
            new_value = _canonical_value(node.value, vocab_name, vocabulary)
            if new_value != node.value:
                _set_concrete_path(data, node.path, new_value)
                replacements += 1
    return replacements


def _apply_declared_legacy_migrations(data: dict[str, Any], legacy_rules: list[dict[str, Any]]) -> int:
    replacements = 0
    for rule in legacy_rules:
        source = rule.get('path')
        target = rule.get('migrate_to') or rule.get('replacement')
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        if any(marker in source + target for marker in ('.', '[', ']')):
            continue
        if source in data and target not in data:
            data[target] = data.pop(source)
            replacements += 1
    return replacements


def autofix_file(filepath: Path, spec: AutofixSpec, *, write_changes: bool) -> tuple[bool, int]:
    _, strict_error = _load_yaml(filepath, reject_duplicate_keys=True)
    if strict_error is not None:
        raise RuntimeError(f'{filepath}: {strict_error}')
    yaml_rt = YAML(typ='rt')
    yaml_rt.preserve_quotes = True
    with filepath.open('r', encoding='utf-8') as handle:
        data = yaml_rt.load(handle)
    if not isinstance(data, dict):
        return False, 0
    replacements = _canonicalize_rule_values(data, spec.rules, spec.vocabulary)
    replacements += _apply_declared_legacy_migrations(data, spec.legacy_rules)
    changed = replacements > 0
    if changed and write_changes:
        with filepath.open('w', encoding='utf-8') as handle:
            yaml_rt.dump(data, handle)
    return changed, replacements


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Conservative vocabulary autofixer')
    parser.add_argument('--write', action='store_true', help='Apply rewrite-safe lexical synonyms and policy-declared migrations.')
    parser.add_argument('--check', action='store_true', help='Explicit spelling for the default read-only mode.')
    args = parser.parse_args(argv)
    if args.write and args.check:
        parser.error('--write and --check are mutually exclusive')
    return args


def _validate_repository_after_write() -> None:
    instrument_ids, instrument_errors, _ = validate_instrument_ledgers()
    event_report = validate_event_ledgers(instrument_ids=instrument_ids)
    errors = [*instrument_errors, *event_report.errors]
    if errors:
        preview = '; '.join(f"{item.code}: {item.path}" for item in errors[:10])
        suffix = '' if len(errors) <= 10 else f"; ... and {len(errors) - 10} more"
        raise RuntimeError(
            f"Autofix produced {len(errors)} validation error(s); writes were rolled back. "
            f"{preview}{suffix}"
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base = get_base_path()
    changed_files: list[Path] = []
    total_replacements = 0
    originals: dict[Path, str] = {}
    try:
        for spec in build_specs(base):
            for filepath in _iter_yaml_files(spec.target_dir):
                original = filepath.read_text(encoding='utf-8') if args.write else None
                changed, replacements = autofix_file(filepath, spec, write_changes=args.write)
                if changed:
                    changed_files.append(filepath)
                    total_replacements += replacements
                    if args.write and original is not None:
                        originals[filepath] = original
        if args.write and originals:
            _validate_repository_after_write()
    except Exception:
        for filepath, original in originals.items():
            filepath.write_text(original, encoding='utf-8')
        raise

    mode = 'Updated' if args.write else 'Would update'
    print(f'{mode} {len(changed_files)} file(s); replacements: {total_replacements}.')
    for filepath in changed_files:
        print(f' - {filepath.relative_to(base)}')
    return 1 if (not args.write and changed_files) else 0


if __name__ == '__main__':
    raise SystemExit(main())
