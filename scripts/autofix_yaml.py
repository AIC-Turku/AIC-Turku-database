"""Automatically replace vocabulary synonyms with canonical IDs in instrument YAML files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Iterable

from ruamel.yaml import YAML

from validate import Vocabulary


def _iter_yaml_files(base_dir: Path) -> Iterable[Path]:
    if not base_dir.exists() or not base_dir.is_dir():
        return []
    return [p for p in sorted(base_dir.rglob("*")) if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}]


def _canonical_if_synonym(vocabulary: Vocabulary, vocab_name: str, value: Any) -> str | None:
    is_match, suggestion = vocabulary.check(vocab_name, value)
    if is_match or suggestion is None:
        return None
    return suggestion


def _fix_string_list(values: Any, *, vocab_name: str, vocabulary: Vocabulary) -> tuple[int, bool]:
    if not isinstance(values, list):
        return 0, False

    replacements = 0
    changed = False
    for index, value in enumerate(values):
        canonical = _canonical_if_synonym(vocabulary, vocab_name, value)
        if canonical is None:
            continue
        values[index] = canonical
        replacements += 1
        changed = True

    return replacements, changed


def _fix_nested_dict_list_key(
    values: Any,
    *,
    key: str,
    vocab_name: str,
    vocabulary: Vocabulary,
) -> tuple[int, bool]:
    if not isinstance(values, list):
        return 0, False

    replacements = 0
    changed = False
    for entry in values:
        if not isinstance(entry, dict):
            continue
        canonical = _canonical_if_synonym(vocabulary, vocab_name, entry.get(key))
        if canonical is None:
            continue
        entry[key] = canonical
        replacements += 1
        changed = True

    return replacements, changed


def autofix_instrument_file(path: Path, *, vocabulary: Vocabulary, yaml: YAML, check_only: bool) -> tuple[bool, int]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.load(handle)

    if not isinstance(payload, dict):
        return False, 0

    replacements = 0
    changed = False

    count, did_change = _fix_string_list(payload.get("modalities"), vocab_name="modalities", vocabulary=vocabulary)
    replacements += count
    changed = changed or did_change

    count, did_change = _fix_nested_dict_list_key(
        payload.get("modules"),
        key="name",
        vocab_name="modules",
        vocabulary=vocabulary,
    )
    replacements += count
    changed = changed or did_change

    hardware = payload.get("hardware") if isinstance(payload.get("hardware"), dict) else {}
    scanner = hardware.get("scanner") if isinstance(hardware.get("scanner"), dict) else {}

    canonical = _canonical_if_synonym(vocabulary, "scanner_types", scanner.get("type"))
    if canonical is not None:
        scanner["type"] = canonical
        replacements += 1
        changed = True

    count, did_change = _fix_nested_dict_list_key(
        hardware.get("light_sources"),
        key="kind",
        vocab_name="light_source_kinds",
        vocabulary=vocabulary,
    )
    replacements += count
    changed = changed or did_change

    count, did_change = _fix_nested_dict_list_key(
        hardware.get("detectors"),
        key="kind",
        vocab_name="detector_kinds",
        vocabulary=vocabulary,
    )
    replacements += count
    changed = changed or did_change

    objectives = hardware.get("objectives")
    if isinstance(objectives, list):
        for objective in objectives:
            if not isinstance(objective, dict):
                continue

            canonical = _canonical_if_synonym(vocabulary, "objective_immersion", objective.get("immersion"))
            if canonical is not None:
                objective["immersion"] = canonical
                replacements += 1
                changed = True

            canonical = _canonical_if_synonym(vocabulary, "objective_corrections", objective.get("correction"))
            if canonical is not None:
                objective["correction"] = canonical
                replacements += 1
                changed = True

    if changed and not check_only:
        with path.open("w", encoding="utf-8") as handle:
            yaml.dump(payload, handle)

    return changed, replacements


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replace vocabulary synonyms with canonical IDs in instrument YAML files."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode only: report files needing fixes and exit non-zero if any would change.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 4096

    vocabulary = Vocabulary(Path("vocab"))

    instrument_dirs = [Path("instruments"), Path("instruments/retired")]
    instrument_files = sorted({p for d in instrument_dirs for p in _iter_yaml_files(d)})

    changed_files: list[Path] = []
    total_replacements = 0

    for instrument_file in instrument_files:
        changed, replacements = autofix_instrument_file(
            instrument_file,
            vocabulary=vocabulary,
            yaml=yaml,
            check_only=args.check,
        )
        if changed:
            changed_files.append(instrument_file)
            total_replacements += replacements

    mode = "Would update" if args.check else "Updated"
    print(f"{mode} {len(changed_files)} instrument file(s); replacements: {total_replacements}.")

    if changed_files:
        for changed_file in changed_files:
            print(f" - {changed_file.as_posix()}")

    if args.check and changed_files:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
