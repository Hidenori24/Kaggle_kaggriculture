from __future__ import annotations

from dataclasses import dataclass
from typing import Any


FIRST_YIELD_DAYS = {
    "WHEAT": 2,
    "CARROT": 2,
    "TOMATO": 8,
    "STRAWBERRY": 10,
    "MELON": 10,
}


@dataclass(frozen=True)
class BaselineConfig:
    seed_crop: str = "MELON"
    seed_purchase_count: int = 15
    active_quadrant_size: int = 5
    max_hands_per_day: int = 6


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _move_towards(current: list[int], target: tuple[int, int]) -> list[str]:
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


def _next_route_target(position: list[int], size: int) -> tuple[int, int]:
    route: list[tuple[int, int]] = []
    for y in range(size - 1, -1, -1):
        xs = range(size - 1, -1, -1) if (size - 1 - y) % 2 == 0 else range(size)
        route.extend((x, y) for x in xs)
    current = (position[0], position[1])
    try:
        index = route.index(current)
    except ValueError:
        return route[0]
    return route[(index + 1) % len(route)]


def _route_cell(index: int, day: int, size: int) -> tuple[int, int]:
    route: list[tuple[int, int]] = []
    for y in range(size - 1, -1, -1):
        xs = range(size - 1, -1, -1) if (size - 1 - y) % 2 == 0 else range(size)
        route.extend((x, y) for x in xs)
    return route[(index * 4 + day) % len(route)]


def _tile_at(tiles: list[Any], position: list[int]) -> Any:
    x, y = position
    if 0 <= y < len(tiles) and 0 <= x < len(tiles[y]):
        return tiles[y][x]
    return "LOCKED"


def _unit_action(
    position: list[int],
    tile: Any,
    private: dict[str, Any],
    day: int,
    config: BaselineConfig,
    inventory: dict[str, int] | None = None,
    target: tuple[int, int] | None = None,
) -> list[Any]:
    inventory = inventory or {}
    if isinstance(tile, dict):
        kind = tile.get("kind")
        if kind == "PLANT":
            if not tile.get("watered_today", False):
                return ["WATER"]
            crop = str(tile.get("crop", config.seed_crop))
            mature_day = FIRST_YIELD_DAYS.get(crop, 2)
            if tile.get("yield_units", 0) > 0 and day - tile.get("planted_day", day) >= mature_day:
                return ["HARVEST"]
        elif kind in ("COOP", "PASTURE") and tile.get("animal"):
            if tile.get("yield_units", 0) > 0:
                return ["COLLECT_FERTILIZER"]
            if not tile.get("fed_today", False):
                return ["FEED"]
            if not tile.get("cared_today", False):
                return ["CARE"]

    seeds = _value(private, "seeds", {}) or {}
    if tile is None and seeds.get(config.seed_crop, 0) > 0:
        return ["PLANT", config.seed_crop]
    return _move_towards(position, target or _next_route_target(position, config.active_quadrant_size))


def choose_action(obs: Any, config: BaselineConfig = BaselineConfig()) -> dict[str, Any]:
    """Parallel melon farming baseline with daily hiring and selling."""
    step = int(_value(obs, "step", 0) or 0)
    day = int(_value(obs, "day", step // 24) or 0)
    hour = int(_value(obs, "hour", step % 24) or 0)
    farms = _value(obs, "farms", []) or []
    player = int(_value(obs, "player", 0) or 0)
    private = _value(obs, "private", {}) or {}
    market: list[list[Any]] = []

    shed = _value(private, "shed", {}) or {}
    for product, quantity in shed.items():
        if int(quantity or 0) > 0 and product not in {"FERTILIZER"}:
            market.append(["SELL", product, int(quantity)])

    if not farms or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": market}

    farm = farms[player]
    money = float(_value(farm, "money", 0) or 0)
    hires_today = int(_value(farm, "hires_today", 0) or 0)
    if step == 0 or hour == 0:
        remaining = max(0, config.max_hands_per_day - hires_today)
        hire_budget = sum([1, 1, 2, 3, 5, 8][hires_today : hires_today + remaining])
        seeds = _value(private, "seeds", {}) or {}
        purchase_count = config.seed_purchase_count if step == 0 else 3
        if step != 0 and seeds.get(config.seed_crop, 0) >= 12:
            purchase_count = 0
        seed_cost = 80 * purchase_count
        if purchase_count and money >= hire_budget + seed_cost + 300:
            market.append(["BUY_SEED", config.seed_crop, purchase_count])
        if money >= hire_budget + 100:
            market.extend([["HIRE"] for _ in range(remaining)])

    tiles = _value(farm, "tiles", []) or []
    farmer_position = list(_value(farm, "farmer", [4, 4]))
    inventories = _value(private, "inventories", []) or []
    farmer_inventory = inventories[0] if inventories else {}
    farmer_action = _unit_action(
        farmer_position, _tile_at(tiles, farmer_position), private, day, config, farmer_inventory
    )

    hand_actions: list[list[Any]] = []
    for index, hand_position in enumerate(_value(farm, "hands", []) or [], start=1):
        hand_position = list(hand_position)
        inventory = inventories[index] if index < len(inventories) else {}
        target = _route_cell(index - 1, day, config.active_quadrant_size)
        if tuple(hand_position) == target:
            target = _next_route_target(hand_position, config.active_quadrant_size)
        hand_actions.append(
            _unit_action(
                hand_position,
                _tile_at(tiles, hand_position),
                private,
                day,
                config,
                inventory,
                target,
            )
        )

    return {"farmer": farmer_action, "hands": hand_actions, "market": market}


if __name__ == "__main__":
    pass
