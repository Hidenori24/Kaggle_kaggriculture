from kaggriculture_agent.crop_mix_policy import _STATE, _switch_seed_purchase, agent


def _obs(step=300, melon=180, wheat_seeds=12):
    return {
        "step": step,
        "player": 0,
        "market": {"prices": {"MELON": melon}},
        "private": {"seeds": {"WHEAT": wheat_seeds}},
        "farms": [{"hands": []}],
    }


def test_crowded_melon_purchase_becomes_wheat_in_same_order_slot():
    _STATE[0] = {"last_step": -1, "converted_seed_units": 0}
    observation = _obs()
    observation["step"] = 0
    observation["market"]["prices"]["MELON"] = 180
    action = {"farmer": ["PASS"], "hands": [], "market": [["BUY_SEED", "MELON", 12]]}
    state = {"converted_seed_units": 0}
    _switch_seed_purchase(observation, action, state)
    assert action["market"] == [["BUY_SEED", "WHEAT", 12]]
    assert state["converted_seed_units"] == 12


def test_switch_is_inactive_when_melon_is_not_crowded():
    _STATE[0] = {"last_step": -1, "converted_seed_units": 0}
    observation = _obs(step=0, melon=250)
    result = agent(observation)
    assert any(order[1] == "MELON" for order in result["market"] if len(order) > 1)
