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

print("Applied post-merge CI corrections")
