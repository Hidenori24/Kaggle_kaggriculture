from kaggriculture_agent.input_budget_policy import _cap_purchase


def _obs(wheat=20, fertilizer=0):
    return {
        "step": 240,
        "day": 10,
        "player": 0,
        "private": {"shed": {"WHEAT": wheat, "FERTILIZER": fertilizer}, "inventories": []},
        "farms": [{"hands": [], "tiles": [[{"animal": "COW"}]]}],
    }


def test_input_budget_trims_excess_wheat_purchase():
    action = {"farmer": ["FEED"], "hands": [], "market": [["BUY_PRODUCT", "WHEAT", 20], ["HIRE"]]}
    result = _cap_purchase(_obs(wheat=20), action)
    assert result["market"][0][0:2] == ["BUY_PRODUCT", "WHEAT"]
    assert result["market"][0][2] < 20


def test_input_budget_does_not_create_market_orders():
    action = {"farmer": ["PASS"], "hands": [], "market": [["HIRE"]]}
    assert _cap_purchase(_obs(wheat=0), action)["market"] == [["HIRE"]]

