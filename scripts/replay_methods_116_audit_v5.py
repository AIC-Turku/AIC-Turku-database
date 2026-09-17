"""Replay the original 116 scenarios with their historical method-selection intent.

The original audit was recorded when ``Imaging method`` was a radio group. PR
#460 intentionally made that section multi-select. A literal replay therefore
changes the meaning of actions such as "tick TIRF" after "Widefield": it adds a
second method instead of switching methods. For a before/after regression audit,
this wrapper restores only that historical interaction semantic while still
using PR #460's current rendered UI and generator for every result.
"""

from __future__ import annotations

from typing import Any

import scripts.replay_methods_116_audit as base
import scripts.replay_methods_116_audit_v4 as compat
from playwright.sync_api import Page


def historical_radio_apply_action(page: Page, action: str, trace: list[dict[str, Any]]) -> None:
    prefix = "tick: Imaging method :: "
    if action.startswith(prefix):
        target = action[len(prefix):].strip()
        # Match the target against all visible method controls before changing the
        # state. Then make the checkbox state look exactly as the old radio group
        # would have looked at the moment its change event fired: target checked,
        # every other method unchecked. Only the target receives a change event so
        # #460's current transition logic is exercised once, not twice.
        rows = [
            row for row in base.control_rows(page, "method-list")
            if row["visible"] and not row["disabled"]
        ]
        target_id, resolved, score = compat.historical_pick_control(
            page, target, "Imaging method", True
        )
        page.locator("#method-list input").evaluate_all(
            "(els, targetId) => els.forEach(e => { if (e.id !== targetId) e.checked = false; })",
            target_id,
        )
        target_locator = page.locator(f"#{target_id}")
        if target_locator.is_checked():
            # It can already be checked on a round trip in the new multi-select UI.
            # Dispatch the same change event the historical radio click generated.
            target_locator.dispatch_event("change")
        else:
            target_locator.check()
        page.wait_for_timeout(20)
        trace.append({"action": action, "resolved": resolved, "score": round(score, 3)})
        return

    compat.historical_apply_action(page, action, trace)


base.apply_action = historical_radio_apply_action

if __name__ == "__main__":
    raise SystemExit(base.main())
