from __future__ import annotations

from scripts._vocab_audit_patch_common import ROOT, replace_once

# The schema-generator integration fixtures predate strict duplicate-key YAML
# validation and carried local yaml.py stubs. Subprocesses run with cwd=fixture,
# so those files shadow installed PyYAML and make strict validation impossible.
# PyYAML is a declared test dependency; delete the obsolete stubs rather than
# weakening duplicate-key enforcement.
fixture_root = ROOT / "tests" / "fixtures" / "schema_generator_validator_contract"
for stub in sorted(fixture_root.glob("*/yaml.py")):
    stub.unlink()

# Keep Ti:Sapphire identity distinct from the broader source kind while making
# its behavior explicit. Classification is semantic metadata for consumers; it
# is deliberately not a rewrite-safe synonym.
replace_once(
    "vocab/light_source_kinds.yaml",
    '''  - id: multiphoton_laser
    label: "Pulsed Near-IR Laser"
    description: "Femtosecond pulsed laser tunable in the near-infrared. Used for deep-tissue multiphoton excitation."
    synonyms: []
''',
    '''  - id: multiphoton_laser
    label: "Pulsed Near-IR Laser"
    description: "Femtosecond pulsed laser tunable in the near-infrared. Used for deep-tissue multiphoton excitation."
    synonyms: []
    classified_values: [ti_sapphire, "ti:sapphire"]
''',
)

# Derive simulator behavior from vocabulary classification without rewriting the
# authored/normalized identity. This keeps kind=ti_sapphire visible while
# correctly treating its tunable range as a laser line rather than a band.
replace_once(
    "scripts/lightpath/spectral_ops.py",
    '''def _source_spectral_mode(
    kind: str,
    wavelength: Any,
    width_nm: Any,
    tunable_min_nm: Any,
    tunable_max_nm: Any,
) -> str:
''',
    '''def _source_behavior_kind(kind: str) -> str:
    vocabulary = get_active_vocab()
    classify = getattr(vocabulary, "classify_canonical", None)
    if callable(classify):
        classified = classify("light_source_kinds", kind)
        if isinstance(classified, str) and classified:
            return classified
    return kind


def _source_spectral_mode(
    kind: str,
    wavelength: Any,
    width_nm: Any,
    tunable_min_nm: Any,
    tunable_max_nm: Any,
) -> str:
    behavior_kind = _source_behavior_kind(kind)
''',
)
replace_once(
    "scripts/lightpath/spectral_ops.py",
    '''        if kind in {
            "laser",
            "white_light_laser",
            "multiphoton_laser",
            "supercontinuum",
        }:
''',
    '''        if behavior_kind in {
            "laser",
            "white_light_laser",
            "multiphoton_laser",
            "supercontinuum",
        }:
''',
)
replace_once(
    "scripts/lightpath/spectral_ops.py",
    '''    if kind in {"arc_lamp", "halogen_lamp", "metal_halide"}:
''',
    '''    if behavior_kind in {"arc_lamp", "halogen_lamp", "metal_halide"}:
''',
)
replace_once(
    "scripts/lightpath/spectral_ops.py",
    '''    kind = _normalize_light_source_kind(source.get("kind") or source.get("type") or "light_source")

    display_label = _light_source_display_label(
''',
    '''    kind = _normalize_light_source_kind(source.get("kind") or source.get("type") or "light_source")
    behavior_kind = _source_behavior_kind(kind)

    display_label = _light_source_display_label(
''',
)
replace_once(
    "scripts/lightpath/spectral_ops.py",
    '''            if kind in {
                "laser",
                "white_light_laser",
                "multiphoton_laser",
                "supercontinuum",
            }
''',
    '''            if behavior_kind in {
                "laser",
                "white_light_laser",
                "multiphoton_laser",
                "supercontinuum",
            }
''',
)

# Regression coverage: classification drives behavior but never canonical
# rewriting, and integration fixtures must not shadow the YAML dependency.
replace_once(
    "tests/test_vocabulary_final_audit.py",
    '''def test_ambiguous_light_source_terms_are_not_rewrite_safe_aliases():
    vocabulary = build_repository_vocabulary(ROOT)
    for value in ("diode", "tunable laser", "x-cite", "fs laser", "ti:sapphire"):
        assert vocabulary.resolve_canonical("light_source_kinds", value) is None
    assert vocabulary.resolve_canonical("light_source_kinds", "laser_diode") == "laser"
    assert vocabulary.resolve_canonical("light_source_kinds", "WLL") == "white_light_laser"
''',
    '''def test_ambiguous_light_source_terms_are_not_rewrite_safe_aliases():
    vocabulary = build_repository_vocabulary(ROOT)
    for value in ("diode", "tunable laser", "x-cite", "fs laser", "ti:sapphire"):
        assert vocabulary.resolve_canonical("light_source_kinds", value) is None
    assert vocabulary.resolve_canonical("light_source_kinds", "laser_diode") == "laser"
    assert vocabulary.resolve_canonical("light_source_kinds", "WLL") == "white_light_laser"
    assert vocabulary.classify_canonical("light_source_kinds", "ti_sapphire") == "multiphoton_laser"
    assert vocabulary.classify_canonical("light_source_kinds", "ti:sapphire") == "multiphoton_laser"
''',
)
replace_once(
    "tests/test_vocabulary_final_audit.py",
    '''def test_no_vocabulary_transfer_or_patch_machinery_remains():
''',
    '''def test_schema_contract_fixtures_do_not_shadow_pyyaml():
    fixture_root = ROOT / "tests" / "fixtures" / "schema_generator_validator_contract"
    assert not list(fixture_root.glob("*/yaml.py"))


def test_no_vocabulary_transfer_or_patch_machinery_remains():
''',
)
replace_once(
    "tests/test_vocabulary_final_audit.py",
    '''    assert not (ROOT / "scripts/_vocab_postmerge_ci_patch.py").exists()
''',
    '''    assert not (ROOT / "scripts/_vocab_postmerge_ci_patch.py").exists()
    assert not (ROOT / "scripts/_vocab_postmerge_ci_patch2.py").exists()
''',
)

print("Applied residual fixture and source-behavior corrections")
