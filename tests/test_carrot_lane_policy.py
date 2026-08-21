from kaggriculture_agent.carrot_lane_policy import (
    _STATE,
    _lane_is_attractive,
    _open_first_lane,
    _sell_carrot_surplus,
)


def test_carrot_lane_requires_a_real_price_gap():
    assert _lane_is_attractive({"market": {"prices": {"CARROT": 35, "WHEAT": 30}}})
    assert not _lane_is_attractive({"market": {"prices": {"CARROT": 34, "WHEAT": 30}}})


def test_carrot_lane_rewrites_only_the_first_seed_batch():
    _STATE[0] = {"last_step": -1, "pending": 0, "opened": False}
    action = {"farmer": ["PASS"], "hands": [], "market": [["BUY_SEED", "WHEAT", 7]]}
    observation = {"market": {"prices": {"CARROT": 35, "WHEAT": 25}}}
    assert _open_first_lane(observation, action, _STATE[0])
    assert action["market"] == [["BUY_SEED", "CARROT", 7]]
    assert _STATE[0]["pending"] == 7


def test_carrot_lane_sells_converted_output():
    action = {"farmer": ["PASS"], "hands": [], "market": []}
    _sell_carrot_surplus({"private": {"shed": {"CARROT": 3}}}, action)
    assert action["market"] == [["SELL", "CARROT", 3]]
