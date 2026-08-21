"""Inspect stateful logistics opportunities without changing production actions."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaggriculture_agent.logistics_state import shadow_report  # noqa: E402
from kaggriculture_agent.replay_policy import agent  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode", type=Path)
    parser.add_argument("--agent", default="N_Matsumoto24")
    args = parser.parse_args()
    episode = json.loads(args.episode.read_text(encoding="utf-8"))
    names = [entry.get("Name", "") for entry in episode.get("info", {}).get("Agents", [])]
    if args.agent not in names:
        raise SystemExit(f"agent not found: {args.agent!r}; available={names!r}")
    seat = names.index(args.agent)
    counts = Counter()
    samples = []
    for index, step in enumerate(episode["steps"]):
        record = step[seat]
        observation = record.get("observation", {})
        proposed_action = agent(observation)
        report = shadow_report(observation, proposed_action)
        recorded_operations = {
            operation[0]
            for operation in [record.get("action", {}).get("farmer", [])]
            + list(record.get("action", {}).get("hands", []) or [])
            if operation
        }
        for job in report["jobs"]:
            if job["kind"] not in recorded_operations:
                counts[job["kind"]] += 1
        if report["urgent_jobs_unserved"] and len(samples) < 20:
            samples.append({"step": index, **report})
    print(f"seat={seat} steps={len(episode['steps'])}")
    print(f"unserved_local_jobs={dict(counts)}")
    print(f"samples={samples}")


if __name__ == "__main__":
    main()
