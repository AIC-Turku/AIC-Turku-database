"""Replay the original 116 Methods Generator black-box scenarios.

This is a disposable audit harness for PR #460. It deliberately recovers the
original action log from commit 0e956b5 so the replay is scenario-for-scenario,
then drives the *current rendered MkDocs page* through Chromium/Playwright.
It does not construct DTOs or call the generator directly.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright

AUDIT_COMMIT = "0e956b5a208f432c1829a12935ea5eb155230789"
TRANSCRIPT_PATH = "docs/audits/methods_generator_ui_audit_transcripts.md"
DEFAULT_URL = "http://127.0.0.1:8000/methods_generator/"

SECTION_IDS = {
    "imaging method": "method-list",
    "light path and readouts": "route-list",
    "light path / readouts": "route-list",
    "measurement readouts": "route-list",
    "readouts": "route-list",
    "confirmed acquisition actions": "confirmed-list",
    "objectives": "obj-list",
    "light sources": "light-list",
    "filters and dichroics": "filter-list",
    "beam splitters": "splitter-list",
    "splitters": "splitter-list",
    "detectors": "det-list",
    "hardware modules and environmental control": "module-list",
    "hardware modules": "module-list",
    "scanner": "scanner-list",
    "scanners": "scanner-list",
    "magnification changers": "magnification-changer-list",
    "magnification changer": "magnification-changer-list",
    "optical modulators": "optical-modulator-list",
    "illumination control": "illumination-logic-list",
    "modalities": "modality-list",
    "modality": "modality-list",
}


@dataclass
class Scenario:
    scenario_id: str
    title: str
    actions: list[str]


def norm(value: str) -> str:
    value = value.replace("×", "x").replace("–", "-").replace("—", "-")
    value = value.replace("µ", "u").replace("μ", "u")
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value


def recover_transcript() -> str:
    return subprocess.check_output(
        ["git", "show", f"{AUDIT_COMMIT}:{TRANSCRIPT_PATH}"],
        text=True,
        encoding="utf-8",
    )


def parse_scenarios(text: str) -> list[Scenario]:
    header_re = re.compile(r"^###\s+([A-D]\d{2})\s+—\s+(.+?)\s*$", re.MULTILINE)
    headers = list(header_re.finditer(text))
    scenarios: list[Scenario] = []
    for i, match in enumerate(headers):
        start = match.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        block = text[start:end]
        action_match = re.search(
            r"\*\*Selections made in the UI \(in order\):\*\*\s*```\s*\n(.*?)\n```",
            block,
            re.DOTALL,
        )
        if not action_match:
            raise RuntimeError(f"No action block for {match.group(1)}")
        actions = [line.strip() for line in action_match.group(1).splitlines() if line.strip()]
        scenarios.append(Scenario(match.group(1), match.group(2).strip(), actions))
    if len(scenarios) != 116:
        raise RuntimeError(f"Expected 116 scenarios, recovered {len(scenarios)}")
    return scenarios


def option_for_instrument(page: Page, target: str) -> str:
    options = page.locator("#system-select option").evaluate_all(
        "els => els.map(e => ({value:e.value, text:(e.textContent||'').trim()})).filter(x => x.value)"
    )
    target_n = norm(target)
    exact = [row for row in options if norm(row["text"]) == target_n]
    if exact:
        return exact[0]["value"]
    prefix = [row for row in options if norm(row["text"]).startswith(target_n) or target_n.startswith(norm(row["text"]))]
    if prefix:
        return prefix[0]["value"]
    scored = sorted(
        ((difflib.SequenceMatcher(None, target_n, norm(row["text"])).ratio(), row) for row in options),
        reverse=True,
        key=lambda x: x[0],
    )
    if scored and scored[0][0] >= 0.68:
        return scored[0][1]["value"]
    raise RuntimeError(f"Instrument not found: {target!r}; options={[r['text'] for r in options]}")


def control_rows(page: Page, container_id: str | None = None) -> list[dict[str, Any]]:
    selector = f"#{container_id} input" if container_id else "#hardware-options input"
    return page.locator(selector).evaluate_all(
        """els => els.map(e => ({
            id: e.id,
            value: e.value || '',
            checked: !!e.checked,
            disabled: !!e.disabled,
            visible: e.offsetParent !== null,
            category: e.dataset.category || '',
            label: e.labels && e.labels.length ? (e.labels[0].textContent || '').trim() :
                   ((e.parentElement && e.parentElement.textContent) || '').trim()
        }))"""
    )


def pick_control(page: Page, target: str, section: str, want_checked: bool) -> tuple[str, str, float]:
    section_id = SECTION_IDS.get(norm(section))
    rows = [row for row in control_rows(page, section_id) if row["visible"] and not row["disabled"]]
    if not rows:
        rows = [row for row in control_rows(page) if row["visible"] and not row["disabled"]]
    if want_checked:
        unchecked = [row for row in rows if not row["checked"]]
        if unchecked:
            rows = unchecked
    else:
        checked = [row for row in rows if row["checked"]]
        if checked:
            rows = checked

    target_n = norm(target)
    ranked: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        label_n = norm(row["label"])
        if label_n == target_n:
            score = 1.0
        elif label_n.startswith(target_n) or target_n.startswith(label_n):
            score = 0.96
        elif target_n in label_n or label_n in target_n:
            score = 0.92
        else:
            # The old audit logged metadata after an em dash. Compare the core label too.
            target_core = target_n.split(" - ", 1)[0]
            label_core = label_n.split(" - ", 1)[0]
            if target_core == label_core:
                score = 0.95
            elif target_core in label_core or label_core in target_core:
                score = 0.90
            else:
                score = difflib.SequenceMatcher(None, target_n, label_n).ratio()
        ranked.append((score, row))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if not ranked or ranked[0][0] < 0.62:
        available = [row["label"] for row in rows]
        raise RuntimeError(
            f"Control not found in {section!r}: {target!r}; best={ranked[:3]}; available={available}"
        )
    score, row = ranked[0]
    return row["id"], row["label"], score


def apply_action(page: Page, action: str, trace: list[dict[str, Any]]) -> None:
    if action.startswith("select instrument:"):
        target = action.split(":", 1)[1].strip()
        value = option_for_instrument(page, target)
        page.select_option("#system-select", value=value)
        page.wait_for_timeout(25)
        trace.append({"action": action, "resolved": value, "score": 1.0})
        return

    if action.startswith("tick:") or action.startswith("untick:"):
        want_checked = action.startswith("tick:")
        payload = action.split(":", 1)[1].strip()
        if " :: " not in payload:
            raise RuntimeError(f"Malformed tick action: {action}")
        section, target = payload.split(" :: ", 1)
        control_id, resolved, score = pick_control(page, target, section, want_checked)
        locator = page.locator(f"#{control_id}")
        if want_checked:
            locator.check()
        else:
            locator.uncheck()
        page.wait_for_timeout(20)
        trace.append({"action": action, "resolved": resolved, "score": round(score, 3)})
        return

    if action.startswith("reference:"):
        value = action.split(":", 1)[1].strip()
        page.fill("#session-label", value)
        page.wait_for_timeout(20)
        trace.append({"action": action, "resolved": value, "score": 1.0})
        return

    if action.startswith("click:"):
        target = norm(action.split(":", 1)[1])
        button_ids = {
            "add to methods": "add-btn",
            "clear all": "clear-btn",
            "start another acquisition": "new-acquisition-btn",
            "copy draft": "copy-btn",
        }
        button_id = button_ids.get(target)
        if not button_id:
            raise RuntimeError(f"Unknown click target: {action}")
        page.click(f"#{button_id}")
        page.wait_for_timeout(25)
        trace.append({"action": action, "resolved": button_id, "score": 1.0})
        return

    raise RuntimeError(f"Unrecognised action: {action}")


def checked_state(page: Page) -> list[dict[str, Any]]:
    return [row for row in control_rows(page) if row["checked"]]


def run_scenario(browser, base_url: str, scenario: Scenario) -> dict[str, Any]:
    context = browser.new_context()
    page = context.new_page()
    errors: list[str] = []
    console_errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    trace: list[dict[str, Any]] = []
    failure = ""
    try:
        page.goto(base_url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_function("document.querySelectorAll('#system-select option').length > 1", timeout=30_000)
        for action in scenario.actions:
            apply_action(page, action, trace)
    except Exception as exc:  # keep the remaining scenarios running
        failure = f"{type(exc).__name__}: {exc}"
    output = page.locator("#output-text").input_value() if page.locator("#output-text").count() else ""
    status = page.locator("#methods-selection-status").text_content() if page.locator("#methods-selection-status").count() else ""
    result = {
        "id": scenario.scenario_id,
        "title": scenario.title,
        "actions": scenario.actions,
        "trace": trace,
        "execution_error": failure,
        "page_errors": errors,
        "console_errors": console_errors,
        "status": status or "",
        "checked": checked_state(page),
        "output": output,
    }
    context.close()
    return result


def write_markdown(results: list[dict[str, Any]], path: Path) -> None:
    executed = sum(not r["execution_error"] for r in results)
    exact = sum(all(t.get("score", 0) == 1.0 for t in r["trace"] if "score" in t) for r in results if not r["execution_error"])
    lines = [
        "# PR #460 — original 116-scenario replay",
        "",
        f"Scenarios recovered: **{len(results)}**  ",
        f"Executed to completion: **{executed}**  ",
        f"All controls resolved exactly: **{exact}**",
        "",
    ]
    for row in results:
        lines += [f"## {row['id']} — {row['title']}", ""]
        if row["execution_error"]:
            lines += [f"**EXECUTION ERROR:** `{row['execution_error']}`", ""]
        fuzzy = [t for t in row["trace"] if t.get("score", 1.0) < 1.0]
        if fuzzy:
            lines.append("**Fuzzy control resolutions:**")
            lines.append("")
            for t in fuzzy:
                lines.append(f"- `{t['action']}` → `{t.get('resolved','')}` ({t.get('score')})")
            lines.append("")
        if row["page_errors"] or row["console_errors"]:
            lines.append(f"**Browser errors:** {row['page_errors'] + row['console_errors']}")
            lines.append("")
        lines += ["```text", row["output"], "```", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--json", default="/tmp/methods-116-rerun.json")
    parser.add_argument("--markdown", default="/tmp/methods-116-rerun.md")
    args = parser.parse_args()

    scenarios = parse_scenarios(recover_transcript())
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        results = [run_scenario(browser, args.url, scenario) for scenario in scenarios]
        browser.close()

    Path(args.json).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(results, Path(args.markdown))

    errors = [r for r in results if r["execution_error"] or r["page_errors"]]
    fuzzy = [
        (r["id"], t)
        for r in results
        for t in r["trace"]
        if t.get("score", 1.0) < 0.90
    ]
    print(f"Recovered {len(results)} scenarios; execution errors={len(errors)}; low-confidence resolutions={len(fuzzy)}")
    if errors:
        for row in errors:
            print(row["id"], row["execution_error"], row["page_errors"])
        return 2
    if fuzzy:
        for scenario_id, item in fuzzy:
            print("FUZZY", scenario_id, item)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
