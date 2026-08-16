"""Shrink a downloaded Kaggriculture replay so it can actually be shared.

A full episode JSON from the Kaggle replay viewer is ~30 MB, because every
one of the 720 steps carries both players' complete observation: the 5x5 (or
larger) tile grid with every crop's growth stage, the full market state, the
private shed and inventories.  That does not fit through a chat upload, and
almost none of it is what post-match analysis actually reads.

This keeps the three things the analyses in `docs/experiments.md` were built
on and drops everything else:

* `actions` -- both seats, all 720 steps, verbatim.  This is what the
  opponent-similarity comparisons run on, and it is what a tape transcription
  would be cut from.
* `days` -- one snapshot per day rollover: money, market prices, shed
  occupancy, and per-farm animal/weed/crop counts for both seats.  The
  money series is what exposed the day-4-to-day-12 tempo reversal; the
  animal and shed series are what the starvation and shed-saturation
  regressions turned on.
* `info` -- player names, episode id, seed, so a match can be reproduced.

Result is roughly 230 KB, a ~130x reduction, with no loss for any question
asked so far.

Usage:
    python scripts/slim_replay.py episode.json               # -> episode.slim.json
    python scripts/slim_replay.py *.json --outdir slim/
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ITEMS_FROM_TILES = ("animals", "weeds", "crops")


def _seat_state(step, seat):
    """Per-seat entry of a replay step, or None when the seat is absent.

    Finished or errored agents can drop out of later steps, which is what
    makes the naive `step[1]` indexing blow up on real downloads.
    """
    if not isinstance(step, list) or seat >= len(step):
        return None
    entry = step[seat]
    return entry if isinstance(entry, dict) else None


def _observation(step, seat):
    entry = _seat_state(step, seat)
    return (entry or {}).get("observation") or {}


def _farm_summary(farm):
    """Collapse a tile grid to the counts the analyses read."""
    animals = weeds = 0
    crops = {}
    for row in farm.get("tiles") or []:
        for tile in row or []:
            if not isinstance(tile, dict):
                continue
            kind = tile.get("kind")
            if "animal" in tile:
                animals += 1
            elif kind == "WEED":
                weeds += 1
            elif kind == "PLANT" and tile.get("crop"):
                crops[tile["crop"]] = crops.get(tile["crop"], 0) + 1
    return {"animals": animals, "weeds": weeds, "crops": crops}


def _day_snapshot(step, seats):
    """Both seats' state at a day rollover.

    Money and tiles are public and live under `farms`, so both seats' come
    from seat 0's observation.  The shed is not: `private` holds only the
    observing seat's, so seat 1's has to be read from seat 1's own
    observation.
    """
    shared = _observation(step, 0)
    money, shed, farm = [], [], []
    farms = shared.get("farms") or []
    for seat in range(seats):
        own_farm = farms[seat] if seat < len(farms) else {}
        private = _observation(step, seat).get("private") or {}
        money.append(own_farm.get("money"))
        shed.append(sum((private.get("shed") or {}).values()))
        farm.append(_farm_summary(own_farm))
    return {
        "day": shared.get("day"),
        "money": money,
        "prices": (shared.get("market") or {}).get("prices") or {},
        "shed": shed,
        "farm": farm,
    }


def slim(replay):
    steps = replay.get("steps") or []
    seats = max((len(s) for s in steps if isinstance(s, list)), default=2)

    actions = []
    days = []
    for step in steps:
        actions.append([(_seat_state(step, seat) or {}).get("action") for seat in range(seats)])
        if _observation(step, 0).get("hour") == 0:
            days.append(_day_snapshot(step, seats))

    info = dict(replay.get("info") or {})
    seed = (replay.get("configuration") or {}).get("seed")
    if seed is not None:
        info["seed"] = seed

    return {
        "info": info,
        "rewards": replay.get("rewards"),
        "actions": actions,
        "days": days,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="full replay JSON files")
    parser.add_argument("--outdir", type=Path, help="write here instead of alongside the input")
    args = parser.parse_args()

    for path in args.paths:
        with open(path) as handle:
            replay = json.load(handle)
        out = (args.outdir or path.parent) / (path.stem + ".slim.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as handle:
            json.dump(slim(replay), handle, separators=(",", ":"))
        before, after = path.stat().st_size, out.stat().st_size
        print(f"{path.name} {before/1e6:.1f}MB -> {out.name} {after/1e3:.0f}KB "
              f"({before/max(after, 1):.0f}x)")


if __name__ == "__main__":
    main()
