#!/usr/bin/env python3
"""Backfill `is_installed: true` for microscope objectives in instrument ledgers."""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML


def iter_yaml_files(base_dir: Path):
    if not base_dir.exists():
        return
    for path in sorted(base_dir.rglob("*.yaml")):
        if path.is_file():
            yield path


def update_objectives(path: Path, yaml: YAML) -> bool:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.load(handle)

    if not isinstance(data, dict):
        return False

    hardware = data.get("hardware")
    if not isinstance(hardware, dict):
        return False

    objectives = hardware.get("objectives")
    if not isinstance(objectives, list):
        return False

    changed = False
    for obj in objectives:
        if isinstance(obj, dict) and "is_installed" not in obj:
            obj["is_installed"] = True
            changed = True

    if changed:
        with path.open("w", encoding="utf-8") as handle:
            yaml.dump(data, handle)

    return changed


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 4096

    updated_files = []
    for relative_dir in ("instruments", "instruments/retired"):
        base_dir = repo_root / relative_dir
        for file_path in iter_yaml_files(base_dir):
            if update_objectives(file_path, yaml):
                updated_files.append(file_path.relative_to(repo_root).as_posix())

    print(f"Updated {len(updated_files)} file(s).")
    for updated in updated_files:
        print(f" - {updated}")


if __name__ == "__main__":
    main()
