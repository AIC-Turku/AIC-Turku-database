from __future__ import annotations

from scripts._vocab_audit_patch_common import ROOT, read, write, replace_once, regex_once

# H4: autofix consumes central policy/vocabulary/path resolvers and preserves YAML formatting.
write(
    "scripts/autofix_yaml.py",
    '''"""Conservative vocabulary and declared-migration autofixer.

The validator/policy/vocabulary modules are authoritative. Default mode is
read-only; writes require ``--write``. Broader classifications are never rewritten.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from scripts.validation.io import _iter_yaml_files, _load_yaml
from scripts.validation.model import EventPolicy, InstrumentPolicy, PolicyRule
from scripts.validation.policy import _load_event_policy, _load_instrument_policy, _resolve_path_nodes
from scripts.validation.vocabulary import Vocabulary


@dataclass
class AutofixSpec:
    target_dir: Path
    vocabulary: Vocabulary
    rules: list[tuple[str, str]]
    legacy_rules: list[dict[str, Any]]


def get_base_path() -> Path:
    return Path.cwd().resolve()


def _rule_pairs_from_instrument(policy: InstrumentPolicy) -> list[tuple[str, str]]:
    return [(rule.path, rule.vocab) for rule in policy.rules if isinstance(rule, PolicyRule) and isinstance(rule.vocab, str) and rule.vocab]


def _rule_pairs_from_event(policy: EventPolicy) -> list[tuple[str, str]]:
    return [(rule['path'], rule['vocab']) for rule in policy.field_rules if isinstance(rule.get('path'), str) and isinstance(rule.get('vocab'), str)]


def build_specs(base: Path) -> list[AutofixSpec]:
    instrument_policy, instrument_error = _load_instrument_policy(base / 'schema' / 'instrument_policy.yaml')
    if instrument_error is not None or instrument_policy is None:
        raise RuntimeError(instrument_error or 'Could not load instrument policy.')
    specs = [AutofixSpec(base / 'instruments', Vocabulary(base / 'vocab', vocab_registry=instrument_policy.vocab_registry), _rule_pairs_from_instrument(instrument_policy), [])]
    for target, policy_name in (('qc/sessions', 'QC_policy.yaml'), ('maintenance/events', 'maintenance_policy.yaml')):
        policy, error = _load_event_policy(base / 'schema' / policy_name)
        if error is not None or policy is None:
            raise RuntimeError(error or f'Could not load {policy_name}.')
        specs.append(AutofixSpec(base / target, Vocabulary(base / 'vocab', vocab_registry=policy.vocab_registry), _rule_pairs_from_event(policy), list(policy.legacy_and_migration_rules)))
    return specs


def _canonical_value(value: Any, vocab_name: str, vocabulary: Vocabulary) -> Any:
    if isinstance(value, list):
        return [vocabulary.resolve_canonical(vocab_name, item) or item if isinstance(item, str) else item for item in value]
    if isinstance(value, str):
        return vocabulary.resolve_canonical(vocab_name, value) or value
    return value


def _parse_concrete_path(path: str) -> list[tuple[str, int | None]]:
    tokens: list[tuple[str, int | None]] = []
    for segment in path.split('.'):
        match = re.fullmatch(r'([^\\[]+)(?:\\[(\\d+)\\])?', segment)
        if match is None:
            raise ValueError(f'Unsupported concrete path segment: {segment}')
        tokens.append((match.group(1), int(match.group(2)) if match.group(2) is not None else None))
    return tokens


def _set_concrete_path(data: Any, path: str, value: Any) -> None:
    current = data
    tokens = _parse_concrete_path(path)
    for key, index in tokens[:-1]:
        current = current[key]
        if index is not None:
            current = current[index]
    key, index = tokens[-1]
    if index is None:
        current[key] = value
    else:
        current[key][index] = value


def _canonicalize_rule_values(data: dict[str, Any], rules: list[tuple[str, str]], vocabulary: Vocabulary) -> int:
    replacements = 0
    for path, vocab_name in rules:
        for node in _resolve_path_nodes(data, path):
            new_value = _canonical_value(node.value, vocab_name, vocabulary)
            if new_value != node.value:
                _set_concrete_path(data, node.path, new_value)
                replacements += 1
    return replacements


def _apply_declared_legacy_migrations(data: dict[str, Any], legacy_rules: list[dict[str, Any]]) -> int:
    replacements = 0
    for rule in legacy_rules:
        source = rule.get('path')
        target = rule.get('migrate_to') or rule.get('replacement')
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        if any(marker in source + target for marker in ('.', '[', ']')):
            continue
        if source in data and target not in data:
            data[target] = data.pop(source)
            replacements += 1
    return replacements


def autofix_file(filepath: Path, spec: AutofixSpec, *, write_changes: bool) -> tuple[bool, int]:
    _, strict_error = _load_yaml(filepath, reject_duplicate_keys=True)
    if strict_error is not None:
        raise RuntimeError(f'{filepath}: {strict_error}')
    yaml_rt = YAML(typ='rt')
    yaml_rt.preserve_quotes = True
    with filepath.open('r', encoding='utf-8') as handle:
        data = yaml_rt.load(handle)
    if not isinstance(data, dict):
        return False, 0
    replacements = _canonicalize_rule_values(data, spec.rules, spec.vocabulary)
    replacements += _apply_declared_legacy_migrations(data, spec.legacy_rules)
    changed = replacements > 0
    if changed and write_changes:
        with filepath.open('w', encoding='utf-8') as handle:
            yaml_rt.dump(data, handle)
    return changed, replacements


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Conservative vocabulary autofixer')
    parser.add_argument('--write', action='store_true', help='Apply rewrite-safe lexical synonyms and policy-declared migrations.')
    parser.add_argument('--check', action='store_true', help='Explicit spelling for the default read-only mode.')
    args = parser.parse_args(argv)
    if args.write and args.check:
        parser.error('--write and --check are mutually exclusive')
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base = get_base_path()
    changed_files: list[Path] = []
    total_replacements = 0
    for spec in build_specs(base):
        for filepath in _iter_yaml_files(spec.target_dir):
            changed, replacements = autofix_file(filepath, spec, write_changes=args.write)
            if changed:
                changed_files.append(filepath)
                total_replacements += replacements
    mode = 'Updated' if args.write else 'Would update'
    print(f'{mode} {len(changed_files)} file(s); replacements: {total_replacements}.')
    for filepath in changed_files:
        print(f' - {filepath.relative_to(base)}')
    return 1 if (not args.write and changed_files) else 0


if __name__ == '__main__':
    raise SystemExit(main())
''',
)

