"""Regression tests from the user-facing planning usability benchmark."""

from pathlib import Path

import yaml

from scripts.dashboard.llm_export import _build_hardware_focus_summary
from scripts.planning_eval import AuthoritativeContext, check_response


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


def test_screening_summary_preserves_triggering_mode_semantics() -> None:
    software = _build_hardware_focus_summary(
        {
            "capabilities": {"imaging_modes": []},
            "hardware": {"triggering": {"primary_mode": "software"}},
        },
        {},
    )
    mixed = _build_hardware_focus_summary(
        {
            "capabilities": {"imaging_modes": []},
            "hardware": {"triggering": {"primary_mode": "mixed"}},
        },
        {},
    )

    assert "software triggering" in software["supporting_feature_labels"]
    assert "hardware triggering" not in software["supporting_feature_labels"]
    assert "mixed triggering" in mixed["supporting_feature_labels"]


def test_crest_dualcam_route_binds_multiple_branches_to_dualcam_splitter() -> None:
    payload = yaml.safe_load(
        (REPO_ROOT / "instruments" / "Nikon Ti2-E Crest V3 Spinning Disk.yaml").read_text(
            encoding="utf-8"
        )
    )
    route = next(
        row for row in payload["light_paths"] if row["id"] == "confocal_spinning_disk"
    )
    steps = route["detection_sequence"]
    branch_index = next(index for index, step in enumerate(steps) if "branches" in step)
    branch_block = steps[branch_index]["branches"]

    # The route parser binds a branch block to the immediately preceding optical
    # path element. This must be the DualCam splitter, not the exclusive
    # trinocular port.
    assert steps[branch_index - 1]["optical_path_element_id"] == (
        "mxr00547_v3_dualcam_gfp_mcherry_2_bands_celesta_set"
    )
    assert branch_block["selection_mode"] == "multiple"
    assert {branch["branch_id"] for branch in branch_block["items"]} == {
        "to_master",
        "to_slave",
    }
    assert {branch.get("mode") for branch in branch_block["items"]} == {
        "transmitted",
        "reflected",
    }
    endpoints = {
        step["endpoint_id"]
        for branch in branch_block["items"]
        for step in branch["sequence"]
        if "endpoint_id" in step
    }
    assert endpoints == {"kinetix_master_camera", "kinetix_slave_camera"}
    assert all(
        "optical_path_element_id" not in step
        for branch in branch_block["items"]
        for step in branch["sequence"]
    )


def test_planning_evaluator_scopes_component_ownership_locally() -> None:
    context = AuthoritativeContext(
        instrument_ids={"scope-a", "scope-b"},
        components_by_instrument={
            "scope-a": {"endpoint:a"},
            "scope-b": {"endpoint:b"},
        },
        route_ids_by_instrument={"scope-a": set(), "scope-b": set()},
    )
    response = """scope-a
Use endpoint:b for acquisition.

scope-b
This is a second candidate.
"""

    codes = {finding.code for finding in check_response(response, context)}
    assert "component_not_on_named_instrument" in codes


def test_planning_prompt_permits_general_guidance_but_keeps_facility_claims_grounded() -> None:
    template = (REPO_ROOT / "scripts" / "templates" / "plan_experiments.md.j2").read_text(
        encoding="utf-8"
    )

    assert "general microscopy principles and trade-offs" in template
    assert "never turn them into an ${facilityShortName}-specific performance claim" in template
    assert "report only hardware details that affect the decision" in template
    assert "one or two important unknowns most likely to change the choice" in template
