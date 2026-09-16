"""Browser regressions for the method-first Methods Generator workflow."""

import json
import shutil
import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def instrument():
    laser = {
        "id": "source:tirf",
        "display_label": "488 nm laser",
        "publication_label": "488 nm laser",
        "inventory_class": "light_source",
        "publication_template": "Excitation was provided by {label}.",
        "method_sentence": "Excitation was provided by 488 nm laser.",
        "review_prompts": [],
    }
    lamp = {
        "id": "source:bf",
        "display_label": "Transmitted lamp",
        "publication_label": "Transmitted lamp",
        "inventory_class": "light_source",
        "publication_template": "Transmitted-light illumination was provided by {label}.",
        "method_sentence": "Transmitted-light illumination was provided by Transmitted lamp.",
        "review_prompts": [],
    }
    holder = {
        "id": "element:cubes",
        "display_label": "Filter turret",
        "publication_label": "Filter turret",
        "inventory_class": "optical_element",
        "publication_template": "The light path included {label}.",
        "method_sentence": "The light path included Filter turret.",
        "review_prompts": [],
        "selectable_positions": [
            {
                "id": "gfp",
                "display_label": "GFP cube",
                "product_code": "49002",
                "component_type": "filter_cube",
                "selection_mode": "exclusive",
                "route_ids": ["widefield"],
                "route_labels": ["Widefield fluorescence"],
            },
            {
                "id": "rfp",
                "display_label": "RFP cube",
                "product_code": "49005",
                "component_type": "filter_cube",
                "selection_mode": "exclusive",
                "route_ids": ["widefield"],
                "route_labels": ["Widefield fluorescence"],
            },
        ],
    }
    camera_a = {
        "id": "endpoint:camera-a",
        "display_label": "Camera A",
        "publication_label": "Camera A",
        "inventory_class": "endpoint",
        "publication_template": "Images were recorded using {label}.",
        "method_sentence": "Images were recorded using Camera A.",
        "review_prompts": [],
    }
    camera_b = {
        "id": "endpoint:camera-b",
        "display_label": "Camera B",
        "publication_label": "Camera B",
        "inventory_class": "endpoint",
        "publication_template": "Images were recorded using {label}.",
        "method_sentence": "Images were recorded using Camera B.",
        "review_prompts": [],
    }
    brightfield_camera = {
        "id": "endpoint:bf-camera",
        "display_label": "Brightfield camera",
        "publication_label": "Brightfield camera",
        "inventory_class": "endpoint",
        "publication_template": "Images were recorded using {label}.",
        "method_sentence": "Images were recorded using Brightfield camera.",
        "review_prompts": [],
    }
    routes = [
        {
            "id": "widefield",
            "display_label": "Widefield fluorescence",
            "route_type": "widefield_fluorescence",
            "route_type_label": "Widefield Fluorescence",
            "route_identity": {
                "imaging_modes": [{"id": "tirf", "display_label": "TIRF"}],
                "contrast_methods": [],
                "readouts": [],
            },
            "relevant_hardware": {
                "sources": [laser],
                "filters": [holder],
                "splitters": [],
                "endpoints": [camera_a, camera_b],
            },
            "branch_summary": {
                "branches": [
                    {
                        "block_id": "camera-selector",
                        "selection_mode": "exclusive",
                        "branch_id": "a",
                        "label": "Camera A",
                        "endpoint_inventory_ids": ["endpoint:camera-a"],
                    },
                    {
                        "block_id": "camera-selector",
                        "selection_mode": "exclusive",
                        "branch_id": "b",
                        "label": "Camera B",
                        "endpoint_inventory_ids": ["endpoint:camera-b"],
                    },
                ]
            },
        },
        {
            "id": "transmitted",
            "display_label": "Transmitted light",
            "route_type": "transmitted_light",
            "route_type_label": "Transmitted Light",
            "route_identity": {
                "imaging_modes": [],
                "contrast_methods": [{"id": "transmitted_brightfield", "display_label": "Transmitted Brightfield"}],
                "readouts": [],
            },
            "relevant_hardware": {
                "sources": [lamp],
                "filters": [],
                "splitters": [],
                "endpoints": [brightfield_camera],
            },
            "branch_summary": {"branches": []},
        },
        {
            "id": "unmapped-service-path",
            "display_label": "Unmapped service path",
            "route_type": "widefield_fluorescence",
            "route_type_label": "Widefield Fluorescence",
            "route_identity": {
                "imaging_modes": [],
                "contrast_methods": [],
                "readouts": [],
            },
            "relevant_hardware": {
                "sources": [], "filters": [], "splitters": [], "endpoints": [],
            },
            "branch_summary": {"branches": []},
        },
    ]
    return {
        "id": "scope-method-first",
        "display_name": "Method First Scope",
        "methods_generation": {"is_blocked": False, "blockers": []},
        "methods": {"base_sentence": "Images were acquired using the Method First Scope."},
        "software": [],
        "modalities": [],
        "modules": [],
        "hardware": {
            "scanner": {"present": False},
            "objectives": [],
            "magnification_changers": [],
            "optical_modulators": [],
            "illumination_logic": [],
            "optical_path": {
                "hardware_inventory_renderables": [laser, lamp, holder, camera_a, camera_b, brightfield_camera],
                "authoritative_route_contract": {"routes": routes},
            },
        },
    }


