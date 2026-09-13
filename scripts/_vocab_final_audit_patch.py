from __future__ import annotations

from scripts._vocab_audit_patch_common import ROOT, read, replace_once, regex_once, write

# The second-audit patch was merged as dormant transformation machinery. This
# script runs after those transformations and corrects residual issues found by
# the post-merge audit before any result is committed.

# 1. The repository vocabulary builder must include every authored vocabulary,
# not only namespaces currently referenced by a policy. Policy aliases/settings
# are merged on top of the canonical file-stem namespaces.
regex_once(
    "scripts/validation/vocabulary.py",
    r"def build_repository_vocabulary\(repo_root: Path\) -> Vocabulary:.*?\n    return Vocabulary\(repo_root / \"vocab\", vocab_registry=combined_registry\)\n",
    '''def build_repository_vocabulary(repo_root: Path) -> Vocabulary:
    """Build the authoritative repository vocabulary from all sources and policies."""
    repo_root = Path(repo_root).resolve()
    vocab_dir = repo_root / "vocab"
    combined_registry: dict[str, dict[str, Any]] = {
        path.stem: {"source": "file", "path": f"vocab/{path.name}"}
        for path in sorted(vocab_dir.glob("*.yaml"))
    }
    for relative_path in REPOSITORY_POLICY_PATHS:
        policy_path = repo_root / relative_path
        if not policy_path.exists():
            continue
        payload, error = _load_yaml(policy_path, reject_duplicate_keys=True)
        if error is not None or payload is None:
            raise VocabularyDefinitionError(
                f"Failed loading policy '{policy_path.as_posix()}': {error or 'unknown policy load error'}"
            )
        registry = payload.get("vocab_registry")
        if registry is None:
            continue
        if not isinstance(registry, dict):
            raise VocabularyDefinitionError(
                f"Policy '{policy_path.as_posix()}' has non-mapping vocab_registry."
            )
        combined_registry = merge_vocab_registries(combined_registry, registry)
    return Vocabulary(vocab_dir, vocab_registry=combined_registry)
''',
)

replace_once(
    "scripts/validation/vocabulary.py",
    '''    def classify_canonical(self, vocab_name: str, value: Any) -> str | None:
        """Return a broader category without authorizing automatic rewriting."""
        if not isinstance(value, str):
            return None
        cleaned = self._normalize(value)
        if not cleaned or vocab_name not in self.valid_ids_by_vocab:
            return None
        if cleaned in self.valid_ids_by_vocab[vocab_name]:
            return cleaned
        return self.classifications_by_vocab.get(vocab_name, {}).get(cleaned.casefold())
''',
    '''    def classify_canonical(self, vocab_name: str, value: Any) -> str | None:
        """Return a category match without authorizing automatic rewriting."""
        if not isinstance(value, str):
            return None
        resolved = self.resolve_canonical(vocab_name, value)
        if resolved is not None:
            return resolved
        cleaned = self._normalize(value)
        if not cleaned or vocab_name not in self.valid_ids_by_vocab:
            return None
        return self.classifications_by_vocab.get(vocab_name, {}).get(cleaned.casefold())
''',
)

