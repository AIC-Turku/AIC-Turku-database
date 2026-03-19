import json
import unittest
from pathlib import Path

from scripts.generate_templates import build_template


class TemplateGenerationTests(unittest.TestCase):
    def test_object_map_uses_example_key_for_brace_paths(self) -> None:
        schema_path = Path('tmp_schema_for_template_test.yaml')
        schema_path.write_text(
            json.dumps(
                {
                    'sections': [
                        {
                            'title': 'Hardware',
                            'rules': [
                                {
                                    'path': 'hardware.light_path.excitation_mechanisms[].positions',
                                    'type': 'object',
                                    'example_key': 'Pos_1',
                                },
                                {
                                    'path': 'hardware.light_path.excitation_mechanisms[].positions{}.component_type',
                                    'type': 'string',
                                },
                            ],
                        }
                    ]
                }
            ),
            encoding='utf-8',
        )

        try:
            rendered = build_template(schema_path)
        finally:
            schema_path.unlink(missing_ok=True)

        self.assertIn('positions:', rendered)
        self.assertIn('Pos_1:', rendered)
        self.assertIn('component_type: ""', rendered)
        self.assertNotIn('positions{}:', rendered)


    def test_instrument_template_includes_light_path_endpoints_branches_and_spectral_fields(self) -> None:
        rendered = Path('templates/microscope_template.yaml').read_text(encoding='utf-8')

        self.assertIn('sources:', rendered)
        self.assertIn('optical_path_elements:', rendered)
        self.assertIn('endpoints:', rendered)
        self.assertIn('endpoint_type: ""', rendered)
        self.assertIn('branches:', rendered)
        self.assertIn('stage_role: ""', rendered)
        self.assertIn('element_type: ""', rendered)
        self.assertIn('selection_mode: ""', rendered)
        self.assertIn('mode: ""', rendered)
        self.assertIn('target_ids:', rendered)
        self.assertIn('branch_id: ""', rendered)
        self.assertIn('sequence:', rendered)
        self.assertIn('supported_branch_count: ""', rendered)
        self.assertIn('collection_min_nm: ""', rendered)
        self.assertIn('collection_max_nm: ""', rendered)
        self.assertIn('collection_center_nm: ""', rendered)
        self.assertIn('collection_width_nm: ""', rendered)
        self.assertIn('tunable_min_nm: ""', rendered)
        self.assertIn('tunable_max_nm: ""', rendered)
        self.assertIn('simultaneous_lines_max: ""', rendered)
        self.assertIn('product_code: ""  # Source product code', rendered)
        self.assertIn('illumination_sequence:', rendered)
        self.assertIn('detection_sequence:', rendered)
        self.assertNotIn('light_sources:', rendered)
        self.assertNotIn('light_path:', rendered)

    def test_plan_experiments_prompt_uses_canonical_v2_route_language(self) -> None:
        rendered = Path('scripts/templates/plan_experiments.md.j2').read_text(encoding='utf-8')

        self.assertIn('hardware.sources', rendered)
        self.assertIn('hardware.optical_path_elements', rendered)
        self.assertIn('hardware.endpoints', rendered)
        self.assertIn('light_paths', rendered)
        self.assertIn('branches', rendered)
        self.assertNotIn('Using the \\`hardware.light_path\\` topological data', rendered)
        self.assertNotIn('\\`excitation_mechanisms\\`', rendered)
        self.assertNotIn('Path 1 vs Path 2', rendered)

if __name__ == '__main__':
    unittest.main()
