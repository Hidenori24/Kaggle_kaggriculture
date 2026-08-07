"""Deterministic, read-only economic lookahead for shadow evaluation.

This module deliberately does not choose actions.  It estimates the value that
is already available in cash, storage, inventory, and ready crops at several
horizons.  The production agent may call it in shadow mode; its return value
must never affect the returned action until a separate experiment enables an
explicit policy gate.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence


_DEFAULT_HORIZONS = (24, 48, 72)
_DEFAULT_CAPACITY = 100


def _get(value, key, default=None):
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _as_count(value) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _seat_and_farm(obs):
    seat = 1 if _as_count(_get(obs, "player", 0)) == 1 else 0
    farms = _get(obs, "farms", []) or []
    if isinstance(farms, Sequence) and not isinstance(farms, (str, bytes)) and seat < len(farms):
        return seat, farms[seat]
    return seat, {}


def _tiles(farm):
    for row in _get(farm, "tiles", []) or []:
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
            continue
        for tile in row:
            if isinstance(tile, Mapping):
                yield tile


def _inventory_totals(private):
    totals = {}
    for inventory in _get(private, "inventories", []) or []:
        if not isinstance(inventory, Mapping):
            continue
        for item, amount in inventory.items():
            totals[item] = totals.get(item, 0) + _as_count(amount)
    return totals


def _observation_step(obs) -> int:
    value = _get(obs, "step", None)
    if value is not None:
        return _as_count(value)
    day = _as_count(_get(obs, "day", 0))
    hour = _as_count(_get(obs, "hour", 0))
    return day * 24 + hour


def forecast_economy(obs, horizons: Sequence[int] = _DEFAULT_HORIZONS) -> dict:
    """Return conservative economic forecasts without mutating ``obs``.

    The estimate intentionally values only resources visible in the current
    observation.  Ready crops are treated as harvestable value; immature crops
    are not guessed.  For longer horizons, the visible value is discounted and
    a small carrying-cost reserve is deducted.  This is a diagnostic baseline,
    not yet an action policy.
    """
    _seat, farm = _seat_and_farm(obs)
    private = _get(obs, "private", {}) or {}
    market = _get(obs, "market", {}) or {}
    prices = _get(market, "prices", {}) or {}
    shed = {item: _as_count(amount) for item, amount in dict(_get(private, "shed", {}) or {}).items()}
    inventory = _inventory_totals(private)
    visible_stock = dict(shed)
    for item, amount in inventory.items():
        visible_stock[item] = visible_stock.get(item, 0) + amount

    ready_units = {}
    for tile in _tiles(farm):
        if tile.get("kind") != "PLANT":
            continue
        units = _as_count(tile.get("yield_units", 0))
        crop = tile.get("crop")
        if crop and units:
            ready_units[crop] = ready_units.get(crop, 0) + units

    def price(item) -> float:
        try:
            return max(0.0, float(prices.get(item, 0) or 0))
        except (TypeError, ValueError):
            return 0.0

    stock_value = sum(amount * price(item) for item, amount in visible_stock.items())
    ready_value = sum(amount * price(item) for item, amount in ready_units.items())
    money = float(_get(farm, "money", 0) or 0)
    capacity = _as_count(_get(market, "shedCapacity", _DEFAULT_CAPACITY)) or _DEFAULT_CAPACITY
    storage_load = sum(shed.values())
    capacity_pressure = max(0, storage_load - capacity)
    current_step = _observation_step(obs)

    forecast = {}
    for raw_horizon in horizons:
        horizon = max(0, _as_count(raw_horizon))
        days = horizon / 24.0
        discount = max(0.80, 1.0 - 0.02 * days)
        reserve = max(0.0, days * 10.0)
        forecast[horizon] = {
            "liquidation_value": round(stock_value, 3),
            "ready_harvest_value": round(ready_value, 3),
            "cash_plus_visible_value": round(money + stock_value, 3),
            "conservative_wait_value": round(money + stock_value * discount - reserve, 3),
            "capacity_pressure": capacity_pressure,
            "storage_load": storage_load,
            "storage_capacity": capacity,
            "ready_units": dict(sorted(ready_units.items())),
        }

    return {
        "step": current_step,
        "horizons": forecast,
        "visible_stock": dict(sorted(visible_stock.items())),
        "prices_available": len(prices),
    }
