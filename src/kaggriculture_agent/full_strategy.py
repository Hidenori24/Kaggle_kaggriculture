from __future__ import annotations

"""Capability-complete, deterministic Kaggriculture policy.

This module intentionally keeps the policy state in the observation.  That is
important for Kaggle replay/restart behavior: every decision can be reproduced
from the current observation without relying on process-local memory.
"""

from typing import Any

from .strategy import BaselineConfig, choose_action as choose_baseline_action


CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
FAST_CROP = "WHEAT"
HIGH_VALUE_CROP = "MELON"
ANIMALS = ("COW", "SHEEP", "GOOSE")
ANIMAL_STRUCTURE = {"COW": "PASTURE", "SHEEP": "PASTURE", "GOOSE": "COOP"}
ANIMAL_PRODUCT = {"COW": "MILK", "SHEEP": "WOOL", "GOOSE": "EGG"}
YIELD_DAYS = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}
QUADRANT_ORIGIN = {"NW": (0, 0), "NE": (1, 0), "SW": (0, 1), "SE": (1, 1)}


def _has_complex_state(obs: Any) -> bool:
    """Return whether the observed game has entered the extended state space.

    The production entry point must not replace the proven melon loop merely
    because the calendar reached the policy hand-off day.  The extended policy
    is therefore activated only after land, animals, structures, or their
    logistics are actually present.  This makes the new capabilities a safe
    extension instead of an unconditional late-game regression.
    """
    farms = _value(obs, "farms", []) or []
    player = int(_value(obs, "player", 0) or 0)
    if player < len(farms):
        farm = farms[player]
        if len(_value(farm, "unlocked_quadrants", ["NW"]) or ["NW"]) > 1:
            return True
        for row in _value(farm, "tiles", []) or []:
            for tile in row:
                if isinstance(tile, dict) and (tile.get("kind") in {"COOP", "PASTURE"} or "animal" in tile):
                    return True
    private = _value(obs, "private", {}) or {}
    for container_name in ("shed", "inventories"):
        container = _value(private, container_name, {}) or []
        pairs = container.items() if isinstance(container, dict) else (
            item for inv in container for item in (inv or {}).items()
        )
        for key, quantity in pairs:
            if (key in ANIMALS or key in {"WHEAT", "FERTILIZER"}) and int(quantity or 0) > 0:
                return True
    return False


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _move(current: list[int], target: tuple[int, int]) -> list[str]:
    x, y = current
    tx, ty = target
    if x < tx:
        return ["EAST"]
    if x > tx:
        return ["WEST"]
    if y < ty:
        return ["SOUTH"]
    if y > ty:
        return ["NORTH"]
    return ["PASS"]


def _route(size: int, quadrants: list[str]) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    for quadrant in ("NW", "NE", "SW", "SE"):
        if quadrant not in quadrants:
            continue
        ox, oy = QUADRANT_ORIGIN[quadrant]
        for local_y in range(size - 1, -1, -1):
            xs = range(size - 1, -1, -1) if (size - 1 - local_y) % 2 == 0 else range(size)
            cells.extend((ox * size + x, oy * size + local_y) for x in xs)
    return cells


def _quadrant(position: list[int], size: int) -> str:
    return ("N" if position[1] < size else "S") + ("W" if position[0] < size else "E")


def _in_quadrants(position: list[int], size: int, quadrants: list[str]) -> bool:
    return _quadrant(position, size) in quadrants


def _tile_at(tiles: list[Any], position: list[int]) -> Any:
    x, y = position
    if 0 <= y < len(tiles) and 0 <= x < len(tiles[y]):
        return tiles[y][x]
    return "LOCKED"


def _empty_cells(tiles: list[Any], quadrants: list[str], size: int) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for position in _route(size, quadrants):
        if _tile_at(tiles, list(position)) is None:
            result.append(position)
    return result


