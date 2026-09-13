from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one match in {path!r}, found {count}: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


# Keep strict duplicate-key rejection even when a fixture/local module shadows
# PyYAML. Production PyYAML continues to use the existing UniqueKeyLoader path;
# ruamel is the complete parser fallback when SafeLoader is unavailable.
replace_once(
    "scripts/validation/io.py",
    '''    if safe_loader is None:\n        if reject_duplicate_keys:\n            return None, "YAML loader cannot enforce duplicate-key rejection."\n        try:\n            payload = yaml.safe_load(path.read_text(encoding="utf-8"))\n        except (OSError, yaml.YAMLError) as exc:\n            return None, str(exc)\n''',
    '''    if safe_loader is None:\n        text = path.read_text(encoding="utf-8")\n        try:\n            from ruamel.yaml import YAML as RuamelYAML\n            from ruamel.yaml.error import YAMLError as RuamelYAMLError\n        except ImportError:\n            if reject_duplicate_keys:\n                return None, "YAML loader cannot enforce duplicate-key rejection."\n            try:\n                payload = yaml.safe_load(text)\n            except (OSError, yaml.YAMLError) as exc:\n                return None, str(exc)\n        else:\n            try:\n                fallback_yaml = RuamelYAML(typ="safe")\n                fallback_yaml.allow_duplicate_keys = not reject_duplicate_keys\n                payload = fallback_yaml.load(text)\n            except (OSError, RuamelYAMLError) as exc:\n                return None, str(exc)\n''',
)

# The validation package now owns YAML loading centrally in validation.io.
# Remove stale mocks against policy.yaml, and register cwd/tmpdir cleanup before
# changing directory so a future setUp failure cannot poison the whole suite.
replace_once(
    "tests/test_validate_instrument_policy.py",
    "from unittest.mock import patch\n",
    "",
)
replace_once(
    "tests/test_validate_instrument_policy.py",
    '''        self._tmpdir = tempfile.TemporaryDirectory()\n        self.repo = Path(self._tmpdir.name)\n        self.prev_cwd = Path.cwd()\n        os.chdir(self.repo)\n        (self.repo / 'schema').mkdir(parents=True, exist_ok=True)\n        self._patchers = [\n            patch('scripts.validation.policy.yaml.safe_load', side_effect=json.loads),\n            patch('scripts.validation.io.yaml.safe_load', side_effect=json.loads),\n        ]\n        for p in self._patchers:\n            p.start()\n\n    def tearDown(self) -> None:\n        for p in reversed(self._patchers):\n            p.stop()\n        os.chdir(self.prev_cwd)\n        self._tmpdir.cleanup()\n''',
    '''        self._tmpdir = tempfile.TemporaryDirectory()\n        self.repo = Path(self._tmpdir.name)\n        self.prev_cwd = Path.cwd()\n        self.addCleanup(self._tmpdir.cleanup)\n        self.addCleanup(os.chdir, self.prev_cwd)\n        os.chdir(self.repo)\n        (self.repo / 'schema').mkdir(parents=True, exist_ok=True)\n''',
)

# Do not replace the real yaml module globally in tests. JSON fixtures are valid
# YAML and should exercise the same loader boundary as production.
replace_once(
    "tests/test_validate_event_policy.py",
    '''import json\nimport sys\nimport types\n\nyaml_stub = types.ModuleType('yaml')\n\nclass _YamlError(Exception):\n    pass\n\ndef _safe_load(value):\n    return json.loads(value)\n\nyaml_stub.safe_load = _safe_load\nyaml_stub.YAMLError = _YamlError\nsys.modules.setdefault('yaml', yaml_stub)\n\n''',
    '''import json\n\n''',
)
replace_once(
    "tests/test_validate_event_policy.py",
    '''        self._tmpdir = tempfile.TemporaryDirectory()\n        self.repo = Path(self._tmpdir.name)\n        self.prev_cwd = Path.cwd()\n        os.chdir(self.repo)\n\n        (self.repo / 'schema').mkdir(parents=True, exist_ok=True)\n''',
    '''        self._tmpdir = tempfile.TemporaryDirectory()\n        self.repo = Path(self._tmpdir.name)\n        self.prev_cwd = Path.cwd()\n        self.addCleanup(self._tmpdir.cleanup)\n        self.addCleanup(os.chdir, self.prev_cwd)\n        os.chdir(self.repo)\n\n        (self.repo / 'schema').mkdir(parents=True, exist_ok=True)\n''',
)
replace_once(
    "tests/test_validate_event_policy.py",
    '''    def tearDown(self) -> None:\n        os.chdir(self.prev_cwd)\n        self._tmpdir.cleanup()\n\n''',
    "",
)

# Ti:sapphire is a technology subtype, not a safe lexical synonym for the
# canonical multiphoton_laser kind. Keep this runtime test canonical instead of
# relying on the scientifically lossy alias that the final audit removed.
replace_once(
    "tests/test_light_path_parser.py",
    '''            {"id": "mp_1", "kind": "ti:sapphire", "tunable_min_nm": 700, "tunable_max_nm": 1040, "timing_mode": "pulsed", "pulse_width_ps": 120, "repetition_rate_mhz": 80},''',
    '''            {"id": "mp_1", "kind": "multiphoton_laser", "technology": "ti_sapphire", "tunable_min_nm": 700, "tunable_max_nm": 1040, "timing_mode": "pulsed", "pulse_width_ps": 120, "repetition_rate_mhz": 80},''',
)

# The direct script invocation was the original import-path bug. The workflow
# intentionally uses module execution now; keep the older regression aligned.
replace_once(
    "tests/test_vocabulary_second_audit.py",
    "    assert 'scripts/autofix_yaml.py --write' in workflow\n",
    "    assert 'python -m scripts.autofix_yaml --write' in workflow\n    assert 'python scripts/autofix_yaml.py --write' not in workflow\n",
)

print("Applied post-merge vocabulary CI corrections")
