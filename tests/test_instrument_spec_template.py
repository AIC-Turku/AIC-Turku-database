import unittest
from pathlib import Path


class InstrumentSpecTemplateTests(unittest.TestCase):
    def test_instrument_spec_template_prefers_route_graph_dto_inputs(self) -> None:
        template = Path("scripts/templates/instrument_spec.md.j2").read_text(encoding="utf-8")

        self.assertIn("optical_path.light_paths or optical_path.route_renderables or optical_path.routes", template)
        self.assertIn("hardware_inventory = optical_path.hardware_inventory", template)
        self.assertIn("hardware_index_map = optical_path.hardware_index_map", template)
        self.assertIn("{% for route in route_graphs %}", template)
        self.assertIn("route.graph_nodes", template)
        self.assertIn("route.graph_edges", template)
        self.assertIn("node.inventory_display_number or node.display_number or ((hardware_index_map.by_inventory_id or {}).get(node.hardware_inventory_id)", template)
        self.assertIn("route.static_graph and route.static_graph.svg_markup", template)
        self.assertIn("Supplementary Optical Path Summaries", template)
        self.assertIn("This route is rendered from canonical DTO graph data", template)
        self.assertIn("route.endpoint_summary.labels", template)
        self.assertIn("route.branch_summary and route.branch_summary.has_branches", template)
        self.assertIn("route.branch_summary.branches", template)
        self.assertIn("route.route_local_hardware_usage.items", template)
        self.assertIn("Inventory usage:", template)
        self.assertIn("item.display_number or '—'", template)
        self.assertIn("Route graphs below may show the same numbered component multiple times", template)
        self.assertNotIn("hw.optical_path.static_graphs or [hw.optical_path.static_graph]", template)
        self.assertNotIn("route_renderables or optical_path.routes or optical_path.light_paths", template)


if __name__ == "__main__":
    unittest.main()
