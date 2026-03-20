import unittest
from pathlib import Path


class VirtualMicroscopeAppTemplateTests(unittest.TestCase):
    def test_app_renders_route_graph_before_derived_control_groups(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("function buildAuthoritativeRouteGraph(topology)", source)
        self.assertIn("function renderAuthoritativeRouteGraph(host, graphModel)", source)
        self.assertIn("function buildDerivedControlGroups(inst, topology, route)", source)
        self.assertIn("const authoritativeGraph = buildAuthoritativeRouteGraph(topology);", source)
        self.assertIn("const derivedControlGroups = buildDerivedControlGroups(inst, topology, route);", source)
        self.assertIn("renderAuthoritativeRouteGraph(topologyWrap, authoritativeGraph);", source)
        self.assertIn("instrument.routeTopology && Array.isArray(instrument.routeTopology.routes)", source)
        self.assertNotIn("const stages = [];", source)

    def test_app_keeps_route_graph_primary_and_stage_groups_derived_only(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("Authoritative route graph rendered directly from canonical graph_nodes / graph_edges", source)
        self.assertIn("Downstream: ${node.downstream.map", source)
        self.assertIn("Branch blocks:", source)
        self.assertIn("const rawBranches = Array.isArray(block && block.branches)", source)
        self.assertIn("endpointIdsFromSequence(sequence)", source)
        self.assertIn("Branch sequence declared without explicit endpoint labels", source)
        self.assertIn("routeRecord.routeHardwareUsage", source)
        self.assertIn("Derived control group layered on top of the active route graph.", source)
        self.assertIn("Derived selectors aligned to route-local detection traversal and explicit branch semantics.", source)
        self.assertIn("Derived control widgets for explicit route endpoints.", source)

    def test_init_sets_up_all_event_listeners_before_instrument_loading(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        # Verify the refactored init() contains the extracted helper functions
        self.assertIn("function populateScopeSelector()", source)
        self.assertIn("function fetchInstrumentsFromDataJson()", source)
        self.assertIn("function initInstrumentList()", source)

        # Confirm event listeners are wired in init() independently of instrument data
        init_block_start = source.index("function init()")
        route_sel_listener = source.index("DOM.routeSel.addEventListener", init_block_start)
        scope_sel_listener = source.index("DOM.scopeSel.addEventListener", init_block_start)
        # Both listeners should appear before initInstrumentList()
        init_instrument_list_call = source.index("initInstrumentList()", init_block_start)
        self.assertLess(scope_sel_listener, init_instrument_list_call)
        self.assertLess(route_sel_listener, init_instrument_list_call)

    def test_scope_selector_uses_display_label_or_display_name(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        # populateScopeSelector should prefer display_label, fall back to display_name
        self.assertIn("display_label || payload.display_name", source)

    def test_instruments_data_json_fallback_is_wired(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("instruments_data.json", source)
        self.assertIn("fetchInstrumentsFromDataJson()", source)

    def test_route_change_clears_spectral_band_state(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        # The routeSel change handler should clear old spectral band state
        route_change_start = source.index("DOM.routeSel.addEventListener")
        route_change_end = source.index("});", route_change_start)
        route_change_handler = source[route_change_start:route_change_end]
        self.assertIn("state.spectralBandsByMechanism.clear()", route_change_handler)

    def test_scope_change_handler_updates_active_instrument_state(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        scope_change_start = source.index("DOM.scopeSel.addEventListener")
        scope_change_end = source.index("});", scope_change_start)
        scope_change_handler = source[scope_change_start:scope_change_end]
        self.assertIn("state.activeInstrumentRaw", scope_change_handler)
        self.assertIn("state.activeInstrument", scope_change_handler)

    def test_route_selector_falls_back_to_route_topology_catalog(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("routeTopology.routeCatalog", source)
        # The render function should use the catalog as a fallback
        self.assertIn("catalogFallback", source)
        # explicitOptions takes priority; catalogFallback used when empty
        self.assertIn("explicitOptions.length ? explicitOptions : catalogFallback", source)

    def test_node_cards_have_click_listeners_for_inspector_navigation(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        # stageGroupForNodeKind helper must exist
        self.assertIn("function stageGroupForNodeKind(kindLabel)", source)
        # The helper should map known component kinds to stage group ids
        self.assertIn("'sources'", source)
        self.assertIn("'illumination-controls'", source)
        self.assertIn("'detection-controls'", source)
        self.assertIn("'detectors'", source)
        self.assertIn("'sample'", source)

        # The authoritative graph renderer must call setInspectorStage via the helper
        self.assertIn("stageGroupForNodeKind(node.kindLabel)", source)
        self.assertIn("setInspectorStage(nodeStageGroup)", source)


if __name__ == "__main__":
    unittest.main()
