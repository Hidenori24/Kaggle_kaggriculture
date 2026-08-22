"""Large exploratory observation-driven Kaggriculture strategy.

Unlike the replay policy, this module plans from the current farm state.  It
uses explicit phases so the expansion path is reachable from a fresh game:
build an initial cash reserve, buy land, buy a first animal, then service the
farm with local jobs.  The policy is intentionally experiment-only.
"""

from __future__ import annotations

from typing import Any, Mapping

from .full_strategy import ANIMALS, FAST_CROP, HIGH_VALUE_CROP, _route, _tile_at, _unit_action, _value
from .strategy import BaselineConfig, choose_action as baseline_action


def _count(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _farm(obs: Any) -> tuple[Any, Any, Any]:
    player = _count(_value(obs, "player", 0))
    farms = _value(obs, "farms", []) or []
    farm = farms[player] if player < len(farms) else {}
    private = _value(obs, "private", {}) or {}
    return farm, private, _value(obs, "market", {}) or {}


def _animal_count(farm: Any, private: Any) -> int:
    tiles = _value(farm, "tiles", []) or []
    shed = _value(private, "shed", {}) or {}
    return sum(
        1
        for row in tiles
        for tile in (row if isinstance(row, list) else [])
        if isinstance(tile, Mapping) and tile.get("animal")
    ) + sum(_count(shed.get(animal, 0)) for animal in ANIMALS)


def _market_orders(obs: Any, farm: Any, private: Any, day: int) -> list[list[Any]]:
    """Create a bounded phase-aware market plan."""
    step = _count(_value(obs, "step", 0))
    hour = _count(_value(obs, "hour", step % 24))
    if step != 0 and hour != 0:
        return []

    shed = _value(private, "shed", {}) or {}
    prices = _value(_value(obs, "market", {}) or {}, "prices", {}) or {}
    money = float(_value(farm, "money", 0) or 0)
    unlocked = list(_value(farm, "unlocked_quadrants", ["NW"]) or ["NW"])
    animals = _animal_count(farm, private)
    seeds = _value(private, "seeds", {}) or {}
    orders: list[list[Any]] = []

    # Sell only finished outputs.  Keep feed and fertilizer in the farm.
    for item, quantity in shed.items():
        if _count(quantity) > 0 and item not in {"WHEAT", "FERTILIZER", *ANIMALS}:
            orders.append(["SELL", item, _count(quantity)])
    feed_reserve = max(4, animals * 2)
    wheat_surplus = _count(shed.get("WHEAT", 0)) - feed_reserve
    if wheat_surplus > 0 and float(prices.get("WHEAT", 0) or 0) >= 20:
        orders.append(["SELL", "WHEAT", wheat_surplus])

    # Expansion is a milestone, not a permanent toggle.  Leave enough cash
    # for the next seed and hire cycle before placing the order.
    if len(unlocked) == 1 and day >= 6 and money >= 1_700:
        orders.append(["BUY_LAND"])
        unlocked.append("NE")

    if len(unlocked) >= 2 and animals == 0 and day >= 8 and money >= 650:
        orders.append(["BUY_ANIMAL", "COW", 1])

    wheat_seeds = _count(seeds.get(FAST_CROP, 0))
    if wheat_seeds < 8 and money >= 400:
        orders.append(["BUY_SEED", FAST_CROP, 8 - wheat_seeds])
    high_seeds = _count(seeds.get(HIGH_VALUE_CROP, 0))
    if day < 18 and high_seeds < 6 and money >= 600:
        orders.append(["BUY_SEED", HIGH_VALUE_CROP, 6 - high_seeds])

    if animals > 0 and _count(shed.get("WHEAT", 0)) < feed_reserve:
        need = feed_reserve - _count(shed.get("WHEAT", 0))
        if money >= 10 * need + 300:
            orders.append(["BUY_PRODUCT", "WHEAT", need])

    hires_today = _count(_value(farm, "hires_today", 0))
    if money >= 500 and hires_today < 10:
        orders.extend([["HIRE"] for _ in range(min(10 - hires_today, 4))])
    return orders[:10]


def choose_action(obs: Any) -> dict[str, Any]:
    farm, private, _market = _farm(obs)
    if not farm:
        return {"farmer": ["PASS"], "hands": [], "market": []}

    step = _count(_value(obs, "step", 0))
    day = _count(_value(obs, "day", step // 24))
    # Keep the proven initial cash-generating route for the first phase.
    if day < 6:
        return baseline_action(obs, BaselineConfig(enable_expansion=False))

    tiles = _value(farm, "tiles", []) or []
    active = list(_value(farm, "unlocked_quadrants", ["NW"]) or ["NW"])
    route = _route(5, active)
    inventories = list(_value(private, "inventories", []) or [])

    farmer_position = list(_value(farm, "farmer", [4, 4]))
    farmer_inventory = inventories[0] if inventories else {}
    farmer_target = route[step % len(route)]
    farmer_action = _unit_action(
        farmer_position, _tile_at(tiles, farmer_position), farmer_target,
        private, tiles, day, 5, "builder", farmer_inventory, active,
    )

    hands = list(_value(farm, "hands", []) or [])
    hand_actions: list[list[Any]] = []
    for index, raw_position in enumerate(hands, start=1):
        position = list(raw_position)
        inventory = inventories[index] if index < len(inventories) else {}
        role = "builder" if index == len(hands) else "farmer"
        target = route[(index * 4 + day) % len(route)]
        hand_actions.append(_unit_action(
            position, _tile_at(tiles, position), target, private, tiles, day,
            5, role, inventory, active,
        ))

    return {
        "farmer": farmer_action,
        "hands": hand_actions,
        "market": _market_orders(obs, farm, private, day),
    }
