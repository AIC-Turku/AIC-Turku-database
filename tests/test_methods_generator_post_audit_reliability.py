"""Browser regressions for the post-audit Methods Generator reliability fixes."""
import json
import shutil
import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class MethodsGeneratorPostAuditReliabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        executable = shutil.which("chromium") or shutil.which("chromium-browser")
        cls.browser = cls.playwright.chromium.launch(**({"executable_path": executable} if executable else {}))
        cls.template = Environment(loader=FileSystemLoader(ROOT / "scripts/templates")).get_template("methods_generator.md.j2")
        cls.core = (ROOT / "assets/javascripts/methods_generator_app.js").read_text(encoding="utf-8")
        cls.controller = (ROOT / "assets/javascripts/methods_generator_session_controller.js").read_text(encoding="utf-8")
        cls.payload = json.loads((ROOT / "assets/instruments_data.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.open_methods()

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def open_methods(self):
        html = self.template.render(methods_generator_config_json=json.dumps({
            "instrument_data_url": "/instruments.json",
            "acknowledgements": {"standard": ""},
            "output_title": "Light Microscopy Methods",
        }))
        bootstrap = (
            "window.fetch = async () => ({ok: true, json: async () => ("
            + json.dumps(self.payload)
            + ")});"
        )
        html = html.replace(
            '<script src="../assets/javascripts/methods_generator_app.js"></script>',
            "<script>" + self.core + "</script>",
        ).replace(
            '<script src="../assets/javascripts/methods_generator_session_controller.js"></script>',
            "<script>" + self.controller + "</script>",
        )
        self.page.set_content("<script>" + bootstrap + "</script>" + html)
        expect(self.page.locator("#system-select")).to_be_enabled()

    def select_instrument(self, label):
        self.page.select_option("#system-select", label=label)

    def check(self, label, nth=0):
        locator = self.page.get_by_label(label, exact=True)
        if locator.count() > 1:
            locator = locator.nth(nth)
        locator.check()
        return locator

    def output(self):
        return self.page.locator("#output-text").input_value()

    def test_same_route_method_change_keeps_path_hardware_and_clears_sted_state(self):
        self.select_instrument("Abberior STED")
        self.check("STED")
        self.check("UPlanSApo 100x/1.40 Oil OIL — Olympus")
        self.check("Easy3D STED — Abberior")
        self.check("640 nm laser (PicoQuant LDH-D-C-640) — PicoQuant")
        self.check("775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics")
        self.check("Hamamatsu Photonics Photomultiplier Tube — Hamamatsu Photonics")

        self.check("Confocal point scanning")
        self.page.wait_for_timeout(10)

        self.assertFalse(self.page.get_by_label("Easy3D STED — Abberior", exact=True).is_checked())
        self.assertFalse(self.page.get_by_label("UPlanSApo 100x/1.40 Oil OIL — Olympus", exact=True).is_checked())
        self.assertTrue(self.page.get_by_label("640 nm laser (PicoQuant LDH-D-C-640) — PicoQuant", exact=True).is_checked())
        self.assertFalse(self.page.get_by_label("775 nm laser (OneFive / NKT Photonics Katana HP 775) — OneFive / NKT Photonics", exact=True).is_checked())
        self.assertTrue(self.page.get_by_label("Hamamatsu Photonics Photomultiplier Tube — Hamamatsu Photonics", exact=True).is_checked())

        self.page.click("#add-btn")
        self.assertNotIn("Easy3D STED", self.output())

    def test_same_physical_path_widefield_to_tirf_retains_valid_selections(self):
        self.select_instrument("Zeiss TIRF")
        self.check("Widefield fluorescence")
        self.check("561 nm laser — Unknown")
        self.check("Filter set 43 HE (DsRed) (catalogue no. 43 HE)")
        self.check("Hamamatsu ORCA-Flash4.0 CMOS — Hamamatsu")

        self.check("TIRF")
        self.page.wait_for_timeout(10)

        self.assertTrue(self.page.get_by_label("561 nm laser — Unknown", exact=True).is_checked())
        self.assertTrue(self.page.get_by_label("Filter set 43 HE (DsRed) (catalogue no. 43 HE)", exact=True).is_checked())
        self.assertTrue(self.page.get_by_label("Hamamatsu ORCA-Flash4.0 CMOS — Hamamatsu", exact=True).is_checked())

    def test_placeholder_detector_becomes_review_request_not_publication_fact(self):
        self.select_instrument("Leica DM IRBE")
        self.check("Widefield fluorescence")
        self.check("PL FLUOTAR 20x/0.50 PH2 AIR — Leica")
        self.check("arc lamp (Leica 50W HBO short arc bulb) — Leica")
        self.check("Unknown Camera — Unknown")
        self.page.click("#add-btn")

        output = self.output()
        self.assertNotIn("Images were recorded using Unknown Camera", output)
        self.assertIn("detector/camera used for this acquisition", output)

    def test_sted_missing_depletion_and_detector_are_explicit(self):
        self.select_instrument("Abberior STED")
        self.check("STED")
        self.check("UPlanSApo 100x/1.40 Oil OIL — Olympus")
        self.check("485 nm laser (PicoQuant LDH-D-C-485) — PicoQuant")
        self.page.click("#add-btn")

        output = self.output()
        self.assertIn("detector or observation path used for this acquisition", output)
        self.assertIn("STED imaging was selected but no depletion source is reported", output)

    def test_legacy_multiphoton_route_is_auto_selected_and_names_method(self):
        self.select_instrument("Leica TCS SP5 Multiphoton (Retired)")
        expect(self.page.get_by_label("Multiphoton", exact=True)).to_be_checked()
        self.check("HCX IR APO L 25x/0.95 WATER — Leica")
        self.check("pulsed near-ir laser (Coherent Chameleon Ultra II) — Coherent")
        self.check("NDD PMT")
        self.page.click("#add-btn")

        output = self.output()
        self.assertIn("Two-photon (multiphoton) excitation imaging was performed", output)
        self.assertNotIn("Multiphoton route", output)

    def test_correction_replaces_entry_and_clear_all_resets_controls(self):
        self.select_instrument("Andor BC43 Benchtop Confocal")
        self.check("Widefield fluorescence")
        self.check("20X Plan Apo LD Air 20x/0.8 AIR — Nikon")
        self.check("488 nm laser (Andor Borealis Illumination) — Andor")
        self.check("Andor 4.1 MP sCMOS — Andor")
        self.page.click("#add-btn")

        self.check("Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).")
        self.page.click("#add-btn")
        output = self.output()
        self.assertEqual(output.count("Widefield fluorescence imaging was performed"), 1)
        self.assertIn("Fusion BC43 (v2.7.0)", output)
        self.assertNotIn("Software version is not recorded for this instrument", output)

        self.page.click("#clear-btn")
        self.assertEqual(self.page.locator("#hardware-options input:checked").count(), 0)
        self.assertEqual(self.page.locator("#session-label").input_value(), "")
        self.assertTrue(self.output().startswith("Select an instrument"))

    def test_identical_selected_cameras_keep_multiplicity(self):
        self.select_instrument("Nikon Ti2-E Crest V3")
        self.check("Confocal spinning disk")
        self.check("CFI Plan Apochromat Lambda D 20X DIC N2 20x/0.8 AIR — Nikon")
        self.check("476 nm laser (Lumencor Celesta 7ch) — Lumencor")
        cameras = self.page.get_by_label("Photometrics Kinetix — Photometrics", exact=True)
        self.assertEqual(cameras.count(), 2)
        cameras.nth(0).check()
        cameras.nth(1).check()
        self.page.click("#add-btn")
        self.assertIn("2 × Photometrics Kinetix", self.output())


if __name__ == "__main__":
    unittest.main()
