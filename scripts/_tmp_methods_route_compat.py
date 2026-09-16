from pathlib import Path

root = Path(__file__).resolve().parents[1]

app = root / "assets/javascripts/methods_generator_app.js"
text = app.read_text(encoding="utf-8")
old = '''            routeCheckbox.type = "radio";\n            routeCheckbox.name = "methods-optical-route";\n            routeCheckbox.id = `route-${routeIdx}`;'''
new = '''            routeCheckbox.type = "checkbox";\n            routeCheckbox.id = `route-${routeIdx}`;'''
if old not in text:
    raise RuntimeError("route radio anchor not found")
text = text.replace(old, new, 1)
old = '        toggleSectionVisibility("section-route", methodCount === 0 && routeCount > 0);'
new = '        toggleSectionVisibility("section-route", routeCount > 0);'
if old not in text:
    raise RuntimeError("route visibility anchor not found")
app.write_text(text.replace(old, new, 1), encoding="utf-8")

test = root / "tests/test_methods_generator_method_first.py"
text = test.read_text(encoding="utf-8")
text = text.replace('expect(self.page.locator("#section-route")).to_be_hidden()', 'expect(self.page.locator("#section-route")).to_be_visible()', 1)
test.write_text(text, encoding="utf-8")