class MethodFirstMethodsTests(unittest.TestCase):
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
            "instrument_data_url": "/instruments.json",
            "acknowledgements": {"standard": ""},
        }))
        bootstrap = (
            "window.fetch = async () => ({ok: true, json: async () => ("
            + json.dumps({"instruments": [instrument()]})
            + ")});"
        )
        html = html.replace(
            '<script src="../assets/javascripts/methods_generator_app.js"></script>',
            "<script>" + self.app + "</script>",
        )
        self.page.set_content("<script>" + bootstrap + "</script>" + html)
        expect(self.page.locator("#system-select")).to_be_enabled()
        self.page.select_option("#system-select", "scope-method-first")

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def output(self):
        return self.page.locator("#output-text").input_value()

    def test_unmapped_route_does_not_become_an_inferred_method(self):
        methods = self.page.locator('#method-list input[data-category="method"]')
        self.assertEqual(methods.count(), 2)
        expect(self.page.locator("#method-list")).not_to_contain_text("Unmapped service path")

    def test_method_first_selection_reveals_only_compatible_route_hardware(self):
        expect(self.page.locator("#section-method")).to_be_visible()
        expect(self.page.locator("#section-route")).to_be_visible()
        expect(self.page.locator("#section-light")).to_be_hidden()
        self.page.check("#method-0")
        expect(self.page.locator("#route-0")).to_be_checked()
        expect(self.page.locator("#section-light")).to_be_visible()
        expect(self.page.locator("#light-list")).to_contain_text("488 nm laser")
        expect(self.page.locator("#light-list")).not_to_contain_text("Transmitted lamp")
        self.page.check("#light-0")
        self.page.click("#add-btn")
        self.assertIn("TIRF imaging was performed using the Method First Scope.", self.output())
        self.assertIn("488 nm laser", self.output())

    def test_exclusive_detector_branches_and_filter_positions_use_radio_controls(self):
        self.page.check("#method-0")
        detectors = self.page.locator('#det-list input[id^="det-"]')
        self.assertEqual(detectors.count(), 2)
        self.assertEqual(detectors.nth(0).get_attribute("type"), "radio")
        self.assertEqual(detectors.nth(1).get_attribute("type"), "radio")
        detectors.nth(0).check()
        detectors.nth(1).check()
        expect(detectors.nth(0)).not_to_be_checked()
        expect(detectors.nth(1)).to_be_checked()

        positions = self.page.locator('#filter-list input[id^="filterposition-"]')
        self.assertEqual(positions.count(), 2)
        self.assertEqual(positions.nth(0).get_attribute("type"), "radio")
        positions.nth(0).check()
        positions.nth(1).check()
        expect(positions.nth(0)).not_to_be_checked()
        expect(positions.nth(1)).to_be_checked()

    def test_switching_method_clears_off_route_position_and_hides_old_hardware(self):
        self.page.check("#method-0")
        self.page.locator('#filter-list input[id^="filterposition-"]').nth(0).check()
        self.page.check("#method-1")
        expect(self.page.locator("#route-1")).to_be_checked()
        expect(self.page.locator("#light-list")).to_contain_text("Transmitted lamp")
        expect(self.page.locator("#light-list")).not_to_contain_text("488 nm laser")
        expect(self.page.locator("#methods-selection-status")).to_contain_text("cleared because it is not available")

    def test_internal_compatibility_marker_is_not_emitted(self):
        self.page.check("#method-0")
        self.page.click("#add-btn")
        self.assertNotIn("(Compatibility)", self.output())


if __name__ == "__main__":
    unittest.main()
