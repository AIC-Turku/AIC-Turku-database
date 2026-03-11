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


if __name__ == "__main__":
    unittest.main()
