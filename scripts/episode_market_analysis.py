"""Inspect market timing differences in a Kaggriculture episode JSON."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _sell_totals(action: dict[str, Any]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for order in action.get("market", []) or []:
        if len(order) >= 3 and order[0] == "SELL":
            totals[str(order[1])] += max(0, int(order[2]))
    return dict(totals)


def _shed(observation: dict[str, Any]) -> dict[str, int]:
    private = observation.get("private", {}) or {}
    return {str(item): max(0, int(amount)) for item, amount in (private.get("shed", {}) or {}).items()}


def analyze(path: Path) -> None:
    episode = json.loads(path.read_text(encoding="utf-8"))
    steps = episode["steps"]
    print(f"episode={episode.get('info', {}).get('EpisodeId')} rewards={episode.get('rewards')}")
    for seat, agent in enumerate(episode.get("info", {}).get("Agents", [])):
        operations = Counter()
        market_operations = Counter()
        order_count = 0
        sell_units = Counter()
        split_turns = 0
        day_money: dict[int, float] = {}
        for step in steps:
            record = step[seat]
            action = record.get("action", {})
            for operation in [action.get("farmer", [])] + list(action.get("hands", [])):
                if operation:
                    operations[str(operation[0])] += 1
            for operation in action.get("market", []) or []:
                if operation:
                    market_operations[str(operation[0])] += 1
            sells = _sell_totals(action)
            order_count += bool(sells)
            sell_units.update(sells)
            if len(sells) != len(
                [order for order in record.get("action", {}).get("market", []) if order and order[0] == "SELL"]
            ):
                split_turns += 1
            observation = record.get("observation", {})
            farms = observation.get("farms", [])
            if seat < len(farms):
                day_money[int(observation.get("day", 0))] = float(farms[seat].get("money", 0))
        print(
            f"seat={seat} agent={agent.get('Name')} sell_turns={order_count} "
            f"split_turns={split_turns} units={dict(sell_units)}"
        )
        print(f"operations={dict(operations)}")
        print(f"market_operations={dict(market_operations)}")
        print("day_money=" + ", ".join(f"{day}:{value:.0f}" for day, value in sorted(day_money.items())))

    shortfalls: list[tuple[int, str, int, int, int]] = []
    action_differences = 0
    for index, step in enumerate(steps):
        left = step[0]
        right = step[1]
        if left.get("action") != right.get("action"):
            action_differences += 1
        left_sells = _sell_totals(left.get("action", {}))
        right_sells = _sell_totals(right.get("action", {}))
        left_shed = _shed(left.get("observation", {}))
        right_shed = _shed(right.get("observation", {}))
        for item in sorted(set(left_sells) | set(right_sells)):
            own = left_sells.get(item, 0)
            opponent = right_sells.get(item, 0)
            if opponent > own and left_shed.get(item, 0) >= opponent:
                shortfalls.append((index, item, own, opponent, left_shed.get(item, 0)))
            if own > opponent and right_shed.get(item, 0) >= own:
                shortfalls.append((index, item, opponent, own, right_shed.get(item, 0)))
    print(f"action_differences={action_differences}")
    print("same-step inventory-supported shortfalls:")
    for row in shortfalls[:40]:
        print("  step=%d item=%s lower=%d higher=%d available=%d" % row)
    print(f"shortfall_count={len(shortfalls)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode", type=Path)
    args = parser.parse_args()
    analyze(args.episode)


if __name__ == "__main__":
    main()
