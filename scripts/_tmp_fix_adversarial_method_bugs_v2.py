from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]

# Apply the original patch first. It intentionally removes its own workflow/script.
runpy.run_path(str(ROOT / "scripts/_tmp_fix_adversarial_method_bugs.py"), run_name="__main__")


def replace_once(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected marker not found in {path}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


test = "tests/test_methods_generator_method_first.py"

# The fixture now deliberately has a third, structured empty position.
replace_once(
    test,
    '''        positions = self.page.locator('#filter-list input[id^="filterposition-"]')
        self.assertEqual(positions.count(), 2)
        self.assertEqual(positions.nth(0).get_attribute("type"), "radio")
''',
    '''        positions = self.page.locator('#filter-list input[id^="filterposition-"]')
        self.assertEqual(positions.count(), 3)
        self.assertEqual(positions.nth(0).get_attribute("type"), "radio")
''',
)

# Method switching now proactively clears route-specific state. Assert the safety
# invariant directly instead of requiring the old post-hoc warning string.
replace_once(
    test,
    '''        expect(self.page.locator("#light-list")).to_contain_text("Transmitted lamp")
        expect(self.page.locator("#light-list")).not_to_contain_text("488 nm laser")
        expect(self.page.locator("#methods-selection-status")).to_contain_text("cleared because it is not available")
''',
    '''        expect(self.page.locator("#light-list")).to_contain_text("Transmitted lamp")
        expect(self.page.locator("#light-list")).not_to_contain_text("488 nm laser")
        self.assertEqual(self.page.locator('#filter-list input:checked').count(), 0)
        self.assertEqual(self.page.locator('#light-list input:checked').count(), 0)
''',
)

# Clean up this second one-shot helper too.
this_file = ROOT / "scripts/_tmp_fix_adversarial_method_bugs_v2.py"
if this_file.exists():
    this_file.unlink()
