from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaggle_environments import make  # noqa: E402

from kaggriculture_agent import kaggriculture_agent  # noqa: E402


def pass_agent(obs):
    farms = obs.get("farms", []) if isinstance(obs, dict) else []
    player = int(obs.get("player", 0) or 0) if isinstance(obs, dict) else 0
    farm = farms[player] if player < len(farms) else {}
    hands = farm.get("hands", []) if isinstance(farm, dict) else []
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in hands], "market": []}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--opponent", choices=("random", "pass"), default="random")
    args = parser.parse_args()
    opponent = "random" if args.opponent == "random" else pass_agent
    scores: list[dict[str, float | int]] = []
    for episode in range(args.episodes):
        env = make("kaggriculture", configuration={"seed": episode})
        env.run([kaggriculture_agent, opponent])
        rewards = [float(state.reward or 0) for state in env.steps[-1]]
        scores.append({"episode": episode, "agent_reward": rewards[0], "opponent_reward": rewards[1]})
    print(json.dumps({"opponent": args.opponent, "episodes": scores}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

