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
        '''    return [\n        {"Fleet Overview": "index.md"},\n        {"System Health": "status.md"},\n        {"Microscopes": microscopes},\n        {"Objectives": "objective_pool.md"},\n        {"Plan Your Experiments": "plan_experiments.md"},\n        {"Virtual Microscope": "virtual_microscope.md"},\n        {"Methods Generator": "methods_generator.md"},\n        {"Vocabulary Dictionary": "vocabulary_dictionary.md"},\n        {"Retired Instruments": [{"Overview": "retired/index.md"}, *retired]},\n    ]\n''',
        '''    return [\n        {"Fleet overview": "index.md"},\n        {"Instrument status": "status.md"},\n        {"Microscopes": microscopes},\n        {"Objectives": "objective_pool.md"},\n        {"Experiment planning": "plan_experiments.md"},\n        {"Virtual Microscope": "virtual_microscope.md"},\n        {"Methods generator": "methods_generator.md"},\n        {"Vocabulary dictionary": "vocabulary_dictionary.md"},\n        {"Retired instruments": [{"Overview": "retired/index.md"}, *retired]},\n    ]\n''',
    )

    replace_once(
        path,
        '''    catalogue_instruments = {item["id"] for item in catalogue["instruments"]}\n\n    (docs_root / "vocabulary_dictionary.md").write_text(\n''',
        '''    catalogue_instruments = {item["id"] for item in catalogue["instruments"]}\n\n    # Reuse the facility's explicit presentation exclusion list for every public\n    # dashboard surface. The excluded records remain loaded and validated, but\n    # synthetic/development fixtures must not enter generated pages, search,\n    # navigation, or researcher-facing exports.\n    presentation_excluded_ids = set(catalogue.get("excluded_instrument_ids") or [])\n    public_retired_instruments = [\n        inst for inst in retired_instruments\n        if inst.get("id") not in presentation_excluded_ids\n    ]\n\n    (docs_root / "vocabulary_dictionary.md").write_text(\n''',
    )

    replace_once(
        path,
        '''    retired_instrument_ids = {inst["id"] for inst in retired_instruments}\n    global_vm_payloads: dict[str, dict[str, Any]] = {}\n\n    for inst in [*instruments, *retired_instruments]:\n''',
        '''    retired_instrument_ids = {inst["id"] for inst in public_retired_instruments}\n    global_vm_payloads: dict[str, dict[str, Any]] = {}\n\n    for inst in [*instruments, *public_retired_instruments]:\n''',
    )

    replace_once(
        path,
        '''            for inst in sorted(\n                [*instruments, *retired_instruments],\n                key=lambda item: item.get("id", ""),\n            )\n''',
        '''            for inst in sorted(\n                [*instruments, *public_retired_instruments],\n                key=lambda item: item.get("id", ""),\n            )\n''',
    )

    replace_once(
        path,
        '''    retired_md = tpl_retired.render(retired_instruments=retired_instruments)\n''',
        '''    retired_md = tpl_retired.render(retired_instruments=public_retired_instruments)\n''',
    )

    replace_once(
        path,
        '''        instruments=instruments,\n        retired_instruments=retired_instruments,\n    )\n''',
        '''        instruments=instruments,\n        retired_instruments=public_retired_instruments,\n    )\n''',
    )


def patch_virtual_microscope() -> None:
    path = ROOT / "scripts" / "templates" / "virtual_microscope_app.js"

    replace_once(
        path,
        '''  function componentLabel(component, fallback) {\n    return (component && (component.display_label || component.name)) || fallback;\n  }\n\n  function rgbaFromHex(hex, alpha) {\n''',
        '''  function componentLabel(component, fallback) {\n    return (component && (component.display_label || component.name)) || fallback;\n  }\n\n  function routeDisplayLabel(routeId) {\n    const normalized = cleanString(routeId).toLowerCase();\n    if (!normalized) return '';\n    const options = state.activeInstrument && Array.isArray(state.activeInstrument.routeOptions)\n      ? state.activeInstrument.routeOptions\n      : [];\n    const match = options.find((entry) => cleanString(entry && entry.id).toLowerCase() === normalized);\n    return cleanString(match && match.label) || normalized;\n  }\n\n  function rgbaFromHex(hex, alpha) {\n''',
    )

    replace_once(
        path,
        '''        source.route_label ? `route: ${source.route_label}` : '',\n        normalizeSourceRoutes(source).length ? `routes: ${normalizeSourceRoutes(source).join(', ')}` : '',\n''',
        '''        source.route_label ? `route: ${source.route_label}` : '',\n        normalizeSourceRoutes(source).length ? `routes: ${normalizeSourceRoutes(source).map(routeDisplayLabel).join(', ')}` : '',\n''',
    )


def write_regression_test() -> None:
    path = ROOT / "tests" / "test_public_dashboard_presentation.py"
    path.write_text(
        '''from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\n\nROOT = Path(__file__).resolve().parents[1]\nSYNTHETIC_NAME = "Test Scope X1"\nSYNTHETIC_ID = "scope-testx1"\n\n\ndef test_synthetic_fixture_is_not_published_on_public_dashboard() -> None:\n    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")\n    retired = (ROOT / "dashboard_docs" / "retired" / "index.md").read_text(encoding="utf-8")\n    methods = json.loads((ROOT / "dashboard_docs" / "assets" / "instruments_data.json").read_text(encoding="utf-8"))\n\n    assert SYNTHETIC_NAME not in mkdocs\n    assert SYNTHETIC_ID not in mkdocs\n    assert SYNTHETIC_NAME not in retired\n    assert SYNTHETIC_ID not in retired\n    assert all(item.get("id") != SYNTHETIC_ID for item in methods.get("instruments", []))\n    assert not (ROOT / "dashboard_docs" / "instruments" / SYNTHETIC_ID).exists()\n    assert not (ROOT / "dashboard_docs" / "events" / SYNTHETIC_ID).exists()\n\n\ndef test_public_navigation_uses_sentence_case_labels() -> None:\n    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")\n    for label in (\n        "Fleet overview",\n        "Instrument status",\n        "Experiment planning",\n        "Methods generator",\n        "Vocabulary dictionary",\n        "Retired instruments",\n    ):\n        assert f"- {label}:" in mkdocs\n''',
        encoding="utf-8",
    )


def main() -> None:
    patch_site_render()
    patch_virtual_microscope()
    write_regression_test()


if __name__ == "__main__":
    main()
