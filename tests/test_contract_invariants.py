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
    def test_virtual_microscope_runtime_parses_cleanly(self) -> None:
        proc = subprocess.run(
            ["node", "-c", str(RUNTIME_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"Runtime parse check failed. stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
        )

    def test_runtime_uses_single_crosstalk_matrix_declaration(self) -> None:
        runtime_source = RUNTIME_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            runtime_source.count("const crosstalkMatrix = computeCrosstalkMatrix(results);"),
            1,
            msg="simulateInstrument must declare crosstalkMatrix only once.",
        )

    def test_evaluate_configuration_score_uses_pairwise_matrix_not_legacy_row_crosstalk(self) -> None:
        runtime_source = RUNTIME_PATH.read_text(encoding="utf-8")
        match = re.search(
            r"function evaluateConfigurationScore\(simulation, fluorophores, tolerance\) \{(?P<body>[\s\S]*?)\n  \}\n\n  function computeCrosstalkMatrix",
            runtime_source,
        )
        self.assertIsNotNone(match, msg="evaluateConfigurationScore function body should be present.")
        body = match.group("body") if match else ""
        self.assertIn("pairwiseCrosstalkByTarget", body)
        self.assertIn("const matrix = simulation.crosstalkMatrix || {};", body)
        self.assertNotIn("chosenRows.map((row) => row.crosstalkPct || 0)", body)
        self.assertNotIn("chosenRows.reduce(\n      (product, row)", body)

    def test_critical_runtime_and_dto_fields_are_declared_in_schema(self) -> None:
        schema_paths = _schema_paths()
        required_paths = {
            "hardware.sources[].manufacturer",
            "hardware.sources[].product_code",
            "hardware.sources[].tunable_min_nm",
            "hardware.sources[].tunable_max_nm",
            "hardware.sources[].simultaneous_lines_max",
            "hardware.optical_path_elements[].element_type",
            "hardware.optical_path_elements[].supported_branch_count",
            "hardware.endpoints[].id",
            "hardware.endpoints[].endpoint_type",
            "light_paths[].id",
            "light_paths[].illumination_sequence[].source_id",
            "light_paths[].illumination_sequence[].optical_path_element_id",
            "light_paths[].detection_sequence[].endpoint_id",
            "light_paths[].detection_sequence[].branches.selection_mode",
            "light_paths[].detection_sequence[].branches.items[].branch_id",
            "light_paths[].detection_sequence[].branches.items[].sequence[].optical_path_element_id",
            "light_paths[].detection_sequence[].branches.items[].sequence[].endpoint_id",
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

    def test_removed_topology_paths_stay_out_of_canonical_schema(self) -> None:
        schema_paths = _schema_paths()
        removed_paths = {
            "light_paths[].illumination_sequence[].branches",
            "light_paths[].illumination_sequence[].branches.items[].sequence[].source_id",
            "hardware.optical_path_elements[].branches",
            "hardware.optical_path_elements[].branches[].target_ids",
        }
        lingering = sorted(path for path in removed_paths if path in schema_paths)
        self.assertEqual(
            lingering,
            [],
            msg=(
                "Removed topology paths unexpectedly remain in the canonical schema contract: "
                + ", ".join(lingering)
            ),
        )

    def test_validator_hardcoded_structural_paths_are_schema_visible(self) -> None:
        schema_paths = _schema_paths()
        normalized_schema = {_normalize_contract_path(path) for path in schema_paths}
        source = VALIDATE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        migration_only_validate_paths = {
            "hardware.light_path.endpoints",
            "hardware.light_path.splitters",
            "hardware.light_path.cube_mechanisms",
            "hardware.light_path.excitation_mechanisms",
            "hardware.light_path.dichroic_mechanisms",
            "hardware.light_path.emission_mechanisms",
            "hardware.light_sources",
        }

        literals = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                token = node.value
                if token.startswith(("hardware.", "instrument.", "software.", "modules.")):
                    literals.add(token)

        unresolved = []
        for token in sorted(literals):
            normalized = _normalize_contract_path(token)
            if normalized in migration_only_validate_paths:
                continue
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

    def test_migration_compatibility_strict_payload_does_not_parse_notes_into_graph_contract(self) -> None:
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

        runtime = ((payload.get("projections") or {}).get("virtual_microscope") or {})
        self.assertEqual(runtime.get("terminals"), [])
        self.assertEqual(runtime.get("splitters", [])[0].get("branches", [])[0].get("target_ids"), [])
        self.assertTrue(payload.get("metadata", {}).get("graph_incomplete"))

    def test_authoritative_dto_exposes_inventory_route_usage_and_graph_contract(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser", "manufacturer": "LaserCo", "model": "488"}],
                    "optical_path_elements": [
                        {"id": "main_splitter", "stage_role": "splitter", "element_type": "splitter", "display_label": "Main splitter"},
                        {"id": "green_filter", "stage_role": "emission", "element_type": "filter_wheel", "display_label": "Green filter"},
                    ],
                    "endpoints": [{"id": "cam_main", "endpoint_type": "camera_port", "display_label": "Main camera"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{"source_id": "src_488"}],
                        "detection_sequence": [
                            {"optical_path_element_id": "main_splitter"},
                            {"branches": {"selection_mode": "exclusive", "items": [{"branch_id": "camera", "sequence": [{"optical_path_element_id": "green_filter"}, {"endpoint_id": "cam_main"}]}]}},
                        ],
                    }
                ],
            }
        )

        self.assertIn("hardware_inventory", payload)
        self.assertIn("hardware_index_map", payload)
        self.assertIn("route_hardware_usage", payload)
        self.assertIn("normalized_endpoints", payload)
        self.assertEqual(payload["hardware_inventory"][0]["display_number"], 1)
        self.assertEqual(payload["route_hardware_usage"][0]["route_id"], "epi")
        self.assertTrue(payload["route_hardware_usage"][0]["hardware_inventory_ids"])
        self.assertTrue(payload["light_paths"][0]["graph_nodes"])
        self.assertTrue(payload["light_paths"][0]["graph_edges"])
        self.assertTrue(payload["light_paths"][0]["branch_blocks"])

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

    def test_identity_fields_do_not_conflate_model_with_name_in_authoritative_dto_builders(self) -> None:
        builder_source = (REPO_ROOT / "scripts" / "dashboard_builder.py").read_text(encoding="utf-8")
        forbidden_fallbacks = [
            'model = clean_text(obj.get("model") or obj.get("name"))',
            'model = clean_text(modulator.get("model") or modulator.get("name"))',
            'model = clean_text(logic.get("model") or logic.get("name"))',
            'model = clean_text(scanner.get("model") or scanner.get("name"))',
            'model = clean_text(changer.get("model") or changer.get("name"))',
        ]
        for fallback in forbidden_fallbacks:
            self.assertNotIn(fallback, builder_source)

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
