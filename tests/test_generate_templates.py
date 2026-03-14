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


if __name__ == '__main__':
    unittest.main()
