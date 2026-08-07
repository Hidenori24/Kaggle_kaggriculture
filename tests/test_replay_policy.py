from kaggriculture_agent.replay_policy import _ACTIONS, _base_agent, agent


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
