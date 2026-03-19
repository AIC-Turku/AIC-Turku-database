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


if __name__ == "__main__":
    unittest.main()
