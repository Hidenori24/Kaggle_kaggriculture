"""Observation-derived state and job candidates for the logistics redesign.

This module is deliberately decision-free for the first phase.  It turns one
Kaggriculture observation into a restart-safe ledger that can be inspected in
shadow mode before any action is changed in production.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ANIMALS = ("COW", "SHEEP", "GOOSE")
GROWTH_DAYS = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}
SHED_CAPACITY = 100


@dataclass(frozen=True)
class UnitLedger:
    """The observable state relevant to assigning work to one unit."""

    actor: str
    position: tuple[int, int]
    inventory_units: int
    inventory: Mapping[str, int]


@dataclass(frozen=True)
class LogisticsState:
    """Restart-safe economic and operational ledger for one player."""

    step: int
    day: int
    cash: float
    shed_units: int
    shed: Mapping[str, int]
    seeds: Mapping[str, int]
    prices: Mapping[str, float]
    animals: int
    units: tuple[UnitLedger, ...]
    mature_crops: int
    watered_crops: int
    fertilizer_ready: int
    unlocked_quadrants: tuple[str, ...]


@dataclass(frozen=True)
class JobCandidate:
    """A candidate local job, used by shadow reports and later scheduling."""

    actor: str
    kind: str
    priority: int
    position: tuple[int, int]
    reason: str


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _count(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _position(value: Any) -> tuple[int, int]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return int(value[0]), int(value[1])
        except (TypeError, ValueError):
            pass
    return 0, 0


def _tile_at(tiles: list[Any], position: tuple[int, int]) -> Any:
    x, y = position
    try:
        return tiles[y][x]
    except (IndexError, TypeError):
        return None


def _units_for_farm(farm: Any, inventories: list[Any]) -> tuple[UnitLedger, ...]:
    positions = [_get(farm, "farmer", [0, 0]), *list(_get(farm, "hands", []) or [])]
    result = []
    for index, raw_position in enumerate(positions):
        raw_inventory = inventories[index] if index < len(inventories) else {}
        inventory = {
            str(item): _count(quantity)
            for item, quantity in dict(raw_inventory or {}).items()
            if _count(quantity) > 0
        }
        result.append(
            UnitLedger(
                actor="farmer" if index == 0 else f"hand-{index - 1}",
                position=_position(raw_position),
                inventory_units=sum(inventory.values()),
                inventory=inventory,
            )
        )
    return tuple(result)


def extract_state(obs: Any) -> LogisticsState:
    """Extract a complete, deterministic ledger from a Kaggriculture observation."""
    player = _count(_get(obs, "player", 0))
    farms = list(_get(obs, "farms", []) or [])
    farm = farms[player] if player < len(farms) else {}
    private = _get(obs, "private", {}) or {}
    shed = {str(item): _count(quantity) for item, quantity in (_get(private, "shed", {}) or {}).items()}
    seeds = {str(item): _count(quantity) for item, quantity in (_get(private, "seeds", {}) or {}).items()}
    market = _get(obs, "market", {}) or {}
    prices = {
        str(item): float(value or 0)
        for item, value in (_get(market, "prices", {}) or {}).items()
    }
    tiles = _get(farm, "tiles", []) or []
    animals = sum(
        1
        for row in tiles
        for tile in row if isinstance(row, list)
        if isinstance(tile, Mapping) and tile.get("animal")
    )
    animals += sum(shed.get(animal, 0) for animal in ANIMALS)
    mature_crops = 0
    watered_crops = 0
    fertilizer_ready = 0
    for row in tiles:
        for tile in row if isinstance(row, list) else []:
            if not isinstance(tile, Mapping):
                continue
            if tile.get("kind") == "PLANT":
                if _count(tile.get("yield_units")) > 0:
                    mature_crops += 1
                if tile.get("watered_today", False):
                    watered_crops += 1
            if tile.get("fertilizer_available", False):
                fertilizer_ready += 1
    return LogisticsState(
        step=_count(_get(obs, "step", 0)),
        day=_count(_get(obs, "day", 0)),
        cash=float(_get(farm, "money", 0) or 0),
        shed_units=sum(shed.values()),
        shed=shed,
        seeds=seeds,
        prices=prices,
        animals=animals,
        units=_units_for_farm(farm, list(_get(private, "inventories", []) or [])),
        mature_crops=mature_crops,
        watered_crops=watered_crops,
        fertilizer_ready=fertilizer_ready,
        unlocked_quadrants=tuple(_get(farm, "unlocked_quadrants", []) or []),
    )


def resource_plan(state: LogisticsState, horizon_days: int = 3) -> dict[str, int | float]:
    """Estimate short-horizon resource pressure without choosing an action."""
    horizon = max(1, int(horizon_days))
    feed_required = state.animals * horizon
    wheat_held = state.shed.get("WHEAT", 0) + sum(
        unit.inventory.get("WHEAT", 0) for unit in state.units
    )
    fertilizer_held = state.shed.get("FERTILIZER", 0) + sum(
        unit.inventory.get("FERTILIZER", 0) for unit in state.units
    )
    return {
        "feed_required": feed_required,
        "feed_deficit": max(0, feed_required + 2 - wheat_held),
        "fertilizer_held": fertilizer_held,
        "shed_free": max(0, SHED_CAPACITY - state.shed_units),
        "mature_value": sum(
            state.prices.get(item, 0.0) * quantity
            for item, quantity in state.shed.items()
            if item not in {"WHEAT", "FERTILIZER", *ANIMALS}
        ),
    }


def job_candidates(obs: Any, state: LogisticsState | None = None) -> tuple[JobCandidate, ...]:
    """List urgent local jobs without modifying or selecting an action."""
    state = state or extract_state(obs)
    player = _count(_get(obs, "player", 0))
    farms = list(_get(obs, "farms", []) or [])
    farm = farms[player] if player < len(farms) else {}
    tiles = _get(farm, "tiles", []) or []
    jobs: list[JobCandidate] = []
    for unit in state.units:
        tile = _tile_at(tiles, unit.position)
        if not isinstance(tile, Mapping):
            continue
        if _count(tile.get("yield_units")) > 0:
            jobs.append(JobCandidate(unit.actor, "HARVEST", 1000, unit.position, "ready yield"))
            continue
        if tile.get("kind") == "PLANT" and not tile.get("watered_today", False):
            jobs.append(JobCandidate(unit.actor, "WATER", 700, unit.position, "not watered today"))
            continue
        if tile.get("animal"):
            if not tile.get("fed_today", False) and unit.inventory.get("WHEAT", 0) > 0:
                jobs.append(JobCandidate(unit.actor, "FEED", 950, unit.position, "animal needs feed"))
            elif not tile.get("cared_today", False):
                jobs.append(JobCandidate(unit.actor, "CARE", 800, unit.position, "animal needs care"))
            elif tile.get("fertilizer_available", False):
                jobs.append(
                    JobCandidate(unit.actor, "COLLECT_FERTILIZER", 780, unit.position, "fertilizer ready")
                )
    return tuple(sorted(jobs, key=lambda job: (-job.priority, job.actor, job.position)))


def shadow_report(obs: Any, action: Mapping[str, Any]) -> dict[str, Any]:
    """Return JSON-friendly diagnostics for one proposed action."""
    state = extract_state(obs)
    jobs = job_candidates(obs, state)
    operations = [action.get("farmer", [])] + list(action.get("hands", []) or [])
    op_names = [operation[0] for operation in operations if operation]
    return {
        "step": state.step,
        "day": state.day,
        "cash": state.cash,
        "animals": state.animals,
        "shed_units": state.shed_units,
        "resource_plan": resource_plan(state),
        "jobs": [job.__dict__ for job in jobs],
        "urgent_jobs_unserved": sum(job.kind not in op_names for job in jobs),
    }
