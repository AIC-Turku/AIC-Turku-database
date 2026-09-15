"""Temporary adversarial prose probe for the Methods Generator.

This file intentionally fails after rendering a matrix of configurations so the
actual browser-generated text is captured in CI logs for manual audit. Do not
merge this probe.
"""
import copy
import json
import shutil
import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def component(identifier, label, cls, sentence):
    return {
        "id": identifier,
        "display_label": label,
        "inventory_class": cls,
        "method_sentence": sentence,
    }


def audit_scope(identifier="scope-audit", display_name="Audit Scope"):
    s405 = component("s405", "405 nm laser", "light_source", "Excitation used the 405 nm laser.")
    s488 = component("s488", "488 nm laser", "light_source", "Excitation used the 488 nm laser.")
    s561 = component("s561", "561 nm laser", "light_source", "Excitation used the 561 nm laser.")
    cam_a = component("cam-a", "Camera A", "endpoint", "Images were recorded using Camera A.")
    cam_b = component("cam-b", "Camera B", "endpoint", "Images were recorded using Camera B.")
    pmt = component("pmt", "PMT", "endpoint", "Images were recorded using the PMT.")
    hyd = component("hyd", "HyD", "endpoint", "Images were recorded using the HyD detector.")
    gfp = component("gfp-cube", "GFP filter cube", "optical_element", "The GFP filter cube was used.")
    dapi = component("dapi-cube", "DAPI filter cube", "optical_element", "The DAPI filter cube was used.")
    dual = component("dual-view", "Dual-view splitter", "splitter", "The Dual-view splitter was used.")
    conf_split = component("conf-split", "Confocal emission splitter", "splitter", "The confocal emission splitter was used.")

    widefield_facts = {
        "selected_or_selectable_emission_filters": [
            {
                "id": "gfp-cube",
                "display_label": "GFP filter cube",
                "selection_state": "selected",
                "selected_position_key": "GFP",
                "product_code": "49002",
            }
        ]
    }
    confocal_facts = {
        "selected_or_selectable_splitters": [
            {
                "id": "conf-split",
                "display_label": "Confocal emission splitter",
                "selection_state": "selected",
                "selected_position_key": "green",
            }
        ]
    }

    return {
        "id": identifier,
        "display_name": display_name,
        "methods_generation": {"is_blocked": False, "blockers": []},
        "methods": {
            "base_sentence": f"Images were acquired using the {display_name}.",
            "specimen_prep_recommendation": "",
            "acquisition_settings_recommendation": "",
            "quarep_light_path_recommendation_needed": False,
            "quarep_light_path_recommendation": "",
            "environment_sentence": "Live cells were imaged at 37 °C and 5% CO2.",
            "stage_sentences": ["Z-stacks were acquired."],
            "autofocus_sentence": "Hardware autofocus was used.",
            "triggering_sentence": "Hardware triggering was used.",
            "processing_sentences": ["Images were deconvolved after acquisition."],
        },
        "hardware": {
            "objectives": [
                {"id": "obj20", "display_label": "20× dry NA 0.75", "method_sentence": "A 20× dry NA 0.75 objective was used."},
                {"id": "obj40", "display_label": "40× water NA 1.15", "method_sentence": "A 40× water NA 1.15 objective was used."},
                {"id": "obj60", "display_label": "60× oil NA 1.40", "method_sentence": "A 60× oil NA 1.40 objective was used."},
            ],
            "optical_path": {
                "hardware_inventory_renderables": [s405, s488, s561, cam_a, cam_b, pmt, hyd, gfp, dapi, dual, conf_split],
                "authoritative_route_contract": {
                    "routes": [
                        {
                            "id": "widefield",
                            "display_label": "Widefield fluorescence",
                            "route_identity": {"readouts": [{"id": "spectral", "display_label": "Spectral imaging"}]},
                            "relevant_hardware": {
                                "sources": [s405, s488],
                                "filters": [gfp, dapi],
                                "splitters": [dual],
                                "endpoints": [cam_a, cam_b],
                            },
                            "route_optical_facts": widefield_facts,
                        },
                        {
                            "id": "confocal",
                            "display_label": "Point-scanning confocal",
                            "route_identity": {"readouts": [{"id": "flim", "display_label": "FLIM"}]},
                            "relevant_hardware": {
                                "sources": [s488, s561],
                                "filters": [],
                                "splitters": [conf_split],
                                "endpoints": [pmt, hyd],
                            },
                            "route_optical_facts": confocal_facts,
                        },
                    ]
                },
            },
        },
    }


