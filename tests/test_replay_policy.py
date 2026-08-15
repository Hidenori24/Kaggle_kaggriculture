from kaggriculture_agent.replay_policy import _ACTIONS, _TROUGH_STATE, agent


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


def _trough_observation(step, shed):
    return {
        "step": step,
        "player": 0,
        "farms": [{"farmer": [4, 4], "hands": []}],
        "private": {"shed": dict(shed), "inventories": [{}]},
        "market": {"prices": {}},
    }


def _reset_trough_state():
    for seat in (0, 1):
        _TROUGH_STATE[seat] = {"last_step": -1, "pending": []}


def test_trough_sell_is_deferred_to_the_restocked_step():
    # Step 68 is a trough step (68 % 4 == 0) whose tape market is a lone
    # SELL WHEAT 2 with nothing to pay for, so deferring it is safe.
    _reset_trough_state()
    held = agent(_trough_observation(68, {"WHEAT": 20}))
    assert _sell_quantity(held, "WHEAT") is None

    released = agent(_trough_observation(69, {"WHEAT": 20}))
    assert _sell_quantity(released, "WHEAT") == 2


def test_trough_sell_is_kept_when_the_step_has_something_to_pay_for():
    # Step 48 pairs SELL FERTILIZER with HIRE and BUY_PRODUCT WHEAT. Deferring
    # the proceeds there starves the tape's own purchases.
    _reset_trough_state()
    action = agent(_trough_observation(48, {"FERTILIZER": 20}))
    assert _sell_quantity(action, "FERTILIZER") == 2


def test_trough_sell_is_kept_when_the_shed_is_nearly_full():
    # A near-full shed must keep draining; holding stock there is how the
    # withdrawn price floor pinned the shed and starved the animals.
    _reset_trough_state()
    action = agent(_trough_observation(68, {"WHEAT": 20, "WOOL": 75}))
    assert _sell_quantity(action, "WHEAT") == 2


def test_trough_deferral_never_holds_stock_past_the_final_step():
    _reset_trough_state()
    last = len(_ACTIONS) - 1
    action = agent(_trough_observation(last - (last % 4), {"WHEAT": 5}))
    assert isinstance(action["market"], list)
    final = agent(_trough_observation(last, {"WHEAT": 5}))
    assert _sell_quantity(final, "WHEAT") == 5
    assert _TROUGH_STATE[0]["pending"] == []


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
