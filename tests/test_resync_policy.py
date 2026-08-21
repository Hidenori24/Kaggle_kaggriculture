from kaggriculture_agent.resync_policy import _STATE, apply_resync


def _obs(step, tile):
    return {
        "step": step,
        "player": 0,
        "farms": [{
            "farmer": [0, 0],
            "hands": [[1, 0]],
            "tiles": [[None, tile]],
        }],
    }


def test_retries_only_when_previous_harvest_is_observed_to_fail():
    _STATE[0] = {"last_step": -1, "previous": None}
    first = _obs(0, {"kind": "PLANT", "yield_units": 2})
    base = {"farmer": ["PASS"], "hands": [["HARVEST"]], "market": []}
    apply_resync(first, base)
    second = _obs(1, {"kind": "PLANT", "yield_units": 2})
    retry = apply_resync(second, {"farmer": ["PASS"], "hands": [["PASS"]], "market": []})
    assert retry["hands"] == [["HARVEST"]]


def test_no_retry_after_observed_success_or_when_position_changed():
    _STATE[0] = {"last_step": -1, "previous": None}
    base = {"farmer": ["PASS"], "hands": [["HARVEST"]], "market": []}
    apply_resync(_obs(0, {"kind": "PLANT", "yield_units": 2}), base)
    assert apply_resync(_obs(1, {"kind": "PLANT", "yield_units": 0}), {"farmer": ["PASS"], "hands": [["PASS"]], "market": []})["hands"] == [["PASS"]]
    _STATE[0] = {"last_step": -1, "previous": None}
    apply_resync(_obs(0, {"kind": "PLANT", "yield_units": 2}), base)
    moved = _obs(1, {"kind": "PLANT", "yield_units": 2})
    moved["farms"][0]["hands"] = [[2, 0]]
    assert apply_resync(moved, {"farmer": ["PASS"], "hands": [["PASS"]], "market": []})["hands"] == [["PASS"]]