# 2. Preserve objective qualifiers without asserting unsupported hardware
# semantics. Cover-glass specification, correction collars and multi-immersion
# are distinct concepts.
write(
    "vocab/objective_specialties.yaml",
    '''terms:
  - id: long_working_distance
    label: "Long Working Distance"
    description: "Objective designed for increased working distance."
    synonyms: [LWD, ELWD]
    classified_values: [ELWD ADM]
  - id: cover_glass_specification
    label: "Cover Glass Specification"
    description: "Objective has an explicit cover-glass thickness or specification; this does not imply an adjustable correction collar."
    classified_values:
      - cover glass 0.17
      - cover glass 0.75
  - id: coverslip_correction
    label: "Coverslip Correction"
    description: "Objective is explicitly described as supporting coverslip correction."
  - id: water_dipping
    label: "Water Dipping"
    description: "Objective designed for direct immersion into sample medium."
  - id: phase
    label: "Phase"
    description: "Objective supports phase-contrast use."
    classified_values:
      - Ph1
      - phase contrast (ph)
      - phase contrast (ph 0)
      - phase contrast (ph 1)
      - phase contrast (ph1 dl)
      - phase contrast (ph2)
      - phase contrast (ext ph4)
      - phase contrast (ph1)
      - phase compatible
  - id: dic
    label: "DIC"
    description: "Objective supports differential interference contrast."
    synonyms: [DIC]
    classified_values:
      - DIC (Suitable)
      - DIC (Recommended)
      - dic compatible
      - DIC N1
      - DIC N1 (Suitable)
      - DIC N2
      - DIC N2 (Suitable)
      - DIC N2 (Recommended)
      - DIC Prism A
      - DIC Prism B
      - DIC Prism C
      - DIC Prism D
      - DIC Prism E
  - id: uv_transmission
    label: "UV Transmission"
    description: "Objective optimized for UV transmission."
    classified_values: ["UV ≥340 nm", "UV ≥365 nm"]
  - id: ir_transmission
    label: "IR Transmission"
    description: "Objective optimized for IR / multiphoton transmission."
    classified_values:
      - UV-VIS-IR
      - (UV)VIS-IR
      - VISIR
      - IR-compatible to 1300 nm
  - id: correction_collar
    label: "Correction Collar"
    description: "Objective is explicitly described as having an adjustable correction collar or correction ring."
    synonyms: [Correction Ring, "Correction Ring (CORR)", correction collar]
    classified_values:
      - correction collar for 0-1.5mm glass
      - correction ring for 0.17 mm cover glass
  - id: multi_immersion
    label: "Multi-immersion"
    description: "Objective is explicitly described as supporting multiple immersion media; this does not imply a correction collar."
    classified_values:
      - Multi-immersion
      - Multi-immersion (BABB/W/Glyc/Sil-Oil)
  - id: tirf
    label: "TIRF"
    description: "Objective optimized for total internal reflection fluorescence imaging."
    synonyms: [TIRF]
  - id: sim
    label: "SIM"
    description: "Objective suitable for structured illumination microscopy workflows."
    synonyms: [SIM]
  - id: sted
    label: "STED"
    description: "Objective suitable for stimulated emission depletion microscopy workflows."
    synonyms: [STED]
  - id: polarization
    label: "Polarization"
    description: "Objective supports polarization imaging workflows."
    classified_values: ["Polarization (Possible)", "Polarization (Suitable)"]
  - id: cleared_tissue_imaging
    label: "Cleared Tissue Imaging"
    description: "Objective suitable for imaging optically cleared tissue samples."
    classified_values: ["Cleared Tissue Imaging (CLARITY and TDE)"]
  - id: other
    label: "Other"
    description: "Specialty not covered by the predefined terms."
''',
)

# 3. Only unambiguous lexical aliases may auto-canonicalize source kinds.
# Generic/brand terms such as diode, tunable laser and X-Cite are not evidence
# for one canonical source kind. The repository itself contains X-Cite XLED1 as LED.
write(
    "vocab/light_source_kinds.yaml",
    '''terms:
  - id: laser
    label: "Laser"
    description: "Provides coherent, narrowband excitation at specific wavelengths. Common for fluorescence imaging requiring high irradiance and precise line selection."
    synonyms: ["single-line laser", "laser_diode", "laser_dpss", "laser (diode)", "laser (DPSS)", "dpss"]
  - id: white_light_laser
    label: "White Light Laser"
    description: "Broadband laser source with tunable output wavelengths selected by software or optics. Supports flexible excitation across many fluorophores."
    synonyms: ["WLL"]
  - id: led
    label: "LED"
    description: "Solid-state light source with stable output and fast switching. Widely used for widefield fluorescence and transmitted illumination."
    synonyms: ["light-emitting diode"]
  - id: arc_lamp
    label: "Arc Lamp"
    description: "Broad-spectrum lamp, such as mercury or xenon, used with filter sets for fluorescence excitation. Historically common on epifluorescence microscopes."
    synonyms: ["mercury lamp", "xenon lamp"]
  - id: metal_halide
    label: "Metal Halide Lamp"
    description: "Broad-spectrum lamp coupled via a liquid light guide. Provides intense, stable excitation for standard widefield fluorescence."
    synonyms: ["hxp"]
  - id: halogen_lamp
    label: "Halogen Lamp"
    description: "Continuous-spectrum tungsten-halogen illumination, primarily for transmitted light imaging. Common for brightfield and contrast techniques."
    synonyms: ["tungsten-halogen", "quartz halogen"]
  - id: multiphoton_laser
    label: "Pulsed Near-IR Laser"
    description: "Femtosecond pulsed laser tunable in the near-infrared. Used for deep-tissue multiphoton excitation."
    synonyms: []
  - id: supercontinuum
    label: "Supercontinuum Source"
    description: "Broadband laser-like source generated by nonlinear spectral broadening. Provides highly flexible, selectable excitation bands."
    synonyms: ["white supercontinuum laser"]
''',
)

