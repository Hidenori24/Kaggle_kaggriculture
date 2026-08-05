from kaggriculture_agent.strategy import choose_action


def observation(tile=None, seeds=None):
    farm = {"farmer": [4, 4], "tiles": [[None for _ in range(10)] for _ in range(10)]}
    farm["tiles"][4][4] = tile
    return {
        "player": 0,
        "step": 1,
        "day": 0,
        "hour": 1,
        "farms": [farm, farm.copy()],
        "private": {"seeds": seeds or {"CARROT": 1}},
    }


def test_first_turn_buys_baseline_seeds():
    action = choose_action({**observation(), "step": 0})
    assert action["market"] == [["BUY_SEED", "CARROT", 20]]


def test_empty_tile_plants_when_seed_is_available():
    action = choose_action(observation())
    assert action["farmer"] == ["PLANT", "CARROT"]


def test_unwatered_plant_is_watered_before_harvest():
    tile = {"kind": "PLANT", "crop": "CARROT", "watered_today": False, "yield_units": 2, "planted_day": 0}
    action = choose_action({**observation(tile, {}), "day": 2})
    assert action["farmer"] == ["WATER"]


def test_ready_plant_is_harvested_after_watering():
    tile = {"kind": "PLANT", "crop": "CARROT", "watered_today": True, "yield_units": 2, "planted_day": 0}
    action = choose_action({**observation(tile, {}), "day": 2})
    assert action["farmer"] == ["HARVEST"]
