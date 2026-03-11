import unittest

from scripts.light_path_parser import generate_virtual_microscope_payload


class LightPathParserTests(unittest.TestCase):
    def test_details_include_notes_with_pipe_separator(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "excitation_mechanisms": [
                            {
                                "name": "Excitation Wheel",
                                "type": "filter_wheel",
                                "positions": {
                                    1: {
                                        "component_type": "bandpass",
                                        "center_nm": 488,
                                        "width_nm": 10,
                                        "manufacturer": "Chroma",
                                        "product_code": "ET488/10",
                                        "notes": "Primary GFP channel",
                                    }
                                },
                            }
                        ]
                    }
                }
            }
        )

        details = payload["stages"]["excitation"][0]["positions"][0]["details"]
        self.assertEqual(details, "Chroma | ET488/10 | Primary GFP channel")

    def test_stage_mechanism_includes_notes(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "emission_mechanisms": [
                            {
                                "name": "Standalone Emission Wheel",
                                "type": "filter_wheel",
                                "notes": "External filter wheel; faster exchange time",
                                "positions": {
                                    1: {
                                        "component_type": "bandpass",
                                        "center_nm": 525,
                                        "width_nm": 50,
                                    }
                                },
                            }
                        ]
                    }
                }
            }
        )

        mechanism = payload["stages"]["emission"][0]
        self.assertEqual(mechanism["notes"], "External filter wheel; faster exchange time")

    def test_mechanism_payload_includes_display_and_control_metadata(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "excitation_mechanisms": [
                            {
                                "type": "filter_wheel",
                                "positions": {
                                    1: {
                                        "component_type": "bandpass",
                                        "center_nm": 405,
                                        "width_nm": 10,
                                    }
                                },
                            }
                        ],
                        "cube_mechanisms": [
                            {
                                "positions": {
                                    1: {
                                        "name": "GFP Cube",
                                        "excitation_filter": {"component_type": "bandpass", "center_nm": 470, "width_nm": 40},
                                        "dichroic": {"component_type": "dichroic", "cutoffs_nm": [495]},
                                        "emission_filter": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50},
                                    }
                                }
                            }
                        ],
                    }
                }
            }
        )

        excitation = payload["stages"]["excitation"][0]
        self.assertEqual(excitation["display_label"], "Exc 1")
        self.assertEqual(excitation["control_kind"], "dropdown")
        self.assertEqual(excitation["control_label"], "Exc 1")
        self.assertEqual(excitation["options"][0]["display_label"], "Slot 1: 405/10")

        cube = payload["stages"]["cube"][0]
        self.assertEqual(cube["display_label"], "Cube 1")
        self.assertEqual(cube["control_kind"], "dropdown")
        self.assertEqual(cube["control_label"], "Cube 1")
        self.assertEqual(cube["options"][0]["display_label"], "GFP Cube")

    def test_splitter_payload_includes_control_metadata(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "splitters": [
                            {
                                "name": "Camera Splitter",
                                "dichroic": {"component_type": "dichroic", "cutoffs_nm": [560]},
                                "path_1": {"emission_filter": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50}},
                                "path_2": {"emission_filter": {"component_type": "bandpass", "center_nm": 700, "width_nm": 75}},
                            }
                        ]
                    }
                }
            }
        )

        splitter = payload["splitters"][0]
        self.assertEqual(splitter["control_kind"], "dropdown")
        self.assertEqual(splitter["control_label"], "Camera Splitter")
        self.assertEqual(splitter["options"][0]["slot"], 1)


if __name__ == "__main__":
    unittest.main()
