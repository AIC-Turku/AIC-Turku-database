"""What may be printed as a component's or a microscope's name in Methods prose.

These cover the cases where the draft named something the record does not actually
identify, or named two different instruments identically.
"""

import unittest

from scripts.dashboard.optical_path_view import (
    _identity_value,
    _indefinite_article,
    _inventory_method_facts,
    _looks_like_internal_id,
    _publication_inventory_label,
    _publication_position_phrase,
)


class PublicationIdentityTests(unittest.TestCase):
    def test_placeholder_values_are_not_identities(self):
        for value in ("Unknown", "unknown", "Unknown Camera", "Placeholder", "n/a", "-", ""):
            self.assertEqual("", _identity_value(value), value)
        self.assertEqual("Kinetix", _identity_value("Kinetix"))

    def test_an_authored_placeholder_label_is_not_a_fallback(self):
        """`Unknown Camera` is what the record says it does not know."""
        item = {"inventory_class": "endpoint", "manufacturer": "Unknown",
                "model": "Unknown Camera", "display_label": "Unknown Camera", "id": "camera_port_main"}
        self.assertEqual("", _publication_inventory_label(item, None))

    def test_a_manufacturer_alone_does_not_identify_a_detector(self):
        """"Zeiss" names a vendor, not the photomultiplier a reader
        would have to look up."""
        item = {"inventory_class": "endpoint", "manufacturer": "Zeiss",
                "model": "Unknown PMT", "display_label": "Zeiss", "id": "detector_1"}
        self.assertEqual("", _publication_inventory_label(item, None))

    def test_an_authored_label_without_an_identity_is_still_usable(self):
        """Eyepieces and named ports carry no manufacturer and need none."""
        item = {"inventory_class": "eyepiece", "manufacturer": "", "model": "",
                "display_label": "eyepieces", "id": "eyepieces"}
        self.assertEqual("eyepieces", _publication_inventory_label(item, None))

    def test_an_unidentifiable_component_produces_a_request_not_a_sentence(self):
        """The component stays selectable; the draft asks who it is."""
        template, sentence, prompts = _inventory_method_facts({"inventory_class": "endpoint"}, "")
        self.assertEqual("", template)
        self.assertEqual("", sentence)
        self.assertEqual(1, len(prompts))
        self.assertIn("the detector or camera used for this acquisition", prompts[0])

    def test_internal_slot_identifiers_are_recognised(self):
        """`EMP_BF` is a key, not a name."""
        self.assertTrue(_looks_like_internal_id("EMP_BF"))
        self.assertTrue(_looks_like_internal_id("Pos_1"))
        self.assertFalse(_looks_like_internal_id("GFP"))
        self.assertFalse(_looks_like_internal_id("387/11"))
        self.assertFalse(_looks_like_internal_id("Filter Cube A"))

    def test_articles_follow_how_a_label_is_read_aloud(self):
        """"""
        self.assertEqual("a", _indefinite_article("640 nm laser"))
        self.assertEqual("an", _indefinite_article("arc lamp"))
        self.assertEqual("an", _indefinite_article("LED illuminator"))
        self.assertEqual("a", _indefinite_article("UV lamp"))
        self.assertEqual("a", _indefinite_article("white light laser"))


class PositionPhraseTests(unittest.TestCase):
    """What a filter passes is the fact a reader checks; the catalogue
    number alone does not carry it."""

    def test_a_spec_named_filter_states_its_band_and_catalogue_number(self):
        phrase = _publication_position_phrase({
            "display_label": "387/11", "has_identity": True, "spec_phrase": "387/11 nm",
            "type_noun": "excitation bandpass filter", "product_code": "FF01-387/11-25",
            "manufacturer": "",
        })
        self.assertEqual("a 387/11 nm excitation bandpass filter (cat. no. FF01-387/11-25)", phrase)

    def test_a_named_cube_keeps_its_name_and_gains_its_bands(self):
        phrase = _publication_position_phrase({
            "display_label": "GFP", "has_identity": True,
            "spec_phrase": "excitation 470/22 nm, 495 nm dichroic, emission 510/42 nm",
            "type_noun": "filter cube", "product_code": "ZP-EPI-9002", "manufacturer": "",
        })
        self.assertEqual(
            "a GFP filter cube (excitation 470/22 nm, 495 nm dichroic, emission 510/42 nm; "
            "cat. no. ZP-EPI-9002)",
            phrase,
        )

    def test_a_name_that_already_says_what_it_is_does_not_repeat_the_type(self):
        phrase = _publication_position_phrase({
            "display_label": "Quad-band Dichroic", "has_identity": True,
            "spec_phrase": "440/25, 521/25 nm", "type_noun": "multi-band dichroic mirror",
            "product_code": "", "manufacturer": "",
        })
        self.assertEqual("a Quad-band Dichroic (440/25, 521/25 nm)", phrase)

    def test_a_qualifier_the_name_carries_is_dropped_but_the_head_noun_stays(self):
        phrase = _publication_position_phrase({
            "display_label": "DAPI Emission", "has_identity": True, "spec_phrase": "435/26 nm",
            "type_noun": "emission bandpass filter", "product_code": "", "manufacturer": "",
        })
        self.assertEqual("a DAPI Emission bandpass filter (435/26 nm)", phrase)

    def test_a_slot_word_is_not_part_of_the_component_name(self):
        """"NIR dichroic position" names a slot, not the optic."""
        phrase = _publication_position_phrase({
            "display_label": "NIR dichroic position", "has_identity": True, "spec_phrase": "",
            "type_noun": "dichroic mirror", "product_code": "", "manufacturer": "",
        })
        self.assertEqual("an NIR dichroic", phrase)

    def test_a_position_with_no_recorded_bands_states_no_bands(self):
        """Nothing is inferred: an unrecorded transmission produces no phrase for it
        and the existing incompleteness request asks for it."""
        phrase = _publication_position_phrase({
            "display_label": "CYR71010", "has_identity": True, "spec_phrase": "",
            "type_noun": "filter cube", "product_code": "11525416", "manufacturer": "",
        })
        self.assertEqual("a CYR71010 filter cube (cat. no. 11525416)", phrase)


if __name__ == "__main__":
    unittest.main()
