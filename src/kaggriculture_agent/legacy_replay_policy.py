"""Exact action-layer reconstruction of the 2026-08-07 high-score policy.

The public 1942.6 submission was made from commit ``286d730``.  Its action
tape is unchanged in the later policies; only experimental market overlays
were added around it.  This module exposes that old action layer explicitly
so it can be compared without changing the current production entry point.
"""

from __future__ import annotations

from typing import Any

from .replay_policy import (
    _ACTIONS,
    _align_hands,
    _copy_action,
    _farm,
    _get,
    _preempt_shift,
    _repay_shift,
    _safe_market,
    _step,
    _terminal_market,
    _weed_repair_action,
)


def agent(obs: Any) -> dict[str, Any]:
    """Run the old replay action layer without later economic overlays."""
    try:
        step = _step(obs)
        action = _weed_repair_action(obs, _copy_action(_ACTIONS[step]), step)
        action = _repay_shift(obs, action, step)
        action = _safe_market(obs, action)
        action = _preempt_shift(obs, action, step)
        action = _safe_market(obs, action)
        if step == len(_ACTIONS) - 1:
            action = _terminal_market(obs, action)
        return _align_hands(action, obs)
    except Exception:
        _seat, farm = _farm(obs)
        return {
            "farmer": ["PASS"],
            "hands": [["PASS"] for _ in (_get(farm, "hands", []) or [])],
            "market": [],
        }

