"""Conservative local-job challenger.

This policy does not route actors and never changes the farmer's action.  For
an extra hand only, it replaces a replay PASS with a job that is executable on
the hand's current tile, provided the hand carries no inventory.  The goal is
to recover one wasted worker turn without changing the fixed travel tape.
"""

from __future__ import annotations

from typing import Any, Mapping

from .logistics_state import _tile_at, extract_state
from .replay_policy import agent as replay_agent


def _farm(obs: Any) -> Mapping[str, Any]:
    seat = int(obs.get("player", 0) or 0) if isinstance(obs, Mapping) else 0
    farms = list(obs.get("farms", []) or []) if isinstance(obs, Mapping) else []
    return farms[seat] if 0 <= seat < len(farms) else {}


def _copy_action(action: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in action.get("hands", []) or []],
        "market": [list(order) for order in action.get("market", []) or []],
    }


def _local_job(tile: Mapping[str, Any]) -> list[Any] | None:
    if int(tile.get("yield_units", 0) or 0) > 0:
        return ["HARVEST"]
    if tile.get("kind") == "PLANT" and not tile.get("watered_today", False):
        return ["WATER"]
    if tile.get("animal"):
        if tile.get("fed_today", False) and not tile.get("cared_today", False):
            return ["CARE"]
        if tile.get("fed_today", False) and tile.get("cared_today", False):
            if tile.get("fertilizer_available", False):
                return ["COLLECT_FERTILIZER"]
    return None


def apply_local_jobs(obs: Any, base_action: Mapping[str, Any]) -> dict[str, Any]:
    action = _copy_action(base_action)
    state = extract_state(obs)
    farm = _farm(obs)
    tiles = list(farm.get("tiles", []) or [])
    free = max(0, 100 - state.shed_units)
    for index, unit in enumerate(state.units[1:], start=1):
        hand_index = index - 1
        if hand_index >= len(action["hands"]):
            continue
        if action["hands"][hand_index][0] != "PASS":
            continue
        if unit.inventory_units:
            continue
        tile = _tile_at(tiles, unit.position)
        if not isinstance(tile, Mapping):
            continue
        job = _local_job(tile)
        if job is None:
            continue
        if job[0] == "HARVEST":
            free -= max(0, int(tile.get("yield_units", 0) or 0))
            if free < 0:
                continue
        action["hands"][hand_index] = job
    return action


def agent(obs: Any) -> dict[str, Any]:
    return apply_local_jobs(obs, replay_agent(obs))
