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
    # The 3i records carry roles on their laser lines and not on their widefield
    # LED, so exactly the LED is expected to be listed for them.
    listed = roles.get("3i CSU-W1 Spinning Disk", [])
    assert listed, "expected the unroled 3i widefield LED to be reported"
    assert all("laser" not in entry for entry in listed), (
        f"laser lines already carry a recorded role and must not be listed: {listed}"
    )
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


def test_a_holder_no_recorded_position_can_serve_is_a_question_for_staff():
    """The BC43's emission wheel is recorded on its transmitted path too.

    All four of its positions are fluorescence bandpass filters and none is open,
    so the path as recorded cannot be traversed for a brightfield acquisition.
    The Methods draft stops offering those positions there, which makes the record
    the thing that needs correcting - and a correction nobody is asked for does
    not happen.
    """
    gaps = collect_gaps()
    reported = gaps.get("route_position_mismatch") or {}
    listed = reported.get("Andor BC43 Benchtop Confocal", [])
    assert listed, "the BC43 emission wheel on the transmitted path must be a question"
    assert any("transmitted_light" in entry for entry in listed), listed


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
