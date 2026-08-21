"""Compare several git revisions against one reference in one environment load.

This is an exploratory tool, not a leaderboard predictor.  It is useful for
finding regressions introduced by market overlays without paying the import
startup cost once per revision.
"""

from __future__ import annotations

import argparse
import statistics
import sys

from kaggle_environments import make

from head_to_head import load_reference


def _match(candidate, reference, seed: int, seat: int) -> tuple[float, float]:
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run([candidate, reference] if seat == 0 else [reference, candidate])
    rewards = [state["reward"] for state in env.steps[-1]]
    return rewards[seat], rewards[1 - seat]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refs",
        nargs="+",
        default=["286d730d9fbf", "d5be9a5", "f6c0638", "27e00c1", "76ebc2b", "532225e", "cc2ca51", "HEAD"],
    )
    parser.add_argument("--reference", default="HEAD")
    parser.add_argument("--seeds", type=int, default=1)
    args = parser.parse_args()
    reference = load_reference(args.reference).agent
    print(f"reference = {args.reference}")
    print(f"{'candidate':<14} {'wins':>5} {'matches':>7} {'mean margin':>13}")
    for ref in args.refs:
        candidate = load_reference(ref).agent
        wins = 0
        margins = []
        for seed in range(1, args.seeds + 1):
            for seat in (0, 1):
                mine, theirs = _match(candidate, reference, seed, seat)
                margins.append((mine - theirs) / max(abs(theirs), 1) * 100)
                wins += mine > theirs
        print(f"{ref:<14} {wins:>5} {len(margins):>7} {statistics.mean(margins):>+12.2f}%")


if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    main()
