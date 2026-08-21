"""Just-in-time input purchasing challenger.

The recorded policy sometimes buys WHEAT/FERTILIZER before the shed needs it.
This module keeps the replay's movement and production actions intact, but
caps an existing input purchase to the observable short-term requirement.
It never creates a purchase and keeps a small safety reserve for animals.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .replay_policy import _ACTIONS, agent as replay_agent


_HORIZON_STEPS = 48
_SAFETY_DAYS = 1


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _count(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _step(obs: Any) -> int:
    value = _get(obs, "step", None)
    if value is not None:
        return _count(value)
    return _count(_get(obs, "day", 0)) * 24 + _count(_get(obs, "hour", 0))


def _available(obs: Any, item: str) -> int:
    private = _get(obs, "private", {}) or {}
    amount = _count((_get(private, "shed", {}) or {}).get(item, 0))
    for inventory in _get(private, "inventories", []) or []:
        amount += _count((_get(inventory, item, 0) if not isinstance(inventory, Mapping) else inventory.get(item, 0)))
    return amount


def _animals(obs: Any) -> int:
    player = _count(_get(obs, "player", 0))
    farms = _get(obs, "farms", []) or []
    farm = farms[player] if player < len(farms) else {}
    total = 0
    for row in _get(farm, "tiles", []) or []:
        for tile in row if isinstance(row, list) else []:
            if isinstance(tile, Mapping) and tile.get("animal"):
                total += 1
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    total += sum(_count(shed.get(item, 0)) for item in ("COW", "SHEEP", "GOOSE"))
    return total


def _future_need(step: int, item: str, horizon: int = _HORIZON_STEPS) -> int:
    need = 0
    for tape_action in _ACTIONS[step : min(len(_ACTIONS), step + horizon + 1)]:
        operations = [tape_action.get("farmer", [])] + list(tape_action.get("hands", []) or [])
        for operation in operations:
            if operation and ((item == "WHEAT" and operation[0] == "FEED") or (item == "FERTILIZER" and operation[0] == "FERTILIZE")):
                need += 1
    return need


def _cap_purchase(obs: Any, action: dict[str, Any]) -> dict[str, Any]:
    step = _step(obs)
    animals = _animals(obs)
    current_feed = sum(
        1
        for operation in [action.get("farmer", []), *list(action.get("hands", []) or [])]
        if operation and operation[0] == "FEED"
    )
    current_fertilize = sum(
        1
        for operation in [action.get("farmer", []), *list(action.get("hands", []) or [])]
        if operation and operation[0] == "FERTILIZE"
    )
    safety = animals * _SAFETY_DAYS
    requirements = {
        "WHEAT": current_feed + _future_need(step + 1, "WHEAT") + safety,
        "FERTILIZER": current_fertilize + _future_need(step + 1, "FERTILIZER") + 2,
    }
    market: list[list[Any]] = []
    available = {item: _available(obs, item) for item in requirements}
    for raw in action.get("market", []) or []:
        order = list(raw)
        if len(order) >= 3 and order[0] == "BUY_PRODUCT" and order[1] in requirements:
            item = order[1]
            requested = _count(order[2])
            needed = max(0, requirements[item] - available[item])
            order[2] = min(requested, needed)
            if order[2] <= 0:
                continue
            available[item] += order[2]
        market.append(order)
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in action.get("hands", []) or []],
        "market": market[:10],
    }


def agent(obs: Any) -> dict[str, Any]:
    return _cap_purchase(obs, replay_agent(obs))

