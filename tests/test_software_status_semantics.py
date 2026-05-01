import unittest

from scripts.dashboard.instrument_view import build_instrument_mega_dto
from scripts.dashboard.llm_export import build_llm_inventory_payload
from scripts.dashboard.methods_export import build_methods_generator_instrument_export
from scripts.validation.instrument import ValidationIssue


class _Vocab:
    def resolve_canonical(self, *_args, **_kwargs):
        return None


class SoftwareStatusSemanticsTests(unittest.TestCase):
    def test_llm_inventory_exports_not_applicable_status(self):
        payload = build_llm_inventory_payload(
            {"short_name": "AIC"},
            [{"id": "s1", "canonical": {"instrument": {"instrument_id": "s1", "display_name": "S1"}, "software": [], "software_status": "not_applicable"}, "lightpath_dto": {"light_paths": []}}],
        )
        record = payload["active_microscopes"][0]
        self.assertEqual("not_applicable", record.get("software_status"))
        self.assertIn("No acquisition/control software", record.get("software_status_caveat", ""))

    def test_methods_export_distinguishes_unknown(self):
        dto = build_methods_generator_instrument_export(
            {"id": "s1", "display_name": "S1", "canonical": {"instrument": {"instrument_id": "s1", "display_name": "S1"}, "hardware": {}, "software": [], "software_status": "unknown"}, "lightpath_dto": {"light_paths": []}},
        )
        self.assertEqual("unknown", dto["methods_view_dto"]["software_status"])

    def test_dashboard_message_for_not_applicable(self):
        dto = build_instrument_mega_dto(
            _Vocab(),
            {"id": "s1", "display_name": "S1", "canonical": {"instrument": {"manufacturer": "Leica", "model": "DM"}, "software": [], "software_status": "not_applicable", "modalities": [], "modules": [], "hardware": {}}},
            {"light_paths": []},
        )
        self.assertEqual("not_applicable", dto.get("software_status"))
        self.assertIn("manual or standalone", dto.get("software_status_message", "").lower())


if __name__ == "__main__":
    unittest.main()
