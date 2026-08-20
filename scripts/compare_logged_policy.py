"""Compare a policy's decisions with one seat in a recorded episode.

The episode path is supplied at runtime so private competition replays never
become repository data.  This is an analysis tool, not a submission path.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaggriculture_agent.replay_policy import (  # noqa: E402
    _future_input_demand,
    _future_tape_counts,
    _step,
    agent,
)
from kaggriculture_agent.adaptive_economy import _state, preferred_optional_crop  # noqa: E402


def _operation_counts(actions: list[dict]) -> Counter:
    return Counter(
        operation[0]
        for action in actions
        for operation in [action.get("farmer", [])] + list(action.get("hands", []) or [])
        if operation
    )


def _market_counts(actions: list[dict]) -> Counter:
    return Counter(
        (order[0], order[1])
        for action in actions
        for order in action.get("market", []) or []
        if len(order) >= 2
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode", type=Path)
    parser.add_argument("--agent", default="N_Matsumoto24")
    args = parser.parse_args()

    episode = json.loads(args.episode.read_text(encoding="utf-8"))
    agents = episode.get("info", {}).get("Agents", [])
    names = [entry.get("Name", "") for entry in agents]
    if args.agent not in names:
        raise SystemExit(f"agent not found: {args.agent!r}; available={names!r}")
    seat = names.index(args.agent)
    records = [step[seat] for step in episode["steps"]]
    recorded = [record.get("action", {}) for record in records]
    proposed = [agent(record.get("observation", {})) for record in records]
    opportunities = []
    purchase_opportunities = []
    purchase_state = []
    for index, record in enumerate(records):
        prices = (record.get("observation", {}).get("market", {}) or {}).get("prices", {}) or {}
        carrot = float(prices.get("CARROT", 0) or 0)
        wheat = float(prices.get("WHEAT", 0) or 0)
        if carrot >= 60 and wheat > 0 and carrot >= 1.35 * wheat:
            opportunities.append((index // 24, index % 24, int(carrot), int(wheat)))
            if any(
                len(order) >= 3
                and order[0] == "BUY_PRODUCT"
                and order[1] == "WHEAT"
                and int(order[2]) == 1
                for order in record.get("action", {}).get("market", []) or []
            ):
                purchase_opportunities.append((index // 24, index % 24, int(carrot), int(wheat)))
                state = _state(record.get("observation", {}), 0, 0, 0)
                step = _step(record.get("observation", {}))
                net_feed, net_fertilizer = _future_input_demand(
                    step,
                    end_step=min(719, step + 6 * 24),
                    net_purchases=True,
                )
                purchase_state.append({
                    "day": index // 24,
                    "hour": index % 24,
                    "cash": state["cash"],
                    "storage": state["storage"],
                    "wheat": state["shed"].get("WHEAT", 0),
                    "animals": state["animals"],
                    "seeds": state["seeds"],
                    "preferred": preferred_optional_crop(state),
                    "step": step,
                    "net_feed": net_feed,
                    "future_wheat_plants": _future_tape_counts(
                        step, min(719, step + 12 * 24)
                    )["PLANT_WHEAT"],
                })
    print(f"seat={seat} steps={len(records)} action_differences="
          f"{sum(left != right for left, right in zip(recorded, proposed))}")
    print(f"recorded_operations={dict(_operation_counts(recorded))}")
    print(f"proposed_operations={dict(_operation_counts(proposed))}")
    print(f"recorded_market={dict(_market_counts(recorded))}")
    print(f"proposed_market={dict(_market_counts(proposed))}")
    print(f"carrot_opportunities={opportunities[:40]}")
    print(f"carrot_purchase_opportunities={purchase_opportunities[:40]}")
    print(f"carrot_purchase_state={purchase_state[:40]}")


if __name__ == "__main__":
    main()
