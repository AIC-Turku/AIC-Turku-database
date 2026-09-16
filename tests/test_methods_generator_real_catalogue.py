"""Methods Generator regressions driven by the real exported instrument catalogue.

Every other browser suite for this page builds its own synthetic instrument. That
is fast and precise, but it can only prove that the generator behaves correctly on
the record the test itself wrote. Four of the audit's Critical findings were
invisible to fixtures by construction:

* two real records sharing a manufacturer and model rendered under one name;
* a real record whose recorded camera identity is a placeholder;
* a real record whose detectors are not reachable from any recorded light path;
* implementation vocabulary reaching prose only for particular recorded labels.

These tests therefore load the catalogue the site actually ships - built by the
shared ``generated_dashboard`` fixture from the authored YAML - and drive the real
page against it. They assert on the instruments the audit named, and then sweep
every instrument and every method the catalogue offers for vocabulary that must
never appear in a manuscript.
"""

from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE_URL = "https://catalogue.test/instruments.json"

# Words that describe how this repository stores a microscope, not how a Methods
# section describes one. "Unknown" and "Placeholder" are how a record says it does
# not know something, which is a question for the author rather than a fact.
BANNED_IN_PROSE = (
    "route", "runtime", "DTO", "inventory", "selected execution",
    "wheel position", "turret position", "Unknown", "Placeholder",
    "other microscope", "compatibility", "hardware_inventory",
)


@pytest.fixture(scope="session")
def real_catalogue(generated_dashboard: Path) -> Path:
    """The instrument export the published page fetches, built from the YAML."""
    payload = generated_dashboard / "assets" / "instruments_data.json"
    assert payload.is_file(), (
        f"{payload} was not produced by the dashboard build; the real-catalogue "
        "regressions cannot run against a catalogue that does not exist."
    )
    return payload


