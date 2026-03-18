from __future__ import annotations

import argparse
from pathlib import Path
import yaml

from scripts.light_path_parser import migrate_instrument_to_light_path_v2


def migrate_file(path: Path) -> bool:
    payload = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        return False
    migrated = migrate_instrument_to_light_path_v2(payload)
    path.write_text(yaml.safe_dump(migrated, sort_keys=False, allow_unicode=True), encoding='utf-8')
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description='Migrate instrument YAML files to the canonical light_paths v2 schema.')
    parser.add_argument('paths', nargs='*', help='Files or directories to migrate. Defaults to instruments/.')
    args = parser.parse_args()
    inputs = [Path(item) for item in args.paths] if args.paths else [Path('instruments')]
    files: list[Path] = []
    for item in inputs:
        if item.is_dir():
            files.extend(sorted(item.glob('*.yaml')))
            files.extend(sorted((item / 'retired').glob('*.yaml')) if (item / 'retired').exists() else [])
        elif item.suffix.lower() == '.yaml' and item.exists():
            files.append(item)
    changed = 0
    for file in files:
        if migrate_file(file):
            changed += 1
    print(f'Migrated {changed} YAML file(s) to light_paths v2.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
