from kaggriculture_agent.replay_policy import (
    _ACTIONS,
    _coalesce_sells,
    _forecast_surplus_sells,
    _future_input_demand,
    agent,
)


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


def test_split_sells_are_coalesced_without_changing_total_quantity():
    action = {
        "market": [
            ["SELL", "MILK", 4],
            ["HIRE"],
            ["SELL", "WOOL", 2],
            ["SELL", "MILK", 3],
        ]
    }

    result = _coalesce_sells(action)

    assert result["market"] == [
        ["SELL", "MILK", 7],
        ["HIRE"],
        ["SELL", "WOOL", 2],
    ]


def test_future_input_demand_is_empty_after_the_tape():
    assert _future_input_demand(len(_ACTIONS) - 1) == (0, 0)


def test_forecast_reserves_inputs_before_selling():
    observation = {
        "day": 5,
        "step": 120,
        "player": 0,
        "farms": [{"farmer": [4, 4], "hands": [], "tiles": [[None] * 5 for _ in range(5)]}],
        "private": {"shed": {"WHEAT": 40, "FERTILIZER": 20}, "inventories": [{}]},
        "market": {"prices": {"WHEAT": 50, "FERTILIZER": 100}},
    }
    action = {"farmer": ["PASS"], "hands": [], "market": [["HIRE"]]}
    result = _forecast_surplus_sells(observation, action, 120)
    assert result["market"] == [["HIRE"]]

