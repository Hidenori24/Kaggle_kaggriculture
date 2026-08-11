from kaggriculture_agent.replay_policy import (
    _ACTIONS,
    _SHIFT_STATE,
    _base_agent,
    _preempt_shift,
    _safe_market,
    _shadow_market_overlay,
    agent,
)


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


def test_preempt_shift_does_not_re_floor_an_already_clamped_sell():
    # Step 167 has a WOOL hazard scheduled for step 168, so _preempt_shift's
    # gating conditions are satisfied once clone_distance is 0 (identical farms).
    _SHIFT_STATE[0] = {"last_step": -1, "due_step": -1, "due": {}, "last_preempt": -(10**9)}
    farm = {
        "farmer": [4, 4],
        "hands": [],
        "tiles": [[None] * 10 for _ in range(10)],
        "unlocked_quadrants": ["NW"],
    }
    observation = {
        "step": 167,
        "farms": [farm, farm],
        "private": {"shed": {"WOOL": 20}, "inventories": [{}]},
        "market": {"prices": {"WOOL": 30}},  # 30 / 200 reference = depressed tier
        "player": 0,
    }
    action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WOOL", 5]]}

    clamped = _safe_market(observation, action)
    assert _sell_quantity(clamped, "WOOL") == 1  # floor tier reduces 5 -> 1

    shifted = _preempt_shift(observation, clamped, 167)
    # A regression here would re-apply the price floor to the already-clamped
    # quantity of 1 (0.2 fraction of 1 rounds down to 0) and drop the order
    # entirely instead of letting the preempt logic size it.
    assert _sell_quantity(shifted, "WOOL") is not None
    assert _sell_quantity(shifted, "WOOL") >= 1


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


def test_shadow_forecast_cannot_change_replay_action():
    observation = {
        "step": 24,
        "player": 0,
        "farms": [{"farmer": [4, 4], "hands": [], "tiles": [[{
            "kind": "PLANT", "crop": "WHEAT", "yield_units": 3,
        }]]}],
        "private": {"shed": {"WHEAT": 2}, "inventories": [{}]},
        "market": {"prices": {"WHEAT": 32}},
    }

    assert agent(observation) == _base_agent(observation)


def test_late_shadow_overlay_changes_market_only_and_is_bounded():
    observation = {
        "step": 672,
        "player": 0,
        "farms": [{"farmer": [4, 4], "hands": [], "tiles": [[{
            "kind": "PLANT", "crop": "WHEAT", "yield_units": 0,
        }]]}],
        "private": {"shed": {"WHEAT": 100}, "inventories": [{}]},
        "market": {"prices": {"WHEAT": 51}},
    }
    base = {"farmer": ["PASS"], "hands": [], "market": []}
    result = _shadow_market_overlay(observation, base.copy())

    assert result["farmer"] == ["PASS"]
    assert result["hands"] == []
    assert len(result["market"]) <= 2
    assert result["market"] == [["SELL", "WHEAT", 8]]
