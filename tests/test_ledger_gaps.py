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