@pytest.mark.usefixtures("real_catalogue")
class RealCatalogueTestCase(unittest.TestCase):
    """Drives the production page with the production catalogue."""

    catalogue_path: Path

    @pytest.fixture(autouse=True)
    def _bind_catalogue(self, real_catalogue: Path) -> None:
        type(self).catalogue_path = real_catalogue

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
        # The catalogue is tens of megabytes, so it is served to the page rather
        # than inlined into the document for every test.
        body = self.catalogue_path.read_bytes()
        # An absolute URL so the request is routable from a set_content document,
        # and served rather than inlined: the catalogue is tens of megabytes.
        self.page.route(
            CATALOGUE_URL,
            lambda route: route.fulfill(status=200, content_type="application/json", body=body),
        )
        html = self.template.render(methods_generator_config_json=json.dumps({
            "instrument_data_url": CATALOGUE_URL,
            "acknowledgements": {"standard": ""},
        }))
        html = html.replace(
            '<script src="../assets/javascripts/methods_generator_app.js"></script>',
            "<script>" + self.app + "</script>",
        )
        self.page.set_content("<script></script>" + html)
        self.page.wait_for_function("document.querySelectorAll('#system-select option').length > 1", timeout=30000)

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    # --- driving the page the way a user does --------------------------------

    def select_instrument(self, label: str) -> None:
        self.page.select_option("#system-select", label=label)

    def tick(self, section_id: str, pattern: str, nth: int = 0) -> str:
        """Tick the nth visible control in a section whose label matches."""
        matches = self.page.evaluate(
            """([sectionId, pattern]) => {
                const rx = new RegExp(pattern, "i");
                return [...document.querySelectorAll(`#${sectionId} input`)]
                    .filter(input => input.offsetParent !== null)
                    .map(input => ({id: input.id, label: (input.closest("label") || input.parentElement).textContent.trim()}))
                    .filter(entry => rx.test(entry.label));
            }""",
            [section_id, pattern],
        )
        self.assertTrue(matches, f"no visible control matching {pattern!r} in #{section_id}")
        self.page.check("#" + matches[nth]["id"])
        return matches[nth]["label"]

    def add(self) -> str:
        self.page.click("#add-btn")
        return self.page.locator("#output-text").input_value()

    def prose(self) -> str:
        return self.page.locator("#output-text").input_value().split("Review before publication")[0]

    # --- findings that only real records can show ----------------------------

    def test_two_records_sharing_a_model_are_named_apart(self):
        """Audit 1.3. Both 3i systems record manufacturer "3i / Zeiss" and model
        "Marianas CSU-W1 Spinning Disk Confocal"; only the display name tells them
        apart, so a section using both used to attribute one to the other."""
        self.select_instrument("3i CSU-W1 Spinning Disk")
        self.tick("method-list", "Confocal spinning disk")
        self.tick("obj-list", "63x/1.4 Oil")
        self.tick("light-list", "488 nm laser")
        self.tick("det-list", "ORCA-Flash4.0")
        self.page.fill("#session-label", "system A")
        self.add()

        self.select_instrument("3i Marianas CSU-W1 Spinning Disk Med C")
        self.tick("method-list", "Confocal spinning disk")
        self.tick("obj-list", "63x/1.4 NA Oil")
        self.tick("light-list", "488 nm laser")
        self.tick("det-list", "Prime BSI")
        self.page.fill("#session-label", "system B")
        output = self.add()

        self.assertIn("3i CSU-W1 Spinning Disk (", output)
        self.assertIn("3i Marianas CSU-W1 Spinning Disk Med C (", output)

    def test_a_recorded_placeholder_camera_is_not_published(self):
        """Audit 1.4. The Leica DM IRBE records its camera as Unknown/Unknown
        Camera, which is the record saying it does not know."""
        self.select_instrument("Leica DM IRBE")
        self.tick("method-list", "Widefield fluorescence")
        self.tick("obj-list", r"40x/0\.70")
        self.tick("light-list", "arc lamp")
        self.tick("filter-list", "Filter Cube EGFP")
        self.tick("det-list", "Unknown Camera")
        output = self.add()
        self.assertNotIn("Unknown Camera", output.split("Review before publication")[0])
        self.assertIn("the detector or camera used for this acquisition", output)

    def test_an_airyscan_entry_says_it_has_no_detector_to_report(self):
        """Audit 1.6 / ledger 3.3. The LSM 880 records an Airyscan detector, but no
        light path reaches it, so the correct answer is not tickable. The draft has
        to say that rather than publish an acquisition with no detection."""
        self.select_instrument("Zeiss LSM 880 with AiryScan")
        self.tick("method-list", r"ISM \(AiryScan\)")
        self.tick("obj-list", "C-Plan-APOCHROMAT 63x")
        self.tick("light-list", "488 nm laser")
        self.tick("module-list", "AiryScan Detector")
        output = self.add()
        self.assertIn("Image scanning microscopy (ISM; Airyscan) was performed", output)
        self.assertIn("[PLEASE SPECIFY: the detector, camera or eyepieces used", output)

    def test_a_module_does_not_survive_into_the_next_real_acquisition(self):
        """Audit 1.1. Airyscan then DIC on the real LSM 880 record."""
        self.select_instrument("Zeiss LSM 880 with AiryScan")
        self.tick("method-list", r"ISM \(AiryScan\)")
        self.tick("obj-list", "C-Plan-APOCHROMAT 63x")
        self.tick("light-list", "488 nm laser")
        self.tick("module-list", "AiryScan Detector")
        self.page.fill("#session-label", "Airyscan")
        self.add()

        self.tick("method-list", "^DIC$")
        self.tick("obj-list", "LD LCI Plan APOCHROMAT 40x")
        self.tick("light-list", "halogen lamp")
        self.tick("det-list", "Transmitted light PMT")
        self.page.fill("#session-label", "DIC")
        output = self.add()

        dic_entry = output.split("\nDIC\n")[-1]
        self.assertIn("Differential interference contrast (DIC) imaging was performed", dic_entry)
        self.assertNotIn("AiryScan Detector/Module", dic_entry)

    def test_a_same_path_method_change_keeps_real_hardware(self):
        """Audit 1.5. On the real Zeiss TIRF record, widefield and TIRF are the same
        recorded path, so nothing about the path stops being true."""
        self.select_instrument("Zeiss TIRF")
        self.tick("method-list", "Widefield fluorescence")
        self.tick("obj-list", r"63x/1\.46")
        self.tick("light-list", "561 nm laser")
        self.tick("filter-list", "Filter set 43 HE")
        self.tick("det-list", "ORCA-Flash4.0 CMOS")
        self.tick("method-list", "^TIRF$")
        output = self.add()
        self.assertIn("561 nm laser", output)
        self.assertIn("ORCA-Flash4.0 CMOS", output)
        self.assertIn("Filter set 43 HE", output)

    def test_the_legacy_multiphoton_record_names_its_method(self):
        """Audit 1.7. The retired SP5 has no imaging-method control, so the method
        has to come from the path it records."""
        self.select_instrument("Leica TCS SP5 Multiphoton (Retired)")
        self.tick("obj-list", r"25x/0\.95")
        self.tick("light-list", "Chameleon Ultra II")
        self.tick("det-list", "NDD PMT")
        output = self.add()
        self.assertIn("Multiphoton imaging was performed", output)
        self.assertNotIn(" route", output.split("Review before publication")[0])

    def test_duplicate_cameras_are_told_apart_by_their_recorded_port(self):
        """Audit 1.11. The Crest V3 records two cameras under one model name; the
        recorded branch labels are what distinguishes them."""
        self.select_instrument("Nikon Ti2-E Crest V3")
        self.tick("method-list", "Confocal spinning disk")
        self.tick("obj-list", "60XC Sil")
        self.tick("light-list", "476 nm laser")
        self.tick("det-list", "Photometrics Kinetix", nth=0)
        self.tick("det-list", "Photometrics Kinetix", nth=1)
        output = self.add()
        self.assertEqual(output.count("Photometrics Kinetix"), 2)
        self.assertIn("master", output.lower())
        self.assertIn("slave", output.lower())

    def test_real_filter_positions_publish_their_recorded_transmission(self):
        """Audit 4.2. The bands come from the spectral model the repository already
        derives, so the draft states what a filter passes and not only its
        catalogue number."""
        self.select_instrument("3i CSU-W1 Spinning Disk")
        self.tick("method-list", "Confocal spinning disk")
        self.tick("obj-list", "63x/1.4 Oil")
        self.tick("light-list", "488 nm laser")
        self.tick("light-list", "561 nm laser")
        self.tick("filter-list", "^GFP$")
        self.tick("filter-list", "Cy3 / Alexa 568")
        self.tick("det-list", "ORCA-Flash4.0")
        output = self.add()
        self.assertIn("525/50 nm", output)
        self.assertIn("617/73 nm", output)
        # Both filters of one wheel are named in a single clause.
        self.assertEqual(output.count("in the CSU-W1 Emission Wheel"), 1)
        self.assertIn("state which filter was used for which channel", output)

    # --- the sweep no fixture can replace ------------------------------------

    def test_no_implementation_vocabulary_in_any_entry_of_the_real_catalogue(self):
        """Audit 1.13. Every instrument, every method it offers, one entry each.

        A fixture can only prove this for the labels the fixture invented. This
        proves it for every label the facility has actually authored, which is where
        "Unknown Camera", "other microscope" and "position EMP_BF" came from.
        """
        findings = self.page.evaluate(
            """(banned) => {
                const wait = () => new Promise(resolve => setTimeout(resolve, 0));
                const visible = selector => [...document.querySelectorAll(selector)]
                    .filter(input => input.offsetParent !== null);
                const fire = (input, checked) => {
                    if (input.checked === checked) return;
                    input.checked = checked;
                    input.dispatchEvent(new Event("change", {bubbles: true}));
                };
                return (async () => {
                    const problems = [];
                    const select = document.getElementById("system-select");
                    const options = [...select.options].filter(option => option.value);
                    for (const option of options) {
                        select.value = option.value;
                        select.dispatchEvent(new Event("change", {bubbles: true}));
                        await wait();
                        const methods = visible('#method-list input');
                        const methodValues = methods.length ? methods.map(m => m.value) : [null];
                        for (const methodValue of methodValues) {
                            document.getElementById("clear-btn").click();
                            await wait();
                            select.value = option.value;
                            select.dispatchEvent(new Event("change", {bubbles: true}));
                            await wait();
                            if (methodValue !== null) {
                                const method = visible('#method-list input')
                                    .find(input => input.value === methodValue);
                                if (!method) continue;
                                fire(method, true);
                                await wait();
                            }
                            // One of everything the instrument offers on this path,
                            // which is the widest prose a single entry can produce.
                            for (const section of ["obj-list", "light-list", "filter-list",
                                                   "splitter-list", "det-list", "module-list",
                                                   "scanner-list", "magnification-changer-list",
                                                   "optical-modulator-list", "illumination-logic-list",
                                                   "confirmed-list"]) {
                                const inputs = visible(`#${section} input`);
                                if (inputs.length) fire(inputs[0], true);
                                await wait();
                            }
                            document.getElementById("add-btn").click();
                            await wait();
                            const output = document.getElementById("output-text").value;
                            const prose = output.split("Review before publication")[0];
                            for (const word of banned) {
                                if (new RegExp(`\\\\b${word.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\\\$&")}\\\\b`).test(prose)) {
                                    problems.push({
                                        instrument: option.textContent.trim(),
                                        method: methodValue,
                                        word,
                                        prose: prose.slice(0, 400),
                                    });
                                }
                            }
                        }
                    }
                    return problems;
                })();
            }""",
            list(BANNED_IN_PROSE),
        )
        self.assertEqual(
            findings, [],
            "publication prose in the real catalogue contains repository vocabulary:\n"
            + "\n".join(
                f"  {f['instrument']} / {f['method']}: {f['word']!r} in {f['prose']!r}"
                for f in findings
            ),
        )


if __name__ == "__main__":
    unittest.main()
