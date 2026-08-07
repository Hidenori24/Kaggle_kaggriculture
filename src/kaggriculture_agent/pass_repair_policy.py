"""Conservative PASS repair candidate.

The validated replay policy remains responsible for the complete action plan.
This experiment only replaces a PASS when the unit is already standing on a
locally actionable tile.  It never changes movement, market orders, hiring,
land purchases, planting, or the endgame liquidation rule.
"""

from __future__ import annotations

from typing import Any

from .adaptive_policy import agent as replay_with_endgame_agent


def _value(obj: Any, key: str, default: Any = None) -> Any:
    return obj.get(key, default) if isinstance(obj, dict) else default


def _farm_for_player(obs: Any) -> dict[str, Any]:
    farms = _value(obs, "farms", []) or []
    player = int(_value(obs, "player", 0) or 0)
    return farms[player] if 0 <= player < len(farms) and isinstance(farms[player], dict) else {}


def _tile_at(farm: dict[str, Any], position: Any) -> Any:
    try:
        x, y = int(position[0]), int(position[1])
        return farm.get("tiles", [])[y][x]
    except (IndexError, KeyError, TypeError, ValueError):
        return "LOCKED"


def _local_repair(tile: Any, day: int) -> list[Any] | None:
    """Return only actions that are safe from the current tile state."""
    if not isinstance(tile, dict):
        return None

    if tile.get("kind") == "PLANT":
        if not tile.get("watered_today", False):
            return ["WATER"]
        planted_day = int(tile.get("planted_day", day) or day)
        crop = str(tile.get("crop", "")).upper()
        maturity = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}
        if tile.get("yield_units", 0) > 0 and day - planted_day >= maturity.get(crop, 2):
            return ["HARVEST"]

    if tile.get("kind") in {"COOP", "PASTURE"} and tile.get("animal"):
        if tile.get("yield_units", 0) > 0:
            return ["COLLECT_FERTILIZER"]

    return None


def _is_pass(action: Any) -> bool:
    return isinstance(action, list) and (not action or action[0] == "PASS")


def _repair_passes(obs: Any, action: dict[str, Any]) -> dict[str, Any]:
    farm = _farm_for_player(obs)
    day = int(_value(obs, "day", 0) or 0)
    positions = [_value(farm, "farmer"), *list(_value(farm, "hands", []) or [])]
    units = [action.get("farmer", ["PASS"]), *list(action.get("hands", []) or [])]

    for index, (position, scheduled) in enumerate(zip(positions, units)):
        if not _is_pass(scheduled) or not isinstance(position, list):
            continue
        repair = _local_repair(_tile_at(farm, position), day)
        if repair is not None:
            units[index] = repair

    action["farmer"] = list(units[0] or ["PASS"])
    expected_hands = len(_value(farm, "hands", []) or [])
    action["hands"] = [list(unit or ["PASS"]) for unit in units[1 : expected_hands + 1]]
    while len(action["hands"]) < expected_hands:
        action["hands"].append(["PASS"])
    return action


def agent(obs: Any) -> dict[str, Any]:
    """Return the replay action with conservative local PASS repairs."""
    action = replay_with_endgame_agent(obs)
    return _repair_passes(obs, action)

