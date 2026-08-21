"""Small CARROT diversification challenger.

Some strong public tapes add a small CARROT crop because its price stays
above the seed cost while premium crops are crowded.  This policy converts
one future MELON seed lot to CARROT only when both observations support that
trade.  It preserves the market order slot and changes the matching PLANT
operations only for the converted lot.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .replay_policy import agent as replay_agent


_CARROT_MIN_PRICE = 42.0
_MELON_MAX_PRICE = 180.0
_STATE = {0: {"last_step": -1, "converted": 0}, 1: {"last_step": -1, "converted": 0}}


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _seat(obs: Any) -> int:
    try:
        return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0
    except (TypeError, ValueError):
        return 0


def _step(obs: Any) -> int:
    try:
        return max(0, int(_get(obs, "step", 0) or 0))
    except (TypeError, ValueError):
        return 0


def _trade_is_attractive(obs: Any) -> bool:
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    try:
        return (
            float(prices.get("CARROT", 0) or 0) >= _CARROT_MIN_PRICE
            and float(prices.get("MELON", 0) or 0) <= _MELON_MAX_PRICE
        )
    except (TypeError, ValueError):
        return False


def _convert_first_melon_seed(action: dict[str, Any]) -> int:
    """Convert one future MELON seed order and return its quantity."""
    for order in action["market"]:
        if len(order) < 3 or order[0] != "BUY_SEED" or order[1] != "MELON":
            continue
        try:
            quantity = max(0, int(order[2]))
        except (TypeError, ValueError):
            continue
        if quantity <= 0:
            continue
        order[1] = "CARROT"
        return quantity
    return 0


def agent(obs: Any) -> dict[str, Any]:
    seat = _seat(obs)
    step = _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "converted": 0}
        _STATE[seat] = state
    state["last_step"] = step
    base = replay_agent(obs)
    action = {
        "farmer": list(base.get("farmer") or ["PASS"]),
        "hands": [list(x or ["PASS"]) for x in base.get("hands", []) or []],
        "market": [list(x) for x in base.get("market", []) or []],
    }
    if not _trade_is_attractive(obs):
        return action
    state["converted"] += _convert_first_melon_seed(action)
    if state["converted"] <= 0:
        return action
    for operation in [action["farmer"], *action["hands"]]:
        if len(operation) >= 2 and operation[0] == "PLANT" and operation[1] == "MELON":
            operation[1] = "CARROT"
            state["converted"] -= 1
            break
    return action
