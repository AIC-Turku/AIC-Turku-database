import json
from pathlib import Path

from scripts.dashboard.instrument_view import vocab_label
from scripts.dashboard.site_render import _build_all_charts_data
from scripts.validation.vocabulary import build_repository_vocabulary

ROOT = Path(__file__).resolve().parents[1]


def test_repository_vocabulary_includes_every_authored_source():
    vocabulary = build_repository_vocabulary(ROOT)
    authored = {path.stem for path in (ROOT / "vocab").glob("*.yaml")}
    assert authored <= set(vocabulary.terms_by_vocab)


def test_classification_accepts_safe_alias_without_making_broad_value_rewriteable():
    vocabulary = build_repository_vocabulary(ROOT)
    assert vocabulary.classify_canonical("objective_specialties", "DIC") == "dic"
    assert vocabulary.resolve_canonical("objective_specialties", "DIC Prism A") is None
    assert vocabulary.classify_canonical("objective_specialties", "DIC Prism A") == "dic"


def test_objective_qualifiers_do_not_invent_correction_hardware():
    vocabulary = build_repository_vocabulary(ROOT)
    assert vocabulary.classify_canonical("objective_specialties", "cover glass 0.17") == "cover_glass_specification"
    assert vocabulary.classify_canonical("objective_specialties", "correction collar for 0-1.5mm glass") == "correction_collar"
    assert vocabulary.classify_canonical("objective_specialties", "Multi-immersion") == "multi_immersion"
    for value in ("cover glass 0.17", "correction collar for 0-1.5mm glass", "Multi-immersion"):
        assert vocabulary.resolve_canonical("objective_specialties", value) is None


def test_ambiguous_light_source_terms_are_not_rewrite_safe_aliases():
    vocabulary = build_repository_vocabulary(ROOT)
    for value in ("diode", "tunable laser", "x-cite", "fs laser", "ti:sapphire"):
        assert vocabulary.resolve_canonical("light_source_kinds", value) is None
    assert vocabulary.resolve_canonical("light_source_kinds", "laser_diode") == "laser"
    assert vocabulary.resolve_canonical("light_source_kinds", "WLL") == "white_light_laser"
    assert vocabulary.classify_canonical("light_source_kinds", "ti_sapphire") == "multiphoton_laser"
    assert vocabulary.classify_canonical("light_source_kinds", "ti:sapphire") == "multiphoton_laser"


def test_dashboard_vocab_label_uses_visible_missing_translation_marker():
    vocabulary = build_repository_vocabulary(ROOT)
    assert vocab_label(vocabulary, "detector_kinds", "scmos") == "Scientific CMOS"
    rendered = vocab_label(vocabulary, "detector_kinds", "future_detector")
    assert rendered == "future_detector (missing vocabulary translation)"


def test_qc_chart_history_splits_same_metric_id_by_authored_unit():
    logs = [
        {"data": {"started_utc": "2026-01-01T00:00:00Z", "inputs_human": [{"metric_id": "example.length", "value": 500, "unit": "nm"}]}},
        {"data": {"started_utc": "2026-02-01T00:00:00Z", "inputs_human": [{"metric_id": "example.length", "value": 0.5, "unit": "um"}]}},
    ]
    charts = json.loads(_build_all_charts_data(logs))
    assert "example.length" not in charts
    assert charts["example.length::unit=nm"]["values"] == [500, None]
    assert charts["example.length::unit=um"]["values"] == [None, 0.5]
    assert charts["example.length::unit=nm"]["metric_id"] == "example.length"
    assert charts["example.length::unit=nm"]["split_by_unit"] is True


def test_single_unit_chart_keeps_backward_compatible_metric_key():
    logs = [
        {"data": {"started_utc": "2026-01-01T00:00:00Z", "inputs_human": [{"metric_id": "example.length", "value": 500, "unit": "nm"}]}},
        {"data": {"started_utc": "2026-02-01T00:00:00Z", "inputs_human": [{"metric_id": "example.length", "value": 510, "unit": "nm"}]}},
    ]
    charts = json.loads(_build_all_charts_data(logs))
    assert charts["example.length"]["values"] == [500, 510]
    assert charts["example.length"]["split_by_unit"] is False


def test_autofix_workflow_executes_package_module_and_validates_before_pr():
    workflow = (ROOT / ".github/workflows/autofix.yml").read_text(encoding="utf-8")
    assert "python -m scripts.autofix_yaml --write" in workflow
    assert "python scripts/autofix_yaml.py --write" not in workflow
    assert workflow.index("python -m scripts.validate") < workflow.index("peter-evans/create-pull-request")


def test_chart_renderer_labels_unit_split_series():
    source = (ROOT / "assets/javascripts/charts.js").read_text(encoding="utf-8")
    assert "chartData.metric_id || metricId" in source
    assert "chartData.split_by_unit" in source


def test_schema_contract_fixtures_do_not_shadow_pyyaml():
    fixture_root = ROOT / "tests" / "fixtures" / "schema_generator_validator_contract"
    assert not list(fixture_root.glob("*/yaml.py"))


def test_no_vocabulary_transfer_or_patch_machinery_remains():
    assert not (ROOT / ".vocab-transfer").exists()
    assert not (ROOT / ".github/workflows/apply-vocabulary-hardening.yml").exists()
    assert not (ROOT / ".github/workflows/apply-vocabulary-second-audit.yml").exists()
    assert not (ROOT / ".github/workflows/apply-vocabulary-final-audit.yml").exists()
    assert not list((ROOT / "scripts").glob("_vocab_audit_patch_*.py"))
    assert not (ROOT / "scripts/_vocab_final_audit_patch.py").exists()
