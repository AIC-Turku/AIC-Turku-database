import copy
import json
import sys
import types
import unittest

yaml_stub = types.ModuleType("yaml")
class _YamlError(Exception):
    pass

def _safe_load(value):
    return json.loads(value)

yaml_stub.safe_load = _safe_load
yaml_stub.YAMLError = _YamlError
sys.modules.setdefault("yaml", yaml_stub)

jinja2_stub = types.ModuleType("jinja2")
class _DummyEnvironment:
    def __init__(self, *args, **kwargs):
        pass
class _DummyLoader:
    def __init__(self, *args, **kwargs):
        pass
jinja2_stub.Environment = _DummyEnvironment
jinja2_stub.FileSystemLoader = _DummyLoader
sys.modules.setdefault("jinja2", jinja2_stub)

from scripts.build_context import build_instrument_context
from scripts.dashboard_builder import build_methods_generator_instrument_export, build_llm_inventory_payload


class DiagnosticsModelTests(unittest.TestCase):
    def test_missing_optional_display_label_creates_warning(self):
        exported = build_methods_generator_instrument_export({"dto": {"id": "x"}, "canonical": {}, "lightpath_dto": {}})
        warnings = [d for d in exported["methods_view_dto"]["diagnostics"] if d.get("severity") == "warning"]
        self.assertTrue(warnings)
        self.assertIn("source", warnings[0])

    def test_missing_selected_execution_creates_error(self):
        import scripts.build_context as bc
        original_strict = bc.canonicalize_light_path_model_strict
        original_payload = bc.generate_virtual_microscope_payload
        bc.canonicalize_light_path_model_strict = lambda *_a, **_k: {"ok": True}
        bc.generate_virtual_microscope_payload = lambda *_a, **_k: {"light_paths": [{"id": "r1"}]}
        try:
            ctx = build_instrument_context(
                {"id": "x", "canonical": {"hardware": {"sources": []}}},
                vocabulary=None,
                build_dashboard_view_dto=lambda *_a, **_k: {"hardware": {"optical_path": {}}},
                build_methods_view_dto=lambda *_a, **_k: {},
                build_llm_inventory_record=lambda *_a, **_k: {},
            )
        finally:
            bc.canonicalize_light_path_model_strict = original_strict
            bc.generate_virtual_microscope_payload = original_payload
        errors = [d for d in ctx.diagnostics if d.get("severity") == "error"]
        self.assertTrue(any(d.get("code") == "missing_selected_execution" for d in errors))

    def test_llm_export_exposes_diagnostics(self):
        inst = {"dto": {"id": "x", "display_name": "X", "diagnostics": [{"severity": "error", "code": "missing_selected_execution"}]}, "canonical": {"policy": {}}, "lightpath_dto": {}}
        payload = build_llm_inventory_payload({"short_name": "Core"}, [inst])
        self.assertIn("diagnostics", payload["active_microscopes"][0]["llm_context"])


if __name__ == "__main__":
    unittest.main()
