"""The exported catalogue has to be JSON a browser will parse.

Python's `json` module writes `Infinity` and `NaN` for float infinities and
accepts them again on read, so a value that is unusable in the browser survives
every Python-side check. The Methods page fetches this file and calls
`JSON.parse` on it: one `Infinity` anywhere makes the whole catalogue fail to
load and the page never lists a single instrument.

This happened: an open-ended longpass pass window was exported as
`float("inf")`. The page went blank, and nothing but a browser test noticed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _reject(constant: str) -> None:
    raise AssertionError(
        f"the exported catalogue contains {constant}, which is not valid JSON and "
        "makes JSON.parse fail in the browser; export an open bound as null"
    )


@pytest.mark.parametrize("asset", [
    "instruments_data.json",
    "llm_inventory.json",
    "objective_pool.json",
    "vocabularies.json",
])
def test_exported_assets_parse_as_strict_json(generated_dashboard: Path, asset: str):
    path = generated_dashboard / "assets" / asset
    if not path.is_file():
        pytest.skip(f"{asset} is not produced by this build")
    json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject)
