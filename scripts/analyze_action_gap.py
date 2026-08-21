"""Compare action density of the replay policy and recorded opponents.

This reads only the checked-in opponent action tapes.  It reports aggregate
operation counts and day buckets, never raw episode IDs or raw action logs.
The result is a diagnostic for choosing the next strategy experiment, not a
score predictor.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kaggle_environments import make  # noqa: E402
from kaggriculture_agent.replay_policy import agent as replay_agent  # noqa: E402

from benchmark import load_opponents, make_tape_agent  # noqa: E402


def _operation_counts(action: dict, counts: collections.Counter) -> None:
    operations = [action.get("farmer", [])] + list(action.get("hands", []) or [])
    for operation in operations:
        if operation:
            counts[str(operation[0])] += 1


def _count_policy(opponent: dict, our_seat: int, policy) -> collections.Counter:
    counts = collections.Counter()

    def wrapped(observation, configuration=None):
        action = policy(observation)
        _operation_counts(action, counts)
        return action

    tape = make_tape_agent(opponent["tape"])
    pair = [wrapped, tape] if our_seat == 0 else [tape, wrapped]
    env = make("kaggriculture", configuration={"seed": opponent["seed"]}, debug=False)
    env.run(pair)
    return counts


def _tape_counts(tape: list[dict]) -> collections.Counter:
    counts = collections.Counter()
    for action in tape:
        _operation_counts(action, counts)
    return counts


def _top(counts: collections.Counter, limit: int = 12) -> dict[str, int]:
    return dict(counts.most_common(limit))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opponent", help="an opponent name from benchmarks/opponents.json")
    args = parser.parse_args()
    opponents = load_opponents()
    if args.opponent:
        if args.opponent not in opponents:
            parser.error(f"unknown opponent; have {sorted(opponents)}")
        opponents = {args.opponent: opponents[args.opponent]}

    report = []
    for name, opponent in sorted(opponents.items()):
        tape = _tape_counts(opponent["tape"])
        seats = [_count_policy(opponent, seat, replay_agent) for seat in (0, 1)]
        replay = collections.Counter()
        for counts in seats:
            replay.update(counts)
        report.append({
            "opponent": name,
            "tape": _top(tape),
            "replay_mean_per_match": {
                key: round(value / 2, 1) for key, value in replay.items()
            },
            "delta_tape_minus_replay_mean": {
                key: round(tape.get(key, 0) - replay.get(key, 0) / 2, 1)
                for key in sorted(set(tape) | set(replay))
            },
        })
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
