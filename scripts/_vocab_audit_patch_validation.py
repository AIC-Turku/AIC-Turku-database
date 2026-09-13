from __future__ import annotations

from scripts._vocab_audit_patch_common import ROOT, read, write, replace_once, regex_once

# H3: distinguish rewrite-safe lexical synonyms from broader classifications.
replace_once(
    "scripts/validation/vocabulary.py",
    "        self.synonyms_by_vocab: dict[str, dict[str, str]] = {}\n        self.registry_spec_by_vocab: dict[str, dict[str, Any]] = {}\n",
    "        self.synonyms_by_vocab: dict[str, dict[str, str]] = {}\n        self.classifications_by_vocab: dict[str, dict[str, str]] = {}\n        self.registry_spec_by_vocab: dict[str, dict[str, Any]] = {}\n",
)
replace_once(
    "scripts/validation/vocabulary.py",
    "        synonym_lookup: dict[str, str] = {}\n        canonical_casefold: dict[str, str] = {}\n",
    "        synonym_lookup: dict[str, str] = {}\n        classification_lookup: dict[str, str] = {}\n        canonical_casefold: dict[str, str] = {}\n",
)
replace_once(
    "scripts/validation/vocabulary.py",
    "        self.terms_by_vocab[vocab_name] = terms\n        self.valid_ids_by_vocab[vocab_name] = valid_ids\n        self.synonyms_by_vocab[vocab_name] = synonym_lookup\n",
    '''        for canonical_id, term in terms.items():
            raw_classified = term.metadata.get("classified_values", [])
            if raw_classified is None:
                raw_classified = []
            if not isinstance(raw_classified, list):
                raise VocabularyDefinitionError(
                    f"{source}: term '{canonical_id}' classified_values must be a list."
                )
            seen_classified: set[str] = set()
            for classified_value in raw_classified:
                if not isinstance(classified_value, str) or not classified_value.strip():
                    raise VocabularyDefinitionError(
                        f"{source}: term '{canonical_id}' has an invalid classified value."
                    )
                cleaned = classified_value.strip()
                key = cleaned.casefold()
                if key in seen_classified:
                    continue
                seen_classified.add(key)
                shadowed_id = canonical_casefold.get(key)
                if shadowed_id is not None and shadowed_id != canonical_id:
                    raise VocabularyDefinitionError(
                        f"{source}: classified value '{cleaned}' for '{canonical_id}' shadows canonical id '{shadowed_id}'."
                    )
                synonym_owner = synonym_lookup.get(key)
                if synonym_owner is not None:
                    if synonym_owner != canonical_id:
                        raise VocabularyDefinitionError(
                            f"{source}: classified value '{cleaned}' for '{canonical_id}' conflicts with synonym of '{synonym_owner}'."
                        )
                    continue
                previous = classification_lookup.get(key)
                if previous is not None and previous != canonical_id:
                    raise VocabularyDefinitionError(
                        f"{source}: classified value '{cleaned}' is ambiguous between '{previous}' and '{canonical_id}'."
                    )
                classification_lookup[key] = canonical_id

        self.terms_by_vocab[vocab_name] = terms
        self.valid_ids_by_vocab[vocab_name] = valid_ids
        self.synonyms_by_vocab[vocab_name] = synonym_lookup
        self.classifications_by_vocab[vocab_name] = classification_lookup
''',
)
replace_once(
    "scripts/validation/vocabulary.py",
    "\n\n    def requires_canonical_ids(self, vocab_name: str) -> bool:\n",
    '''

    def classify_canonical(self, vocab_name: str, value: Any) -> str | None:
        """Return a broader category without authorizing automatic rewriting."""
        if not isinstance(value, str):
            return None
        cleaned = self._normalize(value)
        if not cleaned or vocab_name not in self.valid_ids_by_vocab:
            return None
        if cleaned in self.valid_ids_by_vocab[vocab_name]:
            return cleaned
        return self.classifications_by_vocab.get(vocab_name, {}).get(cleaned.casefold())


    def requires_canonical_ids(self, vocab_name: str) -> bool:
''',
)
with (ROOT / "scripts/validation/vocabulary.py").open("a", encoding="utf-8") as handle:
    handle.write(
        '''

REPOSITORY_POLICY_PATHS: tuple[str, ...] = (
    "schema/instrument_policy.yaml",
    "schema/QC_policy.yaml",
    "schema/maintenance_policy.yaml",
)


def build_repository_vocabulary(repo_root: Path) -> Vocabulary:
    """Build the authoritative repository vocabulary from strict policy registries."""
    repo_root = Path(repo_root).resolve()
    combined_registry: dict[str, dict[str, Any]] = {}
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
    return Vocabulary(repo_root / "vocab", vocab_registry=combined_registry)
'''
    )

