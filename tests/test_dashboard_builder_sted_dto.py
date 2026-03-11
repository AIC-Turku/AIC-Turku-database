import unittest
import json
import sys
import types

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

from scripts.dashboard_builder import build_hardware_dto
from scripts.validate import Vocabulary


EMPTY_LIGHTPATH = {
    "filters": [],
    "splitters": [],
    "sections": [],
    "renderables": [],
}


class DashboardBuilderStedDtoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vocabulary = Vocabulary(
            vocab_registry={
                "light_source_kinds": {"source": "inline", "allowed_values": ["laser"]},
                "light_source_roles": {"source": "inline", "allowed_values": ["excitation", "depletion"]},
                "light_source_timing_modes": {"source": "inline", "allowed_values": ["cw", "pulsed"]},
                "detector_kinds": {"source": "inline", "allowed_values": ["hybrid"]},
                "optical_modulator_types": {"source": "inline", "allowed_values": ["slm", "phase_plate"]},
                "phase_mask_types": {"source": "inline", "allowed_values": ["vortex", "top_hat"]},
                "adaptive_illumination_methods": {"source": "inline", "allowed_values": ["rescue_sted"]},
                "scanner_types": {"source": "inline", "allowed_values": ["galvo"]},
                "autofocus_types": {"source": "inline", "allowed_values": ["laser"]},
                "triggering_modes": {"source": "inline", "allowed_values": ["internal"]},
                "stage_types": {"source": "inline", "allowed_values": ["z_piezo"]},
                "objective_immersion": {"source": "inline", "allowed_values": ["oil"]},
                "objective_corrections": {"source": "inline", "allowed_values": ["plan_apo"]},
            }
        )

    def test_sted_fields_are_renderable_in_hardware_dto(self) -> None:
        inst = {
            "canonical": {
                "hardware": {
                    "light_sources": [
                        {
                            "kind": "laser",
                            "role": "depletion",
                            "timing_mode": "pulsed",
                            "manufacturer": "Coherent",
                            "model": "STED-775",
                            "wavelength_nm": 775,
                            "pulse_width_ps": 600,
                            "repetition_rate_mhz": 80,
                            "depletion_targets_nm": [640, 660],
                        }
                    ],
                    "detectors": [
                        {
                            "kind": "hybrid",
                            "manufacturer": "Leica",
                            "model": "HyD",
                            "supports_time_gating": True,
                            "default_gating_delay_ns": 0.5,
                            "default_gate_width_ns": 6,
                        }
                    ],
                    "optical_modulators": [
                        {
                            "type": "slm",
                            "supported_phase_masks": ["vortex", "top_hat"],
                            "notes": "Donut shaping",
                        }
                    ],
                    "illumination_logic": [
                        {
                            "method": "rescue_sted",
                            "default_enabled": True,
                            "notes": "Suppress depletion in dim regions",
                        }
                    ],
                }
            }
        }

        hardware = build_hardware_dto(self.vocabulary, inst, lightpath_dto=EMPTY_LIGHTPATH)

        light = hardware["light_sources"][0]
        self.assertEqual(light["display_label"], "775 nm laser Coherent STED-775")
        self.assertIn("pulsed depletion laser", light["method_sentence"])
        self.assertIn("Role", "\n".join(light["spec_lines"]))
        self.assertIn("Timing mode", "\n".join(light["spec_lines"]))

        detector = hardware["detectors"][0]
        self.assertIn("time-gated acquisition", detector["method_sentence"])
        self.assertIn("Supports time gating", "\n".join(detector["spec_lines"]))

        modulator = hardware["optical_modulators"][0]
        self.assertEqual(modulator["display_label"], "slm")
        self.assertIn("phase mask", modulator["method_sentence"])
        self.assertIn("Supported phase masks", "\n".join(modulator["spec_lines"]))

        logic = hardware["illumination_logic"][0]
        self.assertIn("Adaptive illumination", logic["method_sentence"])
        self.assertIn("Default enabled", "\n".join(logic["spec_lines"]))

    def test_each_new_renderable_contains_required_dto_fields(self) -> None:
        inst = {
            "canonical": {
                "hardware": {
                    "light_sources": [{"kind": "laser", "manufacturer": "A", "model": "B"}],
                    "detectors": [{"kind": "hybrid", "manufacturer": "A", "model": "B"}],
                    "optical_modulators": [{"type": "phase_plate"}],
                    "illumination_logic": [{"method": "rescue_sted", "default_enabled": False}],
                }
            }
        }
        hardware = build_hardware_dto(self.vocabulary, inst, lightpath_dto=EMPTY_LIGHTPATH)

        for key in ["light_sources", "detectors", "optical_modulators", "illumination_logic"]:
            row = hardware[key][0]
            self.assertIn("display_label", row)
            self.assertIn("spec_lines", row)
            self.assertIn("method_sentence", row)
            self.assertIn("display_subtitle", row)


if __name__ == "__main__":
    unittest.main()
