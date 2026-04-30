import ast
import unittest
from pathlib import Path


def _defs(path: str) -> set[str]:
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}


class TestBuildContextBoundariesStatic(unittest.TestCase):
    def test_build_context_defines_canonical_functions(self) -> None:
        defs = _defs('scripts/build_context.py')
        for name in {
            'clean_text', 'strip_empty_values', 'normalize_software', 'normalize_hardware',
            'normalize_instrument_dto', 'is_valid_instrument_id', '_discover_image_filename'
        }:
            self.assertIn(name, defs)

    def test_dashboard_builder_does_not_define_moved_functions(self) -> None:
        defs = _defs('scripts/dashboard_builder.py')
        for name in {
            'clean_text', 'strip_empty_values', 'normalize_software', 'normalize_hardware',
            'normalize_instrument_dto', 'is_valid_instrument_id', '_discover_image_filename'
        }:
            self.assertNotIn(name, defs)

    def test_no_dashboard_builder_imports_in_dashboard_modules(self) -> None:
        for path in Path('scripts/dashboard').glob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = {alias.name for alias in node.names}
                    self.assertNotIn('scripts.dashboard_builder', names)
                elif isinstance(node, ast.ImportFrom):
                    self.assertFalse(node.module == 'scripts.dashboard_builder')
                    self.assertFalse(node.module == 'scripts' and any(alias.name == 'dashboard_builder' for alias in node.names))

    def test_build_context_does_not_import_dashboard_builder(self) -> None:
        tree = ast.parse(Path('scripts/build_context.py').read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertNotIn('scripts.dashboard_builder', {alias.name for alias in node.names})
            elif isinstance(node, ast.ImportFrom):
                self.assertFalse(node.module == 'scripts.dashboard_builder')
                self.assertFalse(node.module == 'scripts' and any(alias.name == 'dashboard_builder' for alias in node.names))

    def test_no_dashboard_impl_file(self) -> None:
        self.assertFalse(Path('scripts/dashboard/_impl.py').exists())




class TestDashboardBuilderThinCli(unittest.TestCase):
    def test_dashboard_builder_defines_only_cli_functions(self) -> None:
        tree = ast.parse(Path('scripts/dashboard_builder.py').read_text(encoding='utf-8'))
        defs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
        self.assertEqual(set(defs), {'main', '_parse_args'})

    def test_dashboard_builder_main_delegates_to_render_site(self) -> None:
        tree = ast.parse(Path('scripts/dashboard_builder.py').read_text(encoding='utf-8'))
        main_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        ret = next((n for n in ast.walk(main_node) if isinstance(n, ast.Return)), None)
        self.assertIsNotNone(ret)
        self.assertIsInstance(ret.value, ast.Call)
        self.assertIsInstance(ret.value.func, ast.Name)
        self.assertEqual(ret.value.func.id, 'render_site')

if __name__ == '__main__':
    unittest.main()