def _shed_access(size: int = 10) -> list[tuple[int, int]]:
    half = size // 2
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]


def _find_tiles(tiles: list[Any], predicate: Any) -> list[tuple[int, int, Any]]:
    found: list[tuple[int, int, Any]] = []
    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            if predicate(tile):
                found.append((x, y, tile))
    return found


def _market_orders(
    obs: Any,
    farm: Any,
    private: Any,
    day: int,
    max_orders: int = 10,
) -> list[list[Any]]:
    """Create bounded, budget-aware market orders.

    Orders are staged: sell output first, then reinvest in food/seeds/animals,
    then hire.  Every order is conservative because invalid orders are silent
    no-ops in the SDK.
    """
    orders: list[list[Any]] = []
    market_turn = int(_value(obs, "step", 0) or 0) == 0 or int(_value(obs, "hour", 0) or 0) == 0
    if not market_turn:
        return orders
    shed = _value(private, "shed", {}) or {}
    animals_in_shed = {animal: int(shed.get(animal, 0) or 0) for animal in ANIMALS}
    animal_count = sum(
        1
        for _, _, tile in _find_tiles(
            _value(farm, "tiles", []) or [], lambda t: isinstance(t, dict) and "animal" in t
        )
    ) + sum(animals_in_shed.values())
    wheat_reserve = max(0, animal_count + 4)

    for product, quantity in shed.items():
        quantity = int(quantity or 0)
        if quantity <= 0 or product in {"FERTILIZER", "WHEAT", *ANIMALS}:
            continue
        orders.append(["SELL", product, quantity])
    wheat_surplus = int(shed.get("WHEAT", 0) or 0) - wheat_reserve
    if wheat_surplus > 0:
        orders.append(["SELL", "WHEAT", wheat_surplus])

    money = float(_value(farm, "money", 0) or 0)
    hires_today = int(_value(farm, "hires_today", 0) or 0)
    hands = _value(farm, "hands", []) or []
    remaining_hires = max(0, 10 - hires_today)
    hire_costs = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
    hire_budget = sum(hire_costs[hires_today : hires_today + remaining_hires])
    reserve = 300 + 50 * max(0, animal_count - 1)
    seeds = _value(private, "seeds", {}) or {}

    unlocked = _value(farm, "unlocked_quadrants", ["NW"]) or ["NW"]
    if len(unlocked) == 1 and day >= 10 and money >= 1_000 + hire_budget + reserve:
        orders.append(["BUY_LAND"])
        unlocked = ["NW", "NE"]

    # Seeds are cheap inputs and are purchased only when the observed reserve
    # is low.  Wheat serves both as a fast crop and animal feed.
    wheat_target = max(8, animal_count + 4)
    if animal_count > 0 and seeds.get(FAST_CROP, 0) < wheat_target and money >= 10 * (wheat_target - seeds.get(FAST_CROP, 0)) + reserve:
        orders.append(["BUY_SEED", FAST_CROP, wheat_target - seeds.get(FAST_CROP, 0)])
    melon_target = 15 if day == 0 else 3
    if seeds.get(HIGH_VALUE_CROP, 0) < melon_target and money >= 80 * melon_target + reserve:
        orders.append(["BUY_SEED", HIGH_VALUE_CROP, melon_target])
    if len(unlocked) >= 2 and day >= 12 and animal_count == 0 and money >= 400 + reserve:
        orders.append(["BUY_ANIMAL", "COW", 1])

    # Purchased WHEAT is deliberately separate from seed WHEAT.  It enters the
    # shed and can be picked up by a caretaker for FEED.
    if animal_count > 0 and int(shed.get("WHEAT", 0) or 0) < wheat_reserve and money >= 10 + reserve:
        orders.append(["BUY_PRODUCT", "WHEAT", wheat_reserve - int(shed.get("WHEAT", 0) or 0)])

    available_slots = max(0, max_orders - len(orders))
    if money >= hire_budget + reserve and remaining_hires:
        orders.extend([["HIRE"] for _ in range(min(remaining_hires, available_slots))])
    return orders[:max_orders]


