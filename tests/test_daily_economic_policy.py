from kaggriculture_agent.daily_economic_policy import _plan_market, _STATE


def _obs(step=240, price=18, shed=None):
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "market": {"prices": {"WHEAT": price}},
        "private": {"shed": shed or {"WHEAT": 20}},
        "farms": [{"hands": []}],
    }


def test_daily_plan_holds_only_a_bounded_existing_wheat_sale():
    _STATE[0] = {"last_step": -1, "day": -1, "held": {}, "daily_held": {}, "reference": {}}
    action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 20], ["HIRE"]]}
    result = _plan_market(_obs(), action)
    assert result["market"] == [["SELL", "WHEAT", 8], ["HIRE"]]
    assert _STATE[0]["held"] == {"WHEAT": 12}


def test_daily_plan_releases_held_sale_after_recovery():
    _STATE[0] = {"last_step": -1, "day": -1, "held": {}, "daily_held": {}, "reference": {}}
    action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 1]]}
    _plan_market(_obs(price=18), action)
    recovered = _obs(step=264, price=24, shed={"WHEAT": 20})
    result = _plan_market(recovered, {"farmer": ["PASS"], "hands": [], "market": []})
    assert result["market"] == [["SELL", "WHEAT", 1]]


def test_daily_plan_does_not_hold_when_shed_is_near_capacity():
    _STATE[0] = {"last_step": -1, "day": -1, "held": {}, "daily_held": {}, "reference": {}}
    action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 20]]}
    result = _plan_market(_obs(shed={"WHEAT": 79}), action)
    assert result["market"] == action["market"]
