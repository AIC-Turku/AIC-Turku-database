"""CLI compatibility entrypoint for dashboard site rendering."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate import DEFAULT_ALLOWED_RECORD_TYPES
from scripts.dashboard.loaders import _allowed_record_types_from_arg
from scripts.dashboard.site_render import render_site


def main(
    strict: bool = True,
    allowed_record_types: tuple[str, ...] = DEFAULT_ALLOWED_RECORD_TYPES,
) -> int:
    return render_site(strict=strict, allowed_record_types=allowed_record_types)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build MkDocs Material dashboard pages from YAML ledgers.")
    strict_group = parser.add_mutually_exclusive_group()
    strict_group.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="Enable strict validator gate (default behaviour; kept for CI compatibility).",
    )
    strict_group.add_argument(
        "--no-strict",
        action="store_true",
        help="Skip strict validator gate and load all parseable instrument YAML files.",
    )
    parser.add_argument(
        "--allowed-record-types",
        default=None,
        help="Comma-separated set of validator record types to allow (defaults to all).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    raise SystemExit(
        main(
            strict=not args.no_strict,
            allowed_record_types=_allowed_record_types_from_arg(args.allowed_record_types),
        )
    )
