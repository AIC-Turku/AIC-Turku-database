"""The technique a module implements is exported, not restated in the browser.

`vocab/modules.yaml` already records that an Airyscan module provides `ism` and
an easy3D STED module provides `sted`. The Methods generator needs exactly that
relationship to ask why a STED module is reported on an acquisition claiming no
STED, and it used to carry its own table of it in JavaScript. That table both
duplicated the vocabulary and disagreed with it: it held keys no record uses
(`sted_3d`, `tirf_module`, `flim_module`, `fcs_module`) and omitted `3d_sim`,
which the Deltavision OMX record does use — so the check silently did nothing
for the one instrument whose SIM module it should have caught.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.dashboard.instrument_view import _module_provides_capability
from scripts.validation.vocabulary import Vocabulary

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "assets/javascripts/methods_generator_app.js"


def _vocabulary() -> Vocabulary:
    return Vocabulary(ROOT / "vocab")


def _authored_module_types() -> set[str]:
    types: set[str] = set()
    for path in sorted((ROOT / "instruments").rglob("*.yaml")):
        record = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for module in (record.get("hardware") or {}).get("modules") or []:
            module_type = str((module or {}).get("type") or "").strip()
            if module_type:
                types.add(module_type)
    return types


def test_the_export_matches_the_vocabulary_for_every_authored_module():
    """Whatever the vocabulary says a module provides is what is exported."""
    vocabulary = _vocabulary()
    raw_terms = yaml.safe_load((ROOT / "vocab/modules.yaml").read_text(encoding="utf-8"))
    tags_by_id = {
        term["id"]: ((term.get("tags") or {}).get("provides_capability") or {})
        for term in (raw_terms.get("terms") or raw_terms.get("values") or [])
    }

    for module_type in sorted(_authored_module_types()):
        exported = _module_provides_capability(vocabulary, module_type)
        authored = tags_by_id.get(module_type, {})
        for axis in ("imaging_modes", "contrast_methods", "readouts"):
            expected = [str(value) for value in (authored.get(axis) or [])]
            assert [row["id"] for row in exported.get(axis, [])] == expected, (
                f"{module_type}.{axis} is exported as "
                f"{[row['id'] for row in exported.get(axis, [])]} but the vocabulary "
                f"records {expected}"
            )


def test_the_modules_the_old_table_got_wrong_are_exported_correctly():
    """The specific drift that made the check wrong, named."""
    vocabulary = _vocabulary()
    # Authored by the Deltavision OMX record and missing from the removed table.
    assert _module_provides_capability(vocabulary, "3d_sim") == {
        "imaging_modes": [{"id": "sim", "display_label": "SIM"}]
    }
    # Held by the removed table, matching no authored module and no vocabulary term.
    for invented in ("sted_3d", "tirf_module", "flim_module", "fcs_module"):
        assert _module_provides_capability(vocabulary, invented) == {}, (
            f"{invented} is not a module term; nothing may claim it provides a technique"
        )
    # A module that implements no technique must not produce a technique prompt.
    assert _module_provides_capability(vocabulary, "incubation") == {}


def test_the_browser_does_not_carry_its_own_copy_of_the_relationship():
    """The rule this fix exists to keep: no hardcoded vocabulary in the page."""
    source = APP.read_text(encoding="utf-8")
    assert "MODULE_TECHNIQUE_REQUIREMENTS" not in source
    assert "providesCapability" in source, (
        "the page must read the exported relationship from the module record"
    )
