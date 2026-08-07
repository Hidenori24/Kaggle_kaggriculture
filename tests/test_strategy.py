from kaggriculture_agent.strategy import BaselineConfig, _route_cells, choose_action


def observation(tile=None, seeds=None):
    farm = {"money": 3000.0, "farmer": [4, 4], "hands": [], "hires_today": 0,
            "tiles": [[None for _ in range(10)] for _ in range(10)]}
    farm["tiles"][4][4] = tile
    return {
        "player": 0,
        "step": 1,
        "day": 0,
        "hour": 1,
        "farms": [farm, farm.copy()],
        "private": {"seeds": seeds or {"MELON": 1}},
    }


def test_first_turn_buys_baseline_seeds():
    action = choose_action({**observation(), "step": 0})
    assert ["BUY_SEED", "MELON", 15] in action["market"]


def test_empty_tile_plants_when_seed_is_available():
    action = choose_action(observation())
    assert action["farmer"] == ["PLANT", "MELON"]


def test_unwatered_plant_is_watered_before_harvest():
    tile = {"kind": "PLANT", "crop": "CARROT", "watered_today": False, "yield_units": 2, "planted_day": 0}
    action = choose_action({**observation(tile, {}), "day": 2})
    assert action["farmer"] == ["WATER"]


def test_ready_plant_is_harvested_after_watering():
    tile = {"kind": "PLANT", "crop": "CARROT", "watered_today": True, "yield_units": 2, "planted_day": 0}
    action = choose_action({**observation(tile, {}), "day": 2})
    assert action["farmer"] == ["HARVEST"]


def test_expansion_route_covers_each_unlocked_quadrant_once():
    route = _route_cells(5, ["NW", "NE"])

    assert len(route) == 50
    assert len(set(route)) == 50
    assert (0, 0) in route and (4, 4) in route
    assert (5, 0) in route and (9, 4) in route


def test_expansion_is_opt_in_and_buys_short_cycle_seed():
    farm = {
        "money": 20_000.0,
        "farmer": [4, 4],
        "hands": [[4, 4] for _ in range(10)],
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
        "tiles": [[None for _ in range(10)] for _ in range(10)],
    }
    obs = {
        "player": 0,
        "step": 481,
        "day": 20,
        "hour": 0,
        "farms": [farm, farm.copy()],
        "private": {"seeds": {"MELON": 12, "WHEAT": 0}},
    }

    safe_action = choose_action(obs)
    expansion_action = choose_action(obs, BaselineConfig(enable_expansion=True))

    assert not any(order[0] == "BUY_LAND" for order in safe_action["market"])
    assert ["BUY_LAND"] in expansion_action["market"]
    assert ["BUY_SEED", "WHEAT", 30] in expansion_action["market"]
