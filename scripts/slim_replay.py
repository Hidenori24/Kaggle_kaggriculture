"""Shrink a Kaggriculture replay to the part worth analysing.

A downloaded episode is around 30 MB, almost all of it full board snapshots
repeated every one of the 720 steps. The analysis only ever uses the action
sequences plus a daily sample of money and prices, which measured 235 KB
against a 29.7 MB source -- about 130x smaller, so ten fit in a couple of
megabytes.

    python scripts/slim_replay.py 12345678.json
    python scripts/slim_replay.py *.json --out-dir slim/

Writes <name>.slim.json beside the input unless --out-dir is given.

What is kept, and why:
  info, rewards   who played, which seed, who won
  actions         both players' full action sequence -- the analysis of what
                  an opponent actually does, and the source for adding them
                  to benchmarks/opponents.json
  money           per-day cash for both players, which is how a loss gets
                  attributed (a single bad day, or a steady daily deficit)
  prices          per-day market prices, for spotting which goods collapsed
  farm            per-day animal count, shed occupancy and planted crops --
                  the signals behind the starvation and shed-saturation bugs

What is dropped: per-step board tiles, per-step observations, and the 23
intra-day snapshots of everything above.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _farm_summary(farm):
    animals = 0
    crops = {}
    weeds = 0
    for row in farm.get("tiles") or []:
        for tile in row if isinstance(row, list) else [row]:
            if not isinstance(tile, dict):
                continue
            if tile.get("animal"):
                animals += 1
            elif tile.get("kind") == "WEED":
                weeds += 1
            elif tile.get("crop"):
                crops[tile["crop"]] = crops.get(tile["crop"], 0) + 1
    return {"animals": animals, "weeds": weeds, "crops": crops}


def slim(path, out_dir=None):
    with open(path) as handle:
        episode = json.load(handle)

    steps = episode.get("steps") or []
    seats = range(len(steps[0])) if steps else range(2)

    daily = [s for s in steps if s[0]["observation"].get("hour") == 0]
    out = {
        "info": episode.get("info"),
        "rewards": episode.get("rewards"),
        "statuses": episode.get("statuses"),
        "step_count": len(steps),
        "actions": [[s[i].get("action") for i in seats] for s in steps],
        "days": [
            {
                "day": s[0]["observation"].get("day"),
                "money": [s[0]["observation"]["farms"][i].get("money") for i in seats],
                "prices": s[0]["observation"]["market"].get("prices"),
                "shed": [
                    sum((s[i]["observation"].get("private") or {}).get("shed", {}).values())
                    for i in seats
                ],
                "farm": [_farm_summary(s[0]["observation"]["farms"][i]) for i in seats],
            }
            for s in daily
        ],
    }

    source = Path(path)
    target = Path(out_dir or source.parent) / (source.stem + ".slim.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w") as handle:
        json.dump(out, handle, separators=(",", ":"))

    before = source.stat().st_size / 1_048_576
    after = target.stat().st_size / 1024
    print(f"{source.name}  {before:.1f} MB -> {target.name}  {after:.0f} KB "
          f"({before * 1024 / max(after, 1):.0f}x smaller)")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replays", nargs="+", help="episode JSON files")
    parser.add_argument("--out-dir", help="write here instead of beside the input")
    args = parser.parse_args()
    for path in args.replays:
        try:
            slim(path, args.out_dir)
        except Exception as error:                       # keep going through a batch
            print(f"{path}: skipped ({type(error).__name__}: {error})")


if __name__ == "__main__":
    main()
