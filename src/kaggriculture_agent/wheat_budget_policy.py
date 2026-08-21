"""Market-only WHEAT purchase budget challenger.

The fixed action tape buys WHEAT for animal care.  This challenger keeps all
worker actions and market order positions unchanged, but trims one unit from
an existing WHEAT product purchase when the observed shed already covers a
short near-term feed reserve.  It never creates a purchase, changes a SELL,
or operates before the animal economy is established.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .replay_policy import _ACTIONS, _step
from .replay_policy import agent as replay_agent


MIN_DAY = 10
HORIZON = 48
SAFETY_DAYS = 2


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _count_animals(obs: Any) -> int:
    player = int(_get(obs, "player", 0) or 0)
    farms = _get(obs, "farms", []) or []
    farm = farms[player] if player < len(farms) else {}
    total = sum(
        1
        for row in _get(farm, "tiles", []) or []
        for tile in (row if isinstance(row, list) else [])
        if isinstance(tile, Mapping) and tile.get("animal")
    )
    shed = _get(_get(obs, "private", {}) or {}, "shed", {}) or {}
    return total + sum(int(shed.get(item, 0) or 0) for item in ("COW", "SHEEP", "GOOSE"))


def _wheat_available(obs: Any) -> int:
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    total = int(shed.get("WHEAT", 0) or 0)
    for inventory in _get(private, "inventories", []) or []:
        if isinstance(inventory, Mapping):
            total += int(inventory.get("WHEAT", 0) or 0)
    return max(0, total)


def _future_feed(step: int) -> int:
    stop = min(len(_ACTIONS), step + HORIZON + 1)
    return sum(
        1
        for action in _ACTIONS[step + 1 : stop]
        for operation in [action.get("farmer", [])] + list(action.get("hands", []) or [])
        if operation and operation[0] == "FEED"
    )


def _trim_purchase(obs: Any, action: dict[str, Any]) -> dict[str, Any]:
    step = _step(obs)
    if step // 24 < MIN_DAY:
        return action
    animals = _count_animals(obs)
    if animals <= 0:
        return action
    feed = _future_feed(step)
    reserve = feed + SAFETY_DAYS * animals
    if _wheat_available(obs) < reserve:
        return action

    market = [list(order) for order in action.get("market", []) or []]
    for order in market:
        if len(order) < 3 or order[0] != "BUY_PRODUCT" or order[1] != "WHEAT":
            continue
        try:
            quantity = int(order[2])
        except (TypeError, ValueError):
            continue
        if quantity > 1:
            order[2] = quantity - 1
            return {**action, "market": market}
    return action


def agent(obs: Any) -> dict[str, Any]:
    return _trim_purchase(obs, replay_agent(obs))
