import unittest
from pathlib import Path

import yaml

from scripts.light_path_parser import (
    canonicalize_light_path_model,
    generate_virtual_microscope_payload,
    import_legacy_light_path_model,
    infer_light_source_role,
    parse_canonical_light_path_model,
    validate_light_path,
    validate_light_path_warnings,
)


def _runtime_projection(payload: dict) -> dict:
    projections = payload.get("projections") if isinstance(payload, dict) else {}
    if isinstance(projections, dict):
        runtime = projections.get("virtual_microscope")
        if isinstance(runtime, dict):
            return runtime
    return {}


class LightPathParserTests(unittest.TestCase):
    def test_canonical_parser_consumes_only_explicit_v2_fields(self) -> None:
        canonical = parse_canonical_light_path_model(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser"}],
                    "optical_path_elements": [{"id": "exc_filter", "stage_role": "excitation", "element_type": "filter_wheel"}],
                    "endpoints": [{"id": "cam_main", "endpoint_type": "camera_port"}],
                    "light_path": {
                        "excitation_mechanisms": [
                            {
                                "name": "Legacy Excitation Wheel",
                                "positions": {1: {"component_type": "bandpass", "center_nm": 488, "width_nm": 10}},
                            }
                        ]
                    },
                },
            }
        )

        self.assertEqual([row["id"] for row in canonical["sources"]], ["src_488"])
        self.assertEqual([row["id"] for row in canonical["optical_path_elements"]], ["exc_filter"])
        self.assertEqual([row["id"] for row in canonical["endpoints"]], ["cam_main"])
        self.assertEqual(canonical["light_paths"], [])

    def test_dispatcher_prefers_canonical_v2_over_legacy_import(self) -> None:
        canonical = canonicalize_light_path_model(
            {
                "hardware": {
                    "sources": [{"id": "canonical_source", "kind": "laser"}],
                    "optical_path_elements": [{"id": "canonical_splitter", "stage_role": "splitter", "element_type": "splitter"}],
                    "endpoints": [{"id": "canonical_endpoint", "endpoint_type": "detector"}],
                    "light_path": {
                        "excitation_mechanisms": [
                            {
                                "name": "Legacy Excitation Wheel",
                                "positions": {1: {"component_type": "bandpass", "center_nm": 488, "width_nm": 10}},
                            }
                        ],
                        "endpoints": [{"id": "legacy_endpoint", "endpoint_type": "detector"}],
                    },
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{"source_id": "canonical_source"}],
                        "detection_sequence": [{"endpoint_id": "canonical_endpoint"}],
                    }
                ],
            }
        )

        self.assertEqual([row["id"] for row in canonical["sources"]], ["canonical_source"])
        self.assertEqual([row["id"] for row in canonical["optical_path_elements"]], ["canonical_splitter"])
        self.assertEqual([row["id"] for row in canonical["endpoints"]], ["canonical_endpoint"])
        self.assertEqual(canonical["light_paths"][0]["illumination_sequence"], [{"source_id": "canonical_source"}])
        self.assertEqual(canonical["light_paths"][0]["detection_sequence"], [{"endpoint_id": "canonical_endpoint"}])

    def test_stage_role_is_not_synthesized_for_generic_canonical_optical_elements(self) -> None:
        canonical = parse_canonical_light_path_model(
            {
                "hardware": {
                    "optical_path_elements": [
                        {"id": "generic_filter", "element_type": "filter_wheel"},
                        {"id": "route_splitter", "element_type": "splitter"},
                    ]
                }
            }
        )

        generic_filter = next(row for row in canonical["optical_path_elements"] if row["id"] == "generic_filter")
        route_splitter = next(row for row in canonical["optical_path_elements"] if row["id"] == "route_splitter")

        self.assertNotIn("stage_role", generic_filter)
        self.assertEqual(route_splitter.get("stage_role"), "splitter")

    def test_canonical_endpoint_inventory_is_auto_created_from_detectors_and_eyepieces(self) -> None:
        canonical = canonicalize_light_path_model(
            {
                "hardware": {
                    "detectors": [
                        {"id": "detector_1", "kind": "scmos", "channel_name": "Camera 1", "path": "epi"}
                    ],
                    "eyepieces": [
                        {"id": "eyepieces", "name": "Binocular Eyepieces", "path": "epi"}
                    ],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [],
                        "detection_sequence": [
                            {"endpoint_id": "detector_1"},
                            {"endpoint_id": "eyepieces"},
                        ],
                    }
                ],
            }
        )

        self.assertEqual([row["id"] for row in canonical["endpoints"]], ["detector_1", "eyepieces"])
        self.assertEqual(canonical["endpoints"][0]["source_section"], "detectors")
        self.assertEqual(canonical["endpoints"][0]["endpoint_type"], "detector")
        self.assertEqual(canonical["endpoints"][1]["source_section"], "eyepieces")
        self.assertEqual(canonical["endpoints"][1]["endpoint_type"], "eyepiece")

    def test_canonical_parser_accepts_valid_illumination_sequence_item_kinds(self) -> None:
        canonical = parse_canonical_light_path_model(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser"}],
                    "optical_path_elements": [
                        {"id": "exc_filter", "stage_role": "excitation", "element_type": "filter_wheel"},
                    ],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [
                            {"source_id": "src_488"},
                            {"optical_path_element_id": "exc_filter"},
                        ],
                        "detection_sequence": [],
                    }
                ],
            }
        )

        self.assertEqual(canonical["light_paths"][0]["illumination_sequence"][0], {"source_id": "src_488"})
        self.assertEqual(canonical["light_paths"][0]["illumination_sequence"][1], {"optical_path_element_id": "exc_filter"})

    def test_canonical_parser_accepts_valid_detection_sequence_item_kinds(self) -> None:
        canonical = parse_canonical_light_path_model(
            {
                "hardware": {
                    "optical_path_elements": [
                        {"id": "em_filter", "stage_role": "emission", "element_type": "filter_wheel"},
                        {"id": "det_splitter", "stage_role": "splitter", "element_type": "splitter"},
                    ],
                    "detectors": [{"id": "detector_1", "kind": "camera"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [],
                        "detection_sequence": [
                            {"optical_path_element_id": "em_filter"},
                            {"endpoint_id": "detector_1"},
                            {"branches": {"selection_mode": "exclusive", "items": [{"branch_id": "cam", "sequence": [{"endpoint_id": "detector_1"}]}]}},
                        ],
                    }
                ],
            }
        )

        self.assertEqual(canonical["light_paths"][0]["detection_sequence"][0], {"optical_path_element_id": "em_filter"})
        self.assertEqual(canonical["light_paths"][0]["detection_sequence"][1], {"endpoint_id": "detector_1"})
        self.assertIn("branches", canonical["light_paths"][0]["detection_sequence"][2])

    def test_canonical_parser_keeps_valid_branch_block_without_defaulting_fields(self) -> None:
        canonical = parse_canonical_light_path_model(
            {
                "hardware": {
                    "optical_path_elements": [
                        {"id": "det_splitter", "stage_role": "splitter", "element_type": "splitter"},
                    ],
                    "detectors": [{"id": "detector_1", "kind": "camera"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [],
                        "detection_sequence": [
                            {"optical_path_element_id": "det_splitter"},
                            {"branches": {"selection_mode": "exclusive", "items": [{"branch_id": "cam_a", "sequence": [{"endpoint_id": "detector_1"}]}]}},
                        ],
                    }
                ],
            }
        )

        branch_block = canonical["light_paths"][0]["detection_sequence"][1]["branches"]
        self.assertEqual(branch_block["selection_mode"], "exclusive")
        self.assertEqual(branch_block["items"][0]["branch_id"], "cam_a")
        self.assertEqual(branch_block["items"][0]["sequence"], [{"endpoint_id": "detector_1"}])

    def test_migration_compatibility_legacy_import_adapter_remains_explicit_and_available(self) -> None:
        canonical = import_legacy_light_path_model(
            {
                "hardware": {
                    "light_sources": [{"kind": "laser", "wavelength_nm": 488, "path": "confocal"}],
                    "light_path": {
                        "excitation_mechanisms": [
                            {
                                "name": "Legacy Excitation Wheel",
                                "path": "confocal",
                                "positions": {1: {"component_type": "bandpass", "center_nm": 488, "width_nm": 10}},
                            }
                        ],
                    },
                }
            }
        )

        self.assertEqual([route["id"] for route in canonical["light_paths"]], ["confocal"])
        self.assertEqual(canonical["light_paths"][0]["illumination_sequence"][0], {"source_id": canonical["sources"][0]["id"]})

    def test_authoritative_dto_keeps_runtime_projection_nested(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser"}],
                    "optical_path_elements": [{"id": "exc_filter", "stage_role": "excitation", "element_type": "filter_wheel"}],
                    "endpoints": [{"id": "cam_main", "endpoint_type": "camera_port"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{"source_id": "src_488"}, {"optical_path_element_id": "exc_filter"}],
                        "detection_sequence": [{"endpoint_id": "cam_main"}],
                    }
                ],
            }
        )

        self.assertIn("sources", payload)
        self.assertIn("optical_path_elements", payload)
        self.assertIn("endpoints", payload)
        self.assertIn("light_paths", payload)
        self.assertNotIn("stages", payload)
        self.assertNotIn("splitters", payload)
        self.assertNotIn("terminals", payload)
        self.assertIn("projections", payload)
        self.assertIn("virtual_microscope", payload["projections"])
        self.assertIn("hardware_inventory", payload)
        self.assertIn("route_hardware_usage", payload)
        self.assertIn("normalized_endpoints", payload)

    def test_authoritative_dto_builds_numbered_inventory_and_route_graph(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser", "manufacturer": "LaserCo", "model": "488"}],
                    "optical_path_elements": [{"id": "ex_filter", "stage_role": "excitation", "element_type": "filter_wheel", "display_label": "EX 488"}],
                    "endpoints": [{"id": "cam_main", "endpoint_type": "camera_port", "display_label": "Main camera"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{"source_id": "src_488"}, {"optical_path_element_id": "ex_filter"}],
                        "detection_sequence": [{"endpoint_id": "cam_main"}],
                    }
                ],
            }
        )

        self.assertEqual(
            [item["display_number"] for item in payload["hardware_inventory"]],
            [1, 2, 3],
        )
        self.assertEqual(payload["route_hardware_usage"][0]["hardware_inventory_ids"], ["source:src_488", "optical_path_element:ex_filter", "endpoint:cam_main"])
        self.assertEqual(payload["light_paths"][0]["graph_nodes"][0]["display_number"], 1)
        self.assertEqual(payload["light_paths"][0]["graph_nodes"][1]["display_number"], 2)

    def test_inventory_numbering_reuses_identity_across_routes_and_phases(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser", "manufacturer": "LaserCo", "model": "488"}],
                    "optical_path_elements": [{"id": "shared_filter", "stage_role": "excitation", "element_type": "filter_wheel", "display_label": "Shared filter"}],
                    "endpoints": [
                        {"id": "cam_a", "endpoint_type": "camera_port", "display_label": "Camera A"},
                        {"id": "cam_b", "endpoint_type": "camera_port", "display_label": "Camera B"},
                    ],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{"source_id": "src_488"}, {"optical_path_element_id": "shared_filter"}],
                        "detection_sequence": [{"optical_path_element_id": "shared_filter"}, {"endpoint_id": "cam_a"}],
                    },
                    {
                        "id": "confocal",
                        "illumination_sequence": [{"source_id": "src_488"}],
                        "detection_sequence": [{"optical_path_element_id": "shared_filter"}, {"endpoint_id": "cam_b"}],
                    },
                ],
            }
        )

        inventory_item = next(item for item in payload["hardware_inventory"] if item["id"] == "optical_path_element:shared_filter")
        self.assertEqual(inventory_item["display_number"], 2)
        self.assertEqual(inventory_item["inventory_identity"]["inventory_id"], "optical_path_element:shared_filter")

        shared_nodes = [
            node
            for route in payload["light_paths"]
            for node in route["graph_nodes"]
            if node.get("hardware_inventory_id") == "optical_path_element:shared_filter"
        ]
        self.assertGreaterEqual(len(shared_nodes), 3)
        self.assertTrue(all(node["display_number"] == 2 for node in shared_nodes))
        self.assertTrue(all(node["inventory_display_number"] == 2 for node in shared_nodes))
        self.assertTrue(all(node["inventory_identity"]["inventory_id"] == "optical_path_element:shared_filter" for node in shared_nodes))
        self.assertTrue(all(node["graph_occurrence"]["node_id"] == node["id"] for node in shared_nodes))

    def test_details_include_notes_with_pipe_separator(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "excitation_wheel",
                            "name": "Excitation Wheel",
                            "stage_role": "excitation",
                            "element_type": "filter_wheel",
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
                },
                "light_paths": [{"id": "epi", "illumination_sequence": [{"optical_path_element_id": "excitation_wheel"}], "detection_sequence": []}],
            }
        )

        details = _runtime_projection(payload)["stages"]["excitation"][0]["positions"][0]["details"]
        self.assertEqual(details, "Chroma | ET488/10 | Primary GFP channel")


    def test_details_preserve_model_and_product_code_as_distinct_fields(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "excitation_wheel",
                            "name": "Excitation Wheel",
                            "stage_role": "excitation",
                            "element_type": "filter_wheel",
                            "positions": {
                                1: {
                                    "component_type": "bandpass",
                                    "manufacturer": "Semrock",
                                    "model": "BrightLine 615/10",
                                    "product_code": "FF01-615/10-25",
                                }
                            },
                        }
                    ]
                },
                "light_paths": [{"id": "epi", "illumination_sequence": [{"optical_path_element_id": "excitation_wheel"}], "detection_sequence": []}],
            }
        )

        details = _runtime_projection(payload)["stages"]["excitation"][0]["positions"][0]["details"]
        self.assertEqual(details, "Semrock | BrightLine 615/10 | FF01-615/10-25")

    def test_stage_mechanism_includes_notes(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "emission_wheel",
                            "name": "Standalone Emission Wheel",
                            "stage_role": "emission",
                            "element_type": "filter_wheel",
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
                },
                "light_paths": [{"id": "epi", "illumination_sequence": [], "detection_sequence": [{"optical_path_element_id": "emission_wheel"}]}],
            }
        )

        mechanism = _runtime_projection(payload)["stages"]["emission"][0]
        self.assertEqual(mechanism["notes"], "External filter wheel; faster exchange time")

    def test_mechanism_payload_includes_display_and_control_metadata(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "exc_filter",
                            "stage_role": "excitation",
                            "element_type": "filter_wheel",
                            "positions": {
                                1: {
                                    "component_type": "bandpass",
                                    "center_nm": 405,
                                    "width_nm": 10,
                                }
                            },
                        },
                        {
                            "id": "gfp_cube",
                            "stage_role": "cube",
                            "element_type": "filter_cube",
                            "positions": {
                                1: {
                                    "name": "GFP Cube",
                                    "excitation_filter": {"component_type": "bandpass", "center_nm": 470, "width_nm": 40},
                                    "dichroic": {"component_type": "dichroic", "cutoffs_nm": [495]},
                                    "emission_filter": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50},
                                }
                            },
                        },
                    ]
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{"optical_path_element_id": "gfp_cube"}, {"optical_path_element_id": "exc_filter"}],
                        "detection_sequence": [{"optical_path_element_id": "gfp_cube"}],
                    }
                ],
            }
        )

        excitation = _runtime_projection(payload)["stages"]["excitation"][0]
        self.assertEqual(excitation["display_label"], "Exc 1")
        self.assertEqual(excitation["control_kind"], "dropdown")
        self.assertEqual(excitation["control_label"], "Exc 1")
        self.assertEqual(excitation["options"][0]["display_label"], "Slot 1: 405/10")

        cube = _runtime_projection(payload)["stages"]["cube"][0]
        self.assertEqual(cube["display_label"], "Cube 1")
        self.assertEqual(cube["control_kind"], "dropdown")
        self.assertEqual(cube["control_label"], "Cube 1")
        self.assertEqual(cube["options"][0]["display_label"], "GFP Cube")

    def test_splitter_payload_is_derived_from_route_owned_branch_blocks(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser"}],
                    "optical_path_elements": [
                        {"id": "camera_splitter", "name": "Camera Splitter", "stage_role": "splitter", "element_type": "splitter", "selection_mode": "exclusive"},
                        {"id": "green_filter", "name": "Green Filter", "stage_role": "emission", "element_type": "filter_wheel", "component": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50}},
                        {"id": "red_filter", "name": "Red Filter", "stage_role": "emission", "element_type": "filter_wheel", "component": {"component_type": "bandpass", "center_nm": 700, "width_nm": 75}},
                    ],
                    "endpoints": [
                        {"id": "detector_1", "endpoint_type": "detector", "display_label": "Detector 1"},
                        {"id": "detector_2", "endpoint_type": "detector", "display_label": "Detector 2"},
                    ],
                },
                "light_paths": [
                    {
                        "id": "confocal",
                        "illumination_sequence": [{"source_id": "src_488"}],
                        "detection_sequence": [
                            {"optical_path_element_id": "camera_splitter"},
                            {
                                "branches": {
                                    "selection_mode": "exclusive",
                                    "items": [
                                        {
                                            "branch_id": "green",
                                            "label": "Green",
                                            "sequence": [
                                                {"optical_path_element_id": "green_filter"},
                                                {"endpoint_id": "detector_1"},
                                            ],
                                        },
                                        {
                                            "branch_id": "red",
                                            "label": "Red",
                                            "sequence": [
                                                {"optical_path_element_id": "red_filter"},
                                                {"endpoint_id": "detector_2"},
                                            ],
                                        },
                                    ],
                                }
                            },
                        ],
                    }
                ],
            }
        )

        splitter = _runtime_projection(payload)["splitters"][0]
        self.assertEqual(splitter["control_kind"], "dropdown")
        self.assertEqual(splitter["control_label"], "Camera Splitter")
        self.assertEqual(splitter["options"][0]["slot"], 1)
        self.assertEqual(splitter["branches"][0]["sequence"][0]["optical_path_element_id"], "green_filter")
        self.assertEqual(splitter["branches"][0]["target_ids"], ["detector_1"])


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

        source = _runtime_projection(payload)["light_sources"][0]["options"][0]["value"]
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

        detector = _runtime_projection(payload)["detectors"][0]["options"][0]["value"]
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

    def test_runtime_projection_uses_unified_endpoint_inventory_for_terminals_and_detectors(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "detectors": [
                        {"id": "detector_1", "kind": "hyd", "channel_name": "HyD1", "path": "confocal"}
                    ],
                    "eyepieces": [
                        {"id": "eyepieces", "name": "Eyepieces", "path": "confocal"}
                    ],
                },
                "light_paths": [
                    {
                        "id": "confocal",
                        "illumination_sequence": [],
                        "detection_sequence": [{"endpoint_id": "detector_1"}],
                    }
                ],
            }
        )

        runtime = _runtime_projection(payload)
        self.assertEqual([row["id"] for row in payload["endpoints"]], ["detector_1", "eyepieces"])
        self.assertEqual([row["terminal_id"] for row in runtime["terminals"]], ["detector_1", "eyepieces"])
        self.assertEqual(runtime["detectors"][0]["id"], "detector_1")

    def test_duplicate_endpoint_ids_across_endpoint_capable_inventories_raise_validation_error(self) -> None:
        errors = validate_light_path(
            {
                "hardware": {
                    "detectors": [{"id": "shared_endpoint", "kind": "camera"}],
                    "eyepieces": [{"id": "shared_endpoint"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [],
                        "detection_sequence": [{"endpoint_id": "shared_endpoint"}],
                    }
                ],
            }
        )

        self.assertTrue(any("normalized endpoint id `shared_endpoint`" in error for error in errors))

    def test_invalid_mixed_illumination_sequence_item_is_rejected(self) -> None:
        errors = validate_light_path(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser"}],
                    "optical_path_elements": [{"id": "exc_filter", "stage_role": "excitation", "element_type": "filter_wheel"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{"source_id": "src_488", "optical_path_element_id": "exc_filter"}],
                        "detection_sequence": [],
                    }
                ],
            }
        )

        self.assertTrue(any("illumination sequence item must declare exactly one of source_id, or optical_path_element_id." in error for error in errors))

    def test_invalid_mixed_detection_sequence_item_is_rejected(self) -> None:
        errors = validate_light_path(
            {
                "hardware": {
                    "optical_path_elements": [{"id": "em_filter", "stage_role": "emission", "element_type": "filter_wheel"}],
                    "detectors": [{"id": "detector_1", "kind": "camera"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [],
                        "detection_sequence": [{"optical_path_element_id": "em_filter", "endpoint_id": "detector_1"}],
                    }
                ],
            }
        )

        self.assertTrue(any("detection sequence item must declare exactly one of optical_path_element_id, endpoint_id, or branches" in error for error in errors))

    def test_empty_sequence_item_is_rejected(self) -> None:
        errors = validate_light_path(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{}],
                        "detection_sequence": [],
                    }
                ],
            }
        )

        self.assertTrue(any("illumination sequence item must declare exactly one of source_id, or optical_path_element_id." in error for error in errors))

    def test_illumination_branch_blocks_are_rejected_and_detection_branch_locals_stay_strict(self) -> None:
        errors = validate_light_path(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser"}],
                    "optical_path_elements": [
                        {"id": "illum_splitter", "stage_role": "splitter", "element_type": "splitter"},
                        {"id": "det_splitter", "stage_role": "splitter", "element_type": "splitter"},
                    ],
                    "detectors": [{"id": "detector_1", "kind": "camera"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [
                            {"optical_path_element_id": "illum_splitter"},
                            {"branches": {"selection_mode": "exclusive", "items": [{"branch_id": "bad_illum", "sequence": [{"endpoint_id": "detector_1"}]}]}},
                        ],
                        "detection_sequence": [
                            {"optical_path_element_id": "det_splitter"},
                            {"branches": {"selection_mode": "exclusive", "items": [{"branch_id": "bad_detect", "sequence": [{"source_id": "src_488"}]}]}},
                        ],
                    }
                ],
            }
        )

        self.assertTrue(any("illumination sequence item must declare exactly one of source_id, or optical_path_element_id." in error for error in errors))
        self.assertTrue(any("branch-local detection sequence item must declare exactly one of optical_path_element_id, or endpoint_id." in error for error in errors))

    def test_missing_branch_selection_mode_is_rejected(self) -> None:
        errors = validate_light_path(
            {
                "hardware": {
                    "optical_path_elements": [{"id": "det_splitter", "stage_role": "splitter", "element_type": "splitter"}],
                    "detectors": [{"id": "detector_1", "kind": "camera"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [],
                        "detection_sequence": [
                            {"optical_path_element_id": "det_splitter"},
                            {"branches": {"items": [{"branch_id": "cam_a", "sequence": [{"endpoint_id": "detector_1"}]}]}},
                        ],
                    }
                ],
            }
        )

        self.assertTrue(any("branches.selection_mode: must be one of fixed, exclusive, multiple." in error for error in errors))

    def test_missing_branch_items_is_rejected(self) -> None:
        errors = validate_light_path(
            {
                "hardware": {
                    "optical_path_elements": [{"id": "det_splitter", "stage_role": "splitter", "element_type": "splitter"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [],
                        "detection_sequence": [
                            {"optical_path_element_id": "det_splitter"},
                            {"branches": {"selection_mode": "exclusive"}},
                        ],
                    }
                ],
            }
        )

        self.assertTrue(any("branches.items: must be a non-empty list." in error for error in errors))

    def test_empty_branch_items_list_is_rejected(self) -> None:
        errors = validate_light_path(
            {
                "hardware": {
                    "optical_path_elements": [{"id": "det_splitter", "stage_role": "splitter", "element_type": "splitter"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [],
                        "detection_sequence": [
                            {"optical_path_element_id": "det_splitter"},
                            {"branches": {"selection_mode": "exclusive", "items": []}},
                        ],
                    }
                ],
            }
        )

        self.assertTrue(any("branches.items: must be a non-empty list." in error for error in errors))

    def test_missing_branch_id_is_rejected(self) -> None:
        errors = validate_light_path(
            {
                "hardware": {
                    "optical_path_elements": [{"id": "det_splitter", "stage_role": "splitter", "element_type": "splitter"}],
                    "detectors": [{"id": "detector_1", "kind": "camera"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [],
                        "detection_sequence": [
                            {"optical_path_element_id": "det_splitter"},
                            {"branches": {"selection_mode": "exclusive", "items": [{"sequence": [{"endpoint_id": "detector_1"}]}]}},
                        ],
                    }
                ],
            }
        )

        self.assertTrue(any(".branch_id: is required." in error for error in errors))

    def test_missing_branch_sequence_is_rejected(self) -> None:
        errors = validate_light_path(
            {
                "hardware": {
                    "optical_path_elements": [{"id": "det_splitter", "stage_role": "splitter", "element_type": "splitter"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [],
                        "detection_sequence": [
                            {"optical_path_element_id": "det_splitter"},
                            {"branches": {"selection_mode": "exclusive", "items": [{"branch_id": "cam_a"}]}},
                        ],
                    }
                ],
            }
        )

        self.assertTrue(any(".sequence: must be a non-empty list." in error for error in errors))

    def test_deprecated_hardware_owned_branch_routing_is_rejected_in_canonical_mode(self) -> None:
        errors = validate_light_path(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "legacy_splitter",
                            "stage_role": "splitter",
                            "element_type": "splitter",
                            "branches": [{"id": "path_a", "target_ids": ["detector_1"]}],
                        }
                    ],
                    "detectors": [{"id": "detector_1", "kind": "camera"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [],
                        "detection_sequence": [{"optical_path_element_id": "legacy_splitter"}, {"endpoint_id": "detector_1"}],
                    }
                ],
            }
        )

        self.assertTrue(any("deprecated hardware-owned routing metadata is not allowed in canonical topology" in error for error in errors))

    def test_warning_when_detection_path_lacks_clear_endpoint_termination(self) -> None:
        warnings = validate_light_path_warnings(
            {
                "hardware": {
                    "optical_path_elements": [
                        {"id": "emission_wheel", "stage_role": "emission", "element_type": "filter_wheel"}
                    ]
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [],
                        "detection_sequence": [{"optical_path_element_id": "emission_wheel"}],
                    }
                ],
            }
        )

        self.assertTrue(any("route does not terminate in a clear explicit endpoint_id" in warning for warning in warnings))

    def test_warning_when_branch_lacks_clear_endpoint_termination(self) -> None:
        warnings = validate_light_path_warnings(
            {
                "hardware": {
                    "optical_path_elements": [
                        {"id": "splitter_1", "stage_role": "splitter", "element_type": "splitter"},
                        {"id": "green_filter", "stage_role": "emission", "element_type": "filter_wheel"},
                    ],
                    "detectors": [{"id": "detector_1", "kind": "camera"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [],
                        "detection_sequence": [
                            {"optical_path_element_id": "splitter_1"},
                            {
                                "branches": {
                                    "selection_mode": "exclusive",
                                    "items": [
                                        {"branch_id": "good", "sequence": [{"endpoint_id": "detector_1"}]},
                                        {"branch_id": "bad", "sequence": [{"optical_path_element_id": "green_filter"}]},
                                    ],
                                }
                            },
                        ],
                    }
                ],
            }
        )

        self.assertTrue(any(".branches.items[1].sequence: branch does not terminate" in warning for warning in warnings))

    def test_route_owned_branches_drive_runtime_splitter_metadata(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser"}],
                    "optical_path_elements": [
                        {"id": "route_splitter", "name": "Top-level Splitter", "stage_role": "splitter", "element_type": "splitter", "selection_mode": "exclusive"},
                        {"id": "red_filter", "stage_role": "emission", "element_type": "filter_wheel", "component": {"component_type": "bandpass", "center_nm": 700, "width_nm": 75}},
                        {"id": "green_filter", "stage_role": "emission", "element_type": "filter_wheel", "component": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50}},
                    ],
                    "endpoints": [
                        {"id": "detector_1", "endpoint_type": "detector", "display_label": "Detector 1"},
                        {"id": "detector_2", "endpoint_type": "detector", "display_label": "Detector 2"},
                    ],
                }
                ,
                "light_paths": [
                    {
                        "id": "confocal",
                        "illumination_sequence": [{"source_id": "src_488"}],
                        "detection_sequence": [
                            {"optical_path_element_id": "route_splitter"},
                            {"branches": {"selection_mode": "exclusive", "items": [
                                {"branch_id": "red", "label": "Red Path", "mode": "transmitted", "sequence": [{"optical_path_element_id": "red_filter"}, {"endpoint_id": "detector_1"}]},
                                {"branch_id": "green", "label": "Green Path", "mode": "reflected", "sequence": [{"optical_path_element_id": "green_filter"}, {"endpoint_id": "detector_2"}]},
                            ]}},
                        ],
                    }
                ],
            }
        )

        splitter = _runtime_projection(payload)["splitters"][0]
        self.assertEqual(splitter["name"], "Top-level Splitter")
        self.assertEqual(splitter["path"], "confocal")
        self.assertEqual(len(splitter["branches"]), 2)
        self.assertEqual(splitter["branches"][0]["mode"], "transmitted")
        self.assertEqual(splitter["branches"][1]["mode"], "reflected")
        self.assertEqual(splitter["branches"][0]["component"]["center_nm"], 700.0)
        self.assertEqual(splitter["branches"][1]["component"]["center_nm"], 525.0)

    def test_route_owned_splitter_branch_component_uses_selected_position_payload(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser", "wavelength_nm": 488}],
                    "optical_path_elements": [
                        {"id": "camera_splitter", "name": "Camera Splitter", "stage_role": "splitter", "element_type": "splitter"},
                        {
                            "id": "emission_selector",
                            "name": "Emission Selector",
                            "stage_role": "emission",
                            "element_type": "filter_wheel",
                            "positions": {
                                "green": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50, "label": "525/50"},
                                "red": {"component_type": "bandpass", "center_nm": 700, "width_nm": 75, "label": "700/75"},
                            },
                        },
                    ],
                    "endpoints": [
                        {"id": "cam_a", "endpoint_type": "camera_port"},
                        {"id": "cam_b", "endpoint_type": "camera_port"},
                    ],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{"source_id": "src_488"}],
                        "detection_sequence": [
                            {"optical_path_element_id": "camera_splitter"},
                            {
                                "branches": {
                                    "selection_mode": "exclusive",
                                    "items": [
                                        {"branch_id": "green", "mode": "reflected", "sequence": [{"optical_path_element_id": "emission_selector", "position_id": "green"}, {"endpoint_id": "cam_a"}]},
                                        {"branch_id": "red", "mode": "transmitted", "sequence": [{"optical_path_element_id": "emission_selector", "position_id": "red"}, {"endpoint_id": "cam_b"}]},
                                    ],
                                }
                            },
                        ],
                    }
                ],
            }
        )

        splitter = _runtime_projection(payload)["splitters"][0]
        self.assertEqual([branch["component"]["center_nm"] for branch in splitter["branches"]], [525.0, 700.0])
        self.assertEqual([branch["component"]["display_label"] for branch in splitter["branches"]], ["525/50", "700/75"])

    def test_nikon_dual_camera_splitter_branch_optics_are_parser_resolved(self) -> None:
        instrument = yaml.safe_load(
            Path("instruments/Nikon Ti2-E Crest V3 Spinning Disk.yaml").read_text(encoding="utf-8")
        )
        payload = generate_virtual_microscope_payload(instrument)

        route = next((entry for entry in payload["light_paths"] if entry.get("id") == "confocal_spinning_disk"), None)
        self.assertIsNotNone(route)
        routing_step = next(
            step for step in route["selected_execution"]["steps"]
            if step.get("kind") == "routing_component" and step.get("phase") == "detection"
        )
        branches = routing_step["routing"]["branches"]
        self.assertTrue(any(item.get("kind") == "optical_component" for item in branches[0]["sequence"]))
        self.assertTrue(any(item.get("kind") == "optical_component" for item in branches[1]["sequence"]))

        splitter = next(
            row for row in _runtime_projection(payload)["splitters"]
            if row.get("id") == "trinocular_port"
        )
        branch_map = {branch["id"]: branch for branch in splitter["branches"]}
        self.assertIn("to_master", branch_map)
        self.assertIn("to_slave", branch_map)
        self.assertEqual(branch_map["to_master"]["target_ids"], ["kinetix_master_camera"])
        self.assertEqual(branch_map["to_slave"]["target_ids"], ["kinetix_slave_camera"])
        self.assertIn("spectral_ops", branch_map["to_master"]["component"])
        self.assertIn("spectral_ops", branch_map["to_slave"]["component"])

    def test_oni_internal_emission_splitter_passthrough_is_flagged_when_branch_has_no_optics(self) -> None:
        instrument = yaml.safe_load(
            Path("instruments/ONI Nanoimager.yaml").read_text(encoding="utf-8")
        )
        payload = generate_virtual_microscope_payload(instrument)

        route = next((entry for entry in payload["light_paths"] if entry.get("id") == "tirf"), None)
        self.assertIsNotNone(route)
        routing_step = next(
            step for step in route["selected_execution"]["steps"]
            if step.get("kind") == "routing_component" and step.get("phase") == "detection"
        )
        self.assertTrue(all(
            all(seq_step.get("kind") != "optical_component" for seq_step in branch.get("sequence") or [])
            for branch in routing_step["routing"]["branches"]
        ))

        splitter = next(
            row for row in _runtime_projection(payload)["splitters"]
            if row.get("id") == "internal_emission_splitter"
        )
        for branch in splitter["branches"]:
            component = branch["component"]
            self.assertEqual(component.get("component_type"), "unknown")
            detection_ops = component.get("spectral_ops", {}).get("detection") or []
            self.assertTrue(detection_ops)
            self.assertIn("unsupported_reason", detection_ops[0])

    def test_migration_compatibility_splitter_payload_does_not_fabricate_branches_from_legacy_path_nodes(self) -> None:
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

        self.assertEqual(_runtime_projection(payload)["splitters"][0]["branches"], [])
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

        self.assertEqual(_runtime_projection(payload)["splitters"][0]["branches"][0]["target_ids"], [])
        self.assertTrue(payload["metadata"].get("graph_incomplete"))

    def test_branch_blocks_must_follow_optical_path_element_and_detection_branches_need_endpoints(self) -> None:
        errors = validate_light_path(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser"}],
                    "optical_path_elements": [{"id": "split_1", "stage_role": "splitter", "element_type": "splitter"}],
                    "endpoints": [{"id": "cam_a", "endpoint_type": "detector"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{"source_id": "src_488"}],
                        "detection_sequence": [
                            {"branches": {"selection_mode": "exclusive", "items": [{"branch_id": "broken", "sequence": [{"optical_path_element_id": "split_1"}]}]}}
                        ],
                    }
                ],
            }
        )
        warnings = validate_light_path_warnings(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser"}],
                    "optical_path_elements": [{"id": "split_1", "stage_role": "splitter", "element_type": "splitter"}],
                    "endpoints": [{"id": "cam_a", "endpoint_type": "detector"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{"source_id": "src_488"}],
                        "detection_sequence": [
                            {"branches": {"selection_mode": "exclusive", "items": [{"branch_id": "broken", "sequence": [{"optical_path_element_id": "split_1"}]}]}}
                        ],
                    }
                ],
            }
        )

        self.assertTrue(any("branches must follow an optical_path_element_id" in error for error in errors))
        self.assertTrue(any("branch does not terminate in a clear explicit endpoint_id" in warning for warning in warnings))

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

        cube = _runtime_projection(payload)["stages"]["cube"][0]["options"][0]["value"]
        self.assertEqual(cube["excitation_filter"]["center_nm"], 550.0)
        self.assertEqual(cube["dichroic"]["cutoffs_nm"], [570.0])
        self.assertEqual(cube["emission_filter"]["center_nm"], 605.0)

    def test_filter_cube_single_band_synthesizes_bandpass_emission_filter(self) -> None:
        """filter_cube positions with a single band should produce a bandpass emission_filter."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "cube_turret",
                            "stage_role": "cube",
                            "element_type": "turret",
                            "positions": {
                                "Pos_1": {
                                    "name": "CY3 Cube",
                                    "component_type": "filter_cube",
                                    "bands": [{"center_nm": 605, "width_nm": 70}],
                                }
                            },
                        }
                    ],
                }
            }
        )
        cube_options = _runtime_projection(payload)["stages"]["cube"][0]["options"]
        cube = cube_options[0]["value"]
        self.assertIn("emission_filter", cube["linked_components"])
        ef = cube["emission_filter"]
        self.assertEqual(ef["component_type"], "bandpass")
        self.assertEqual(ef["center_nm"], 605.0)
        self.assertEqual(ef["width_nm"], 70.0)

    def test_filter_cube_multiband_synthesizes_multiband_bandpass_emission_filter(self) -> None:
        """filter_cube positions with multiple bands should produce a multiband_bandpass emission_filter."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "cube_turret",
                            "stage_role": "cube",
                            "element_type": "turret",
                            "positions": {
                                "Pos_1": {
                                    "name": "Triple Band Cube",
                                    "component_type": "filter_cube",
                                    "bands": [
                                        {"center_nm": 459, "width_nm": 25},
                                        {"center_nm": 525, "width_nm": 30},
                                        {"center_nm": 608, "width_nm": 30},
                                    ],
                                }
                            },
                        }
                    ],
                }
            }
        )
        cube = _runtime_projection(payload)["stages"]["cube"][0]["options"][0]["value"]
        ef = cube["emission_filter"]
        self.assertEqual(ef["component_type"], "multiband_bandpass")
        self.assertEqual(len(ef["bands"]), 3)
        self.assertEqual(ef["bands"][0]["center_nm"], 459.0)
        self.assertEqual(ef["bands"][1]["center_nm"], 525.0)
        self.assertEqual(ef["bands"][2]["center_nm"], 608.0)

    def test_filter_cube_longpass_synthesizes_longpass_emission_filter(self) -> None:
        """filter_cube positions with cut_on_nm list produce a longpass emission_filter."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "cube_turret",
                            "stage_role": "cube",
                            "element_type": "turret",
                            "positions": {
                                "Pos_1": {
                                    "name": "DAPI Cube",
                                    "component_type": "filter_cube",
                                    "cut_on_nm": [425],
                                }
                            },
                        }
                    ],
                }
            }
        )
        cube = _runtime_projection(payload)["stages"]["cube"][0]["options"][0]["value"]
        ef = cube["emission_filter"]
        self.assertEqual(ef["component_type"], "longpass")
        self.assertEqual(ef["cut_on_nm"], 425.0)

    def test_filter_cube_with_explicit_linked_components_keeps_them(self) -> None:
        """filter_cube should not override explicit linked_components."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "cube_turret",
                            "stage_role": "cube",
                            "element_type": "turret",
                            "positions": {
                                "Pos_1": {
                                    "name": "TRITC Cube",
                                    "excitation_filter": {"component_type": "bandpass", "center_nm": 550, "width_nm": 25},
                                    "emission_filter": {"component_type": "bandpass", "center_nm": 605, "width_nm": 70},
                                }
                            },
                        }
                    ],
                }
            }
        )
        cube = _runtime_projection(payload)["stages"]["cube"][0]["options"][0]["value"]
        self.assertEqual(cube["excitation_filter"]["center_nm"], 550.0)
        self.assertEqual(cube["emission_filter"]["center_nm"], 605.0)

    def test_flattened_cube_synthesizes_dichroic_from_emission_band(self) -> None:
        """Flattened filter_cube should synthesize a dichroic estimated from the emission band edge."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "cube_turret",
                            "stage_role": "cube",
                            "element_type": "turret",
                            "positions": {
                                "Pos_1": {
                                    "name": "GFP Cube",
                                    "component_type": "filter_cube",
                                    "bands": [{"center_nm": 525, "width_nm": 50}],
                                }
                            },
                        }
                    ],
                }
            }
        )
        cube = _runtime_projection(payload)["stages"]["cube"][0]["options"][0]["value"]
        self.assertIn("dichroic", cube["linked_components"])
        di = cube["dichroic"]
        self.assertEqual(di["component_type"], "dichroic")
        # Dichroic cut-on: (525 - 50/2) - 20 = 480.0
        self.assertEqual(di["cut_on_nm"], 480.0)

    def test_flattened_cube_multiband_dichroic_uses_lowest_band_edge(self) -> None:
        """Multiband flattened cube dichroic should use lowest emission band edge."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "cube_turret",
                            "stage_role": "cube",
                            "element_type": "turret",
                            "positions": {
                                "Pos_1": {
                                    "name": "Triple Band",
                                    "component_type": "filter_cube",
                                    "bands": [
                                        {"center_nm": 459, "width_nm": 25},
                                        {"center_nm": 525, "width_nm": 30},
                                        {"center_nm": 608, "width_nm": 30},
                                    ],
                                }
                            },
                        }
                    ],
                }
            }
        )
        cube = _runtime_projection(payload)["stages"]["cube"][0]["options"][0]["value"]
        di = cube["dichroic"]
        # Lowest band edge: 459 - 25/2 = 446.5, dichroic = 446.5 - 20 = 426.5
        self.assertEqual(di["cut_on_nm"], 426.5)

    def test_flattened_cube_longpass_dichroic_estimate(self) -> None:
        """Longpass flattened cube should also get a synthesized dichroic."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "cube_turret",
                            "stage_role": "cube",
                            "element_type": "turret",
                            "positions": {
                                "Pos_1": {
                                    "name": "DAPI LP",
                                    "component_type": "filter_cube",
                                    "cut_on_nm": [425],
                                }
                            },
                        }
                    ],
                }
            }
        )
        cube = _runtime_projection(payload)["stages"]["cube"][0]["options"][0]["value"]
        di = cube["dichroic"]
        self.assertEqual(di["component_type"], "dichroic")
        # Dichroic: 425 - 20 = 405.0
        self.assertEqual(di["cut_on_nm"], 405.0)

    def test_flattened_cube_flagged_incomplete_without_excitation(self) -> None:
        """Flattened cubes without excitation data should be flagged _cube_incomplete."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "cube_turret",
                            "stage_role": "cube",
                            "element_type": "turret",
                            "positions": {
                                "Pos_1": {
                                    "name": "Incomplete Cube",
                                    "component_type": "filter_cube",
                                    "bands": [{"center_nm": 510, "width_nm": 40}],
                                }
                            },
                        }
                    ],
                }
            }
        )
        cube = _runtime_projection(payload)["stages"]["cube"][0]["options"][0]["value"]
        self.assertTrue(cube.get("_cube_incomplete"), "Flattened cube without excitation should be flagged incomplete")
        self.assertTrue(cube.get("_unsupported_spectral_model"), "Flattened incomplete cube should be marked unsupported")
        self.assertEqual(cube["spectral_ops"]["illumination"][0].get("unsupported_reason"), "filter_cube_incomplete_reconstruction")
        self.assertEqual(cube["spectral_ops"]["detection"][0].get("unsupported_reason"), "filter_cube_incomplete_reconstruction")

    def test_explicit_cube_not_flagged_incomplete(self) -> None:
        """Cubes with explicit excitation_filter should NOT be flagged incomplete."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "cube_turret",
                            "stage_role": "cube",
                            "element_type": "turret",
                            "positions": {
                                "Pos_1": {
                                    "name": "Full Cube",
                                    "excitation_filter": {"component_type": "bandpass", "center_nm": 470, "width_nm": 40},
                                    "dichroic": {"component_type": "dichroic", "cut_on_nm": 495},
                                    "emission_filter": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50},
                                }
                            },
                        }
                    ],
                }
            }
        )
        cube = _runtime_projection(payload)["stages"]["cube"][0]["options"][0]["value"]
        self.assertFalse(cube.get("_cube_incomplete", False), "Explicit cube should not be flagged incomplete")
        self.assertFalse(cube.get("_unsupported_spectral_model", False), "Explicit cube should remain supported")

    def test_splitter_branches_deduplicated_across_routes(self) -> None:
        """Branches with the same branch_id across routes should be merged, not duplicated."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "trinocular",
                            "stage_role": "splitter",
                            "element_type": "splitter",
                            "selection_mode": "exclusive",
                        },
                    ],
                    "endpoints": [
                        {"id": "cam", "endpoint_type": "camera_port"},
                        {"id": "eyes", "endpoint_type": "eyepiece"},
                    ],
                },
                "light_paths": [
                    {
                        "id": "route_a",
                        "name": "Route A",
                        "detection_sequence": [
                            {"optical_path_element_id": "trinocular"},
                            {
                                "branches": {
                                    "selection_mode": "exclusive",
                                    "items": [
                                        {"branch_id": "to_cam", "label": "To Camera", "sequence": [{"endpoint_id": "cam"}]},
                                        {"branch_id": "to_eyes", "label": "To Eyes", "sequence": [{"endpoint_id": "eyes"}]},
                                    ],
                                }
                            },
                        ],
                    },
                    {
                        "id": "route_b",
                        "name": "Route B",
                        "detection_sequence": [
                            {"optical_path_element_id": "trinocular"},
                            {
                                "branches": {
                                    "selection_mode": "exclusive",
                                    "items": [
                                        {"branch_id": "to_cam", "label": "To Camera", "sequence": [{"endpoint_id": "cam"}]},
                                        {"branch_id": "to_eyes", "label": "To Eyes", "sequence": [{"endpoint_id": "eyes"}]},
                                    ],
                                }
                            },
                        ],
                    },
                ],
            }
        )
        splitters = _runtime_projection(payload)["splitters"]
        self.assertEqual(len(splitters), 1)
        branches = splitters[0]["branches"]
        self.assertEqual(len(branches), 2, f"Expected 2 branches but got {len(branches)}: {[b.get('label') for b in branches]}")


    def test_multiband_dichroic_bands_are_normalized_and_labeled(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "dichroic_mechanisms": [
                            {
                                "positions": {
                                    1: {
                                        "component_type": "multiband_dichroic",
                                        "transmission_bands": [
                                            {"center_nm": "520", "width_nm": "30"},
                                            {"center_nm": "bad", "width_nm": 25},
                                            {"center_nm": 700, "width_nm": None},
                                        ],
                                        "reflection_bands": [
                                            {"center_nm": 450, "width_nm": "40"},
                                            {"center_nm": "", "width_nm": "15"},
                                        ],
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        )

        dichroic = _runtime_projection(payload)["stages"]["dichroic"][0]["options"][0]["value"]
        self.assertEqual(dichroic["transmission_bands"], [{"center_nm": 520.0, "width_nm": 30.0}])
        self.assertEqual(dichroic["reflection_bands"], [{"center_nm": 450.0, "width_nm": 40.0}])
        self.assertEqual(dichroic["label"], "Dichroic T[520/30] | R[450/40]")

    def test_migration_compatibility_splitter_dichroic_keeps_legacy_cutoff_and_preserves_explicit_bands(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "splitters": [
                            {
                                "name": "Legacy Splitter",
                                "dichroic": {
                                    "component_type": "dichroic",
                                    "cut_on_nm": "560",
                                    "transmission_bands": [{"center_nm": 525, "width_nm": 50}],
                                    "reflection_bands": [{"center_nm": "700", "width_nm": "75"}],
                                },
                            }
                        ]
                    }
                }
            }
        )

        dichroic = _runtime_projection(payload)["splitters"][0]["dichroic"]["positions"]["1"]
        self.assertEqual(dichroic["cutoffs_nm"], [560.0])
        self.assertEqual(dichroic["label"], "Dichroic [560]")
        self.assertEqual(dichroic["transmission_bands"], [{"center_nm": 525.0, "width_nm": 50.0}])
        self.assertEqual(dichroic["reflection_bands"], [{"center_nm": 700.0, "width_nm": 75.0}])


    def test_csu_w1_like_multiband_dichroic_keeps_green_transmission_band(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "dichroic_mechanisms": [
                            {
                                "name": "CSU-W1 Dichroic Slider",
                                "positions": {
                                    "Pos_1": {
                                        "component_type": "multiband_dichroic",
                                        "transmission_bands": [
                                            {"center_nm": 440, "width_nm": 25},
                                            {"center_nm": 521, "width_nm": 25},
                                            {"center_nm": 607, "width_nm": 25},
                                        ],
                                        "reflection_bands": [{"center_nm": 488, "width_nm": 20}],
                                    }
                                },
                            }
                        ],
                        "emission_mechanisms": [
                            {
                                "name": "CSU-W1 Emission Wheel",
                                "positions": {
                                    "Pos_1": {"component_type": "bandpass", "center_nm": 525, "width_nm": 30}
                                },
                            }
                        ],
                    }
                }
            }
        )

        dichroic = _runtime_projection(payload)["stages"]["dichroic"][0]["options"][0]["value"]
        self.assertIn({"center_nm": 521.0, "width_nm": 25.0}, dichroic["transmission_bands"])
        self.assertIn("521/25", dichroic["label"])

    def test_migration_compatibility_legacy_position_keys_are_normalized_in_mechanisms(self) -> None:
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

        excitation_slots = [position["slot"] for position in _runtime_projection(payload)["stages"]["excitation"][0]["positions"]]
        cube_slots = [position["slot"] for position in _runtime_projection(payload)["stages"]["cube"][0]["positions"]]
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

        self.assertEqual([entry["id"] for entry in _runtime_projection(payload)["available_routes"]], ["confocal", "epi"])
        self.assertEqual(_runtime_projection(payload)["default_route"], "confocal")
        self.assertGreaterEqual(len(_runtime_projection(payload)["valid_paths"]), 1)


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

        self.assertEqual(_runtime_projection(payload)["terminals"], [])
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

        source = _runtime_projection(payload)["light_sources"][0]["options"][0]["value"]
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

        source = _runtime_projection(payload)["light_sources"][0]["options"][0]["value"]
        detector = _runtime_projection(payload)["detectors"][0]["options"][0]["value"]
        endpoint = next(row for row in _runtime_projection(payload)["terminals"] if row.get("terminal_id") == "ep_1")

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

        detector = _runtime_projection(payload)["detectors"][0]["options"][0]["value"]
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

    def test_analyzer_stage_role_is_preserved_in_virtual_microscope_stages(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "hal", "kind": "halogen_lamp"}],
                    "optical_path_elements": [
                        {
                            "id": "analyzer_slider",
                            "name": "DIC Fixed Analyzer",
                            "stage_role": "analyzer",
                            "element_type": "slider",
                            "positions": {
                                "Pos_1": {"component_type": "analyzer"},
                            },
                        }
                    ],
                    "endpoints": [{"id": "cam", "endpoint_type": "camera_port"}],
                    "light_paths": [
                        {
                            "id": "dic",
                            "illumination_sequence": [{"source_id": "hal"}],
                            "detection_sequence": [
                                {"optical_path_element_id": "analyzer_slider"},
                                {"endpoint_id": "cam"},
                            ],
                        }
                    ],
                },
            }
        )

        stages = _runtime_projection(payload).get("stages", {})
        self.assertIn("analyzer", stages)
        self.assertEqual(len(stages["analyzer"]), 1)
        self.assertEqual(stages["analyzer"][0]["id"], "analyzer_mech_0")
        self.assertEqual(stages["analyzer"][0]["name"], "DIC Fixed Analyzer")

        valid_paths = _runtime_projection(payload).get("valid_paths", [])
        self.assertTrue(len(valid_paths) > 0)
        self.assertIn("analyzer_mech_0", valid_paths[0])

    def test_render_kind_covers_all_vocabulary_component_types(self) -> None:
        """Every component_type in the vocabulary must produce a recognised render_kind (not 'other')."""
        vocabulary_types = {
            "bandpass", "multiband_bandpass", "longpass", "shortpass",
            "dichroic", "multiband_dichroic", "polychroic", "notch",
            "filter_cube", "analyzer", "empty", "mirror", "block",
            "passthrough", "neutral_density",
        }
        expected_non_other = {
            "bandpass": "band",
            "multiband_bandpass": "band",
            "longpass": "longpass",
            "shortpass": "shortpass",
            "dichroic": "dichroic",
            "multiband_dichroic": "dichroic",
            "polychroic": "dichroic",
            "notch": "band",
            "filter_cube": "band",
            "analyzer": "analyzer",
            "empty": "empty",
            "mirror": "empty",
            "block": "empty",
            "passthrough": "empty",
            "neutral_density": "empty",
        }
        for comp_type in vocabulary_types:
            payload = generate_virtual_microscope_payload(
                {
                    "hardware": {
                        "light_path": {
                            "excitation_mechanisms": [
                                {"positions": {1: {"component_type": comp_type}}}
                            ]
                        }
                    }
                }
            )
            stages = _runtime_projection(payload).get("stages", {})
            positions = stages.get("excitation", [{}])[0].get("options", [])
            if not positions:
                continue
            render_kind = positions[0].get("value", {}).get("render_kind", "other")
            self.assertEqual(
                render_kind,
                expected_non_other.get(comp_type, "other"),
                f"component_type '{comp_type}' should map to render_kind '{expected_non_other.get(comp_type)}' but got '{render_kind}'",
            )

    # ── VM-006: analyzer flagged _unsupported_spectral_model ────────────

    def test_analyzer_component_payload_flagged_unsupported_spectral_model(self) -> None:
        """Analyzer positions should carry _unsupported_spectral_model flag."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "analyzer_slider",
                            "name": "DIC Fixed Analyzer",
                            "stage_role": "analyzer",
                            "element_type": "slider",
                            "positions": {
                                "Pos_1": {"component_type": "analyzer"},
                            },
                        },
                    ],
                    "light_path": {
                        "detection_mechanisms": [{"optical_path_element_id": "analyzer_slider"}],
                    },
                }
            }
        )
        stages = _runtime_projection(payload).get("stages", {})
        self.assertIn("analyzer", stages)
        positions = stages["analyzer"][0].get("options", [])
        self.assertTrue(len(positions) > 0)
        self.assertTrue(
            positions[0]["value"].get("_unsupported_spectral_model"),
            "Analyzer positions should be flagged _unsupported_spectral_model",
        )

    def test_non_analyzer_component_has_no_unsupported_flag(self) -> None:
        """Normal spectral components should not carry _unsupported_spectral_model."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "excitation_mechanisms": [
                            {"positions": {1: {"component_type": "bandpass", "center_nm": 470, "width_nm": 40}}}
                        ]
                    }
                }
            }
        )
        stages = _runtime_projection(payload).get("stages", {})
        positions = stages.get("excitation", [{}])[0].get("options", [])
        self.assertTrue(len(positions) > 0)
        self.assertFalse(
            positions[0]["value"].get("_unsupported_spectral_model", False),
            "Bandpass should not have _unsupported_spectral_model flag",
        )

    # ── VM-006: analyzer in legacy detection sequence ──

    def test_analyzer_included_in_legacy_detection_sequence(self) -> None:
        """Analyzer elements with stage_role=analyzer should appear in detection sequences."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "hal", "kind": "halogen_lamp"}],
                    "optical_path_elements": [
                        {
                            "id": "analyzer_slider",
                            "name": "DIC Fixed Analyzer",
                            "stage_role": "analyzer",
                            "element_type": "slider",
                            "modalities": ["dic"],
                            "positions": {
                                "Pos_1": {"component_type": "analyzer"},
                            },
                        },
                    ],
                    "endpoints": [{"id": "cam", "endpoint_type": "camera_port"}],
                },
            }
        )
        light_paths = payload.get("light_paths", [])
        dic_routes = [r for r in light_paths if r.get("id") == "dic"]
        if dic_routes:
            detection_seq = dic_routes[0].get("detection_sequence", [])
            analyzer_refs = [s for s in detection_seq if s.get("optical_path_element_id") == "analyzer_slider"]
            self.assertTrue(len(analyzer_refs) > 0, "Analyzer should appear in DIC detection sequence")

    # ── VM-010: position_key preserved from YAML ──

    def test_position_key_preserved_in_mechanism_payload(self) -> None:
        """The original YAML position key (e.g. Pos_1) should be preserved as position_key."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "excitation_mechanisms": [
                            {
                                "positions": {
                                    "Pos_1": {"component_type": "bandpass", "center_nm": 470, "width_nm": 40},
                                    "Pos_2": {"component_type": "longpass", "cut_on_nm": 500},
                                }
                            }
                        ]
                    }
                }
            }
        )
        stages = _runtime_projection(payload).get("stages", {})
        positions = stages.get("excitation", [{}])[0].get("options", [])
        self.assertTrue(len(positions) >= 2)
        position_keys = [p["value"].get("position_key") for p in positions]
        self.assertIn("Pos_1", position_keys, "Original position key Pos_1 should be preserved")
        self.assertIn("Pos_2", position_keys, "Original position key Pos_2 should be preserved")

    def test_position_key_preserved_in_cube_mechanism_payload(self) -> None:
        """Cube position keys should also be preserved."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "cube_mechanisms": [
                            {
                                "positions": {
                                    "Pos_1": {
                                        "name": "DAPI",
                                        "component_type": "filter_cube",
                                        "bands": [{"center_nm": 460, "width_nm": 50}],
                                    },
                                }
                            }
                        ]
                    }
                }
            }
        )
        stages = _runtime_projection(payload).get("stages", {})
        cube_positions = stages.get("cube", [{}])[0].get("options", [])
        self.assertTrue(len(cube_positions) > 0)
        position_keys = [p["value"].get("position_key") for p in cube_positions]
        self.assertIn("Pos_1", position_keys, "Original cube position key should be preserved")

    # ── spectral_ops contract tests ──────────────────────────────────────

    def test_bandpass_position_has_spectral_ops(self) -> None:
        """Mechanism positions of type bandpass should carry spectral_ops."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "exc",
                            "stage_role": "excitation",
                            "element_type": "filter_wheel",
                            "positions": {
                                1: {"component_type": "bandpass", "center_nm": 470, "width_nm": 40},
                            },
                        }
                    ],
                }
            }
        )
        stages = _runtime_projection(payload).get("stages", {})
        pos = stages["excitation"][0]["options"][0]["value"]
        self.assertIn("spectral_ops", pos)
        ops = pos["spectral_ops"]
        self.assertIn("illumination", ops)
        self.assertIn("detection", ops)
        self.assertEqual(ops["illumination"][0]["op"], "bandpass")
        self.assertEqual(ops["illumination"][0]["center_nm"], 470.0)
        self.assertEqual(ops["illumination"][0]["width_nm"], 40.0)

    def test_dichroic_position_has_phase_aware_spectral_ops(self) -> None:
        """Dichroic positions must have different ops for illumination and detection."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "di",
                            "stage_role": "dichroic",
                            "element_type": "filter_wheel",
                            "positions": {
                                1: {"component_type": "dichroic", "cut_on_nm": 505},
                            },
                        }
                    ],
                }
            }
        )
        stages = _runtime_projection(payload).get("stages", {})
        pos = stages["dichroic"][0]["options"][0]["value"]
        ops = pos["spectral_ops"]
        self.assertEqual(ops["illumination"][0]["op"], "dichroic_reflect")
        self.assertEqual(ops["detection"][0]["op"], "dichroic_transmit")
        self.assertEqual(ops["illumination"][0]["cut_on_nm"], 505.0)

    def test_filter_cube_position_has_expanded_spectral_ops(self) -> None:
        """Filter cube positions must carry expanded spectral_ops with sub-roles."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "light_path": {
                        "cube_mechanisms": [
                            {
                                "positions": {
                                    1: {
                                        "name": "GFP Cube",
                                        "excitation_filter": {"component_type": "bandpass", "center_nm": 470, "width_nm": 40},
                                        "dichroic": {"component_type": "dichroic", "cut_on_nm": 495},
                                        "emission_filter": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50},
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        )
        cube_options = _runtime_projection(payload)["stages"]["cube"][0]["options"]
        cube = cube_options[0]["value"]
        ops = cube["spectral_ops"]
        # Illumination: excitation_filter + dichroic_reflect
        self.assertTrue(len(ops["illumination"]) >= 2)
        sub_roles = [o.get("sub_role") for o in ops["illumination"]]
        self.assertIn("excitation_filter", sub_roles)
        self.assertIn("dichroic", sub_roles)
        # Detection: dichroic_transmit + emission_filter
        self.assertTrue(len(ops["detection"]) >= 2)
        sub_roles_det = [o.get("sub_role") for o in ops["detection"]]
        self.assertIn("dichroic", sub_roles_det)
        self.assertIn("emission_filter", sub_roles_det)

    def test_analyzer_spectral_ops_are_passthrough_with_unsupported_reason(self) -> None:
        """Analyzer positions should have passthrough ops with an unsupported_reason."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "analyzer_wheel",
                            "stage_role": "analyzer",
                            "element_type": "analyzer",
                            "positions": {
                                1: {"component_type": "analyzer", "name": "Polarizer"},
                            },
                        }
                    ],
                }
            }
        )
        stages = _runtime_projection(payload).get("stages", {})
        pos = stages["analyzer"][0]["options"][0]["value"]
        ops = pos["spectral_ops"]
        self.assertEqual(ops["illumination"][0]["op"], "passthrough")
        self.assertIsNotNone(ops["illumination"][0].get("unsupported_reason"))

    def test_unknown_type_spectral_ops_carry_unsupported_reason(self) -> None:
        """Unknown component types should carry unsupported_reason."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "optical_path_elements": [
                        {
                            "id": "mystery",
                            "stage_role": "excitation",
                            "element_type": "filter_wheel",
                            "positions": {
                                1: {"component_type": "exotic_filter", "name": "Magic"},
                            },
                        }
                    ],
                }
            }
        )
        stages = _runtime_projection(payload).get("stages", {})
        pos = stages["excitation"][0]["options"][0]["value"]
        ops = pos["spectral_ops"]
        self.assertIn("unsupported_reason", ops["illumination"][0])

    # ── route_steps contract tests ────────────────────────────────────────

    def test_route_steps_are_present_in_light_paths(self) -> None:
        """Each light_path route should contain a route_steps array."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser", "wavelength_nm": 488}],
                    "optical_path_elements": [
                        {"id": "exc_filter", "stage_role": "excitation", "element_type": "filter_wheel", "positions": {1: {"component_type": "bandpass", "center_nm": 470, "width_nm": 40}}},
                    ],
                    "endpoints": [{"id": "cam", "endpoint_type": "camera_port"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "name": "Epi-fluorescence",
                        "illumination_sequence": [{"source_id": "src_488"}, {"optical_path_element_id": "exc_filter"}],
                        "detection_sequence": [{"endpoint_id": "cam"}],
                    }
                ],
            }
        )
        route = payload["light_paths"][0]
        self.assertIn("route_steps", route)
        steps = route["route_steps"]
        self.assertIsInstance(steps, list)
        self.assertTrue(len(steps) >= 3, "route_steps should have at least source + sample + detector")

    def test_route_steps_have_ordered_phases(self) -> None:
        """route_steps should be ordered: illumination → sample → detection."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "src", "kind": "laser", "wavelength_nm": 488}],
                    "endpoints": [{"id": "cam", "endpoint_type": "camera_port"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{"source_id": "src"}],
                        "detection_sequence": [{"endpoint_id": "cam"}],
                    }
                ],
            }
        )
        steps = payload["light_paths"][0]["route_steps"]
        phases = [s["phase"] for s in steps]
        # Illumination steps come before sample, which comes before detection
        sample_idx = phases.index("sample")
        self.assertTrue(all(p == "illumination" for p in phases[:sample_idx]))
        self.assertTrue(all(p == "detection" for p in phases[sample_idx + 1:]))

    def test_route_steps_include_metadata_from_inventory(self) -> None:
        """route_steps should carry authored metadata from the hardware inventory."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "src", "kind": "laser", "wavelength_nm": 488, "manufacturer": "Coherent", "model": "OBIS 488"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [{"source_id": "src"}],
                        "detection_sequence": [],
                    }
                ],
            }
        )
        steps = payload["light_paths"][0]["route_steps"]
        source_steps = [s for s in steps if s["kind"] == "source"]
        self.assertTrue(len(source_steps) > 0)
        meta = source_steps[0]["metadata"]
        self.assertEqual(meta["manufacturer"], "Coherent")
        self.assertEqual(meta["model"], "OBIS 488")

    def test_route_steps_preserve_selected_position_metadata_and_spectral_ops(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser", "wavelength_nm": 488}],
                    "optical_path_elements": [
                        {
                            "id": "exc_filter",
                            "stage_role": "excitation",
                            "element_type": "filter_wheel",
                            "positions": {
                                "Pos_1": {"component_type": "bandpass", "center_nm": 470, "width_nm": 40, "label": "BP 470/40"},
                                "Pos_2": {"component_type": "bandpass", "center_nm": 640, "width_nm": 30, "label": "BP 640/30"},
                            },
                        }
                    ],
                    "endpoints": [{"id": "cam", "endpoint_type": "camera_port"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [
                            {"source_id": "src_488"},
                            {"optical_path_element_id": "exc_filter", "position_id": "Pos_2"},
                        ],
                        "detection_sequence": [{"endpoint_id": "cam"}],
                    }
                ],
            }
        )

        route = payload["light_paths"][0]
        exc_step = next(step for step in route["route_steps"] if step.get("component_id") == "exc_filter")
        self.assertEqual(exc_step["position_id"], "Pos_2")
        self.assertEqual(exc_step["position_key"], "Pos_2")
        self.assertEqual(exc_step["position_label"], "BP 640/30")
        self.assertEqual(exc_step["component_type"], "bandpass")
        self.assertEqual(exc_step["spectral_ops"]["illumination"][0]["center_nm"], 640.0)

        selected_execution = route["selected_execution"]
        self.assertEqual(selected_execution["contract_version"], "selected_execution.v2")
        selected_step = next(step for step in selected_execution["selected_route_steps"] if step.get("component_id") == "exc_filter")
        self.assertEqual(selected_step["selection_state"], "resolved")
        self.assertEqual(selected_step["selected_position_id"], "Pos_2")
        self.assertEqual(selected_step["selected_position_key"], "Pos_2")
        self.assertEqual(selected_step["position_id"], "Pos_2")
        self.assertEqual(selected_step["spectral_ops"]["illumination"][0]["center_nm"], 640.0)
        self.assertEqual(selected_step["route_step_id"], exc_step["step_id"])
        self.assertEqual(selected_step["route_id"], "epi")
        self.assertEqual(selected_step["mechanism_id"], "exc_filter")
        self.assertEqual(selected_step["element_id"], "exc_filter")

    def test_selected_execution_marks_unresolved_multi_position_mechanisms(self) -> None:
        """When no position_id is authored in the route, multi-position mechanisms must be unresolved."""
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser", "wavelength_nm": 488}],
                    "optical_path_elements": [
                        {
                            "id": "exc_filter",
                            "stage_role": "excitation",
                            "element_type": "filter_wheel",
                            "positions": {
                                "Pos_1": {"component_type": "bandpass", "center_nm": 470, "width_nm": 40, "label": "BP 470/40"},
                                "Pos_2": {"component_type": "bandpass", "center_nm": 640, "width_nm": 30, "label": "BP 640/30"},
                            },
                        }
                    ],
                    "endpoints": [{"id": "cam", "endpoint_type": "camera_port"}],
                },
                "light_paths": [
                    {
                        "id": "epi",
                        "illumination_sequence": [
                            {"source_id": "src_488"},
                            {"optical_path_element_id": "exc_filter"},  # No position_id!
                        ],
                        "detection_sequence": [{"endpoint_id": "cam"}],
                    }
                ],
            }
        )

        route = payload["light_paths"][0]
        selected_execution = route["selected_execution"]
        self.assertEqual(selected_execution["contract_version"], "selected_execution.v2")
        exc_step = next(
            step for step in selected_execution["selected_route_steps"]
            if step.get("component_id") == "exc_filter"
        )
        self.assertEqual(exc_step["selection_state"], "unresolved")
        self.assertIsNone(exc_step["selected_position_id"])
        self.assertIsNone(exc_step["selected_position_key"])
        self.assertIsNone(exc_step["spectral_ops"])
        self.assertIsInstance(exc_step["available_positions"], list)
        self.assertEqual(len(exc_step["available_positions"]), 2)
        self.assertEqual(exc_step["available_positions"][0]["position_key"], "Pos_1")
        self.assertEqual(exc_step["available_positions"][1]["position_key"], "Pos_2")
        self.assertEqual(exc_step["mechanism_id"], "exc_filter")
        self.assertEqual(exc_step["route_id"], "epi")

        # route_steps topology should still have the defaulted first position
        topology_step = next(step for step in route["route_steps"] if step.get("component_id") == "exc_filter")
        self.assertEqual(topology_step["position_key"], "Pos_1")
        self.assertIsNotNone(topology_step["spectral_ops"])

    def test_route_step_splitter_branches_include_resolved_branch_optics(self) -> None:
        payload = generate_virtual_microscope_payload(
            {
                "hardware": {
                    "sources": [{"id": "src_488", "kind": "laser", "wavelength_nm": 488}],
                    "optical_path_elements": [
                        {"id": "camera_splitter", "name": "Camera Splitter", "stage_role": "splitter", "element_type": "splitter"},
                        {
                            "id": "green_filter",
                            "stage_role": "emission",
                            "element_type": "filter_wheel",
                            "positions": {
                                "1": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50, "label": "525/50"},
                            },
                        },
                        {
                            "id": "red_filter",
                            "stage_role": "emission",
                            "element_type": "filter_wheel",
                            "positions": {
                                "1": {"component_type": "bandpass", "center_nm": 700, "width_nm": 75, "label": "700/75"},
                            },
                        },
                    ],
                    "endpoints": [
                        {"id": "detector_1", "endpoint_type": "detector"},
                        {"id": "detector_2", "endpoint_type": "detector"},
                    ],
                },
                "light_paths": [
                    {
                        "id": "confocal",
                        "illumination_sequence": [{"source_id": "src_488"}],
                        "detection_sequence": [
                            {"optical_path_element_id": "camera_splitter"},
                            {
                                "branches": {
                                    "selection_mode": "exclusive",
                                    "items": [
                                        {
                                            "branch_id": "green",
                                            "mode": "reflected",
                                            "sequence": [
                                                {"optical_path_element_id": "green_filter", "position_id": "1"},
                                                {"endpoint_id": "detector_1"},
                                            ],
                                        },
                                        {
                                            "branch_id": "red",
                                            "mode": "transmitted",
                                            "sequence": [
                                                {"optical_path_element_id": "red_filter", "position_id": "1"},
                                                {"endpoint_id": "detector_2"},
                                            ],
                                        },
                                    ],
                                }
                            },
                        ],
                    }
                ],
            }
        )

        route_steps = payload["light_paths"][0]["route_steps"]
        routing_step = next(step for step in route_steps if step.get("kind") == "routing_component")
        branches = routing_step["routing"]["branches"]
        self.assertEqual(len(branches), 2)

        green_component = next(item for item in branches[0]["sequence"] if item.get("kind") == "optical_component")
        self.assertEqual(green_component["component_id"], "green_filter")
        self.assertEqual(green_component["position_id"], "1")
        self.assertEqual(green_component["position_key"], "1")
        self.assertEqual(green_component["position_label"], "525/50")
        self.assertEqual(green_component["spectral_ops"]["detection"][0]["center_nm"], 525.0)
