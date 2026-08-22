from kaggriculture_agent.strawberry_all_mix_policy import _attractive, _open


def test_all_mix_uses_growth_adjusted_prices():
    assert _attractive({"market": {"prices": {"WHEAT": 49, "STRAWBERRY": 47}}})


def test_all_mix_rewrites_every_seed_lot():
    action = {"market": [["BUY_SEED", "STRAWBERRY", 8], ["BUY_SEED", "STRAWBERRY", 4]]}
    state = {"pending": 0, "opened": False}
    _open(action, state)
    assert action["market"] == [["BUY_SEED", "WHEAT", 8], ["BUY_SEED", "WHEAT", 4]]
    assert state["pending"] == 12
