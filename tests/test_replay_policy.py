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
