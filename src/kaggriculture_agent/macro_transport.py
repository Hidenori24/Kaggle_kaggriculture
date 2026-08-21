"""Restart-safe transport planning for an isolated challenger.

The planner is intentionally conservative.  It only takes over an actor when
the replay policy has chosen PASS, the actor carries only saleable output, and
the current shed has room for that complete load.  The route is recomputed
from the current observation on every call; no hidden progress flag is needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .logistics_state import SHED_CAPACITY, extract_state
from .replay_policy import agent as replay_agent


MOVEMENT = {"NORTH", "SOUTH", "EAST", "WEST", "PASS"}
SAFE_CARGO = {
    "CARROT", "TOMATO", "STRAWBERRY", "MELON", "MILK", "WOOL", "EGG",
}


@dataclass(frozen=True)
class TransportPlan:
    """A complete, observation-derived route to the shed."""

    actor: str
    start: tuple[int, int]
    target: tuple[int, int]
    cargo: Mapping[str, int]
    next_action: tuple[str, ...]


def _shed_access(size: int) -> tuple[tuple[int, int], ...]:
    half = size // 2
    return tuple(sorted({
        (half - 1, half - 1), (half, half - 1),
        (half - 1, half), (half, half),
    }))


def _next_step(start: tuple[int, int], target: tuple[int, int]) -> tuple[str, ...]:
    x, y = start
    tx, ty = target
    if x < tx:
        return ("EAST",)
    if x > tx:
        return ("WEST",)
    if y < ty:
        return ("SOUTH",)
    if y > ty:
        return ("NORTH",)
    return ("DROP",)


def _unit_actions(action: Mapping[str, Any]) -> list[list[Any]]:
    return [list(action.get("farmer") or ["PASS"])] + [
        list(order or ["PASS"]) for order in action.get("hands", []) or []
    ]


def _farm(obs: Any) -> Mapping[str, Any]:
    seat = int(obs.get("player", 0) or 0) if isinstance(obs, Mapping) else 0
    farms = list(obs.get("farms", []) or []) if isinstance(obs, Mapping) else []
    return farms[seat] if 0 <= seat < len(farms) else {}


def build_transport_plans(
    obs: Any, base_action: Mapping[str, Any]
) -> tuple[TransportPlan, ...]:
    """Return only plans whose entire cargo can fit in the current shed."""
    state = extract_state(obs)
    farm = _farm(obs)
    tiles = list(farm.get("tiles", []) or [])
    access = _shed_access(len(tiles) or 10)
    free = max(0, SHED_CAPACITY - state.shed_units)
    actions = _unit_actions(base_action)
    plans: list[TransportPlan] = []
    for index, unit in enumerate(state.units):
        if index >= len(actions) or actions[index][0] != "PASS":
            continue
        cargo = {
            item: int(quantity)
            for item, quantity in unit.inventory.items()
            if item in SAFE_CARGO and int(quantity) > 0
        }
        if not cargo or sum(cargo.values()) > free:
            continue
        target = min(
            access,
            key=lambda position: (
                abs(unit.position[0] - position[0])
                + abs(unit.position[1] - position[1]),
                position[1],
                position[0],
            ),
        )
        plans.append(TransportPlan(
            actor=unit.actor,
            start=unit.position,
            target=target,
            cargo=cargo,
            next_action=_next_step(unit.position, target),
        ))
        free -= sum(cargo.values())
    return tuple(plans)


def apply_transport_plans(obs: Any, base_action: Mapping[str, Any]) -> dict[str, Any]:
    """Apply at most one conservative route step per actor."""
    plans = build_transport_plans(obs, base_action)
    actions = _unit_actions(base_action)
    for plan in plans:
        index = 0 if plan.actor == "farmer" else int(plan.actor.split("-", 1)[1]) + 1
        if index < len(actions):
            actions[index] = list(plan.next_action)
    return {
        "farmer": actions[0] if actions else ["PASS"],
        "hands": actions[1:],
        "market": [list(order) for order in base_action.get("market", []) or []],
    }


def agent(obs: Any) -> dict[str, Any]:
    return apply_transport_plans(obs, replay_agent(obs))
