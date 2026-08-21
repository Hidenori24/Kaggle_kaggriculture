"""First action-changing challenger for the stateful logistics redesign.

The replay policy remains the default production entry point.  This challenger
only repairs one narrow transport failure: a worker carrying a harvest or
fertilizer is already at the shed entrance, while the replay action would move
or wait instead of dropping the load. Feed, animals, and seeds are excluded
because they may have an immediate downstream job.
"""

from __future__ import annotations

from typing import Any

from .logistics_state import extract_state
from .replay_policy import agent as replay_agent


_MOVEMENT = {"NORTH", "SOUTH", "EAST", "WEST", "PASS"}
_SAFE_DELIVERABLES = {
    "FERTILIZER", "MILK", "WOOL", "EGG", "CARROT", "TOMATO", "STRAWBERRY", "MELON"
}


def _shed_access(tiles: list[Any]) -> set[tuple[int, int]]:
    size = len(tiles) or 10
    half = size // 2
    return {(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)}


def _transport_repair(obs: Any, action: dict[str, Any]) -> dict[str, Any]:
    state = extract_state(obs)
    farms = list(obs.get("farms", []) or []) if isinstance(obs, dict) else []
    seat = int(obs.get("player", 0) or 0) if isinstance(obs, dict) else 0
    farm = farms[seat] if seat < len(farms) else {}
    access = _shed_access(farm.get("tiles", []) or [])
    actions = [list(action.get("farmer") or ["PASS"])] + [
        list(order or ["PASS"]) for order in action.get("hands", []) or []
    ]
    for index, unit in enumerate(state.units):
        if index >= len(actions) or actions[index][0] not in _MOVEMENT:
            continue
        if unit.position not in access:
            continue
        if not unit.inventory or not set(unit.inventory).issubset(_SAFE_DELIVERABLES):
            continue
        actions[index] = ["DROP"]
    return {
        "farmer": actions[0],
        "hands": actions[1:],
        "market": [list(order) for order in action.get("market", []) or []],
    }


def agent(obs: Any) -> dict[str, Any]:
    """Return the replay action plus the narrow transport challenger."""
    return _transport_repair(obs, replay_agent(obs))