write(
    ".github/workflows/autofix.yml",
    '''name: Auto-fix YAML and Regenerate Templates

on:
  workflow_dispatch:
  schedule:
    - cron: '0 0 * * 0'

permissions:
  contents: write
  pull-requests: write

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"

jobs:
  autofix:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v5
      - name: Setup Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.10"
          cache: "pip"
          cache-dependency-path: "requirements-docs.txt"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-docs.txt
      - name: Apply rewrite-safe vocabulary fixes
        run: python scripts/autofix_yaml.py --write
      - name: Regenerate schema-derived templates
        run: python -m scripts.generate_templates
      - name: Validate proposed changes
        run: |
          python -m scripts.generate_templates --check
          python -m scripts.validate
          PYTHONPATH=. python -m pytest -q tests/test_vocabulary_hardening.py tests/test_vocabulary_second_audit.py tests/test_validate_event_policy.py tests/test_validate_instrument_policy.py
          python -m scripts.dashboard_builder --strict
          mkdocs build --strict
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v6
        with:
          commit-message: "chore: apply validated vocabulary fixes"
          title: "✨ chore: Apply validated vocabulary fixes"
          body: |
            This automated PR contains only rewrite-safe lexical vocabulary normalization
            and simple migrations explicitly declared by policy. Broader scientific
            classifications are preserved verbatim and never auto-canonicalized.
          branch: "bot/auto-fix-yaml"
          base: "main"
          labels: "automated pr, data-migration"
''',
)

