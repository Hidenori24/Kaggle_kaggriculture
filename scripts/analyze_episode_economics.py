"""Summarize economic state and action pressure in one Kaggriculture replay.

The replay path is supplied at runtime, so private competition data stays out
of the repository.  This tool is intentionally descriptive: it does not
change the agent or infer a leaderboard score from one episode.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any


def _count_animals(farm: dict[str, Any], private: dict[str, Any]) -> int:
    count = 0
    for row in farm.get("tiles", []) or []:
        for tile in row if isinstance(row, list) else []:
            if isinstance(tile, dict) and tile.get("animal"):
                count += 1
    for item in ("COW", "SHEEP", "GOOSE"):
        count += int((private.get("shed", {}) or {}).get(item, 0) or 0)
    return count


def _state(record: dict[str, Any]) -> dict[str, Any]:
    obs = record["observation"]
    private = obs.get("private", {}) or {}
    farms = obs.get("farms", []) or []
    player = int(obs.get("player", 0) or 0)
    farm = farms[player] if player < len(farms) else {}
    shed = private.get("shed", {}) or {}
    crops = collections.Counter()
    for row in farm.get("tiles", []) or []:
        for tile in row if isinstance(row, list) else []:
            if isinstance(tile, dict) and tile.get("crop"):
                crops[str(tile["crop"])] += 1
    prices = (obs.get("market", {}) or {}).get("prices", {}) or {}
    return {
        "day": int(obs.get("day", 0) or 0),
        "money": int(farm.get("money", 0) or 0),
        "shed": sum(int(value or 0) for value in shed.values()),
        "wheat": int(shed.get("WHEAT", 0) or 0),
        "animals": _count_animals(farm, private),
        "quadrants": len(farm.get("unlocked_quadrants", []) or []),
        "crops": dict(sorted(crops.items())),
        "wheat_price": int(prices.get("WHEAT", 0) or 0),
        "melon_price": int(prices.get("MELON", 0) or 0),
        "reward": record.get("reward"),
    }


def _action_counts(records: list[dict[str, Any]]) -> tuple[collections.Counter, collections.Counter]:
    operations: collections.Counter = collections.Counter()
    market: collections.Counter = collections.Counter()
    for record in records:
        action = record.get("action", {}) or {}
        for operation in [action.get("farmer", [])] + list(action.get("hands", []) or []):
            if operation:
                operations[operation[0]] += 1
        for order in action.get("market", []) or []:
            if len(order) >= 2:
                market[(order[0], order[1])] += 1
    return operations, market


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode", type=Path)
    parser.add_argument("--agent", required=True)
    args = parser.parse_args()
    episode = json.loads(args.episode.read_text(encoding="utf-8"))
    names = [entry.get("Name", "") for entry in episode.get("info", {}).get("Agents", [])]
    if args.agent not in names:
        raise SystemExit(f"agent not found: {args.agent!r}; available={names!r}")
    seat = names.index(args.agent)
    records = [step[seat] for step in episode["steps"]]
    opponent_seat = 1 - seat
    opponent_records = [step[opponent_seat] for step in episode["steps"]]

    by_day: dict[int, tuple[dict[str, Any], dict[str, Any]]] = {}
    for record, opponent_record in zip(records, opponent_records):
        if int(record["observation"].get("hour", -1)) == 0:
            day = int(record["observation"].get("day", 0) or 0)
            by_day[day] = (_state(record), _state(opponent_record))

    print(f"episode={episode.get('info', {}).get('EpisodeId')} seat={seat} agent={args.agent}")
    print(f"opponent={names[opponent_seat]} final={records[-1].get('reward')} vs {opponent_records[-1].get('reward')}")
    print("day | money mine/theirs | shed mine/theirs | animals | quadrants | wheat price | melon price")
    for day, (mine, theirs) in sorted(by_day.items()):
        print(
            f"{day:>3} | {mine['money']:>5}/{theirs['money']:<5} "
            f"| {mine['shed']:>3}/{theirs['shed']:<3} "
            f"| {mine['animals']:>2}/{theirs['animals']:<2} "
            f"| {mine['quadrants']:>2}/{theirs['quadrants']:<2} "
            f"| {mine['wheat_price']:>3} "
            f"| {mine['melon_price']:>3}"
        )

    mine_ops, mine_market = _action_counts(records)
    theirs_ops, theirs_market = _action_counts(opponent_records)
    print(f"mine_operations={dict(mine_ops)}")
    print(f"opponent_operations={dict(theirs_ops)}")
    print(f"mine_market={dict(mine_market)}")
    print(f"opponent_market={dict(theirs_market)}")
    print(f"mine_final_crops={by_day[max(by_day)][0]['crops']}")
    print(f"opponent_final_crops={by_day[max(by_day)][1]['crops']}")


if __name__ == "__main__":
    main()
