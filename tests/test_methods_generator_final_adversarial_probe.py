"""TEMPORARY audit probe: exercise the real built Methods Generator site.

Intentionally fails after printing compact browser outputs. Audit-only; do not merge.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = [
    "route", "readout", "modality", "module", "scanner", "obj", "light",
    "filter", "splitter", "det", "magnification-changer", "optical-modulator",
    "illumination-logic", "confirmed",
]


def _compact(text: str) -> str:
    return " ".join(text.split())


def test_final_methods_generator_adversarial_probe(generated_dashboard: Path, tmp_path: Path):
    data_path = generated_dashboard / "assets" / "instruments_data.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    instruments = payload.get("instruments", payload if isinstance(payload, list) else [])
    assert instruments, "generated Methods inventory is empty"

    site = tmp_path / "site"
    subprocess.run(
        ["mkdocs", "build", "--strict", "--site-dir", str(site)],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(site)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"

    executable = shutil.which("chromium") or shutil.which("chromium-browser")
    results = []
    errors = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(**({"executable_path": executable} if executable else {}))
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(origin + "/") else route.abort())
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "/methods_generator/")
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
                    rows = []
                    for idx in range(page.locator(selector).count()):
                        node = page.locator(selector).nth(idx)
                        rows.append({
                            "value": node.get_attribute("value") or "",
                            "label": node.get_attribute("data-display-label") or "",
                        })
                    option_rows.append((category, rows))

                page.click("#add-btn")
                results.append({
                    "instrument": display, "id": inst_id, "retired": retired,
                    "case": "base", "selected": [],
                    "output": _compact(page.locator("#output-text").input_value()),
                })
                page.click("#clear-btn")

                available = [(cat, rows) for cat, rows in option_rows if rows]
                for case_name, which in (("first_each_category", "first"), ("last_each_category", "last")):
                    selected = []
                    for cat, rows in available:
                        if cat == "readout":
                            continue
                        locator = page.locator(f'input[data-category="{cat}"]')
                        if not locator.count():
                            continue
                        node = locator.first if which == "first" else locator.last
                        if not node.is_disabled():
                            node.check()
                            selected.append(f"{cat}:{node.get_attribute('data-display-label') or node.get_attribute('value') or ''}")
                    page.click("#add-btn")
                    results.append({
                        "instrument": display, "id": inst_id, "retired": retired,
                        "case": case_name, "selected": selected,
                        "output": _compact(page.locator("#output-text").input_value()),
                    })
                    page.click("#clear-btn")
                    for cat, _rows in available:
                        nodes = page.locator(f'input[data-category="{cat}"]:checked')
                        while nodes.count():
                            nodes.first.uncheck()

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

            context.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    print("FINAL_METHODS_ADVERSARIAL_RESULTS=" + json.dumps(results, ensure_ascii=False, separators=(",", ":")))
    print("FINAL_METHODS_PAGE_ERRORS=" + json.dumps(errors, ensure_ascii=False))
    raise AssertionError(f"intentional audit probe: {len(results)} real-browser configurations rendered")
