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

    def _run_pipeline(self, fixture_name: str) -> tuple[subprocess.CompletedProcess[str], subprocess.CompletedProcess[str], Path]:
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

            return generate, validate, workdir

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
        self.assertIn('positions.Pos_1.bands', validate.stderr)


if __name__ == '__main__':
    unittest.main()