# M4: software roles from authoritative vocab.
replace_once(
    "scripts/build_context.py",
    "from scripts.validate import build_instrument_completeness_report\n",
    "from scripts.validate import build_instrument_completeness_report\nfrom scripts.validation.vocabulary import Vocabulary, build_repository_vocabulary\n",
)
regex_once(
    "scripts/build_context.py",
    r"def normalize_software\(raw: Any\) -> list\[dict\[str, str\]\]:.*?\n    rows: list\[dict\[str, str\]\] = \[\]",
    '''_DEFAULT_REPOSITORY_VOCABULARY: Vocabulary | None = None


def _default_repository_vocabulary() -> Vocabulary:
    global _DEFAULT_REPOSITORY_VOCABULARY
    if _DEFAULT_REPOSITORY_VOCABULARY is None:
        _DEFAULT_REPOSITORY_VOCABULARY = build_repository_vocabulary(Path(__file__).resolve().parents[1])
    return _DEFAULT_REPOSITORY_VOCABULARY


def normalize_software(raw: Any, *, vocabulary: Vocabulary | None = None) -> list[dict[str, str]]:
    """Normalize software metadata through the authoritative role vocabulary."""
    vocabulary = vocabulary or _default_repository_vocabulary()

    def normalize_role(value: Any, fallback: str = "other") -> str:
        role = clean_text(value)
        if not role:
            return fallback
        return vocabulary.resolve_canonical("software_roles", role) or role.lower()

    rows: list[dict[str, str]] = []''',
)
replace_once(
    "scripts/build_context.py",
    "    software = strip_empty_values(normalize_software(payload.get(\"software\")))\n",
    "    vocabulary = _default_repository_vocabulary()\n    software = strip_empty_values(normalize_software(payload.get(\"software\"), vocabulary=vocabulary))\n",
)
replace_once(
    "scripts/build_context.py",
    "    software_roles = (\"acquisition\", \"processing\", \"analysis\", \"hardware_control\", \"other\")\n",
    "    software_roles = tuple(vocabulary.terms_by_vocab.get(\"software_roles\", {}).keys())\n",
)

# Add detector consumer metadata to its vocabulary.
write(
    "vocab/detector_kinds.yaml",
    '''terms:
  - id: pmt
    label: "Photomultiplier Tube"
    description: "Highly sensitive point detector that amplifies photoelectrons through a dynode chain. Common in confocal detection paths."
    synonyms: ["PMT"]
    tags: {architecture: point_scanning, frontend_class: point}
  - id: gaasp_pmt
    label: "GaAsP Photomultiplier Tube"
    description: "PMT using gallium arsenide phosphide photocathodes with improved quantum efficiency over conventional PMTs. Useful for low-light confocal imaging."
    synonyms: ["GaAsP_PMT", "gaasp detector"]
    tags: {architecture: point_scanning, frontend_class: point}
  - id: hyd
    label: "Hybrid Detector"
    description: "Combines features of PMTs and avalanche gain to provide high sensitivity and fast response. Frequently used in modern confocal systems."
    synonyms: ["HyD", "hybrid pmt"]
    tags: {architecture: point_scanning, frontend_class: hybrid}
  - id: scmos
    label: "Scientific CMOS"
    description: "Low-noise, high-speed area detector with large field of view and high dynamic range. Common for widefield, spinning-disk, and fast live imaging."
    synonyms: ["sCMOS"]
    tags: {architecture: camera, frontend_class: camera}
  - id: cmos
    label: "Standard CMOS"
    description: "Standard digital camera sensor. Commonly used in routine brightfield, color histology, or basic fluorescence."
    synonyms: ["CMOS"]
    tags: {architecture: camera, frontend_class: camera}
  - id: emccd
    label: "Electron-Multiplying CCD"
    description: "CCD detector with on-chip gain for very low-light imaging. Useful for single-molecule and fast, dim signal applications."
    synonyms: ["EMCCD"]
    tags: {architecture: camera, frontend_class: camera}
  - id: ccd
    label: "Charge-Coupled Device"
    description: "Area detector technology with historically strong image quality and uniformity. Still used in some fluorescence and brightfield setups."
    synonyms: ["CCD"]
    tags: {architecture: camera, frontend_class: camera}
  - id: apd
    label: "Avalanche Photodiode"
    description: "Semiconductor point detector with internal gain and fast timing response. Used in photon counting and correlation-based measurements."
    synonyms: ["APD"]
    tags: {architecture: point_scanning, frontend_class: apd}
  - id: spad
    label: "SPAD Array"
    description: "Single-Photon Avalanche Diode array. Provides exceptional timing resolution and single-photon sensitivity, crucial for advanced FLIM."
    tags: {architecture: point_scanning, frontend_class: apd}
''',
)

