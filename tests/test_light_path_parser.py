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


    def test_light_source_metadata_is_preserved_for_runtime_simulation(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_sources": [
                        {
                            "kind": "white_light_laser",
                            "role": "depletion",
                            "manufacturer": "Leica",
                            "model": "WLL-STED",
                            "tunable_min_nm": 440,
                            "tunable_max_nm": 790,
                            "width_nm": 2,
                            "path": "confocal",
                            "power": "20 mW",
                            "timing_mode": "pulsed",
                            "pulse_width_ps": 600,
                            "repetition_rate_mhz": 80,
                            "depletion_targets_nm": [640],
                        }
                    ],
                    "light_path": {},
                }
            }
        )

        source = payload["light_sources"][0]["options"][0]["value"]
        self.assertEqual(source["kind"], "white_light_laser")
        self.assertEqual(source["role"], "depletion")
        self.assertEqual(source["spectral_mode"], "tunable_line")
        self.assertEqual(source["tunable_min_nm"], 440.0)
        self.assertEqual(source["tunable_max_nm"], 790.0)
        self.assertEqual(source["width_nm"], 2.0)
        self.assertEqual(source["path"], "confocal")
        self.assertEqual(source["timing_mode"], "pulsed")
        self.assertEqual(source["pulse_width_ps"], 600.0)
        self.assertEqual(source["repetition_rate_mhz"], 80.0)
        self.assertEqual(source["depletion_targets_nm"], [640])
        self.assertEqual(source["power_weight"], 20.0)

    def test_detector_metadata_is_preserved_for_runtime_simulation(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "detectors": [
                        {
                            "kind": "hyd",
                            "manufacturer": "Leica",
                            "model": "HyD S",
                            "channel_name": "HyD1",
                            "path": "confocal",
                            "qe_peak_pct": 45,
                            "supports_time_gating": True,
                            "default_gating_delay_ns": 0.5,
                            "default_gate_width_ns": 6,
                        }
                    ],
                    "light_path": {},
                }
            }
        )

        detector = payload["detectors"][0]["options"][0]["value"]
        self.assertEqual(detector["kind"], "hyd")
        self.assertEqual(detector["detector_class"], "hybrid")
        self.assertEqual(detector["channel_name"], "HyD1")
        self.assertEqual(detector["path"], "confocal")
        self.assertEqual(detector["qe_peak_pct"], 45.0)
        self.assertTrue(detector["supports_time_gating"])
        self.assertEqual(detector["default_gating_delay_ns"], 0.5)
        self.assertEqual(detector["default_gate_width_ns"], 6.0)
        self.assertEqual(detector["default_gain"], 1.0)

    def test_top_level_splitters_are_ingested_with_branch_metadata(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "splitters": [
                        {
                            "name": "Top-level Splitter",
                            "path": "confocal",
                            "dichroic": {"component_type": "dichroic", "cutoffs_nm": [560]},
                            "path_1": {
                                "name": "Red Path",
                                "emission_filter": {"component_type": "bandpass", "center_nm": 700, "width_nm": 75},
                            },
                            "path_2": {
                                "name": "Green Path",
                                "emission_filter": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50},
                            },
                        }
                    ],
                    "light_path": {},
                }
            }
        )

        splitter = payload["splitters"][0]
        self.assertEqual(splitter["name"], "Top-level Splitter")
        self.assertEqual(splitter["path"], "confocal")
        self.assertEqual(len(splitter["branches"]), 2)
        self.assertEqual(splitter["branches"][0]["mode"], "transmitted")
        self.assertEqual(splitter["branches"][1]["mode"], "reflected")
        self.assertEqual(splitter["branches"][0]["component"]["center_nm"], 700.0)
        self.assertEqual(splitter["branches"][1]["component"]["center_nm"], 525.0)

    def test_cube_payload_exposes_direct_component_aliases(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "cube_mechanisms": [
                            {
                                "positions": {
                                    1: {
                                        "name": "TRITC Cube",
                                        "excitation_filter": {"component_type": "bandpass", "center_nm": 550, "width_nm": 25},
                                        "dichroic": {"component_type": "dichroic", "cutoffs_nm": [570]},
                                        "emission_filter": {"component_type": "bandpass", "center_nm": 605, "width_nm": 70},
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        )

        cube = payload["stages"]["cube"][0]["options"][0]["value"]
        self.assertEqual(cube["excitation_filter"]["center_nm"], 550.0)
        self.assertEqual(cube["dichroic"]["cutoffs_nm"], [570.0])
        self.assertEqual(cube["emission_filter"]["center_nm"], 605.0)


if __name__ == "__main__":
    unittest.main()
