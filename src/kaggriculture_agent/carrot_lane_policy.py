"""One-batch fast-crop lane challenger.

The latest public loss showed a strong opponent repeatedly cycling CARROT and
WHEAT, while the replay policy never planted CARROT.  This experiment changes
only the first future WHEAT seed batch when the initial CARROT price is
materially better.  The matching number of early WHEAT plant actions is then
changed to CARROT, keeping the movement and action schedule intact.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .replay_policy import agent as replay_agent


_MIN_CARROT_PRICE = 32.0
_MIN_PRICE_GAP = 5.0
_STATE = {
    0: {"last_step": -1, "pending": 0, "opened": False},
    1: {"last_step": -1, "pending": 0, "opened": False},
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


def _lane_is_attractive(obs: Any) -> bool:
    market = _get(obs, "market", {}) or {}
    prices = _get(market, "prices", {}) or {}
    try:
        carrot = float(prices.get("CARROT", 0) or 0)
        wheat = float(prices.get("WHEAT", 0) or 0)
    except (TypeError, ValueError):
        return False
    return carrot >= _MIN_CARROT_PRICE and carrot >= wheat + _MIN_PRICE_GAP


def _copy_action(action: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in action.get("hands", []) or []],
        "market": [list(order) for order in action.get("market", []) or []],
    }


def _open_first_lane(obs: Any, action: dict[str, Any], state: dict[str, Any]) -> bool:
    if state["opened"] or not _lane_is_attractive(obs):
        return False
    for order in action["market"]:
        if len(order) < 3 or order[0] != "BUY_SEED" or order[1] != "WHEAT":
            continue
        try:
            quantity = max(0, int(order[2]))
        except (TypeError, ValueError):
            continue
        if quantity <= 0:
            continue
        order[1] = "CARROT"
        state["pending"] = quantity
        state["opened"] = True
        return True
    return False


def _rewrite_next_plant(action: dict[str, Any], state: dict[str, Any]) -> bool:
    if state["pending"] <= 0:
        return False
    for operation in [action["farmer"], *action["hands"]]:
        if len(operation) >= 2 and operation[0] == "PLANT" and operation[1] == "WHEAT":
            operation[1] = "CARROT"
            state["pending"] -= 1
            return True
    return False


def _sell_carrot_surplus(obs: Any, action: dict[str, Any]) -> None:
    """Expose converted output to the market without changing other orders."""
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    quantity = max(0, int(shed.get("CARROT", 0) or 0))
    if quantity <= 0 or any(
        len(order) >= 2 and order[0] == "SELL" and order[1] == "CARROT"
        for order in action["market"]
    ):
        return
    if len(action["market"]) < 10:
        action["market"].append(["SELL", "CARROT", quantity])


def agent(obs: Any) -> dict[str, Any]:
    seat = _seat(obs)
    step = _step(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "pending": 0, "opened": False}
        _STATE[seat] = state
    state["last_step"] = step
    action = _copy_action(replay_agent(obs))
    if step == 0:
        _open_first_lane(obs, action, state)
    _rewrite_next_plant(action, state)
    if state["opened"]:
        _sell_carrot_surplus(obs, action)
    return action