def _act_on_tile(tile: Any, private: Any, day: int, inventory: dict[str, int]) -> list[Any] | None:
    if not isinstance(tile, dict):
        return None
    if tile.get("kind") == "PLANT":
        if not tile.get("watered_today", False):
            return ["WATER"]
        crop = str(tile.get("crop", HIGH_VALUE_CROP))
        if tile.get("yield_units", 0) > 0 and day - tile.get("planted_day", day) >= YIELD_DAYS.get(crop, 2):
            return ["HARVEST"]
        if inventory.get("FERTILIZER", 0) > 0 and day < tile.get("planted_day", day) + 8:
            return ["FERTILIZE"]
    if "animal" in tile:
        if tile.get("yield_units", 0) > 0:
            return ["HARVEST"]
        if not tile.get("fed_today", False) and inventory.get("WHEAT", 0) > 0:
            return ["FEED"]
        if not tile.get("cared_today", False):
            return ["CARE"]
        if tile.get("fertilizer_available", False):
            return ["COLLECT_FERTILIZER"]
    return None


def _unit_action(
    position: list[int],
    tile: Any,
    target: tuple[int, int],
    private: Any,
    tiles: list[Any],
    day: int,
    size: int,
    role: str,
    inventory: dict[str, int],
    active_quadrants: list[str],
) -> list[Any]:
    """Select a legal action with local-tile priority and safe movement fallback."""
    local = _act_on_tile(tile, private, day, inventory)
    if local is not None:
        return local

    shed = _value(private, "shed", {}) or {}
    # ``size`` is the side of one quadrant; the SDK board is two quadrants
    # wide and tall.  Using ``size`` directly would make every worker search
    # for a nonexistent 5x5 shed entrance on the 10x10 board.
    access = _shed_access(size * 2)
    animals = [a for a in ANIMALS if int(shed.get(a, 0) or 0) > 0]
    structures = _find_tiles(tiles, lambda t: isinstance(t, dict) and t.get("kind") in {"COOP", "PASTURE"})

    # Carrying harvested products or fertilizer is always resolved before
    # starting another job.  This prevents inventory stranded losses.
    if inventory:
        if inventory.get("WHEAT", 0) > 0:
            needs_feed = _find_tiles(
                tiles,
                lambda t: isinstance(t, dict) and "animal" in t and not t.get("fed_today", False),
            )
            if needs_feed:
                animal = min(needs_feed, key=lambda p: abs(p[0] - position[0]) + abs(p[1] - position[1]))
                if tuple(position) == (animal[0], animal[1]):
                    return ["FEED"]
                return _move(position, (animal[0], animal[1]))
        if inventory.get("FERTILIZER", 0) > 0:
            plants = _find_tiles(tiles, lambda t: isinstance(t, dict) and t.get("kind") == "PLANT")
            if plants:
                plant = min(plants, key=lambda p: abs(p[0] - position[0]) + abs(p[1] - position[1]))
                if tuple(position) == (plant[0], plant[1]):
                    return ["FERTILIZE"]
                return _move(position, (plant[0], plant[1]))
        animal_items = [a for a in ANIMALS if inventory.get(a, 0) > 0]
        if animal_items:
            wanted = next((s for s in structures if s[2].get("kind") == ANIMAL_STRUCTURE[animal_items[0]] and "animal" not in s[2]), None)
            if wanted:
                if tuple(position) == (wanted[0], wanted[1]):
                    return ["PLACE", animal_items[0]]
                return _move(position, (wanted[0], wanted[1]))
        if tuple(position) in access:
            return ["DROP"]
        return _move(position, access[0])

    live_animals = _find_tiles(tiles, lambda t: isinstance(t, dict) and "animal" in t)
    empty_animal_structures = [
        s for s in structures if "animal" not in s[2] and s[2].get("kind") in {ANIMAL_STRUCTURE[a] for a in animals}
    ]
    if animals and empty_animal_structures and role == "builder":
        if tuple(position) in access:
            return ["PICKUP", animals[0], 1]
        return _move(position, access[0])

    if live_animals and int(shed.get("WHEAT", 0) or 0) > 0 and role == "builder":
        if tuple(position) in access:
            return ["PICKUP", "WHEAT", 1]
        return _move(position, access[0])

    # Build one structure before placing the first animal.  Prefer an empty
    # cell in the newly opened quadrant so the NW crop loop remains intact.
    if animals and role == "builder":
        wanted_kind = ANIMAL_STRUCTURE[animals[0]]
        if not any(s[2].get("kind") == wanted_kind and "animal" not in s[2] for s in structures):
            empty = _empty_cells(tiles, active_quadrants[-1:], size)
            if empty:
                if tuple(position) == empty[0]:
                    return ["BUILD_PASTURE" if wanted_kind == "PASTURE" else "BUILD_COOP"]
                return _move(position, empty[0])

    if tile is None:
        seeds = _value(private, "seeds", {}) or {}
        crop = FAST_CROP if role == "explorer" else HIGH_VALUE_CROP
        if seeds.get(crop, 0) > 0 and _in_quadrants(position, size, active_quadrants):
            return ["PLANT", crop]
    if tile == "LOCKED" or not _in_quadrants(position, size, active_quadrants):
        return _move(position, target)
    return _move(position, target)


