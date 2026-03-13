#!/usr/bin/env python3
"""Import SpectraScope spectral TSV data into the local AIC spectral library.

Usage:
    python scripts/import_spectrascope.py \
        --source ../SpectraScope-master \
        --output assets/data/spectra

The importer is deterministic and safe to rerun. It rebuilds the target library
from SpectraScope metadata + per-item spectrum TSV files and writes:

    assets/data/spectra/manifest.json
    assets/data/spectra/<category>/index.json
    assets/data/spectra/<category>/<slug>.json
    assets/data/spectra/<category>/by_id.json

The storage layout is intentionally human-inspectable and easy to extend.
Adding compatible spectra later should only require updating the upstream TSVs
and rerunning this script.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = REPO_ROOT.parent / "SpectraScope-master"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "assets" / "data" / "spectra"
SOURCE_LIBRARY = "SpectraScope"

FILTER_SPECTRUM_TYPES = {
    "EX": "transmission",
    "EM": "transmission",
    "DM": "dichroic",
}


@dataclass(frozen=True)
class ImportStats:
    item_count: int
    spectrum_file_count: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE_ROOT,
        help="Path to the SpectraScope repository root (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Output directory for the local spectral library (default: %(default)s)",
    )
    return parser.parse_args()


def read_tsv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [
            {str(key): (value.strip() if isinstance(value, str) else value) for key, value in row.items()}
            for row in reader
        ]


_NUMERIC_RE = re.compile(r"^-?(?:\d+\.?\d*|\d*\.\d+)(?:[eE][+-]?\d+)?$")


def number_or_none(value: Any) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not value.is_integer():
            return value
        return int(value)
    text = str(value).strip()
    if not text or text.lower() == "none":
        return None
    if not _NUMERIC_RE.match(text):
        return None
    numeric = float(text)
    if numeric.is_integer():
        return int(numeric)
    return numeric


def clean_slug(text: str, *, fallback_prefix: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", str(text).strip().lower()).strip("-")
    return cleaned or fallback_prefix


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def split_list_field(value: Any) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_spectrum_file(path: Path) -> list[list[int | float]]:
    rows = read_tsv_rows(path)
    points: list[list[int | float]] = []
    for row in rows:
        x = number_or_none(row.get("w") or row.get("wl") or row.get("wavelength") or row.get("nm"))
        y = number_or_none(row.get("ri") or row.get("value") or row.get("intensity") or row.get("y"))
        if x is None or y is None:
            continue
        points.append([x, y])
    points.sort(key=lambda pair: pair[0])
    return points


def metadata_for_row(row: dict[str, str], exclude: set[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, raw_value in row.items():
        if key in exclude:
            continue
        text = clean_text(raw_value)
        if text is None:
            continue
        numeric = number_or_none(text)
        payload[key] = numeric if numeric is not None else text
    return payload


def discover_fluorophore_spectra(source_root: Path) -> dict[str, dict[str, Path]]:
    spectra_dir = source_root / "web" / "data" / "fluorophore-spectra"
    grouped: dict[str, dict[str, Path]] = defaultdict(dict)
    for path in sorted(spectra_dir.glob("*.tsv")):
        stem = path.stem
        if "_" not in stem:
            continue
        name, raw_type = stem.rsplit("_", 1)
        spectrum_type = raw_type.strip().lower()
        grouped[name][spectrum_type] = path
    return dict(grouped)


def discover_filter_spectra(source_root: Path) -> dict[tuple[str, str], Path]:
    spectra_dir = source_root / "web" / "data" / "filter-spectra"
    grouped: dict[tuple[str, str], Path] = {}
    for path in sorted(spectra_dir.glob("*.tsv")):
        stem = path.stem
        if " " in stem:
            raw_type, name = stem.split(" ", 1)
        else:
            raw_type, name = stem, stem
        grouped[(raw_type.strip().upper(), name.strip())] = path
    return grouped


def discover_source_spectra(source_root: Path) -> dict[str, Path]:
    spectra_dir = source_root / "web" / "data" / "source-spectra"
    return {path.stem.strip(): path for path in sorted(spectra_dir.glob("*.tsv"))}


def build_fluorophores(source_root: Path) -> tuple[list[dict[str, Any]], ImportStats]:
    metadata_path = source_root / "web" / "data" / "fluorophores.tsv"
    rows = read_tsv_rows(metadata_path)
    spectra_by_name = discover_fluorophore_spectra(source_root)
    items: list[dict[str, Any]] = []
    spectrum_file_count = 0
    seen_names: set[str] = set()

    for row in rows:
        name = clean_text(row.get("name"))
        if not name:
            continue
        seen_names.add(name)
        slug = clean_slug(name, fallback_prefix="fluorophore")
        spectra_files = spectra_by_name.get(name, {})
        spectra = []
        for spectrum_type in ("ex", "em"):
            spectrum_path = spectra_files.get(spectrum_type)
            if spectrum_path is None:
                continue
            data = read_spectrum_file(spectrum_path)
            if not data:
                continue
            spectra.append({
                "spectrum_type": spectrum_type,
                "data": data,
            })
            spectrum_file_count += 1

        item = {
            "id": slug,
            "slug": slug,
            "name": name,
            "aliases": [],
            "category": "fluorophore",
            "source_library": SOURCE_LIBRARY,
            "exMax": number_or_none(row.get("wex")),
            "emMax": number_or_none(row.get("wem")),
            "metadata": metadata_for_row(row, {"name", "wex", "wem"}),
            "spectra": spectra,
            "raw_source": {
                "metadata_file": relative_posix(metadata_path, source_root),
                "spectra_files": [relative_posix(path, source_root) for _, path in sorted(spectra_files.items())],
            },
        }
        items.append(item)

    for name, spectra_files in sorted(spectra_by_name.items()):
        if name in seen_names:
            continue
        slug = clean_slug(name, fallback_prefix="fluorophore")
        spectra = []
        for spectrum_type, spectrum_path in sorted(spectra_files.items()):
            data = read_spectrum_file(spectrum_path)
            if not data:
                continue
            spectra.append({"spectrum_type": spectrum_type, "data": data})
            spectrum_file_count += 1
        items.append({
            "id": slug,
            "slug": slug,
            "name": name,
            "aliases": [],
            "category": "fluorophore",
            "source_library": SOURCE_LIBRARY,
            "exMax": None,
            "emMax": None,
            "metadata": {},
            "spectra": spectra,
            "raw_source": {
                "metadata_file": relative_posix(metadata_path, source_root),
                "spectra_files": [relative_posix(path, source_root) for _, path in sorted(spectra_files.items())],
            },
        })

    items.sort(key=lambda item: (item["name"].lower(), item["slug"]))
    return items, ImportStats(item_count=len(items), spectrum_file_count=spectrum_file_count)


def build_filters(source_root: Path) -> tuple[list[dict[str, Any]], ImportStats]:
    metadata_path = source_root / "web" / "data" / "filters.tsv"
    rows = read_tsv_rows(metadata_path)
    spectra_by_key = discover_filter_spectra(source_root)
    items: list[dict[str, Any]] = []
    spectrum_file_count = 0
    seen_keys: set[tuple[str, str]] = set()

    for row in rows:
        subtype = clean_text(row.get("type")) or "FILTER"
        name = clean_text(row.get("name"))
        if not name:
            continue
        key = (subtype.upper(), name)
        seen_keys.add(key)
        slug = clean_slug(f"{subtype}-{name}", fallback_prefix="filter")
        spectrum_path = spectra_by_key.get(key)
        spectra = []
        if spectrum_path is not None:
            data = read_spectrum_file(spectrum_path)
            if data:
                spectra.append({
                    "spectrum_type": FILTER_SPECTRUM_TYPES.get(subtype.upper(), "transmission"),
                    "data": data,
                })
                spectrum_file_count += 1

        item = {
            "id": slug,
            "slug": slug,
            "name": name,
            "category": "filter",
            "subtype": subtype.lower(),
            "source_library": SOURCE_LIBRARY,
            "metadata": {
                **metadata_for_row(row, {"type", "name"}),
                "scope": split_list_field(row.get("scope")),
            },
            "spectra": spectra,
            "raw_source": {
                "metadata_file": relative_posix(metadata_path, source_root),
                "spectra_files": [relative_posix(spectrum_path, source_root)] if spectrum_path else [],
            },
        }
        items.append(item)

    for (subtype, name), spectrum_path in sorted(spectra_by_key.items()):
        if (subtype, name) in seen_keys:
            continue
        slug = clean_slug(f"{subtype}-{name}", fallback_prefix="filter")
        data = read_spectrum_file(spectrum_path)
        spectra = []
        if data:
            spectra.append({"spectrum_type": FILTER_SPECTRUM_TYPES.get(subtype.upper(), "transmission"), "data": data})
            spectrum_file_count += 1
        items.append({
            "id": slug,
            "slug": slug,
            "name": name,
            "category": "filter",
            "subtype": subtype.lower(),
            "source_library": SOURCE_LIBRARY,
            "metadata": {},
            "spectra": spectra,
            "raw_source": {
                "metadata_file": relative_posix(metadata_path, source_root),
                "spectra_files": [relative_posix(spectrum_path, source_root)],
            },
        })

    items.sort(key=lambda item: (item["subtype"], item["name"].lower(), item["slug"]))
    return items, ImportStats(item_count=len(items), spectrum_file_count=spectrum_file_count)


def build_sources(source_root: Path) -> tuple[list[dict[str, Any]], ImportStats]:
    metadata_path = source_root / "web" / "data" / "sources.tsv"
    rows = read_tsv_rows(metadata_path)
    spectra_by_name = discover_source_spectra(source_root)
    items: list[dict[str, Any]] = []
    spectrum_file_count = 0
    seen_names: set[str] = set()

    for row in rows:
        name = clean_text(row.get("name"))
        if not name:
            continue
        seen_names.add(name)
        slug = clean_slug(name, fallback_prefix="source")
        spectrum_path = spectra_by_name.get(name)
        spectra = []
        if spectrum_path is not None:
            data = read_spectrum_file(spectrum_path)
            if data:
                spectra.append({
                    "spectrum_type": "output",
                    "data": data,
                })
                spectrum_file_count += 1

        item = {
            "id": slug,
            "slug": slug,
            "name": name,
            "category": "source",
            "subtype": None,
            "source_library": SOURCE_LIBRARY,
            "peak": number_or_none(row.get("peak")),
            "metadata": {
                **metadata_for_row(row, {"name", "peak"}),
                "scope": split_list_field(row.get("scope")),
                "details": split_list_field(row.get("details")),
            },
            "spectra": spectra,
            "raw_source": {
                "metadata_file": relative_posix(metadata_path, source_root),
                "spectra_files": [relative_posix(spectrum_path, source_root)] if spectrum_path else [],
            },
        }
        items.append(item)

    for name, spectrum_path in sorted(spectra_by_name.items()):
        if name in seen_names:
            continue
        slug = clean_slug(name, fallback_prefix="source")
        data = read_spectrum_file(spectrum_path)
        spectra = []
        if data:
            spectra.append({"spectrum_type": "output", "data": data})
            spectrum_file_count += 1
        items.append({
            "id": slug,
            "slug": slug,
            "name": name,
            "category": "source",
            "subtype": None,
            "source_library": SOURCE_LIBRARY,
            "peak": None,
            "metadata": {},
            "spectra": spectra,
            "raw_source": {
                "metadata_file": relative_posix(metadata_path, source_root),
                "spectra_files": [relative_posix(spectrum_path, source_root)],
            },
        })

    items.sort(key=lambda item: (item["name"].lower(), item["slug"]))
    return items, ImportStats(item_count=len(items), spectrum_file_count=spectrum_file_count)


def index_row_for_item(item: dict[str, Any], category_dir: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": item["id"],
        "slug": item["slug"],
        "name": item["name"],
        "source": "local",
        "source_library": item["source_library"],
        "asset_path": f"assets/data/spectra/{category_dir}/{item['slug']}.json",
    }
    if item.get("category") == "fluorophore":
        row.update({
            "aliases": item.get("aliases", []),
            "exMax": item.get("exMax"),
            "emMax": item.get("emMax"),
        })
    if item.get("category") in {"filter", "source"}:
        row["category"] = item.get("category")
    if item.get("subtype") is not None:
        row["subtype"] = item.get("subtype")
    if item.get("peak") is not None:
        row["peak"] = item.get("peak")
    return row


def write_category(temp_root: Path, category_dir: str, items: list[dict[str, Any]]) -> None:
    target_dir = temp_root / category_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    index_rows = [index_row_for_item(item, category_dir) for item in items]
    by_id = {row["id"]: row for row in index_rows}
    for item in items:
        json_dump(target_dir / f"{item['slug']}.json", item)
    json_dump(target_dir / "index.json", index_rows)
    json_dump(target_dir / "by_id.json", by_id)


def build_manifest(source_root: Path, counts: dict[str, ImportStats], items_by_category: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "source_library": SOURCE_LIBRARY,
        "generated_at": generated_at,
        "importer": "scripts/import_spectrascope.py",
        "source_root": str(source_root.resolve()),
        "categories": {
            category: {
                "count": stats.item_count,
                "spectrum_file_count": stats.spectrum_file_count,
            }
            for category, stats in counts.items()
        },
        "imports": {
            category: [
                {
                    "id": item["id"],
                    "slug": item["slug"],
                    "name": item["name"],
                }
                for item in items
            ]
            for category, items in items_by_category.items()
        },
        "provenance": {
            "fluorophores": {
                "metadata": "web/data/fluorophores.tsv",
                "spectra_dir": "web/data/fluorophore-spectra",
            },
            "filters": {
                "metadata": "web/data/filters.tsv",
                "spectra_dir": "web/data/filter-spectra",
            },
            "sources": {
                "metadata": "web/data/sources.tsv",
                "spectra_dir": "web/data/source-spectra",
            },
        },
    }


def rebuild_library(source_root: Path, output_root: Path) -> dict[str, ImportStats]:
    fluorophores, fluor_stats = build_fluorophores(source_root)
    filters, filter_stats = build_filters(source_root)
    sources, source_stats = build_sources(source_root)

    items_by_category = {
        "fluorophores": fluorophores,
        "filters": filters,
        "sources": sources,
    }
    stats_by_category = {
        "fluorophores": fluor_stats,
        "filters": filter_stats,
        "sources": source_stats,
    }

    temp_parent = output_root.parent
    temp_parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="spectra_import_", dir=str(temp_parent)))
    try:
        write_category(temp_root, "fluorophores", fluorophores)
        write_category(temp_root, "filters", filters)
        write_category(temp_root, "sources", sources)
        json_dump(temp_root / "manifest.json", build_manifest(source_root, stats_by_category, items_by_category))

        if output_root.exists():
            shutil.rmtree(output_root)
        temp_root.replace(output_root)
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise

    return stats_by_category


def validate_source_root(source_root: Path) -> None:
    required_paths = [
        source_root / "web" / "data" / "fluorophores.tsv",
        source_root / "web" / "data" / "fluorophore-spectra",
        source_root / "web" / "data" / "filters.tsv",
        source_root / "web" / "data" / "filter-spectra",
        source_root / "web" / "data" / "sources.tsv",
        source_root / "web" / "data" / "source-spectra",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise SystemExit("Missing required SpectraScope inputs:\n- " + "\n- ".join(missing))


def main() -> int:
    args = parse_args()
    source_root = args.source.resolve()
    output_root = args.output.resolve()
    validate_source_root(source_root)
    stats_by_category = rebuild_library(source_root, output_root)
    print(f"Imported SpectraScope data into {output_root}")
    for category, stats in stats_by_category.items():
        print(f"- {category}: {stats.item_count} item(s), {stats.spectrum_file_count} spectrum file(s)")
    print("Re-run this command after SpectraScope metadata or TSV spectra change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
