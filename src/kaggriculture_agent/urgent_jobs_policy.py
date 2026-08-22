"""Observation-verified urgent-job challenger.

The replay policy follows a fixed route.  This is usually useful, but a
changed farm state can leave an actor standing on a ready crop or an animal
while the tape asks it to move.  This challenger changes only a movement or
PASS into an immediately legal local job, and only when the actor is not
carrying cargo that would make the job unsafe.

It deliberately does not reroute actors, buy resources, or change market
orders.  The production entry point remains the replay policy until this
candidate beats its predecessor in direct matches.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .logistics_state import _tile_at, extract_state
from .replay_policy import agent as replay_agent


_IDLE = {"PASS", "NORTH", "SOUTH", "EAST", "WEST"}


def _copy_action(action: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in action.get("hands", []) or []],
        "market": [list(order) for order in action.get("market", []) or []],
    }


def _farm(obs: Any) -> Mapping[str, Any]:
    if not isinstance(obs, Mapping):
        return {}
    seat = int(obs.get("player", 0) or 0)
    farms = list(obs.get("farms", []) or [])
    return farms[seat] if 0 <= seat < len(farms) else {}


def _local_job(tile: Mapping[str, Any], inventory: Mapping[str, Any]) -> list[Any] | None:
    if int(tile.get("yield_units", 0) or 0) > 0:
        return ["HARVEST"]
    if tile.get("kind") == "PLANT" and not tile.get("watered_today", False):
        return ["WATER"]
    if tile.get("animal"):
        if not tile.get("fed_today", False) and int(inventory.get("WHEAT", 0) or 0) > 0:
            return ["FEED"]
        if not tile.get("cared_today", False) and not inventory:
            return ["CARE"]
        if tile.get("fertilizer_available", False) and not inventory:
            return ["COLLECT_FERTILIZER"]
    return None


def apply_urgent_jobs(obs: Any, base_action: Mapping[str, Any]) -> dict[str, Any]:
    action = _copy_action(base_action)
    state = extract_state(obs)
    farm = _farm(obs)
    tiles = list(farm.get("tiles", []) or [])
    free = max(0, 100 - state.shed_units)
    units = list(state.units)
    actions = [action["farmer"], *action["hands"]]
    for index, unit in enumerate(units):
        if index >= len(actions) or not actions[index] or actions[index][0] not in _IDLE:
            continue
        if unit.inventory_units:
            continue
        tile = _tile_at(tiles, unit.position)
        if not isinstance(tile, Mapping):
            continue
        job = _local_job(tile, unit.inventory)
        if job is None:
            continue
        if job[0] == "HARVEST":
            amount = max(0, int(tile.get("yield_units", 0) or 0))
            if amount > free:
                continue
            free -= amount
        actions[index] = job
    return {
        "farmer": actions[0],
        "hands": actions[1:],
        "market": [list(order) for order in action.get("market", []) or []],
    }


def agent(obs: Any) -> dict[str, Any]:
    return apply_urgent_jobs(obs, replay_agent(obs))