# Instrument cross-field detector support now derives from the detector vocabulary itself.
replace_once(
    "scripts/validation/instrument.py",
    """        digital_detector_kinds = {'scmos', 'cmos', 'ccd', 'emccd', 'pmt', 'gaasp_pmt', 'hyd', 'apd', 'spad'}
        has_digital_detector = bool(detector_kinds & digital_detector_kinds)
""",
    """        has_digital_detector = any(
            vocabulary.get_term('detector_kinds', detector_kind) is not None
            for detector_kind in detector_kinds
        )
""",
)

# Light-path normalizers use vocabulary resolution and term metadata rather than alias sets.
replace_once(
    "scripts/lightpath/model.py",
    "import re\nfrom typing import Any\n",
    "import re\nfrom pathlib import Path\nfrom typing import Any\n\nfrom scripts.validation.vocabulary import Vocabulary, build_repository_vocabulary\n",
)
regex_once("scripts/lightpath/model.py", r"CAMERA_DETECTOR_KINDS = \{.*?\n\}\nPOINT_DETECTOR_KINDS = \{.*?\n\}\n", "")
regex_once(
    "scripts/lightpath/model.py",
    r"_LIGHT_SOURCE_KIND_ALIASES = \{.*?\n\}\n\n_CANONICAL_LIGHT_SOURCE_KINDS = \{.*?\n\}\n\n\ndef _normalize_light_source_kind\(value: Any\) -> str:.*?\n\n\ndef _detector_class",
    '''_fallback_vocab: Vocabulary | None = None


def _vocab_context() -> Vocabulary | VocabLookup | None:
    global _fallback_vocab
    if _active_vocab is not None:
        return _active_vocab
    if _fallback_vocab is None:
        _fallback_vocab = build_repository_vocabulary(Path(__file__).resolve().parents[2])
    return _fallback_vocab


def _normalize_light_source_kind(value: Any) -> str:
    raw = _clean_string(value)
    token = _clean_identifier(raw) or "light_source"
    vocabulary = _vocab_context()
    resolver = getattr(vocabulary, "resolve_canonical", None)
    if callable(resolver):
        return resolver("light_source_kinds", raw) or resolver("light_source_kinds", token) or token
    return token


def _detector_class''',
)
regex_once(
    "scripts/lightpath/model.py",
    r"def _detector_class\(kind: str\) -> str:.*?\n\n\ndef _normalize_endpoint_type",
    '''def _detector_class(kind: str) -> str:
    vocabulary = _vocab_context()
    resolver = getattr(vocabulary, "resolve_canonical", None)
    get_term = getattr(vocabulary, "get_term", None)
    canonical = resolver("detector_kinds", kind) if callable(resolver) else None
    canonical = canonical or _clean_identifier(kind)
    term = get_term("detector_kinds", canonical) if callable(get_term) else None
    if term is not None:
        frontend_class = term.tag_value("frontend_class")
        if isinstance(frontend_class, str) and frontend_class.strip():
            return frontend_class.strip()
    return "detector"


def _normalize_endpoint_type''',
)
regex_once(
    "scripts/lightpath/model.py",
    r"def _normalize_endpoint_type\(value: Any\) -> str:.*?\n\n\n__all__ = \[",
    '''def _normalize_endpoint_type(value: Any) -> str:
    raw = _clean_string(value)
    token = _clean_identifier(raw)
    if not raw and not token:
        return "detector"
    vocabulary = _vocab_context()
    resolver = getattr(vocabulary, "resolve_canonical", None)
    if callable(resolver):
        endpoint_type = resolver("endpoint_types", raw) or resolver("endpoint_types", token)
        if endpoint_type:
            return endpoint_type
        if resolver("detector_kinds", raw) or resolver("detector_kinds", token):
            return "detector"
    return token or "detector"


__all__ = [''',
)
text = read("scripts/lightpath/model.py").replace('    "CAMERA_DETECTOR_KINDS",\n', '').replace('    "POINT_DETECTOR_KINDS",\n', '')
write("scripts/lightpath/model.py", text)

