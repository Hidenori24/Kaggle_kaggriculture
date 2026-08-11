from kaggriculture_agent.replay_policy import _ACTIONS, agent


def _sell_quantity(action, item):
    for order in action["market"]:
        if len(order) >= 3 and order[0] == "SELL" and order[1] == item:
            return order[2]
    return None


def _fertilizer_sale_observation(price):
    # Step 39's scheduled tape sells 2 FERTILIZER; FERTILIZER opens at 100.
    return {
        "step": 39,
        "farms": [{"farmer": [4, 4], "hands": []}],
        "private": {"shed": {"FERTILIZER": 10}, "inventories": [{}]},
        "market": {"prices": {"FERTILIZER": price}},
        "player": 0,
    }


def test_replay_policy_sells_full_tape_quantity_at_healthy_prices():
    action = agent(_fertilizer_sale_observation(100))
    assert _sell_quantity(action, "FERTILIZER") == 2


def test_replay_policy_holds_back_sales_into_a_crashed_price():
    action = agent(_fertilizer_sale_observation(5))
    assert _sell_quantity(action, "FERTILIZER") is None


def test_replay_policy_partially_sells_into_a_depressed_price():
    action = agent(_fertilizer_sale_observation(30))
    assert _sell_quantity(action, "FERTILIZER") == 1


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
