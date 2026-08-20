"""Deterministic, observation-driven economic decisions.

The replay policy remains responsible for legal movement and animal logistics.
This module owns the part that a fixed action tape cannot solve: allocating a
limited budget between feed, seeds, and output sales under changing prices.
Every decision is bounded and read-only with respect to the observation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


ANIMALS = ("COW", "SHEEP", "GOOSE")
GROWTH_DAYS = {
    "WHEAT": 2,
    "CARROT": 2,
    "TOMATO": 8,
    "STRAWBERRY": 10,
    "MELON": 10,
}
OPTIONAL_CROPS = ("CARROT", "STRAWBERRY", "MELON")


@dataclass(frozen=True)
class EconomicPolicyConfig:
    """Safety limits for the adaptive economic layer."""

    enabled: bool = True
    first_adaptive_day: int = 5
    last_adaptive_day: int = 26
    minimum_cash: float = 1_200.0
    shed_pressure_limit: int = 78
    feed_safety_days: int = 2
    max_new_seed_units: int = 1
    max_crop_replacements_per_step: int = 1


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _count(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _seat_and_farm(obs: Any) -> tuple[int, Any]:
    seat = 1 if _count(_get(obs, "player", 0)) == 1 else 0
    farms = _get(obs, "farms", []) or []
    return seat, farms[seat] if seat < len(farms) else {}


def _animal_count(farm: Any, private: Any) -> int:
    total = 0
    for row in _get(farm, "tiles", []) or []:
        for tile in row if isinstance(row, list) else []:
            if isinstance(tile, Mapping) and tile.get("animal"):
                total += 1
    shed = _get(private, "shed", {}) or {}
    return total + sum(_count(shed.get(animal, 0)) for animal in ANIMALS)


def _state(
    obs: Any,
    future_feed: int,
    future_fertilizer: int,
    future_wheat_plants: int,
) -> dict[str, Any]:
    _seat, farm = _seat_and_farm(obs)
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    seeds = _get(private, "seeds", {}) or {}
    market = _get(obs, "market", {}) or {}
    prices = _get(market, "prices", {}) or {}
    day = _count(_get(obs, "day", 0))
    capacity = _count(_get(market, "shedCapacity", 100)) or 100
    storage = sum(_count(value) for value in shed.values())
    animals = _animal_count(farm, private)
    return {
        "day": day,
        "cash": float(_get(farm, "money", 0) or 0),
        "shed": {str(item): _count(value) for item, value in shed.items()},
        "seeds": {str(item): _count(value) for item, value in seeds.items()},
        "prices": {str(item): float(value or 0) for item, value in prices.items()},
        "capacity": capacity,
        "storage": storage,
        "animals": animals,
        "future_feed": max(0, int(future_feed)),
        "future_fertilizer": max(0, int(future_fertilizer)),
        "future_wheat_plants": max(0, int(future_wheat_plants)),
    }


def _crop_score(item: str, prices: Mapping[str, Any]) -> float:
    price = float(prices.get(item, 0) or 0)
    return price / GROWTH_DAYS[item]


def preferred_optional_crop(state: Mapping[str, Any]) -> str | None:
    """Return one bounded crop opportunity, or ``None`` when none is clear."""
    prices = state["prices"]
    wheat_price = float(prices.get("WHEAT", 0) or 0)
    if wheat_price <= 0:
        return None

    # The recorded strong opponent repeatedly used CARROT when its price was
    # materially above WHEAT.  Do not generalise that evidence to long-cycle
    # crops: a one-step price snapshot is not enough to justify their larger
    # seed, fertilizer, and storage exposure.
    best = "CARROT"
    carrot_price = float(prices.get(best, 0) or 0)
    if carrot_price < 60 or carrot_price < wheat_price * 1.35:
        return None
    return best


def _market_order_kind(order: Any, kind: str, item: str | None = None) -> bool:
    return (
        isinstance(order, list)
        and len(order) >= 2
        and order[0] == kind
        and (item is None or order[1] == item)
    )


def _replace_one_optional_wheat_purchase(
    market: list[list[Any]], state: Mapping[str, Any], crop: str | None, config: EconomicPolicyConfig
) -> bool:
    if crop is None or state["cash"] < config.minimum_cash:
        return False
    if state["storage"] >= config.shed_pressure_limit:
        return False
    if state["seeds"].get(crop, 0) > 0:
        return False
    if _market_order_kind(next((o for o in market if _market_order_kind(o, "BUY_SEED", crop)), None), "BUY_SEED", crop):
        return False

    # Future tape purchases replenish WHEAT during the horizon.  Reserving
    # the entire multi-day FEED count here incorrectly treats those purchases
    # as unavailable and disables every crop switch.  Keep one immediate
    # feeding day plus the current replacement quantity instead.
    reserve = max(1, state["animals"])
    wheat = state["shed"].get("WHEAT", 0)
    # Keep the market order count and index unchanged.  Market matching is
    # index-sensitive: inserting a new order or shifting later orders changes
    # the opponent interaction even when the requested quantities are equal.
    # Therefore an optional WHEAT purchase is replaced in-place as one whole
    # decision slot.  This policy never partially edits a product order.
    for index, order in enumerate(market):
        if not _market_order_kind(order, "BUY_PRODUCT", "WHEAT") or len(order) < 3:
            continue
        if state["future_wheat_plants"] <= 0:
            return False
        try:
            quantity = _count(order[2])
        except (TypeError, ValueError):
            return False
        if quantity not in (1, 2) or wheat < reserve + quantity:
            return False
        market[index] = ["BUY_SEED", crop, config.max_new_seed_units]
        return True
    return False


def _rewrite_one_plant(action: dict[str, Any], state: Mapping[str, Any], crop: str | None, config: EconomicPolicyConfig) -> bool:
    if crop is None:
        return False
    if state["day"] > config.last_adaptive_day:
        return False
    for group_name in ("hands", "farmer"):
        group = action.get(group_name, [])
        groups = group if group_name == "hands" else [group]
        for operation in groups:
            if not isinstance(operation, list) or len(operation) < 2 or operation[0] != "PLANT":
                continue
            if operation[1] == crop:
                continue
            operation[1] = crop
            return True
    return False


def apply_adaptive_economy(
    obs: Any,
    action: dict[str, Any],
    future_feed: int,
    future_fertilizer: int,
    future_wheat_plants: int,
    config: EconomicPolicyConfig = EconomicPolicyConfig(),
) -> dict[str, Any]:
    """Adapt only bounded economic choices while preserving legal operations."""
    result = {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(order or ["PASS"]) for order in action.get("hands", []) or []],
        "market": [list(order) for order in action.get("market", []) or []],
    }
    if not config.enabled:
        return result
    state = _state(obs, future_feed, future_fertilizer, future_wheat_plants)
    if not (config.first_adaptive_day <= state["day"] <= config.last_adaptive_day):
        return result
    crop = preferred_optional_crop(state)
    if crop is not None:
        original_hands = [list(operation) for operation in result["hands"]]
        plant_changed = _rewrite_one_plant(result, state, crop, config)
        if plant_changed and state["seeds"].get(crop, 0) <= 0:
            # Buying a seed without a corresponding plant slot is pure risk.
            # Treat the market purchase and plant rewrite as one atomic
            # bounded decision; on failure retain the original action.
            if not _replace_one_optional_wheat_purchase(result["market"], state, crop, config):
                result["hands"] = original_hands
        elif not plant_changed and state["seeds"].get(crop, 0) <= 0:
            # Purchasing and planting are separate turns in the SDK.  Allow a
            # single funded seed purchase to precede the future tape slot.
            _replace_one_optional_wheat_purchase(result["market"], state, crop, config)
    return result
