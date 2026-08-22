"""Small long-cycle crop replacement challenger.

The replay buys a first eight-unit STRAWBERRY batch.  When the observed
WHEAT return per growth day is clearly better, this experiment converts that
complete batch to WHEAT.  The quantity is never shortened: every converted
seed has a matching future PLANT rewrite.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .replay_policy import agent as replay_agent


_STATE = {0: {"last_step": -1, "pending": 0, "opened": False}, 1: {"last_step": -1, "pending": 0, "opened": False}}
_BATCH_SIZE = 8
_MIN_RATIO = 1.15


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


def _attractive(obs: Any) -> bool:
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    try:
        wheat_per_day = float(prices.get("WHEAT", 0) or 0) / 2
        strawberry_per_day = float(prices.get("STRAWBERRY", 0) or 0) / 10
    except (TypeError, ValueError):
        return False
    return wheat_per_day >= strawberry_per_day * _MIN_RATIO


def _copy_action(action: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in action.get("hands", []) or []],
        "market": [list(order) for order in action.get("market", []) or []],
    }


def _open(action: dict[str, Any], state: dict[str, Any]) -> bool:
    if state["opened"]:
        return False
    for order in action["market"]:
        if len(order) < 3 or order[0] != "BUY_SEED" or order[1] != "STRAWBERRY":
            continue
        try:
            quantity = int(order[2])
        except (TypeError, ValueError):
            continue
        if quantity != _BATCH_SIZE:
            continue
        order[1] = "WHEAT"
        state["pending"] = quantity
        state["opened"] = True
        return True
    return False


def _rewrite_plant(action: dict[str, Any], state: dict[str, Any]) -> None:
    if state["pending"] <= 0:
        return
    for operation in [action["farmer"], *action["hands"]]:
        if len(operation) >= 2 and operation[0] == "PLANT" and operation[1] == "STRAWBERRY":
            operation[1] = "WHEAT"
            state["pending"] -= 1
            return


def _rewrite_sale(obs: Any, action: dict[str, Any]) -> None:
    shed = _get(_get(obs, "private", {}) or {}, "shed", {}) or {}
    wheat = max(0, int(shed.get("WHEAT", 0) or 0))
    if wheat <= 0:
        return
    for order in action["market"]:
        if len(order) >= 3 and order[0] == "SELL" and order[1] == "STRAWBERRY":
            order[1] = "WHEAT"
            order[2] = min(int(order[2]), wheat)
            return


def agent(obs: Any) -> dict[str, Any]:
    seat = _seat(obs)
    step = _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "pending": 0, "opened": False}
        _STATE[seat] = state
    state["last_step"] = step
    action = _copy_action(replay_agent(obs))
    if step == 0 and _attractive(obs):
        _open(action, state)
    _rewrite_plant(action, state)
    if state["opened"]:
        _rewrite_sale(obs, action)
    return action
