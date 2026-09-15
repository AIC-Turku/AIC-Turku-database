"""Regressions for the grounding failures found in the Methods Generator audit.

Each test pins one claim the generator used to make without evidence. They run
against the real page and the real application script in a browser DOM, or against
the real export functions, so a fixture cannot drift away from what production does.
"""
import json
import shutil
import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import expect, sync_playwright

from scripts.dashboard.instrument_view import build_instrument_mega_dto
from scripts.dashboard.methods_export import (
    _has_explicit_route_fact_selection,
    build_methods_generator_instrument_export,
)
from scripts.dashboard.optical_path_view import build_optical_path_view_dto
from scripts.validate import Vocabulary

ROOT = Path(__file__).resolve().parents[1]

# Wording that describes how the generator works rather than how the images were
# made. None of it may reach the textarea the user copies into a manuscript.
INTERNAL_WORDING = [
    "runtime-selected",
    "browser fallback",
    "exported DTO",
    "wheel/turret",
    "Route-specific optical",
    "as an explicit selector",
    "missing (ask staff)",
    "caveats:",
    "Detected or observed light terminated at",
    "halogen_lamp",
    "white_light_laser",
    "selectable positions",
]


def _vocabulary() -> Vocabulary:
    return Vocabulary(ROOT / "vocab")


def _lightpath(sources):
    return {
        "light_paths": [],
        "hardware_inventory": sources,
        "route_hardware_usage": [],
        "normalized_endpoints": [],
    }


class LightSourceRoleGrounding(unittest.TestCase):
    """A source's recorded role decides what the draft says it did."""

    def _sentence_for(self, source_metadata, **overrides):
        item = {
            "id": "source:probe",
            "inventory_class": "light_source",
            "display_label": "raw label",
            "manufacturer": "Acme",
            "model": "L1",
            "source_metadata": source_metadata,
        }
        item.update(overrides)
        dto = build_optical_path_view_dto(_lightpath([item]), vocabulary=_vocabulary())
        return dto["hardware_inventory_renderables"][0]

    def test_depletion_source_is_never_described_as_excitation(self):
        card = self._sentence_for({"kind": "laser", "wavelength_nm": 775, "role": "depletion"})
        self.assertIn("Stimulated-emission depletion", card["method_sentence"])
        self.assertNotIn("Excitation", card["method_sentence"])

    def test_transmitted_illumination_is_never_described_as_excitation(self):
        card = self._sentence_for({"kind": "halogen_lamp", "role": "transmitted_illumination"})
        self.assertIn("Transmitted-light illumination", card["method_sentence"])
        self.assertNotIn("Excitation", card["method_sentence"])

    def test_excitation_source_is_described_as_excitation(self):
        card = self._sentence_for({"kind": "laser", "wavelength_nm": 488, "role": "excitation"})
        self.assertIn("Excitation was provided by 488 nm laser", card["method_sentence"])

    def test_unrecorded_role_states_nothing_about_function_and_asks(self):
        card = self._sentence_for({"kind": "laser", "wavelength_nm": 488})
        self.assertIn("Illumination was provided by", card["method_sentence"])
        self.assertNotIn("Excitation", card["method_sentence"])
        self.assertEqual(len(card["review_prompts"]), 1)
        self.assertIn("[PLEASE SPECIFY: the role of", card["review_prompts"][0])

    def test_vocabulary_ids_and_placeholder_identities_stay_out_of_prose(self):
        card = self._sentence_for(
            {"kind": "halogen_lamp", "role": "transmitted_illumination"},
            manufacturer="Unknown",
            model="Lamp",
        )
        self.assertNotIn("halogen_lamp", card["method_sentence"])
        self.assertIn("halogen lamp", card["method_sentence"])
        self.assertNotIn("Unknown", card["method_sentence"])


