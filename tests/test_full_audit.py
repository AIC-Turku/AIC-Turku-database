import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

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
                    "light_sources": [
                        {"kind": "laser", "role": "excitation", "wavelength_nm": 488},
                        {"kind": "laser", "role": "depletion", "wavelength_nm": 775, "depletion_targets_nm": [640]},
                    ],
                    "detectors": [
                        {"kind": "camera", "channel_name": "Cam A", "path": "widefield"},
                        {"kind": "pmt", "channel_name": "PMT A", "path": "confocal", "supports_time_gating": True},
                    ],
                    "splitters": [
                        {
                            "name": "Top-level splitter",
                            "dichroic": {"type": "dichroic", "cutoffs_nm": [560]},
                            "branches": [
                                {"label": "Green", "mode": "reflected", "component": {"type": "bandpass", "center_nm": 525, "width_nm": 50}},
                                {"label": "Red", "mode": "transmitted", "component": {"type": "bandpass", "center_nm": 700, "width_nm": 75}},
                            ],
                        }
                    ],
                    "light_path": {
                        "excitation_mechanisms": [{"positions": {1: {"type": "bandpass", "center_nm": 488, "width_nm": 10}}}],
                        "dichroic_mechanisms": [{"positions": {1: {"type": "dichroic", "cutoffs_nm": [560]}}}],
                        "emission_mechanisms": [{"positions": {1: {"type": "bandpass", "center_nm": 525, "width_nm": 50}}}],
                        "splitters": [],
                    },
                }
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
            "completeness": {"top_missing_required_paths": [{"name": "hardware.detectors[]", "count": 2}]},
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
        self.assertIn("Test Scope", markdown)

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
