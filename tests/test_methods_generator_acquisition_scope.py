"""Browser regressions for what one acquisition entry may state.

Every test here reproduces a user-visible failure found by the Methods generator
audit, through the same controls a user clicks. The failures they cover all had
the same shape: the draft asserted hardware, a method or a microscope identity
that the user had not selected for the acquisition being described.

Each test names the behaviour it protects; the audit that found them is recorded
in the pull request that introduced these fixes.

Implementation vocabulary in prose is not checked here. A fixture can only prove
it for the labels the fixture invented, and
`tests/test_methods_generator_real_catalogue.py` sweeps every instrument and every
method the facility has actually authored, which is where the words that reached a
draft came from.
"""

import json
import shutil
import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


# Roles whose sources do not produce an image channel, as
# vocab/light_source_roles.yaml records it and the export carries it.
_NON_CHANNEL_ROLES = {"depletion", "activation", "alignment"}


def _source(identifier, label, template, role=""):
    return {
        "id": identifier,
        "display_label": label,
        "publication_label": label,
        "inventory_class": "light_source",
        "publication_template": template,
        "method_sentence": template.replace("{label}", label),
        "role": role,
        "forms_imaging_channel": role not in _NON_CHANNEL_ROLES,
        "source_metadata": {"role": role} if role else {},
        "review_prompts": [],
    }


def _endpoint(identifier, label):
    return {
        "id": identifier,
        "display_label": label,
        "publication_label": label,
        "inventory_class": "endpoint",
        "publication_template": "Images were recorded using {label}.",
        "method_sentence": f"Images were recorded using {label}.",
        "review_prompts": [],
    }


def instrument():
    """A microscope offering super-resolution, confocal and transmitted imaging.

    Shaped like the real records the audit ran against: two methods share the
    point-scanning path, the transmitted path is separate, and the super-resolution
    module is offered independently of the method - which is how a previous
    acquisition's module used to end up in the next acquisition's prose.
    """
    excitation = _source("source:exc", "488 nm laser", "Excitation was provided by {label}.", "excitation")
    depletion = _source("source:dep", "775 nm laser", "Depletion was provided by {label}.", "depletion")
    lamp = _source("source:bf", "Halogen lamp", "Transmitted-light illumination was provided by {label}.",
                   "transmitted_illumination")
    detector = _endpoint("endpoint:apd", "Avalanche photodiode")
    bf_detector = _endpoint("endpoint:bf", "Transmitted-light detector")
    routes = [
        {
            "id": "confocal",
            "display_label": "Point-scanning confocal",
            "route_type": "confocal_point",
            "route_identity": {
                "imaging_modes": [
                    {"id": "confocal_point", "display_label": "Confocal point scanning",
                     "publication_phrase": "Point-scanning confocal imaging"},
                    # As the real export carries it, from vocab/imaging_modes.yaml
                    # `tags.requires_source_role`. The page must not know this by
                    # itself.
                    {"id": "sted", "display_label": "STED",
                     "publication_phrase": "Stimulated emission depletion (STED) imaging",
                     "requires_source_role": "depletion"},
                ],
                "contrast_methods": [],
                "readouts": [],
            },
            "relevant_hardware": {
                "sources": [excitation, depletion], "filters": [], "splitters": [],
                "endpoints": [detector],
            },
            "branch_summary": {"branches": []},
        },
        {
            "id": "transmitted",
            "display_label": "Transmitted light",
            "route_type": "transmitted_light",
            "route_identity": {
                "imaging_modes": [],
                "contrast_methods": [{"id": "transmitted_brightfield",
                                      "display_label": "Transmitted brightfield",
                                      "publication_phrase": "Transmitted-light brightfield imaging"}],
                "readouts": [],
            },
            "relevant_hardware": {
                "sources": [lamp], "filters": [], "splitters": [], "endpoints": [bf_detector],
            },
            "branch_summary": {"branches": []},
        },
    ]
    return {
        "id": "scope-scope-test",
        "display_name": "Scope Under Test",
        "methods_generation": {"is_blocked": False, "blockers": []},
        "methods": {
            "base_sentence": "Images were acquired using the Scope Under Test.",
            "instrument_reference": "the Scope Under Test, an inverted microscope",
            "specimen_preparation_recommendation": "[PLEASE SPECIFY: Specimen preparation metadata]",
            "acquisition_settings_recommendation": "[PLEASE SPECIFY: exposure time and pixel size].",
        },
        "software": [{"name": "Scope Acquire", "version": "1.0", "role": "acquisition"}],
        "modalities": [],
        "modules": [{
            "type": "easy3d_sted",
            "display_label": "Easy3D STED",
            # As the real export carries it, from vocab/modules.yaml
            # `tags.provides_capability`. The page must not know this by itself.
            "provides_capability": {"imaging_modes": [{"id": "sted", "display_label": "STED"}]},
            "publication_template": "The {label} {be} used.",
            "publication_label": "Easy3D STED module",
            "method_sentence": "The Easy3D STED module was used.",
            "review_prompts": [],
        }],
        "hardware": {
            "scanner": {"present": False},
            "objectives": [
                {"id": "obj-63", "display_label": "63x/1.4 Oil",
                 "publication_template": "Imaging was performed with {label}.",
                 "publication_label": "a 63x/1.4 Oil objective",
                 "method_sentence": "Imaging was performed with a 63x/1.4 Oil objective.",
                 "review_prompts": []},
                {"id": "obj-10", "display_label": "10x/0.3 Air",
                 "publication_template": "Imaging was performed with {label}.",
                 "publication_label": "a 10x/0.3 Air objective",
                 "method_sentence": "Imaging was performed with a 10x/0.3 Air objective.",
                 "review_prompts": []},
            ],
            "magnification_changers": [],
            "optical_modulators": [],
            "illumination_logic": [],
            "optical_path": {
                "hardware_inventory_renderables": [excitation, depletion, lamp, detector, bf_detector],
                "authoritative_route_contract": {"routes": routes},
            },
        },
    }


class AcquisitionScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        executable = shutil.which("chromium") or shutil.which("chromium-browser")
        cls.browser = cls.playwright.chromium.launch(**({"executable_path": executable} if executable else {}))
        cls.template = Environment(loader=FileSystemLoader(ROOT / "scripts/templates")).get_template("methods_generator.md.j2")
        cls.app = (ROOT / "assets/javascripts/methods_generator_app.js").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        html = self.template.render(methods_generator_config_json=json.dumps({
            "instrument_data_url": "/instruments.json", "acknowledgements": {"standard": ""}}))
        bootstrap = ("window.fetch = async () => ({ok: true, json: async () => ("
                     + json.dumps({"instruments": [instrument()]}) + ")});")
        html = html.replace('<script src="../assets/javascripts/methods_generator_app.js"></script>',
                            "<script>" + self.app + "</script>")
        self.page.set_content("<script>" + bootstrap + "</script>" + html)
        expect(self.page.locator("#system-select")).to_be_enabled()
        self.page.select_option("#system-select", "scope-scope-test")

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def output(self):
        return self.page.locator("#output-text").input_value()

    def method(self, label):
        return self.page.locator(f'#method-list input[data-display-label="{label}"]')

    # --- Critical: an entry states only what was selected for it ---------------

    def test_a_module_does_not_survive_into_the_next_acquisition(self):
        """STED with its 3D module, then a confocal reference: the
        reference image was not taken with the depletion module."""
        self.method("STED").check()
        self.page.check("#obj-0")
        self.page.check("#light-0")
        self.page.check("#light-1")
        self.page.check("#det-0")
        self.page.check("#module-0")
        self.page.fill("#session-label", "STED")
        self.page.click("#add-btn")
        self.assertIn("Easy3D STED module", self.output())

        self.method("Confocal point scanning").check()
        self.page.check("#obj-0")
        self.page.check("#light-0")
        self.page.check("#det-0")
        self.page.fill("#session-label", "confocal reference")
        self.page.click("#add-btn")
        reference = self.output().split("confocal reference")[-1]
        self.assertNotIn("Easy3D STED", reference)
        self.assertIn("Point-scanning confocal imaging was performed", reference)
        self.assertNotIn("Stimulated emission depletion", reference)

    def test_an_objective_does_not_survive_into_the_next_acquisition(self):
        """The overview objective is not the detail objective."""
        self.method("Transmitted brightfield").check()
        self.page.check("#obj-1")
        self.page.check("#light-0")
        self.page.check("#det-0")
        self.page.fill("#session-label", "overview")
        self.page.click("#add-btn")

        self.method("Confocal point scanning").check()
        self.page.check("#obj-0")
        self.page.check("#light-0")
        self.page.check("#det-0")
        self.page.fill("#session-label", "detail")
        self.page.click("#add-btn")
        detail = self.output().split("\ndetail\n")[-1]
        self.assertIn("63x/1.4 Oil objective", detail)
        self.assertNotIn("10x/0.3 Air objective", detail)

    # --- High: selections survive exactly as long as they are still offered ----

    def test_a_second_method_on_the_same_path_keeps_the_hardware_chosen(self):
        """Confocal and STED share one recorded path, so nothing about the path
        stops being true when the method changes."""
        self.method("Confocal point scanning").check()
        self.page.check("#light-0")
        self.page.check("#det-0")
        self.method("STED").check()
        expect(self.page.locator("#light-0")).to_be_checked()
        expect(self.page.locator("#det-0")).to_be_checked()
        self.page.click("#add-btn")
        self.assertIn("488 nm laser", self.output())
        self.assertIn("Avalanche photodiode", self.output())

    def test_hardware_only_the_old_method_reached_is_withdrawn(self):
        """Leaving the transmitted path withdraws its lamp."""
        self.method("Transmitted brightfield").check()
        self.page.check("#light-0")
        expect(self.page.locator("#light-0")).to_be_checked()
        self.method("Confocal point scanning").check()
        self.method("Transmitted brightfield").uncheck()
        self.assertEqual(self.page.locator('#light-list input:checked').count(), 0)
        self.page.click("#add-btn")
        self.assertNotIn("Halogen lamp", self.output())

    def test_two_methods_describe_one_acquisition_path_by_path(self):
        """Brightfield beside fluorescence is one image set, and the hardware of
        each path is described in its own clause."""
        self.method("Confocal point scanning").check()
        self.method("Transmitted brightfield").check()
        self.page.check("#obj-0")
        for index in range(self.page.locator('#light-list input[id^="light-"]').count()):
            self.page.locator('#light-list input[id^="light-"]').nth(index).check()
        for index in range(self.page.locator('#det-list input[id^="det-"]').count()):
            self.page.locator('#det-list input[id^="det-"]').nth(index).check()
        self.page.click("#add-btn")
        output = self.output()
        self.assertIn("Point-scanning confocal imaging and transmitted-light brightfield imaging were performed", output)
        self.assertIn("For the confocal point scanning images,", output)
        self.assertIn("For the transmitted brightfield images,", output)
        # Neither clause may claim the other path's illumination.
        confocal_clause = output.split("For the confocal point scanning images,")[1].split("For the")[0]
        self.assertNotIn("Halogen lamp", confocal_clause)

    # --- High: what the entry does not say, it asks about ----------------------

    def test_an_entry_without_a_detector_asks_for_one(self):
        """"""
        self.method("Confocal point scanning").check()
        self.page.check("#obj-0")
        self.page.check("#light-0")
        self.page.click("#add-btn")
        self.assertIn("[PLEASE SPECIFY: the detector, camera or eyepieces used", self.output())

    def test_an_entry_without_an_objective_or_illumination_asks_for_them(self):
        """"""
        self.method("Confocal point scanning").check()
        self.page.check("#det-0")
        self.page.click("#add-btn")
        self.assertIn("[PLEASE SPECIFY: the objective used for this acquisition", self.output())
        self.assertIn("[PLEASE SPECIFY: the illumination used for this acquisition", self.output())

    def test_sted_without_a_depletion_source_is_flagged(self):
        """The technique's defining beam is selectable, so its absence is a fact
        about the draft rather than about the microscope."""
        self.method("STED").check()
        self.page.check("#obj-0")
        self.page.check("#light-0")
        self.page.check("#det-0")
        self.page.click("#add-btn")
        # The role is named as the record spells it, because the question is
        # answered by looking at what the record calls that beam.
        self.assertIn("no source recorded as depletion was selected", self.output())

    def test_a_depletion_source_outside_sted_is_flagged(self):
        """The converse: a confocal acquisition reporting a depletion beam is either
        mis-ticked or mis-described."""
        self.method("Confocal point scanning").check()
        self.page.check("#obj-0")
        self.page.check("#light-1")
        self.page.check("#det-0")
        self.page.click("#add-btn")
        self.assertIn("a depletion source is reported", self.output())

    def test_a_module_outside_its_technique_is_flagged(self):
        """The Easy3D module belongs to STED; a confocal entry that reports it is
        asked to confirm the method."""
        self.method("Confocal point scanning").check()
        self.page.check("#obj-0")
        self.page.check("#light-0")
        self.page.check("#det-0")
        self.page.check("#module-0")
        self.page.click("#add-btn")
        self.assertIn("STED is not among the methods selected", self.output())

    # --- High: entry identity and the form's own state ------------------------

    def test_correcting_a_selection_updates_the_entry_instead_of_duplicating_it(self):
        """Noticing a forgotten checkbox is the most common correction."""
        self.method("Confocal point scanning").check()
        self.page.check("#obj-0")
        self.page.check("#light-0")
        self.page.check("#det-0")
        self.page.click("#add-btn")
        self.page.check("#confirmed-0")
        self.page.click("#add-btn")
        self.assertEqual(self.output().count("Point-scanning confocal imaging was performed"), 1)
        self.assertIn("Scope Acquire", self.output())

    def test_a_new_acquisition_reference_starts_from_a_clean_acquisition(self):
        """Naming a different figure is naming a different acquisition.

        The page says a new reference starts a separate entry, so the second entry
        must state what the author selects for it and nothing else. This test used
        to add the same selections twice and call that two acquisitions, which is
        the inheritance the audit found rather than a defence against it.
        """
        self.method("STED").check()
        self.page.check("#obj-0")
        self.page.check("#module-0")
        self.page.check("#light-0")
        self.page.check("#light-1")
        self.page.check("#det-0")
        self.page.check("#confirmed-0")
        self.page.fill("#session-label", "Figure 1")
        self.page.click("#add-btn")

        self.page.fill("#session-label", "Figure 2")
        # Everything describing the finished acquisition is released. The reference
        # the author is typing stays, and so does the imaging method - with it, the
        # one path that method is recorded on, which was never a question.
        for selector in ("#obj-list", "#module-list", "#light-list", "#det-list", "#confirmed-list"):
            self.assertEqual(self.page.locator(f"{selector} input:checked").count(), 0,
                             f"{selector} still describes the acquisition that was added")
        self.assertEqual(self.page.locator("#session-label").input_value(), "Figure 2")
        self.assertTrue(self.method("STED").is_checked())

        self.page.check("#obj-1")
        self.page.check("#light-0")
        self.page.check("#light-1")
        self.page.check("#det-0")
        self.page.click("#add-btn")

        output = self.output()
        self.assertIn("Figure 1", output)
        self.assertIn("Figure 2", output)
        second = output.split("Figure 2")[-1]
        self.assertIn("10x/0.3 Air", second)
        self.assertNotIn("63x/1.4 Oil", second)
        self.assertNotIn("Easy3D STED", second)

    def test_clear_all_resets_every_selection_as_well_as_the_draft(self):
        """"Start again" has to mean every control, confirmed actions included.

        Confirmed actions cover the acquisition software, the environmental control
        and the post-acquisition processing. A cleared draft that keeps them ticked
        republishes a processing step the next author never claimed.
        """
        self.method("Confocal point scanning").check()
        self.page.check("#obj-0")
        self.page.check("#light-0")
        self.page.check("#det-0")
        self.page.check("#confirmed-0")
        self.page.click("#add-btn")
        self.page.click("#clear-btn")
        self.assertEqual(self.page.locator("#hardware-options input:checked").count(), 0)
        self.assertEqual(self.page.locator("#confirmed-list input:checked").count(), 0)
        self.assertIn("Select an instrument", self.output())

    def test_start_another_acquisition_clears_the_previous_selections(self):
        """The explicit way to begin a different image set clears all of it."""
        self.method("STED").check()
        self.page.check("#obj-0")
        self.page.check("#module-0")
        self.page.check("#light-0")
        self.page.check("#det-0")
        self.page.check("#confirmed-0")
        self.page.click("#add-btn")
        self.page.click("#new-acquisition-btn")
        self.assertEqual(self.page.locator("#hardware-options input:checked").count(), 0)
        self.assertEqual(self.page.locator("#confirmed-list input:checked").count(), 0)
        self.assertEqual(self.page.locator("#session-label").input_value(), "")

    # --- Medium/Low: what may appear in publication prose ---------------------

    def test_generic_requests_are_stated_once_for_the_whole_section(self):
        """19 / 4.1. Specimen preparation is the same request every time."""
        self.method("Confocal point scanning").check()
        self.page.check("#obj-0")
        self.page.check("#light-0")
        self.page.check("#det-0")
        self.page.fill("#session-label", "one")
        self.page.click("#add-btn")
        self.method("Transmitted brightfield").check()
        self.page.check("#obj-1")
        self.page.check("#light-0")
        self.page.check("#det-0")
        self.page.fill("#session-label", "two")
        self.page.click("#add-btn")
        output = self.output()
        self.assertEqual(output.count("Specimen preparation metadata"), 1)
        self.assertIn("applies to every acquisition above", output)

if __name__ == "__main__":
    unittest.main()
