import unittest


class LightpathModuleCompatTests(unittest.TestCase):
    def test_public_module_imports(self) -> None:
        from scripts.lightpath import (
            parse_canonical_light_path_model,
            canonicalize_light_path_model_strict,
            import_legacy_light_path_model,
            migrate_instrument_to_light_path_v2,
            has_legacy_light_path_input,
            validate_light_path,
            validate_light_path_warnings,
            validate_filter_cube_warnings,
            validate_light_path_diagnostics,
            generate_virtual_microscope_payload,
            canonicalize_light_path_model,
        )
        for fn in [
            parse_canonical_light_path_model,
            canonicalize_light_path_model_strict,
            import_legacy_light_path_model,
            migrate_instrument_to_light_path_v2,
            has_legacy_light_path_input,
            validate_light_path,
            validate_light_path_warnings,
            validate_filter_cube_warnings,
            validate_light_path_diagnostics,
            generate_virtual_microscope_payload,
            canonicalize_light_path_model,
        ]:
            self.assertTrue(callable(fn))


if __name__ == "__main__":
    unittest.main()
