"""Read-only diagnostics for comparing a replay with the logistics policy.

The shadow policy is deliberately not used as the Kaggle entry point.  It
answers a narrower question: when the proven replay is running, what would
the state-aware policy try to do, and where do the two plans disagree?  This
keeps experiments observable without risking the stable submission line.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .full_strategy import choose_action as choose_logistics_action


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _farm(obs: Any) -> dict[str, Any]:
    farms = _value(obs, "farms", []) or []
    player = int(_value(obs, "player", 0) or 0)
    return farms[player] if 0 <= player < len(farms) else {}


def _private(obs: Any) -> dict[str, Any]:
    return _value(obs, "private", {}) or {}


def _quantity_map(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int] = {}
    for key, raw in value.items():
        try:
            result[str(key)] = int(raw or 0)
        except (TypeError, ValueError):
            continue
    return result


def _action_signature(action: Any) -> tuple[Any, ...]:
    action = action or {}
    farmer = tuple(_value(action, "farmer", []) or [])
    hands = tuple(tuple(order or []) for order in (_value(action, "hands", []) or []))
    market = tuple(tuple(order or []) for order in (_value(action, "market", []) or []))
    return farmer, hands, market


def _action_counts(action: Any) -> dict[str, int]:
    counts: Counter[str] = Counter()
    action = action or {}
    units = [_value(action, "farmer", []) or []]
    units.extend(_value(action, "hands", []) or [])
    for order in units:
        if order:
            counts[str(order[0])] += 1
    for order in _value(action, "market", []) or []:
        if order:
            counts[f"MARKET:{order[0]}"] += 1
    return dict(sorted(counts.items()))


def _tile_metrics(farm: Any) -> dict[str, int]:
    metrics: Counter[str] = Counter()
    for row in _value(farm, "tiles", []) or []:
        for tile in row or []:
            if not isinstance(tile, dict):
                continue
            kind = str(tile.get("kind", "UNKNOWN"))
            metrics[f"tiles:{kind}"] += 1
            if kind == "PLANT":
                if tile.get("yield_units", 0):
                    metrics["plants:ready"] += 1
                if not tile.get("watered_today", False):
                    metrics["plants:need_water"] += 1
            if "animal" in tile:
                metrics["animals:live"] += 1
                if not tile.get("fed_today", False):
                    metrics["animals:need_feed"] += 1
                if not tile.get("cared_today", False):
                    metrics["animals:need_care"] += 1
                if tile.get("fertilizer_available", False):
                    metrics["animals:fertilizer_ready"] += 1
    return dict(sorted(metrics.items()))


def diagnose_step(obs: Any, actual_action: Any | None = None) -> dict[str, Any]:
    """Return JSON-serializable state and shadow-policy diagnostics."""

    farm = _farm(obs)
    private = _private(obs)
    actual = actual_action or {}
    try:
        shadow = choose_logistics_action(obs)
        shadow_error = None
    except Exception as exc:  # Diagnostics must never stop a replay run.
        shadow = {"farmer": ["PASS"], "hands": [], "market": []}
        shadow_error = f"{type(exc).__name__}: {exc}"

    inventories = _value(private, "inventories", []) or []
    inventory_total = sum(sum(_quantity_map(inventory).values()) for inventory in inventories)
    shed = _quantity_map(_value(private, "shed", {}))
    tile_metrics = _tile_metrics(farm)
    actual_counts = _action_counts(actual)
    bottlenecks = []
    if tile_metrics.get("plants:ready", 0) and not actual_counts.get("HARVEST", 0):
        bottlenecks.append("harvest_backlog")
    if tile_metrics.get("plants:need_water", 0) and not actual_counts.get("WATER", 0):
        bottlenecks.append("watering_backlog")
    if tile_metrics.get("animals:need_feed", 0) and not actual_counts.get("FEED", 0):
        bottlenecks.append("feed_backlog")
    if tile_metrics.get("animals:need_care", 0) and not actual_counts.get("CARE", 0):
        bottlenecks.append("care_backlog")
    if tile_metrics.get("animals:fertilizer_ready", 0) and not actual_counts.get("COLLECT_FERTILIZER", 0):
        bottlenecks.append("fertilizer_backlog")
    if inventory_total:
        bottlenecks.append("carrying_inventory")
    return {
        "step": int(_value(obs, "step", 0) or 0),
        "day": int(_value(obs, "day", 0) or 0),
        "hour": int(_value(obs, "hour", 0) or 0),
        "money": float(_value(farm, "money", 0) or 0),
        "hands": len(_value(farm, "hands", []) or []),
        "hires_today": int(_value(farm, "hires_today", 0) or 0),
        "unlocked_quadrants": list(_value(farm, "unlocked_quadrants", []) or []),
        "shed_total": sum(shed.values()),
        "shed": shed,
        "inventory_total": inventory_total,
        "tile_metrics": tile_metrics,
        "actual_counts": actual_counts,
        "shadow_counts": _action_counts(shadow),
        "action_differs": _action_signature(actual) != _action_signature(shadow),
        "bottlenecks": bottlenecks,
        "shadow_error": shadow_error,
    }


def summarize_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate diagnostics by phase without interpreting the score."""

    if not rows:
        return {"steps": 0, "different_steps": 0, "phase_summary": []}
    phases: dict[str, list[dict[str, Any]]] = {"early": [], "growth": [], "late": []}
    for row in rows:
        phase = "early" if row["day"] < 10 else "growth" if row["day"] < 22 else "late"
        phases[phase].append(row)
    phase_summary = []
    for name, phase_rows in phases.items():
        if not phase_rows:
            continue
        phase_summary.append(
            {
                "phase": name,
                "steps": len(phase_rows),
                "different_steps": sum(row["action_differs"] for row in phase_rows),
                "money_start": phase_rows[0]["money"],
                "money_end": phase_rows[-1]["money"],
                "max_inventory_total": max(row["inventory_total"] for row in phase_rows),
                "max_shed_total": max(row["shed_total"] for row in phase_rows),
                "max_hands": max(row["hands"] for row in phase_rows),
                "quadrants_seen": sorted(
                    {q for row in phase_rows for q in row["unlocked_quadrants"]}
                ),
                "actual_action_counts": _sum_counts(phase_rows, "actual_counts"),
                "shadow_action_counts": _sum_counts(phase_rows, "shadow_counts"),
                "bottleneck_steps": sum(bool(row["bottlenecks"]) for row in phase_rows),
                "bottleneck_counts": _sum_bottlenecks(phase_rows),
            }
        )
    return {
        "steps": len(rows),
        "different_steps": sum(row["action_differs"] for row in rows),
        "shadow_errors": sum(row["shadow_error"] is not None for row in rows),
        "phase_summary": phase_summary,
    }


def _sum_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(row.get(key, {}))
    return dict(sorted(counts.items()))


def _sum_bottlenecks(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(row.get("bottlenecks", []))
    return dict(sorted(counts.items()))
