"""Historical 116-scenario replay adapted to current intentional software defaults.

Current main automatically reports exactly one recorded acquisition-software row.
Older audit transcripts explicitly ticked that sentence under Confirmed acquisition
actions. This wrapper treats only that now-redundant action as a verified no-op,
after checking the current rendered instrument export has exactly one real
acquisition-software row and that its name matches the historical sentence.
Multiple acquisition-software choices still go through the normal browser action.
"""

from __future__ import annotations

from typing import Any

import scripts.replay_methods_116_audit as base
import scripts.replay_methods_116_audit_v5 as v5
from playwright.sync_api import Page

_ORIGINAL = base.apply_action
_SOFTWARE_PREFIX = (
    "tick: Confirmed acquisition actions :: "
    "Instrument control and image acquisition were performed using "
)
_PLACEHOLDERS = {"unknown", "n/a", "na", "none", "not applicable", "tbd", "-", "--", "?"}


def _sole_acquisition_software(page: Page) -> dict[str, Any] | None:
    instrument_id = page.locator("#system-select").input_value()
    if not instrument_id:
        return None
    row = page.evaluate(
        """async (instrumentId) => {
            const configNode = document.getElementById('methods-generator-config');
            let url = '../assets/instruments_data.json';
            try {
                const cfg = JSON.parse(configNode?.textContent || '{}');
                if (cfg.instrument_data_url) url = cfg.instrument_data_url;
            } catch (_) {}
            const response = await fetch(url, {headers: {Accept: 'application/json'}});
            if (!response.ok) throw new Error(`instrument export HTTP ${response.status}`);
            const payload = await response.json();
            const instruments = Array.isArray(payload) ? payload : (payload?.instruments || []);
            const inst = instruments.find(item => item?.id === instrumentId);
            if (!inst) return null;
            const placeholders = new Set(['unknown','n/a','na','none','not applicable','tbd','-','--','?']);
            const rows = (Array.isArray(inst.software) ? inst.software : []).filter(item => {
                const name = String(item?.name || '').trim();
                const role = String(item?.role || '').trim().toLowerCase();
                return role === 'acquisition' && name && !placeholders.has(name.toLowerCase());
            });
            return rows.length === 1 ? rows[0] : null;
        }""",
        instrument_id,
    )
    return row if isinstance(row, dict) else None


def software_default_apply_action(page: Page, action: str, trace: list[dict[str, Any]]) -> None:
    try:
        _ORIGINAL(page, action, trace)
        return
    except RuntimeError:
        if not action.startswith(_SOFTWARE_PREFIX):
            raise

        # If acquisition-software choices remain visible, this is not the sole-row
        # default case and the normal failure must remain visible to the audit.
        visible_software_controls = [
            row for row in base.control_rows(page, "confirmed-list")
            if row["visible"]
            and base.norm(row["label"]).startswith(
                base.norm("Instrument control and image acquisition were performed using ")
            )
        ]
        if visible_software_controls:
            raise

        software = _sole_acquisition_software(page)
        if not software:
            raise
        name = str(software.get("name") or "").strip()
        if not name or name.lower() in _PLACEHOLDERS or base.norm(name) not in base.norm(action):
            raise

        trace.append({
            "action": action,
            "resolved": f"already automatic sole acquisition software: {name}",
            "score": 1.0,
        })


base.apply_action = software_default_apply_action

if __name__ == "__main__":
    raise SystemExit(base.main())
