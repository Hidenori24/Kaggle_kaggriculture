"""Daily market-plan challenger built on the validated replay policy.

The replay policy already supplies the legal farm actions.  This challenger
changes only the timing of existing SELL orders.  When a product is visibly
in a glut, it keeps a small, bounded batch in the shed and releases it when
the price recovers or the season is close to ending.  The ledger is local to
the player seat and resets when a new episode starts, so the policy remains
deterministic and restart-safe.

This is deliberately an experiment policy.  It is not enabled by the
submission entry point until it beats the replay policy in head-to-head tests.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .replay_policy import agent as replay_agent


_BASE_PRICE = {
    "WHEAT": 25.0,
    "FERTILIZER": 100.0,
    "CARROT": 35.0,
    "TOMATO": 60.0,
    "STRAWBERRY": 120.0,
    "MELON": 250.0,
    "MILK": 160.0,
    "WOOL": 200.0,
    "EGG": 50.0,
}
_PREMIUM = {"STRAWBERRY", "MELON", "MILK", "WOOL"}
_HOLD_LIMIT = {"WHEAT": 12, "FERTILIZER": 8}
_PREMIUM_HOLD_LIMIT = 6
_MAX_HOLD_DAY = 26
_MAX_SHED_UNITS = 78
_RECOVERY_FACTOR = 1.08
_STATE = {
    0: {"last_step": -1, "day": -1, "held": {}, "daily_held": {}, "reference": {}},
    1: {"last_step": -1, "day": -1, "held": {}, "daily_held": {}, "reference": {}},
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


def _state_for(obs: Any) -> dict[str, Any]:
    seat = _seat(obs)
    step = _step(obs)
    day = int(_get(obs, "day", step // 24) or step // 24)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "day": day, "held": {}, "daily_held": {}, "reference": {}}
        _STATE[seat] = state
    if day != int(state.get("day", -1)):
        state["day"] = day
        state["daily_held"] = {}
    state["last_step"] = step
    return state


def _prices(obs: Any) -> Mapping[str, Any]:
    return _get(_get(obs, "market", {}) or {}, "prices", {}) or {}


def _shed(obs: Any) -> Mapping[str, Any]:
    private = _get(obs, "private", {}) or {}
    return _get(private, "shed", {}) or {}


def _market_copy(action: Mapping[str, Any]) -> list[list[Any]]:
    return [list(order) for order in action.get("market", []) or [] if order]


def _sell_orders(market: list[list[Any]], item: str) -> list[list[Any]]:
    return [
        order
        for order in market
        if len(order) >= 3 and order[0] == "SELL" and order[1] == item
    ]


def _hold_budget(item: str) -> int:
    return _HOLD_LIMIT.get(item, _PREMIUM_HOLD_LIMIT if item in _PREMIUM else 0)


def _should_hold(obs: Any, item: str, day: int) -> bool:
    if day > _MAX_HOLD_DAY:
        return False
    try:
        price = float(_prices(obs).get(item, 0) or 0)
    except (TypeError, ValueError):
        return False
    base = _BASE_PRICE.get(item, 0.0)
    if item == "WHEAT":
        return 0 < price < 24.0
    if item == "FERTILIZER":
        return 0 < price < 55.0
    return item in _PREMIUM and 0 < price < base * 0.45


def _shed_units(obs: Any) -> int:
    total = 0
    for amount in _shed(obs).values():
        try:
            total += max(0, int(amount or 0))
        except (TypeError, ValueError):
            continue
    return total


def _merge_sell(market: list[list[Any]], item: str, quantity: int) -> bool:
    if quantity <= 0:
        return False
    existing = _sell_orders(market, item)
    if existing:
        existing[0][2] = max(0, int(existing[0][2])) + quantity
        return True
    if len(market) >= 10:
        return False
    market.append(["SELL", item, quantity])
    return True


def _release_recovered(obs: Any, market: list[list[Any]], state: dict[str, Any], day: int) -> None:
    prices = _prices(obs)
    shed = _shed(obs)
    for item, amount in list(state["held"].items()):
        if amount <= 0:
            continue
        try:
            price = float(prices.get(item, 0) or 0)
            reference = float(state["reference"].get(item, price) or price)
            available = max(0, int(shed.get(item, 0) or 0))
        except (TypeError, ValueError):
            continue
        recovered = price >= reference * _RECOVERY_FACTOR
        forced = day >= _MAX_HOLD_DAY
        if not (recovered or forced):
            continue
        quantity = min(int(amount), available)
        if _merge_sell(market, item, quantity):
            state["held"][item] = int(amount) - quantity
            if state["held"][item] <= 0:
                state["held"].pop(item, None)
                state["reference"].pop(item, None)


def _hold_cheap_orders(obs: Any, market: list[list[Any]], state: dict[str, Any], day: int) -> None:
    if _shed_units(obs) > _MAX_SHED_UNITS:
        return
    for item in tuple(_BASE_PRICE):
        if not _should_hold(obs, item, day):
            continue
        budget = _hold_budget(item) - int(state["daily_held"].get(item, 0) or 0)
        if budget <= 0:
            continue
        for order in _sell_orders(market, item):
            try:
                requested = max(0, int(order[2]))
            except (TypeError, ValueError):
                continue
            held = min(requested, budget)
            if held <= 0:
                continue
            order[2] = requested - held
            if order[2] <= 0:
                market.remove(order)
            state["held"][item] = int(state["held"].get(item, 0) or 0) + held
            state["daily_held"][item] = int(state["daily_held"].get(item, 0) or 0) + held
            state["reference"].setdefault(item, float(_prices(obs).get(item, 0) or 0))
            break


def _plan_market(obs: Any, action: dict[str, Any]) -> dict[str, Any]:
    state = _state_for(obs)
    day = int(_get(obs, "day", _step(obs) // 24) or _step(obs) // 24)
    market = _market_copy(action)
    _release_recovered(obs, market, state, day)
    _hold_cheap_orders(obs, market, state, day)
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in action.get("hands", []) or []],
        "market": market[:10],
    }


def agent(obs: Any) -> dict[str, Any]:
    """Replay farm actions with a bounded daily market timing plan."""
    return _plan_market(obs, replay_agent(obs))
