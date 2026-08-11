import json
import unittest
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from scripts.dashboard.qc_metrics import (
    build_qc_laser_context_view,
    build_qc_metric_view,
    metric_display_lookup,
    metric_name_lookup,
    metric_raw_lookup,
)
from scripts.dashboard.site_render import _build_all_charts_data


class DashboardQcMetricViewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = {
            "record_type": "qc_session",
            "started_utc": "2026-05-13T00:00:00Z",
            "inputs_human": [
                {
                    "metric_id": "stage.tile_scan_error_x_px",
                    "metric_class": "stage_repeatability",
                    "value": 2,
                    "unit": "px",
                    "details": "Manual stage check.",
                },
                {
                    "metric_id": "visual.optics_clean",
                    "metric_class": "signal_to_noise",
                    "value": "yes",
                    "unit": "",
                },
            ],
            "laser_inputs_human": {
                "measurement_position": "at_objective",
                "measurement_position_details": "Measured with a test objective.",
                "power_meter": {
                    "model": "PM100D",
                    "serial": "meter-123",
                    "calibration_due": "2027-01-01",
                    "integration_time_s": 1.0,
                },
                "linearity_series": [
                    {
                        "laser": "405",
                        "setpoint_units": "percent",
                        "power_units": "mW",
                        "points": [
                            {"setpoint": 50, "power": 1.9},
                            {"setpoint": 100, "power": 3.8},
                        ],
                        "details": "Linearity sweep.",
                    }
                ],
                "stability_series": [
                    {
                        "laser": "488",
                        "setpoint": 80,
                        "setpoint_units": "percent",
                        "sampling": "1 Hz",
                        "power_units": "mW",
                        "timepoints": [
                            {"t_s": 0, "power": 1.75},
                            {"t_s": 60, "power": 1.74},
                        ],
                    }
                ],
                "single_point_measurements": [
                    {
                        "laser": "405",
                        "setpoint": 100,
                        "setpoint_units": "percent",
                        "power": 3.83,
                        "power_units": "mW",
                        "details": "Final single-point reading.",
                    }
                ],
            },
            "metrics_computed": [
                {
                    "metric_id": "laser.405.linearity_r2",
                    "metric_class": "laser_power",
                    "value": 0.998,
                    "unit": "unitless",
                }
            ],
        }

    def test_view_combines_all_sources_with_units_and_provenance(self) -> None:
        view = build_qc_metric_view(self.payload)
        by_id = {item["metric_id"]: item for item in view}

        self.assertEqual(by_id["stage.tile_scan_error_x_px"]["display_value"], "2 px")
        self.assertEqual(by_id["stage.tile_scan_error_x_px"]["source"], "Human input")
        self.assertEqual(
            by_id["laser.at_obj.405.100pct.power_mw"]["display_value"],
            "3.83 mW",
        )
        self.assertEqual(
            by_id["laser.at_obj.405.100pct.power_mw"]["source"],
            "Laser input",
        )
        self.assertIn("laser.at_obj.405.50pct.power_mw", by_id)
        self.assertIn("laser.at_obj.488.80pct.stability_t0s.power_mw", by_id)
        self.assertEqual(by_id["laser.405.linearity_r2"]["display_value"], "0.998")
        self.assertEqual(by_id["laser.405.linearity_r2"]["source"], "Computed metric")

    def test_lookup_helpers_keep_raw_and_display_values_separate(self) -> None:
        self.assertEqual(metric_raw_lookup(self.payload)["stage.tile_scan_error_x_px"], 2)
        self.assertEqual(
            metric_display_lookup(self.payload)["stage.tile_scan_error_x_px"],
            "2 px",
        )
        self.assertEqual(
            metric_name_lookup(self.payload)["laser.at_obj.405.100pct.power_mw"],
            "405 nm laser power at objective (100%)",
        )

    def test_series_can_be_omitted_for_compact_consumers(self) -> None:
        ids = {
            item["metric_id"]
            for item in build_qc_metric_view(self.payload, include_series=False)
        }
        self.assertNotIn("laser.at_obj.405.50pct.power_mw", ids)
        self.assertNotIn("laser.at_obj.488.80pct.stability_t0s.power_mw", ids)
        self.assertIn("laser.at_obj.405.100pct.power_mw", ids)

    def test_legacy_single_point_shape_is_supported(self) -> None:
        payload = {
            "laser_inputs_human": {
                "single_point_measurements": [
                    {
                        "wavelength_nm": 405,
                        "measured_power_mw": 41.0,
                        "location": "fiber_output_sdc",
                    }
                ]
            }
        }
        view = build_qc_metric_view(payload)

        self.assertEqual(len(view), 1)
        self.assertEqual(view[0]["metric_id"], "laser.fiber_output_sdc.405.power_mw")
        self.assertEqual(view[0]["display_value"], "41 mW")

    def test_laser_context_exposes_measurement_setup(self) -> None:
        rows = build_qc_laser_context_view(self.payload)
        row_map = {row["label"]: row["value"] for row in rows}

        self.assertEqual(row_map["Measurement position"], "at objective")
        self.assertEqual(row_map["Power meter"], "PM100D")
        self.assertEqual(row_map["Integration time"], "1 s")

    def test_chart_data_includes_numeric_human_and_laser_inputs(self) -> None:
        charts = json.loads(
            _build_all_charts_data(
                [
                    {"data": self.payload},
                    {
                        "data": {
                            "started_utc": "2026-06-13T00:00:00Z",
                            "inputs_human": [
                                {
                                    "metric_id": "stage.tile_scan_error_x_px",
                                    "value": 3,
                                    "unit": "px",
                                }
                            ],
                        }
                    },
                ]
            )
        )

        self.assertEqual(charts["stage.tile_scan_error_x_px"]["values"], [2, 3])
        self.assertEqual(
            charts["laser.at_obj.405.100pct.power_mw"]["values"],
            [3.83, None],
        )
        self.assertNotIn("visual.optics_clean", charts)

    def test_event_template_renders_human_and_laser_measurements(self) -> None:
        environment = Environment(loader=FileSystemLoader("scripts/templates"))
        template = environment.get_template("event_detail.md.j2")
        rendered = template.render(
            event_id="qc_example",
            instrument="scope-example",
            instrument_id="scope-example",
            operator="operator",
            raw_yaml_content="record_type: qc_session",
            payload=self.payload,
            qc_metrics=build_qc_metric_view(self.payload),
            qc_laser_context=build_qc_laser_context_view(self.payload),
        )

        self.assertIn("Laser Measurement Context", rendered)
        self.assertIn("QC Measurements", rendered)
        self.assertIn("stage.tile_scan_error_x_px", rendered)
        self.assertIn("laser.at_obj.405.100pct.power_mw", rendered)
        self.assertIn("3.83 mW", rendered)
        self.assertIn("Human input", rendered)