def choose_action(obs: Any) -> dict[str, Any]:
    """Capability-complete deterministic policy with legal-action fallbacks."""
    if not _has_complex_state(obs):
        # Preserve the measured baseline until the extended state is actually
        # in play.  This is also the default path for ordinary Kaggriculture
        # episodes, so enabling the module cannot silently reduce the score.
        return choose_baseline_action(obs, BaselineConfig(enable_expansion=False))

    farms = _value(obs, "farms", []) or []
    player = int(_value(obs, "player", 0) or 0)
    private = _value(obs, "private", {}) or {}
    if not farms or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}

    farm = farms[player]
    step = int(_value(obs, "step", 0) or 0)
    day = int(_value(obs, "day", step // 24) or 0)
    size = 5
    tiles = _value(farm, "tiles", []) or []
    unlocked = _value(farm, "unlocked_quadrants", ["NW"]) or ["NW"]
    active = list(unlocked)
    route = _route(size, active)

    farmer_position = list(_value(farm, "farmer", [4, 4]))
    inventories = _value(private, "inventories", []) or []
    farmer_inventory = inventories[0] if inventories else {}
    farmer_target = route[step % len(route)]
    farmer_action = _unit_action(
        farmer_position,
        _tile_at(tiles, farmer_position),
        farmer_target,
        private,
        tiles,
        day,
        size,
        "farmer",
        farmer_inventory,
        active,
    )

    hands = _value(farm, "hands", []) or []
    hand_actions: list[list[Any]] = []
    for index, raw_position in enumerate(hands, start=1):
        position = list(raw_position)
        inventory = inventories[index] if index < len(inventories) else {}
        role = "builder" if index == len(hands) else ("explorer" if index > 6 and len(active) > 1 else "farmer")
        target_route = _route(size, ["NE"]) if role == "explorer" and "NE" in active else route
        target = target_route[(index * 4 + day) % len(target_route)]
        hand_actions.append(
            _unit_action(
                position,
                _tile_at(tiles, position),
                target,
                private,
                tiles,
                day,
                size,
                role,
                inventory,
                ["NE"] if role == "explorer" and "NE" in active else ["NW"],
            )
        )

    return {"farmer": farmer_action, "hands": hand_actions, "market": _market_orders(obs, farm, private, day)}

