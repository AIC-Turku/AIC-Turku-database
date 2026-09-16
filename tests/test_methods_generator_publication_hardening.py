"""Regressions from the 48-configuration Methods publication audit."""
import json
import shutil
import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def scope():
    source = {"id": "laser", "display_label": "Laser v1.2", "inventory_class": "light_source",
              "method_sentence": "Excitation used Laser v1.2."}
    detector = {"id": "camera", "display_label": "pco.edge 4.2", "inventory_class": "endpoint",
                "method_sentence": "Images were recorded using pco.edge 4.2."}
    return {
        "id": "scope-audit", "display_name": "Audit Scope",
        "methods_generation": {"is_blocked": False, "blockers": []},
        "methods": {"base_sentence": "Images were acquired using the Audit Scope."},
        "hardware": {"objectives": [], "optical_path": {
            "hardware_inventory_renderables": [source, detector],
            "authoritative_route_contract": {"routes": [
                {"id": "widefield", "display_label": "Widefield fluorescence",
                 "relevant_hardware": {"sources": [source], "endpoints": [detector]},
                 "route_identity": {"readouts": [{"id": "spectral", "display_label": "Spectral imaging"}]}},
                {"id": "confocal", "display_label": "Point-scanning confocal", "relevant_hardware": {}}
            ]}}}
    }


class PublicationHardeningTests(unittest.TestCase):
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
        instrument = instrument or scope()
        html = self.template.render(methods_generator_config_json=json.dumps({
            "instrument_data_url": "/instruments.json", "acknowledgements": {"standard": ""}}))
        bootstrap = (
            "window.fetch = async () => ({ok: true, json: async () => ("
            + json.dumps({"instruments": [instrument]})
            + ")});"
        )
        if storage is not None:
            bootstrap += (
                "Object.defineProperty(window, 'localStorage', {configurable: true, value: {getItem() {return "
                + json.dumps(json.dumps(storage))
                + ";}}});"
            )
        html = html.replace(
            '<script src="../assets/javascripts/methods_generator_app.js"></script>',
            "<script>" + self.app + "</script>",
        )
        self.page.set_content("<script>" + bootstrap + "</script>" + html)
        expect(self.page.locator("#system-select")).to_be_enabled()
        self.page.select_option("#system-select", instrument["id"])

    def output(self):
        return self.page.locator("#output-text").input_value()

    def test_unknown_runtime_route_cannot_be_imported(self):
        self.open_methods(storage={"scope_id": "scope-audit", "route": "nonexistent-route", "validSelection": True,
                                   "sources": [{"display_label": "488 nm laser", "selected_wavelength_nm": 488}]})
        expect(self.page.locator("#runtime-confirm")).to_be_disabled()
        expect(self.page.locator("#runtime-review-status")).to_contain_text("not present in the instrument's recorded routes")
        self.page.click("#add-btn")
        self.assertNotIn("nonexistent-route", self.output())
        self.assertNotIn("488 nm laser (488 nm)", self.output())

    def test_dotted_hardware_names_are_not_truncated(self):
        self.open_methods()
        self.page.check("#route-0")
        self.page.check("#light-0")
        self.page.check("#det-0")
        self.page.click("#add-btn")
        self.assertIn("Laser v1.2", self.output())
        self.assertIn("pco.edge 4.2", self.output())

    def test_review_prompts_are_consolidated_and_idempotent(self):
        instrument = scope()
        instrument["methods"]["acquisition_settings_recommendation"] = "[PLEASE SPECIFY: exposure time and pixel size]."
        instrument["methods"]["quarep_light_path_recommendation_needed"] = True
        instrument["methods"]["quarep_light_path_recommendation"] = "[PLEASE VERIFY: exact emission filter and detector path]."
        self.open_methods(instrument=instrument)
        self.page.click("#add-btn")
        output = self.output()
        self.assertEqual(output.count("Review before publication:"), 1)
        self.assertIn("- [PLEASE VERIFY: exact emission filter and detector path]", output)
        self.assertIn("- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting exposure time and pixel size.", output)
        self.assertIn("original image metadata", output)
        self.page.click("#add-btn")
        self.assertEqual(self.output().count("Review before publication:"), 1)


if __name__ == "__main__":
    unittest.main()
