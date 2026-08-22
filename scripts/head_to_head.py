"""Gate a change by playing it against a reference version of itself.

This exists because `benchmark.py` was caught being wrong in the direction
that matters.  Its opponents are recorded tapes, and a recorded tape replayed
against a different policy plays weakly and, crucially, *does not contest the
market*.  Any change that raises our own production or sales therefore looks
good there: the extra goods sell into an uncontested market and the winning
margin grows.

The idle-work + feed-reserve candidate measured +1.99% on that benchmark and
then lost 24 out of 24 head-to-head matches against the very version it was
meant to improve, by a mean of -10.7%.  Against a peer that sells into the
same market, the extra harvest crushes the price of our own goods and the
reserve holds back WHEAT that could have been sold.

So: benchmark.py answers "how big is the win when we already win", which is
not the question. The ladder sits at a rating where matches are close and
both sides compete for the same buyers. This script reproduces that regime by
playing the working tree's policy against a reference revision, both seats,
across many seeds.

Neither harness is the ladder. But a change that cannot beat its own
predecessor here has no business being submitted.

Usage:
    python scripts/head_to_head.py                    # vs origin/main
    python scripts/head_to_head.py --ref HEAD~1 --seeds 20
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

POLICY = "src/kaggriculture_agent/replay_policy.py"


def load_reference(ref):
    """Import the policy module as it exists at a git revision."""
    blob = subprocess.run(
        ["git", "show", f"{ref}:{POLICY}"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    tmp = Path(tempfile.mkdtemp()) / "reference_policy.py"
    # The submission branch's copy imports a sibling module; the agent path
    # does not need it, so drop the import rather than vendoring the package.
    tmp.write_text(
        blob
        .replace(
            "from .economic_shadow import forecast_economy",
            "from kaggriculture_agent.economic_shadow import forecast_economy",
        )
        .replace(
            "from .adaptive_economy import apply_adaptive_economy",
            "from kaggriculture_agent.adaptive_economy import apply_adaptive_economy",
        )
    )
    spec = importlib.util.spec_from_file_location("reference_policy", tmp)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="origin/main", help="reference git revision")
    parser.add_argument(
        "--candidate-ref",
        help="load the candidate policy from this git revision instead of the working tree",
    )
    parser.add_argument(
        "--policy", choices=("replay", "legacy", "crop-mix", "carrot-mix", "carrot-lane", "stateful", "macro", "local", "late", "resync", "pressure", "wheat-budget", "redundant-feed", "daily-economic", "input-budget", "urgent-jobs", "strawberry-mix", "replanned", "replanned-logistics", "job-queue", "strawberry-all-mix"), default="replay",
        help="working-tree challenger policy; includes the experimental replanned policies",
    )
    parser.add_argument("--seeds", type=int, default=12)
    args = parser.parse_args()

    if args.policy == "legacy":
        from kaggriculture_agent.legacy_replay_policy import agent as candidate
    elif args.policy == "crop-mix":
        from kaggriculture_agent.crop_mix_policy import agent as candidate
    elif args.policy == "carrot-mix":
        from kaggriculture_agent.carrot_mix_policy import agent as candidate
    elif args.policy == "carrot-lane":
        from kaggriculture_agent.carrot_lane_policy import agent as candidate
    elif args.policy == "stateful":
        from kaggriculture_agent.stateful_policy import agent as candidate
    elif args.policy == "macro":
        from kaggriculture_agent.macro_transport import agent as candidate
    elif args.policy == "local":
        from kaggriculture_agent.local_jobs_policy import agent as candidate
    elif args.policy == "late":
        from kaggriculture_agent.late_harvest_policy import agent as candidate
    elif args.policy == "resync":
        from kaggriculture_agent.resync_policy import agent as candidate
    elif args.policy == "pressure":
        from kaggriculture_agent.pressure_order_policy import agent as candidate
    elif args.policy == "wheat-budget":
        from kaggriculture_agent.wheat_budget_policy import agent as candidate
    elif args.policy == "redundant-feed":
        from kaggriculture_agent.redundant_feed_policy import agent as candidate
    elif args.policy == "daily-economic":
        from kaggriculture_agent.daily_economic_policy import agent as candidate
    elif args.policy == "input-budget":
        from kaggriculture_agent.input_budget_policy import agent as candidate
    elif args.policy == "urgent-jobs":
        from kaggriculture_agent.urgent_jobs_policy import agent as candidate
    elif args.policy == "strawberry-mix":
        from kaggriculture_agent.strawberry_mix_policy import agent as candidate
    elif args.policy == "replanned":
        from kaggriculture_agent.replanned_strategy import choose_action as candidate
    elif args.policy == "replanned-logistics":
        from kaggriculture_agent.replanned_logistics_strategy import choose_action as candidate
    elif args.policy == "job-queue":
        from kaggriculture_agent.job_queue_strategy import choose_action as candidate
    elif args.policy == "strawberry-all-mix":
        from kaggriculture_agent.strawberry_all_mix_policy import agent as candidate
    else:
        from kaggriculture_agent.replay_policy import agent as candidate
    reference = load_reference(args.ref).agent
    if args.candidate_ref:
        candidate = load_reference(args.candidate_ref).agent

    seeds = list(range(1, args.seeds + 1))
    wins = losses = 0
    margins = []
    print(f"candidate = working tree, reference = {args.ref}")
    print(f"{'seed':>6} {'cand seat':>9} {'candidate':>11} {'reference':>11} {'margin':>8}  winner")
    for seed in seeds:
        for seat in (0, 1):
            env = make("kaggriculture", configuration={"seed": seed}, debug=False)
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
    if wins <= losses:
        print("\nVERDICT: does not beat its own predecessor -- do not submit.")
    else:
        print("\nVERDICT: beats its predecessor here; still not a ladder guarantee.")


if __name__ == "__main__":
    main()
