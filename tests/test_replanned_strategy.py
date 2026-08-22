from kaggriculture_agent.replanned_strategy import choose_action


def _observation(*, day=6, step=144, money=2_000, unlocked=None, animals=None):
    unlocked = list(unlocked or ["NW"])
    tiles = [[None for _ in range(10)] for _ in range(10)]
    if animals:
        tiles[1][1] = {"kind": "PASTURE", "animal": animals}
    farm = {
        "money": money,
        "farmer": [4, 4],
        "hands": [],
        "hires_today": 0,
        "unlocked_quadrants": unlocked,
        "tiles": tiles,
    }
    return {
        "player": 0,
        "step": step,
        "day": day,
        "hour": 0,
        "farms": [farm, dict(farm)],
        "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
        "market": {"prices": {"WHEAT": 40, "MELON": 80}},
    }


def test_replanned_policy_reaches_expansion_from_fresh_state():
    action = choose_action(_observation())
    assert ["BUY_LAND"] in action["market"]


def test_replanned_policy_buys_first_animal_after_expansion():
    action = choose_action(
        _observation(day=8, step=192, money=1_000, unlocked=["NW", "NE"])
    )
    assert ["BUY_ANIMAL", "COW", 1] in action["market"]


def test_replanned_policy_returns_sdk_action_shape():
    action = choose_action(_observation(day=10, step=241, money=500, unlocked=["NW", "NE"], animals="COW"))
    assert set(action) == {"farmer", "hands", "market"}
    assert isinstance(action["farmer"], list)
    assert isinstance(action["hands"], list)
    assert isinstance(action["market"], list)
