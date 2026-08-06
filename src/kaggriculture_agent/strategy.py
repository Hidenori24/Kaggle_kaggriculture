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

QUADRANT_ORIGIN = {
    "NW": (0, 0),
    "NE": (1, 0),
    "SW": (0, 1),
    "SE": (1, 1),
}


@dataclass(frozen=True)
class BaselineConfig:
    seed_crop: str = "MELON"
    exploration_crop: str = "WHEAT"
    seed_purchase_count: int = 15
    active_quadrant_size: int = 5
    max_hands_per_day: int = 10
    enable_expansion: bool = False


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


def _route_cells(size: int, quadrants: list[str] | None = None) -> list[tuple[int, int]]:
    """Build a deterministic serpentine route over every unlocked quadrant."""
    quadrants = quadrants or ["NW"]
    route: list[tuple[int, int]] = []
    for quadrant in ("NW", "NE", "SW", "SE"):
        if quadrant not in quadrants:
            continue
        quadrant_x, quadrant_y = QUADRANT_ORIGIN[quadrant]
        for local_y in range(size - 1, -1, -1):
            xs = range(size - 1, -1, -1) if (size - 1 - local_y) % 2 == 0 else range(size)
            route.extend((quadrant_x * size + x, quadrant_y * size + local_y) for x in xs)
    return route


def _next_route_target(
    position: list[int],
    size: int,
    quadrants: list[str] | None = None,
    route: list[tuple[int, int]] | None = None,
) -> tuple[int, int]:
    route = route or _route_cells(size, quadrants)
    current = (position[0], position[1])
    try:
        index = route.index(current)
    except ValueError:
        return route[0]
    return route[(index + 1) % len(route)]


def _route_cell(
    index: int, day: int, size: int, quadrants: list[str] | None = None
) -> tuple[int, int]:
    route = _route_cells(size, quadrants)
    return route[(index * 4 + day) % len(route)]


def _tile_at(tiles: list[Any], position: list[int]) -> Any:
    x, y = position
    if 0 <= y < len(tiles) and 0 <= x < len(tiles[y]):
        return tiles[y][x]
    return "LOCKED"


def _quadrant_of_position(position: list[int], size: int) -> str:
    x, y = position
    return ("N" if y < size else "S") + ("W" if x < size else "E")


def _position_in_quadrants(position: list[int], size: int, quadrants: list[str]) -> bool:
    return _quadrant_of_position(position, size) in quadrants


def _unit_action(
    position: list[int],
    tile: Any,
    private: dict[str, Any],
    day: int,
    config: BaselineConfig,
    inventory: dict[str, int] | None = None,
    target: tuple[int, int] | None = None,
    route: list[tuple[int, int]] | None = None,
    crop: str | None = None,
) -> list[Any]:
    """Choose one action for the farmer or one hired hand."""
    inventory = inventory or {}
    if isinstance(tile, dict):
        kind = tile.get("kind")
        if kind == "PLANT":
            if not tile.get("watered_today", False):
                return ["WATER"]
            planted_crop = str(tile.get("crop", crop or config.seed_crop))
            mature_day = FIRST_YIELD_DAYS.get(planted_crop, 2)
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
    active_crop = crop or config.seed_crop
    if tile is None and seeds.get(active_crop, 0) > 0:
        return ["PLANT", active_crop]
    return _move_towards(
        position,
        target or _next_route_target(position, config.active_quadrant_size, route=route),
    )


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
        hire_costs = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
        hire_budget = sum(hire_costs[hires_today : hires_today + remaining])
        seeds = _value(private, "seeds", {}) or {}
        purchase_count = config.seed_purchase_count if step == 0 else 3
        if step != 0 and seeds.get(config.seed_crop, 0) >= 12:
            purchase_count = 0
        seed_cost = 80 * purchase_count
        can_buy_seed = bool(purchase_count and money >= hire_budget + seed_cost + 300)
        if can_buy_seed:
            market.append(["BUY_SEED", config.seed_crop, purchase_count])

        unlocked = _value(farm, "unlocked_quadrants", ["NW"]) or ["NW"]
        # First expansion is the safe, high-value milestone.  A second
        # expansion is left for a later experiment after dedicated routing
        # and seed budgeting are in place.
        land_cost = {1: 1_000}.get(len(unlocked))
        buy_land = config.enable_expansion and (
            land_cost is not None
            and len(unlocked) == 1
            and day >= 18
            and money >= hire_budget + (seed_cost if can_buy_seed else 0) + land_cost + 500
        )
        if buy_land:
            market.append(["BUY_LAND"])
            # Melons planted in the newly opened area cannot mature before
            # the 30-day episode ends.  Buy a small wheat budget for the
            # dedicated explorer so the first expansion has a short cycle.
            expansion_seed_count = 30
            expansion_seed_cost = 10 * expansion_seed_count
            if money >= hire_budget + land_cost + expansion_seed_cost + 500:
                market.append(["BUY_SEED", config.exploration_crop, expansion_seed_count])

        hire_slots = max(0, 10 - len(market))
        if money >= hire_budget + 100:
            market.extend([["HIRE"] for _ in range(min(remaining, hire_slots))])

    tiles = _value(farm, "tiles", []) or []
    unlocked_quadrants = (
        (_value(farm, "unlocked_quadrants", ["NW"]) or ["NW"])
        if config.enable_expansion
        else ["NW"]
    )
    farmer_route = _route_cells(config.active_quadrant_size, ["NW"])
    farmer_position = list(_value(farm, "farmer", [4, 4]))
    inventories = _value(private, "inventories", []) or []
    farmer_inventory = inventories[0] if inventories else {}
    farmer_tile = _tile_at(tiles, farmer_position)
    if farmer_tile is None and not _position_in_quadrants(
        farmer_position, config.active_quadrant_size, ["NW"]
    ):
        farmer_action = _move_towards(farmer_position, farmer_route[0])
    else:
        farmer_action = _unit_action(
            farmer_position,
            farmer_tile,
            private,
            day,
            config,
            farmer_inventory,
            target=None,
            route=farmer_route,
            crop=config.seed_crop,
        )

    hand_actions: list[list[Any]] = []
    for index, hand_position in enumerate(_value(farm, "hands", []) or [], start=1):
        hand_position = list(hand_position)
        inventory = inventories[index] if index < len(inventories) else {}
        # Keep six workers on the profitable NW loop.  Only the remaining hands
        # becomes an explorer after NE is unlocked; this makes expansion a
        # measured investment instead of sending half the workforce across a
        # newly opened, mostly empty quadrant.
        if index <= 6 or "NE" not in unlocked_quadrants:
            unit_quadrants = ["NW"]
            unit_crop = config.seed_crop
        else:
            unit_quadrants = ["NE"]
            unit_crop = config.exploration_crop
        unit_route = _route_cells(config.active_quadrant_size, unit_quadrants)
        target = _route_cell(index - 1, day, config.active_quadrant_size, unit_quadrants)
        if tuple(hand_position) == target:
            target = _next_route_target(
                hand_position,
                config.active_quadrant_size,
                unit_quadrants,
                unit_route,
            )
        hand_tile = _tile_at(tiles, hand_position)
        if hand_tile is None and not _position_in_quadrants(
            hand_position, config.active_quadrant_size, unit_quadrants
        ):
            hand_actions.append(_move_towards(hand_position, target))
        else:
            hand_actions.append(
                _unit_action(
                    hand_position,
                    hand_tile,
                    private,
                    day,
                    config,
                    inventory,
                    target,
                    unit_route,
                    unit_crop,
                )
            )

    return {"farmer": farmer_action, "hands": hand_actions, "market": market}