def runtime(**overrides):
    data = {
        "scope_id": "scope-audit",
        "route": "widefield",
        "validSelection": True,
        "sources": [],
        "detectors": [],
        "splitters": [],
        "selected_route_steps": [],
    }
    data.update(overrides)
    return data


class MethodsGenerator48CaseAuditProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        executable = shutil.which("chromium") or shutil.which("chromium-browser")
        cls.browser = cls.playwright.chromium.launch(**({"executable_path": executable} if executable else {}))
        cls.template = Environment(loader=FileSystemLoader(ROOT / "scripts/templates")).get_template("methods_generator.md.j2")
        cls.app_script = (ROOT / "assets/javascripts/methods_generator_app.js").read_text(encoding="utf-8")
        cls.prose_script = (ROOT / "assets/javascripts/methods_generator_prose.js").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def open_methods(self, instrument=None, storage=None, instruments=None):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        insts = instruments or [instrument or audit_scope()]
        html = self.template.render(methods_generator_config_json=json.dumps({
            "instrument_data_url": "/instruments.json",
            "acknowledgements": {"standard": "Facility acknowledgement."},
        }))
        bootstrap = "window.fetch = async () => ({ok: true, json: async () => (" + json.dumps({"instruments": insts}) + ")});"
        if storage is not None:
            bootstrap += "Object.defineProperty(window, 'localStorage', {configurable: true, value: {getItem() {return " + json.dumps(json.dumps(storage)) + ";}}});"
        html = html.replace('<script src="../assets/javascripts/methods_generator_app.js"></script>', "<script>" + self.app_script + "</script>")
        html = html.replace('<script src="../assets/javascripts/methods_generator_prose.js"></script>', "<script>" + self.prose_script + "</script>")
        self.page.set_content("<script>" + bootstrap + "</script>" + html)
        expect(self.page.locator("#system-select")).to_be_enabled()
        self.page.select_option("#system-select", insts[0]["id"])

    def close_methods(self):
        self.context.close()

    def check_value(self, prefix, value):
        self.page.locator(f'input[id^="{prefix}-"][value="{value}"]').check()

    def output_body(self):
        text = self.page.locator("#output-text").input_value()
        text = text.replace("Light Microscopy Methods:\n\n", "", 1)
        text = text.split("\n\nAcknowledgements:\n\n", 1)[0]
        return text.strip()

    def run_single(self, *, instrument=None, storage=None, checks=None, confirmed=None, session=None, confirm_runtime=False):
        self.open_methods(instrument=instrument, storage=storage)
        if session:
            self.page.fill("#session-label", session)
        for prefix, value in checks or []:
            self.check_value(prefix, value)
        for index in confirmed or []:
            self.page.locator(f"#confirmed-{index}").check()
        if confirm_runtime:
            self.page.locator("#runtime-confirm").check()
        self.page.click("#add-btn")
        result = self.output_body()
        self.close_methods()
        return result

    def test_render_48_configurations_for_manual_audit(self):
        outputs = {}
        base = audit_scope()

        cases = [
            ("01_base_only", {}),
            ("02_obj20", {"checks": [("obj", "obj20")]}),
            ("03_obj40", {"checks": [("obj", "obj40")]}),
            ("04_obj60_decimal_na", {"checks": [("obj", "obj60")]}),
            ("05_two_objectives", {"checks": [("obj", "obj20"), ("obj", "obj40")]}),
            ("06_two_objectives_decimal", {"checks": [("obj", "obj40"), ("obj", "obj60")]}),
            ("07_three_objectives", {"checks": [("obj", "obj20"), ("obj", "obj40"), ("obj", "obj60")]}),
            ("08_source_405", {"checks": [("light", "s405")]}),
            ("09_source_488", {"checks": [("light", "s488")]}),
            ("10_two_sources", {"checks": [("light", "s405"), ("light", "s488")]}),
            ("11_detector_a", {"checks": [("det", "cam-a")]}),
            ("12_two_detectors", {"checks": [("det", "cam-a"), ("det", "cam-b")]}),
            ("13_route_widefield", {"checks": [("route", "widefield")]}),
            ("14_route_confocal", {"checks": [("route", "confocal")]}),
            ("15_widefield_obj20", {"checks": [("route", "widefield"), ("obj", "obj20")]}),
            ("16_widefield_full", {"checks": [("route", "widefield"), ("obj", "obj60"), ("light", "s488"), ("det", "cam-a"), ("filter", "gfp-cube")]}),
            ("17_confocal_full", {"checks": [("route", "confocal"), ("obj", "obj60"), ("light", "s488"), ("det", "pmt"), ("splitter", "conf-split")]}),
            ("18_widefield_readout", {"checks": [("route", "widefield"), ("readout-0", "widefield:spectral")]}),
            ("19_confocal_flim", {"checks": [("route", "confocal"), ("readout-1", "confocal:flim")]}),
            ("20_two_routes", {"checks": [("route", "widefield"), ("route", "confocal")]}),
            ("21_environment_confirmed", {"confirmed": [0]}),
            ("22_zstack_confirmed", {"confirmed": [1]}),
            ("23_autofocus_confirmed", {"confirmed": [2]}),
            ("24_all_actions_confirmed", {"confirmed": [0, 1, 2, 3, 4]}),
        ]
        for name, kwargs in cases:
            outputs[name] = self.run_single(**kwargs)

        inst = copy.deepcopy(base)
        inst["methods"]["acquisition_settings_recommendation"] = "[PLEASE SPECIFY: exposure time, pixel size (µm/px), and z-step (µm)]."
        outputs["25_acquisition_prompt"] = self.run_single(instrument=inst)

        inst = copy.deepcopy(base)
        inst["methods"]["specimen_prep_recommendation"] = "[PLEASE SPECIFY: mounting medium and coverslip thickness]."
        outputs["26_specimen_prompt"] = self.run_single(instrument=inst)

        inst = copy.deepcopy(base)
        inst["methods"]["quarep_light_path_recommendation_needed"] = True
        inst["methods"]["quarep_light_path_recommendation"] = "[PLEASE VERIFY: exact emission filter and dichroic used]."
        outputs["27_optical_verify_prompt"] = self.run_single(instrument=inst)

        inst = copy.deepcopy(base)
        inst["methods_generation"] = {
            "is_blocked": True,
            "blockers": [{"kind": "instrument_metadata", "title": "Acquisition software version"}],
        }
        outputs["28_metadata_blocker"] = self.run_single(instrument=inst)

        inst = copy.deepcopy(base)
        inst["methods"]["specimen_prep_recommendation"] = "[PLEASE SPECIFY: mounting medium]."
        inst["methods"]["acquisition_settings_recommendation"] = "[PLEASE SPECIFY: exposure time and pixel size (µm/px)]."
        inst["methods"]["quarep_light_path_recommendation_needed"] = True
        inst["methods"]["quarep_light_path_recommendation"] = "[PLEASE VERIFY: exact detector path]."
        outputs["29_multiple_review_prompts"] = self.run_single(instrument=inst)

        inst = copy.deepcopy(base)
        inst["display_name"] = "Unidentified microscope"
        inst["methods"]["base_sentence"] = "[PLEASE VERIFY: microscope identity is missing from the facility record]."
        outputs["30_missing_identity"] = self.run_single(instrument=inst)

        plan = runtime(sources=[{"display_label": "Plan laser", "selected_wavelength_nm": 488}])
        outputs["31_runtime_unconfirmed"] = self.run_single(storage=plan)
        outputs["32_runtime_source_confirmed"] = self.run_single(storage=plan, confirm_runtime=True)

        plan = runtime(detectors=[{"display_label": "Plan camera", "collection_min_nm": 500, "collection_max_nm": 550}])
        outputs["33_runtime_detector_window"] = self.run_single(storage=plan, confirm_runtime=True)

        plan = runtime(
            sources=[{"display_label": "Plan laser", "selected_wavelength_nm": 488}],
            detectors=[{"display_label": "Plan camera", "collection_min_nm": 500, "collection_max_nm": 550}],
        )
        outputs["34_runtime_source_detector"] = self.run_single(storage=plan, confirm_runtime=True)

        plan = runtime(selected_route_steps=[{
            "kind": "optical_component", "display_label": "GFP filter cube", "position_key": "GFP"
        }])
        outputs["35_runtime_filter_position"] = self.run_single(storage=plan, confirm_runtime=True)

        plan = runtime(splitters=[{"display_label": "Dual-view splitter", "selected_branch_ids": ["left", "right"]}])
        outputs["36_runtime_splitter_branches"] = self.run_single(storage=plan, confirm_runtime=True)

        plan = runtime(selected_route_steps=[{
            "kind": "optical_component", "display_label": "GFP filter cube", "position_key": "GFP"
        }])
        outputs["37_route_fact_product_code"] = self.run_single(storage=plan, confirm_runtime=True)

        inst = copy.deepcopy(base)
        inst["hardware"]["optical_path"]["authoritative_route_contract"]["routes"][0]["route_optical_facts"] = {
            "selected_or_selectable_emission_filters": [{
                "id": "gfp-cube", "display_label": "GFP filter cube", "selection_state": "selected",
                "selected_position_key": "GFP", "product_code": "49002",
                "excitation_filter": {"display_label": "470/40"},
                "dichroic": {"display_label": "495 LP"},
                "emission_filter": {"display_label": "525/50"},
            }]
        }
        outputs["38_route_fact_cube_internals"] = self.run_single(instrument=inst, storage=plan, confirm_runtime=True)

        plan = runtime(acquisition_plan={
            "requiresSequentialAcquisition": True,
            "steps": [
                {"step": 1, "fluorophoreName": "DAPI", "route": "widefield"},
                {"step": 2, "fluorophoreName": "GFP", "route": "widefield"},
            ],
        })
        outputs["39_runtime_sequential"] = self.run_single(storage=plan, confirm_runtime=True)

        plan = runtime(selected_route_steps=[{
            "kind": "optical_component", "display_label": "Legacy GFP cube", "position_key": "GFP", "_cube_incomplete": True
        }])
        outputs["40_runtime_incomplete_optic"] = self.run_single(storage=plan, confirm_runtime=True)

        plan = runtime(selected_route_steps=[{
            "kind": "optical_component", "display_label": "Spectral element", "position_key": "P1",
            "_unsupported_spectral_model": True, "unsupported_reason": "non-standard spectral curve"
        }])
        outputs["41_runtime_unsupported_spectral"] = self.run_single(storage=plan, confirm_runtime=True)

        plan = runtime(
            sources=[{"display_label": "Unknown laser", "selected_wavelength_nm": None}, {"display_label": "Zero laser", "selected_wavelength_nm": 0}],
            detectors=[{"display_label": "Unknown detector", "collection_min_nm": None, "collection_max_nm": None}],
        )
        outputs["42_runtime_unknown_numbers"] = self.run_single(storage=plan, confirm_runtime=True)

        plan = runtime(route="nonexistent-route", sources=[{"display_label": "488 nm laser", "selected_wavelength_nm": 488}])
        outputs["43_runtime_unknown_route"] = self.run_single(storage=plan, confirm_runtime=True)

        plan = runtime(instrument_id="different-scope")
        self.open_methods(storage=plan)
        disabled = self.page.locator("#runtime-confirm").is_disabled()
        self.page.click("#add-btn")
        outputs["44_conflicting_instrument_ids"] = f"confirm_disabled={disabled}; text={self.output_body()}"
        self.close_methods()

        self.open_methods()
        self.page.fill("#session-label", "Acquisition A")
        self.check_value("obj", "obj20")
        self.page.click("#add-btn")
        first = self.output_body()
        self.page.click("#add-btn")
        second = self.output_body()
        outputs["45_double_add_idempotence"] = f"same={first == second}; text={second}"
        self.close_methods()

        self.open_methods()
        self.page.fill("#session-label", "Acquisition A")
        self.check_value("obj", "obj20")
        self.page.click("#add-btn")
        self.page.fill("#session-label", "Acquisition B")
        self.page.locator('input[id^="obj-"]:checked').uncheck()
        self.check_value("obj", "obj60")
        self.page.click("#add-btn")
        outputs["46_two_acquisitions_same_scope"] = self.output_body()
        self.close_methods()

        second_scope = audit_scope("scope-second", "Second Scope")
        self.open_methods(instruments=[base, second_scope])
        self.check_value("light", "s488")
        self.page.select_option("#system-select", "scope-second")
        carry = self.page.locator('input[id^="light-"]:checked').count()
        self.page.click("#add-btn")
        outputs["47_switch_scope_no_carryover"] = f"checked_after_switch={carry}; text={self.output_body()}"
        self.close_methods()

        self.open_methods(instruments=[base, second_scope])
        self.page.fill("#session-label", "Scope A acquisition")
        self.check_value("route", "widefield")
        self.check_value("obj", "obj20")
        self.page.click("#add-btn")
        self.page.select_option("#system-select", "scope-second")
        self.page.fill("#session-label", "Scope B acquisition")
        self.check_value("route", "confocal")
        self.check_value("obj", "obj60")
        self.page.click("#add-btn")
        outputs["48_multi_scope_methods"] = self.output_body()
        self.close_methods()

        self.fail("METHODS_48CASE_AUDIT=" + json.dumps(outputs, ensure_ascii=False, separators=(",", ":")))
