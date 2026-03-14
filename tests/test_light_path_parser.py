import unittest

from scripts.light_path_parser import generate_virtual_microscope_payload, infer_light_source_role, validate_light_path


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
                                "branches": [
                                    {
                                        "id": "green",
                                        "label": "Green",
                                        "mode": "transmitted",
                                        "component": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50},
                                        "target_ids": ["detector_1"],
                                    },
                                    {
                                        "id": "red",
                                        "label": "Red",
                                        "mode": "reflected",
                                        "component": {"component_type": "bandpass", "center_nm": 700, "width_nm": 75},
                                        "target_ids": ["detector_2"],
                                    },
                                ],
                            }
                        ],
                        "endpoints": [
                            {"id": "detector_1", "endpoint_type": "detector", "display_label": "Detector 1"},
                            {"id": "detector_2", "endpoint_type": "detector", "display_label": "Detector 2"},
                        ],
                    }
                }
            }
        )

        splitter = payload["splitters"][0]
        self.assertEqual(splitter["control_kind"], "dropdown")
        self.assertEqual(splitter["control_label"], "Camera Splitter")
        self.assertEqual(splitter["options"][0]["slot"], 1)


    def test_validate_light_path_ignores_policy_owned_component_shape_requirements(self) -> None:
        errors = validate_light_path(
            {
                "hardware": {
                    "detectors": [{"channel_name": "Cam"}],
                    "light_path": {
                        "excitation_mechanisms": [
                            {"positions": {1: {"component_type": "bandpass"}}}
                        ]
                    },
                }
            }
        )

        self.assertEqual(errors, [])

    def test_validate_light_path_keeps_splitter_target_graph_validation(self) -> None:
        errors = validate_light_path(
            {
                "hardware": {
                    "detectors": [{"channel_name": "Cam"}],
                    "light_path": {
                        "splitters": [
                            {
                                "path_1": {"targets": ["Cam"]},
                                "path_2": {"targets": ["Missing"]},
                            }
                        ]
                    },
                }
            }
        )

        self.assertTrue(any("does not match any declared detector or endpoint" in message for message in errors))

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
                            "collection_min_nm": 650,
                            "collection_max_nm": 700,
                            "channel_center_nm": 675,
                            "bandwidth_nm": 50,
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
        self.assertEqual(detector["collection_min_nm"], 650.0)
        self.assertEqual(detector["collection_max_nm"], 700.0)
        self.assertEqual(detector["channel_center_nm"], 675.0)
        self.assertEqual(detector["bandwidth_nm"], 50.0)
        self.assertNotIn("default_gain", detector)

    def test_top_level_splitters_are_ingested_with_branch_metadata(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "splitters": [
                        {
                            "name": "Top-level Splitter",
                            "path": "confocal",
                            "dichroic": {"component_type": "dichroic", "cutoffs_nm": [560]},
                            "branches": [
                                {
                                    "id": "red",
                                    "name": "Red Path",
                                    "mode": "transmitted",
                                    "component": {"component_type": "bandpass", "center_nm": 700, "width_nm": 75},
                                    "target_ids": ["detector_1"],
                                },
                                {
                                    "id": "green",
                                    "name": "Green Path",
                                    "mode": "reflected",
                                    "component": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50},
                                    "target_ids": ["detector_2"],
                                },
                            ],
                        }
                    ],
                    "light_path": {
                        "endpoints": [
                            {"id": "detector_1", "endpoint_type": "detector", "display_label": "Detector 1"},
                            {"id": "detector_2", "endpoint_type": "detector", "display_label": "Detector 2"},
                        ]
                    },
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

    def test_splitter_payload_does_not_fabricate_branches_from_legacy_path_nodes(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "splitters": [
                            {
                                "name": "Legacy Splitter",
                                "path_1": {"targets": ["cam"]},
                                "path_2": {"targets": ["pmt"]},
                            }
                        ]
                    }
                }
            }
        )

        self.assertEqual(payload["splitters"][0]["branches"], [])
        self.assertTrue(payload["metadata"].get("graph_incomplete"))

    def test_splitter_branch_targets_match_explicit_endpoint_ids_only(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "endpoints": [
                            {"id": "cam_main", "endpoint_type": "camera_port", "display_label": "Main Cam Port"},
                        ],
                        "splitters": [
                            {
                                "name": "Routing Splitter",
                                "branches": [
                                    {
                                        "id": "path_1",
                                        "label": "Camera branch",
                                        "target_ids": ["Main Cam Port"],
                                    }
                                ],
                            }
                        ],
                    }
                }
            }
        )

        self.assertEqual(payload["splitters"][0]["branches"][0]["target_ids"], [])
        self.assertTrue(payload["metadata"].get("graph_incomplete"))

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

    def test_legacy_position_keys_are_normalized_in_mechanisms(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "excitation_mechanisms": [
                            {
                                "name": "Legacy Excitation Wheel",
                                "positions": {
                                    "Pos_1": {
                                        "component_type": "bandpass",
                                        "center_nm": 405,
                                        "width_nm": 10,
                                    },
                                    "2": {
                                        "component_type": "bandpass",
                                        "center_nm": 488,
                                        "width_nm": 10,
                                    },
                                },
                            }
                        ],
                        "cube_mechanisms": [
                            {
                                "positions": {
                                    "Pos_3": {
                                        "name": "TRITC Cube",
                                        "excitation_filter": {"component_type": "bandpass", "center_nm": 550, "width_nm": 25},
                                        "dichroic": {"component_type": "dichroic", "cutoffs_nm": [570]},
                                        "emission_filter": {"component_type": "bandpass", "center_nm": 605, "width_nm": 70},
                                    }
                                }
                            }
                        ],
                    }
                }
            }
        )

        excitation_slots = [position["slot"] for position in payload["stages"]["excitation"][0]["positions"]]
        cube_slots = [position["slot"] for position in payload["stages"]["cube"][0]["positions"]]
        self.assertEqual(excitation_slots, [1, 2])
        self.assertEqual(cube_slots, [3])

    def test_available_routes_and_default_route_are_exported_for_multi_route_payloads(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_sources": [
                        {"kind": "laser", "wavelength_nm": 488, "path": "confocal"},
                        {"kind": "led", "wavelength_nm": 470, "path": "epi"},
                    ],
                    "detectors": [
                        {"kind": "pmt", "channel_name": "PMT", "path": "confocal"},
                        {"kind": "camera", "channel_name": "Camera", "path": "epi"},
                    ],
                    "light_path": {
                        "excitation_mechanisms": [
                            {
                                "name": "Excitation Wheel",
                                "path": "confocal",
                                "positions": {
                                    1: {"component_type": "bandpass", "center_nm": 488, "width_nm": 10}
                                },
                            }
                        ],
                        "emission_mechanisms": [
                            {
                                "name": "Emission Wheel",
                                "path": "epi",
                                "positions": {
                                    1: {"component_type": "bandpass", "center_nm": 525, "width_nm": 50}
                                },
                            }
                        ],
                    },
                }
            }
        )

        self.assertEqual([entry["id"] for entry in payload["available_routes"]], ["confocal", "epi"])
        self.assertEqual(payload["default_route"], "confocal")
        self.assertGreaterEqual(len(payload["valid_paths"]), 1)


    def test_generate_virtual_microscope_payload_can_disable_inferred_terminals(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "instrument": {"ocular_availability": "trinocular"},
                "hardware": {
                    "light_sources": [{"kind": "halogen_lamp", "path": "transmitted"}],
                    "light_path": {},
                },
            },
            include_inferred_terminals=False,
        )

        self.assertEqual(payload["terminals"], [])
        self.assertTrue(payload["metadata"].get("graph_incomplete"))

    def test_source_position_role_stays_missing_when_yaml_role_is_missing(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_sources": [
                        {"kind": "halogen_lamp", "path": "transmitted", "name": "Lamp"},
                    ]
                }
            }
        )

        source = payload["light_sources"][0]["options"][0]["value"]
        self.assertEqual(source.get("role"), "")
        self.assertEqual(source.get("simulator_inferred_role"), "transmitted_illumination")

    def test_product_code_is_not_backfilled_from_model_or_name(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_sources": [{"kind": "laser", "model": "Laser-1", "name": "Legacy Name"}],
                    "detectors": [{"id": "det-1", "kind": "hyd", "model": "HyD Model"}],
                    "light_path": {
                        "endpoints": [{"id": "ep-1", "endpoint_type": "detector", "model": "Endpoint Model", "name": "Endpoint"}],
                    },
                }
            }
        )

        source = payload["light_sources"][0]["options"][0]["value"]
        detector = payload["detectors"][0]["options"][0]["value"]
        endpoint = next(row for row in payload["terminals"] if row.get("terminal_id") == "ep_1")

        self.assertIsNone(source.get("product_code"))
        self.assertIsNone(detector.get("product_code"))
        self.assertIsNone(endpoint.get("product_code"))

    def test_detector_manufacturer_is_not_backfilled_from_name(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "detectors": [{"id": "det-1", "kind": "hyd", "name": "Detector Legacy Name"}],
                    "light_path": {},
                }
            }
        )

        detector = payload["detectors"][0]["options"][0]["value"]
        self.assertIsNone(detector.get("manufacturer"))

    def test_infer_transmitted_light_source_role_from_path_and_kind(self) -> None:
        self.assertEqual(
            infer_light_source_role({
                "kind": "halogen_lamp",
                "path": "transmitted",
                "notes": "Brightfield and DIC source",
            }),
            "transmitted_illumination",
        )

    def test_infer_light_source_role_defaults_to_excitation_when_no_transmitted_hints_exist(self) -> None:
        self.assertEqual(
            infer_light_source_role({
                "kind": "laser",
                "wavelength_nm": 488,
            }),
            "excitation",
        )


if __name__ == "__main__":
    unittest.main()
