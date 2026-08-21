"""Late-game-only harvest challenger.

The full local-job repair was rejected because it desynchronised the care
tape.  This candidate is intentionally narrower: after step 600 it may let a
loaded-free extra hand harvest a mature crop while the replay action is PASS.
No watering, care, movement, farmer action, or market order is changed.
"""

from __future__ import annotations

from typing import Any, Mapping

from .logistics_state import _tile_at, extract_state
from .replay_policy import agent as replay_agent


START_STEP = 600


def _copy_action(action: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in action.get("hands", []) or []],
        "market": [list(order) for order in action.get("market", []) or []],
    }


def apply_late_harvest(obs: Any, base_action: Mapping[str, Any]) -> dict[str, Any]:
    action = _copy_action(base_action)
    step = int(obs.get("step", 0) or 0) if isinstance(obs, Mapping) else 0
    if step < START_STEP:
        return action
    state = extract_state(obs)
    farms = list(obs.get("farms", []) or []) if isinstance(obs, Mapping) else []
    seat = int(obs.get("player", 0) or 0) if isinstance(obs, Mapping) else 0
    farm = farms[seat] if 0 <= seat < len(farms) else {}
    tiles = list(farm.get("tiles", []) or [])
    free = max(0, 100 - state.shed_units)
    for index, unit in enumerate(state.units[1:], start=1):
        hand_index = index - 1
        if hand_index >= len(action["hands"]):
            continue
        if action["hands"][hand_index][0] != "PASS" or unit.inventory_units:
            continue
        tile = _tile_at(tiles, unit.position)
        if not isinstance(tile, Mapping):
            continue
        yield_units = max(0, int(tile.get("yield_units", 0) or 0))
        if yield_units <= 0 or yield_units > free:
            continue
        action["hands"][hand_index] = ["HARVEST"]
        free -= yield_units
    return action


def agent(obs: Any) -> dict[str, Any]:
    return apply_late_harvest(obs, replay_agent(obs))
