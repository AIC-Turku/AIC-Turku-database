from __future__ import annotations

from scripts.dashboard.site_render import build_nav, filter_public_instruments


def test_presentation_exclusion_filters_fixture_from_public_navigation() -> None:
    retired = [
        {"id": "scope-real", "display_name": "Real retired microscope"},
        {"id": "scope-testx1", "display_name": "Test Scope X1"},
    ]

    public = filter_public_instruments(retired, {"scope-testx1"})

    assert [item["id"] for item in public] == ["scope-real"]
    nav = build_nav([], public)
    rendered = str(nav)
    assert "Test Scope X1" not in rendered
    assert "scope-testx1" not in rendered
    assert "Real retired microscope" in rendered


def test_public_navigation_uses_sentence_case_labels() -> None:
    nav = build_nav([], [])
    labels = [next(iter(item)) for item in nav]

    assert labels == [
        "Fleet overview",
        "Instrument status",
        "Microscopes",
        "Objectives",
        "Experiment planning",
        "Virtual Microscope",
        "Methods generator",
        "Vocabulary dictionary",
        "Retired instruments",
    ]
