from kaggriculture_agent.legacy_replay_policy import agent


def test_legacy_policy_returns_kaggle_action_shape():
    observation = {
        "step": 0,
        "player": 0,
        "farms": [{"hands": []}],
        "private": {"shed": {}, "inventories": []},
    }
    result = agent(observation)
    assert set(result) == {"farmer", "hands", "market"}
    assert result["farmer"]
    assert result["hands"] == []
