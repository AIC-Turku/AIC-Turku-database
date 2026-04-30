import unittest

from tests.test_build_context_boundaries_static import TestBuildContextBoundariesStatic


class TestDashboardExportBoundariesStatic(unittest.TestCase):
    def test_dashboard_modules_do_not_import_dashboard_builder(self) -> None:
        case = TestBuildContextBoundariesStatic()
        case.test_no_dashboard_builder_imports_in_dashboard_modules()


if __name__ == '__main__':
    unittest.main()
