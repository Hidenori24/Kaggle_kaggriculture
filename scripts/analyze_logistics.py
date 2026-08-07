from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaggle_environments import make  # noqa: E402

from kaggriculture_agent import kaggriculture_agent  # noqa: E402
from kaggriculture_agent.logistics_shadow import (  # noqa: E402
    diagnose_step,
    summarize_diagnostics,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze replay/物流 differences without applying them.")
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    episodes = []
    for seed in range(args.episodes):
        env = make("kaggriculture", configuration={"seed": seed})
        env.run([kaggriculture_agent, "random"])
        rows = []
        for states in env.steps:
            for state in states:
                observation = state.get("observation", {})
                if int(observation.get("player", 0) or 0) != 0:
                    continue
                rows.append(diagnose_step(observation, state.get("action", {})))
        rewards = [float(state.reward or 0) for state in env.steps[-1]]
        episodes.append(
            {
                "seed": seed,
                "agent_reward": rewards[0],
                "opponent_reward": rewards[1],
                "diagnostics": summarize_diagnostics(rows),
                "rows": rows,
            }
        )

    report = {"episodes": episodes}
    encoded = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "episodes": [
                    {
                        "seed": episode["seed"],
                        "agent_reward": episode["agent_reward"],
                        "opponent_reward": episode["opponent_reward"],
                        "diagnostics": episode["diagnostics"],
                    }
                    for episode in episodes
                ],
                "detail_output": str(args.output) if args.output else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
