#!/usr/bin/env python3
"""Build searchable local spectra indexes for the virtual microscope.

Usage:
    python scripts/build_local_spectra_index.py
    python scripts/build_local_spectra_index.py --root assets/data/spectra

The script scans category folders such as ``assets/data/spectra/fluorophores`` for
``*.json`` item files, then regenerates lightweight ``index.json`` and ``by_id.json``
lookup files plus a top-level ``manifest.json``.
"""
from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CATEGORIES = {
    "fluorophores": {
        "category": "fluorophore",
        "index_fields": ["id", "slug", "name", "aliases", "category", "source_library", "exMax", "emMax"],
    },
    "filters": {
        "category": "filter",
        "index_fields": ["id", "slug", "name", "aliases", "category", "subtype", "source_library"],
    },
    "sources": {
        "category": "source",
        "index_fields": ["id", "slug", "name", "aliases", "category", "subtype", "source_library"],
    },
}


@dataclass
class CategorySummary:
    count: int
    files: list[str]



def stable_slug(value: str) -> str:
    token = ''.join(ch.lower() if ch.isalnum() else '-' for ch in value.strip())
    token = '-'.join(part for part in token.split('-') if part)
    return token or 'item'



def read_json(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f'{path} must contain a JSON object')
    return data



def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write('\n')



def item_files(category_dir: Path) -> list[Path]:
    return sorted(
        path for path in category_dir.glob('*.json')
        if path.name not in {'index.json', 'by_id.json'}
    )



def build_category(root: Path, category_name: str, config: dict[str, Any]) -> CategorySummary:
    category_dir = root / category_name
    category_dir.mkdir(parents=True, exist_ok=True)

    index_rows: list[dict[str, Any]] = []
    by_id: OrderedDict[str, str] = OrderedDict()
    files_written: list[str] = []

    for path in item_files(category_dir):
        item = read_json(path)
        item.setdefault('id', stable_slug(str(item.get('slug') or item.get('name') or path.stem)))
        item.setdefault('slug', stable_slug(str(item.get('slug') or item.get('id') or item.get('name') or path.stem)))
        item.setdefault('name', str(item.get('name') or item['slug']))
        item.setdefault('aliases', [])
        item.setdefault('category', config['category'])

        if path.stem != item['slug']:
            normalized_path = path.with_name(f"{item['slug']}.json")
            if normalized_path != path:
                path.rename(normalized_path)
                path = normalized_path
        write_json(path, item)
        files_written.append(path.name)

        index_row = {field: item.get(field) for field in config['index_fields']}
        index_row['source'] = 'local'
        index_rows.append(index_row)

        for key in {str(item.get('id') or '').strip(), str(item.get('slug') or '').strip(), str(item.get('name') or '').strip()}:
            if key:
                by_id[key.lower()] = item['slug']
        for alias in item.get('aliases') or []:
            alias_token = str(alias).strip().lower()
            if alias_token:
                by_id[alias_token] = item['slug']

    index_rows.sort(key=lambda row: (str(row.get('name') or '').lower(), str(row.get('slug') or '').lower()))
    by_id_sorted = OrderedDict(sorted(by_id.items(), key=lambda entry: entry[0]))
    write_json(category_dir / 'index.json', index_rows)
    write_json(category_dir / 'by_id.json', by_id_sorted)

    return CategorySummary(count=len(index_rows), files=files_written)



def build_manifest(root: Path, summaries: dict[str, CategorySummary]) -> None:
    manifest = {
        'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'generator': 'scripts/build_local_spectra_index.py',
        'categories': {
            name: {
                'count': summary.count,
                'files': summary.files,
            }
            for name, summary in summaries.items()
        },
    }
    write_json(root / 'manifest.json', manifest)



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='assets/data/spectra', help='Spectra root directory to index')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)

    summaries = {
        name: build_category(root, name, config)
        for name, config in CATEGORIES.items()
    }
    build_manifest(root, summaries)

    for name, summary in summaries.items():
      print(f'{name}: {summary.count} item(s) indexed')
    print(f'Manifest written to {root / "manifest.json"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
