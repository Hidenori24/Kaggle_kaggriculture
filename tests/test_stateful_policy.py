from kaggriculture_agent.stateful_policy import _transport_repair


def _obs(inventory, action):
    return {
        "step": 100,
        "day": 4,
        "player": 0,
        "private": {"shed": {}, "seeds": {}, "inventories": [inventory]},
        "farms": [{
            "money": 1000,
            "farmer": [4, 4],
            "hands": [],
            "unlocked_quadrants": ["NW"],
            "tiles": [[None] * 10 for _ in range(10)],
        }],
    }, action


def test_transport_repair_drops_safe_product_at_shed():
    obs, action = _obs({"MILK": 1}, {"farmer": ["PASS"], "hands": [], "market": []})
    assert _transport_repair(obs, action)["farmer"] == ["DROP"]


def test_transport_repair_does_not_drop_feed_at_shed():
    obs, action = _obs({"WHEAT": 1}, {"farmer": ["PASS"], "hands": [], "market": []})
    assert _transport_repair(obs, action)["farmer"] == ["PASS"]


def test_transport_repair_changes_only_the_transport_action():
    obs, action = _obs({"MILK": 1}, {"farmer": ["EAST"], "hands": [], "market": [["HIRE"]]})
    result = _transport_repair(obs, action)
    assert result["farmer"] == ["DROP"]
    assert result["market"] == [["HIRE"]]
