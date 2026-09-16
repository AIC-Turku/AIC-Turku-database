"""The generated light-path reference must match the schema and the code.

`docs/light_path_model.md` replaced a hand-written document that had drifted: it
omitted a required field, described a DTO shape with a third of the real keys, and
listed a deprecated field as canonical. Generating it removes the drift only while
the committed copy is actually regenerated, so this test is what makes skipping
that step fail rather than pass silently.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.light_path_model import (
    DIAGNOSTIC_NOTES,
    OUTPUT_PATH,
    canonical_rules,
    diagnostic_codes,
    load_policy,
    render,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_committed_reference_matches_the_schema_and_the_code():
    expected = render(load_policy())
    actual = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    assert actual == expected, (
        "docs/light_path_model.md no longer matches the schema, the validator, or "
        "the DTO builders. Run `python -m scripts.light_path_model` and commit the "
        "result; do not edit the Markdown by hand."
    )


def test_check_mode_reports_success_on_a_clean_tree():
    """The command AGENTS.md tells people to run has to be usable as a gate."""
    result = subprocess.run(
        [sys.executable, "-m", "scripts.light_path_model", "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_required_schema_field_is_documented():
    """The drift that prompted this file was a required field nobody listed."""
    text = OUTPUT_PATH.read_text(encoding="utf-8")
    required = [
        rule["path"] for rule in canonical_rules(load_policy())
        if rule.get("status") == "required"
    ]
    assert "light_paths[].route_type" in required, (
        "route_type stopped being required; the schema changed under this test"
    )
    for path in required:
        assert f"`{path}`" in text, f"required field {path} is missing from the reference"


def test_every_light_path_diagnostic_has_a_description():
    """A code with no note renders a placeholder, which must not be committed."""
    undescribed = [code for code in diagnostic_codes() if code not in DIAGNOSTIC_NOTES]
    assert not undescribed, (
        f"add these codes to DIAGNOSTIC_NOTES in scripts/light_path_model.py: {undescribed}"
    )
    assert "No description recorded" not in OUTPUT_PATH.read_text(encoding="utf-8")


def test_the_reference_states_the_semantics_the_schema_cannot():
    """The point of keeping a document at all is the part the schema cannot say."""
    text = OUTPUT_PATH.read_text(encoding="utf-8")
    for phrase in (
        "A route family is not a technique",
        "compatibility gate, not an implementation claim",
        "The fork belongs to the route, not to the hardware",
        "What is not canonical",
    ):
        assert phrase in text, f"authored section missing: {phrase}"


def test_a_schema_change_makes_the_committed_file_stale():
    """A generator that cannot fail is not a gate. Prove this one can."""
    policy = load_policy()
    for section in policy["sections"]:
        if (section.get("name") or section.get("id")) == "canonical_light_paths_v2":
            section["rules"].append({
                "path": "light_paths[].invented_field",
                "title": "Invented",
                "status": "required",
                "type": "string",
                "rationale": "Only exists inside this test.",
            })
            break
    regenerated = render(policy)
    assert "light_paths[].invented_field" in regenerated
    assert regenerated != OUTPUT_PATH.read_text(encoding="utf-8")
