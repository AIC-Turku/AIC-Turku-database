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
        self.assertIn("[PLEASE SPECIFY: which phase mask profile was applied", dto["method_sentence"])

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
              "method_sentence": "Excitation was provided by 488 nm laser."}
    camera_a = {"id": "cam_a", "display_label": "Acme Cam", "inventory_class": "endpoint",
                "publication_label": "Acme Cam", "publication_template": "Images were recorded using {label}.",
                "method_sentence": "Images were recorded using Acme Cam."}
    camera_b = {**camera_a, "id": "cam_b"}
    instrument = {
        "id": "scope-reg", "display_name": "Regression Scope",
        "methods_generation": {"is_blocked": False, "blockers": []},
        "methods": {"base_sentence": "Images were acquired using the Regression Scope."},
        "hardware": {"objectives": [], "optical_path": {
            "hardware_inventory_renderables": [source, camera_a, camera_b],
            "authoritative_route_contract": {"routes": [
                {"id": "epi", "display_label": "Epifluorescence",
                 "relevant_hardware": {"sources": [source], "endpoints": [camera_a, camera_b]}},
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

    def test_plan_component_absent_from_the_record_is_flagged_not_asserted(self):
        self.open_methods(storage={
            "scope_id": "scope-reg", "route": "epi", "validSelection": True,
            "sources": [{"display_label": "Decommissioned 594 nm laser", "selected_wavelength_nm": 594}],
        })
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        self.assertIn("which is not in the current instrument record", self.output())

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

    def test_publication_prose_is_not_produced_by_rewriting_finished_text(self):
        """The page loads one script; prose is rendered, never re-parsed."""
        rendered = self.template.render(methods_generator_config_json="{}")
        self.assertEqual(rendered.count("<script src="), 1)
        self.assertIn("methods_generator_app.js", rendered)


if __name__ == "__main__":
    unittest.main()