class RouteFactGrounding(unittest.TestCase):
    """Being on a route is not evidence that a component was used."""

    def test_route_membership_of_a_source_is_not_an_acquisition_claim(self):
        # `selected_execution._derive_selection_state` returns "fixed" for every
        # source and endpoint on a route, meaning "has no selectable position".
        row = {"display_label": "405 nm diode", "selection_state": "fixed"}
        self.assertFalse(_has_explicit_route_fact_selection(row, "selected_or_selectable_sources"))
        self.assertFalse(_has_explicit_route_fact_selection(row, "selected_or_selectable_endpoints"))

    def test_an_element_that_still_offers_alternatives_is_never_evidence(self):
        row = {
            "display_label": "Port selector",
            "selection_state": "fixed",
            "available_positions": [{"display_label": "Left"}, {"display_label": "Right"}],
        }
        self.assertFalse(_has_explicit_route_fact_selection(row, "selected_or_selectable_branch_selectors"))

    def test_an_explicitly_selected_position_is_evidence(self):
        row = {"display_label": "GFP cube", "selection_state": "resolved", "selected_position_key": "3"}
        self.assertTrue(_has_explicit_route_fact_selection(row, "selected_or_selectable_emission_filters"))

    def test_surviving_facts_never_carry_unused_alternatives(self):
        facts = {
            "selected_or_selectable_emission_filters": [
                {
                    "display_label": "GFP cube",
                    "selection_state": "resolved",
                    "selected_position_key": "3",
                    "available_positions": [{"display_label": "DAPI"}],
                }
            ]
        }
        exported = build_methods_generator_instrument_export({
            "id": "scope-x",
            "display_name": "Scope X",
            "dto": {
                "id": "scope-x",
                "display_name": "Scope X",
                "methods": {},
                "hardware": {"optical_path": {"authoritative_route_contract": {"routes": [
                    {"id": "r", "display_label": "R", "route_optical_facts": facts}
                ]}}},
            },
        })
        rows = (exported["hardware"]["optical_path"]["authoritative_route_contract"]
                ["routes"][0]["route_optical_facts"]["selected_or_selectable_emission_filters"])
        self.assertEqual(rows, [])

    def test_quarep_prompt_names_the_unresolved_selectors_rather_than_firing_always(self):
        lightpath = {
            "light_paths": [
                {
                    "id": "epi",
                    "name": "Epifluorescence",
                    "selected_execution": {"selected_route_steps": [
                        {"kind": "optical_component", "display_label": "Filter turret",
                         "selection_state": "unresolved"},
                        {"kind": "optical_component", "display_label": "Fixed dichroic",
                         "selection_state": "fixed"},
                    ]},
                }
            ],
            "hardware_inventory": [],
            "route_hardware_usage": [],
            "normalized_endpoints": [],
        }
        inst = {"id": "s", "display_name": "S", "canonical": {
            "instrument": {"manufacturer": "A", "model": "B"}, "software": [],
            "modalities": [], "modules": [], "hardware": {}}}
        methods = build_instrument_mega_dto(_vocabulary(), inst, lightpath)["methods"]
        self.assertTrue(methods["quarep_light_path_recommendation_needed"])
        self.assertIn("Filter turret", methods["quarep_light_path_recommendation"])
        self.assertNotIn("Fixed dichroic", methods["quarep_light_path_recommendation"])

    def test_fully_resolved_route_optics_need_no_prompt(self):
        lightpath = {
            "light_paths": [
                {
                    "id": "epi",
                    "name": "Epifluorescence",
                    "selected_execution": {"selected_route_steps": [
                        {"kind": "optical_component", "display_label": "Fixed dichroic",
                         "selection_state": "fixed"},
                    ]},
                }
            ],
            "hardware_inventory": [],
            "route_hardware_usage": [],
            "normalized_endpoints": [],
        }
        inst = {"id": "s", "display_name": "S", "canonical": {
            "instrument": {"manufacturer": "A", "model": "B"}, "software": [],
            "modalities": [], "modules": [], "hardware": {}}}
        methods = build_instrument_mega_dto(_vocabulary(), inst, lightpath)["methods"]
        self.assertFalse(methods["quarep_light_path_recommendation_needed"])


