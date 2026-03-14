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

        self.assertIn('endpoints:', rendered)
        self.assertIn('endpoint_type: ""', rendered)
        self.assertIn('branches:', rendered)
        self.assertIn('target_ids:', rendered)
        self.assertIn('collection_min_nm: ""', rendered)
        self.assertIn('collection_max_nm: ""', rendered)
        self.assertIn('collection_center_nm: ""', rendered)
        self.assertIn('collection_width_nm: ""', rendered)
        self.assertIn('tunable_min_nm: ""', rendered)
        self.assertIn('tunable_max_nm: ""', rendered)
        self.assertIn('simultaneous_lines_max: ""', rendered)

if __name__ == '__main__':
    unittest.main()
