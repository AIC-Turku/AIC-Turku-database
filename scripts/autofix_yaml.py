"""Automatically replace vocabulary synonyms with canonical IDs in instrument YAML files.

The fixer intentionally operates on raw text instead of a YAML round-trip parser so it can
run in lightweight environments (for example CI checks that do not install optional
format-preserving YAML tooling).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Iterable

from validate import Vocabulary, _load_instrument_policy


def _iter_yaml_files(base_dir: Path) -> Iterable[Path]:
    if not base_dir.exists() or not base_dir.is_dir():
        return []
    return [p for p in sorted(base_dir.rglob("*")) if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}]


def _canonical_if_synonym(vocabulary: Vocabulary, vocab_name: str, value: Any) -> str | None:
    is_match, suggestion = vocabulary.check(vocab_name, value)
    if is_match or suggestion is None:
        return None
    return suggestion


def _indent_width(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _replace_quoted_value(line: str, *, key: str, vocab_name: str, vocabulary: Vocabulary) -> tuple[str, int]:
    suffix = "\n" if line.endswith("\n") else ""
    body = line[:-1] if suffix else line
    match = re.match(rf'^(\s*{re.escape(key)}\s*:\s*")([^"]+)(".*)$', body)
    if match is None:
        return line, 0

    canonical = _canonical_if_synonym(vocabulary, vocab_name, match.group(2))
    if canonical is None:
        return line, 0

    updated = f"{match.group(1)}{canonical}{match.group(3)}{suffix}"
    return updated, 1


def _replace_modalities_item(line: str, *, vocabulary: Vocabulary) -> tuple[str, int]:
    suffix = "\n" if line.endswith("\n") else ""
    body = line[:-1] if suffix else line
    match = re.match(r'^(\s*-\s*")([^"]+)(".*)$', body)
    if match is None:
        return line, 0

    canonical = _canonical_if_synonym(vocabulary, "modalities", match.group(2))
    if canonical is None:
        return line, 0

    updated = f"{match.group(1)}{canonical}{match.group(3)}{suffix}"
    return updated, 1


def autofix_instrument_file(path: Path, *, vocabulary: Vocabulary, check_only: bool) -> tuple[bool, int]:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

    changed = False
    replacements = 0
    result: list[str] = []

    in_modalities = False
    in_modules = False
    in_hardware = False
    in_scanner = False
    in_light_sources = False
    in_detectors = False
    in_objectives = False

    for line in lines:
        stripped = line.strip()
        indent = _indent_width(line)

        if indent == 0 and re.match(r"^[A-Za-z_][A-Za-z0-9_]*:\s*$", stripped):
            in_modalities = stripped.startswith("modalities:")
            in_modules = stripped.startswith("modules:")
            in_hardware = stripped.startswith("hardware:")
            in_scanner = False
            in_light_sources = False
            in_detectors = False
            in_objectives = False

        if in_hardware and indent == 2 and re.match(r"^[A-Za-z_][A-Za-z0-9_]*:\s*$", stripped):
            in_scanner = stripped.startswith("scanner:")
            in_light_sources = stripped.startswith("light_sources:")
            in_detectors = stripped.startswith("detectors:")
            in_objectives = stripped.startswith("objectives:")

        updated = line
        count = 0
        if in_modalities:
            updated, count = _replace_modalities_item(updated, vocabulary=vocabulary)
        elif in_modules:
            updated, count = _replace_quoted_value(
                updated,
                key="- name",
                vocab_name="modules",
                vocabulary=vocabulary,
            )
        elif in_scanner:
            updated, count = _replace_quoted_value(
                updated,
                key="type",
                vocab_name="scanner_types",
                vocabulary=vocabulary,
            )
        elif in_light_sources:
            updated, count = _replace_quoted_value(
                updated,
                key="kind",
                vocab_name="light_source_kinds",
                vocabulary=vocabulary,
            )
        elif in_detectors:
            updated, count = _replace_quoted_value(
                updated,
                key="kind",
                vocab_name="detector_kinds",
                vocabulary=vocabulary,
            )
        elif in_objectives:
            updated, count = _replace_quoted_value(
                updated,
                key="immersion",
                vocab_name="objective_immersion",
                vocabulary=vocabulary,
            )
            if count == 0:
                updated, count = _replace_quoted_value(
                    updated,
                    key="correction",
                    vocab_name="objective_corrections",
                    vocabulary=vocabulary,
                )

        if count > 0:
            replacements += count
            changed = True

        result.append(updated)

    if changed and not check_only:
        path.write_text("".join(result), encoding="utf-8")

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
    policy, policy_error = _load_instrument_policy()
    if policy_error is not None or policy is None:
        print(policy_error or "Failed to load instrument policy.")
        return 1

    vocabulary = Vocabulary(vocab_registry=policy.vocab_registry)

    instrument_dirs = [Path("instruments"), Path("instruments/retired")]
    instrument_files = sorted({p for d in instrument_dirs for p in _iter_yaml_files(d)})

    changed_files: list[Path] = []
    total_replacements = 0

    for instrument_file in instrument_files:
        changed, replacements = autofix_instrument_file(
            instrument_file,
            vocabulary=vocabulary,
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
