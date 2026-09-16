"""Regression coverage for the September 2026 audit using the real DOM/runtime."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def scope(identifier="scope-test"):
    source = {"id": "laser", "display_label": "488 laser", "inventory_class": "light_source",
              "method_sentence": "Excitation used the 488 laser."}
    detector = {"id": "camera", "display_label": "Camera", "inventory_class": "endpoint",
                "method_sentence": "Images were recorded on Camera."}
    return {
        "id": identifier, "display_name": identifier,
        "methods_generation": {"is_blocked": False, "blockers": []},
        "methods": {"base_sentence": "Images were acquired on the test microscope.",
                    "environment_sentence": "Live cells were imaged at 37 degrees.",
                    "stage_sentences": ["Z-stacks were acquired."],
                    "autofocus_sentence": "Autofocus was used.",
                    "triggering_sentence": "Hardware triggering was used.",
                    "processing_sentences": ["Images were deconvolved."]},
        "hardware": {"objectives": [
            # Shaped like the real export: prose is assembled from the template and
            # phrase, so the test exercises what production actually renders.
            {"id": "obj20", "display_label": "20x", "method_sentence": "Imaging was performed with a 20x objective.",
             "publication_template": "Imaging was performed with {label}.", "publication_phrase": "a 20x objective"},
            {"id": "obj40", "display_label": "40x", "method_sentence": "Imaging was performed with a 40x objective.",
             "publication_template": "Imaging was performed with {label}.", "publication_phrase": "a 40x objective"}],
            "optical_path": {"hardware_inventory_renderables": [source, detector],
                "authoritative_route_contract": {"routes": [
                    {"id": "epi", "display_label": "Epi", "relevant_hardware": {"sources": [source], "endpoints": [detector]},
                     "route_identity": {"readouts": [{"id": "flim", "display_label": "FLIM"}]}},
                    {"id": "other", "display_label": "Other", "relevant_hardware": {}}]}}},
    }


class AuditRuntimeRegressions(unittest.TestCase):
    def test_public_runtime_regressions(self):
        result = subprocess.run(["node", "tests/fixtures/audit_runtime_regressions.js"],
                                cwd=ROOT, text=True, capture_output=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class AuditBrowserRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        executable = shutil.which("chromium") or shutil.which("chromium-browser")
        cls.browser = cls.playwright.chromium.launch(
            **({"executable_path": executable} if executable else {}))
        cls.template = Environment(loader=FileSystemLoader(ROOT / "scripts/templates")).get_template("methods_generator.md.j2")
        cls.script = (ROOT / "assets/javascripts/methods_generator_app.js").read_text()

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

    def open_methods(self, instruments=None, storage=None, init_script=None, select_route=True):
        instruments = instruments or [scope()]
        html = self.template.render(methods_generator_config_json=json.dumps({
            "instrument_data_url": "/instruments.json", "acknowledgements": {"standard": "Facility acknowledgement."}}))
        # No network is needed: exercise the production page and JavaScript in a
        # real browser DOM with deterministic fetch/storage boundaries.
        bootstrap = "window.fetch = async () => ({ok: true, json: async () => (" + json.dumps({"instruments": instruments}) + ")});"
        if storage is not None:
            bootstrap += "Object.defineProperty(window, 'localStorage', {configurable: true, value: {getItem() {return " + json.dumps(json.dumps(storage)) + ";}}});"
        if init_script:
            bootstrap += init_script
        html = html.replace('<script src="../assets/javascripts/methods_generator_app.js"></script>',
                            "<script>" + self.script + "</script>")
        self.page.set_content("<script>" + bootstrap + "</script>" + html)
        expect(self.page.locator("#system-select")).to_be_enabled()
        self.page.select_option("#system-select", instruments[0]["id"])
        # An acquisition has to name the light path it travelled before it can state
        # anything else, so tests that are not about path selection confirm it here.
        if select_route and self.page.locator("#route-0").count():
            self.page.check("#route-0")

    def output(self):
        return self.page.locator("#output-text").input_value()

    def test_installed_actions_are_not_reported_until_confirmed(self):
        self.open_methods()
        self.page.click("#add-btn")
        for text in ["Live cells were", "Z-stacks were", "Autofocus was", "triggering was", "deconvolved"]:
            self.assertNotIn(text, self.output())
        self.page.check("#confirmed-2")
        self.page.click("#add-btn")
        self.assertIn("Autofocus was used.", self.output())
        self.assertNotIn("Images were deconvolved.", self.output())

    def test_simulator_requires_confirmation_and_preserves_unknown_numbers(self):
        plan = {"scope_id": "scope-test", "route": "epi", "validSelection": True,
                "sources": [{"id": "laser", "display_label": "Plan laser", "selected_wavelength_nm": 561},
                            {"id": "laser2", "display_label": "Unknown laser", "wavelength_nm": None}],
                "detectors": [{"id": "camera", "display_label": "Plan camera",
                               "collection_min_nm": None, "collection_max_nm": None}]}
        # Only components the record holds may be reported, so the plan names them
        # by their canonical ids.
        instrument = scope()
        inventory = instrument["hardware"]["optical_path"]["hardware_inventory_renderables"]
        inventory[0].update({"publication_label": "Plan laser",
                             "source_metadata": {"wavelength_nm": 561},
                             "publication_template": "Excitation used {label}."})
        inventory[1].update({"publication_label": "Plan camera",
                             "publication_template": "Images were recorded using {label}."})
        inventory.append({"id": "laser2", "display_label": "Unknown laser", "inventory_class": "light_source",
                          "publication_label": "Unknown laser",
                          "publication_template": "Excitation used {label}."})
        self.open_methods(instruments=[instrument], storage=plan)
        self.page.click("#add-btn")
        self.assertNotIn("Plan laser", self.output())
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        self.assertIn("Plan laser (561 nm)", self.output())
        self.assertNotIn("Unknown laser (0", self.output())
        self.assertNotIn("Plan camera (0", self.output())
        for internal_wording in ["runtime-selected", "exported DTO", "browser fallback", "wheel/turret", "Route-specific optical"]:
            self.assertNotIn(internal_wording, self.output())

    def test_invalid_simulator_plan_cannot_be_confirmed(self):
        self.open_methods(storage={"scope_id": "scope-test", "route": "epi", "validSelection": False})
        expect(self.page.locator("#runtime-confirm")).to_be_disabled()
        self.page.click("#add-btn")
        self.assertNotIn("runtime-selected configuration", self.output())

    def test_storage_access_failure_does_not_break_the_form(self):
        self.open_methods(init_script="Object.defineProperty(window, 'localStorage', {get() {throw new Error('Storage denied');}});")
        self.page.click("#add-btn")
        # The point is that a draft is still produced; the opening names the
        # technique from the confirmed light path.
        self.assertIn("Epi imaging was performed using", self.output())

    def test_route_changes_preserve_compatible_choices_and_clear_incompatible_ones(self):
        # Light paths are multi-select, because one acquisition can travel two of
        # them, so leaving a path is unchecking it rather than checking another.
        self.open_methods(select_route=False)
        self.page.check("#readout-0-0")
        expect(self.page.locator("#route-0")).to_be_checked()
        self.page.check("#light-0")
        expect(self.page.locator("#light-0")).to_be_checked()
        self.page.check("#route-1")
        self.page.uncheck("#route-0")
        expect(self.page.locator("#readout-0-0")).not_to_be_checked()
        expect(self.page.locator("#light-list input")).to_have_count(0)
        self.page.click("#add-btn")
        self.assertNotIn("Excitation used the 488 laser.", self.output())

    def test_instrument_switch_does_not_reuse_previous_selections(self):
        self.open_methods(instruments=[scope(), scope("scope-second")])
        self.page.check("#light-0")
        self.page.check("#confirmed-0")
        self.page.select_option("#system-select", "scope-second")
        expect(self.page.locator("#light-0")).not_to_be_checked()
        expect(self.page.locator("#confirmed-0")).not_to_be_checked()

    def test_repeated_acquisitions_do_not_overwrite_and_double_click_is_idempotent(self):
        self.open_methods()
        self.page.fill("#session-label", "Fixed cells")
        self.page.check("#obj-0")
        self.page.click("#add-btn")
        self.page.click("#add-btn")
        self.assertEqual(self.output().count("a 20x objective"), 1)
        self.page.fill("#session-label", "Second acquisition")
        self.page.uncheck("#obj-0")
        self.page.check("#obj-1")
        self.page.click("#add-btn")
        for expected in ["Fixed cells", "Second acquisition", "20x", "40x"]:
            self.assertIn(expected, self.output())
        self.assertEqual(self.page.locator('label[for="acquisition-date"]').count(), 0)

    def test_compatible_objective_facts_are_combined_into_normal_prose(self):
        self.open_methods()
        self.page.check("#obj-0")
        self.page.check("#obj-1")
        self.page.click("#add-btn")
        self.assertIn("Imaging was performed with a 20x objective and a 40x objective.", self.output())
        self.assertNotIn("Imaging was performed with a 20x objective. Imaging was performed with", self.output())

    def test_review_prompts_are_separate_from_finished_prose(self):
        instrument = scope()
        instrument["methods"]["acquisition_settings_recommendation"] = "[PLEASE SPECIFY: exposure time and pixel size]."
        instrument["methods"]["quarep_light_path_recommendation_needed"] = True
        instrument["methods"]["quarep_light_path_recommendation"] = "[PLEASE VERIFY: emission filter used]."
        self.open_methods(instruments=[instrument])
        self.page.click("#add-btn")
        output = self.output()
        self.assertEqual(output.count("Review before publication:"), 1)
        self.assertIn("- [PLEASE VERIFY: emission filter used]", output)
        self.assertIn("- [RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting exposure time and pixel size.", output)
        self.assertIn("original image metadata", output)
        self.assertNotIn("microscope. [PLEASE", output)

    def test_clipboard_rejection_reports_failure_instead_of_success(self):
        self.open_methods()
        self.page.click("#add-btn")
        self.page.evaluate("Object.defineProperty(navigator, 'clipboard', {value: {writeText() {return Promise.reject(new Error('denied'));}}});")
        self.page.click("#copy-btn")
        expect(self.page.locator("#copy-feedback")).to_contain_text("Automatic copying failed")
        self.assertNotEqual(self.page.locator("#copy-feedback").inner_text(), "Copied!")

    def test_clipboard_success_is_reported_only_after_resolution(self):
        self.open_methods()
        self.page.click("#add-btn")
        self.page.evaluate("Object.defineProperty(navigator, 'clipboard', {value: {writeText() {return new Promise(resolve => {window.finishCopy = resolve;});}}});")
        self.page.click("#copy-btn")
        expect(self.page.locator("#copy-feedback")).not_to_be_visible()
        self.page.evaluate("window.finishCopy()")
        expect(self.page.locator("#copy-feedback")).to_have_text("Copied!")

    def test_confirmed_import_uses_the_reviewed_snapshot(self):
        self.open_methods(storage={"scope_id": "scope-test", "route": "epi",
                                  "sources": [{"display_label": "Reviewed laser", "wavelength_nm": 488}]})
        self.page.evaluate("Object.defineProperty(window, 'localStorage', {value: {getItem() {return JSON.stringify({scope_id: 'scope-test', route: 'epi', sources: [{display_label: 'Unreviewed laser'}]});}}});")
        self.page.check("#runtime-confirm")
        self.page.click("#add-btn")
        self.assertIn("Reviewed laser", self.output())
        self.assertNotIn("Unreviewed laser", self.output())

    def test_conflicting_instrument_ids_are_not_importable(self):
        self.open_methods(storage={"scope_id": "scope-test", "instrument_id": "different-scope", "route": "epi"})
        expect(self.page.locator("#runtime-confirm")).to_be_disabled()

    def test_scoreboard_reads_the_runtime_result_fields(self):
        # Exercise the production renderer with its DOM dependencies, not a
        # second implementation of the formatting logic.
        source = (ROOT / "scripts/templates/virtual_microscope_app.js").read_text()
        renderer = "function renderScoreboard(simulation) {" + source.split("function renderScoreboard(simulation) {", 1)[1].split("\n  function errorMessage", 1)[0]
        self.page.set_content('<div id="scoreboard"></div>')
        self.page.evaluate("""() => {
          const state = {loadedProteins: new Map([['f', {key: 'f', emMax: 530}]])};
          const DOM = {scoreboard: document.getElementById('scoreboard')};
          const mapToArray = value => Array.from(value.values());
          const colorHex = () => '#000000';
          const escapeHtml = value => String(value ?? '');
        """ + renderer + """
          renderScoreboard({results: [{fluorophoreKey: 'f', fluorophoreName: 'Green', qualityLabel: 'good',
            excitationStrength: 0.6, sted: {emissionOverlap: 0.4}}]});
        }""")
        expect(self.page.locator('.vm-info-row').filter(has_text='Excitation')).to_contain_text('60.0%')
        expect(self.page.locator('.vm-info-row').filter(has_text='Depletion overlap')).to_contain_text('40%')
