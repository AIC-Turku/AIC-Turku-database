from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/"
OUT = Path("presentation_redteam_artifacts")
OUT.mkdir(exist_ok=True)

VIEWPORTS = {
    "laptop": {"width": 1440, "height": 900},
    "projector": {"width": 1920, "height": 1080},
    "mobile": {"width": 390, "height": 844},
}

PAGES = {
    "home": "",
    "status": "status/",
    "objective_pool": "objective_pool/",
    "planning": "plan_experiments/",
    "virtual_microscope": "virtual_microscope/",
    "methods_generator": "methods_generator/",
    "retired": "retired/",
    "scope_3i": "instruments/scope-3i-csu-w1-spinning-disk/",
    "scope_stellaris": "instruments/scope-leica-stellaris-8-falcon-flim-resonant/",
    "scope_andor": "instruments/scope-andor-bc43/",
    "history": "instruments/scope-3i-csu-w1-spinning-disk/history/",
}

DEV_PATTERNS = [
    re.compile(r"\bTest Scope X1\b", re.I),
    re.compile(r"\bscope-testx1\b", re.I),
    re.compile(r"\bfixture\b", re.I),
    re.compile(r"\bTODO\b", re.I),
    re.compile(r"\bWIP\b", re.I),
    re.compile(r"\bplaceholder\b", re.I),
    re.compile(r"\bdebug\b", re.I),
    re.compile(r"temporary audit", re.I),
    re.compile(r"internal repair", re.I),
]

RAW_ID_RE = re.compile(r"\bscope-[a-z0-9][a-z0-9-]+\b")


def safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value)


