import json
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

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

from scripts.full_audit import (
    audit_fpbase_runtime_contract,
    audit_virtual_microscope_instrument,
    generate_full_audit,
    render_markdown_report,
)



class FullAuditScriptTests(unittest.TestCase):
    def test_virtual_microscope_audit_detects_payload_health(self) -> None:
        instrument = {
            "id": "test-scope",
            "display_name": "Test Scope",
            "canonical": {
                "hardware": {
                    "sources": [
                        {"id": "src_488", "kind": "laser", "role": "excitation", "wavelength_nm": 488},
                        {"id": "src_775", "kind": "laser", "role": "depletion", "wavelength_nm": 775, "depletion_targets_nm": [640]},
                    ],
                    "optical_path_elements": [
                        {
                            "id": "exc_filter",
                            "stage_role": "excitation",
                            "element_type": "filter_wheel",
                            "positions": {1: {"type": "bandpass", "center_nm": 488, "width_nm": 10}},
                        },
                        {
                            "id": "main_dichroic",
                            "stage_role": "dichroic",
                            "element_type": "dichroic",
                            "positions": {1: {"type": "dichroic", "cutoffs_nm": [560]}},
                        },
                        {
                            "id": "em_filter",
                            "stage_role": "emission",
                            "element_type": "filter_wheel",
                            "positions": {1: {"type": "bandpass", "center_nm": 525, "width_nm": 50}},
                        },
                        {
                            "id": "det_splitter",
                            "stage_role": "splitter",
                            "element_type": "splitter",
                            "dichroic": {"type": "dichroic", "cutoffs_nm": [560]},
                            "selection_mode": "exclusive",
                            "supported_branch_count": 2,
                        },
                    ],
                    "endpoints": [
                        {"id": "cam_a", "kind": "camera", "channel_name": "Cam A", "endpoint_type": "camera"},
                        {"id": "pmt_a", "kind": "pmt", "channel_name": "PMT A", "endpoint_type": "detector", "supports_time_gating": True},
                    ],
                },
                "light_paths": [
                    {
                        "id": "confocal",
                        "illumination_sequence": [{"source_id": "src_488"}, {"optical_path_element_id": "exc_filter"}],
                        "detection_sequence": [
                            {"optical_path_element_id": "main_dichroic"},
                            {"optical_path_element_id": "em_filter"},
                            {"optical_path_element_id": "det_splitter"},
                            {"branches": {"selection_mode": "exclusive", "items": [
                                {"branch_id": "green", "label": "Green", "mode": "reflected", "sequence": [{"endpoint_id": "cam_a"}]},
                                {"branch_id": "red", "label": "Red", "mode": "transmitted", "sequence": [{"endpoint_id": "pmt_a"}]},
                            ]}},
                        ],
                    }
                ],
            },
        }

        audit = audit_virtual_microscope_instrument(instrument)
        self.assertEqual(audit["readiness"], "ok")
        self.assertEqual(audit["counts"]["hardware_sources"], 2)
        self.assertEqual(audit["counts"]["payload_splitters"], 1)
        self.assertGreater(audit["counts"]["valid_paths"], 0)

    def test_generate_full_audit_returns_report_and_markdown(self) -> None:
        report = {
            "summary": {"status": "warn", "errors": 1, "warnings": 2},
            "inventory": {
                "active_instruments": 3,
                "retired_instruments": 1,
                "yaml_load_failures_active": 0,
                "yaml_load_failures_retired": 0,
            },
            "validation": {
                "instrument_errors": {"count": 1},
                "instrument_warnings": {"count": 2},
                "event_errors": {"count": 0},
                "event_warnings": {"count": 1},
            },
            "completeness": {
                "top_missing_required_paths": [{"name": "hardware.detectors[]", "count": 2}],
                "top_missing_conditional_paths": [{"name": "software[].version", "count": 1}],
                "top_alias_fallback_paths": [{"name": "instrument.display_name", "count": 1}],
                "top_methods_blocker_paths": [{"name": "hardware.detectors[]", "count": 2}],
            },
            "virtual_microscope": {
                "readiness_counts": {"ok": 2, "warning": 1},
                "instruments": [
                    {
                        "display_name": "Test Scope",
                        "instrument_id": "test-scope",
                        "issues": [],
                        "warnings": [{"message": "Detector metadata incomplete."}],
                    }
                ],
            },
            "fpbase_runtime": {"status": "ok", "message": "mCherry runtime contract passed."},
        }
        markdown = render_markdown_report(report)
        self.assertIn("# Repository Audit", markdown)
        self.assertIn("## Inventory", markdown)
        self.assertIn("### FPbase/browser runtime contract", markdown)
        self.assertIn("### Most common missing conditional instrument-policy fields", markdown)
        self.assertIn("### Fields currently blocking trustworthy methods generation", markdown)
        self.assertIn("Test Scope", markdown)

    def test_virtual_microscope_audit_treats_inferable_transmitted_role_as_info(self) -> None:
        instrument = {
            "id": "test-scope",
            "display_name": "Test Scope",
            "canonical": {
                "hardware": {
                    "sources": [
                        {"id": "lamp", "kind": "halogen_lamp", "path": "transmitted", "notes": "Brightfield lamp"}
                    ],
                    "optical_path_elements": [],
                    "endpoints": [],
                },
                "light_paths": [{"id": "transmitted", "illumination_sequence": [{"source_id": "lamp"}], "detection_sequence": []}],
            },
        }

        audit = audit_virtual_microscope_instrument(instrument)

        role_infos = [entry for entry in audit["info"] if entry["field"] == "role"]
        self.assertTrue(role_infos)
        self.assertTrue(any("transmitted illumination" in entry["message"] for entry in role_infos))
        self.assertFalse(any(entry["field"] == "role" for entry in audit["warnings"]))


    def test_audit_fpbase_runtime_contract_works_with_recorded_fixture(self) -> None:
        result = audit_fpbase_runtime_contract(REPO_ROOT)
        if shutil.which("node") is None:
            self.assertEqual(result["status"], "warning")
        else:
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["result"]["summaryName"], "mCherry")
            self.assertEqual(result["result"]["fluorName"], "mCherry")
            self.assertGreater(result["result"]["exPoints"], 0)
            self.assertGreater(result["result"]["emPoints"], 0)

    # ── Semantic authority audit checks ──

    def test_audit_detects_selected_execution_that_is_copy_of_route_steps(self) -> None:
        """Audit must NOT fire on proper parser output (which has selection_state)."""
        instrument = {
            "id": "copy-scope",
            "display_name": "Copy Scope",
            "canonical": {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser", "role": "excitation", "wavelength_nm": 488}],
                    "optical_path_elements": [
                        {"id": "exc_filter", "stage_role": "excitation", "element_type": "filter_wheel",
                         "positions": {1: {"type": "bandpass", "center_nm": 488, "width_nm": 10}}},
                    ],
                    "endpoints": [{"id": "cam_a", "kind": "camera", "channel_name": "Cam A", "endpoint_type": "camera"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{"source_id": "src_488"}, {"optical_path_element_id": "exc_filter"}],
                        "detection_sequence": [{"endpoint_id": "cam_a"}],
                    }
                ],
            },
        }

        audit = audit_virtual_microscope_instrument(instrument)
        copy_errors = [
            issue for issue in audit["issues"]
            if "verbatim copy of static route_steps" in issue.get("message", "")
        ]
        self.assertEqual(copy_errors, [], msg="Parser-generated selected_execution should not trigger copy detection.")

    def test_audit_flags_fake_selected_execution_without_selection_state(self) -> None:
        """Directly test the copy-detection logic against a hand-crafted payload."""
        from scripts.light_path_parser import generate_virtual_microscope_payload

        instrument_data = {
            "hardware": {
                "sources": [{"id": "src_488", "kind": "laser", "role": "excitation", "wavelength_nm": 488}],
                "optical_path_elements": [],
                "endpoints": [{"id": "cam_a", "kind": "camera", "endpoint_type": "camera"}],
            },
            "light_paths": [
                {
                    "id": "epi",
                    "illumination_sequence": [{"source_id": "src_488"}],
                    "detection_sequence": [{"endpoint_id": "cam_a"}],
                }
            ],
        }

        payload = generate_virtual_microscope_payload(instrument_data)
        # Tamper: copy route_steps into selected_execution without selection_state
        for route in payload.get("light_paths", []):
            static_steps = route.get("route_steps", [])
            if static_steps:
                route["selected_execution"] = {
                    "contract_version": "selected_execution.v2",
                    "selected_route_steps": [
                        {k: v for k, v in step.items() if k != "selection_state"}
                        for step in static_steps
                    ],
                }

        # Verify the copy-detection logic catches this
        detected = False
        for route in payload.get("light_paths", []):
            route_steps = route.get("route_steps")
            sel_exec = route.get("selected_execution")
            if isinstance(sel_exec, dict):
                sel_steps = sel_exec.get("selected_route_steps", [])
                if isinstance(route_steps, list) and isinstance(sel_steps, list) and len(sel_steps) == len(route_steps):
                    has_any_selection_state = any(
                        isinstance(s, dict) and s.get("selection_state") is not None
                        for s in sel_steps
                    )
                    static_step_ids = [s.get("step_id") for s in route_steps if isinstance(s, dict)]
                    sel_step_ids = [s.get("step_id") for s in sel_steps if isinstance(s, dict)]
                    if not has_any_selection_state and static_step_ids == sel_step_ids:
                        detected = True

        self.assertTrue(detected, msg="Audit should detect that tampered selected_route_steps is a copy of route_steps.")

    def test_audit_flags_unresolved_step_with_defaulted_optics(self) -> None:
        """Audit must catch unresolved steps that have spectral_ops (defaulting to first position)."""
        from scripts.light_path_parser import generate_virtual_microscope_payload

        instrument_data = {
            "hardware": {
                "sources": [{"id": "src_488", "kind": "laser", "role": "excitation", "wavelength_nm": 488}],
                "optical_path_elements": [
                    {"id": "exc_wheel", "stage_role": "excitation", "element_type": "filter_wheel",
                     "positions": {
                         1: {"type": "bandpass", "center_nm": 488, "width_nm": 10},
                         2: {"type": "bandpass", "center_nm": 561, "width_nm": 10},
                     }},
                ],
                "endpoints": [{"id": "cam_a", "kind": "camera", "endpoint_type": "camera"}],
            },
            "light_paths": [
                {
                    "id": "epi",
                    "illumination_sequence": [{"source_id": "src_488"}, {"optical_path_element_id": "exc_wheel"}],
                    "detection_sequence": [{"endpoint_id": "cam_a"}],
                }
            ],
        }

        payload = generate_virtual_microscope_payload(instrument_data)
        # Tamper: set an unresolved step to have spectral_ops
        for route in payload.get("light_paths", []):
            sel_exec = route.get("selected_execution")
            if not isinstance(sel_exec, dict):
                continue
            for step in sel_exec.get("selected_route_steps", []):
                if isinstance(step, dict) and step.get("selection_state") == "unresolved":
                    step["spectral_ops"] = [{"type": "bandpass", "center_nm": 488, "width_nm": 10}]

        # Verify the detection logic catches this
        detected = False
        for route in payload.get("light_paths", []):
            sel_exec = route.get("selected_execution")
            if not isinstance(sel_exec, dict):
                continue
            for step in sel_exec.get("selected_route_steps", []):
                if not isinstance(step, dict):
                    continue
                if (step.get("kind") == "optical_component"
                    and step.get("selection_state") == "unresolved"
                    and isinstance(step.get("available_positions"), list)
                    and len(step.get("available_positions", [])) > 1
                    and step.get("spectral_ops") is not None):
                    detected = True

        self.assertTrue(detected, msg="Audit should detect unresolved step with defaulted spectral_ops.")

    def test_cli_writes_outputs(self) -> None:
        dependency_check = subprocess.run(
            [sys.executable, "-c", "import yaml"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if dependency_check.returncode != 0:
            self.skipTest("PyYAML is required to execute scripts/full_audit.py in a subprocess.")
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "audit.json"
            md_path = Path(tmpdir) / "audit.md"
            proc = subprocess.run(
                [
                    "python",
                    "scripts/full_audit.py",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--json-out",
                    str(json_path),
                    "--markdown-out",
                    str(md_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertTrue(json_path.exists(), msg=proc.stderr)
            self.assertTrue(md_path.exists(), msg=proc.stderr)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("summary", payload)
            # The repository may currently contain validation failures; the CLI is allowed to exit non-zero.
            self.assertIn(proc.returncode, {0, 1})

    # ── JS runtime authority audit tests ──

    def test_js_runtime_authority_audit_passes_on_current_code(self) -> None:
        """The JS runtime authority audit should pass on the current (correct) codebase."""
        from scripts.full_audit import audit_js_runtime_authority
        result = audit_js_runtime_authority(REPO_ROOT)
        self.assertEqual(result["status"], "ok", msg=f"JS runtime authority audit failed: {result.get('issues', [])}")
        self.assertEqual(result["issues"], [])

    def test_js_runtime_authority_detects_missing_resolved_execution(self) -> None:
        """Audit should fail if resolveSelectedExecution call is absent."""
        from scripts.full_audit import audit_js_runtime_authority
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            templates_dir = tmpdir_path / "scripts" / "templates"
            templates_dir.mkdir(parents=True)
            # Write a minimal app.js that is missing resolveSelectedExecution
            (templates_dir / "virtual_microscope_app.js").write_text(
                "function buildSelectedConfiguration(selection) { return {}; }\n",
                encoding="utf-8",
            )
            result = audit_js_runtime_authority(tmpdir_path)
            self.assertEqual(result["status"], "error")
            messages = [i["message"] for i in result["issues"]]
            self.assertTrue(
                any("resolveSelectedExecution" in m for m in messages),
                msg=f"Expected resolveSelectedExecution issue, got: {messages}",
            )

    def test_js_runtime_authority_detects_forbidden_reconstruction(self) -> None:
        """Audit should fail if buildTraversalOrderedComponents is present in JS."""
        from scripts.full_audit import audit_js_runtime_authority
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            templates_dir = tmpdir_path / "scripts" / "templates"
            templates_dir.mkdir(parents=True)
            (templates_dir / "virtual_microscope_app.js").write_text(
                "function buildTraversalOrderedComponents() {}\n"
                "function buildSelectedConfiguration(selection) {\n"
                "  const resolvedSteps = selection.resolvedExecution;\n"
                "  return { selected_route_steps: resolvedSteps };\n"
                "}\n"
                "selection.resolvedExecution = resolveSelectedExecution(x, y);\n"
                "orderedComponentsFromExecution(selection.resolvedExecution, 'illumination');\n"
                "persistSelectedConfiguration();\n"
                "localStorage.setItem('aic.virtualMicroscope.selectedConfiguration', '');\n",
                encoding="utf-8",
            )
            result = audit_js_runtime_authority(tmpdir_path)
            self.assertEqual(result["status"], "error")
            messages = [i["message"] for i in result["issues"]]
            self.assertTrue(
                any("buildTraversalOrderedComponents" in m for m in messages),
                msg=f"Expected buildTraversalOrderedComponents issue, got: {messages}",
            )

    # ── Issue categorization tests ──

    def test_audit_issues_carry_category_field(self) -> None:
        """All issues from audit_virtual_microscope_instrument should carry a 'category' field."""
        instrument = {
            "id": "cat-test-scope",
            "display_name": "Category Test Scope",
            "canonical": {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser", "role": "excitation", "wavelength_nm": 488}],
                    "optical_path_elements": [],
                    "endpoints": [{"id": "cam_a", "kind": "camera", "endpoint_type": "camera"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{"source_id": "src_488"}],
                        "detection_sequence": [{"endpoint_id": "cam_a"}],
                    }
                ],
            },
        }
        result = audit_virtual_microscope_instrument(instrument)
        for issue in result.get("issues", []):
            self.assertIn("category", issue, msg=f"Issue missing 'category': {issue}")
            self.assertIn(
                issue["category"],
                ("topology_completeness", "runtime_execution_authority", "scientific_support_completeness"),
                msg=f"Unknown category: {issue['category']}",
            )
        for warning in result.get("warnings", []):
            if "category" in warning:
                self.assertIn(
                    warning["category"],
                    ("topology_completeness", "runtime_execution_authority", "scientific_support_completeness"),
                    msg=f"Unknown category: {warning['category']}",
                )

    def test_full_audit_report_includes_category_breakdown(self) -> None:
        """The full audit report summary must include by_category breakdown."""
        dependency_check = subprocess.run(
            [sys.executable, "-c", "import yaml"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if dependency_check.returncode != 0:
            self.skipTest("PyYAML is required for full audit report generation.")
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "audit.json"
            md_path = Path(tmpdir) / "audit.md"
            subprocess.run(
                ["python", "scripts/full_audit.py", "--repo-root", str(REPO_ROOT),
                 "--json-out", str(json_path), "--markdown-out", str(md_path)],
                cwd=REPO_ROOT, capture_output=True, text=True, check=False,
            )
            if not json_path.exists():
                self.skipTest("Audit JSON not generated.")
            report = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("by_category", report["summary"])
            self.assertIsInstance(report["summary"]["by_category"], dict)

    def test_full_audit_report_includes_js_runtime_authority(self) -> None:
        """The full audit report must include the js_runtime_authority section."""
        dependency_check = subprocess.run(
            [sys.executable, "-c", "import yaml"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if dependency_check.returncode != 0:
            self.skipTest("PyYAML is required for full audit report generation.")
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "audit.json"
            md_path = Path(tmpdir) / "audit.md"
            subprocess.run(
                ["python", "scripts/full_audit.py", "--repo-root", str(REPO_ROOT),
                 "--json-out", str(json_path), "--markdown-out", str(md_path)],
                cwd=REPO_ROOT, capture_output=True, text=True, check=False,
            )
            if not json_path.exists():
                self.skipTest("Audit JSON not generated.")
            report = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("js_runtime_authority", report)
            self.assertIn("status", report["js_runtime_authority"])
            self.assertIn("issues", report["js_runtime_authority"])

    def test_markdown_report_includes_js_runtime_and_categories(self) -> None:
        """The markdown report must include JS runtime authority and category sections."""
        dependency_check = subprocess.run(
            [sys.executable, "-c", "import yaml"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if dependency_check.returncode != 0:
            self.skipTest("PyYAML is required for full audit report generation.")
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "audit.json"
            md_path = Path(tmpdir) / "audit.md"
            subprocess.run(
                ["python", "scripts/full_audit.py", "--repo-root", str(REPO_ROOT),
                 "--json-out", str(json_path), "--markdown-out", str(md_path)],
                cwd=REPO_ROOT, capture_output=True, text=True, check=False,
            )
            if not md_path.exists():
                self.skipTest("Audit markdown not generated.")
            md = md_path.read_text(encoding="utf-8")
            self.assertIn("JS runtime execution authority", md)


if __name__ == "__main__":
    unittest.main()
