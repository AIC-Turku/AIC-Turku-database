import unittest


class DashboardModuleCompatTests(unittest.TestCase):
    def test_new_module_imports_work(self) -> None:
        from scripts.dashboard import (
            load_instruments,
            validated_instrument_selection,
            build_instrument_mega_dto,
            build_hardware_dto,
            build_optical_path_view_dto,
            build_optical_path_dto,
            build_llm_inventory_payload,
            build_methods_generator_instrument_export,
        )

        self.assertTrue(callable(load_instruments))
        self.assertTrue(callable(validated_instrument_selection))
        self.assertTrue(callable(build_instrument_mega_dto))
        self.assertTrue(callable(build_hardware_dto))
        self.assertTrue(callable(build_optical_path_view_dto))
        self.assertTrue(callable(build_optical_path_dto))
        self.assertTrue(callable(build_llm_inventory_payload))
        self.assertTrue(callable(build_methods_generator_instrument_export))


if __name__ == "__main__":
    unittest.main()
