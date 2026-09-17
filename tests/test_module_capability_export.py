"""The scientific relationships the page needs are exported, not restated in it.

Three of them: which technique a module implements, which source role a technique
cannot be performed without, and which roles produce an image channel. Each was a
table in browser JavaScript, each duplicated a vocabulary that already held the
fact, and each had drifted from it.

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


def test_a_technique_states_the_source_role_it_requires():
    """STED and RESOLFT both need a depletion beam, and both say so.

    The removed browser table required one for STED and not for RESOLFT, which
    use the same beam, so a RESOLFT acquisition with no depletion source selected
    was never questioned.
    """
    vocabulary = _vocabulary()
    modes = vocabulary.terms_by_vocab["imaging_modes"]
    assert modes["sted"].tag_value("requires_source_role") == "depletion"
    assert modes["resolft"].tag_value("requires_source_role") == "depletion"
    # A technique that needs no particular beam must not claim to.
    for mode_id in ("confocal_point", "widefield_fluorescence", "tirf"):
        assert modes[mode_id].tag_value("requires_source_role") is None


def test_a_role_states_whether_it_produces_an_image_channel():
    """The channel-order question is about channels; a depletion beam is not one."""
    roles = _vocabulary().terms_by_vocab["light_source_roles"]
    for role_id in ("depletion", "activation", "alignment"):
        assert roles[role_id].tag_value("forms_imaging_channel") is False
    # Illumination roles say nothing, and saying nothing means they do.
    for role_id in ("excitation", "transmitted_illumination", "reflected_illumination"):
        assert roles[role_id].tag_value("forms_imaging_channel", True) is True


def test_the_browser_carries_no_copy_of_any_of_the_three_relationships():
    source = APP.read_text(encoding="utf-8")
    for removed in ("MODULE_TECHNIQUE_REQUIREMENTS", "METHOD_REQUIRED_SOURCE_ROLES",
                    "DEPLETION_METHOD_IDS", "NON_CHANNEL_SOURCE_ROLES"):
        assert removed not in source, f"{removed} is a second copy of a vocabulary"
    for read_instead in ("providesCapability", "requiresSourceRole", "formsImagingChannel"):
        assert read_instead in source, f"the page must read {read_instead} from the record"
