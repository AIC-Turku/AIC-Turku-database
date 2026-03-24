import unittest
from pathlib import Path

import yaml

from scripts.light_path_parser import generate_virtual_microscope_payload, validate_light_path_warnings, validate_filter_cube_warnings


REPO_ROOT = Path(__file__).resolve().parents[1]
VOCAB_PATH = REPO_ROOT / "vocab" / "optical_component_types.yaml"
INSTRUMENTS_DIR = REPO_ROOT / "instruments"


COMPONENT_FIXTURES = {
    "bandpass": {
        "stage_role": "emission",
        "element_type": "filter_wheel",
        "component": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50},
        "expect": {"illumination": "bandpass", "detection": "bandpass"},
    },
    "multiband_bandpass": {
        "stage_role": "emission",
        "element_type": "filter_wheel",
        "component": {
            "component_type": "multiband_bandpass",
            "bands": [
                {"center_nm": 525, "width_nm": 50},
                {"center_nm": 700, "width_nm": 75},
            ],
        },
        "expect": {"illumination": "multiband_bandpass", "detection": "multiband_bandpass"},
    },
    "longpass": {
        "stage_role": "emission",
        "element_type": "filter_wheel",
        "component": {"component_type": "longpass", "cut_on_nm": 600},
        "expect": {"illumination": "longpass", "detection": "longpass"},
    },
    "shortpass": {
        "stage_role": "emission",
        "element_type": "filter_wheel",
        "component": {"component_type": "shortpass", "cut_off_nm": 450},
        "expect": {"illumination": "shortpass", "detection": "shortpass"},
    },
    "dichroic": {
        "stage_role": "dichroic",
        "element_type": "slider",
        "component": {"component_type": "dichroic", "cut_on_nm": 495},
        "expect": {"illumination": "dichroic_reflect", "detection": "dichroic_transmit"},
    },
    "multiband_dichroic": {
        "stage_role": "dichroic",
        "element_type": "slider",
        "component": {
            "component_type": "multiband_dichroic",
            "transmission_bands": [{"center_nm": 521, "width_nm": 25}],
            "reflection_bands": [{"center_nm": 440, "width_nm": 25}],
        },
        "expect": {"illumination": "dichroic_reflect", "detection": "dichroic_transmit"},
    },
    "polychroic": {
        "stage_role": "dichroic",
        "element_type": "slider",
        "component": {
            "component_type": "polychroic",
            "transmission_bands": [{"center_nm": 607, "width_nm": 25}],
            "reflection_bands": [{"center_nm": 561, "width_nm": 20}],
        },
        "expect": {"illumination": "dichroic_reflect", "detection": "dichroic_transmit"},
    },
    "notch": {
        "stage_role": "emission",
        "element_type": "filter_wheel",
        "component": {"component_type": "notch", "center_nm": 561, "width_nm": 20},
        "expect": {"illumination": "notch", "detection": "notch"},
    },
    "filter_cube": {
        "stage_role": "cube",
        "element_type": "turret",
        "component": {
            "name": "GFP",
            "component_type": "filter_cube",
            "excitation_filter": {"component_type": "bandpass", "center_nm": 470, "width_nm": 40},
            "dichroic": {"component_type": "dichroic", "cut_on_nm": 495},
            "emission_filter": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50},
        },
        "expect": {"illumination": "bandpass", "detection": "dichroic_transmit"},
    },
    "analyzer": {
        "stage_role": "analyzer",
        "element_type": "slider",
        "component": {"component_type": "analyzer", "name": "Analyzer"},
        "expect": {"illumination": "passthrough", "detection": "passthrough"},
        "unsupported": True,
    },
    "empty": {
        "stage_role": "emission",
        "element_type": "filter_wheel",
        "component": {"component_type": "empty", "name": "Empty"},
        "expect": {"illumination": "passthrough", "detection": "passthrough"},
    },
    "mirror": {
        "stage_role": "emission",
        "element_type": "slider",
        "component": {"component_type": "mirror", "name": "Mirror"},
        "expect": {"illumination": "passthrough", "detection": "passthrough"},
    },
    "block": {
        "stage_role": "emission",
        "element_type": "slider",
        "component": {"component_type": "block", "name": "Block"},
        "expect": {"illumination": "block", "detection": "block"},
    },
    "passthrough": {
        "stage_role": "emission",
        "element_type": "slider",
        "component": {"component_type": "passthrough", "name": "Passthrough"},
        "expect": {"illumination": "passthrough", "detection": "passthrough"},
    },
    "neutral_density": {
        "stage_role": "emission",
        "element_type": "filter_wheel",
        "component": {"component_type": "neutral_density", "name": "ND"},
        "expect": {"illumination": "passthrough", "detection": "passthrough"},
    },
}


