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

    def method_input(self, label: str) -> str:
        """The selector for the method checkbox with exactly this recorded label."""
        matches = self.page.evaluate(
            """(label) => [...document.querySelectorAll('#method-list input')]
                 .filter(input => input.dataset.displayLabel === label)
                 .map(input => "#" + input.id)""",
            label,
        )
        self.assertEqual(len(matches), 1, f"expected one method labelled {label!r}, got {matches}")
        return matches[0]

    def add(self) -> str:
        self.page.click("#add-btn")
        return self.page.locator("#output-text").input_value()

    def prose(self) -> str:
        return self.page.locator("#output-text").input_value().split("Review before publication")[0]

    def test_one_global_role_serves_both_techniques_that_share_a_beam(self):
        """The Abberior's two depletion beams serve STED and RESOLFT alike.

        `hardware.sources[].role` is instrument-global by decision: the role says
        the beam depletes, and the method says by which mechanism. That only holds
        while no sentence built from the role names a mechanism, so both halves are
        pinned here - the STED paragraph and the RESOLFT paragraph are built from
        the same recorded role, and neither may claim stimulated emission.
        """
        self.select_instrument("Abberior STED")
        for method_label in ("STED", "RESOLFT"):
            with self.subTest(method=method_label):
                self.page.click("#clear-btn")
                self.page.check(self.method_input(method_label))
                self.tick("obj-list", ".")
                self.tick("light-list", "485")
                self.tick("light-list", "775")
                prose = self.add().split("Review before publication")[0]
                self.assertIn(method_label, prose)
                self.assertIn("Depletion was provided by", prose)
                self.assertNotIn("Stimulated-emission", prose)
                self.assertNotIn("STED depletion", prose)

    def test_resolft_asks_for_its_depletion_beam_just_as_sted_does(self):
        """Both techniques need the beam, so both are asked for it.

        The browser table this replaced required a depletion source for STED only,
        so a RESOLFT acquisition that named no depletion beam was published without
        a word about the beam that makes it RESOLFT.
        """
        self.select_instrument("Abberior STED")
        for method_label in ("STED", "RESOLFT"):
            with self.subTest(method=method_label):
                self.page.click("#clear-btn")
                self.page.check(self.method_input(method_label))
                self.tick("obj-list", ".")
                self.tick("light-list", "485")
                output = self.add()
                self.assertIn("no source recorded as depletion was selected", output)

    def test_a_depletion_beam_is_not_counted_as_an_imaging_channel(self):
        """Its role says it shapes the spot rather than forming a channel."""
        self.select_instrument("Abberior STED")
        self.page.check(self.method_input("STED"))
        self.tick("obj-list", ".")
        self.tick("light-list", "485")
        self.tick("light-list", "775")
        self.tick("det-list", ".")
        output = self.add()
        self.assertNotIn("sequentially or simultaneously", output)

    # --- configurations the record says the instrument cannot produce ----------

    def test_a_brightfield_acquisition_is_not_offered_fluorescence_filters(self):
        """The BC43 records its emission wheel on the transmitted path too.

        Every position in that wheel is a fluorescence bandpass and none is open,
        so a brightfield acquisition could not have used any of them. The page used
        to offer all four and let a draft state "the light path included a mCherry
        emission bandpass filter (600/50 nm)" in a transmitted-light paragraph, and
        to ask which of them was used - a question with no correct answer.
        """
        self.select_instrument("Andor BC43 Benchtop Confocal")
        self.tick("method-list", "brightfield")
        offered = self.page.evaluate(
            """() => [...document.querySelectorAll('input[id^="filterposition-"]')]
                 .map(input => input.dataset.displayLabel)"""
        )
        self.assertEqual(offered, [], f"fluorescence positions offered on a brightfield path: {offered}")

        self.tick("obj-list", ".")
        output = self.add()
        self.assertNotIn("mCherry", output)
        self.assertNotIn("which position of the BC43 Internal Emission Filters", output)

    def test_a_source_that_cannot_pass_the_selected_filter_is_questioned(self):
        """Each EVOS light cube carries its own LED.

        Pairing the 470 nm GFP cube's LED with the Cy5 cube is a configuration the
        instrument cannot produce, and the draft reported both without comment.
        """
        self.select_instrument("EVOS fl")
        self.tick("method-list", "idefield")
        self.tick("light-list", "470 nm")
        self.tick("filter-list", "Cy5")
        self.tick("obj-list", ".")
        output = self.add()
        self.assertIn("does not pass that wavelength", output)

    def test_a_source_the_selected_filter_passes_is_not_questioned(self):
        """The check has to stay silent on the pairing the instrument is for."""
        self.select_instrument("EVOS fl")
        self.tick("method-list", "idefield")
        self.tick("light-list", "470 nm")
        self.tick("filter-list", "GFP/Alexa 488")
        self.tick("obj-list", ".")
        output = self.add()
        self.assertNotIn("does not pass", output)

    def test_a_simultaneous_splitter_with_one_detector_asks_about_the_other_branch(self):
        """A DualCam set feeds two cameras at once; one may still be unused."""
        self.select_instrument("Nikon Ti2-E Crest V3")
        self.tick("method-list", "onfocal spinning")
        self.tick("obj-list", ".")
        self.tick("light-list", ".")
        self.tick("splitter-list", "DualCam-GFP")
        self.page.check("#det-0")
        output = self.add()
        self.assertIn("feeds 2 branches at once", output)

    def test_an_exclusive_port_selector_raises_no_branch_question(self):
        """Choosing one branch of a selector is its normal use, not a gap."""
        self.select_instrument("Nikon Ti2-E Crest V3")
        self.tick("method-list", "onfocal spinning")
        self.tick("obj-list", ".")
        self.tick("light-list", ".")
        self.tick("splitter-list", "Trinocular Port")
        self.page.check("#det-0")
        output = self.add()
        self.assertNotIn("branches at once", output)

    def test_a_reported_software_version_is_not_also_reported_as_missing(self):
        """The draft stated a version and denied having one in the same breath.

        The instrument-level note fired because a different row - the analysis
        package - had no version. Each reported software fact now asks for what it
        is missing, by name.
        """
        self.select_instrument("Andor BC43 Benchtop Confocal")
        self.tick("method-list", "brightfield")
        self.tick("obj-list", ".")
        output = self.add()
        self.assertIn("Fusion BC43 (v2.7.0)", output)
        self.assertNotIn("Software version is not recorded", output)

    def test_a_single_recorded_acquisition_software_is_reported_without_confirmation(self):
        """One recorded row could not have produced an image any other way.

        The BC43 has exactly one row with role: acquisition, and stating it used
        to require ticking a checkbox that asked, in effect, whether the only
        software this stand has was used to acquire the image. It reports itself
        now, the way a sole recorded light path or objective already did, and the
        checkbox is gone rather than pre-ticked: there is nothing left to confirm.
        """
        self.select_instrument("Andor BC43 Benchtop Confocal")
        self.tick("method-list", "brightfield")
        confirmable = self.page.evaluate(
            """() => [...document.querySelectorAll('#confirmed-list input')]
                 .map(input => (input.closest('label') || input.parentElement).textContent)"""
        )
        self.assertFalse(
            any("Fusion BC43" in label for label in confirmable),
            f"a single recorded acquisition software must not be offered as a checkbox: {confirmable}",
        )
        self.tick("obj-list", ".")
        output = self.add()
        self.assertIn(
            "Instrument control and image acquisition were performed using Fusion BC43 (v2.7.0).",
            output,
        )

    def test_several_recorded_acquisition_software_rows_still_ask_which_were_used(self):
        """Five LAS X modules is a real choice; reporting all five would not be true.

        Unlike a stand with one control package, the STELLARIS records five rows
        under role: acquisition. Which of them this acquisition actually used is
        not implied by the record, so each still requires an explicit tick.
        """
        self.select_instrument("Leica STELLARIS 8 FALCON FLIM")
        self.tick("method-list", "Confocal point")
        self.tick("obj-list", ".")
        unconfirmed = self.add()
        self.assertNotIn("Instrument control and image acquisition", unconfirmed)

        self.tick("confirmed-list", "STELLARIS Control")
        confirmed = self.add()
        self.assertIn(
            "Instrument control and image acquisition were performed using "
            "LAS X STELLARIS Control Software.",
            confirmed,
        )
        self.assertNotIn("Dye Finder", confirmed)

    def test_a_reported_package_with_no_version_is_asked_for_by_name(self):
        self.select_instrument("Andor BC43 Benchtop Confocal")
        self.tick("method-list", "brightfield")
        self.tick("obj-list", ".")
        self.tick("confirmed-list", "Imaris")
        output = self.add()
        self.assertIn("[PLEASE SPECIFY: the version of Imaris Quant used]", output)

    def test_a_module_is_withdrawn_when_its_technique_is_deselected(self):
        """A draft must not state a module as fact and warn about it as well.

        Swapping STED for RESOLFT keeps the path and its hardware - that round trip
        is what the same-path preservation exists for - but the depletion module
        belongs to STED, and the record says so.
        """
        self.select_instrument("Abberior STED")
        sted = self.method_input("STED")
        resolft = self.method_input("RESOLFT")
        self.page.check(sted)
        self.tick("module-list", "Easy3D")
        self.assertEqual(self.page.locator("#module-list input:checked").count(), 1)

        self.page.uncheck(sted)
        self.page.check(resolft)
        self.assertEqual(self.page.locator("#module-list input:checked").count(), 0,
                         "a STED module survived into an acquisition claiming no STED")

        self.tick("obj-list", ".")
        self.tick("light-list", "485")
        output = self.add()
        self.assertNotIn("Easy3D STED module", output.split("Review before publication")[0])

    def test_a_module_re_ticked_deliberately_is_reported_with_its_warning(self):
        """Re-ticking is how an author states a use the record does not anticipate."""
        self.select_instrument("Abberior STED")
        self.page.check(self.method_input("RESOLFT"))
        self.tick("module-list", "Easy3D")
        self.tick("obj-list", ".")
        self.tick("light-list", "485")
        output = self.add()
        self.assertIn("Easy3D STED module", output.split("Review before publication")[0])
        self.assertIn("STED is not among the methods selected", output)

    # --- findings that only real records can show ----------------------------

    def test_two_records_sharing_a_model_are_named_apart(self):
        """Both 3i systems record manufacturer "3i / Zeiss" and model
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
        """The Leica DM IRBE records its camera as Unknown/Unknown
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

    def test_airyscan_detector_and_filter_are_reachable_on_the_real_lsm880(self):
        """First-generation Airyscan hardware must be selectable and publishable."""
        self.select_instrument("Zeiss LSM 880 with AiryScan")
        self.tick("method-list", r"ISM \(AiryScan\)")
        self.tick("obj-list", "C-Plan-APOCHROMAT 63x")
        self.tick("light-list", "488 nm laser")
        self.tick("module-list", "AiryScan Detector")
        self.tick("det-list", "Airyscan first-generation 32-element GaAsP detector")
        self.tick("filter-list", "AiryScan Emission Wheel")
        self.tick("filter-list", "BP 465-505 + LP 525")
        output = self.add()
        self.assertIn("Image scanning microscopy (ISM; Airyscan) was performed", output)
        self.assertIn("Airyscan first-generation 32-element GaAsP detector", output)
        self.assertIn("BP 465-505 + LP 525", output)
        self.assertNotIn("[PLEASE SPECIFY: the detector, camera or eyepieces used", output)

    def test_a_module_does_not_survive_into_the_next_real_acquisition(self):
        """Airyscan then DIC on the real LSM 880 record."""
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
        """On the real Zeiss TIRF record, widefield and TIRF are the same recorded
        path, so nothing about the path stops being true when the method changes."""
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
        """The retired SP5 has no imaging-method control, so the method has to come
        from the path it records."""
        self.select_instrument("Leica TCS SP5 Multiphoton (Retired)")
        self.tick("obj-list", r"25x/0\.95")
        self.tick("light-list", "Chameleon Ultra II")
        self.tick("det-list", "NDD PMT")
        output = self.add()
        self.assertIn("Multiphoton imaging was performed", output)
        self.assertNotIn(" route", output.split("Review before publication")[0])

    def test_duplicate_cameras_are_told_apart_by_their_recorded_port(self):
        """The Crest V3 records two cameras under one model name; the
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

    def test_3i_confocal_camera_selection_scopes_branch_local_filter_wheel(self):
        """ORCA and Evolve are exclusive camera branches with different emission wheels."""
        self.select_instrument("3i CSU-W1 Spinning Disk")
        self.tick("method-list", "Confocal spinning disk")
        self.tick("light-list", "730 nm laser")

        self.tick("det-list", "ORCA-Flash4.0")
        filter_text = self.page.locator("#filter-list").inner_text()
        self.assertIn("CSU-W Filter Wheel 1 (ORCA path)", filter_text)
        self.assertNotIn("CSU-W Filter Wheel 2 (Evolve path)", filter_text)
        self.assertIn("Alexa 750", filter_text)

        self.tick("det-list", "Photometrics Evolve")
        filter_text = self.page.locator("#filter-list").inner_text()
        self.assertNotIn("CSU-W Filter Wheel 1 (ORCA path)", filter_text)
        self.assertIn("CSU-W Filter Wheel 2 (Evolve path)", filter_text)
        self.assertIn("Alexa 750", filter_text)

    def test_3i_source_selection_scopes_recorded_confocal_positions(self):
        """The recorded SlideBook states tie VIS lines to turret 1 and 730 nm to turret 2."""
        self.select_instrument("3i CSU-W1 Spinning Disk")
        self.tick("method-list", "Confocal spinning disk")
        self.tick("light-list", "488 nm laser")
        self.tick("det-list", "ORCA-Flash4.0")

        text = self.page.locator("#filter-list").inner_text()
        self.assertIn("VIS quad-band confocal dichroic", text)
        self.assertNotIn("NIR short-pass confocal dichroic", text)
        self.assertIn("GFP", text)
        self.assertNotIn("Alexa 750", text)

        # Start a clean 730-nm acquisition so the compatibility check is not
        # broadened by retaining the 488-nm source as a second channel.
        self.page.click("#clear-btn")
        self.page.check(self.method_input("Confocal spinning disk"))
        self.tick("light-list", "730 nm laser")
        self.tick("det-list", "ORCA-Flash4.0")
        text = self.page.locator("#filter-list").inner_text()
        self.assertNotIn("VIS quad-band confocal dichroic", text)
        self.assertIn("NIR short-pass confocal dichroic", text)
        self.assertNotIn("GFP", text)
        self.assertIn("Alexa 750", text)

    def test_3i_partial_evolve_wheel_does_not_imply_alexa750_for_visible_acquisition(self):
        """One documented slot on the six-position Evolve wheel is not a fixed filter."""
        self.select_instrument("3i CSU-W1 Spinning Disk")
        self.tick("method-list", "Confocal spinning disk")
        self.tick("light-list", "488 nm laser")
        self.tick("det-list", "Photometrics Evolve")

        text = self.page.locator("#filter-list").inner_text()
        self.assertIn("CSU-W Filter Wheel 2 (Evolve path)", text)
        self.assertNotIn("Alexa 750", text)
        # The holder is present because the branch traverses it, but no known
        # visible-light position is invented from wheel 1.
        self.assertNotIn("GFP", text)

    def test_real_filter_positions_publish_their_recorded_transmission(self):
        """The bands come from the spectral model the repository already derives, so
        the draft states what a filter passes and not only its catalogue number."""
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
        self.assertEqual(output.count("in the CSU-W Filter Wheel 1 (ORCA path)"), 1)
        self.assertIn("state which filter was used for which channel", output)

    # --- the sweep no fixture can replace ------------------------------------

    def test_no_implementation_vocabulary_in_any_entry_of_the_real_catalogue(self):
        """Every instrument, every method it offers, one entry each.

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

    # --- the light-path checkbox: real work only, never a repeat of the method ---

    def test_the_light_path_section_never_appears_for_a_real_instrument_or_method(self):
        """No method in the real catalogue is recorded on more than one path.

        A path is a real question only when the method the user selected is
        recorded on two or more physically different implementations, which
        happens nowhere in this catalogue. Before this fix "Light path and
        readouts" showed up, already ticked, for every method of every
        instrument - a section a user could not act on because it repeated
        what they had just told the generator by picking the method.
        """
        findings = self.page.evaluate(
            """() => {
                const wait = () => new Promise(resolve => setTimeout(resolve, 0));
                const visible = selector => [...document.querySelectorAll(selector)]
                    .filter(input => input.offsetParent !== null);
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
                        // A record with no imaging-method control (methodValue === null)
                        // has nothing else to state the path with, so the section
                        // showing there - with the path already confirmed - is
                        // correct rather than the redundancy this test checks for.
                        if (!methodValues.some(value => value !== null)) continue;
                        for (const methodValue of methodValues) {
                            if (methodValue === null) continue;
                            document.getElementById("clear-btn").click();
                            await wait();
                            select.value = option.value;
                            select.dispatchEvent(new Event("change", {bubbles: true}));
                            await wait();
                            const method = visible('#method-list input')
                                .find(input => input.value === methodValue);
                            if (!method) continue;
                            method.checked = true;
                            method.dispatchEvent(new Event("change", {bubbles: true}));
                            await wait();
                            const section = document.getElementById("section-route");
                            if (section && section.offsetParent !== null) {
                                problems.push({
                                    instrument: option.textContent.trim(),
                                    method: methodValue,
                                });
                            }
                        }
                    }
                    return problems;
                })();
            }"""
        )
        self.assertEqual(
            findings, [],
            "the light-path section appeared for a method recorded on exactly one "
            "path, which is never a real question:\n"
            + "\n".join(f"  {f['instrument']} / {f['method']}" for f in findings),
        )

    def test_unchecking_the_only_method_leaves_no_light_path_confirmed(self):
        """A path confirmed for a method must not survive the method's removal.

        The light path is hidden, not removed, while its method is checked: it
        still exists in the page and is still marked as confirmed. Unchecking
        the method that justified it used to leave that stale "yes" behind,
        with nothing left to explain it and no visible control to notice or
        correct it.
        """
        self.select_instrument("Andor BC43 Benchtop Confocal")
        self.tick("method-list", "Confocal spinning")
        checked_before = self.page.evaluate(
            "() => [...document.querySelectorAll('#route-list input')]"
            ".filter(i => i.checked).map(i => i.id)"
        )
        self.assertTrue(checked_before, "expected the sole path to be confirmed automatically")

        method_id = self.page.evaluate(
            "() => [...document.querySelectorAll('#method-list input')].find(i => i.checked).id"
        )
        self.page.uncheck("#" + method_id)
        checked_after = self.page.evaluate(
            "() => [...document.querySelectorAll('#route-list input')]"
            ".filter(i => i.checked).map(i => i.id)"
        )
        self.assertEqual(checked_after, [], "a path survived the method that implied it being unchecked")

    def test_add_is_never_blocked_by_the_light_path_for_a_real_instrument(self):
        """Nothing the user cannot see or reach may be a precondition for Add.

        A path confirmed for an unambiguous method is hidden by design; Add must
        never ask the user to act on a control that is not on the page.
        """
        self.select_instrument("Andor BC43 Benchtop Confocal")
        self.tick("method-list", "Confocal spinning")
        self.tick("obj-list", ".")
        self.tick("light-list", ".")
        output = self.add()
        status = self.page.locator("#methods-selection-status").inner_text()
        self.assertNotIn("light path", status.lower())
        self.assertIn("Spinning-disk confocal imaging", output)

    def test_readouts_remain_selectable_while_the_path_stays_hidden(self):
        """A readout is a real, separate fact and keeps its own control.

        The STELLARIS records FLIM, FCS, spectral imaging and FRET on its
        confocal path. The method that implies the path is unambiguous, so the
        path itself is never shown, but the readouts it can additionally record
        are not a repeat of anything and must still be offered.
        """
        self.select_instrument("Leica STELLARIS 8 FALCON FLIM")
        self.tick("method-list", "Confocal point")
        self.assertFalse(
            self.page.evaluate("() => document.getElementById('section-route').offsetParent !== null"),
            "the light path is unambiguous and must stay hidden",
        )
        self.tick("readout-list", "FLIM")
        self.tick("obj-list", ".")
        output = self.add()
        self.assertIn("with FLIM data acquired on the same light path", output)


if __name__ == "__main__":
    unittest.main()
