from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected marker not found in {path}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Preserve hardware choices that remain valid on the newly selected route.
# updateHardwareVisibility itself drops anything that is not present on that route,
# so retaining compatible selections is safe and avoids surprising users.
replace_once(
    "assets/javascripts/methods_generator_app.js",
    '''        const target = event?.target;
        const selectedRouteBefore = getCheckedIds("route")[0] || "";
        let preserveHardware = true;
        if (target?.dataset.category === "route" && target.checked) {
            preserveHardware = false;
            document.querySelectorAll('input[id^="readout-"]').forEach(readout => {
                if (readout.dataset.routeId !== target.value) readout.checked = false;
            });
        } else if (target?.dataset.category === "readout" && target.checked) {
            const targetRouteId = cleanText(target.dataset.routeId);
            preserveHardware = selectedRouteBefore === targetRouteId;
            document.querySelectorAll('input[id^="route-"]').forEach(route => {
                if (route.value === targetRouteId) route.checked = true;
            });
''',
    '''        const target = event?.target;
        const preserveHardware = true;
        if (target?.dataset.category === "route" && target.checked) {
            document.querySelectorAll('input[id^="readout-"]').forEach(readout => {
                if (readout.dataset.routeId !== target.value) readout.checked = false;
            });
        } else if (target?.dataset.category === "readout" && target.checked) {
            const targetRouteId = cleanText(target.dataset.routeId);
            document.querySelectorAll('input[id^="route-"]').forEach(route => {
                if (route.value === targetRouteId) route.checked = true;
            });
''',
)

# The old regression expected an invalid two-route acquisition. Routes are now
# deliberately radios: selecting another path replaces the first one.
replace_once(
    "tests/test_methods_generator_grounding_regressions.py",
    '''    def test_several_routes_in_one_acquisition_are_questioned(self):
        instrument = _instrument()
        instrument["hardware"]["optical_path"]["authoritative_route_contract"]["routes"].append(
            {"id": "confocal", "display_label": "Point-scanning confocal", "relevant_hardware": {}})
        self.open_methods(instrument)
        self.page.check("#route-0")
        self.page.check("#route-1")
        self.page.click("#add-btn")
        self.assertIn("optical routes are reported for a single acquisition", self.output())
''',
    '''    def test_one_acquisition_cannot_select_several_routes(self):
        instrument = _instrument()
        instrument["hardware"]["optical_path"]["authoritative_route_contract"]["routes"].append(
            {"id": "confocal", "display_label": "Point-scanning confocal", "relevant_hardware": {}})
        self.open_methods(instrument)
        self.page.check("#route-0")
        expect(self.page.locator("#route-0")).to_be_checked()
        self.page.check("#route-1")
        expect(self.page.locator("#route-0")).not_to_be_checked()
        expect(self.page.locator("#route-1")).to_be_checked()
        self.page.click("#add-btn")
        self.assertNotIn("optical routes are reported for a single acquisition", self.output())
        self.assertIn("Point-scanning confocal route", self.output())
''',
)

# Route controls are radios now: switch directly to the second route rather than
# unchecking the first. The test still checks the important contract: a compatible
# light choice survives route activation through a readout, then incompatible state
# disappears when the user moves to a different physical path.
replace_once(
    "tests/test_audit_regressions.py",
    '''        expect(self.page.locator("#route-0")).to_be_checked()
        expect(self.page.locator("#light-0")).to_be_checked()
        self.page.uncheck("#route-0")
        expect(self.page.locator("#readout-0-0")).not_to_be_checked()
        self.page.check("#route-1")
        expect(self.page.locator("#light-list input")).to_have_count(0)
''',
    '''        expect(self.page.locator("#route-0")).to_be_checked()
        expect(self.page.locator("#light-0")).to_be_checked()
        self.page.check("#route-1")
        expect(self.page.locator("#route-0")).not_to_be_checked()
        expect(self.page.locator("#readout-0-0")).not_to_be_checked()
        expect(self.page.locator("#light-list input")).to_have_count(0)
''',
)

for rel in (
    "scripts/_tmp_fix_fullsuite_method_regressions.py",
    ".github/workflows/tmp-fix-fullsuite-method-regressions.yml",
):
    path = ROOT / rel
    if path.exists():
        path.unlink()