# 4. Dashboard labels must use the central diagnostic resolver.
replace_once(
    "scripts/dashboard/instrument_view.py",
    "from scripts.display_labels import resolve_endpoint_type_label\n",
    "from scripts.display_labels import resolve_endpoint_type_label, resolve_vocab_label\n",
)
replace_once(
    "scripts/dashboard/instrument_view.py",
    '''def vocab_label(vocabulary: Vocabulary, vocab_name: str, term_id: str) -> str:
    """Return a friendly vocabulary label for a canonical ID."""
    term = vocabulary.terms_by_vocab.get(vocab_name, {}).get(term_id)
    return term.label if term else term_id
''',
    '''def vocab_label(vocabulary: Vocabulary, vocab_name: str, term_id: str) -> str:
    """Resolve a vocabulary label through the central diagnostic boundary."""
    return resolve_vocab_label(vocabulary, vocab_name, term_id)
''',
)

# 5. Historical QC charts must never put numerically incompatible units on one
# axis. Preserve old metric IDs for single-unit histories; split only when a
# metric ID actually occurs with multiple authored units. No unit conversion is
# inferred here.
replace_once(
    "scripts/dashboard/site_render.py",
    "    build_qc_laser_context_view,\n    build_qc_metric_view,\n" if "build_qc_metric_view" in read("scripts/dashboard/site_render.py") else "    build_qc_laser_context_view,\n",
    "    build_qc_laser_context_view,\n    build_qc_metric_view,\n",
)
regex_once(
    "scripts/dashboard/site_render.py",
    r"def _build_all_charts_data\(qc_logs: list\[dict\[str, Any\]\]\) -> str:.*?\n    return json.dumps\(charts\)\n",
    '''def _build_all_charts_data(qc_logs: list[dict[str, Any]]) -> str:
    dated_metrics: list[tuple[str, dict[str, dict[str, Any]]]] = []
    units_by_metric: dict[str, set[str]] = {}

    for entry in qc_logs:
        payload = entry.get("data")
        if not isinstance(payload, dict):
            continue
        parsed_started = _parse_iso_datetime(payload.get("started_utc"))
        if parsed_started is None:
            continue
        metrics = {
            item["metric_id"]: item
            for item in build_qc_metric_view(payload)
            if isinstance(item.get("metric_id"), str)
        }
        dated_metrics.append((parsed_started.strftime("%Y-%m-%d"), metrics))
        for metric_id, item in metrics.items():
            value = item.get("value")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                units_by_metric.setdefault(metric_id, set()).add(str(item.get("unit") or ""))

    charts: dict[str, Any] = {}
    for metric_id in sorted(units_by_metric):
        units = sorted(units_by_metric[metric_id])
        split_by_unit = len(units) > 1
        for unit in units:
            labels: list[str] = []
            values: list[Any] = []
            for date_label, metrics in dated_metrics:
                labels.append(date_label)
                item = metrics.get(metric_id)
                value = item.get("value") if isinstance(item, dict) and str(item.get("unit") or "") == unit else None
                is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
                values.append(value if is_number else None)

            if not any(value is not None for value in values):
                continue
            series_key = metric_id if not split_by_unit else f"{metric_id}::unit={unit or 'none'}"
            charts[series_key] = {
                "labels": labels,
                "values": values,
                "metric_id": metric_id,
                "unit": unit,
                "split_by_unit": split_by_unit,
            }

    return json.dumps(charts)
''',
)

