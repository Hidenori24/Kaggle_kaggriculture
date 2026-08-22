from kaggriculture_agent.strawberry_mix_policy import _attractive, _open


def test_growth_adjusted_price_can_trigger_wheat_mix():
    assert _attractive({"market": {"prices": {"WHEAT": 49, "STRAWBERRY": 47}}})


def test_growth_adjusted_price_rejects_weak_wheat():
    assert not _attractive({"market": {"prices": {"WHEAT": 20, "STRAWBERRY": 200}}})


def test_only_complete_eight_unit_batch_is_replaced():
    state = {"pending": 0, "opened": False}
    action = {"market": [["BUY_SEED", "STRAWBERRY", 8]]}
    assert _open(action, state)
    assert action["market"] == [["BUY_SEED", "WHEAT", 8]]
    assert state["pending"] == 8