write(
    "vocab/objective_specialties.yaml",
    '''terms:
  - id: long_working_distance
    label: "Long Working Distance"
    description: "Objective designed for increased working distance."
    synonyms: [LWD, ELWD]
    classified_values: [ELWD ADM]
  - id: coverslip_correction
    label: "Coverslip Correction"
    description: "Objective supports adjustable coverslip correction."
    classified_values:
      - cover glass 0.17
      - cover glass 0.75
      - correction collar for 0-1.5mm glass
      - correction ring for 0.17 mm cover glass
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
    description: "Objective includes correction collar."
    synonyms: [Correction Ring, "Correction Ring (CORR)", correction collar]
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

# M1/M3: duplicate-key-safe policy loading and canonical comparison helpers.
replace_once(
    "scripts/validation/policy.py",
    "import yaml\n\nfrom scripts.validation.io import _is_non_empty_string\n",
    "from scripts.validation.io import _is_non_empty_string, _load_yaml\n",
)
regex_once(
    "scripts/validation/policy.py",
    r"def load_policy\(policy_path: Path\).*?\n\ndef _load_instrument_policy",
    '''def load_policy(policy_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    payload, load_error = _load_yaml(policy_path, reject_duplicate_keys=True)
    if load_error is not None or payload is None:
        return None, f"Failed loading policy '{policy_path.as_posix()}': {load_error or 'unknown YAML load error'}"
    return payload, None


def _load_instrument_policy''',
)
replace_once(
    "scripts/validation/policy.py",
    "    return index\n\n\ndef _get_software_roles",
    '''    return index


def _build_path_vocab_index(rules: list[PolicyRule]) -> dict[str, str]:
    return {
        rule.path: rule.vocab
        for rule in rules
        if isinstance(rule.path, str) and isinstance(rule.vocab, str) and rule.vocab
    }


def _get_software_roles''',
)
# Add canonicalization to generic membership operators without changing their external schema.
replace_once(
    "scripts/validation/policy.py",
    "def _evaluate_required_if(required_if: dict[str, Any], *, payload: dict[str, Any], item_context: dict[str, Any] | None, vocabulary: Vocabulary, item_field_vocabs: dict[str, str] | None = None) -> bool:\n",
    "def _evaluate_required_if(required_if: dict[str, Any], *, payload: dict[str, Any], item_context: dict[str, Any] | None, vocabulary: Vocabulary, item_field_vocabs: dict[str, str] | None = None, path_vocabs: dict[str, str] | None = None) -> bool:\n    item_field_vocabs = item_field_vocabs or {}\n    path_vocabs = path_vocabs or {}\n",
)
replace_once(
    "scripts/validation/policy.py",
    """        imaging_modes_any_of = condition_spec.get('imaging_modes_any_of')
        if isinstance(imaging_modes_any_of, list):
            imaging_mode_nodes = _resolve_path_nodes(payload, 'capabilities.imaging_modes')
            has_match = False
            if imaging_mode_nodes and isinstance(imaging_mode_nodes[0].value, list):
                imaging_mode_ids = {str(v).strip() for v in imaging_mode_nodes[0].value if isinstance(v, str)}
                targets = {str(v).strip() for v in imaging_modes_any_of if isinstance(v, str)}
                has_match = bool(imaging_mode_ids & targets)
            conditions.append(has_match)
""",
    """        imaging_modes_any_of = condition_spec.get('imaging_modes_any_of')
        if isinstance(imaging_modes_any_of, list):
            imaging_mode_nodes = _resolve_path_nodes(payload, 'capabilities.imaging_modes')
            has_match = False
            if imaging_mode_nodes and isinstance(imaging_mode_nodes[0].value, list):
                imaging_mode_ids = {vocabulary.resolve_canonical('imaging_modes', v) or str(v).strip() for v in imaging_mode_nodes[0].value if isinstance(v, str)}
                targets = {vocabulary.resolve_canonical('imaging_modes', v) or str(v).strip() for v in imaging_modes_any_of if isinstance(v, str)}
                has_match = bool(imaging_mode_ids & targets)
            conditions.append(has_match)
""",
)
replace_once(
    "scripts/validation/policy.py",
    """        scanner_type_in = condition_spec.get('scanner_type_in')
        if isinstance(scanner_type_in, list):
            scanner_nodes = _resolve_path_nodes(payload, 'hardware.scanner.type')
            scanner_type = scanner_nodes[0].value if scanner_nodes else None
            conditions.append(isinstance(scanner_type, str) and scanner_type in {str(v).strip() for v in scanner_type_in if isinstance(v, str)})
""",
    """        scanner_type_in = condition_spec.get('scanner_type_in')
        if isinstance(scanner_type_in, list):
            scanner_nodes = _resolve_path_nodes(payload, 'hardware.scanner.type')
            scanner_type = scanner_nodes[0].value if scanner_nodes else None
            canonical_scanner = vocabulary.resolve_canonical('scanner_types', scanner_type) or scanner_type if isinstance(scanner_type, str) else None
            targets = {vocabulary.resolve_canonical('scanner_types', v) or str(v).strip() for v in scanner_type_in if isinstance(v, str)}
            conditions.append(isinstance(canonical_scanner, str) and canonical_scanner in targets)
""",
)
replace_once(
    "scripts/validation/policy.py",
    """                normalized_allowed = {str(v).strip().casefold() for v in allowed_values if isinstance(v, (str, int, float, bool))}
                matches = False
                for node in nodes:
                    if not isinstance(node.value, dict):
                        continue
                    raw_value = node.value.get(field_name)
                    if isinstance(raw_value, (str, int, float, bool)) and str(raw_value).strip().casefold() in normalized_allowed:
                        matches = True
                        break
""",
    """                field_vocab = path_vocabs.get(f"{list_path}.{field_name}") or path_vocabs.get(f"{list_path}[].{field_name}") or item_field_vocabs.get(field_name)
                normalized_allowed = {_normalize_scalar(vocabulary.resolve_canonical(field_vocab, v) or v if isinstance(v, str) and isinstance(field_vocab, str) else v) for v in allowed_values if isinstance(v, (str, int, float, bool))}
                matches = False
                for node in nodes:
                    if not isinstance(node.value, dict):
                        continue
                    raw_value = node.value.get(field_name)
                    if isinstance(raw_value, str) and isinstance(field_vocab, str):
                        raw_value = vocabulary.resolve_canonical(field_vocab, raw_value) or raw_value
                    if _normalize_scalar(raw_value) in normalized_allowed:
                        matches = True
                        break
""",
)
replace_once(
    "scripts/validation/policy.py",
    """                        normalized_allowed = {str(v).strip().casefold() for v in allowed_values if isinstance(v, (str, int, float, bool))}
                        raw_value = node.value.get(field_name)
                        if not isinstance(raw_value, (str, int, float, bool)) or str(raw_value).strip().casefold() not in normalized_allowed:
                            item_ok = False; break
""",
    """                        field_vocab = path_vocabs.get(f"{list_path}.{field_name}") or path_vocabs.get(f"{list_path}[].{field_name}") or item_field_vocabs.get(field_name)
                        normalized_allowed = {_normalize_scalar(vocabulary.resolve_canonical(field_vocab, v) or v if isinstance(v, str) and isinstance(field_vocab, str) else v) for v in allowed_values if isinstance(v, (str, int, float, bool))}
                        raw_value = node.value.get(field_name)
                        if isinstance(raw_value, str) and isinstance(field_vocab, str):
                            raw_value = vocabulary.resolve_canonical(field_vocab, raw_value) or raw_value
                        if _normalize_scalar(raw_value) not in normalized_allowed:
                            item_ok = False; break
""",
)
replace_once(
    "scripts/validation/policy.py",
    """                nodes = _resolve_path_nodes(payload, field_path)
                normalized_allowed = {str(v).strip().casefold() for v in allowed_values if isinstance(v, (str, int, float, bool))}
                matches = any(isinstance(node.value, (str, int, float, bool)) and str(node.value).strip().casefold() in normalized_allowed for node in nodes)
""",
    """                nodes = _resolve_path_nodes(payload, field_path)
                field_vocab = path_vocabs.get(field_path)
                normalized_allowed = {_normalize_scalar(vocabulary.resolve_canonical(field_vocab, v) or v if isinstance(v, str) and isinstance(field_vocab, str) else v) for v in allowed_values if isinstance(v, (str, int, float, bool))}
                matches = False
                for node in nodes:
                    raw_value = node.value
                    if isinstance(raw_value, str) and isinstance(field_vocab, str):
                        raw_value = vocabulary.resolve_canonical(field_vocab, raw_value) or raw_value
                    if _normalize_scalar(raw_value) in normalized_allowed:
                        matches = True
                        break
""",
)
# Recursive calls must forward path vocab metadata.
text = read("scripts/validation/policy.py")
text = text.replace(
    "vocabulary=vocabulary, item_field_vocabs=item_field_vocabs)",
    "vocabulary=vocabulary, item_field_vocabs=item_field_vocabs, path_vocabs=path_vocabs)",
)
write("scripts/validation/policy.py", text)

# H1: fail predictably instead of the broken local exception return.
replace_once(
    "scripts/validation/instrument.py",
    "    _build_item_field_vocab_index,\n",
    "    _build_item_field_vocab_index,\n    _build_path_vocab_index,\n",
)
replace_once(
    "scripts/validation/instrument.py",
    "from scripts.validation.vocabulary import Vocabulary, VocabularyDefinitionError\n",
    "from scripts.validation.vocabulary import Vocabulary\n",
)
replace_once(
    "scripts/validation/instrument.py",
    """    try:
        vocabulary = Vocabulary(vocab_registry=policy.vocab_registry)
    except VocabularyDefinitionError as exc:
        issues.append(ValidationIssue(code='vocabulary_definition_error', path='vocab', message=str(exc)))
        return instrument_ids, issues, warnings
    item_field_vocab_index = _build_item_field_vocab_index(policy.rules)
""",
    """    vocabulary = Vocabulary(vocab_registry=policy.vocab_registry)
    item_field_vocab_index = _build_item_field_vocab_index(policy.rules)
    path_vocab_index = _build_path_vocab_index(policy.rules)
""",
)
replace_once(
    "scripts/validation/instrument.py",
    "    item_field_vocab_index = _build_item_field_vocab_index(policy.rules)\n\n    for instrument_file in _iter_yaml_files(instruments_dir):\n",
    "    item_field_vocab_index = _build_item_field_vocab_index(policy.rules)\n    path_vocab_index = _build_path_vocab_index(policy.rules)\n\n    for instrument_file in _iter_yaml_files(instruments_dir):\n",
)
text = read("scripts/validation/instrument.py")
needle = "item_field_vocabs=item_field_vocab_index.get(_list_context_path(rule.path) or ''),\n"
if text.count(needle) < 3:
    raise RuntimeError("instrument conditional call sites changed unexpectedly")
text = text.replace(needle, needle + "                path_vocabs=path_vocab_index,\n")
write("scripts/validation/instrument.py", text)

# H2/M2: current controlled event terms are errors; explicitly allowed empty is absent semantics.
replace_once(
    "scripts/validation/events.py",
    """            if policy is None:
                errors.append(ValidationIssue(code='missing_policy_for_record_type', path=event_file.as_posix(), message=f"No event policy loaded for record_type '{record_type}'."))
                continue

            allowed_roots = set()
""",
    """            if policy is None:
                errors.append(ValidationIssue(code='missing_policy_for_record_type', path=event_file.as_posix(), message=f"No event policy loaded for record_type '{record_type}'."))
                continue

            allowed_roots = set()
""",
)
replace_once(
    "scripts/validation/events.py",
    """                for node in resolved:
                    full_path = f"{event_file.as_posix()}:{node.path}"
                    if not _check_event_type(node.value, field_type):
""",
    """                for node in resolved:
                    full_path = f"{event_file.as_posix()}:{node.path}"
                    if node.value == '' and rule.get('allow_empty') is True:
                        continue
                    if not _check_event_type(node.value, field_type):
""",
)
replace_once(
    "scripts/validation/events.py",
    """                            else:
                                warnings.append(ValidationIssue(code='unknown_vocab_term', path=full_path, message=f"Unknown value '{vocab_value}' for vocabulary '{vocab_name}'."))
""",
    """                            else:
                                issue = ValidationIssue(code='unknown_vocab_term', path=full_path, message=f"Unknown value '{vocab_value}' for vocabulary '{vocab_name}'.")
                                (errors if vocabulary.requires_canonical_ids(vocab_name) else warnings).append(issue)
""",
)
replace_once(
    "schema/QC_policy.yaml",
    """  - path: inputs_human[].unit
    status: optional
    type: string
    vocab: metric_unit
    written_by: human
    used_by: [dashboard]
    rationale: Unit may be empty for checklist values.
""",
    """  - path: inputs_human[].unit
    status: optional
    type: string
    vocab: metric_unit
    allow_empty: true
    written_by: human
    used_by: [dashboard]
    rationale: >-
      Unit may be empty for checklist or categorical values. Empty means no unit
      was supplied or applicable and is distinct from canonical `unitless`, which
      means the measured quantity is dimensionless.
""",
)

print("Applied vocabulary validation and policy fixes")
