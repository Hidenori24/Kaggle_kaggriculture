from kaggriculture_agent.replanned_logistics_strategy import choose_action


def _observation(*, fed=True):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[1][1] = {"kind": "PASTURE", "animal": "COW", "fed_today": fed}
    farm = {
        "money": 1_000,
        "farmer": [4, 4],
        "hands": [],
        "hires_today": 0,
        "unlocked_quadrants": ["NW", "NE"],
        "tiles": tiles,
    }
    return {
        "player": 0,
        "step": 241,
        "day": 10,
        "hour": 1,
        "farms": [farm, dict(farm)],
        "private": {"shed": {"WHEAT": 1}, "seeds": {}, "inventories": [{}]},
        "market": {"prices": {"WHEAT": 40, "MELON": 80}},
    }


def test_logistics_gate_preserves_feed_pickup_when_animal_is_unfed():
    action = choose_action(_observation(fed=False))
    assert action["farmer"] != ["PASS"]


def test_logistics_gate_does_not_create_feed_pickup_when_fully_serviced():
    action = choose_action(_observation(fed=True))
    assert action["farmer"] != ["PICKUP", "WHEAT", 1]
