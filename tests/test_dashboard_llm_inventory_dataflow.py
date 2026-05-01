import unittest

from scripts.dashboard.llm_export import build_llm_inventory_payload
from scripts.dashboard.site_render import _build_llm_inventory_record_from_build_input


class TestDashboardLlmInventoryDataflow(unittest.TestCase):
    def test_llm_inventory_record_preserves_canonical_context(self):
        build_input = {
            "id": "scope-a1",
            "display_name": "Scope A1",
            "status": {"color": "green"},
            "canonical": {
                "instrument": {"instrument_id": "scope-a1", "display_name": "Scope A1"},
                "hardware": {
                    "objectives": [{"id": "obj-1", "display_label": "60x Oil", "is_installed": True}],
                    "sources": [{"id": "src-488", "display_label": "488nm Laser"}],
                    "detectors": [{"id": "det-1", "display_label": "sCMOS"}],
                },
                "software": [{"id": "sw-1", "display_label": "AcqSuite"}],
                "modalities": [{"id": "confocal", "display_label": "Confocal"}],
            },
            "lightpath_dto": {
                "projections": {
                    "llm": {
                        "authoritative_route_contract": {
                            "routes": [
                                {
                                    "id": "route-1",
                                    "display_label": "Confocal 488",
                                    "route_identity": {"route_id": "route-1"},
                                    "route_optical_facts": {
                                        "selected_or_selectable_sources": [{"id": "src-488"}],
                                        "selected_or_selectable_excitation_filters": [{"id": "ex-1"}],
                                        "selected_or_selectable_dichroics": [{"id": "dm-1"}],
                                        "selected_or_selectable_emission_filters": [{"id": "em-1"}],
                                        "selected_or_selectable_splitters": [{"id": "sp-1"}],
                                        "selected_or_selectable_branch_selectors": [{"id": "bs-1"}],
                                        "selected_or_selectable_endpoints": [{"id": "det-1"}],
                                        "selected_or_selectable_modulators": [],
                                    },
                                }
                            ],
                            "available_routes": [{"id": "route-1", "label": "Confocal 488"}],
                        }
                    }
                },
                "light_paths": [{"selected_execution": {"path": ["src-488", "det-1"]}}],
            },
            "dto": {"display_name": "Scope A1", "diagnostics": [{"code": "ok"}]},
            "diagnostics": [{"severity": "info", "code": "build_ok"}],
        }

        record = _build_llm_inventory_record_from_build_input(build_input)
        self.assertTrue(record.get("canonical"))
        self.assertTrue(record.get("canonical_instrument_dto"))
        self.assertTrue(record.get("lightpath_dto"))
        self.assertTrue(record.get("canonical_lightpath_dto"))

        payload = build_llm_inventory_payload({"short_name": "AIC"}, [record])
        self.assertEqual(1, len(payload.get("active_microscopes", [])))

        microscope = payload["active_microscopes"][0]
        self.assertTrue(microscope.get("hardware"))
        self.assertTrue(microscope.get("software"))

        llm_context = microscope.get("llm_context", {})
        self.assertTrue(
            llm_context.get("authoritative_route_contract")
            or llm_context.get("route_planning_summary")
        )

    def test_old_dto_only_record_lacks_required_canonical_context(self):
        old_record = {"display_name": "Scope A1", "diagnostics": [{"code": "only_dto"}]}
        self.assertFalse(old_record.get("canonical"))
        self.assertFalse(old_record.get("canonical_instrument_dto"))
        self.assertFalse(old_record.get("lightpath_dto"))


if __name__ == "__main__":
    unittest.main()
