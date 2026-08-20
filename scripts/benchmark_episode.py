"""Run the local policy against an opponent tape extracted from a JSON log.

The JSON is read only at runtime and is never copied into the repository.
This is a controlled replay diagnostic, not a leaderboard prediction.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaggle_environments import make  # noqa: E402

from kaggriculture_agent.replay_policy import agent  # noqa: E402


def _reference_agent(ref: str):
    policy = "src/kaggriculture_agent/replay_policy.py"
    blob = subprocess.run(
        ["git", "show", f"{ref}:{policy}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    path = Path(tempfile.mkdtemp()) / "reference_policy.py"
    path.write_text(blob.replace("from .economic_shadow import forecast_economy", ""))
    spec = importlib.util.spec_from_file_location("episode_reference_policy", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


def _tape_agent(tape):
    def replay(observation, configuration=None):
        step = int(observation.get("step", 0) or 0)
        raw = tape[step] if 0 <= step < len(tape) else {}
        farms = observation.get("farms", []) or []
        seat = int(observation.get("player", 0) or 0)
        expected = len(farms[seat].get("hands", []) or []) if seat < len(farms) else 0
        hands = [list(order or ["PASS"]) for order in raw.get("hands", []) or []]
        hands = (hands + [["PASS"]] * expected)[:expected]
        return {
            "farmer": list(raw.get("farmer") or ["PASS"]),
            "hands": hands,
            "market": [list(order) for order in raw.get("market", []) or []],
        }

    return replay


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode", type=Path)
    parser.add_argument("--self", default="N_Matsumoto24")
    parser.add_argument("--our-seat", type=int, default=1, choices=(0, 1))
    parser.add_argument("--ref", help="also run a git reference policy")
    args = parser.parse_args()

    episode = json.loads(args.episode.read_text(encoding="utf-8"))
    names = [entry.get("Name", "") for entry in episode["info"]["Agents"]]
    self_seat = names.index(args.self)
    opponent_seat = 1 - self_seat
    tape = [step[opponent_seat].get("action", {}) for step in episode["steps"]]
    seed = episode["info"].get("seed")
    if seed is None:
        raise SystemExit("episode has no replay seed")

    opponent = _tape_agent(tape)
    policies = [("candidate", agent)]
    if args.ref:
        policies.append((args.ref, _reference_agent(args.ref)))
    results = []
    for label, policy in policies:
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        pair = [policy, opponent] if args.our_seat == 0 else [opponent, policy]
        env.run(pair)
        final = env.steps[-1]
        results.append({
            "policy": label,
            "our_reward": final[args.our_seat]["reward"],
            "opponent_reward": final[1 - args.our_seat]["reward"],
        })
    print(json.dumps({
        "episode": episode["info"].get("EpisodeId"),
        "source_self_seat": self_seat,
        "our_seat": args.our_seat,
        "results": results,
    }, indent=2))


if __name__ == "__main__":
    main()
