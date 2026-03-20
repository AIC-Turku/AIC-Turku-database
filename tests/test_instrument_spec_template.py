import unittest
from pathlib import Path


class InstrumentSpecTemplateTests(unittest.TestCase):
    def test_instrument_spec_template_prefers_route_graph_dto_inputs(self) -> None:
        template = Path("scripts/templates/instrument_spec.md.j2").read_text(encoding="utf-8")

        self.assertIn("optical_path.light_paths or optical_path.route_renderables or optical_path.routes", template)
        self.assertIn("hardware_inventory = optical_path.hardware_inventory", template)
        self.assertIn("hardware_index_map = optical_path.hardware_index_map", template)
        self.assertIn("Optical Path Elements", template)
        self.assertNotIn("Route Graph Topology", template)
        self.assertNotIn("Supplementary Optical Path Summaries", template)
        self.assertNotIn("{% for route in route_graphs %}", template)
        self.assertNotIn("route.static_graph and route.static_graph.svg_markup", template)
        self.assertNotIn("This route is rendered from canonical DTO graph data", template)
        self.assertNotIn("Route graphs below may show the same numbered component multiple times", template)
        self.assertNotIn("Route-local hardware usage", template)
        self.assertNotIn('route.route_local_hardware_usage["items"]', template)
        self.assertNotIn("hw.optical_path.static_graphs or [hw.optical_path.static_graph]", template)
        self.assertNotIn("route_renderables or optical_path.routes or optical_path.light_paths", template)


if __name__ == "__main__":
    unittest.main()
