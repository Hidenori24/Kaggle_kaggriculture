"""Benchmark the policy against recorded real-ladder opponents.

Why this exists: `simulate.py` plays `random`, which never depresses market
prices, and self-play only depresses them mildly (MELON to ~106).  Real
matches drive MELON to ~4 and WOOL to ~1.  A change gated on price is
therefore unmeasurable in both of those harnesses -- that is how the price
floor in PR #10 shipped a ~900 point live regression while local scores
looked unchanged.

This harness replays the *opponent's* recorded action sequence from real
Kaggriculture matches (`benchmarks/opponents.json`), at the original seed, in
both seatings.  Because the opponent is a fixed tape and the environment is
deterministic, the result is a clean controlled A/B: run it before and after
a change and the difference in our reward is attributable to the change.

Two things it is NOT:

* Not a faithful opponent.  Their recorded actions were conditioned on the
  state they actually saw; replayed against a different policy their farm
  actions partly become invalid, so they play weaker than they really did.
* Not a leaderboard predictor.  Absolute rewards here mean little.  Compare
  our reward across candidate versions against the same tape, never against
  the reward they scored in the source match.

What it does give is a hostile market with real price collapse, plus the shed
and animal diagnostics that the earlier regressions turned on.
"""
from __future__ import annotations

import argparse
import base64
import json
import statistics
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaggle_environments import make  # noqa: E402

OPPONENTS_PATH = ROOT / "benchmarks" / "opponents.json"


def load_policy(name):
    """Load a local challenger without changing the production entry point."""
    if name == "replay":
        from kaggriculture_agent.replay_policy import agent
        return agent
    if name == "full":
        from kaggriculture_agent.full_strategy import choose_action
        return choose_action
    if name == "baseline":
        from kaggriculture_agent.strategy import BaselineConfig, choose_action
        return lambda observation: choose_action(
            observation, BaselineConfig(enable_expansion=False)
        )
    if name == "stateful":
        from kaggriculture_agent.stateful_policy import agent
        return agent
    raise ValueError(f"unknown policy: {name}")


def load_opponents(path=OPPONENTS_PATH):
    with open(path) as handle:
        raw = json.load(handle)
    opponents = {}
    for name, entry in raw.items():
        tape = json.loads(zlib.decompress(base64.b85decode(entry["actions_b85_zlib"])))
        opponents[name] = {"seed": entry["seed"], "tape": tape}
    return opponents


def make_tape_agent(tape):
    """Replay a recorded action sequence, padding hands to the live farm."""
    passes = {"farmer": ["PASS"], "hands": [], "market": []}

    def tape_agent(observation, configuration=None):
        step = observation.get("step")
        if step is None:
            step = int(observation.get("day", 0)) * 24 + int(observation.get("hour", 0))
        action = tape[step] if 0 <= step < len(tape) else passes
        if not isinstance(action, dict):
            action = passes
        seat = 1 if int(observation.get("player", 0) or 0) == 1 else 0
        farms = observation.get("farms") or []
        expected = len(farms[seat].get("hands", []) or []) if seat < len(farms) else 0
        hands = [list(order or ["PASS"]) for order in (action.get("hands") or [])]
        hands = (hands + [["PASS"]] * expected)[:expected]
        return {
            "farmer": list(action.get("farmer") or ["PASS"]),
            "hands": hands,
            "market": [list(order) for order in (action.get("market") or [])],
        }

    return tape_agent


def _diagnostics(env, seat):
    peak_shed = 0
    final_animals = 0
    min_animals_after_day10 = None
    for step in env.steps:
        # Each env step contains one observation per seat.  Using seat 0 here
        # made the reward comparison correct but reported the wrong shed and
        # animal diagnostics for every match where we played seat 1.
        observation = step[seat]["observation"]
        if observation["hour"] != 0:
            continue
        peak_shed = max(peak_shed, sum(observation["private"]["shed"].values()))
        farm = observation["farms"][seat]
        animals = sum(
            1
            for row in farm["tiles"]
            for tile in row
            if isinstance(tile, dict) and tile.get("animal")
        )
        final_animals = animals
        if observation["day"] >= 10:
            if min_animals_after_day10 is None:
                min_animals_after_day10 = animals
            else:
                min_animals_after_day10 = min(min_animals_after_day10, animals)
    return {
        "peak_shed_units": peak_shed,
        "final_animals": final_animals,
        "min_animals_after_day10": min_animals_after_day10,
    }


def run_match(opponent, our_seat, policy):
    tape_agent = make_tape_agent(opponent["tape"])
    env = make(
        "kaggriculture",
        configuration={"seed": opponent["seed"]},
        debug=False,
    )
    pair = [policy, tape_agent] if our_seat == 0 else [tape_agent, policy]
    env.run(pair)
    final = env.steps[-1]
    return {
        "our_seat": our_seat,
        "our_reward": final[our_seat]["reward"],
        "opponent_reward": final[1 - our_seat]["reward"],
        "final_prices": final[0]["observation"]["market"]["prices"],
        **_diagnostics(env, our_seat),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opponent", help="run only this recorded opponent")
    parser.add_argument(
        "--policy", choices=("replay", "full", "baseline", "stateful"), default="replay",
        help="local policy to benchmark; replay is the production default",
    )
    parser.add_argument("--json", action="store_true", help="emit raw JSON")
    args = parser.parse_args()

    opponents = load_opponents()
    if args.opponent:
        if args.opponent not in opponents:
            parser.error(f"unknown opponent; have {sorted(opponents)}")
        opponents = {args.opponent: opponents[args.opponent]}

    policy = load_policy(args.policy)
    matches = []
    for name, opponent in sorted(opponents.items()):
        for our_seat in (0, 1):
            result = run_match(opponent, our_seat, policy)
            result["opponent"] = name
            matches.append(result)

    ours = [m["our_reward"] for m in matches]
    summary = {
        "matches": matches,
        "our_mean": round(statistics.mean(ours), 1),
        "our_min": min(ours),
        "wins": sum(1 for m in matches if m["our_reward"] > m["opponent_reward"]),
        "total_matches": len(matches),
    }

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return

    print(f"{'opponent':<16} {'seat':>4} {'ours':>10} {'theirs':>10} "
          f"{'shed':>5} {'animals':>8}  low-price items")
    for m in matches:
        cheap = sorted(k for k, v in m["final_prices"].items() if v <= 10)
        print(f"{m['opponent']:<16} {m['our_seat']:>4} {m['our_reward']:>10,.0f} "
              f"{m['opponent_reward']:>10,.0f} {m['peak_shed_units']:>5} "
              f"{str(m['final_animals']) + '/' + str(m['min_animals_after_day10']):>8}"
              f"  {','.join(cheap) or '-'}")
    print(f"\nmean {summary['our_mean']:,.0f}  min {summary['our_min']:,.0f}  "
          f"wins {summary['wins']}/{summary['total_matches']}")


if __name__ == "__main__":
    main()
