import pytest

from kaggriculture_agent.replay_policy import (
    _ACTIONS,
    _EXCURSION,
    _idle_run,
    _idle_work,
    _release_fertilizer,
    agent,
)


@pytest.fixture(autouse=True)
def _clear_excursions():
    for state in _EXCURSION.values():
        state.clear()
    yield
    for state in _EXCURSION.values():
        state.clear()


def _animal(**overrides):
    tile = {
        "kind": "PASTURE",
        "animal": "COW",
        "fed_today": True,
        "cared_today": False,
        "fertilizer_available": True,
        "yield_units": 0,
    }
    tile.update(overrides)
    return tile


def _observation(tiles, hands=(), inventories=(), shed=None, step=200):
    return {
        "step": step,
        "player": 0,
        "farms": [{"farmer": [0, 0], "hands": [list(h) for h in hands], "tiles": tiles,
                   "money": 5000}],
        "private": {"shed": dict(shed or {}),
                    "inventories": [dict(i) for i in (inventories or [{}])]},
        "market": {"prices": {"FERTILIZER": 100}},
    }


def test_replay_policy_is_deterministic_and_bounded():
    observation = {
        "step": 0,
        "farms": [{"hands": [[4, 4]]}],
        "private": {"shed": {}, "inventories": [{}]},
        "market": {"prices": {}},
    }

    first = agent(observation)
    second = agent(observation)

    assert first == second
    assert len(first["hands"]) == 1
    assert len(first["market"]) <= 10


def test_replay_policy_has_a_complete_episode_tape():
    assert len(_ACTIONS) >= 700
    assert all(isinstance(action, dict) for action in _ACTIONS)


def _sell_quantity(action, item):
    for order in action["market"]:
        if len(order) >= 3 and order[0] == "SELL" and order[1] == item:
            return order[2]
    return None


def test_sells_are_ordered_ahead_of_buys_by_expected_proceeds():
    # Step 120's tape is [SELL WHEAT 25, SELL FERTILIZER 3, HIRE,
    # BUY_ANIMAL COW 1]. With WHEAT at 2 and FERTILIZER at 100 the fertilizer
    # batch is worth far more, so it has to trade first.
    tiles = [[None] * 5 for _ in range(5)]
    observation = {
        "step": 120,
        "player": 0,
        "farms": [{"farmer": [4, 4], "hands": [], "tiles": tiles}],
        "private": {"shed": {"WHEAT": 40, "FERTILIZER": 10}, "inventories": [{}]},
        "market": {"prices": {"WHEAT": 2, "FERTILIZER": 100}},
    }
    market = agent(observation)["market"]
    kinds = [order[0] for order in market]
    assert kinds.index("SELL") < min(
        i for i, k in enumerate(kinds) if str(k).startswith("BUY_")
    )
    sells = [order for order in market if order[0] == "SELL"]
    assert sells[0][1] == "FERTILIZER"      # 3 x 100 beats 25 x 2

    observation["market"]["prices"] = {"WHEAT": 50, "FERTILIZER": 1}
    sells = [o for o in agent(observation)["market"] if o[0] == "SELL"]
    assert sells[0][1] == "WHEAT"           # order follows value, not identity


def test_market_stays_within_the_ten_order_cap_after_reordering():
    observation = {
        "step": 120,
        "player": 0,
        "farms": [{"farmer": [4, 4], "hands": [], "tiles": [[None] * 5 for _ in range(5)]}],
        "private": {"shed": {"WHEAT": 40, "FERTILIZER": 10}, "inventories": [{}]},
        "market": {"prices": {"WHEAT": 30, "FERTILIZER": 40}},
    }
    assert len(agent(observation)["market"]) <= 10


def test_idle_actor_collects_the_fertilizer_it_is_standing_on():
    tiles = [[None] * 10 for _ in range(10)]
    tiles[0][0] = _animal()
    action = {"farmer": ["PASS"], "hands": [], "market": []}
    out = _idle_work(_observation(tiles), action)
    assert out["farmer"] == ["COLLECT_FERTILIZER"]


def test_idle_work_never_overrides_an_action_the_tape_asked_for():
    tiles = [[None] * 10 for _ in range(10)]
    tiles[0][0] = _animal()
    action = {"farmer": ["HARVEST"], "hands": [], "market": []}
    out = _idle_work(_observation(tiles), action)
    assert out["farmer"] == ["HARVEST"]


def test_idle_work_feeds_only_when_the_actor_carries_wheat():
    tiles = [[None] * 10 for _ in range(10)]
    tiles[0][0] = _animal(fed_today=False, fertilizer_available=False)
    obs = _observation(tiles, inventories=[{}])
    assert _idle_work(obs, {"farmer": ["PASS"], "hands": [], "market": []})["farmer"] == ["PASS"]
    obs = _observation(tiles, inventories=[{"WHEAT": 1}])
    assert _idle_work(obs, {"farmer": ["PASS"], "hands": [], "market": []})["farmer"] == ["FEED"]


def test_idle_run_matches_the_tape():
    # The run reported for a step is the count of consecutive PASSes the tape
    # holds that actor for, counting the step itself.
    for step in (100, 300, 500):
        expected = 0
        for ahead in range(step, len(_ACTIONS)):
            if (_ACTIONS[ahead].get("farmer") or ["PASS"])[0] != "PASS":
                break
            expected += 1
        assert _idle_run(step, "farmer") == expected


def test_fertilizer_release_keeps_a_working_stock_back():
    # The tape spends 80 actions on FERTILIZE and picks the unit up from the
    # shed, so the reserve has to survive the drain.
    tiles = [[None] * 10 for _ in range(10)]
    obs = _observation(tiles, shed={"FERTILIZER": 50})
    out = _release_fertilizer(obs, {"farmer": ["PASS"], "hands": [], "market": []})
    assert out["market"] == [["SELL", "FERTILIZER", 30]]

    obs = _observation(tiles, shed={"FERTILIZER": 20})
    out = _release_fertilizer(obs, {"farmer": ["PASS"], "hands": [], "market": []})
    assert out["market"] == []


def test_fertilizer_release_leaves_a_full_order_book_alone():
    tiles = [[None] * 10 for _ in range(10)]
    obs = _observation(tiles, shed={"FERTILIZER": 90})
    full = {"farmer": ["PASS"], "hands": [], "market": [["HIRE"]] * 10}
    assert _release_fertilizer(obs, full)["market"] == [["HIRE"]] * 10
