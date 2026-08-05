Exit code: 0
Wall time: 8.3 seconds
Output:
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaggle_environments import make  # noqa: E402

from kaggriculture_agent import kaggriculture_agent  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=3)
    args = parser.parse_args()
    scores: list[dict[str, float | int]] = []
    for episode in range(args.episodes):
        env = make("kaggriculture", configuration={"seed": episode})
        env.run([kaggriculture_agent, "random"])
        rewards = [float(state.reward or 0) for state in env.steps[-1]]
        scores.append({"episode": episode, "agent_reward": rewards[0], "opponent_reward": rewards[1]})
    print(json.dumps({"episodes": scores}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

