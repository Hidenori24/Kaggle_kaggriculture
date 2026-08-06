from kaggriculture_agent.full_strategy import (
    _shed_access,
    _unit_action,
    choose_action,
)
from kaggriculture_agent.strategy import BaselineConfig, choose_action as choose_baseline


def _farm(tile=None, unlocked=("NW",), position=(4, 4)):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    if tile is not None:
        tiles[position[1]][position[0]] = tile
    return {
        "money": 10_000.0,
        "farmer": list(position),
        "hands": [],
        "hires_today": 0,
        "unlocked_quadrants": list(unlocked),
        "tiles": tiles,
    }


def _obs(farm, private=None, *, step=1, day=24, hour=1):
    return {
        "player": 0,
        "step": step,
        "day": day,
        "hour": hour,
        "farms": [farm, dict(farm)],
        "private": private or {"seeds": {"MELON": 3}},
    }


def test_extended_policy_delegates_to_baseline_until_extended_state_exists():
    obs = _obs(_farm(), {"seeds": {"MELON": 3}})
    assert choose_action(obs) == choose_baseline(obs, BaselineConfig(enable_expansion=False))


def test_extended_policy_does_not_sell_living_animals():
    tile = {"kind": "PASTURE", "animal": "COW", "fed_today": True, "cared_today": True}
    private = {"seeds": {"MELON": 3}, "shed": {"COW": 1, "MELON": 2}, "inventories": [{}]}
    action = choose_action(_obs(_farm(tile, ("NW", "NE")), private, step=0, day=24, hour=0))
    assert ["SELL", "MELON", 2] in action["market"]
    assert not any(order[:2] == ["SELL", "COW"] for order in action["market"])


def test_extended_unit_policy_covers_local_operations():
    empty_private = {"seeds": {"MELON": 1}}
    plant = {"kind": "PLANT", "crop": "MELON", "watered_today": False, "yield_units": 1, "planted_day": 0}
    ready = {"kind": "PLANT", "crop": "WHEAT", "watered_today": True, "yield_units": 1, "planted_day": 0}
    animal = {"kind": "PASTURE", "animal": "COW", "fed_today": False, "cared_today": False}
    cared_animal = {**animal, "fed_today": True, "cared_today": True, "fertilizer_available": True}
    structures = [[None for _ in range(10)] for _ in range(10)]
    structures[0][0] = {"kind": "PASTURE"}
    cases = [
        (_unit_action([0, 0], plant, (0, 0), empty_private, structures, 24, 5, "farmer", {}, ["NW"]), "WATER"),
        (_unit_action([0, 0], ready, (0, 0), empty_private, structures, 24, 5, "farmer", {}, ["NW"]), "HARVEST"),
        (_unit_action([0, 0], plant, (0, 0), empty_private, structures, 24, 5, "farmer", {"FERTILIZER": 1}, ["NW"]), "WATER"),
        (_unit_action([0, 0], animal, (0, 0), empty_private, structures, 24, 5, "farmer", {"WHEAT": 1}, ["NW"]), "FEED"),
        (_unit_action([0, 0], cared_animal, (0, 0), empty_private, structures, 24, 5, "farmer", {}, ["NW"]), "COLLECT_FERTILIZER"),
        (_unit_action(list(_shed_access()[0]), None, (0, 0), {"shed": {"COW": 1}}, structures, 24, 5, "builder", {}, ["NW"]), "PICKUP"),
        (_unit_action([0, 0], None, (0, 0), empty_private, structures, 24, 5, "farmer", {}, ["NW"]), "PLANT"),
    ]
    assert all(action[0] == expected for action, expected in cases)