class CapabilityIsNotUse(unittest.TestCase):
    def test_supported_phase_masks_are_requested_not_asserted(self):
        from scripts.dashboard.instrument_view import build_optical_modulator_dto

        dto = build_optical_modulator_dto(_vocabulary(), {
            "type": "slm", "manufacturer": "Abberior", "model": "easy3D SLM",
            "supported_phase_masks": ["vortex", "bottle", "3d_sted"],
        })
        self.assertNotIn("using Vortex, Bottle", dto["method_sentence"])
        # The request belongs in the review block like every other one, not inside
        # the finished sentence.
        self.assertNotIn("PLEASE SPECIFY", dto["method_sentence"])
        self.assertTrue(any("which phase mask profile was applied" in prompt
                            for prompt in dto["review_prompts"]))

    def test_no_method_sentence_interpolates_an_availability_field(self):
        """A `supported_*`/`available_*` list records capability, never use."""
        source = (ROOT / "scripts/dashboard/instrument_view.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if "method_sentence" not in line or "f\"" not in line:
                continue
            for banned in ("supported_", "available_", "compatible_"):
                self.assertNotIn(banned, line, msg=f"availability interpolated into prose: {line.strip()}")


def _instrument(**overrides):
    source = {"id": "laser", "display_label": "488 nm laser", "inventory_class": "light_source",
              "publication_label": "488 nm laser", "publication_template": "Excitation was provided by {label}.",
              "source_metadata": {"kind": "laser", "wavelength_nm": 488},
              "method_sentence": "Excitation was provided by 488 nm laser."}
    tunable = {"id": "wll", "display_label": "White light laser", "inventory_class": "light_source",
               "publication_label": "white light laser", "publication_template": "Excitation was provided by {label}.",
               "source_metadata": {"kind": "white_light_laser", "tunable_min_nm": 440, "tunable_max_nm": 790},
               "method_sentence": "Excitation was provided by white light laser."}
    lower_only = {"id": "lower_only_det", "display_label": "Lower-bound detector", "inventory_class": "endpoint",
                  "publication_label": "Lower-bound detector",
                  "publication_template": "Images were recorded using {label}.",
                  "endpoint_metadata": {"endpoint_type": "detector", "collection_min_nm": 400},
                  "method_sentence": "Images were recorded using Lower-bound detector."}
    upper_only = {"id": "upper_only_det", "display_label": "Upper-bound detector", "inventory_class": "endpoint",
                  "publication_label": "Upper-bound detector",
                  "publication_template": "Images were recorded using {label}.",
                  "endpoint_metadata": {"endpoint_type": "detector", "collection_max_nm": 700},
                  "method_sentence": "Images were recorded using Upper-bound detector."}
    spectral = {"id": "spectral_det", "display_label": "Spectral detector", "inventory_class": "endpoint",
                "publication_label": "Spectral detector",
                "publication_template": "Images were recorded using {label}.",
                "endpoint_metadata": {"endpoint_type": "detector",
                                      "collection_min_nm": 400, "collection_max_nm": 700},
                "method_sentence": "Images were recorded using Spectral detector."}
    camera_a = {"id": "cam_a", "display_label": "Acme Cam", "inventory_class": "endpoint",
                "publication_label": "Acme Cam", "publication_template": "Images were recorded using {label}.",
                "method_sentence": "Images were recorded using Acme Cam."}
    camera_b = {**camera_a, "id": "cam_b"}
    turret = {"id": "turret", "display_label": "Filter Turret", "inventory_class": "optical_element",
              "publication_label": "Filter Turret", "publication_template": "The light path included {label}.",
              "method_sentence": "The light path included Filter Turret.",
              "selectable_positions": [
                  {"id": "Pos_1", "display_label": "GFP cube", "product_code": "49002", "incomplete": False},
                  {"id": "Pos_2", "display_label": "DAPI cube", "product_code": "49000", "incomplete": True},
              ]}
    instrument = {
        "id": "scope-reg", "display_name": "Regression Scope",
        "methods_generation": {"is_blocked": False, "blockers": []},
        "methods": {"base_sentence": "Images were acquired using the Regression Scope."},
        "hardware": {"objectives": [], "optical_path": {
            "hardware_inventory_renderables": [source, camera_a, camera_b, turret, tunable, spectral,
                                               lower_only, upper_only],
            "authoritative_route_contract": {"routes": [
                {"id": "epi", "display_label": "Epifluorescence",
                 "relevant_hardware": {"sources": [source, tunable],
                                       "endpoints": [camera_a, camera_b, spectral, lower_only, upper_only],
                                       "filters": [turret]}},
            ]}}},
    }
    instrument.update(overrides)
    return instrument


class BrowserGroundingRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        executable = shutil.which("chromium") or shutil.which("chromium-browser")
        cls.browser = cls.playwright.chromium.launch(**({"executable_path": executable} if executable else {}))
        cls.template = Environment(loader=FileSystemLoader(ROOT / "scripts/templates")).get_template("methods_generator.md.j2")
        cls.app = (ROOT / "assets/javascripts/methods_generator_app.js").read_text()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def open_methods(self, instrument=None, storage=None):
        instrument = instrument or _instrument()
        html = self.template.render(methods_generator_config_json=json.dumps({
            "instrument_data_url": "/instruments.json", "acknowledgements": {"standard": ""}}))
        bootstrap = ("window.fetch = async () => ({ok: true, json: async () => ("
                     + json.dumps({"instruments": [instrument]}) + ")});")
        if storage is not None:
            bootstrap += ("Object.defineProperty(window, 'localStorage', {configurable: true, value: {getItem() {return "
                          + json.dumps(json.dumps(storage)) + ";}}});")
        html = html.replace('<script src="../assets/javascripts/methods_generator_app.js"></script>',
                            "<script>" + self.app + "</script>")
        self.page.set_content("<script>" + bootstrap + "</script>" + html)
        expect(self.page.locator("#system-select")).to_be_enabled()
        self.page.select_option("#system-select", instrument["id"])
        return instrument

    def output(self):
        return self.page.locator("#output-text").input_value()

    def test_draft_never_contains_implementation_wording(self):
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "sources": [{"display_label": "488 nm laser", "selected_wavelength_nm": 488}],
            "selected_route_steps": [{"kind": "optical_component", "display_label": "Wheel", "position_key": "3"}],
            "detectors": [{"display_label": "Acme Cam", "collection_min_nm": 500, "collection_max_nm": 550}],
            "acquisition_plan": {"requiresSequentialAcquisition": True,
                                 "steps": [{"step": 1, "fluorophoreName": "EGFP"},
                                           {"step": 2, "fluorophoreName": "mCherry"}]},
        })
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        for wording in INTERNAL_WORDING:
            self.assertNotIn(wording, self.output())

    def _prose(self):
        """The finished prose only: everything a reader takes as stated fact."""
        blocks = []
        for block in self.output().split("\n\n"):
            if block.startswith(("Review before publication:", "Acknowledgements:", "Light Microscopy Methods:")):
                continue
            blocks.append(block)
        return "\n\n".join(blocks)

    def test_plan_component_absent_from_the_record_is_flagged_and_never_asserted(self):
        # A warning next to a sentence does not undo the sentence: a reader takes
        # the prose. An unresolved component must produce the question ONLY.
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "sources": [{"display_label": "Decommissioned 594 nm laser", "selected_wavelength_nm": 594}],
            "detectors": [{"display_label": "Sold EMCCD", "collection_min_nm": 500, "collection_max_nm": 600}],
            "splitters": [{"display_label": "Removed Optosplit", "selected_branch_ids": ["a", "b"]}],
            "selected_route_steps": [{"kind": "optical_component", "display_label": "Scrapped cube",
                                      "position_key": "3"}],
        })
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        prose = self._prose()
        for absent in ["Decommissioned 594 nm laser", "Sold EMCCD", "Removed Optosplit", "Scrapped cube"]:
            self.assertNotIn(absent, prose, msg=f"unsupported component asserted in prose: {absent}")
            self.assertIn(absent, self.output(), msg=f"unsupported component not flagged: {absent}")
        self.assertEqual(self.output().count("which is not in the current instrument record"), 4)

    def test_a_window_below_a_recorded_minimum_is_not_reported(self):
        # The schema makes each bound independently optional, so a detector may
        # record only a minimum. That bound still constrains the window.
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "detectors": [{"id": "lower_only_det", "display_label": "Lower-bound detector",
                           "collection_min_nm": 300, "collection_max_nm": 550}]})
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        prose = self._prose()
        self.assertIn("Images were recorded using Lower-bound detector.", prose)
        self.assertNotIn("300", prose)
        self.assertIn("below its recorded collection minimum of 400 nm", self.output())

    def test_a_window_above_a_recorded_maximum_is_not_reported(self):
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "detectors": [{"id": "upper_only_det", "display_label": "Upper-bound detector",
                           "collection_min_nm": 500, "collection_max_nm": 900}]})
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        prose = self._prose()
        self.assertIn("Images were recorded using Upper-bound detector.", prose)
        self.assertNotIn("900", prose)
        self.assertIn("above its recorded collection maximum of 700 nm", self.output())

    def test_a_window_respecting_a_single_recorded_bound_is_reported(self):
        # The guard must not refuse a window the one recorded bound allows.
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "detectors": [{"id": "lower_only_det", "display_label": "Lower-bound detector",
                           "collection_min_nm": 500, "collection_max_nm": 900}]})
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        self.assertIn("Lower-bound detector (detection 500–900 nm)", self._prose())
        self.assertNotIn("recorded collection", self.output())

    def test_a_position_key_and_label_naming_different_positions_is_review_only(self):
        # A stale plan can carry a key and a label that disagree. The key decides,
        # and a label that contradicts it means the position is not established.
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "selected_route_steps": [{"kind": "optical_component", "component_id": "turret",
                                      "display_label": "Filter Turret",
                                      "position_key": "Pos_2", "position_label": "GFP cube"}]})
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        prose = self._prose()
        self.assertIn("The light path included Filter Turret.", prose)
        self.assertNotIn("GFP cube", prose)
        self.assertNotIn("DAPI cube", prose)
        self.assertIn("do not describe the same recorded position", self.output())

    def test_a_position_key_and_agreeing_label_resolve_normally(self):
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "selected_route_steps": [{"kind": "optical_component", "component_id": "turret",
                                      "display_label": "Filter Turret",
                                      "position_key": "Pos_1", "position_label": "GFP cube"}]})
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        self.assertIn("GFP cube (catalogue no. 49002) in the Filter Turret", self._prose())
        self.assertNotIn("do not describe the same recorded position", self.output())

    def test_a_depletion_source_is_not_asked_for_its_excitation_wavelength(self):
        instrument = _instrument()
        instrument["hardware"]["optical_path"]["hardware_inventory_renderables"].append(
            {"id": "sted", "display_label": "775 nm depletion laser", "inventory_class": "light_source",
             "publication_label": "775 nm laser",
             "publication_template": "Stimulated-emission depletion was provided by {label}.",
             "source_metadata": {"kind": "laser", "role": "depletion", "wavelength_nm": 775},
             "method_sentence": "Stimulated-emission depletion was provided by 775 nm laser."})
        self.open_methods(instrument, storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "sources": [{"id": "sted", "display_label": "775 nm depletion laser",
                         "selected_wavelength_nm": 660}]})
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        output = self.output()
        self.assertIn("confirm the depletion wavelength used", output)
        self.assertNotIn("excitation wavelength", output)

    def test_a_wavelength_a_fixed_source_cannot_emit_is_not_reported(self):
        # Matching the laser by id says the right laser was named; it says nothing
        # about the line. "488 nm laser (594 nm)" would be a fabricated setting.
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "sources": [{"id": "laser", "display_label": "488 nm laser", "selected_wavelength_nm": 594}]})
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        prose = self._prose()
        self.assertIn("Excitation was provided by 488 nm laser.", prose)
        self.assertNotIn("594", prose)
        self.assertIn("which the instrument record gives as a fixed 488 nm source", self.output())

    def test_a_wavelength_within_a_tunable_range_is_reported(self):
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "sources": [{"id": "wll", "display_label": "White light laser", "selected_wavelength_nm": 561}]})
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        self.assertIn("white light laser (561 nm)", self._prose())
        self.assertNotIn("outside its recorded tunable range", self.output())

    def test_a_wavelength_outside_a_tunable_range_is_not_reported(self):
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "sources": [{"id": "wll", "display_label": "White light laser", "selected_wavelength_nm": 900}]})
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        self.assertNotIn("900", self._prose())
        self.assertIn("outside its recorded tunable range of 440–790 nm", self.output())

    def test_a_detection_window_outside_the_recorded_range_is_not_reported(self):
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "detectors": [{"id": "spectral_det", "display_label": "Spectral detector",
                           "collection_min_nm": 300, "collection_max_nm": 900}]})
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        prose = self._prose()
        self.assertIn("Images were recorded using Spectral detector.", prose)
        self.assertNotIn("300", prose)
        self.assertIn("below its recorded collection minimum of 400 nm", self.output())
        self.assertIn("above its recorded collection maximum of 700 nm", self.output())

    def test_a_detection_window_within_the_recorded_range_is_reported(self):
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "detectors": [{"id": "spectral_det", "display_label": "Spectral detector",
                           "collection_min_nm": 500, "collection_max_nm": 550}]})
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        self.assertIn("Spectral detector (detection 500–550 nm)", self._prose())

    def test_a_position_the_component_does_not_have_is_not_reported(self):
        # The same failure one level down: the right turret, the wrong position.
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "selected_route_steps": [{"kind": "optical_component", "component_id": "turret",
                                      "display_label": "Filter Turret",
                                      "position_label": "Nonexistent GFP cube"}]})
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        prose = self._prose()
        self.assertIn("The light path included Filter Turret.", prose)
        self.assertNotIn("Nonexistent GFP cube", prose)
        self.assertIn("which is not one of its recorded positions", self.output())

    def test_a_recorded_position_is_reported_from_the_record_not_the_plan(self):
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "selected_route_steps": [{"kind": "optical_component", "component_id": "turret",
                                      "display_label": "Filter Turret", "position_key": "Pos_1"}]})
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        # The plan named the position by key; the prose uses the record's own name
        # and catalogue number.
        self.assertIn("GFP cube (catalogue no. 49002) in the Filter Turret", self._prose())

    def test_an_ambiguous_label_binds_to_nothing_and_asserts_nothing(self):
        # Two recorded cameras share a display label, so a plan naming that label
        # identifies neither; binding to whichever was indexed first would produce
        # a confident sentence about the wrong physical component.
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "detectors": [{"display_label": "Acme Cam", "collection_min_nm": 500, "collection_max_nm": 550}],
        })
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        self.assertNotIn("Acme Cam", self._prose())
        self.assertIn("more than one recorded component is called", self.output())

    def test_a_plan_matched_by_canonical_id_is_reported_normally(self):
        # The guard must not block the case it exists to protect: an id resolves to
        # exactly one component, so the claim is made.
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "detectors": [{"id": "cam_a", "display_label": "Acme Cam",
                           "collection_min_nm": 500, "collection_max_nm": 550}],
        })
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        self.assertIn("Images were recorded using Acme Cam (detection 500–550 nm).", self._prose())
        self.assertNotIn("more than one recorded component", self.output())

    def test_a_route_named_by_a_shared_illumination_mode_binds_to_nothing(self):
        instrument = _instrument()
        routes = instrument["hardware"]["optical_path"]["authoritative_route_contract"]["routes"]
        routes[0]["illumination_mode"] = "widefield"
        routes.append({"id": "wf2", "display_label": "Second widefield path",
                       "illumination_mode": "widefield", "relevant_hardware": {}})
        self.open_methods(instrument, storage={
            "scope_id": "scope-reg", "route": "widefield", "validSelection": True,
            "sources": [{"id": "laser", "display_label": "488 nm laser"}]})
        # Two routes answer to the same broad mode, so it identifies neither.
        expect(self.page.locator("#runtime-confirm")).to_be_disabled()
        self.page.click("#add-btn")
        self.assertNotIn("488 nm laser", self._prose())

    def test_a_filter_position_from_another_route_is_neither_offered_nor_claimed(self):
        instrument = _instrument()
        routes = instrument["hardware"]["optical_path"]["authoritative_route_contract"]["routes"]
        routes.append({"id": "confocal", "display_label": "Point-scanning confocal", "relevant_hardware": {}})
        turret = next(item for item in instrument["hardware"]["optical_path"]["hardware_inventory_renderables"]
                      if item["id"] == "turret")
        turret["selectable_positions"] = [
            {"id": "Pos_1", "display_label": "GFP cube", "product_code": "49002",
             "incomplete": False, "route_ids": ["epi"], "route_labels": ["Epifluorescence"]},
            {"id": "Pos_9", "display_label": "Confocal-only cube", "product_code": "49009",
             "incomplete": False, "route_ids": ["confocal"], "route_labels": ["Point-scanning confocal"]},
        ]
        self.open_methods(instrument)
        self.page.check("#route-0")
        # Only the position that exists on the selected route is offered at all.
        positions = self.page.locator('input[id^="filterposition-"]')
        self.assertEqual(positions.count(), 1)
        self.page.check("#filterposition-0-0")
        self.page.click("#add-btn")
        prose = self._prose()
        self.assertIn("GFP cube (catalogue no. 49002)", prose)
        self.assertNotIn("Confocal-only cube", prose)

    def test_exported_configuration_without_identity_is_not_offered(self):
        # The localStorage path already required identity; the exported path treated
        # its absence as permission, so any plan could be attributed to any scope.
        self.open_methods(_instrument(runtime_selected_configuration={
            "route": "epi", "validSelection": True,
            "sources": [{"display_label": "Ghost laser", "wavelength_nm": 999}]}))
        expect(self.page.locator("#runtime-confirm")).to_be_disabled()
        self.page.click("#add-btn")
        self.assertNotIn("Ghost laser", self.output())

    def test_record_without_a_methods_block_is_refused_rather_than_rendered_empty(self):
        self.open_methods({"id": "scope-bare", "display_name": "Bare Record"})
        self.page.click("#add-btn")
        self.assertIn("is incomplete", self.output())
        self.assertNotIn("Light Microscopy Methods:", self.output())

    def test_two_components_sharing_a_label_are_not_silently_reported_as_one(self):
        self.open_methods()
        self.page.check("#det-0")
        self.page.check("#det-1")
        self.page.click("#add-btn")
        self.assertIn("cannot tell them apart", self.output())

    def test_several_channels_prompt_for_acquisition_order(self):
        self.open_methods()
        self.page.check("#det-0")
        self.page.check("#det-1")
        self.page.click("#add-btn")
        self.assertIn("sequentially or simultaneously", self.output())

    def test_several_routes_in_one_acquisition_are_questioned(self):
        instrument = _instrument()
        instrument["hardware"]["optical_path"]["authoritative_route_contract"]["routes"].append(
            {"id": "confocal", "display_label": "Point-scanning confocal", "relevant_hardware": {}})
        self.open_methods(instrument)
        self.page.check("#route-0")
        self.page.check("#route-1")
        self.page.click("#add-btn")
        self.assertIn("optical routes are reported for a single acquisition", self.output())

    def test_changing_the_selection_after_confirming_says_the_plan_was_dropped(self):
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "sources": [{"display_label": "488 nm laser", "selected_wavelength_nm": 488}]})
        self.page.check("#runtime-confirm")
        self.page.check("#det-0")
        expect(self.page.locator("#runtime-confirm")).not_to_be_checked()
        expect(self.page.locator("#runtime-review-status")).to_contain_text("no longer included")

    def test_a_component_named_like_a_review_marker_survives_intact(self):
        instrument = _instrument()
        instrument["hardware"]["optical_path"]["authoritative_route_contract"]["routes"][0]["display_label"] = (
            "[PLEASE SPECIFY: fake] route")
        self.open_methods(instrument)
        self.page.check("#route-0")
        self.page.click("#add-btn")
        # Prose is built from structured facts, so nothing scans the finished text
        # for markers and no recorded name can be mistaken for one.
        self.assertIn("[PLEASE SPECIFY: fake] route", self.output())

    def test_selectors_on_routes_that_were_not_used_are_not_asked_about(self):
        instrument = _instrument()
        instrument["hardware"]["optical_path"]["authoritative_route_contract"]["routes"].append(
            {"id": "confocal", "display_label": "Point-scanning confocal", "relevant_hardware": {}})
        instrument["methods"]["unresolved_optics"] = [
            {"inventory_id": "turret", "display_label": "Filter Turret",
             "route_label": "Epifluorescence", "scoped_label": "Filter Turret (Epifluorescence route)"},
            {"inventory_id": "sp", "display_label": "Spectral module",
             "route_label": "Point-scanning confocal",
             "scoped_label": "Spectral module (Point-scanning confocal route)"},
        ]
        self.open_methods(instrument)
        self.page.check("#route-0")
        self.page.click("#add-btn")
        output = self.output()
        self.assertIn("Filter Turret (Epifluorescence route)", output)
        self.assertNotIn("Spectral module", output)

    def test_technique_specific_settings_are_requested(self):
        instrument = _instrument()
        routes = instrument["hardware"]["optical_path"]["authoritative_route_contract"]["routes"]
        routes[0]["route_type"] = "confocal_point"
        routes[0]["route_identity"] = {"readouts": [{"id": "flim", "display_label": "FLIM"}]}
        self.open_methods(instrument)
        self.page.check("#readout-0-0")
        self.page.click("#add-btn")
        output = self.output()
        # The generic settings list is identical for every acquisition; these are the
        # parameters that make this particular measurement reproducible.
        self.assertIn("confocal pinhole diameter (in Airy units)", output)
        self.assertIn("how the instrument response was determined", output)

    def test_widefield_acquisition_gets_no_confocal_prompt(self):
        self.open_methods()
        self.page.check("#route-0")
        self.page.click("#add-btn")
        self.assertNotIn("Airy units", self.output())

    def test_the_filter_actually_used_can_be_stated_not_just_its_holder(self):
        # Ticking the holder only says light passed through it. The position is the
        # filter, and the filter is the fact a fluorescence Methods section needs.
        instrument = _instrument()
        instrument["methods"]["unresolved_optics"] = [{
            "inventory_id": "turret", "display_label": "Filter Turret",
            "route_label": "Epifluorescence",
            "scoped_label": "Filter Turret (Epifluorescence route)"}]
        self.open_methods(instrument)
        self.page.check("#filterposition-0-0")
        expect(self.page.locator("#filter-0")).to_be_checked()
        self.page.click("#add-btn")
        output = self.output()
        self.assertIn("The light path included GFP cube (catalogue no. 49002) in the Filter Turret.", output)
        # The holder alone is no longer claimed, and the question it prompted is answered.
        self.assertNotIn("The light path included Filter Turret.", output)
        self.assertNotIn("which position of Filter Turret", output)

    def test_an_unresolved_selector_is_still_asked_about(self):
        instrument = _instrument()
        instrument["methods"]["unresolved_optics"] = [
            {"inventory_id": "turret", "display_label": "Filter Turret",
             "route_label": "Epifluorescence", "scoped_label": "Filter Turret (Epifluorescence route)"},
            {"inventory_id": "wheel", "display_label": "Emission Wheel",
             "route_label": "Epifluorescence", "scoped_label": "Emission Wheel (Epifluorescence route)"},
        ]
        self.open_methods(instrument)
        self.page.check("#filterposition-0-0")
        self.page.click("#add-btn")
        output = self.output()
        self.assertIn("which position of Emission Wheel (Epifluorescence route)", output)
        self.assertNotIn("Filter Turret (Epifluorescence route)", output)

    def test_a_position_with_incomplete_bands_is_flagged(self):
        self.open_methods()
        self.page.check("#filterposition-0-1")
        self.page.click("#add-btn")
        self.assertIn("recorded transmission bands for DAPI cube are incomplete", self.output())

    def test_clearing_the_holder_clears_the_position_under_it(self):
        self.open_methods()
        self.page.check("#filterposition-0-0")
        expect(self.page.locator("#filter-0")).to_be_checked()
        self.page.uncheck("#filter-0")
        expect(self.page.locator("#filterposition-0-0")).not_to_be_checked()


    def test_publication_prose_is_not_produced_by_rewriting_finished_text(self):
        """The page loads one script; prose is rendered, never re-parsed."""
        rendered = self.template.render(methods_generator_config_json="{}")
        self.assertEqual(rendered.count("<script src="), 1)
        self.assertIn("methods_generator_app.js", rendered)


if __name__ == "__main__":
    unittest.main()
