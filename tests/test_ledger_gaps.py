"""The generated list of open ledger questions must match the records.

`docs/ledger_gaps.md` is the working list of what facility staff still have to
answer, and it is only useful while it is true. Regenerating it is a documented
step after any instrument-ledger change (see AGENTS.md); this test is what makes
forgetting that step fail rather than pass silently.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.ledger_gaps import OUTPUT_PATH, collect_gaps, render

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_committed_ledger_gaps_match_the_instrument_records():
    expected = render(collect_gaps())
    actual = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    assert actual == expected, (
        "docs/ledger_gaps.md no longer matches instruments/*.yaml. "
        "Run `python -m scripts.ledger_gaps` and commit the result; do not edit the "
        "Markdown by hand."
    )


def test_check_mode_reports_success_on_a_clean_tree():
    """The command AGENTS.md tells people to run has to be usable as a gate."""
    result = subprocess.run(
        [sys.executable, "-m", "scripts.ledger_gaps", "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_gap_that_is_filled_in_leaves_the_list():
    """A recorded role is not a gap, so the generator must stop reporting it.

    Without this the list could keep its shape while silently ignoring the field
    that was corrected, which would make the count meaningless as a progress
    measure.
    """
    gaps = collect_gaps()
    roles = gaps.get("source_role") or {}
    reported = {name for name, items in roles.items() if items}
    # The 3i CSU-W1 record now carries an explicit role on both its laser
    # sources and the X-Cite widefield LED, so it must not be reported.
    assert "3i CSU-W1 Spinning Disk" not in reported
    # Deltavision records roles on every source, so it must not appear at all.
    assert "Deltavision OMX" not in reported


def test_a_record_that_says_it_has_no_software_is_not_asked_about_software():
    """`software_status: not_applicable` is an answer, not a blank.

    The three Leica visual stands record it explicitly, and the generated list
    asked all three for the acquisition software they had already said they do
    not have. The whole section was false questions for staff.
    """
    gaps = collect_gaps()
    asked = gaps.get("no_acquisition_software") or {}
    for name in ("Leica DM IRBE", "Leica DM RB", "Leica DM RE"):
        assert name not in asked, (
            f"{name} records software_status: not_applicable and must not be asked "
            "for acquisition software"
        )


def test_recorded_spectra_are_not_reported_as_missing_bands():
    """Spectral detail is authored in several shapes, and all of them count.

    A filter cube records its spectra on the excitation, dichroic and emission
    sub-components; a longpass records a cut-on edge; a multiband dichroic records
    cutoffs. Reading only a top-level `bands` list reported every one of those as
    unanswered, which inflated the list staff are asked to work through.
    """
    from scripts.ledger_gaps import position_spectrum_is_missing

    cube = {
        "component_type": "filter_cube",
        "excitation_filter": {"center_nm": 470, "width_nm": 40},
        "dichroic": {"cut_on_nm": 495},
        "emission_filter": {"center_nm": 525, "width_nm": 50},
    }
    assert not position_spectrum_is_missing(cube)
    assert not position_spectrum_is_missing({"component_type": "longpass", "cut_on_nm": 500})
    assert not position_spectrum_is_missing(
        {"component_type": "multiband_dichroic", "cutoffs_nm": [485, 560, 645]})
    # A component with no passband has no bands to record.
    assert not position_spectrum_is_missing({"component_type": "analyzer"})
    assert not position_spectrum_is_missing({"component_type": "neutral_density"})
    # A cube with nothing recorded is still a real question.
    assert position_spectrum_is_missing({"component_type": "filter_cube", "name": "Standard Cubes"})


def test_a_holder_whose_positions_serve_their_route_is_not_reported():
    """The same wheel on the fluorescence paths is not a gap."""
    from scripts.ledger_gaps import holder_cannot_serve_route

    assert not holder_cannot_serve_route({
        "stage_role": "emission",
        "positions": {"Pos_1": {"component_type": "empty"}, "Pos_2": {"component_type": "bandpass"}},
    }), "a wheel with an open position can serve any path"
    assert not holder_cannot_serve_route({
        "stage_role": "analyzer",
        "positions": {"Pos_1": {"component_type": "analyzer"}},
    }), "an analyser selects no fluorescence band"
    assert holder_cannot_serve_route({
        "stage_role": "emission",
        "positions": {"Pos_1": {"component_type": "bandpass"}, "Pos_2": {"component_type": "bandpass"}},
    })


def test_the_fluorescence_classification_has_one_source_of_truth():
    """This file's gap detector and the generator's position filter must agree.

    Both ask the same question - can this position select a fluorescence band -
    about the same recorded component types and stage roles. They used to answer
    it from two independently written constant sets that happened to agree, then
    from two imports of the same dashboard-owned constants (an inverted
    dependency: an audit/reporting tool importing from the dashboard layer).
    Both now call scripts.lightpath.spectral_ops.is_fluorescence_band_position,
    a neutral module neither the dashboard nor ledger_gaps.py owns, so the two
    cannot silently diverge and ledger_gaps.py does not depend on the dashboard.

    Semantic examples, not object identity: a set swapped for a frozenset, or a
    copy returned instead of the same object, must not make this fail while a
    real behavior change - accepting a component type that is not a passband
    shape, or a stage role that carries no fluorescence signal - must.
    """
    from scripts.dashboard.optical_path_view import position_serves_route
    from scripts.ledger_gaps import holder_cannot_serve_route
    from scripts.lightpath.spectral_ops import is_fluorescence_band_position

    # Passband shapes in a fluorescence-carrying stage role select a band.
    for component_type in ("bandpass", "multiband_bandpass", "longpass", "shortpass", "notch"):
        for stage_role in ("excitation", "emission", "cube"):
            assert is_fluorescence_band_position(component_type, stage_role), (
                component_type, stage_role,
            )

    # An open position selects nothing, whatever the stage role.
    assert not is_fluorescence_band_position("empty", "emission")
    assert not is_fluorescence_band_position("mirror", "cube")
    # A stage role that carries no fluorescence signal is not a fluorescence
    # question even when the component type would otherwise qualify.
    assert not is_fluorescence_band_position("bandpass", "analyzer")
    assert not is_fluorescence_band_position("bandpass", "")
    # Case is not authored consistently in the ledger.
    assert is_fluorescence_band_position("BANDPASS", "Emission")

    # Both call sites see the same answer for the same recorded facts, so a
    # mismatch (were one to redefine its own copy again) fails here rather
    # than as an unreported gap or a wrongly offered route position.
    fact = ("bandpass", "emission")
    assert is_fluorescence_band_position(*fact)
    assert not position_serves_route(
        {"component_type": fact[0]}, fact[1], route_declares_imaging_modes=False,
    )
    assert holder_cannot_serve_route({
        "stage_role": fact[1],
        "positions": {"Pos_1": {"component_type": fact[0]}},
    })
