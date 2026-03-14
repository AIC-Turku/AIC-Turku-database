import ast
import re
import subprocess
import sys
import types
import unittest
from pathlib import Path

yaml_stub = types.ModuleType("yaml")


class _YamlError(Exception):
    pass


def _safe_load(value):
    import json

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

from scripts.dashboard_builder import build_methods_generator_instrument_export, build_llm_inventory_payload
from scripts.light_path_parser import generate_virtual_microscope_payload


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schema" / "instrument_policy.yaml"
TEMPLATE_PATH = REPO_ROOT / "templates" / "microscope_template.yaml"
VALIDATE_PATH = REPO_ROOT / "scripts" / "validate.py"
RUNTIME_PATH = REPO_ROOT / "scripts" / "templates" / "virtual_microscope_runtime.js"
APP_PATH = REPO_ROOT / "scripts" / "templates" / "virtual_microscope_app.js"


def _schema_paths() -> set[str]:
    paths: set[str] = set()
    for raw_line in SCHEMA_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("- path:"):
            continue
        value = line.split(":", 1)[1].strip().strip('"').strip("'")
        if value:
            paths.add(value)
    return paths


def _normalize_contract_path(path: str) -> str:
    return path.replace("[]", "").replace("{}", "")


class ContractInvariantTests(unittest.TestCase):
    def test_critical_runtime_and_dto_fields_are_declared_in_schema(self) -> None:
        schema_paths = _schema_paths()
        required_paths = {
            "hardware.light_path.endpoints[].id",
            "hardware.light_path.endpoints[].endpoint_type",
            "hardware.light_path.splitters[].branches[].target_ids",
            "hardware.light_sources[].manufacturer",
            "hardware.light_sources[].product_code",
            "hardware.light_sources[].tunable_min_nm",
            "hardware.light_sources[].tunable_max_nm",
            "hardware.light_sources[].simultaneous_lines_max",
            "hardware.detectors[].manufacturer",
            "hardware.detectors[].collection_min_nm",
            "hardware.detectors[].collection_max_nm",
            "hardware.detectors[].collection_center_nm",
            "hardware.detectors[].collection_width_nm",
        }
        missing = sorted(path for path in required_paths if path not in schema_paths)
        self.assertEqual(
            missing,
            [],
            msg=(
                "Critical downstream contract fields are missing from schema/instrument_policy.yaml: "
                + ", ".join(missing)
            ),
        )

    def test_validator_hardcoded_structural_paths_are_schema_visible(self) -> None:
        schema_paths = _schema_paths()
        normalized_schema = {_normalize_contract_path(path) for path in schema_paths}
        source = VALIDATE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)

        literals = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                token = node.value
                if token.startswith(("hardware.", "instrument.", "software.", "modules.")):
                    literals.add(token)

        unresolved = []
        for token in sorted(literals):
            normalized = _normalize_contract_path(token)
            if normalized in normalized_schema:
                continue
            if any(candidate.startswith(normalized + ".") for candidate in normalized_schema):
                continue
            unresolved.append(token)

        self.assertEqual(
            unresolved,
            [],
            msg=(
                "scripts/validate.py contains structural path checks not represented in schema policy: "
                + ", ".join(unresolved)
            ),
        )

    def test_template_generation_check_is_enforced(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "scripts.generate_templates", "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"Template freshness check failed. stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
        )

    def test_strict_payload_does_not_parse_notes_into_graph_contract(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "instrument": {"ocular_availability": "trinocular"},
                "hardware": {
                    "light_path": {
                        "splitters": [
                            {
                                "name": "Camera/Ocular splitter",
                                "notes": "send output to camera_port endpoint",
                                "branches": [
                                    {
                                        "id": "b1",
                                        "label": "Main",
                                        "notes": "target cam endpoint",
                                    }
                                ],
                            }
                        ]
                    }
                },
            },
            include_inferred_terminals=False,
        )

        self.assertEqual(payload.get("terminals"), [])
        self.assertEqual(payload.get("splitters", [])[0].get("branches", [])[0].get("target_ids"), [])
        self.assertTrue(payload.get("metadata", {}).get("graph_incomplete"))

    def test_methods_and_llm_exports_use_dto_contract_not_raw_yaml_fields(self) -> None:
        inst = {
            "manufacturer": "RAW Manufacturer",
            "hardware": {"light_sources": [{"name": "RAW Laser"}]},
            "dto": {
                "id": "scope-1",
                "manufacturer": "DTO Manufacturer",
                "hardware": {"light_sources": [{"display_label": "DTO Laser"}]},
            },
            "methods_generation": {"base_sentence": "DTO sentence"},
            "canonical": {"policy": {"missing_required": [], "missing_conditional": [], "alias_fallbacks": []}},
        }

        methods_export = build_methods_generator_instrument_export(inst)
        self.assertEqual(methods_export["manufacturer"], "DTO Manufacturer")
        self.assertEqual(methods_export["hardware"]["light_sources"][0]["display_label"], "DTO Laser")
        self.assertNotIn("RAW Manufacturer", str(methods_export))

        llm_payload = build_llm_inventory_payload({"short_name": "Core"}, [inst])
        microscope = llm_payload["active_microscopes"][0]
        self.assertEqual(microscope["manufacturer"], "DTO Manufacturer")
        self.assertEqual(microscope["hardware"]["light_sources"][0]["display_label"], "DTO Laser")

    def test_runtime_and_app_keep_strict_mode_gates_for_non_authoritative_fallbacks(self) -> None:
        runtime_source = RUNTIME_PATH.read_text(encoding="utf-8")
        app_source = APP_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "normalized.routeOptions = explicitRouteOptions.length\n      ? explicitRouteOptions\n      : (approximationMode ? collectRouteCatalogFallback(normalized) : []);",
            runtime_source,
            msg="Strict runtime must not use inferred route catalog fallback when approximation mode is off.",
        )
        self.assertIn(
            "if (!allowApproximation) return [];",
            runtime_source,
            msg="Strict runtime must not invent detector targets/virtual detectors.",
        )
        self.assertRegex(
            app_source,
            r"if \(!strictHardwareTruthMode\(\) && autoRepairBlockedPath\(selection, simulation\)\)",
            msg="App must gate blocked-path auto-repair behind non-strict simulator mode.",
        )


if __name__ == "__main__":
    unittest.main()
