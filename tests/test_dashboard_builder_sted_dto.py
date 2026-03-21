import unittest
from unittest import mock
import json
import os
import sys
import tempfile
import types
from pathlib import Path

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

from scripts.dashboard_builder import (
    build_hardware_dto,
    build_instrument_mega_dto,
    build_llm_inventory_payload,
    build_methods_generator_instrument_export,
    build_methods_generator_page_config,
    build_optical_path_dto,
    json_script_data,
    normalize_hardware,
    normalize_instrument_dto,
    load_instruments,
)
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
                "light_source_kinds": {"source": "inline", "allowed_values": ["laser", "halogen_lamp"]},
                "light_source_roles": {"source": "inline", "allowed_values": ["excitation", "depletion", "transmitted_illumination"]},
                "light_source_timing_modes": {"source": "inline", "allowed_values": ["cw", "pulsed"]},
                "detector_kinds": {"source": "inline", "allowed_values": ["hybrid"]},
                "optical_routes": {"source": "inline", "allowed_values": ["confocal", "epi"]},
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
        self.assertEqual(light["kind_label"], "laser")
        self.assertEqual(light["role_label"], "depletion")
        self.assertEqual(light["timing_mode_label"], "pulsed")

        detector = hardware["detectors"][0]
        self.assertIn("time-gated acquisition", detector["method_sentence"])
        self.assertIn("Supports time gating", "\n".join(detector["spec_lines"]))
        self.assertEqual(detector["kind_label"], "hybrid")

        modulator = hardware["optical_modulators"][0]
        self.assertEqual(modulator["display_label"], "slm")
        self.assertIn("phase mask", modulator["method_sentence"])
        self.assertIn("Supported phase masks", "\n".join(modulator["spec_lines"]))

        logic = hardware["illumination_logic"][0]
        self.assertIn("Adaptive illumination", logic["method_sentence"])
        self.assertIn("Default enabled", "\n".join(logic["spec_lines"]))



    def test_explicit_light_source_role_is_used_instead_of_notes_inference(self) -> None:
        inst = {
            "canonical": {
                "hardware": {
                    "light_sources": [
                        {
                            "kind": "laser",
                            "manufacturer": "Legacy",
                            "model": "Laser",
                            "wavelength_nm": 775,
                            "role": "depletion",
                            "notes": "Legacy free-text should not be used for role parsing",
                        }
                    ]
                }
            }
        }

        hardware = build_hardware_dto(self.vocabulary, inst, lightpath_dto=EMPTY_LIGHTPATH)

        light = hardware["light_sources"][0]
        self.assertEqual(light["role"], "depletion")
        self.assertIn("STED depletion was delivered", light["method_sentence"])


    def test_transmitted_light_role_uses_transmitted_methods_sentence(self) -> None:
        inst = {
            "canonical": {
                "hardware": {
                    "light_sources": [
                        {
                            "kind": "halogen_lamp",
                            "manufacturer": "Leica",
                            "model": "TL lamp",
                            "path": "transmitted",
                            "role": "transmitted_illumination",
                        }
                    ]
                }
            }
        }

        hardware = build_hardware_dto(self.vocabulary, inst, lightpath_dto=EMPTY_LIGHTPATH)

        light = hardware["light_sources"][0]
        self.assertEqual(light["role"], "transmitted_illumination")
        self.assertIn("Transmitted illumination was provided by", light["method_sentence"])

    def test_wavelength_model_placeholder_is_deduplicated_in_label(self) -> None:
        inst = {
            "canonical": {
                "hardware": {
                    "light_sources": [
                        {
                            "kind": "laser",
                            "manufacturer": "Placeholder",
                            "model": "488 nm",
                            "wavelength_nm": 488,
                        }
                    ]
                }
            }
        }

        hardware = build_hardware_dto(self.vocabulary, inst, lightpath_dto=EMPTY_LIGHTPATH)

        light = hardware["light_sources"][0]
        self.assertEqual(light["display_label"], "488 nm laser Placeholder")

    def test_mega_dto_methods_include_all_hardware_sentence_groups(self) -> None:
        inst = {
            "id": "scope-123",
            "display_name": "Test Scope",
            "manufacturer": "Acme",
            "model": "S1",
            "stand_orientation": "inverted",
            "software": [{"role": "acquisition", "name": "ScopeSoft", "version": "1.0"}],
            "modalities": [],
            "modules": [],
            "canonical": {
                "hardware": {
                    "light_sources": [],
                    "detectors": [],
                    "magnification_changers": [{"type": "optovar", "positions": [{"label": "1.5x"}]}],
                    "optical_modulators": [{"type": "slm", "supported_phase_masks": ["vortex"]}],
                    "illumination_logic": [{"method": "rescue_sted", "default_enabled": True}],
                    "stages": [],
                }
            },
        }

        dto = build_instrument_mega_dto(self.vocabulary, inst, EMPTY_LIGHTPATH)

        self.assertIn("magnification_changer_sentences", dto["methods"])
        self.assertIn("optical_modulator_sentences", dto["methods"])
        self.assertIn("illumination_logic_sentences", dto["methods"])
        self.assertIn("quarep_light_path_recommendation", dto["methods"])
        self.assertIn("specimen_preparation_recommendation", dto["methods"])
        self.assertIn("acquisition_settings_recommendation", dto["methods"])
        self.assertIn("nyquist_recommendation", dto["methods"])
        self.assertIn("data_deposition_recommendation", dto["methods"])
        self.assertNotIn("canonical", dto)
        self.assertNotIn("methods_generation", dto)

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

    def test_optical_path_dto_exposes_authoritative_inventory_and_route_views(self) -> None:
        lightpath_dto = {
            "hardware_inventory": [
                {"id": "source:src_488", "display_label": "488 Laser", "display_number": 1, "inventory_class": "light_source", "route_usage_summary": ["epi"]},
                {"id": "optical_path_element:ex_488", "display_label": "EX 488", "display_number": 2, "inventory_class": "optical_element", "route_usage_summary": ["epi"]},
                {"id": "endpoint:cam", "display_label": "Main Camera", "display_number": 3, "inventory_class": "endpoint", "route_usage_summary": ["epi"]},
            ],
            "normalized_endpoints": [{"id": "cam", "display_label": "Main Camera", "endpoint_type": "camera_port"}],
            "light_paths": [
                {
                    "id": "epi",
                    "name": "Epi",
                    "graph_nodes": [
                        {"id": "n1", "component_kind": "source", "hardware_inventory_id": "source:src_488", "label": "488 Laser", "display_number": 1, "column": 0, "lane": 0},
                        {"id": "n2", "component_kind": "optical_path_element", "hardware_inventory_id": "optical_path_element:ex_488", "label": "EX 488", "display_number": 2, "column": 1, "lane": 0},
                        {"id": "n3", "component_kind": "sample", "label": "Objective / Sample Plane", "column": 2, "lane": 0},
                        {"id": "n4", "component_kind": "endpoint", "hardware_inventory_id": "endpoint:cam", "label": "Main Camera", "display_number": 3, "column": 3, "lane": 0, "endpoint_type": "camera_port"},
                    ],
                    "graph_edges": [
                        {"source": "n1", "target": "n2"},
                        {"source": "n2", "target": "n3"},
                        {"source": "n3", "target": "n4"},
                    ],
                }
            ],
            "route_hardware_usage": [
                {"route_id": "epi", "hardware_inventory_ids": ["source:src_488", "optical_path_element:ex_488", "endpoint:cam"], "endpoint_inventory_ids": ["endpoint:cam"]},
            ],
        }

        optical_path = build_optical_path_dto(lightpath_dto)

        self.assertEqual(optical_path["hardware_inventory_renderables"][0]["display_number"], 1)
        self.assertEqual(optical_path["hardware_index_map"]["by_inventory_id"]["source:src_488"], 1)
        self.assertEqual(optical_path["primary_rendering_contract"]["routes"], "light_paths")
        self.assertEqual(len(optical_path["light_paths"]), 1)
        self.assertEqual(optical_path["light_paths"][0]["id"], "epi")
        self.assertEqual(len(optical_path["route_renderables"]), 1)
        self.assertEqual(optical_path["route_renderables"][0]["id"], "epi")
        self.assertEqual(optical_path["route_renderables"][0]["graph_nodes"][0]["display_number"], 1)
        self.assertEqual(optical_path["route_renderables"][0]["graph_nodes"][0]["inventory_display_number"], 1)
        self.assertEqual(
            optical_path["route_renderables"][0]["graph_nodes"][0]["inventory_identity"]["inventory_id"],
            "source:src_488",
        )
        self.assertEqual(
            optical_path["route_renderables"][0]["graph_nodes"][0]["graph_occurrence"]["node_id"],
            "n1",
        )
        self.assertEqual(
            optical_path["route_renderables"][0]["endpoint_summary"]["inventory_ids"],
            ["endpoint:cam"],
        )
        self.assertEqual(
            optical_path["route_renderables"][0]["route_local_hardware_usage"]["inventory_ids"],
            ["source:src_488", "optical_path_element:ex_488", "endpoint:cam"],
        )
        self.assertEqual(optical_path["methods_route_options"], [{
            "id": "epi",
            "label": "Epi",
            "display_label": "Epi",
            "method_sentence": "Excitation was provided by 488 Laser. The optical path included EX 488. Detected or observed light terminated at Main Camera.",
        }])
        self.assertEqual(optical_path["light_paths"][0]["route_method_paragraph"], "Excitation was provided by 488 Laser. The optical path included EX 488. Detected or observed light terminated at Main Camera.")
        self.assertEqual(optical_path["methods_route_views"][0]["route_method_paragraph"], "Excitation was provided by 488 Laser. The optical path included EX 488. Detected or observed light terminated at Main Camera.")
        self.assertEqual(optical_path["methods_route_views"][0]["light_sources"][0]["display_label"], "488 Laser")
        self.assertEqual(optical_path["methods_route_views"][0]["filters"][0]["display_label"], "EX 488")
        self.assertEqual(optical_path["authoritative_route_contract"]["available_routes"][0]["id"], "epi")
        self.assertEqual(
            optical_path["authoritative_route_contract"]["routes"][0]["relevant_hardware"]["sources"][0]["id"],
            "source:src_488",
        )
        self.assertEqual(
            optical_path["authoritative_route_contract"]["routes"][0]["relevant_hardware"]["endpoints"][0]["id"],
            "endpoint:cam",
        )
        self.assertEqual(
            optical_path["authoritative_route_contract"]["routes"][0]["topology"]["graph_nodes"][0]["hardware_inventory_id"],
            "source:src_488",
        )
        self.assertEqual(optical_path["authoritative_route_contract"]["primary_rendering_contract"]["routes"], "light_paths")

    def test_optical_path_dto_keeps_one_graph_per_route_with_stable_deduplicated_inventory(self) -> None:
        lightpath_dto = {
            "hardware_inventory": [
                {"id": "source:src_488", "display_label": "488 Laser", "display_number": 1, "inventory_class": "light_source", "route_usage_summary": ["epi"]},
                {"id": "source:src_561", "display_label": "561 Laser", "display_number": 2, "inventory_class": "light_source", "route_usage_summary": ["confocal"]},
                {"id": "optical_path_element:shared_di", "display_label": "Shared DI", "display_number": 3, "inventory_class": "optical_element", "route_usage_summary": ["epi", "confocal"]},
                {"id": "endpoint:cam_a", "display_label": "Camera A", "display_number": 4, "inventory_class": "endpoint", "route_usage_summary": ["epi"]},
                {"id": "endpoint:pmt_1", "display_label": "PMT 1", "display_number": 5, "inventory_class": "endpoint", "route_usage_summary": ["confocal"]},
            ],
            "normalized_endpoints": [
                {"id": "cam_a", "display_label": "Camera A", "endpoint_type": "camera_port"},
                {"id": "pmt_1", "display_label": "PMT 1", "endpoint_type": "detector"},
            ],
            "light_paths": [
                {
                    "id": "epi",
                    "name": "Epi",
                    "graph_nodes": [
                        {"id": "epi_src", "component_kind": "source", "hardware_inventory_id": "source:src_488", "label": "488 Laser", "inventory_display_number": 1, "column": 0, "lane": 0, "graph_occurrence": {"node_id": "epi_src"}},
                        {"id": "epi_di_i", "component_kind": "optical_path_element", "hardware_inventory_id": "optical_path_element:shared_di", "label": "Shared DI", "inventory_display_number": 3, "column": 1, "lane": 0, "graph_occurrence": {"node_id": "epi_di_i"}},
                        {"id": "epi_sample", "component_kind": "sample", "label": "Sample", "column": 2, "lane": 0},
                        {"id": "epi_di_d", "component_kind": "optical_path_element", "hardware_inventory_id": "optical_path_element:shared_di", "label": "Shared DI", "inventory_display_number": 3, "column": 3, "lane": 0, "graph_occurrence": {"node_id": "epi_di_d"}},
                        {"id": "epi_cam", "component_kind": "endpoint", "hardware_inventory_id": "endpoint:cam_a", "label": "Camera A", "inventory_display_number": 4, "column": 4, "lane": 0},
                    ],
                    "graph_edges": [
                        {"source": "epi_src", "target": "epi_di_i"},
                        {"source": "epi_di_i", "target": "epi_sample"},
                        {"source": "epi_sample", "target": "epi_di_d"},
                        {"source": "epi_di_d", "target": "epi_cam"},
                    ],
                },
                {
                    "id": "confocal",
                    "name": "Confocal",
                    "graph_nodes": [
                        {"id": "conf_src", "component_kind": "source", "hardware_inventory_id": "source:src_561", "label": "561 Laser", "inventory_display_number": 2, "column": 0, "lane": 0},
                        {"id": "conf_di", "component_kind": "optical_path_element", "hardware_inventory_id": "optical_path_element:shared_di", "label": "Shared DI", "inventory_display_number": 3, "column": 1, "lane": 0, "graph_occurrence": {"node_id": "conf_di"}},
                        {"id": "conf_pmt", "component_kind": "endpoint", "hardware_inventory_id": "endpoint:pmt_1", "label": "PMT 1", "inventory_display_number": 5, "column": 2, "lane": 0},
                    ],
                    "graph_edges": [
                        {"source": "conf_src", "target": "conf_di"},
                        {"source": "conf_di", "target": "conf_pmt"},
                    ],
                },
            ],
            "route_hardware_usage": [
                {"route_id": "epi", "hardware_inventory_ids": ["source:src_488", "optical_path_element:shared_di", "endpoint:cam_a"], "endpoint_inventory_ids": ["endpoint:cam_a"]},
                {"route_id": "confocal", "hardware_inventory_ids": ["source:src_561", "optical_path_element:shared_di", "endpoint:pmt_1"], "endpoint_inventory_ids": ["endpoint:pmt_1"]},
            ],
        }

        optical_path = build_optical_path_dto(lightpath_dto)

        self.assertEqual([route["id"] for route in optical_path["light_paths"]], ["epi", "confocal"])
        self.assertEqual([route["id"] for route in optical_path["route_renderables"]], ["epi", "confocal"])
        self.assertTrue(all(route["graph_nodes"] for route in optical_path["light_paths"]))
        self.assertTrue(all(route["graph_edges"] for route in optical_path["light_paths"]))
        self.assertTrue(all(route["graph_nodes"] for route in optical_path["route_renderables"]))
        self.assertTrue(all(route["graph_edges"] for route in optical_path["route_renderables"]))
        self.assertEqual(
            [item["id"] for item in optical_path["hardware_inventory"]],
            ["source:src_488", "source:src_561", "optical_path_element:shared_di", "endpoint:cam_a", "endpoint:pmt_1"],
        )
        self.assertEqual(optical_path["hardware_index_map"]["by_inventory_id"]["optical_path_element:shared_di"], 3)
        repeated_shared_nodes = [
            node
            for route in optical_path["route_renderables"]
            for node in route["graph_nodes"]
            if node.get("hardware_inventory_id") == "optical_path_element:shared_di"
        ]
        self.assertEqual(len(repeated_shared_nodes), 3)
        self.assertEqual({node["inventory_display_number"] for node in repeated_shared_nodes}, {3})
        self.assertEqual({node["inventory_identity"]["inventory_id"] for node in repeated_shared_nodes}, {"optical_path_element:shared_di"})
        self.assertEqual(
            [route["route_hardware_usage"]["hardware_inventory_ids"] for route in optical_path["authoritative_route_contract"]["routes"]],
            [
                ["source:src_488", "optical_path_element:shared_di", "endpoint:cam_a"],
                ["source:src_561", "optical_path_element:shared_di", "endpoint:pmt_1"],
            ],
        )
        self.assertEqual(optical_path["route_renderables"], optical_path["light_paths"])

    def test_normalize_hardware_preserves_tunable_source_and_detector_path_metadata(self) -> None:
        hardware = normalize_hardware(
            {
                "light_sources": [
                    {
                        "kind": "white_light_laser",
                        "manufacturer": "Leica",
                        "model": "WLL",
                        "tunable_min_nm": 440,
                        "tunable_max_nm": 790,
                        "width_nm": 2,
                        "path": "confocal",
                        "role": "excitation",
                        "simultaneous_lines_max": 8,
                    }
                ],
                "detectors": [
                    {
                        "kind": "hyd",
                        "manufacturer": "Leica",
                        "model": "HyD S",
                        "channel_name": "HyD1",
                        "path": "confocal",
                        "qe_peak_pct": 45,
                        "collection_min_nm": 650,
                        "collection_max_nm": 700,
                        "channel_center_nm": 675,
                        "bandwidth_nm": 50,
                    }
                ],
            }
        )

        light = hardware["light_sources"][0]
        self.assertEqual(light["tunable_min_nm"], 440)
        self.assertEqual(light["tunable_max_nm"], 790)
        self.assertEqual(light["width_nm"], 2)
        self.assertEqual(light["path"], "confocal")
        self.assertEqual(light["simultaneous_lines_max"], 8)

        detector = hardware["detectors"][0]
        self.assertEqual(detector["channel_name"], "HyD1")
        self.assertEqual(detector["path"], "confocal")
        self.assertEqual(detector["qe_peak_pct"], 45)
        self.assertEqual(detector["collection_min_nm"], 650)
        self.assertEqual(detector["collection_max_nm"], 700)
        self.assertEqual(detector["channel_center_nm"], 675)
        self.assertEqual(detector["bandwidth_nm"], 50)

    def test_normalize_hardware_preserves_authored_source_id(self) -> None:
        hardware = normalize_hardware(
            {
                "sources": [
                    {
                        "id": "spectra_x_488",
                        "kind": "led",
                        "manufacturer": "Lumencor",
                        "model": "Spectra X",
                        "wavelength_nm": 488,
                    }
                ],
            }
        )

        source = hardware["sources"][0]
        self.assertEqual(source["id"], "spectra_x_488")
        source_alias = hardware["light_sources"][0]
        self.assertEqual(source_alias["id"], "spectra_x_488")


        inst = {
            "canonical": {
                "hardware": {
                    "light_sources": [
                        {
                            "kind": "laser",
                            "manufacturer": "Leica",
                            "model": "488 Laser",
                            "wavelength_nm": 488,
                            "path": "confocal",
                        }
                    ],
                    "detectors": [
                        {
                            "kind": "hybrid",
                            "manufacturer": "Leica",
                            "model": "HyD",
                            "path": "confocal",
                        }
                    ],
                }
            }
        }

        hardware = build_hardware_dto(self.vocabulary, inst, lightpath_dto=EMPTY_LIGHTPATH)

        self.assertIn("**Optical route:** confocal", "\n".join(hardware["light_sources"][0]["spec_lines"]))
        self.assertIn("**Optical route:** confocal", "\n".join(hardware["detectors"][0]["spec_lines"]))

    def test_methods_generator_export_carries_blockers_without_changing_main_dto(self) -> None:
        instrument = {
            "dto": {
                "id": "scope-1",
                "display_name": "Scope 1",
                "hardware": {
                    "optical_path": {
                        "authoritative_route_contract": {
                            "available_routes": [{"id": "epi", "display_label": "Epi"}],
                            "routes": [{"id": "epi", "display_label": "Epi"}],
                        }
                    }
                },
            },
            "methods_generation": {"is_blocked": True, "blockers": [{"path": "software[0].version"}]},
        }

        exported = build_methods_generator_instrument_export(instrument)

        self.assertEqual(exported["id"], "scope-1")
        self.assertIn("methods_generation", exported)
        self.assertTrue(exported["methods_generation"]["is_blocked"])
        self.assertEqual(
            exported["hardware"]["optical_path"]["authoritative_route_contract"]["available_routes"][0]["id"],
            "epi",
        )

    def test_llm_inventory_payload_includes_policy_grounding_metadata(self) -> None:
        payload = build_llm_inventory_payload(
            {"short_name": "Core"},
            [
                {
                    "dto": {"id": "scope-1", "display_name": "Scope 1", "hardware": {"detectors": None}},
                    "canonical": {
                        "policy": {
                            "missing_required": [{"path": "hardware.detectors", "title": "Detectors"}],
                            "missing_conditional": [{"path": "software[].version", "title": "Software version"}],
                            "alias_fallbacks": [{"path": "instrument.display_name", "alias": "instrument.name"}],
                        }
                    },
                }
            ],
        )

        scope = payload["active_microscopes"][0]
        completeness = scope["inventory_completeness"]
        self.assertEqual(completeness["policy_missing_required"][0]["path"], "hardware.detectors")
        self.assertEqual(completeness["policy_missing_conditional"][0]["path"], "software[].version")
        self.assertEqual(completeness["alias_fallbacks"][0]["alias"], "instrument.name")


    def test_llm_inventory_payload_adds_hardware_focus_summary(self) -> None:
        payload = build_llm_inventory_payload(
            {"short_name": "Core"},
            [
                {
                    "dto": {
                        "id": "scope-1",
                        "display_name": "Scope 1",
                        "modalities": [{"display_label": "Confocal"}],
                        "hardware": {
                            "objectives": [{"display_label": "63x Oil", "is_installed": True}],
                            "light_sources": [{"display_label": "488 nm laser"}],
                            "detectors": [{"display_label": "HyD"}],
                            "optical_modulators": [{"display_label": "SLM"}],
                            "illumination_logic": [{"display_label": "Adaptive illumination"}],
                            "optical_path": {
                                "available_routes": [{"label": "Confocal route"}],
                                "authoritative_route_contract": {
                                    "available_routes": [{"id": "confocal", "display_label": "Confocal route"}],
                                    "routes": [
                                        {
                                            "id": "confocal",
                                            "display_label": "Confocal route",
                                            "illumination_mode": "confocal",
                                            "relevant_hardware": {
                                                "sources": [{"id": "source:488", "display_label": "488 nm laser"}],
                                                "filters": [{"id": "optical_path_element:pinhole", "display_label": "Pinhole"}],
                                                "splitters": [],
                                                "endpoints": [{"id": "endpoint:hyd", "display_label": "HyD"}],
                                            },
                                            "endpoint_summary": {"inventory_ids": ["endpoint:hyd"]},
                                            "branch_summary": {"branches": []},
                                            "topology": {"graph_nodes": [], "graph_edges": []},
                                        }
                                    ],
                                },
                            },
                        },
                    },
                    "canonical": {"policy": {}},
                }
            ],
        )

        summary = payload["active_microscopes"][0]["hardware_focus_summary"]
        self.assertEqual(summary["modality_labels"], ["Confocal"])
        self.assertEqual(summary["route_labels"], ["Confocal route"])
        self.assertEqual(summary["light_source_labels"], ["488 nm laser"])
        self.assertEqual(summary["detector_labels"], ["HyD"])
        self.assertIn("adaptive illumination", summary["supporting_feature_labels"])
        self.assertIn("optical modulation", summary["supporting_feature_labels"])
        self.assertEqual(
            payload["active_microscopes"][0]["llm_context"]["authoritative_route_contract"]["routes"][0]["illumination_mode"],
            "confocal",
        )
        self.assertEqual(
            payload["active_microscopes"][0]["llm_context"]["authoritative_route_contract"]["routes"][0]["relevant_hardware"]["filters"][0]["display_label"],
            "Pinhole",
        )

    def test_json_script_data_escapes_script_terminators_and_round_trips(self) -> None:
        payload = {"text": 'Quote "line"\n</script><script>alert(1)</script>'}
        encoded = json_script_data(payload)

        self.assertNotIn("</script>", encoded)
        self.assertEqual(json.loads(encoded), payload)

    def test_methods_generator_page_config_reads_override_file_and_is_render_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / "acknowledgements.yaml").write_text(
                json.dumps({
                    "standard": 'Standard ack with "quotes" and </script>',
                    "xcelligence_addition": "xCELL ack",
                }),
                encoding="utf-8",
            )

            config = build_methods_generator_page_config(
                {
                    "acknowledgements": {"standard": "fallback", "xcelligence_addition": "fallback x"},
                    "methods_generator": {"instrument_data_url": "../assets/custom.json"},
                },
                repo_root,
            )

            template = Path("scripts/templates/methods_generator.md.j2").read_text(encoding="utf-8")
            rendered = template.replace("{{ methods_generator_config_json | safe }}", json_script_data(config))

            self.assertIn("../assets/custom.json", rendered)
            match = rendered.split('<script id="methods-generator-config" type="application/json">', 1)[1].split('</script>', 1)[0].strip()
            parsed = json.loads(match)
            self.assertEqual(parsed["acknowledgements"]["standard"], 'Standard ack with "quotes" and </script>')
            self.assertNotIn("</script>", match)

    def test_plan_template_config_round_trips_with_escaped_facility_strings(self) -> None:
        config = {
            "facility_short_name": 'Core "A" </script>',
            "facility_contact_url": "https://example.org/contact",
            "facility_contact_label": "Contact Core Staff",
            "llm_inventory_asset_url": "assets/llm_inventory.json",
        }
        template = Path("scripts/templates/plan_experiments.md.j2").read_text(encoding="utf-8")
        rendered = template.replace("{{ plan_experiments_config_json | safe }}", json_script_data(config))
        match = rendered.split('<script id="plan-experiments-config" type="application/json">', 1)[1].split('</script>', 1)[0].strip()

        self.assertEqual(json.loads(match), config)
        self.assertNotIn("</script>", match)

    def test_methods_and_plan_templates_reference_authoritative_route_contract(self) -> None:
        methods_template = Path("scripts/templates/methods_generator.md.j2").read_text(encoding="utf-8")
        plan_template = Path("scripts/templates/plan_experiments.md.j2").read_text(encoding="utf-8")

        self.assertIn("authoritative_route_contract", methods_template)
        self.assertIn("llm_context.authoritative_route_contract", plan_template)

    def test_optical_path_dto_marks_missing_explicit_terminals_as_incomplete(self) -> None:
        dto = build_optical_path_dto({"stages": {}, "splitters": [], "terminals": []})

        section = next(item for item in dto["sections"] if item["id"] == "terminals")
        self.assertEqual(section["items"][0]["id"], "no_explicit_terminals")
        self.assertIn("Action needed", section["items"][0]["spec_lines"][0])

    def test_optical_path_static_graph_does_not_fabricate_unspecified_endpoint(self) -> None:
        dto = build_optical_path_dto(
            {
                "stages": {},
                "terminals": [],
                "splitters": [
                    {
                        "name": "Incomplete Splitter",
                        "branches": [{"id": "branch_1", "label": "Branch 1", "target_ids": []}],
                    }
                ],
            }
        )

        node_keys = [node.get("key") for node in dto.get("static_graph", {}).get("nodes", [])]
        edge_labels = [edge.get("label", "") for edge in dto.get("static_graph", {}).get("edges", [])]

        self.assertNotIn("unspecified_endpoint", node_keys)
        self.assertFalse(any("inferred" in label.lower() for label in edge_labels))

    def test_optical_path_dto_preserves_runtime_splitters_for_virtual_microscope(self) -> None:
        lightpath_dto = {
            "stages": {},
            "splitters": [
                {
                    "name": "Camera Splitter",
                    "display_label": "Di: 560 LP | P1: 700/75 | P2: 525/50",
                    "dichroic": {"positions": {1: {"label": "560 LP", "component_type": "dichroic", "cutoffs_nm": [560]}}},
                    "path1": {"positions": {1: {"label": "700/75", "component_type": "bandpass", "center_nm": 700, "width_nm": 75}}},
                    "path2": {"positions": {1: {"label": "525/50", "component_type": "bandpass", "center_nm": 525, "width_nm": 50}}},
                    "branches": [
                        {"id": "red", "label": "Red path", "mode": "transmitted", "component": {"component_type": "bandpass", "center_nm": 700, "width_nm": 75}},
                        {"id": "green", "label": "Green path", "mode": "reflected", "component": {"component_type": "bandpass", "center_nm": 525, "width_nm": 50}},
                    ],
                }
            ],
        }

        dto = build_optical_path_dto(lightpath_dto)

        self.assertIn("runtime_splitters", dto)
        self.assertEqual(len(dto["runtime_splitters"]), 1)
        self.assertEqual(dto["runtime_splitters"][0]["branches"][0]["mode"], "transmitted")
        self.assertEqual(dto["runtime_splitters"][0]["branches"][1]["component"]["center_nm"], 525)
        self.assertEqual(dto["splitters"][0]["display_label"], "Di: 560 LP | P1: 700/75 | P2: 525/50")

    def test_build_instrument_mega_dto_uses_canonical_identity_as_source_of_truth(self) -> None:
        inst = {
            "id": "scope-9",
            "display_name": "Top-level Name",
            "manufacturer": "Top-level Manufacturer",
            "model": "Top-level Model",
            "stand_orientation": "upright",
            "software": [{"role": "acquisition", "name": "TopLevelSW", "version": "1.0"}],
            "modalities": ["confocal"],
            "modules": [{"name": "legacy-module"}],
            "canonical": {
                "instrument": {
                    "manufacturer": "Canonical Manufacturer",
                    "model": "Canonical Model",
                    "stand_orientation": "inverted",
                    "ocular_availability": "yes",
                    "year_of_purchase": "2020",
                    "funding": "Grant",
                    "location": "Room 1",
                },
                "software": [{"role": "acquisition", "name": "CanonicalSW", "version": "2.0"}],
                "modalities": [],
                "modules": [],
                "hardware": {"light_sources": [], "detectors": [], "stages": []},
            },
        }

        dto = build_instrument_mega_dto(self.vocabulary, inst, EMPTY_LIGHTPATH)

        self.assertEqual(dto["identity"]["manufacturer"], "Canonical Manufacturer")
        self.assertEqual(dto["identity"]["model"], "Canonical Model")
        self.assertIn("Canonical Manufacturer Canonical Model", dto["methods"]["base_sentence"])
        self.assertNotIn("Top-level Manufacturer", dto["methods"]["base_sentence"])

    def test_normalize_instrument_dto_marks_top_level_objectives_compatibility_in_provenance(self) -> None:
        payload = {
            "instrument": {"instrument_id": "scope-legacy", "display_name": "Legacy Scope"},
            "objectives": [{"manufacturer": "Nikon", "model": "CFI", "magnification": 60}],
            "hardware": {},
        }

        with mock.patch("scripts.dashboard_builder.build_instrument_completeness_report") as report_builder:
            report_builder.return_value = mock.Mock(sections=[], missing_required=[], missing_conditional=[], alias_fallbacks=[])
            normalized = normalize_instrument_dto(payload, Path("instruments/scope-legacy.yaml"), retired=False)

        self.assertTrue(
            normalized["canonical"]["provenance"]["deprecated_compatibility"]["top_level_objectives_to_hardware_objectives"]
        )

    def test_load_instruments_respects_validated_handoff_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            instruments_dir = root / "instruments"
            instruments_dir.mkdir(parents=True, exist_ok=True)
            (instruments_dir / "valid.yaml").write_text(
                json.dumps({"instrument": {"instrument_id": "valid-scope", "display_name": "Valid"}, "hardware": {}}),
                encoding="utf-8",
            )
            (instruments_dir / "invalid.yaml").write_text(
                json.dumps({"instrument": {"instrument_id": "invalid-scope", "display_name": "Invalid"}, "hardware": {}}),
                encoding="utf-8",
            )

            prev = Path.cwd()
            try:
                os.chdir(root)
                with mock.patch("scripts.dashboard_builder.build_instrument_completeness_report") as report_builder:
                    report_builder.return_value = mock.Mock(sections=[], missing_required=[], missing_conditional=[], alias_fallbacks=[])
                    instruments = load_instruments(
                        "instruments",
                        allowed_instrument_ids={"valid-scope"},
                    )
            finally:
                os.chdir(prev)

        self.assertEqual([inst["id"] for inst in instruments], ["valid-scope"])

    def test_build_light_source_dto_does_not_infer_role_when_missing(self) -> None:
        inst = {
            "canonical": {
                "hardware": {
                    "light_sources": [
                        {
                            "kind": "laser",
                            "manufacturer": "NoRole",
                            "model": "X",
                            "wavelength_nm": 488,
                        }
                    ]
                }
            }
        }

        hardware = build_hardware_dto(self.vocabulary, inst, lightpath_dto=EMPTY_LIGHTPATH)
        light = hardware["light_sources"][0]
        self.assertEqual(light["role"], "")
        self.assertEqual(light["method_sentence"], "Light source in use: 488 nm laser NoRole X.")

    def test_build_light_source_dto_does_not_infer_timing_mode_from_notes(self) -> None:
        inst = {
            "canonical": {
                "hardware": {
                    "light_sources": [
                        {
                            "kind": "laser",
                            "manufacturer": "Legacy",
                            "model": "TextOnly",
                            "role": "depletion",
                            "notes": "pulsed mode in notes only",
                        }
                    ]
                }
            }
        }

        hardware = build_hardware_dto(self.vocabulary, inst, lightpath_dto=EMPTY_LIGHTPATH)
        light = hardware["light_sources"][0]
        self.assertEqual(light.get("timing_mode", ""), "")
        self.assertNotIn("pulsed", light["method_sentence"].lower())

    def test_build_instrument_mega_dto_uses_module_vocab_labels(self) -> None:
        inst = {
            "id": "scope-modules",
            "display_name": "Scope Modules",
            "canonical": {
                "instrument": {
                    "manufacturer": "Maker",
                    "model": "Model",
                    "stand_orientation": "inverted",
                    "ocular_availability": "yes",
                },
                "software": [{"role": "acquisition", "name": "Acquire", "version": "1.0"}],
                "modalities": [],
                "modules": [{"name": "hardware_autofocus", "manufacturer": "Nikon", "model": "PFS"}],
                "hardware": {},
            },
        }

        with mock.patch("scripts.dashboard_builder._vocab_display", return_value="Hardware Autofocus"):
            dto = build_instrument_mega_dto(self.vocabulary, inst, EMPTY_LIGHTPATH)

        self.assertEqual(dto["modules"][0]["display_label"], "Hardware Autofocus")

    def test_scanner_subtitle_does_not_duplicate_notes(self) -> None:
        inst = {
            "canonical": {
                "hardware": {
                    "scanner": {
                        "type": "galvo",
                        "notes": "Scanner notes only",
                    }
                }
            }
        }

        hardware = build_hardware_dto(self.vocabulary, inst, lightpath_dto=EMPTY_LIGHTPATH)
        scanner = hardware["scanner"]
        self.assertEqual(scanner["display_subtitle"], "")
        self.assertIn("**Notes:** Scanner notes only", scanner["spec_lines"])

    def test_normalize_instrument_dto_preserves_module_manufacturer_and_model(self) -> None:
        payload = {
            "instrument": {"instrument_id": "scope-1", "display_name": "Scope 1"},
            "modules": [{"name": "confocal", "manufacturer": "Leica", "model": "TCS", "notes": "n", "url": "u"}],
            "hardware": {},
        }

        with mock.patch("scripts.dashboard_builder.build_instrument_completeness_report") as report_builder:
            report_builder.return_value = mock.Mock(sections=[], missing_required=[], missing_conditional=[], alias_fallbacks=[])
            normalized = normalize_instrument_dto(payload, Path("instruments/scope-1.yaml"), retired=False)

        self.assertIsNotNone(normalized)
        self.assertEqual(normalized["modules"][0]["manufacturer"], "Leica")
        self.assertEqual(normalized["modules"][0]["model"], "TCS")

    def test_normalize_instrument_dto_migrates_legacy_top_level_objectives_to_hardware(self) -> None:
        payload = {
            "instrument": {"instrument_id": "scope-2", "display_name": "Scope 2"},
            "objectives": [{"manufacturer": "Nikon", "model": "CFI", "magnification": 60}],
            "hardware": {},
        }

        with mock.patch("scripts.dashboard_builder.build_instrument_completeness_report") as report_builder:
            report_builder.return_value = mock.Mock(sections=[], missing_required=[], missing_conditional=[], alias_fallbacks=[])
            normalized = normalize_instrument_dto(payload, Path("instruments/scope-2.yaml"), retired=False)

        self.assertIsNotNone(normalized)
        objectives = normalized["canonical"]["hardware"].get("objectives")
        self.assertIsInstance(objectives, list)
        self.assertEqual(objectives[0]["manufacturer"], "Nikon")

    def test_objective_uses_name_as_display_label_without_overwriting_model(self) -> None:
        inst = {
            "canonical": {
                "hardware": {
                    "objectives": [
                        {
                            "id": "obj1",
                            "name": "Oil Objective Slot A",
                            "manufacturer": "Nikon",
                            "model": "Plan Apo 60x/1.4 Oil",
                            "magnification": 60,
                            "numerical_aperture": 1.4,
                            "immersion": "oil",
                            "correction": "plan_apo",
                        }
                    ]
                }
            }
        }

        hardware = build_hardware_dto(self.vocabulary, inst, lightpath_dto=EMPTY_LIGHTPATH)
        objective = hardware["objectives"][0]
        self.assertEqual(objective["display_label"], "Oil Objective Slot A 60x/1.4 OIL")
        self.assertIn("**Model:** Plan Apo 60x/1.4 Oil", objective["spec_lines"])

    def test_product_code_is_not_inferred_for_detector_or_light_source(self) -> None:
        inst = {
            "canonical": {
                "hardware": {
                    "light_sources": [
                        {
                            "kind": "laser",
                            "manufacturer": "Vendor",
                            "model": "488 nm Laser Family",
                            "name": "Blue excitation",
                            "wavelength_nm": 488,
                        }
                    ],
                    "detectors": [
                        {
                            "kind": "hybrid",
                            "manufacturer": "Vendor",
                            "model": "Detector Model",
                            "name": "Channel A",
                        }
                    ],
                }
            }
        }

        hardware = build_hardware_dto(self.vocabulary, inst, lightpath_dto=EMPTY_LIGHTPATH)
        light = hardware["light_sources"][0]
        detector = hardware["detectors"][0]
        self.assertNotIn("Product code", "\n".join(light["spec_lines"]))
        self.assertNotIn("Product code", "\n".join(detector["spec_lines"]))
        self.assertIsNone(light.get("product_code"))
        self.assertIsNone(detector.get("product_code"))

    def test_build_hardware_dto_exposes_unified_normalized_endpoint_inventory(self) -> None:
        inst = {
            "canonical": {
                "hardware": {
                    "detectors": [{"id": "detector_1", "kind": "hybrid", "model": "HyD"}],
                    "eyepieces": [{"id": "eyepieces", "name": "Eyepieces"}],
                }
            }
        }
        lightpath_dto = {
            "endpoints": [
                {"id": "detector_1", "endpoint_type": "detector", "source_section": "detectors", "display_label": "HyD"},
                {"id": "eyepieces", "endpoint_type": "eyepiece", "source_section": "eyepieces", "display_label": "Eyepieces"},
            ],
            "filters": [],
            "splitters": [],
            "sections": [],
            "renderables": [],
        }

        hardware = build_hardware_dto(self.vocabulary, inst, lightpath_dto=lightpath_dto)

        self.assertEqual([row["id"] for row in hardware["endpoints"]], ["detector_1", "eyepieces"])
        self.assertIn("Source section", "\n".join(hardware["endpoints"][0]["spec_lines"]))


if __name__ == "__main__":
    unittest.main()
