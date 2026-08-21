"""Compare historical policy revisions against the same recorded opponents.

This is an exploratory diagnostic.  It keeps the opponent tapes and seeds
fixed, so differences between revisions are attributable to the policy code,
not to a new opponent draw.  It is not a leaderboard predictor.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark import load_opponents, make_tape_agent  # noqa: E402
from head_to_head import load_reference  # noqa: E402
from kaggle_environments import make  # noqa: E402


def _match(policy, opponent: dict, seat: int) -> tuple[float, float]:
    env = make("kaggriculture", configuration={"seed": opponent["seed"]}, debug=False)
    tape = make_tape_agent(opponent["tape"])
    env.run([policy, tape] if seat == 0 else [tape, policy])
    final = env.steps[-1]
    return float(final[seat]["reward"] or 0), float(final[1 - seat]["reward"] or 0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refs",
        nargs="+",
        default=["286d730d9fbf", "85740a2f71b5", "2f3303525dc7", "cc2ca51"],
    )
    parser.add_argument(
        "--opponents",
        nargs="+",
        default=["X1a0Ch3n", "ali dzaki"],
    )
    args = parser.parse_args()
    opponents = load_opponents()
    unknown = sorted(set(args.opponents) - set(opponents))
    if unknown:
        raise SystemExit(f"unknown opponents: {unknown}; have {sorted(opponents)}")

    print(f"opponents = {', '.join(args.opponents)}")
    print(f"{'ref':<14} {'wins':>5} {'matches':>7} {'mean reward':>13} {'mean margin':>13}")
    for ref in args.refs:
        policy = load_reference(ref).agent
        rewards = []
        margins = []
        wins = 0
        for name in args.opponents:
            for seat in (0, 1):
                mine, theirs = _match(policy, opponents[name], seat)
                rewards.append(mine)
                margins.append((mine - theirs) / max(abs(theirs), 1) * 100)
                wins += mine > theirs
        print(
            f"{ref:<14} {wins:>5} {len(rewards):>7} "
            f"{statistics.mean(rewards):>13,.1f} {statistics.mean(margins):>+12.2f}%"
        )


if __name__ == "__main__":
    main()
