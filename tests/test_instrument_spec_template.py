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

    def test_optical_path_section_only_shows_optical_path_elements(self) -> None:
        template = Path("scripts/templates/instrument_spec.md.j2").read_text(encoding="utf-8")

        # Branching & Selector Summaries must be removed
        self.assertNotIn("Branching & Selector Summaries", template)
        self.assertNotIn("hw.optical_path.splitters", template)

        # Detection Endpoint Summaries must be removed
        self.assertNotIn("Detection Endpoint Summaries", template)
        self.assertNotIn("hw.optical_path.terminal_renderables", template)

        # Only optical_path_elements sections should be rendered
        self.assertIn('"optical_path_elements"', template)
        self.assertNotIn('section.id not in ["terminals"', template)

    def test_stages_section_uses_cards(self) -> None:
        template = Path("scripts/templates/instrument_spec.md.j2").read_text(encoding="utf-8")

        # Stages section must use the grid cards layout
        self.assertIn("hw.stages", template)
        # The stages loop must use render_spec_card (not a bare list)
        self.assertNotIn("- {{ item.display_label }}", template)

    def test_render_spec_card_avoids_empty_line_without_subtitle(self) -> None:
        template = Path("scripts/templates/instrument_spec.md.j2").read_text(encoding="utf-8")

        # The macro must NOT produce an unconditional blank line between title and spec_lines.
        # The subtitle must be on the same line as the title (inside the same if block),
        # not on a separate unconditional line that leaves a blank when subtitle is absent.
        self.assertNotIn(
            "**\n  {% if item.display_subtitle %}",
            template,
            "render_spec_card must not place the subtitle check on a separate line that produces an empty line",
        )


class DashboardBuilderOpticalPathTests(unittest.TestCase):
    def test_optical_element_position_pairs_dict(self) -> None:
        from scripts.dashboard_builder import _optical_element_position_pairs

        # YAML position keys use underscores (e.g. "Pos_1"); the helper converts them to
        # title-case display labels with spaces (e.g. "Pos 1").
        element = {
            "positions": {
                "Pos_1": {"name": "GFP Filter", "product_code": "ET525/50", "bands": [{"center_nm": 525, "width_nm": 50}], "notes": "Excitation: 488 nm."},
                "Pos_2": {"name": "RFP Filter", "product_code": "ET605/70", "bands": [{"center_nm": 605, "width_nm": 70}]},
            }
        }
        pairs = _optical_element_position_pairs(element)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0][0], "Pos 1")
        self.assertIn("GFP Filter", pairs[0][1])
        self.assertIn("ET525/50", pairs[0][1])
        self.assertIn("525/50 nm", pairs[0][1])
        self.assertIn("488 nm", pairs[0][1])
        self.assertEqual(pairs[1][0], "Pos 2")
        self.assertIn("RFP Filter", pairs[1][1])
        self.assertIn("605/70 nm", pairs[1][1])

    def test_optical_element_position_pairs_list(self) -> None:
        from scripts.dashboard_builder import _optical_element_position_pairs

        element = {
            "positions": [
                {"name": "DAPI", "bands": [{"center_nm": 435, "width_nm": 26}]},
                {"name": "GFP", "bands": [{"center_nm": 515, "width_nm": 30}]},
            ]
        }
        pairs = _optical_element_position_pairs(element)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0][0], "Pos 1")
        self.assertIn("DAPI", pairs[0][1])
        self.assertIn("435/26 nm", pairs[0][1])

    def test_optical_element_position_pairs_empty(self) -> None:
        from scripts.dashboard_builder import _optical_element_position_pairs

        self.assertEqual(_optical_element_position_pairs({}), [])
        self.assertEqual(_optical_element_position_pairs({"positions": None}), [])
        self.assertEqual(_optical_element_position_pairs({"positions": {}}), [])

    def test_format_position_value(self) -> None:
        from scripts.dashboard_builder import _format_position_value

        pos = {"name": "Filter set 38 HE", "product_code": "38 HE", "bands": [{"center_nm": 525, "width_nm": 50}], "notes": "Excitation: 470/40 nm."}
        result = _format_position_value(pos)
        self.assertIn("Filter set 38 HE", result)
        self.assertIn("38 HE", result)
        self.assertIn("525/50 nm", result)
        self.assertIn("470/40 nm", result)

    def test_format_position_value_no_name(self) -> None:
        from scripts.dashboard_builder import _format_position_value

        self.assertEqual(_format_position_value({}), "")
        self.assertEqual(_format_position_value({"product_code": "XY"}), "")

    def test_optical_path_element_card_includes_positions(self) -> None:
        """Integration test: optical path element DTO must include position spec_lines."""
        from scripts.dashboard_builder import build_optical_path_dto

        lightpath_dto = {
            "optical_path_elements": [
                {
                    "id": "filter_turret",
                    "name": "Filter Turret",
                    "stage_role": "cube",
                    "element_type": "turret",
                    "modalities": ["widefield_fluorescence"],
                    "positions": {
                        "Pos_1": {"name": "GFP Cube", "product_code": "38HE", "bands": [{"center_nm": 525, "width_nm": 50}], "notes": "Excitation: 470 nm."},
                    },
                }
            ]
        }
        dto = build_optical_path_dto(lightpath_dto)
        sections = dto.get("sections", [])
        opt_el_sections = [s for s in sections if s.get("id") == "optical_path_elements"]
        self.assertEqual(len(opt_el_sections), 1)
        items = opt_el_sections[0]["items"]
        self.assertEqual(len(items), 1)
        spec_lines = items[0]["spec_lines"]
        joined = " ".join(spec_lines)
        self.assertIn("GFP Cube", joined)
        self.assertIn("38HE", joined)
        self.assertIn("525/50 nm", joined)
        self.assertIn("470 nm", joined)


if __name__ == "__main__":
    unittest.main()
