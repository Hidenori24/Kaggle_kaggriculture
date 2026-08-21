"""Failure-triggered resynchronization challenger.

Unlike a local-job override, this module changes an action only after the
previous observation proves that a local operation did not take effect.  It
keeps one small per-seat snapshot for the normal sequential Kaggle callback;
if the process restarts or steps move backwards, it clears the snapshot and
falls back to replay without guessing.
"""

from __future__ import annotations

from typing import Any, Mapping

from .replay_policy import agent as replay_agent


_WORK = {"HARVEST", "WATER", "FEED", "CARE", "COLLECT_FERTILIZER"}
_STATE = {0: {"last_step": -1, "previous": None}, 1: {"last_step": -1, "previous": None}}


def _farm(obs: Mapping[str, Any]) -> Mapping[str, Any]:
    seat = int(obs.get("player", 0) or 0)
    farms = list(obs.get("farms", []) or [])
    return farms[seat] if 0 <= seat < len(farms) else {}


def _positions(farm: Mapping[str, Any]) -> list[tuple[int, int]]:
    raw = [farm.get("farmer", [0, 0]), *list(farm.get("hands", []) or [])]
    result = []
    for position in raw:
        try:
            result.append((int(position[0]), int(position[1])))
        except (IndexError, TypeError, ValueError):
            result.append((0, 0))
    return result


def _tile(farm: Mapping[str, Any], position: tuple[int, int]) -> Mapping[str, Any] | None:
    tiles = list(farm.get("tiles", []) or [])
    x, y = position
    try:
        value = tiles[y][x]
    except (IndexError, TypeError):
        return None
    return value if isinstance(value, Mapping) else None


def _failed(operation: list[Any], before: Mapping[str, Any] | None, after: Mapping[str, Any] | None) -> bool:
    if not operation or operation[0] not in _WORK or before is None or after is None:
        return False
    if operation[0] == "HARVEST":
        return int(before.get("yield_units", 0) or 0) > 0 and int(after.get("yield_units", 0) or 0) > 0
    if operation[0] == "WATER":
        return before.get("kind") == "PLANT" and not before.get("watered_today", False) and not after.get("watered_today", False)
    if operation[0] == "FEED":
        return bool(before.get("animal")) and not before.get("fed_today", False) and not after.get("fed_today", False)
    if operation[0] == "CARE":
        return bool(before.get("animal")) and not before.get("cared_today", False) and not after.get("cared_today", False)
    return bool(before.get("fertilizer_available")) and bool(after.get("fertilizer_available"))


def _copy_action(action: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in action.get("hands", []) or []],
        "market": [list(order) for order in action.get("market", []) or []],
    }


def apply_resync(obs: Mapping[str, Any], base_action: Mapping[str, Any]) -> dict[str, Any]:
    action = _copy_action(base_action)
    seat = int(obs.get("player", 0) or 0)
    step = int(obs.get("step", 0) or 0)
    state = _STATE.setdefault(seat, {"last_step": -1, "previous": None})
    if step == 0 or step <= int(state.get("last_step", -1)):
        state.clear()
        state.update({"last_step": step, "previous": None})
    previous = state.get("previous")
    current_farm = _farm(obs)
    current_positions = _positions(current_farm)
    if previous and int(previous.get("step", -2)) == step - 1:
        previous_positions = previous.get("positions", [])
        for index, operation in enumerate(previous.get("operations", [])):
            if index >= len(action["hands"]) + 1 or index >= len(previous_positions):
                continue
            if index >= len(current_positions) or current_positions[index] != tuple(previous_positions[index]):
                continue
            before = previous.get("tiles", [])[index]
            after = _tile(current_farm, current_positions[index])
            if not _failed(operation, before, after):
                continue
            if index == 0:
                action["farmer"] = list(operation)
            else:
                hand_index = index - 1
                if action["hands"][hand_index][0] in {"PASS", "NORTH", "SOUTH", "EAST", "WEST"}:
                    action["hands"][hand_index] = list(operation)
    state["last_step"] = step
    state["previous"] = {
        "step": step,
        "positions": current_positions,
        "operations": [action["farmer"], *action["hands"]],
        "tiles": [_tile(current_farm, position) for position in current_positions],
    }
    return action


def agent(obs: Any) -> dict[str, Any]:
    return apply_resync(obs, replay_agent(obs))
