from kaggriculture_agent.late_harvest_policy import apply_late_harvest


def _obs(step, tile):
    return {
        "step": step,
        "player": 0,
        "private": {"shed": {}, "inventories": [{}, {}]},
        "farms": [{
            "farmer": [0, 0],
            "hands": [[1, 0]],
            "tiles": [[None, tile]],
        }],
    }


def test_late_mature_crop_is_harvested():
    obs = _obs(600, {"kind": "PLANT", "yield_units": 2})
    base = {"farmer": ["PASS"], "hands": [["PASS"]], "market": []}
    assert apply_late_harvest(obs, base)["hands"] == [["HARVEST"]]


def test_early_steps_and_non_mature_tiles_are_unchanged():
    base = {"farmer": ["PASS"], "hands": [["PASS"]], "market": []}
    assert apply_late_harvest(_obs(599, {"yield_units": 2}), base) == base
    assert apply_late_harvest(_obs(600, {"yield_units": 0}), base) == base
