import ast
import json
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

from scripts.dashboard_builder import (
    build_llm_inventory_payload,
    build_methods_generator_instrument_export,
    build_optical_path_dto,
)
from scripts.generate_templates import build_template
from scripts.light_path_parser import generate_virtual_microscope_payload


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schema" / "instrument_policy.yaml"
TEMPLATE_PATH = REPO_ROOT / "templates" / "microscope_template.yaml"
VALIDATE_PATH = REPO_ROOT / "scripts" / "validate.py"
RUNTIME_PATH = REPO_ROOT / "scripts" / "templates" / "virtual_microscope_runtime.js"
APP_PATH = REPO_ROOT / "scripts" / "templates" / "virtual_microscope_app.js"
METHODS_TEMPLATE_PATH = REPO_ROOT / "scripts" / "templates" / "methods_generator.md.j2"
PLAN_TEMPLATE_PATH = REPO_ROOT / "scripts" / "templates" / "plan_experiments.md.j2"
EXAMPLE_INSTRUMENTS = [
    REPO_ROOT / "instruments" / "3i CSU-W1 Spinning Disk.yaml",
    REPO_ROOT / "instruments" / "xCELLigence RTCA eSight.yaml",
    REPO_ROOT / "instruments" / "EVOS fl.yaml",
    REPO_ROOT / "instruments" / "Nikon Ti2-E Crest V3 Spinning Disk.yaml",
]


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
        self.assertEqual(payload["metadata"]["primary_rendering_contract"]["routes"], "light_paths")

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

    def test_methods_export_preserves_structured_cube_route_facts(self) -> None:
        inst = {
            "dto": {
                "id": "scope-structured-cube",
                "hardware": {
                    "optical_path": {
                        "authoritative_route_contract": {
                            "routes": [
                                {
                                    "id": "widefield",
                                    "route_optical_facts": {
                                        "selected_or_selectable_emission_filters": [
                                            {
                                                "display_label": "GFP cube",
                                                "product_code": "49002",
                                                "excitation_filter": {"display_label": "470/40"},
                                                "dichroic": {"display_label": "495LP"},
                                                "emission_filter": {"display_label": "525/50"},
                                            }
                                        ]
                                    },
                                }
                            ]
                        }
                    }
                },
            },
            "methods_generation": {},
            "canonical": {"policy": {}},
        }
        exported = build_methods_generator_instrument_export(inst)
        route = exported["hardware"]["optical_path"]["authoritative_route_contract"]["routes"][0]
        cube = route["route_optical_facts"]["selected_or_selectable_emission_filters"][0]
        self.assertEqual(cube["product_code"], "49002")
        self.assertEqual(cube["excitation_filter"]["display_label"], "470/40")
        self.assertEqual(cube["dichroic"]["display_label"], "495LP")
        self.assertEqual(cube["emission_filter"]["display_label"], "525/50")

    def test_llm_inventory_route_truth_and_planning_summary_are_both_present_and_actionable(self) -> None:
        payload = build_llm_inventory_payload(
            {"short_name": "Core"},
            [
                {
                    "dto": {
                        "id": "scope-llm-truth",
                        "hardware": {
                            "optical_path": {
                                "authoritative_route_contract": {
                                    "routes": [
                                        {
                                            "id": "confocal",
                                            "illumination_mode": "confocal",
                                            "route_optical_facts": {
                                                "selected_or_selectable_sources": [{"id": "source:561", "display_label": "561 laser"}],
                                                "selected_or_selectable_endpoints": [{"id": "endpoint:hyd", "display_label": "HyD"}],
                                            },
                                            "relevant_hardware": {"sources": [{"id": "source:561"}]},
                                        }
                                    ]
                                }
                            }
                        },
                    },
                    "canonical": {"policy": {}},
                }
            ],
        )
        microscope = payload["active_microscopes"][0]
        self.assertEqual(microscope["llm_context"]["authoritative_route_contract"]["routes"][0]["id"], "confocal")
        planning = microscope["llm_context"]["route_planning_summary"]["routes"][0]
        self.assertEqual(planning["route_specific_vs_generic"]["route_specific_facts_source"], "route_optical_facts")
        self.assertIn("actionable_note", planning["known_vs_unknown"])
        self.assertIn("missing_categories", planning["known_vs_unknown"])

    def test_example_instruments_for_route_truth_regression_suite_exist(self) -> None:
        for instrument_path in EXAMPLE_INSTRUMENTS:
            self.assertTrue(
                instrument_path.exists(),
                msg=f"Expected regression example instrument is missing: {instrument_path}",
            )

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

        self.assertNotIn("collectRouteCatalogFallback", runtime_source)
        self.assertNotIn("adaptLegacyPayloadToCanonicalDto", runtime_source)
        self.assertIn("missing canonical DTO contract", runtime_source)
        self.assertIn(
            "authoritativeTopologyContract",
            runtime_source,
            msg="Runtime should declare the authoritative topology contract separately from derived stage adapters.",
        )
        self.assertIn(
            "hardwareIndexMap",
            runtime_source,
            msg="Runtime should preserve the canonical hardware index map for downstream numbering.",
        )
        self.assertNotIn("inferredDetectorTargets", runtime_source)
        self.assertRegex(
            app_source,
            r"if \(!strictHardwareTruthMode\(\) && autoRepairBlockedPath\(selection, simulation\)\)",
            msg="App must gate blocked-path auto-repair behind non-strict simulator mode.",
        )

    def test_methods_and_plan_consumers_keep_authoritative_route_contract_as_primary_input(self) -> None:
        methods_source = METHODS_TEMPLATE_PATH.read_text(encoding="utf-8")
        plan_source = PLAN_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("authoritative_route_contract?.routes", methods_source)
        self.assertIn("hardware_inventory_renderables", methods_source)
        self.assertNotIn("methods_route_views", methods_source)
        self.assertIn("llm_context.authoritative_route_contract", plan_source)
        self.assertNotIn("hardware.light_path", plan_source)

    # ── Semantic authority: JS simulation sources from selected execution, not DOM ──

    def test_simulation_uses_resolved_execution_not_dom_order(self) -> None:
        """JS simulation must derive component order from resolvedExecution, not DOM/mechanism state."""
        app_source = APP_PATH.read_text(encoding="utf-8")

        # Must have resolvedExecution and orderedComponentsFromExecution
        self.assertIn("selection.resolvedExecution = resolveSelectedExecution(", app_source)
        self.assertIn("orderedComponentsFromExecution(selection.resolvedExecution,", app_source)

        # Must NOT have deleted buildTraversalOrderedComponents reconstruction
        self.assertNotIn("buildTraversalOrderedComponents", app_source)
        # Must NOT reconstruct component order from DOM
        self.assertNotIn("buildOrderedComponentsFromDom", app_source)
        self.assertNotIn("selection.excitation.map(", app_source)

    def test_build_selected_configuration_sources_from_resolved_execution(self) -> None:
        """buildSelectedConfiguration must read from resolvedExecution, not debugSelections."""
        app_source = APP_PATH.read_text(encoding="utf-8")

        # Find the buildSelectedConfiguration function body
        fn_start = app_source.index("function buildSelectedConfiguration(")
        fn_body = app_source[fn_start:fn_start + 3000]

        # Must read from resolvedExecution
        self.assertIn("selection.resolvedExecution", fn_body)
        self.assertIn("selected_route_steps:", fn_body)

        # Must NOT read from debugSelections
        self.assertNotIn("debugSelections", fn_body)
        # Must NOT output a 'stages' field sourced from debug data
        self.assertNotIn("stages:", fn_body)

    def test_methods_generator_reads_selected_route_steps_not_stages(self) -> None:
        """Methods generator must read selected_route_steps, not deprecated stages or static route_steps."""
        methods_source = METHODS_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("selected_route_steps", methods_source)
        # Must not read deprecated 'stages' field from runtime config
        self.assertNotIn("runtimeConfig.stages", methods_source)
        # Must not read static route_steps as optical truth
        self.assertNotIn("runtimeConfig.route_steps", methods_source)

    def test_methods_template_keeps_exported_runtime_primary_and_legacy_fallback_only(self) -> None:
        methods_source = METHODS_TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("Exported runtime selection is authoritative for this page", methods_source)
        self.assertIn("localStorage is legacy fallback", methods_source)
        self.assertNotIn("paragraphRuntimeSelectedConfig", methods_source)

    def test_authoritative_route_contract_route_optical_facts_source_selected_route_steps(self) -> None:
        dto = build_optical_path_dto(
            {
                "light_paths": [
                    {
                        "id": "epi",
                        "selected_execution": {
                            "stages": [
                                {
                                    "selected_or_selectable_sources": [
                                        {"id": "deprecated_stage_source"}
                                    ]
                                }
                            ],
                            "selected_route_steps": [
                                {
                                    "route_step_id": "illumination-step-0",
                                    "selected_or_selectable_sources": [{"id": "src_561"}],
                                }
                            ],
                        },
                    }
                ],
                "hardware_inventory": [],
                "hardware_index_map": {},
                "route_hardware_usage": [],
                "normalized_endpoints": [],
                "optical_path_elements": [],
                "splitters": [],
                "stages": {},
                "terminals": [],
            }
        )
        facts = dto["authoritative_route_contract"]["routes"][0]["route_optical_facts"]
        self.assertEqual(facts["selected_or_selectable_sources"][0]["id"], "src_561")
        self.assertNotIn("deprecated_stage_source", json.dumps(facts))

    def test_acquisition_plan_wording_does_not_overstate_execution(self) -> None:
        """Sequential acquisition must be described as planned, not as executed."""
        methods_source = METHODS_TEMPLATE_PATH.read_text(encoding="utf-8")

        # Must not claim sequential acquisition "was executed"
        self.assertNotIn("was required and executed", methods_source)
        self.assertNotIn("was executed as", methods_source)
        # Should use "planned" language
        self.assertIn("is planned", methods_source)

    def test_reporting_export_uses_selected_execution_contract(self) -> None:
        """The exported configuration must carry selected_route_steps from the resolved execution."""
        app_source = APP_PATH.read_text(encoding="utf-8")

        # buildSelectedConfiguration must persist to localStorage
        self.assertIn("persistSelectedConfiguration", app_source)
        self.assertIn("aic.virtualMicroscope.selectedConfiguration", app_source)

        # The persisted config must include selected_route_steps, not a bare route_steps key
        fn_start = app_source.index("function buildSelectedConfiguration(")
        fn_body = app_source[fn_start:fn_start + 3000]
        self.assertIn("selected_route_steps:", fn_body)
        # Must not have a standalone 'route_steps:' key (not preceded by 'selected_')
        import re
        bare_route_steps = re.findall(r'(?<!selected_)route_steps:', fn_body)
        self.assertEqual(
            bare_route_steps, [],
            msg="buildSelectedConfiguration should only have selected_route_steps, not a separate route_steps key.",
        )


    # ── Template generation tests (consolidated from test_generate_templates.py) ──

    def test_object_map_uses_example_key_for_brace_paths(self) -> None:
        schema_path = Path("tmp_schema_for_template_test.yaml")
        schema_path.write_text(
            json.dumps(
                {
                    "sections": [
                        {
                            "title": "Hardware",
                            "rules": [
                                {
                                    "path": "hardware.light_path.excitation_mechanisms[].positions",
                                    "type": "object",
                                    "example_key": "Pos_1",
                                },
                                {
                                    "path": "hardware.light_path.excitation_mechanisms[].positions{}.component_type",
                                    "type": "string",
                                },
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        try:
            rendered = build_template(schema_path)
        finally:
            schema_path.unlink(missing_ok=True)

        self.assertIn("positions:", rendered)
        self.assertIn("Pos_1:", rendered)
        self.assertIn('component_type: ""', rendered)
        self.assertNotIn("positions{}:", rendered)

    def test_instrument_template_includes_light_path_endpoints_branches_and_spectral_fields(self) -> None:
        rendered = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("sources:", rendered)
        self.assertIn("optical_path_elements:", rendered)
        self.assertIn("endpoints:", rendered)
        self.assertIn('endpoint_type: ""', rendered)
        self.assertIn("branches:", rendered)
        self.assertIn('stage_role: ""', rendered)
        self.assertIn('element_type: ""', rendered)
        self.assertIn('selection_mode: ""', rendered)
        self.assertIn('branch_id: ""', rendered)
        self.assertIn("sequence:", rendered)
        self.assertIn('supported_branch_count: ""', rendered)
        self.assertIn('collection_min_nm: ""', rendered)
        self.assertIn('collection_max_nm: ""', rendered)
        self.assertIn('collection_center_nm: ""', rendered)
        self.assertIn('collection_width_nm: ""', rendered)
        self.assertIn('tunable_min_nm: ""', rendered)
        self.assertIn('tunable_max_nm: ""', rendered)
        self.assertIn('simultaneous_lines_max: ""', rendered)
        self.assertIn('product_code: ""  # Source product code', rendered)
        self.assertIn("illumination_sequence:", rendered)
        self.assertIn("detection_sequence:", rendered)
        self.assertNotIn("light_sources:", rendered)
        self.assertNotIn("light_path:", rendered)

    def test_plan_experiments_prompt_uses_canonical_v2_route_language(self) -> None:
        rendered = PLAN_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("llm_context.authoritative_route_contract", rendered)
        self.assertIn("llm_context.route_planning_summary", rendered)
        self.assertIn("required procedure in order", rendered)
        self.assertIn("Eliminate unavailable or incompatible instruments first", rendered)
        self.assertIn("Choose one best route on the top instrument and one backup route/instrument", rendered)
        self.assertIn("Raw hardware lists are secondary context and must not override route contract truth", rendered)
        self.assertIn("known vs unknown facts", rendered)
        self.assertIn("selected route", rendered)
        self.assertIn("detector/endpoint", rendered)
        self.assertIn("objective(s)", rendered)
        self.assertIn("branch/splitter handling", rendered)
        self.assertNotIn("Using the \\`hardware.light_path\\` topological data", rendered)
        self.assertNotIn("\\`excitation_mechanisms\\`", rendered)
        self.assertNotIn("Path 1 vs Path 2", rendered)


if __name__ == "__main__":
    unittest.main()
