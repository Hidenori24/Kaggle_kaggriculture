"""No-op repair for already-fed animals.

The replay tape contains a small number of FEED attempts against animals that
are already marked ``fed_today``.  Such an action cannot change state.  This
challenger turns only that no-op into PASS; it does not alter movement,
market orders, or a valid feeding action.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .replay_policy import agent as replay_agent


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _fed_today(obs: Any, position: Any) -> bool:
    player = int(_get(obs, "player", 0) or 0)
    farms = _get(obs, "farms", []) or []
    if player >= len(farms) or not isinstance(position, (list, tuple)) or len(position) < 2:
        return False
    farm = farms[player]
    tiles = _get(farm, "tiles", []) or []
    try:
        x, y = int(position[0]), int(position[1])
        tile = tiles[y][x]
    except (IndexError, TypeError, ValueError):
        return False
    return isinstance(tile, Mapping) and bool(tile.get("animal")) and bool(tile.get("fed_today"))


def _repair(obs: Any, action: dict[str, Any]) -> dict[str, Any]:
    player = int(_get(obs, "player", 0) or 0)
    farms = _get(obs, "farms", []) or []
    if player >= len(farms):
        return action
    farm = farms[player]
    positions = [_get(farm, "farmer", []), *list(_get(farm, "hands", []) or [])]
    units = [list(action.get("farmer") or ["PASS"]), *[list(x) for x in action.get("hands", []) or []]]
    changed = False
    for index, operation in enumerate(units):
        if index >= len(positions) or not operation or operation[0] != "FEED":
            continue
        if _fed_today(obs, positions[index]):
            units[index] = ["PASS"]
            changed = True
    if not changed:
        return action
    return {"farmer": units[0], "hands": units[1:], "market": [list(x) for x in action.get("market", []) or []]}


def agent(obs: Any) -> dict[str, Any]:
    return _repair(obs, replay_agent(obs))
