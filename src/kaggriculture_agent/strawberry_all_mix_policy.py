"""Full STRAWBERRY-to-WHEAT portfolio challenger.

This keeps replay movement and harvest timing but converts every STRAWBERRY
seed lot to WHEAT when the observed growth-adjusted WHEAT return is better.
Each lot is converted whole and tracked until matching plant actions finish.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .replay_policy import agent as replay_agent


_STATE = {0: {"last_step": -1, "pending": 0, "opened": False}, 1: {"last_step": -1, "pending": 0, "opened": False}}
_MIN_RATIO = 1.05


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
        wheat = float(prices.get("WHEAT", 0) or 0) / 2
        strawberry = float(prices.get("STRAWBERRY", 0) or 0) / 10
    except (TypeError, ValueError):
        return False
    return wheat >= strawberry * _MIN_RATIO


def _copy_action(action: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in action.get("hands", []) or []],
        "market": [list(order) for order in action.get("market", []) or []],
    }


def _open(action: dict[str, Any], state: dict[str, Any]) -> None:
    total = 0
    for order in action["market"]:
        if len(order) >= 3 and order[0] == "BUY_SEED" and order[1] == "STRAWBERRY":
            try:
                total += max(0, int(order[2]))
            except (TypeError, ValueError):
                continue
            order[1] = "WHEAT"
    if total:
        state["pending"] += total
        state["opened"] = True


def _rewrite_plants(action: dict[str, Any], state: dict[str, Any]) -> None:
    for operation in [action["farmer"], *action["hands"]]:
        if state["pending"] <= 0:
            return
        if len(operation) >= 2 and operation[0] == "PLANT" and operation[1] == "STRAWBERRY":
            operation[1] = "WHEAT"
            state["pending"] -= 1


def _rewrite_sales(obs: Any, action: dict[str, Any]) -> None:
    shed = _get(_get(obs, "private", {}) or {}, "shed", {}) or {}
    wheat = max(0, int(shed.get("WHEAT", 0) or 0))
    if wheat <= 0:
        return
    for order in action["market"]:
        if len(order) >= 3 and order[0] == "SELL" and order[1] == "STRAWBERRY":
            order[1] = "WHEAT"
            order[2] = min(int(order[2]), wheat)


def agent(obs: Any) -> dict[str, Any]:
    seat = _seat(obs)
    step = _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "pending": 0, "opened": False}
        _STATE[seat] = state
    state["last_step"] = step
    action = _copy_action(replay_agent(obs))
    if _attractive(obs):
        _open(action, state)
    _rewrite_plants(action, state)
    if state["opened"]:
        _rewrite_sales(obs, action)
    return action
