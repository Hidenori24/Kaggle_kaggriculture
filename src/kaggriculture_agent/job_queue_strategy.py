"""Observation-driven job queue challenger.

This is a deliberately independent experiment.  Every turn it builds a
priority queue from the visible board and assigns different jobs to different
workers.  No process-local ledger is required: the next observation is the
source of truth after every action.
"""

from __future__ import annotations

from typing import Any

from .full_strategy import (
    ANIMAL_STRUCTURE,
    ANIMALS,
    FAST_CROP,
    HIGH_VALUE_CROP,
    _act_on_tile,
    _find_tiles,
    _move,
    _shed_access,
    _tile_at,
    _value,
)


def _int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _state(obs: Any) -> tuple[dict[str, Any], dict[str, Any], int, int]:
    player = _int(_value(obs, "player", 0))
    farms = _value(obs, "farms", []) or []
    farm = farms[player] if player < len(farms) else {}
    private = _value(obs, "private", {}) or {}
    step = _int(_value(obs, "step", 0))
    day = _int(_value(obs, "day", step // 24))
    return farm, private, step, day


def _animals(farm: Any, private: Any) -> list[tuple[int, int, Any]]:
    tiles = _value(farm, "tiles", []) or []
    result = _find_tiles(tiles, lambda tile: isinstance(tile, dict) and tile.get("animal"))
    shed = _value(private, "shed", {}) or {}
    for animal in ANIMALS:
        if _int(shed.get(animal, 0)):
            result.append((-1, -1, {"animal": animal, "from_shed": True}))
    return result


def _unfed_animals(tiles: list[Any]) -> list[tuple[int, int, Any]]:
    return _find_tiles(
        tiles,
        lambda tile: isinstance(tile, dict)
        and tile.get("animal")
        and not tile.get("fed_today", False),
    )


def _needs(farm: Any, private: Any, day: int) -> list[tuple[int, int, str]]:
    tiles = _value(farm, "tiles", []) or []
    jobs: list[tuple[int, int, str]] = []
    # Harvest is cash-generating and must outrank maintenance.
    for x, y, tile in _find_tiles(tiles, lambda t: isinstance(t, dict) and t.get("yield_units", 0) > 0):
        jobs.append((x, y, "HARVEST"))
    for x, y, tile in _unfed_animals(tiles):
        jobs.append((x, y, "FEED"))
    for x, y, tile in _find_tiles(
        tiles,
        lambda t: isinstance(t, dict)
        and t.get("animal")
        and not t.get("cared_today", False),
    ):
        jobs.append((x, y, "CARE"))
    for x, y, tile in _find_tiles(
        tiles,
        lambda t: isinstance(t, dict)
        and t.get("kind") == "PLANT"
        and not t.get("watered_today", False),
    ):
        jobs.append((x, y, "WATER"))
    fertilizer = _int((_value(private, "shed", {}) or {}).get("FERTILIZER", 0))
    if fertilizer:
        for x, y, tile in _find_tiles(
            tiles,
            lambda t: isinstance(t, dict) and t.get("kind") == "PLANT",
        ):
            jobs.append((x, y, "FERTILIZE"))
    return jobs


def _market_orders(farm: Any, private: Any, day: int, step: int) -> list[list[Any]]:
    if step != 0 and step % 24 != 0:
        return []
    shed = _value(private, "shed", {}) or {}
    orders: list[list[Any]] = []
    for item, quantity in shed.items():
        if _int(quantity) and item not in {"WHEAT", "FERTILIZER", *ANIMALS}:
            orders.append(["SELL", item, _int(quantity)])
    farm_money = float(_value(farm, "money", 0) or 0)
    unlocked = list(_value(farm, "unlocked_quadrants", ["NW"]) or ["NW"])
    animals = sum(1 for _, _, tile in _animals(farm, private) if not tile.get("from_shed"))
    animals += sum(_int(shed.get(animal, 0)) for animal in ANIMALS)
    seeds = _value(private, "seeds", {}) or {}

    # Build a cash reserve before expansion.  Expansion is only attempted once
    # and the animal purchase is delayed until the next market turn.
    if len(unlocked) == 1 and day >= 7 and farm_money >= 1_800:
        orders.append(["BUY_LAND"])
    if day == 0:
        orders.append(["BUY_SEED", HIGH_VALUE_CROP, 12])
        orders.append(["BUY_SEED", FAST_CROP, 12])
    elif _int(seeds.get(FAST_CROP, 0)) < 5 and farm_money >= 200:
        orders.append(["BUY_SEED", FAST_CROP, 6 - _int(seeds.get(FAST_CROP, 0))])
    elif day < 22 and _int(seeds.get(HIGH_VALUE_CROP, 0)) < 3 and farm_money >= 300:
        orders.append(["BUY_SEED", HIGH_VALUE_CROP, 3 - _int(seeds.get(HIGH_VALUE_CROP, 0))])
    if len(unlocked) >= 2 and animals == 0 and day >= 9 and farm_money >= 700:
        orders.append(["BUY_ANIMAL", "COW", 1])

    hires = _int(_value(farm, "hires_today", 0))
    target_hires = 6 if day < 12 else 8
    if farm_money >= 500:
        orders.extend([["HIRE"] for _ in range(max(0, min(2, target_hires - hires)))])
    return orders[:10]


def _inventory_action(
    position: list[int], inventory: dict[str, int], farm: Any, private: Any, tiles: list[Any], role: str,
) -> list[Any] | None:
    if not inventory:
        return None
    unfed = _unfed_animals(tiles)
    if inventory.get("WHEAT", 0) > 0 and unfed:
        target = min(unfed, key=lambda item: abs(item[0] - position[0]) + abs(item[1] - position[1]))
        if tuple(position) == (target[0], target[1]):
            return ["FEED"]
        return _move(position, (target[0], target[1]))
    if any(item in ANIMALS for item in inventory):
        structures = _find_tiles(
            tiles,
            lambda tile: isinstance(tile, dict) and tile.get("kind") in {"COOP", "PASTURE"}
            and "animal" not in tile,
        )
        for animal in ANIMALS:
            if inventory.get(animal, 0) <= 0:
                continue
            wanted = next((s for s in structures if s[2].get("kind") == ANIMAL_STRUCTURE[animal]), None)
            if wanted is not None:
                if tuple(position) == wanted[:2]:
                    return ["PLACE", animal]
                return _move(position, wanted[:2])
    access = _shed_access(10)
    if tuple(position) in access:
        return ["DROP"]
    return _move(position, access[0])


def _unit_action(
    position: list[int], tile: Any, inventory: dict[str, int], farm: Any, private: Any,
    tiles: list[Any], job: tuple[int, int, str] | None, day: int,
) -> list[Any]:
    local = _act_on_tile(tile, private, day, inventory)
    if local is not None:
        return local
    carried = _inventory_action(position, inventory, farm, private, tiles, "worker")
    if carried is not None:
        return carried
    if job is not None:
        target = job[:2]
        if tuple(position) == target:
            if job[2] == "PLANT":
                seeds = _value(private, "seeds", {}) or {}
                crop = FAST_CROP if _int(seeds.get(FAST_CROP, 0)) else HIGH_VALUE_CROP
                return ["PLANT", crop] if _int(seeds.get(crop, 0)) else ["PASS"]
            return [job[2]]
        return _move(position, target)
    return ["PASS"]


def choose_action(obs: Any) -> dict[str, Any]:
    farm, private, step, day = _state(obs)
    if not farm:
        return {"farmer": ["PASS"], "hands": [], "market": []}
    tiles = _value(farm, "tiles", []) or []
    inventories = list(_value(private, "inventories", []) or [])
    jobs = _needs(farm, private, day)
    seeds = _value(private, "seeds", {}) or {}
    if _int(seeds.get(FAST_CROP, 0)) or _int(seeds.get(HIGH_VALUE_CROP, 0)):
        empty = _find_tiles(tiles, lambda tile: tile is None)
        jobs.extend((x, y, "PLANT") for x, y, _ in empty[: max(0, 8 - len(jobs))])

    positions = [list(_value(farm, "farmer", [4, 4]))]
    positions.extend(list(position) for position in (_value(farm, "hands", []) or []))
    actions: list[list[Any]] = []
    used: set[tuple[int, int, str]] = set()
    for index, position in enumerate(positions):
        inventory = inventories[index] if index < len(inventories) else {}
        job = next((candidate for candidate in jobs if candidate not in used), None)
        if job is not None:
            used.add(job)
        actions.append(_unit_action(position, _tile_at(tiles, position), inventory, farm, private, tiles, job, day))

    return {"farmer": actions[0], "hands": actions[1:], "market": _market_orders(farm, private, day, step)}
