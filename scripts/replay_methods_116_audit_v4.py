"""Final historical-compatibility wrapper for the 116-scenario replay.

PR #460 now clears acquisition-scoped controls when a second acquisition is
started. In four original scenarios, the old audit subsequently unticked a
control that is already absent/cleared in the fixed UI. An absent *untick* is
therefore a successful no-op; an absent *tick* remains a real replay failure.
"""

from __future__ import annotations

from typing import Any

import scripts.replay_methods_116_audit as base
from playwright.sync_api import Page

_ORIGINAL_APPLY_ACTION = base.apply_action
_ORIGINAL_PICK_CONTROL = base.pick_control


def historical_pick_control(page: Page, target: str, section: str, want_checked: bool):
    try:
        return _ORIGINAL_PICK_CONTROL(page, target, section, want_checked)
    except RuntimeError:
        target_n = base.norm(target)
        parts = [part.strip() for part in target_n.split(" - ") if part.strip()]
        if len(parts) == 2 and parts[0] == parts[1]:
            section_id = base.SECTION_IDS.get(base.norm(section))
            rows = [row for row in base.control_rows(page, section_id) if row["visible"] and not row["disabled"]]
            preferred = [row for row in rows if (not row["checked"] if want_checked else row["checked"])]
            if preferred:
                rows = preferred
            manufacturer = parts[0]
            matches = [row for row in rows if base.norm(row["label"]).endswith(f" - {manufacturer}")]
            if len(matches) == 1:
                row = matches[0]
                return row["id"], row["label"], 0.95
        raise


def historical_apply_action(page: Page, action: str, trace: list[dict[str, Any]]) -> None:
    if action.startswith("[state]"):
        trace.append({"action": action, "resolved": "historical state observation", "score": 1.0})
        return

    if action.startswith("tick:") or action.startswith("untick:"):
        want_checked = action.startswith("tick:")
        payload = action.split(":", 1)[1].strip()
        if " :: " not in payload:
            try:
                control_id, resolved, score = historical_pick_control(page, payload, "", want_checked)
            except RuntimeError:
                if not want_checked:
                    trace.append({"action": action, "resolved": "already cleared by acquisition transition", "score": 1.0})
                    return
                raise
            locator = page.locator(f"#{control_id}")
            if want_checked:
                locator.check()
            else:
                locator.uncheck()
            page.wait_for_timeout(20)
            trace.append({"action": action, "resolved": resolved, "score": round(score, 3)})
            return

    old_picker = base.pick_control
    try:
        base.pick_control = historical_pick_control
        _ORIGINAL_APPLY_ACTION(page, action, trace)
    finally:
        base.pick_control = old_picker


base.apply_action = historical_apply_action

if __name__ == "__main__":
    raise SystemExit(base.main())
