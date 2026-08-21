"""Market-only challenger for crowded late-game markets.

The production replay, worker actions, quantities, and order count are left
unchanged.  Only the ordering of existing SELL orders is reconsidered when a
crowded market is observable.  This keeps the experiment isolated from the
fixed movement and animal-care schedule.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .replay_policy import agent as replay_agent


REFERENCE_PRICES = {
    "WHEAT": 25.0,
    "CARROT": 35.0,
    "TOMATO": 60.0,
    "STRAWBERRY": 120.0,
    "MELON": 250.0,
    "FERTILIZER": 100.0,
    "EGG": 50.0,
    "MILK": 160.0,
    "WOOL": 200.0,
}
PRESSURE_ITEMS = frozenset(("MELON", "MILK", "WOOL", "FERTILIZER"))
PRESSURE_RATIO = 0.35


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _crowded(obs: Any) -> bool:
    market = _get(obs, "market", {}) or {}
    prices = _get(market, "prices", {}) or {}
    return any(
        float(prices.get(item, 0) or 0) <= REFERENCE_PRICES[item] * PRESSURE_RATIO
        for item in PRESSURE_ITEMS
    )


def _pressure_order(obs: Any, action: dict[str, Any]) -> dict[str, Any]:
    if not _crowded(obs):
        return action
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    market = [list(order) for order in action.get("market", []) or []]
    sells = [order for order in market if len(order) >= 3 and order[0] == "SELL"]
    rest = [order for order in market if not (len(order) >= 3 and order[0] == "SELL")]

    def score(order: list[Any]) -> float:
        item = str(order[1])
        quantity = max(0, int(order[2]))
        price = max(0.0, float(prices.get(item, 0) or 0))
        reference = REFERENCE_PRICES.get(item, max(price, 1.0))
        # In a crowded market, preserve scarce relative value first while
        # retaining quantity as the secondary tiebreaker.
        relative_value = price / max(reference, 1.0)
        return relative_value * quantity

    sells.sort(key=score, reverse=True)
    return {**action, "market": (sells + rest)[:10]}


def agent(obs: Any) -> dict[str, Any]:
    return _pressure_order(obs, replay_agent(obs))
