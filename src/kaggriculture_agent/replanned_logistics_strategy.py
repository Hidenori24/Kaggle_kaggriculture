"""Replanned strategy with a conservative, observation-derived logistics gate.

The first replanned challenger repeatedly picked up feed even when every
animal was already fed, then dropped the same unit and picked it up again.
This wrapper keeps the large policy separate while suppressing only that
provably unnecessary pickup.  It is an experiment, not the production agent.
"""

from __future__ import annotations

from typing import Any

from .full_strategy import _value
from .replanned_strategy import choose_action as replanned_action


def _has_unfed_animal(obs: Any) -> bool:
    farms = _value(obs, "farms", []) or []
    player = int(_value(obs, "player", 0) or 0)
    farm = farms[player] if player < len(farms) else {}
    for row in _value(farm, "tiles", []) or []:
        for tile in row if isinstance(row, list) else []:
            if isinstance(tile, dict) and tile.get("animal") and not tile.get("fed_today", False):
                return True
    return False


def _is_builder_feed_pickup(action: list[Any]) -> bool:
    return len(action) >= 2 and action[0] == "PICKUP" and action[1] == "WHEAT"


def choose_action(obs: Any) -> dict[str, Any]:
    action = replanned_action(obs)
    if _has_unfed_animal(obs):
        return action

    # When no animal needs feed, a WHEAT pickup can only create a transport
    # loop in the current planner. Leave every other action untouched.
    if _is_builder_feed_pickup(action.get("farmer", [])):
        action["farmer"] = ["PASS"]
    action["hands"] = [
        ["PASS"] if _is_builder_feed_pickup(order) else order
        for order in action.get("hands", [])
    ]
    return action
