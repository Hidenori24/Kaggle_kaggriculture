from kaggriculture_agent.job_queue_strategy import choose_action


def _observation():
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[1][1] = {"kind": "PLANT", "crop": "WHEAT", "yield_units": 2, "planted_day": 0, "watered_today": True}
    farm = {
        "money": 1_000,
        "farmer": [1, 1],
        "hands": [],
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
        "tiles": tiles,
    }
    return {
        "player": 0,
        "step": 48,
        "day": 2,
        "hour": 0,
        "farms": [farm, dict(farm)],
        "private": {"shed": {}, "seeds": {"WHEAT": 2}, "inventories": [{}]},
        "market": {"prices": {"WHEAT": 40, "MELON": 80}},
    }


def test_job_queue_prioritises_harvest_at_current_position():
    assert choose_action(_observation())["farmer"] == ["HARVEST"]


def test_job_queue_keeps_sdk_action_shape():
    action = choose_action(_observation())
    assert set(action) == {"farmer", "hands", "market"}
