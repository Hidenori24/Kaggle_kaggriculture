from kaggriculture_agent.carrot_mix_policy import _STATE, _convert_first_melon_seed, agent


def test_carrot_mix_converts_one_future_melon_order():
    action = {
        "farmer": ["PASS"],
        "hands": [],
        "market": [["BUY_SEED", "MELON", 6], ["HIRE"]],
    }
    assert _convert_first_melon_seed(action) == 6
    assert action["market"] == [["BUY_SEED", "CARROT", 6], ["HIRE"]]


def test_carrot_mix_keeps_melon_when_trade_is_not_attractive():
    _STATE[0] = {"last_step": -1, "converted": 0}
    observation = {
        "step": 0,
        "player": 0,
        "market": {"prices": {"CARROT": 35, "MELON": 250}},
        "private": {"seeds": {}},
        "farms": [{"hands": []}],
    }
    result = agent(observation)
    assert all(order[1] != "CARROT" for order in result["market"] if len(order) > 1)
