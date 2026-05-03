import unittest

from scripts.dashboard.llm_export import build_llm_inventory_payload
from scripts.dashboard.site_render import _build_llm_inventory_record_from_build_input


class TestDashboardLlmInventoryDataflow(unittest.TestCase):
    def _record(self, *, scope_id: str, display_name: str, route_id: str, route_type: str, route_type_label: str, readouts: list[str], contrast_methods: list[str] | None = None):
        route_readouts = [{"id": r, "display_label": r.replace("_", " ").title()} for r in readouts]
        return {
            "id": scope_id,
            "display_name": display_name,
            "status": {"color": "green"},
            "canonical": {"instrument": {"instrument_id": scope_id, "display_name": display_name}},
            "canonical_instrument_dto": {"capabilities": {"contrast_methods": contrast_methods or []}},
            "lightpath_dto": {"projections": {"llm": {"authoritative_route_contract": {"routes": [{"id": route_id, "readouts": route_readouts, "route_identity": {"route_type": route_type, "route_type_label": route_type_label}}]}}}},
            "dto": {"display_name": display_name},
        }

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

    def test_llm_inventory_answerability_core_questions(self):
        records = [
            self._record(scope_id="leica-stellaris-8-falcon-flim", display_name="Leica STELLARIS 8 FALCON FLIM", route_id="confocal_point", route_type="confocal_point", route_type_label="Confocal point scanning", readouts=["flim", "fcs", "spectral_imaging"]),
            self._record(scope_id="lambert-flim", display_name="Lambert FLIM", route_id="widefield_fluorescence", route_type="widefield_fluorescence", route_type_label="Widefield fluorescence", readouts=["flim"]),
            self._record(scope_id="oni-nanoimager", display_name="ONI Nanoimager", route_id="tirf", route_type="tirf", route_type_label="TIRF", readouts=["fret"]),
            self._record(scope_id="zeiss-lsm-880-airyscan", display_name="Zeiss LSM 880 with AiryScan", route_id="confocal_point", route_type="confocal_point", route_type_label="Confocal point scanning", readouts=["spectral_imaging"]),
            self._record(scope_id="bf-manual", display_name="Olympus BX53 + DP74 + PM2000 + XCite 120LED Mini", route_id="transmitted_light", route_type="transmitted_light", route_type_label="Transmitted light", readouts=[], contrast_methods=["transmitted_brightfield"]),
        ]
        payload = build_llm_inventory_payload({"short_name": "AIC"}, records)
        microscopes = {m.get("display_name"): m for m in payload.get("active_microscopes", [])}

        stellaris = microscopes["Leica STELLARIS 8 FALCON FLIM"]
        routes = stellaris["llm_context"]["authoritative_route_contract"]["routes"]
        confocal = next(r for r in routes if r.get("id") == "confocal_point")
        confocal_readouts = {r.get("id") for r in confocal.get("readouts", [])}
        self.assertTrue({"flim", "fcs", "spectral_imaging"}.issubset(confocal_readouts))
        self.assertIn("route_type", confocal.get("route_identity", {}))
        self.assertIn("route_type_label", confocal.get("route_identity", {}))

        lambert = microscopes["Lambert FLIM"]
        lambert_routes = lambert["llm_context"]["authoritative_route_contract"]["routes"]
        lambert_wf = next(r for r in lambert_routes if r.get("id") == "widefield_fluorescence")
        self.assertIn("flim", {r.get("id") for r in lambert_wf.get("readouts", [])})

        oni = microscopes["ONI Nanoimager"]
        oni_routes = oni["llm_context"]["authoritative_route_contract"]["routes"]
        oni_tirf = next(r for r in oni_routes if r.get("id") == "tirf")
        self.assertIn("fret", {r.get("id") for r in oni_tirf.get("readouts", [])})

        zeiss = microscopes["Zeiss LSM 880 with AiryScan"]
        zeiss_routes = zeiss["llm_context"]["authoritative_route_contract"]["routes"]
        zeiss_confocal = next(r for r in zeiss_routes if r.get("id") == "confocal_point")
        self.assertIn("spectral_imaging", {r.get("id") for r in zeiss_confocal.get("readouts", [])})

        transmitted = microscopes["Olympus BX53 + DP74 + PM2000 + XCite 120LED Mini"]
        contrast_ids = set(transmitted.get("capabilities", {}).get("contrast_methods", []))
        self.assertIn("transmitted_brightfield", contrast_ids)
        self.assertFalse(transmitted.get("legacy_modalities"))


if __name__ == "__main__":
    unittest.main()
