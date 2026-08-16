"""Head-to-head in a market that has already collapsed.

The ladder plateau sits where matches are close, and the losses there happen
in fully collapsed markets: episode 93332940 ended with MELON at 1, WOOL at 1,
MILK at 5 and FERTILIZER at 3, while the inelastic goods went the other way --
EGG 50 -> 154, WHEAT 25 -> 54.

Neither existing harness reproduces that. `benchmark.py` replays opponent
tapes that do not contest the market at all. `head_to_head.py` puts two of our
own agents in one market, which depresses prices somewhat but never collapses
them, because two sellers are not the crowd. So a change whose whole thesis is
"this product survives a crowd" has been unmeasurable: geese and eggs score
-62% head-to-head purely because a lone opponent never crashes MILK and WOOL.

The environment takes a `marketParams` override, and price is a pure function
of that table plus inventory. Setting the fragile products' `base` low starts
the match in the state the real losses end in, without needing a crowd to
produce it. That is a caricature, not a simulation: it says nothing about how
a market gets there, only how a policy earns once it has.

Run a change here *in addition to* head_to_head.py, never instead of it. A
policy tuned for a permanently dead MILK market would be badly wrong in the
fresh markets that make up most of a match.

Usage:
    python scripts/stress_market.py --ref origin/main --seeds 8
    python scripts/stress_market.py --profile fresh     # sanity: no override
"""
from __future__ import annotations

import argparse
import importlib.util
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaggle_environments import make  # noqa: E402
from kaggle_environments.envs.kaggriculture.kaggriculture import MARKET_PARAMS  # noqa: E402

POLICY = "src/kaggriculture_agent/replay_policy.py"

# What the fragile products are worth once a crowd has finished with them,
# taken from the closing prices of episode 93332940. The robust ones keep
# their opening value; EGG and WHEAT actually appreciated there, but starting
# them high would be assuming the conclusion, so they are left alone.
COLLAPSED = {"MELON": 4, "WOOL": 2, "MILK": 5, "STRAWBERRY": 12, "FERTILIZER": 6}


def market_params(profile):
    if profile == "fresh":
        return None
    params = {item: dict(values) for item, values in MARKET_PARAMS.items()}
    for item, base in COLLAPSED.items():
        params[item]["base"] = base
    return params


def load_reference(ref):
    blob = subprocess.run(
        ["git", "show", f"{ref}:{POLICY}"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    tmp = Path(tempfile.mkdtemp()) / "reference_policy.py"
    tmp.write_text(blob.replace("from .economic_shadow import forecast_economy", ""))
    spec = importlib.util.spec_from_file_location("reference_policy", tmp)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--profile", choices=("collapsed", "fresh"), default="collapsed")
    args = parser.parse_args()

    from kaggriculture_agent.replay_policy import agent as candidate
    reference = load_reference(args.ref).agent
    params = market_params(args.profile)

    configuration = {}
    if params is not None:
        configuration["marketParams"] = params

    print(f"candidate = working tree, reference = {args.ref}, market = {args.profile}")
    if params is not None:
        print("collapsed at start: " + ", ".join(f"{k}={v}" for k, v in COLLAPSED.items()))
    print(f"{'seed':>6} {'cand seat':>9} {'candidate':>11} {'reference':>11} {'margin':>8}  winner")

    wins = losses = 0
    margins = []
    for seed in range(1, args.seeds + 1):
        for seat in (0, 1):
            env = make("kaggriculture", configuration={"seed": seed, **configuration}, debug=False)
            env.run([candidate, reference] if seat == 0 else [reference, candidate])
            rewards = [s["reward"] for s in env.steps[-1]]
            mine, theirs = rewards[seat], rewards[1 - seat]
            margin = (mine - theirs) / max(abs(theirs), 1) * 100
            margins.append(margin)
            if mine > theirs:
                wins += 1
            else:
                losses += 1
            print(f"{seed:>6} {seat:>9} {mine:>11,.0f} {theirs:>11,.0f} "
                  f"{margin:>+7.1f}%  {'candidate' if mine > theirs else 'reference'}")

    print(f"\ncandidate {wins} - {losses} reference over {len(margins)} matches")
    print(f"mean margin {statistics.mean(margins):+.2f}%   "
          f"median {statistics.median(margins):+.2f}%")


if __name__ == "__main__":
    main()
