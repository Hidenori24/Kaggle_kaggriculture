from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaggle_environments import make  # noqa: E402

import kaggriculture_agent.replay_policy as replay_policy  # noqa: E402
from kaggriculture_agent.full_strategy import choose_action as full_strategy  # noqa: E402
from kaggriculture_agent.strategy import (  # noqa: E402
    BaselineConfig,
    choose_action as baseline,
)


def pass_agent(obs: Any) -> dict[str, Any]:
    farms = obs.get("farms", []) if isinstance(obs, dict) else []
    player = int(obs.get("player", 0) or 0) if isinstance(obs, dict) else 0
    farm = farms[player] if player < len(farms) else {}
    hands = farm.get("hands", []) if isinstance(farm, dict) else []
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in hands], "market": []}


def raw_replay(obs: Any) -> dict[str, Any]:
    step = max(0, min(int(obs.get("step", 0) or 0), len(replay_policy._ACTIONS) - 1))
    action = copy.deepcopy(replay_policy._ACTIONS[step] or {})
    farms = obs.get("farms", []) or []
    player = int(obs.get("player", 0) or 0)
    farm = farms[player] if player < len(farms) else {}
    expected = len(farm.get("hands", []) or [])
    hands = list(action.get("hands", []) or [])
    hands.extend([["PASS"] for _ in range(max(0, expected - len(hands)))])
    action["hands"] = hands[:expected]
    action.setdefault("farmer", ["PASS"])
    action.setdefault("market", [])
    return action


def policies() -> dict[str, Callable[[Any], dict[str, Any]]]:
    return {
        "old-baseline": lambda obs: baseline(obs, BaselineConfig(enable_expansion=False)),
        "expanded-baseline": lambda obs: baseline(obs, BaselineConfig(enable_expansion=True)),
        "full-strategy": full_strategy,
        "raw-replay": raw_replay,
        "replay-base": replay_policy._base_agent,
        "replay-shadow-market": replay_policy.agent,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare historical Kaggriculture policies.")
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--opponent", choices=("pass", "random"), default="pass")
    args = parser.parse_args()
    opponent = pass_agent if args.opponent == "pass" else "random"
    results = []
    for name, policy in policies().items():
        scores = []
        for seed in range(args.episodes):
            if args.opponent == "random":
                random.seed(10_000 + seed)
            env = make("kaggriculture", configuration={"seed": seed})
            env.run([policy, opponent])
            scores.append(float(env.steps[-1][0].reward or 0))
        results.append(
            {
                "policy": name,
                "scores": scores,
                "mean": sum(scores) / len(scores) if scores else 0.0,
                "minimum": min(scores) if scores else 0.0,
            }
        )
    print(json.dumps({"opponent": args.opponent, "episodes": args.episodes, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
