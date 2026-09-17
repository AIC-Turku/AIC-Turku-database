"""Compatibility wrapper for the original 116-scenario replay harness.

The historical transcript contains observation lines (``[state] ...``), a few
shorthand untick actions without a section name, and one detector whose display
label was intentionally made more explicit by PR #460. Those are transcript/UI
compatibility details, not generator failures. This wrapper teaches the replay
harness those three historical conventions without changing any scenario action.
"""

from __future__ import annotations

from typing import Any

import scripts.replay_methods_116_audit as base
from playwright.sync_api import Page


def _historical_pick_control(
    page: Page, target: str, section: str, want_checked: bool
) -> tuple[str, str, float]:
    try:
        return base.pick_control(page, target, section, want_checked)
    except RuntimeError:
        # One old scenario identified an LSM 510 detector only as "Zeiss — Zeiss".
        # PR #460 deliberately exposes the recorded placeholder nature of that same
        # component as "Unknown PMT — Zeiss". Match it only when the old label is a
        # repeated manufacturer and there is exactly one visible candidate from that
        # manufacturer in the requested section. Nothing scientific is inferred.
        target_n = base.norm(target)
        parts = [part.strip() for part in target_n.split(" - ") if part.strip()]
        if len(parts) == 2 and parts[0] == parts[1]:
            section_id = base.SECTION_IDS.get(base.norm(section))
            rows = [
                row for row in base.control_rows(page, section_id)
                if row["visible"] and not row["disabled"]
            ]
            if want_checked:
                remaining = [row for row in rows if not row["checked"]]
                if remaining:
                    rows = remaining
            else:
                remaining = [row for row in rows if row["checked"]]
                if remaining:
                    rows = remaining
            manufacturer = parts[0]
            matches = [
                row for row in rows
                if base.norm(row["label"]).endswith(f" - {manufacturer}")
            ]
            if len(matches) == 1:
                row = matches[0]
                return row["id"], row["label"], 0.95
        raise


def _historical_apply_action(
    page: Page, action: str, trace: list[dict[str, Any]]
) -> None:
    # These lines were observations written by the first audit after an action,
    # not actions performed by the user. Preserve them in the trace but do not try
    # to click anything.
    if action.startswith("[state]"):
        trace.append({"action": action, "resolved": "historical state observation", "score": 1.0})
        return

    if action.startswith("tick:") or action.startswith("untick:"):
        want_checked = action.startswith("tick:")
        payload = action.split(":", 1)[1].strip()
        if " :: " not in payload:
            # Several historical steps shortened an untick to the label alone. Search
            # the visible controls globally; because untick prefers checked controls,
            # this remains deterministic and does not guess an unavailable item.
            control_id, resolved, score = _historical_pick_control(
                page, payload, "", want_checked
            )
            locator = page.locator(f"#{control_id}")
            if want_checked:
                locator.check()
            else:
                locator.uncheck()
            page.wait_for_timeout(20)
            trace.append({
                "action": action,
                "resolved": resolved,
                "score": round(score, 3),
            })
            return

    # Temporarily substitute the stricter historical matcher so the base action
    # implementation also benefits from the explicit placeholder-label rule above.
    original = base.pick_control
    try:
        base.pick_control = _historical_pick_control
        return base.apply_action(page, action, trace)
    finally:
        base.pick_control = original


base.apply_action = _historical_apply_action

if __name__ == "__main__":
    raise SystemExit(base.main())