# Full audit also derives point-detector semantics from vocabulary metadata.
replace_once(
    "scripts/full_audit.py",
    "from scripts.lightpath.legacy_import import has_legacy_light_path_input\n",
    "from scripts.lightpath.legacy_import import has_legacy_light_path_input\nfrom scripts.validation.vocabulary import Vocabulary, build_repository_vocabulary\n",
)
replace_once("scripts/full_audit.py", "\n\nPOINT_DETECTOR_KINDS = {\"pmt\", \"gaasp_pmt\", \"hyd\", \"apd\", \"spad\"}\n", "")
replace_once("scripts/full_audit.py", "def _detector_readiness_issue(index: int, detector: dict[str, Any]) -> list[dict[str, str]]:\n", "def _detector_readiness_issue(index: int, detector: dict[str, Any], vocabulary: Vocabulary) -> list[dict[str, str]]:\n")
replace_once(
    "scripts/full_audit.py",
    """    if detector.get("kind") in POINT_DETECTOR_KINDS and detector.get("supports_time_gating") is None:
        issues.append(
""",
    """    raw_kind = detector.get("kind")
    canonical_kind = vocabulary.resolve_canonical("detector_kinds", raw_kind) if isinstance(raw_kind, str) else None
    detector_term = vocabulary.get_term("detector_kinds", canonical_kind) if canonical_kind else None
    is_point_detector = detector_term is not None and detector_term.tag_value("architecture") == "point_scanning"
    if is_point_detector and detector.get("supports_time_gating") is None:
        issues.append(
""",
)
replace_once("scripts/full_audit.py", "def audit_virtual_microscope_instrument(instrument: dict[str, Any]) -> dict[str, Any]:\n", "def audit_virtual_microscope_instrument(instrument: dict[str, Any], vocabulary: Vocabulary | None = None) -> dict[str, Any]:\n    vocabulary = vocabulary or build_repository_vocabulary(Path(__file__).resolve().parents[1])\n")
replace_once("scripts/full_audit.py", "    payload = generate_virtual_microscope_payload(canonical, compatibility_mode=True)\n", "    payload = generate_virtual_microscope_payload(canonical, compatibility_mode=True, vocab=vocabulary)\n")
replace_once("scripts/full_audit.py", "        for issue in _detector_readiness_issue(index, detector):\n", "        for issue in _detector_readiness_issue(index, detector, vocabulary):\n")
replace_once("scripts/full_audit.py", "        vm_rows = [audit_virtual_microscope_instrument(instrument) for instrument in [*instruments, *retired_instruments]]\n", "        vocabulary = build_repository_vocabulary(repo_root)\n        vm_rows = [audit_virtual_microscope_instrument(instrument, vocabulary) for instrument in [*instruments, *retired_instruments]]\n")

