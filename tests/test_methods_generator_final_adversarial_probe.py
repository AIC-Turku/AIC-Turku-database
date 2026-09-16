"""TEMPORARY audit probe: exercise the real generated Methods Generator inventory.

Intentionally fails after printing compact browser outputs. Audit-only; do not merge.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = [
    "route", "readout", "modality", "module", "scanner", "obj", "light",
    "filter", "splitter", "det", "magnification-changer", "optical-modulator",
    "illumination-logic", "confirmed",
]


def _compact(text: str) -> str:
    return " ".join(text.split())


def test_final_methods_generator_adversarial_probe(generated_dashboard: Path):
    data_path = generated_dashboard / "assets" / "instruments_data.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    instruments = payload.get("instruments", payload if isinstance(payload, list) else [])
    assert instruments, "generated Methods inventory is empty"

    template = Environment(loader=FileSystemLoader(ROOT / "scripts/templates")).get_template(
        "methods_generator.md.j2"
    )
    app = (ROOT / "assets/javascripts/methods_generator_app.js").read_text(encoding="utf-8")
    html = template.render(
        methods_generator_config_json=json.dumps({
            "instrument_data_url": "/instruments.json",
            "acknowledgements": {"standard": ""},
        }),
        facility_short_name="AIC Turku",
    )
    html = html.replace(
        '<script src="../assets/javascripts/methods_generator_app.js"></script>',
        "<script>" + app + "</script>",
    )
    bootstrap = (
        "window.fetch=async()=>({ok:true,json:async()=>"
        + json.dumps({"instruments": instruments})
        + "});"
    )

    executable = shutil.which("chromium") or shutil.which("chromium-browser")
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**({"executable_path": executable} if executable else {}))
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content("<script>" + bootstrap + "</script>" + html)
        expect(page.locator("#system-select")).to_be_enabled()

        for inst in instruments:
            inst_id = str(inst.get("id") or "")
            if not inst_id:
                continue
            page.select_option("#system-select", inst_id)
            display = str(inst.get("display_name") or inst_id)
            retired = bool(inst.get("retired"))

            option_rows = []
            for category in CATEGORIES:
                selector = f'input[data-category="{category}"]'
                count = page.locator(selector).count()
                rows = []
                for idx in range(count):
                    node = page.locator(selector).nth(idx)
                    rows.append({
                        "value": node.get_attribute("value") or "",
                        "label": node.get_attribute("data-display-label") or "",
                    })
                option_rows.append((category, rows))

            # Base output tests default/review behaviour.
            page.click("#add-btn")
            results.append({
                "instrument": display,
                "id": inst_id,
                "retired": retired,
                "case": "base",
                "selected": [],
                "output": _compact(page.locator("#output-text").input_value()),
            })
            page.click("#clear-btn")

            available = [(cat, rows) for cat, rows in option_rows if rows]
            if available:
                # First realistic cross-category combination.
                selected = []
                for cat, rows in available:
                    if cat == "readout":
                        continue
                    node = page.locator(f'input[data-category="{cat}"]').first
                    if not node.is_disabled():
                        node.check()
                        selected.append(f"{cat}:{rows[0]['label'] or rows[0]['value']}")
                page.click("#add-btn")
                results.append({
                    "instrument": display, "id": inst_id, "retired": retired,
                    "case": "first_each_category", "selected": selected,
                    "output": _compact(page.locator("#output-text").input_value()),
                })
                page.click("#clear-btn")
                for cat, _rows in available:
                    for node_idx in range(page.locator(f'input[data-category="{cat}"]:checked').count()):
                        pass
                    # clear all checked boxes defensively after Clear all (which clears entries, not selections)
                    nodes = page.locator(f'input[data-category="{cat}"]:checked')
                    while nodes.count():
                        nodes.first.uncheck()

                # Last options stress alternate routes/hardware and often specialist hardware.
                selected = []
                for cat, rows in available:
                    if cat == "readout":
                        continue
                    node = page.locator(f'input[data-category="{cat}"]').last
                    if not node.is_disabled():
                        node.check()
                        selected.append(f"{cat}:{rows[-1]['label'] or rows[-1]['value']}")
                page.click("#add-btn")
                results.append({
                    "instrument": display, "id": inst_id, "retired": retired,
                    "case": "last_each_category", "selected": selected,
                    "output": _compact(page.locator("#output-text").input_value()),
                })
                page.click("#clear-btn")
                for cat, _rows in available:
                    nodes = page.locator(f'input[data-category="{cat}"]:checked')
                    while nodes.count():
                        nodes.first.uncheck()

            # Route/readout pairs are tested separately because readouts are nested and route-bound.
            routes = page.locator('input[data-category="route"]')
            for route_idx in range(min(routes.count(), 2)):
                route = routes.nth(route_idx)
                if route.is_disabled():
                    continue
                route.check()
                route_id = route.get_attribute("value") or ""
                selected = ["route:" + (route.get_attribute("data-display-label") or route_id)]
                readouts = page.locator(f'input[data-category="readout"][data-route-id="{route_id}"]')
                if readouts.count():
                    readout = readouts.first
                    if not readout.is_disabled():
                        readout.check()
                        selected.append("readout:" + (readout.get_attribute("data-display-label") or readout.get_attribute("value") or ""))
                page.click("#add-btn")
                results.append({
                    "instrument": display, "id": inst_id, "retired": retired,
                    "case": f"route_{route_idx+1}_readout", "selected": selected,
                    "output": _compact(page.locator("#output-text").input_value()),
                })
                page.click("#clear-btn")
                if readouts.count() and readouts.first.is_checked():
                    readouts.first.uncheck()
                if route.is_checked():
                    route.uncheck()

        browser.close()

    print("FINAL_METHODS_ADVERSARIAL_RESULTS=" + json.dumps(results, ensure_ascii=False, separators=(",", ":")))
    print("FINAL_METHODS_PAGE_ERRORS=" + json.dumps(errors, ensure_ascii=False))
    raise AssertionError(f"intentional audit probe: {len(results)} real-browser configurations rendered")
