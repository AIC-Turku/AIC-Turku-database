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
        self.assertNotIn("const stages = [];", source)

    def test_app_keeps_route_graph_primary_and_stage_groups_derived_only(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("Authoritative route graph rendered directly from canonical graph_nodes / graph_edges", source)
        self.assertIn("Downstream: ${node.downstream.map", source)
        self.assertIn("Branch blocks:", source)
        self.assertIn("Derived control group layered on top of the active route graph.", source)
        self.assertIn("Derived selectors aligned to route-local detection traversal and explicit branch semantics.", source)
        self.assertIn("Derived control widgets for explicit route endpoints.", source)


if __name__ == "__main__":
    unittest.main()
