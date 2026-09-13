from __future__ import annotations

from scripts._vocab_audit_patch_common import replace_once

# The strict vocabulary/policy loader deliberately no longer exposes a private
# `policy.yaml` dependency. The old test harness patched that implementation
# detail after changing CWD; when patch setup failed, unittest never reached
# tearDown and the remainder of the suite ran from a temporary directory.
replace_once(
    "tests/test_validate_instrument_policy.py",
    """        self._patchers = [
            patch('scripts.validation.policy.yaml.safe_load', side_effect=json.loads),
            patch('scripts.validation.io.yaml.safe_load', side_effect=json.loads),
        ]
        for p in self._patchers:
            p.start()
""",
    """        # Policy parsing is exercised through the real strict YAML loader.
        # Do not patch removed implementation details after changing CWD: a
        # failed setUp would prevent tearDown from restoring the repository.
        self._patchers = []
""",
)

# These modules carried dependency stubs for environments without PyYAML/Jinja.
# In the normal test environment the real dependencies are installed; injecting
# the stubs globally before validation modules import would disable SafeLoader
# and therefore duplicate-key enforcement for unrelated tests.
replace_once(
    "tests/test_full_audit.py",
    'sys.modules.setdefault("yaml", yaml_stub)\n',
    'if importlib.util.find_spec("yaml") is None:\n    sys.modules.setdefault("yaml", yaml_stub)\n',
)
replace_once(
    "tests/test_full_audit.py",
    'sys.modules.setdefault("jinja2", jinja2_stub)\n',
    'if importlib.util.find_spec("jinja2") is None:\n    sys.modules.setdefault("jinja2", jinja2_stub)\n',
)
replace_once(
    "tests/test_validate_event_policy.py",
    "import json\nimport sys\nimport types\n",
    "import importlib.util\nimport json\nimport sys\nimport types\n",
)
replace_once(
    "tests/test_validate_event_policy.py",
    "sys.modules.setdefault('yaml', yaml_stub)\n",
    "if importlib.util.find_spec('yaml') is None:\n    sys.modules.setdefault('yaml', yaml_stub)\n",
)

# Ti:Sapphire is a source technology, not a rewrite-safe synonym for the
# higher-level `multiphoton_laser` kind. Legacy parser compatibility preserves
# the normalized raw value instead of silently asserting a different concept.
replace_once(
    "tests/test_light_path_parser.py",
    '        self.assertEqual(by_index["mp_1"]["kind"], "multiphoton_laser")\n',
    '        self.assertEqual(by_index["mp_1"]["kind"], "ti_sapphire")\n',
)

# The autofix command is now a package module so imports resolve consistently in
# Actions. Keep the regression test aligned with that execution contract.
replace_once(
    "tests/test_vocabulary_second_audit.py",
    "    assert 'scripts/autofix_yaml.py --write' in workflow\n",
    "    assert 'python -m scripts.autofix_yaml --write' in workflow\n",
)

# A local --write must not leave the repository in an invalid state. Preserve
# original bytes for every changed file, run the authoritative validators after
# the complete proposed transformation, and roll all writes back on any error.
replace_once(
    "scripts/autofix_yaml.py",
    "from scripts.validation.io import _iter_yaml_files, _load_yaml\n",
    "from scripts.validation.events import validate_event_ledgers\nfrom scripts.validation.instrument import validate_instrument_ledgers\nfrom scripts.validation.io import _iter_yaml_files, _load_yaml\n",
)
replace_once(
    "scripts/autofix_yaml.py",
    '''def main(argv: list[str] | None = None) -> int:
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
''',
    '''def _validate_repository_after_write() -> None:
    instrument_ids, instrument_errors, _ = validate_instrument_ledgers()
    event_report = validate_event_ledgers(instrument_ids=instrument_ids)
    errors = [*instrument_errors, *event_report.errors]
    if errors:
        preview = '; '.join(f"{item.code}: {item.path}" for item in errors[:10])
        suffix = '' if len(errors) <= 10 else f"; ... and {len(errors) - 10} more"
        raise RuntimeError(
            f"Autofix produced {len(errors)} validation error(s); writes were rolled back. "
            f"{preview}{suffix}"
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base = get_base_path()
    changed_files: list[Path] = []
    total_replacements = 0
    originals: dict[Path, str] = {}
    try:
        for spec in build_specs(base):
            for filepath in _iter_yaml_files(spec.target_dir):
                original = filepath.read_text(encoding='utf-8') if args.write else None
                changed, replacements = autofix_file(filepath, spec, write_changes=args.write)
                if changed:
                    changed_files.append(filepath)
                    total_replacements += replacements
                    if args.write and original is not None:
                        originals[filepath] = original
        if args.write and originals:
            _validate_repository_after_write()
    except Exception:
        for filepath, original in originals.items():
            filepath.write_text(original, encoding='utf-8')
        raise

    mode = 'Updated' if args.write else 'Would update'
    print(f'{mode} {len(changed_files)} file(s); replacements: {total_replacements}.')
    for filepath in changed_files:
        print(f' - {filepath.relative_to(base)}')
    return 1 if (not args.write and changed_files) else 0
''',
)

replace_once(
    "tests/test_vocabulary_second_audit.py",
    "    assert 'load_vocabs' not in source and 'metric_class_rules' not in source\n",
    "    assert 'load_vocabs' not in source and 'metric_class_rules' not in source\n    assert '_validate_repository_after_write' in source and 'writes were rolled back' in source\n",
)
replace_once(
    "tests/test_vocabulary_second_audit.py",
    "from scripts.autofix_yaml import _canonicalize_rule_values, parse_args\n",
    "import scripts.autofix_yaml as autofix_yaml\nfrom scripts.autofix_yaml import _canonicalize_rule_values, parse_args\n",
)
replace_once(
    "tests/test_vocabulary_second_audit.py",
    '''    assert workflow.index('python -m scripts.dashboard_builder --strict') < workflow.index('peter-evans/create-pull-request')


def test_required_if_canonicalizes_generic_membership_operators''',
    '''    assert workflow.index('python -m scripts.dashboard_builder --strict') < workflow.index('peter-evans/create-pull-request')


def test_autofix_write_rolls_back_when_repository_validation_fails(tmp_path, monkeypatch):
    target = tmp_path / 'instrument.yaml'
    original = 'kind: legacy\\n'
    target.write_text(original, encoding='utf-8')
    spec = type('Spec', (), {'target_dir': tmp_path})()
    monkeypatch.setattr(autofix_yaml, 'get_base_path', lambda: tmp_path)
    monkeypatch.setattr(autofix_yaml, 'build_specs', lambda base: [spec])
    monkeypatch.setattr(autofix_yaml, '_iter_yaml_files', lambda base: [target])

    def fake_autofix(filepath, spec, *, write_changes):
        assert write_changes is True
        filepath.write_text('kind: changed\\n', encoding='utf-8')
        return True, 1

    monkeypatch.setattr(autofix_yaml, 'autofix_file', fake_autofix)
    monkeypatch.setattr(
        autofix_yaml,
        '_validate_repository_after_write',
        lambda: (_ for _ in ()).throw(RuntimeError('invalid transformed repository')),
    )
    with pytest.raises(RuntimeError, match='invalid transformed repository'):
        autofix_yaml.main(['--write'])
    assert target.read_text(encoding='utf-8') == original


def test_required_if_canonicalizes_generic_membership_operators''',
)

print("Applied post-merge CI corrections")
