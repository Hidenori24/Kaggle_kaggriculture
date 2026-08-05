from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BaselineConfig:
    seed_crop: str = "CARROT"
    seed_purchase_count: int = 20
    active_quadrant_size: int = 5


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
    """Return the next cell on a bottom-right-to-top-left serpentine route."""
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


def choose_action(obs: Any, config: BaselineConfig = BaselineConfig()) -> dict[str, Any]:
    """Choose a safe deterministic crop-growing action."""
    step = int(_value(obs, "step", 0) or 0)
    day = int(_value(obs, "day", step // 24) or 0)
    farms = _value(obs, "farms", []) or []
    player = int(_value(obs, "player", 0) or 0)
    private = _value(obs, "private", {}) or {}

    market: list[list[Any]] = []
    shed = _value(private, "shed", {}) or {}
    quantity = int(shed.get(config.seed_crop, 0) or 0)
    if quantity > 0:
        market.append(["SELL", config.seed_crop, quantity])
    if step == 0:
        market.append(["BUY_SEED", config.seed_crop, config.seed_purchase_count])

    if not farms or player >= len(farms):
        return {"farmer": ["PASS"], "market": market}

    farm = farms[player]
    position = list(_value(farm, "farmer", [4, 4]))
    tiles = _value(farm, "tiles", []) or []
    x, y = position
    tile = tiles[y][x] if 0 <= y < len(tiles) and 0 <= x < len(tiles[y]) else None

    if isinstance(tile, dict) and tile.get("kind") == "PLANT":
        if not tile.get("watered_today", False):
            return {"farmer": ["WATER"], "market": market}
        if tile.get("yield_units", 0) > 0 and day - tile.get("planted_day", day) >= 2:
            return {"farmer": ["HARVEST"], "market": market}

    seeds = _value(private, "seeds", {}) or {}
    if tile is None and seeds.get(config.seed_crop, 0) > 0:
        return {"farmer": ["PLANT", config.seed_crop], "market": market}

    target = _next_route_target(position, config.active_quadrant_size)
    return {"farmer": _move_towards(position, target), "market": market}
