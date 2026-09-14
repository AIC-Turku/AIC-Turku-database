"""Regression tests from the user-facing planning usability benchmark."""

from pathlib import Path

import yaml

from scripts.dashboard.llm_export import _build_hardware_focus_summary


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_screening_summary_accepts_string_capability_ids() -> None:
    summary = _build_hardware_focus_summary(
        {
            "capabilities": {
                "imaging_modes": ["confocal_spinning_disk", "widefield_fluorescence"]
            },
            "hardware": {},
        },
        {},
    )

    assert summary["modality_labels"] == [
        "confocal_spinning_disk",
        "widefield_fluorescence",
    ]


def test_screening_summary_uses_canonical_environment_and_autofocus_fields() -> None:
    summary = _build_hardware_focus_summary(
        {
            "capabilities": {"imaging_modes": []},
            "hardware": {
                "environment": {
                    "temperature_control": True,
                    "co2_control": True,
                },
                "hardware_autofocus": {
                    "is_installed": True,
                    "type": "infrared_reflection",
                },
                "triggering": {"primary_mode": "hardware"},
            },
        },
        {},
    )

    assert "environmental control" in summary["supporting_feature_labels"]
    assert "hardware autofocus" in summary["supporting_feature_labels"]
    assert "hardware triggering" in summary["supporting_feature_labels"]


def test_crest_dualcam_route_allows_both_camera_branches() -> None:
    payload = yaml.safe_load(
        (REPO_ROOT / "instruments" / "Nikon Ti2-E Crest V3 Spinning Disk.yaml").read_text(
            encoding="utf-8"
        )
    )
    route = next(
        row for row in payload["light_paths"] if row["id"] == "confocal_spinning_disk"
    )
    branch_block = next(
        step["branches"] for step in route["detection_sequence"] if "branches" in step
    )

    assert branch_block["selection_mode"] == "multiple"
    assert {branch["branch_id"] for branch in branch_block["items"]} == {
        "to_master",
        "to_slave",
    }
    endpoints = {
        step["endpoint_id"]
        for branch in branch_block["items"]
        for step in branch["sequence"]
        if "endpoint_id" in step
    }
    assert endpoints == {"kinetix_master_camera", "kinetix_slave_camera"}


def test_planning_prompt_permits_general_guidance_but_keeps_facility_claims_grounded() -> None:
    template = (REPO_ROOT / "scripts" / "templates" / "plan_experiments.md.j2").read_text(
        encoding="utf-8"
    )

    assert "general microscopy principles and trade-offs" in template
    assert "never turn them into an ${facilityShortName}-specific performance claim" in template
    assert "report only hardware details that affect the decision" in template
    assert "one or two important unknowns most likely to change the choice" in template