def _runtime_projection(payload: dict) -> dict:
    projections = payload.get("projections") if isinstance(payload, dict) else {}
    if isinstance(projections, dict):
        runtime = projections.get("virtual_microscope")
        if isinstance(runtime, dict):
            return runtime
    return {}


def _single_position_payload(component_type: str, spec: dict) -> dict:
    stage_role = spec["stage_role"]
    element_type = spec["element_type"]
    position = dict(spec["component"])
    return {
        "hardware": {
            "optical_path_elements": [
                {
                    "id": f"{component_type}_element",
                    "name": f"{component_type} element",
                    "stage_role": stage_role,
                    "element_type": element_type,
                    "positions": {"Pos_1": position},
                }
            ]
        },
        "light_paths": [],
    }


class ParserComponentMatrixTests(unittest.TestCase):
    def test_vocab_component_types_have_parser_fixtures(self) -> None:
        vocab = yaml.safe_load(VOCAB_PATH.read_text())
        vocab_types = {term["id"] for term in vocab.get("terms", []) if isinstance(term, dict) and term.get("id")}
        self.assertEqual(vocab_types, set(COMPONENT_FIXTURES), "Every schema/vocab optical component type should have a parser fixture test")

    def test_schema_supported_component_types_parse_with_spectral_ops(self) -> None:
        for component_type, spec in COMPONENT_FIXTURES.items():
            with self.subTest(component_type=component_type):
                payload = generate_virtual_microscope_payload(_single_position_payload(component_type, spec))
                runtime = _runtime_projection(payload)
                stages = runtime.get("stages", {})
                mechanism = stages[spec["stage_role"]][0]
                value = mechanism["options"][0]["value"]

                self.assertEqual(value["component_type"], component_type)
                self.assertIn("spectral_ops", value)
                self.assertIn("illumination", value["spectral_ops"])
                self.assertIn("detection", value["spectral_ops"])
                self.assertEqual(value["spectral_ops"]["illumination"][0]["op"], spec["expect"]["illumination"])
                self.assertEqual(value["spectral_ops"]["detection"][0]["op"], spec["expect"]["detection"])

                if component_type == "filter_cube":
                    self.assertFalse(value.get("_cube_incomplete", False))
                    self.assertFalse(value.get("_unsupported_spectral_model", False))
                    illum_sub_roles = [entry.get("sub_role") for entry in value["spectral_ops"]["illumination"]]
                    det_sub_roles = [entry.get("sub_role") for entry in value["spectral_ops"]["detection"]]
                    self.assertEqual(illum_sub_roles, ["excitation_filter", "dichroic"])
                    self.assertEqual(det_sub_roles, ["dichroic", "emission_filter"])
                if spec.get("unsupported"):
                    self.assertTrue(value.get("_unsupported_spectral_model"))

    def test_flattened_filter_cube_is_degraded_by_design(self) -> None:
        instrument = {
            "hardware": {
                "optical_path_elements": [
                    {
                        "id": "cube_turret",
                        "stage_role": "cube",
                        "element_type": "turret",
                        "positions": {
                            "Pos_1": {
                                "name": "Blue Channel",
                                "component_type": "filter_cube",
                                "bands": [{"center_nm": 445, "width_nm": 35}],
                            }
                        },
                    }
                ]
            },
            "light_paths": [],
        }
        payload = generate_virtual_microscope_payload(instrument)
        value = _runtime_projection(payload)["stages"]["cube"][0]["options"][0]["value"]
        self.assertTrue(value.get("_cube_incomplete"))
        self.assertTrue(value.get("_unsupported_spectral_model"))
        self.assertEqual(
            value["spectral_ops"]["illumination"][0].get("unsupported_reason"),
            "filter_cube_incomplete_reconstruction",
        )
        self.assertEqual(
            value["spectral_ops"]["detection"][0].get("unsupported_reason"),
            "filter_cube_incomplete_reconstruction",
        )

    def test_flattened_filter_cube_emits_validation_warning(self) -> None:
        instrument = {
            "hardware": {
                "optical_path_elements": [
                    {
                        "id": "cube_turret",
                        "stage_role": "cube",
                        "element_type": "turret",
                        "positions": {
                            "Pos_1": {
                                "name": "Blue Channel",
                                "component_type": "filter_cube",
                                "bands": [{"center_nm": 445, "width_nm": 35}],
                            }
                        },
                    }
                ]
            },
            "light_paths": [],
        }
        warnings = validate_filter_cube_warnings(instrument)
        self.assertTrue(any("flattened" in warning and "excitation_filter, dichroic, and emission_filter" in warning for warning in warnings))

    def test_complete_filter_cube_emits_no_validation_warning(self) -> None:
        """Complete cube with all three sub-components emits zero warnings."""
        instrument = {
            "hardware": {
                "optical_path_elements": [
                    {
                        "id": "cube_turret",
                        "stage_role": "cube",
                        "element_type": "turret",
                        "positions": {
                            "Pos_1": {
                                "component_type": "filter_cube",
                                "excitation_filter": {"component_type": "bandpass", "center_nm": 470, "width_nm": 40},
                                "dichroic": {"component_type": "dichroic", "cut_on_nm": 495},
                                "emission_filter": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50},
                            }
                        },
                    }
                ]
            },
            "light_paths": [],
        }
        warnings = validate_filter_cube_warnings(instrument)
        self.assertEqual(warnings, [], "Complete cubes must emit zero validation warnings")

    def test_partial_filter_cube_missing_one_component_warns(self) -> None:
        """Cube with excitation_filter + dichroic but no emission_filter warns about the missing component."""
        instrument = {
            "hardware": {
                "optical_path_elements": [
                    {
                        "id": "cube_turret",
                        "stage_role": "cube",
                        "element_type": "turret",
                        "positions": {
                            "Pos_1": {
                                "name": "Partial Cube",
                                "component_type": "filter_cube",
                                "excitation_filter": {"component_type": "bandpass", "center_nm": 470, "width_nm": 40},
                                "dichroic": {"component_type": "dichroic", "cut_on_nm": 495},
                            }
                        },
                    }
                ]
            },
            "light_paths": [],
        }
        warnings = validate_filter_cube_warnings(instrument)
        self.assertTrue(len(warnings) >= 1, "Partial cube must emit a warning")
        self.assertTrue(any("emission_filter" in w and "degraded" in w for w in warnings))

        payload = generate_virtual_microscope_payload(instrument)
        value = _runtime_projection(payload)["stages"]["cube"][0]["options"][0]["value"]
        self.assertTrue(value.get("_cube_incomplete"))

    def test_partial_filter_cube_missing_two_components_warns(self) -> None:
        """Cube with only emission_filter (missing excitation_filter, dichroic) warns with specific missing list."""
        instrument = {
            "hardware": {
                "optical_path_elements": [
                    {
                        "id": "cube_turret",
                        "stage_role": "cube",
                        "element_type": "turret",
                        "positions": {
                            "Pos_1": {
                                "name": "Minimal Cube",
                                "component_type": "filter_cube",
                                "emission_filter": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50},
                            }
                        },
                    }
                ]
            },
            "light_paths": [],
        }
        warnings = validate_filter_cube_warnings(instrument)
        self.assertTrue(len(warnings) >= 1, "Partial cube missing 2 components must emit a warning")
        self.assertTrue(any("excitation_filter" in w and "dichroic" in w for w in warnings))

        payload = generate_virtual_microscope_payload(instrument)
        value = _runtime_projection(payload)["stages"]["cube"][0]["options"][0]["value"]
        self.assertTrue(value.get("_cube_incomplete"))

    def test_authored_complete_filter_cubes_in_repo_do_not_degrade(self) -> None:
        for yaml_path in sorted(INSTRUMENTS_DIR.rglob("*.yaml")):
            instrument = yaml.safe_load(yaml_path.read_text())
            optical_elements = ((instrument or {}).get("hardware") or {}).get("optical_path_elements") or []
            authored_complete = set()
            for element in optical_elements:
                if not isinstance(element, dict):
                    continue
                if str(element.get("stage_role") or "").lower() != "cube":
                    continue
                mechanism_id = str(element.get("id") or "")
                positions = element.get("positions") or {}
                if isinstance(positions, dict):
                    for position_key, cube_position in positions.items():
                        if not isinstance(cube_position, dict):
                            continue
                        if str(cube_position.get("component_type") or "").lower() != "filter_cube":
                            continue
                        if all(isinstance(cube_position.get(link_key), dict) for link_key in ("excitation_filter", "dichroic", "emission_filter")):
                            authored_complete.add((mechanism_id, str(position_key)))
            if not authored_complete:
                continue

            payload = generate_virtual_microscope_payload(instrument)
            cube_mechanisms = _runtime_projection(payload).get("stages", {}).get("cube", [])
            parsed = {}
            for mechanism in cube_mechanisms:
                mechanism_id = str(mechanism.get("id") or "")
                for option in mechanism.get("options") or []:
                    value = option.get("value") or {}
                    parsed[(mechanism_id, str(value.get("position_key") or value.get("id") or ""))] = value

            for authored_key in authored_complete:
                with self.subTest(instrument=str(yaml_path), mechanism=authored_key[0], position=authored_key[1]):
                    value = parsed[authored_key]
                    self.assertFalse(value.get("_cube_incomplete", False))
                    self.assertFalse(value.get("_unsupported_spectral_model", False))


if __name__ == "__main__":
    unittest.main()
