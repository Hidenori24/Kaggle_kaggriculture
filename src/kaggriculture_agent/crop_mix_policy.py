"""Exploratory crop-mix challenger guided by public strong-agent tapes.

The validated replay plants 24 MELON units.  Strong public tapes planted
more WHEAT and fewer MELON units.  This policy converts only future MELON
seed purchases and their matching PLANT actions after the observed MELON
price falls below a conservative threshold.  It keeps order positions and
quantities unchanged and leaves the replay fallback untouched when no WHEAT
seed is available.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .replay_policy import agent as replay_agent


_MELON_SWITCH_PRICE = 200.0
_STATE = {
    0: {"last_step": -1, "converted_seed_units": 0},
    1: {"last_step": -1, "converted_seed_units": 0},
}


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


def _melon_is_crowded(obs: Any) -> bool:
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    try:
        return float(prices.get("MELON", 0) or 0) < _MELON_SWITCH_PRICE
    except (TypeError, ValueError):
        return False


def _wheat_seed_available(obs: Any) -> int:
    private = _get(obs, "private", {}) or {}
    seeds = _get(private, "seeds", {}) or {}
    try:
        return max(0, int(seeds.get("WHEAT", 0) or 0))
    except (TypeError, ValueError):
        return 0


def _copy_action(action: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in action.get("hands", []) or []],
        "market": [list(order) for order in action.get("market", []) or []],
    }


def _switch_seed_purchase(obs: Any, action: dict[str, Any], state: dict[str, Any]) -> None:
    if not _melon_is_crowded(obs):
        return
    for order in action["market"]:
        if len(order) < 3 or order[0] != "BUY_SEED" or order[1] != "MELON":
            continue
        try:
            quantity = max(0, int(order[2]))
        except (TypeError, ValueError):
            continue
        if quantity <= 0:
            continue
        order[1] = "WHEAT"
        state["converted_seed_units"] += quantity
        return


def _switch_plant(obs: Any, action: dict[str, Any], state: dict[str, Any]) -> None:
    if not _melon_is_crowded(obs) or state["converted_seed_units"] <= 0:
        return
    if _wheat_seed_available(obs) <= 0:
        return
    operations = [action["farmer"], *action["hands"]]
    for operation in operations:
        if len(operation) < 2 or operation[0] != "PLANT" or operation[1] != "MELON":
            continue
        operation[1] = "WHEAT"
        state["converted_seed_units"] -= 1
        return


def agent(obs: Any) -> dict[str, Any]:
    seat = _seat(obs)
    step = _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "converted_seed_units": 0}
        _STATE[seat] = state
    state["last_step"] = step
    action = _copy_action(replay_agent(obs))
    _switch_seed_purchase(obs, action, state)
    _switch_plant(obs, action, state)
    return action
