from __future__ import annotations

from pathlib import Path
import ast
import re
import unittest


class ValidationModuleBoundariesStaticTests(unittest.TestCase):
    def test_model_symbols_defined(self) -> None:
        text = Path("scripts/validation/model.py").read_text(encoding="utf-8")
        for symbol in (
            "class ValidationIssue", "class VocabularyTerm", "class PolicyRule", "class ResolvedNode",
            "class InstrumentPolicy", "class EventPolicy", "class EventValidationReport", "class InstrumentCompletenessReport",
        ):
            self.assertIn(symbol, text)

    def test_vocabulary_defined(self) -> None:
        self.assertIn("class Vocabulary", Path("scripts/validation/vocabulary.py").read_text(encoding="utf-8"))

    def test_events_symbols_defined(self) -> None:
        text = Path("scripts/validation/events.py").read_text(encoding="utf-8")
        for symbol in ("DEFAULT_ALLOWED_RECORD_TYPES", "YEAR_PATTERN", "ISO_YEAR_PATTERN", "FILENAME_DATE_PATTERN", "def _get_started_year", "def _check_event_type", "def validate_event_ledgers"):
            self.assertIn(symbol, text)

    def test_policy_symbols_defined(self) -> None:
        text = Path("scripts/validation/policy.py").read_text(encoding="utf-8")
        for symbol in (
            "def load_policy", "def _load_instrument_policy", "def _load_event_policy", "def _resolve_path_nodes",
            "def _resolve_rule_nodes", "def _nodes_have_present_value", "def _context_item_alias_present",
            "def _parent_path_from_list_path", "def _list_context_path", "def _build_item_field_vocab_index",
            "def _evaluate_required_if", "def _evaluate_event_required_if", "def _get_software_roles",
        ):
            self.assertIn(symbol, text)

    def test_instrument_symbols_defined(self) -> None:
        text = Path("scripts/validation/instrument.py").read_text(encoding="utf-8")
        for symbol in (
            "INSTRUMENT_ID_PATTERN", "def _is_valid_instrument_id",
            "def _is_numeric_string", "def _is_positive_number", "def _is_positive_number_or_numeric_string",
            "def _is_valid_wavelength", "def _is_descriptive_wavelength", "def _check_type", "def _coerce_number",
            "def _check_rule_validation", "def build_instrument_completeness_report",
            "def _append_name_model_redundancy_warnings",
            "def _build_canonical_instrument_payload",
            "def _legacy_instrument_topology_paths",
            "def _append_product_code_redundancy_warnings",
            "def _append_light_path_modality_warnings",
            "def validate_instrument_ledgers",
        ):
            self.assertIn(symbol, text)

    def test_validate_no_direct_defs_for_moved_symbols(self) -> None:
        text = Path("scripts/validate.py").read_text(encoding="utf-8")
        forbidden = (
            "class ValidationIssue", "class VocabularyTerm", "class Vocabulary", "class PolicyRule", "class ResolvedNode",
            "class InstrumentPolicy", "class EventPolicy", "class EventValidationReport", "class InstrumentCompletenessReport",
            "DEFAULT_ALLOWED_RECORD_TYPES: tuple", "YEAR_PATTERN =", "ISO_YEAR_PATTERN =", "FILENAME_DATE_PATTERN =",
            "def _get_started_year", "def load_policy", "def _load_instrument_policy", "def _load_event_policy",
            "def _resolve_path_nodes", "def _resolve_rule_nodes", "def _nodes_have_present_value", "def _context_item_alias_present",
            "def _parent_path_from_list_path", "def _list_context_path", "def _build_item_field_vocab_index",
            "def _evaluate_required_if", "def _evaluate_event_required_if", "def _check_event_type", "def validate_event_ledgers",
            "INSTRUMENT_ID_PATTERN =", "def _is_valid_instrument_id", "def _is_non_empty_string", "def _is_number",
            "def _is_numeric_string", "def _is_positive_number", "def _is_positive_number_or_numeric_string",
            "def _is_valid_wavelength", "def _is_descriptive_wavelength", "def _check_type", "def _coerce_number",
            "def _check_rule_validation", "def _get_software_roles", "def build_instrument_completeness_report",
            "def _append_name_model_redundancy_warnings",
            "def _build_canonical_instrument_payload",
            "def _legacy_instrument_topology_paths",
            "def _append_product_code_redundancy_warnings",
            "def _append_light_path_modality_warnings",
            "def validate_instrument_ledgers",
        )
        for item in forbidden:
            if item.startswith("def ") or item.startswith("class "):
                self.assertIsNone(re.search(rf"^\s*{re.escape(item)}\b", text, flags=re.MULTILINE))
            else:
                self.assertNotIn(item, text)


    def test_io_helpers_defined_if_module_exists(self) -> None:
        io_path = Path("scripts/validation/io.py")
        if not io_path.exists():
            return
        text = io_path.read_text(encoding="utf-8")
        self.assertIn("def _iter_yaml_files", text)
        self.assertIn("def _load_yaml", text)
        self.assertIn("def _is_non_empty_string", text)
        self.assertIn("def _is_number", text)
        self.assertNotIn("import scripts.validate", text)
        self.assertNotIn("from scripts.validate", text)

    def test_validation_modules_do_not_import_validate(self) -> None:
        for path in Path("scripts/validation").glob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("import scripts.validate", text)
            self.assertNotIn("from scripts.validate", text)

    def test_no_impl_module_exists(self) -> None:
        self.assertFalse(Path("scripts/validation/_impl.py").exists())

    def test_no_duplicate_definitions_across_package(self) -> None:
        """Ensure no function, class, or uppercase constant is defined more than once
        across scripts/validate.py and scripts/validation/*.py (excluding the shim
        re-exports in scripts/validate.py, which are import aliases not definitions)."""
        files = [Path("scripts/validate.py"), *Path("scripts/validation").glob("*.py")]
        locations: dict[str, list[str]] = {}
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    locations.setdefault(node.name, []).append(str(path))
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            locations.setdefault(target.id, []).append(str(path))
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    if node.target.id.isupper():
                        locations.setdefault(node.target.id, []).append(str(path))
        duplicates = {name: paths for name, paths in locations.items() if len(paths) > 1}
        self.assertEqual({}, duplicates, f"Duplicate definitions found across validation package: {duplicates}")

    def test_vocabulary_uses_io_load_yaml(self) -> None:
        """vocabulary.py must import _load_yaml from io.py rather than defining its own copy."""
        vocab_text = Path("scripts/validation/vocabulary.py").read_text(encoding="utf-8")
        self.assertIn("from scripts.validation.io import", vocab_text)
        self.assertNotIn("def _load_yaml", vocab_text)

    def test_shared_utilities_defined_in_io(self) -> None:
        """_is_non_empty_string and _is_number must be defined only in io.py."""
        io_text = Path("scripts/validation/io.py").read_text(encoding="utf-8")
        self.assertIn("def _is_non_empty_string", io_text)
        self.assertIn("def _is_number", io_text)
        for module in ("events.py", "instrument.py", "policy.py", "vocabulary.py", "reporting.py"):
            text = Path(f"scripts/validation/{module}").read_text(encoding="utf-8")
            self.assertNotIn("def _is_non_empty_string", text, f"Should not define _is_non_empty_string in {module}")
            self.assertNotIn("def _is_number", text, f"Should not define _is_number in {module}")

    def test_get_software_roles_not_duplicated(self) -> None:
        """_get_software_roles must be defined only once (in policy.py) across the package."""
        count = 0
        for path in Path("scripts/validation").glob("*.py"):
            if "def _get_software_roles" in path.read_text(encoding="utf-8"):
                count += 1
        self.assertEqual(1, count, "_get_software_roles should be defined in exactly one module")


    def test_reporting_symbols_defined(self) -> None:
        text = Path("scripts/validation/reporting.py").read_text(encoding="utf-8")
        self.assertIn("def print_validation_report", text)
        self.assertIn("def main", text)
        self.assertNotIn("import scripts.validate", text)
        self.assertNotIn("from scripts.validate", text)

    def test_validate_module_thin_ast(self) -> None:
        tree = ast.parse(Path("scripts/validate.py").read_text(encoding="utf-8"))
        defs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        self.assertEqual([], defs, "scripts/validate.py should not define classes/functions")

    def test_compat_imports(self) -> None:
        from scripts.validate import (
            DEFAULT_ALLOWED_RECORD_TYPES,
            ValidationIssue, VocabularyTerm, Vocabulary, PolicyRule, ResolvedNode,
            InstrumentPolicy, EventPolicy, EventValidationReport, InstrumentCompletenessReport,
            load_policy, validate_event_ledgers, validate_instrument_ledgers, print_validation_report, main, build_instrument_completeness_report, _is_valid_instrument_id,
        )
        self.assertIsNotNone(DEFAULT_ALLOWED_RECORD_TYPES)
        self.assertTrue(all(obj is not None for obj in (
            ValidationIssue, VocabularyTerm, Vocabulary, PolicyRule, ResolvedNode, InstrumentPolicy, EventPolicy,
            EventValidationReport, InstrumentCompletenessReport, load_policy, validate_event_ledgers,
            validate_instrument_ledgers, print_validation_report, main, build_instrument_completeness_report, _is_valid_instrument_id,
        )))


if __name__ == "__main__":
    unittest.main()