# Event required-if aliases are canonicalized at the same vocabulary boundary.
replace_once(
    "scripts/validation/policy.py",
    "def _evaluate_event_required_if(required_if: dict[str, Any], *, payload: dict[str, Any], item_context: dict[str, Any] | None) -> tuple[bool | None, str | None]:\n",
    "def _evaluate_event_required_if(required_if: dict[str, Any], *, payload: dict[str, Any], item_context: dict[str, Any] | None, vocabulary: Vocabulary | None = None, path_vocabs: dict[str, str] | None = None) -> tuple[bool | None, str | None]:\n    path_vocabs = path_vocabs or {}\n    def _canonical(path: str, value: Any) -> Any:\n        vocab_name = path_vocabs.get(path)\n        if vocabulary is not None and isinstance(vocab_name, str) and isinstance(value, str):\n            return vocabulary.resolve_canonical(vocab_name, value) or value\n        return value\n",
)
replace_once(
    "scripts/validation/policy.py",
    """        found = {item.value.get('qc_type') for item in performed_nodes if isinstance(item.value, dict) and isinstance(item.value.get('qc_type'), str)}
        conditions.append(isinstance(expected, str) and expected in found)
""",
    """        expected = _canonical('performed[].qc_type', expected)
        found = {_canonical('performed[].qc_type', item.value.get('qc_type')) for item in performed_nodes if isinstance(item.value, dict) and isinstance(item.value.get('qc_type'), str)}
        conditions.append(isinstance(expected, str) and expected in found)
""",
)
replace_once(
    "scripts/validation/policy.py",
    """        conditions.append(isinstance(provider, str) and provider in {str(v).strip() for v in allowed if isinstance(v, str)})
""",
    """        provider = _canonical('service_provider', provider)
        canonical_allowed = {_canonical('service_provider', str(v).strip()) for v in allowed if isinstance(v, str)}
        conditions.append(isinstance(provider, str) and provider in canonical_allowed)
""",
)
replace_once(
    "scripts/validation/events.py",
    """            allowed_roots = set()
            for rule in policy.field_rules:
""",
    """            path_vocab_index = {rule.get('path'): rule.get('vocab') for rule in policy.field_rules if isinstance(rule.get('path'), str) and isinstance(rule.get('vocab'), str)}
            allowed_roots = set()
            for rule in policy.field_rules:
""",
)
replace_once(
    "scripts/validation/events.py",
    "required_eval, condition_error = _evaluate_event_required_if(required_if, payload=payload, item_context=None)",
    "required_eval, condition_error = _evaluate_event_required_if(required_if, payload=payload, item_context=None, vocabulary=vocabulary, path_vocabs=path_vocab_index)",
)