class ZeissServiceLedgerTests(unittest.TestCase):
    def test_vendor_qc_metrics_are_available_to_dashboard_view(self) -> None:
        path = Path(
            "qc/sessions/scope-zeiss-lsm-880-with-airyscan/2026/"
            "2026-05-13_vendor_pm_qc.yaml"
        )
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        metrics = metric_display_lookup(payload)

        self.assertEqual(metrics["laser.fiber.argon.optimal_power_mw"], "11.42 mW")
        self.assertEqual(metrics["laser.at_obj.405.100pct.power_mw"], "3.83 mW")
        self.assertEqual(metrics["stage.tile_scan_error_total_px"], "4 px")

    def test_objective_repair_is_consolidated_into_vendor_visit(self) -> None:
        directory = Path(
            "maintenance/events/scope-zeiss-lsm-880-with-airyscan/2026"
        )
        merged_path = directory / "2026-05-13_preventive_maintenance.yaml"
        duplicate_path = directory / "2026-05-14_40x_objective_correction_collar_repair.yaml"
        payload = yaml.safe_load(merged_path.read_text(encoding="utf-8"))
        instrument_text = Path(
            "instruments/Zeiss LSM 880 with AiryScan.yaml"
        ).read_text(encoding="utf-8")

        self.assertFalse(duplicate_path.exists())
        self.assertIn("correction collar", payload["action_details"].lower())
        self.assertIn(
            "maint_scope-zeiss-lsm-880-with-airyscan_20260504_40x_objective_correction_collar_issue",
            payload["related_maintenance"],
        )
        self.assertIn(payload["maintenance_id"], instrument_text)
        self.assertNotIn("20260514_40x_objective_correction_collar_repair", instrument_text)


if __name__ == "__main__":
    unittest.main()
