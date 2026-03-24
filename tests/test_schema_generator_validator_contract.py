import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class SchemaGeneratorValidatorContractIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.fixtures_root = self.repo_root / 'tests' / 'fixtures' / 'schema_generator_validator_contract'

    def _run_pipeline(self, fixture_name: str) -> tuple[subprocess.CompletedProcess[str], subprocess.CompletedProcess[str], str]:
        source_dir = self.fixtures_root / fixture_name
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / fixture_name
            shutil.copytree(source_dir, workdir)

            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.repo_root)

            generate = subprocess.run(
                ['python', '-m', 'scripts.generate_templates'],
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            validate = subprocess.run(
                ['python', '-m', 'scripts.validate'],
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            template_content = (workdir / 'templates' / 'microscope_template.yaml').read_text(encoding='utf-8')
            self.assertIn('positions:', template_content)
            self.assertIn('Pos_1:', template_content)

            if fixture_name == 'valid_repo':
                self.assertIn('bands:', template_content)

            return generate, validate, template_content

    def test_pipeline_passes_for_valid_multiband_fixture(self) -> None:
        generate, validate, _ = self._run_pipeline('valid_repo')

        self.assertEqual(generate.returncode, 0, msg=generate.stderr)
        self.assertEqual(validate.returncode, 0, msg=validate.stderr)
        self.assertIn('Validation passed.', validate.stdout)

    def test_pipeline_reports_missing_bands_for_invalid_multiband_fixture(self) -> None:
        generate, validate, _ = self._run_pipeline('invalid_repo')

        self.assertEqual(generate.returncode, 0, msg=generate.stderr)
        self.assertEqual(validate.returncode, 0, msg=validate.stderr)
        self.assertIn('missing_conditional_field', validate.stderr)
        self.assertIn('hardware.light_path.excitation_mechanisms[].positions{}.bands', validate.stderr)

    def test_pipeline_passes_for_explicit_filter_cube(self) -> None:
        """A filter_cube with explicit excitation_filter, dichroic, and emission_filter must be schema-valid."""
        generate, validate, template_content = self._run_pipeline('filter_cube_repo')

        self.assertEqual(generate.returncode, 0, msg=generate.stderr)
        self.assertEqual(validate.returncode, 0, msg=validate.stderr)
        self.assertIn('Validation passed.', validate.stdout)

        self.assertIn('excitation_filter:', template_content)
        self.assertIn('dichroic:', template_content)
        self.assertIn('emission_filter:', template_content)

    def test_pipeline_passes_for_flattened_filter_cube(self) -> None:
        """A flattened filter_cube (no explicit sub-components) must remain schema-valid for backward compatibility."""
        generate, validate, _ = self._run_pipeline('filter_cube_flattened_repo')

        self.assertEqual(generate.returncode, 0, msg=generate.stderr)
        self.assertEqual(validate.returncode, 0, msg=validate.stderr)
        self.assertIn('Validation passed.', validate.stdout)

    def test_pipeline_passes_for_incomplete_filter_cube(self) -> None:
        """A filter_cube with some but not all sub-components is schema-valid (parser flags incompleteness separately)."""
        generate, validate, _ = self._run_pipeline('filter_cube_incomplete_repo')

        self.assertEqual(generate.returncode, 0, msg=generate.stderr)
        self.assertEqual(validate.returncode, 0, msg=validate.stderr)
        self.assertIn('Validation passed.', validate.stdout)


if __name__ == '__main__':
    unittest.main()
