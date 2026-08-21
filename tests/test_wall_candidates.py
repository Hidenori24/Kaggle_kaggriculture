from kaggriculture_agent.pressure_order_policy import _pressure_order
from kaggriculture_agent.redundant_feed_policy import _repair
from kaggriculture_agent.wheat_budget_policy import _trim_purchase


def _farm(tile):
    return {
        "farmer": [0, 0],
        "hands": [[1, 0]],
        "tiles": [[None, tile]],
        "money": 20000,
    }


def test_pressure_order_only_reorders_existing_market_orders():
    observation = {"market": {"prices": {"MELON": 1, "MILK": 20, "WOOL": 30, "WHEAT": 25}}}
    action = {
        "farmer": ["PASS"],
        "hands": [["PASS"]],
        "market": [["SELL", "MELON", 4], ["SELL", "MILK", 2], ["HIRE"]],
    }
    result = _pressure_order(observation, action)
    assert sorted(result["market"]) == sorted(action["market"])
    assert result["market"][-1] == ["HIRE"]


def test_wheat_budget_never_adds_or_reorders_orders():
    observation = {
        "step": 240,
        "player": 0,
        "farms": [{**_farm({"animal": "COW", "fed_today": False})}],
        "private": {"shed": {"WHEAT": 200}, "inventories": [{"WHEAT": 5}]},
    }
    action = {"farmer": ["PASS"], "hands": [["PASS"]], "market": [["BUY_PRODUCT", "WHEAT", 3], ["HIRE"]]}
    result = _trim_purchase(observation, action)
    assert result["market"][1] == ["HIRE"]
    assert 1 <= result["market"][0][2] < 3


def test_redundant_feed_becomes_pass_only_when_already_fed():
    observation = {
        "player": 0,
        "farms": [{**_farm({"animal": "COW", "fed_today": True})}],
    }
    action = {"farmer": ["PASS"], "hands": [["FEED"]], "market": []}
    assert _repair(observation, action)["hands"] == [["PASS"]]


def test_valid_feed_is_preserved():
    observation = {
        "player": 0,
        "farms": [{**_farm({"animal": "COW", "fed_today": False})}],
    }
    action = {"farmer": ["PASS"], "hands": [["FEED"]], "market": []}
    assert _repair(observation, action) == action