# M5: one dictionary section per canonical source vocabulary.
replace_once("scripts/dashboard/site_render.py", "from scripts.validation.vocabulary import merge_vocab_registries\n", "from scripts.validation.vocabulary import build_repository_vocabulary\n")
regex_once(
    "scripts/dashboard/site_render.py",
    r"def _build_vocabulary\(repo_root: Path\) -> Vocabulary:.*?\n\ndef _annotate_display_labels",
    '''def _build_vocabulary(repo_root: Path) -> Vocabulary:
    return build_repository_vocabulary(repo_root)


def _annotate_display_labels''',
)
new_dictionary = '''def build_vocabulary_dictionary_markdown(vocabulary: Vocabulary) -> str:
    """Render canonical sources once, grouped by authoring task."""
    lines = [
        "---", "title: Vocabulary Dictionary", "description: Controlled terminology used in the AIC database.", "---", "",
        "# 📖 Vocabulary Dictionary\\n",
        "Use the **Canonical ID** when authoring controlled fields. **Synonyms** are rewrite-safe lexical aliases. **Classified values** are more specific scientific descriptions that map to a broader category but are preserved verbatim and never automatically rewritten.\\n",
    ]
    source_groups: dict[str, dict[str, Any]] = {}
    for namespace, terms in vocabulary.terms_by_vocab.items():
        spec = vocabulary.registry_spec_by_vocab.get(namespace, {})
        raw_path = spec.get("path") or spec.get("file")
        if isinstance(raw_path, str) and raw_path.strip():
            source = raw_path.strip(); source_key = f"file:{source}"; source_name = Path(source).stem
        else:
            source = "inline policy vocabulary"; source_key = f"inline:{namespace}"; source_name = namespace
        group = source_groups.setdefault(source_key, {"source": source, "source_name": source_name, "namespaces": [], "terms": terms})
        group["namespaces"].append(namespace)
    categories = [
        ("🧭 Capabilities & Workflows", {"modalities", "modules", "imaging_modes", "contrast_methods", "measurement_readouts", "workflow_tags", "assay_operations", "non_optical_capabilities", "optical_routes"}),
        ("🔬 Light Paths & Hardware", {"scanner_types", "light_source_kinds", "light_source_roles", "detector_kinds", "stage_types", "autofocus_types", "triggering_modes", "optical_component_types", "endpoint_types", "branch_modes", "ocular_availability"}),
        ("🔭 Objectives", {"objective_immersion", "objective_corrections", "objective_specialties"}),
        ("💻 Software", {"software_roles"}),
        ("✅ Quality Control", {"qc_type", "qc_metric_classes", "qc_evaluation_status", "qc_artifact_roles", "qc_measurement_positions", "qc_setpoint_units", "metric_unit"}),
        ("🛠️ Maintenance", {"maintenance_action", "maintenance_reason", "maintenance_status", "service_provider"}),
    ]
    rendered: set[str] = set()
    def render_group(source_key: str, group: dict[str, Any]) -> None:
        lines.append(f"    ## {resolve_vocab_section_title(str(group['source_name']))}\\n")
        namespaces = ", ".join(f"`{_markdown_table_cell(name)}`" for name in sorted(set(group["namespaces"])))
        lines.append(f"    **Canonical source:** `{_markdown_table_cell(group['source'])}`  ")
        lines.append(f"    **Used by namespaces:** {namespaces}\\n")
        lines.append("    | Label | Canonical ID | Synonyms (rewrite-safe) | Classified values (preserved) | Description |")
        lines.append("    | :--- | :--- | :--- | :--- | :--- |")
        for term in sorted(group["terms"].values(), key=lambda item: item.label.lower()):
            synonyms = ", ".join(f"`{_markdown_table_cell(value).replace(chr(96), chr(92)+chr(96))}`" for value in term.synonyms) if term.synonyms else "-"
            raw_classified = term.metadata.get("classified_values", [])
            classified = ", ".join(f"`{_markdown_table_cell(value).replace(chr(96), chr(92)+chr(96))}`" for value in raw_classified if isinstance(value, str)) if isinstance(raw_classified, list) and raw_classified else "-"
            lines.append(f"    | **{_markdown_table_cell(term.label)}** | `{_markdown_table_cell(term.id)}` | {synonyms} | {classified} | {_markdown_table_cell(term.description) if term.description else '-'} |")
        lines.append("\\n"); rendered.add(source_key)
    for title, names in categories:
        matching = [(key, group) for key, group in source_groups.items() if group["source_name"] in names]
        if matching:
            lines.append(f'=== "{title}"\\n')
            for key, group in sorted(matching, key=lambda item: str(item[1]["source_name"])):
                render_group(key, group)
    remaining = [(key, group) for key, group in source_groups.items() if key not in rendered]
    if remaining:
        lines.append('=== "📦 Other"\\n')
        for key, group in sorted(remaining, key=lambda item: str(item[1]["source_name"])):
            render_group(key, group)
    return "\\n".join(lines)
'''
regex_once("scripts/dashboard/site_render.py", r"def build_vocabulary_dictionary_markdown\(vocabulary: Vocabulary\) -> str:.*?\n\ndef build_mkdocs_config", new_dictionary + "\n\ndef build_mkdocs_config")

print("Applied autofix, downstream vocabulary, and dictionary fixes")