replace_once(
    "assets/javascripts/charts.js",
    "    title.textContent = (metricNames && metricNames[metricId]) ? metricNames[metricId] : metricId;\n",
    "    const baseMetricId = chartData.metric_id || metricId;\n    const baseTitle = (metricNames && metricNames[baseMetricId]) ? metricNames[baseMetricId] : baseMetricId;\n    const unitSuffix = chartData.split_by_unit ? ` (${chartData.unit || 'no unit'})` : '';\n    title.textContent = `${baseTitle}${unitSuffix}`;\n",
)

# 6. The rewritten autofix is a package module; invoke it as one in Actions.
replace_once(
    ".github/workflows/autofix.yml",
    "run: python scripts/autofix_yaml.py --write",
    "run: python -m scripts.autofix_yaml --write",
)

# 7. Final-audit regression coverage.
write(
    "tests/test_vocabulary_final_audit.py",
    '''import json
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


def test_no_vocabulary_transfer_or_patch_machinery_remains():
    assert not (ROOT / ".vocab-transfer").exists()
    assert not (ROOT / ".github/workflows/apply-vocabulary-hardening.yml").exists()
    assert not (ROOT / ".github/workflows/apply-vocabulary-second-audit.yml").exists()
    assert not (ROOT / ".github/workflows/apply-vocabulary-final-audit.yml").exists()
    assert not list((ROOT / "scripts").glob("_vocab_audit_patch_*.py"))
    assert not (ROOT / "scripts/_vocab_final_audit_patch.py").exists()
''',
)

write(
    "docs/vocabulary_final_audit_2026-09-13.md",
    '''# Vocabulary final adversarial audit — 2026-09-13

## Scope

This pass audited current `main` after PR #435 merged. The audit re-ran the failure modes from the two prior vocabulary audits and inspected the actual post-merge repository rather than relying on PR descriptions.

## Critical post-merge finding

PR #435 merged its temporary transformation scripts and one-shot workflows instead of the verified transformed tree. The intended fixes therefore remained dormant on `main`. This PR applies those transformations, incorporates the import-cycle correction discovered during the earlier verification run, and removes all transfer/patch machinery before the result is committed.

## Additional residual findings corrected

- Historical QC charts previously grouped values solely by `metric_id`; the same metric recorded in different units could therefore create a false numerical discontinuity. Histories now split by authored unit when a metric has multiple units. No conversion is inferred.
- `x-cite`, `diode`, `tunable laser`, `fs laser`, and `ti:sapphire` were too ambiguous to be rewrite-safe aliases for a single light-source kind. They are no longer auto-canonicalized. Exact model/technology evidence remains in source records.
- Objective source descriptions now distinguish cover-glass specification, correction-collar hardware, and multi-immersion capability instead of conflating them.
- The central repository vocabulary builder now includes every authored vocabulary file before merging policy aliases/settings, so unbound vocabularies do not disappear from shared consumers.
- Dashboard vocabulary labels now use the central diagnostic resolver rather than silently exposing unknown raw IDs.
- The scheduled autofix workflow now invokes the package module correctly and validates proposed changes before opening its PR.

## Verification contract

The preparation workflow must remove itself and all historical transfer machinery, then pass compilation, generated-template freshness, repository validation, the full pytest suite, JavaScript syntax checks, strict dashboard generation, strict MkDocs generation, conservative autofix check, and `git diff --check` before committing the clean tree.

No PR is merged automatically.
''',
)

print("Applied final vocabulary audit corrections")
