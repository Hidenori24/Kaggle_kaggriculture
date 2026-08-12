"""Self-play evaluation for market-side changes.

`simulate.py` plays against `random`, which never depresses market prices.
Any change gated on price (a SELL floor, a hold-back rule, a market-timing
tweak) is therefore invisible to it -- the gate simply never fires, and the
run looks identical before and after the change.

Self-play puts two copies of the policy in the same market, which is the
condition that actually moves prices: FERTILIZER 100 -> ~30, MILK 160 -> ~26,
MELON 250 -> ~106 by the final day.  It also reports shed occupancy and
animal count per day, because the shed is a shared 100-unit resource -- once
it is pinned full, feed WHEAT can no longer be deposited and animals starve.

Caveat: self-play still under-reproduces the real ladder.  Live Kaggriculture
matches drive MELON to ~4 and WOOL to ~1, far below anything seen here, so a
change that looks neutral or favourable in self-play can still regress in
live play.  Treat a self-play win as necessary, not sufficient.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kaggle_environments import make  # noqa: E402

from kaggriculture_agent.replay_policy import agent  # noqa: E402


def _daily_trace(env, seat):
    """Shed occupancy and animal count at the start of each day."""
    trace = []
    for step in env.steps:
        observation = step[0]["observation"]
        if observation["hour"] != 0:
            continue
        farm = observation["farms"][seat]
        animals = sum(
            1
            for row in farm["tiles"]
            for tile in row
            if isinstance(tile, dict) and tile.get("animal")
        )
        trace.append(
            {
                "day": observation["day"],
                "shed_units": sum(observation["private"]["shed"].values()),
                "animals": animals,
            }
        )
    return trace


def run_episode(seed):
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run([agent, agent])
    final = env.steps[-1]
    return {
        "seed": seed,
        "rewards": [seat["reward"] for seat in final],
        "final_prices": final[0]["observation"]["market"]["prices"],
        "seat0": _daily_trace(env, 0),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument(
        "--full-trace",
        action="store_true",
        help="emit every day instead of the shed/animal summary",
    )
    args = parser.parse_args()

    episodes = []
    for seed in range(1, args.episodes + 1):
        result = run_episode(seed)
        trace = result["seat0"]
        if not args.full_trace:
            result["seat0_peak_shed_units"] = max(row["shed_units"] for row in trace)
            result["seat0_final_animals"] = trace[-1]["animals"]
            result["seat0_min_animals_after_day10"] = min(
                (row["animals"] for row in trace if row["day"] >= 10), default=None
            )
            del result["seat0"]
        episodes.append(result)

    print(json.dumps({"episodes": episodes}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
