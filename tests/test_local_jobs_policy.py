from kaggriculture_agent.local_jobs_policy import apply_local_jobs


def _obs(tile, action=("PASS",), inventory=None):
    return {
        "step": 10,
        "day": 0,
        "player": 0,
        "private": {"shed": {}, "inventories": [{}, inventory or {}]},
        "farms": [{
            "money": 1000,
            "farmer": [0, 0],
            "hands": [[1, 0]],
            "tiles": [[None, tile]],
        }],
    }, {"farmer": ["PASS"], "hands": [list(action)], "market": []}


def test_replaces_idle_hand_pass_with_harvest_on_mature_crop():
    obs, action = _obs({"kind": "PLANT", "yield_units": 2})
    assert apply_local_jobs(obs, action)["hands"] == [["HARVEST"]]


def test_replaces_idle_hand_pass_with_water_on_unwatered_crop():
    obs, action = _obs({"kind": "PLANT", "yield_units": 0, "watered_today": False})
    assert apply_local_jobs(obs, action)["hands"] == [["WATER"]]


def test_does_not_interrupt_non_pass_or_loaded_hand():
    obs, action = _obs({"kind": "PLANT", "yield_units": 2}, action=("EAST",))
    assert apply_local_jobs(obs, action)["hands"] == [["EAST"]]
    obs, action = _obs({"kind": "PLANT", "yield_units": 2}, inventory={"MILK": 1})
    assert apply_local_jobs(obs, action)["hands"] == [["PASS"]]
