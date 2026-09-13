from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}: {old[:100]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_site_render() -> None:
    path = ROOT / "scripts" / "dashboard" / "site_render.py"

    replace_once(
        path,
        '''def build_nav(\n    instruments: list[dict[str, Any]],\n    retired_instruments: list[dict[str, Any]],\n) -> list[dict[str, Any]]:\n''',
        '''def filter_public_instruments(\n    instruments: list[dict[str, Any]],\n    excluded_ids: set[str],\n) -> list[dict[str, Any]]:\n    """Remove explicitly presentation-excluded records from public dashboard surfaces."""\n    return [\n        inst\n        for inst in instruments\n        if isinstance(inst, dict) and inst.get("id") not in excluded_ids\n    ]\n\n\ndef build_nav(\n    instruments: list[dict[str, Any]],\n    retired_instruments: list[dict[str, Any]],\n) -> list[dict[str, Any]]:\n''',
    )

    replace_once(
        path,
        '''    presentation_excluded_ids = set(catalogue.get("excluded_instrument_ids") or [])\n    public_retired_instruments = [\n        inst for inst in retired_instruments\n        if inst.get("id") not in presentation_excluded_ids\n    ]\n''',
        '''    presentation_excluded_ids = set(catalogue.get("excluded_instrument_ids") or [])\n    public_retired_instruments = filter_public_instruments(\n        retired_instruments, presentation_excluded_ids\n    )\n''',
    )


def write_regression_test() -> None:
    path = ROOT / "tests" / "test_public_dashboard_presentation.py"
    path.write_text(
        '''from __future__ import annotations\n\nfrom scripts.dashboard.site_render import build_nav, filter_public_instruments\n\n\ndef test_presentation_exclusion_filters_fixture_from_public_navigation() -> None:\n    retired = [\n        {"id": "scope-real", "display_name": "Real retired microscope"},\n        {"id": "scope-testx1", "display_name": "Test Scope X1"},\n    ]\n\n    public = filter_public_instruments(retired, {"scope-testx1"})\n\n    assert [item["id"] for item in public] == ["scope-real"]\n    nav = build_nav([], public)\n    rendered = str(nav)\n    assert "Test Scope X1" not in rendered\n    assert "scope-testx1" not in rendered\n    assert "Real retired microscope" in rendered\n\n\ndef test_public_navigation_uses_sentence_case_labels() -> None:\n    nav = build_nav([], [])\n    labels = [next(iter(item)) for item in nav]\n\n    assert labels == [\n        "Fleet overview",\n        "Instrument status",\n        "Microscopes",\n        "Objectives",\n        "Experiment planning",\n        "Virtual Microscope",\n        "Methods generator",\n        "Vocabulary dictionary",\n        "Retired instruments",\n    ]\n''',
        encoding="utf-8",
    )


def main() -> None:
    patch_site_render()
    write_regression_test()


if __name__ == "__main__":
    main()