def main() -> int:
    report: dict = {
        "base": BASE,
        "pages": {},
        "global": {"broken_links": [], "console_errors": [], "page_errors": [], "dev_text": [], "raw_ids": []},
        "interactions": {},
    }
    checked_links: dict[str, int] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for vp_name, vp in VIEWPORTS.items():
            context = browser.new_context(viewport=vp)
            page = context.new_page()
            console_errors: list[str] = []
            page_errors: list[str] = []
            page.on("console", lambda msg, bucket=console_errors: bucket.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc, bucket=page_errors: bucket.append(str(exc)))

            for page_name, rel in PAGES.items():
                url = urljoin(BASE, rel)
                key = f"{vp_name}:{page_name}"
                entry = {"url": url, "viewport": vp, "status": None}
                response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(400)
                entry["status"] = response.status if response else None
                entry["title"] = page.title()
                entry["h1"] = page.locator("h1").first.inner_text() if page.locator("h1").count() else ""
                body_text = page.locator("body").inner_text()
                entry["body_chars"] = len(body_text)
                entry["horizontal_overflow_px"] = page.evaluate("Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)")
                entry["body_scroll_height"] = page.evaluate("document.documentElement.scrollHeight")
                entry["viewport_height"] = vp["height"]
                entry["buttons"] = page.locator("button").all_inner_texts()
                entry["select_count"] = page.locator("select").count()
                entry["input_count"] = page.locator("input").count()

                dev_hits = sorted({pat.pattern for pat in DEV_PATTERNS if pat.search(body_text)})
                raw_ids = sorted(set(RAW_ID_RE.findall(body_text)))
                entry["dev_text_patterns"] = dev_hits
                entry["raw_ids"] = raw_ids[:30]

                # Detect elements that force the document wider than the viewport.
                offenders = page.evaluate(
                    """() => Array.from(document.querySelectorAll('body *')).map(el => {
                        const r = el.getBoundingClientRect();
                        return {tag: el.tagName, cls: el.className || '', id: el.id || '', left: r.left, right: r.right, width: r.width};
                    }).filter(x => x.width > 0 && (x.right > document.documentElement.clientWidth + 2 || x.left < -2)).slice(0, 25)"""
                )
                entry["overflow_offenders"] = offenders

                # Tables should either fit or live inside an explicitly scrollable wrapper.
                table_issues = page.evaluate(
                    """() => Array.from(document.querySelectorAll('table')).map(t => {
                        const r = t.getBoundingClientRect();
                        const p = t.parentElement;
                        const ps = p ? getComputedStyle(p) : null;
                        return {width: r.width, parentWidth: p ? p.getBoundingClientRect().width : 0,
                                parentOverflowX: ps ? ps.overflowX : '', text: (t.innerText || '').slice(0, 100)};
                    }).filter(x => x.width > x.parentWidth + 2 && !['auto','scroll'].includes(x.parentOverflowX))"""
                )
                entry["table_issues"] = table_issues

                # Check local links once globally.
                hrefs = page.locator("a[href]").evaluate_all("els => els.map(a => a.href)")
                for href in hrefs:
                    parsed = urlparse(href)
                    if parsed.hostname not in {"127.0.0.1", "localhost"}:
                        continue
                    clean = href.split("#", 1)[0]
                    if clean in checked_links:
                        continue
                    try:
                        res = context.request.get(clean, timeout=10000)
                        checked_links[clean] = res.status
                    except Exception:
                        checked_links[clean] = 0

                screenshot = OUT / f"baseline_{safe_name(vp_name)}_{safe_name(page_name)}.png"
                page.screenshot(path=str(screenshot), full_page=True)
                entry["screenshot"] = str(screenshot)
                report["pages"][key] = entry

            # Homepage search/filter only needs one interaction per viewport.
            page.goto(BASE, wait_until="domcontentloaded")
            if page.locator("#aicSearch").count():
                page.locator("#aicSearch").fill("Leica")
                page.wait_for_timeout(150)
                visible = page.locator(".aic-card:visible").count()
                report["interactions"][f"{vp_name}:home_search"] = {"visible_cards": visible}
                page.screenshot(path=str(OUT / f"baseline_{vp_name}_home_search.png"), full_page=True)
                page.locator("#aicSearch").fill("")
            if page.locator("#aicModality").count():
                options = page.locator("#aicModality option").all()
                if len(options) > 1:
                    value = options[1].get_attribute("value")
                    label = options[1].inner_text()
                    page.locator("#aicModality").select_option(value)
                    page.wait_for_timeout(150)
                    visible = page.locator(".aic-card:visible").count()
                    report["interactions"][f"{vp_name}:home_filter"] = {"option": label, "value": value, "visible_cards": visible}

            # Exercise visible action buttons on VM and Methods Generator without assuming internals.
            for feature, rel in [("virtual_microscope", "virtual_microscope/"), ("methods_generator", "methods_generator/")]:
                page.goto(urljoin(BASE, rel), wait_until="domcontentloaded")
                page.wait_for_timeout(300)
                buttons = page.locator("button:visible")
                button_texts = [x.strip() for x in buttons.all_inner_texts() if x.strip()]
                interaction = {"buttons": button_texts, "clicked": [], "post_click_text": ""}
                preferred = ["Suggest a configuration", "Generate", "Generate methods", "Create methods", "Update"]
                target = None
                for label in preferred:
                    loc = page.get_by_role("button", name=label, exact=False)
                    if loc.count():
                        target = loc.first
                        break
                if target is None and buttons.count():
                    target = buttons.first
                if target is not None:
                    try:
                        interaction["clicked"].append(target.inner_text())
                        target.click(timeout=5000)
                        page.wait_for_timeout(300)
                        interaction["post_click_text"] = page.locator("body").inner_text()[-1200:]
                    except Exception as exc:
                        interaction["click_error"] = str(exc)
                report["interactions"][f"{vp_name}:{feature}"] = interaction

            report["global"]["console_errors"].extend([f"{vp_name}: {x}" for x in console_errors])
            report["global"]["page_errors"].extend([f"{vp_name}: {x}" for x in page_errors])
            context.close()

        browser.close()

    report["global"]["broken_links"] = [
        {"url": url, "status": status} for url, status in sorted(checked_links.items()) if status == 0 or status >= 400
    ]
    for key, entry in report["pages"].items():
        for pat in entry["dev_text_patterns"]:
            report["global"]["dev_text"].append({"page": key, "pattern": pat})
        for raw in entry["raw_ids"]:
            report["global"]["raw_ids"].append({"page": key, "id": raw})

    Path(OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    summary = {
        "broken_links": len(report["global"]["broken_links"]),
        "console_errors": len(report["global"]["console_errors"]),
        "page_errors": len(report["global"]["page_errors"]),
        "dev_text_hits": len(report["global"]["dev_text"]),
        "raw_id_hits": len(report["global"]["raw_ids"]),
        "overflow_pages": [k for k, v in report["pages"].items() if v["horizontal_overflow_px"] > 2],
        "table_issue_pages": [k for k, v in report["pages"].items() if v["table_issues"]],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
