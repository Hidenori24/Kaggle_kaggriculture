from kaggriculture_agent.adaptive_policy import ENDGAME_START_STEP, agent
from kaggriculture_agent.pass_repair_policy import agent as pass_repair_agent
from kaggriculture_agent.replay_policy import agent as replay_agent


def _observation(step: int, shed=None):
    farm = {
        "money": 10_000,
        "farmer": [4, 4],
        "hands": [],
        "tiles": [[None for _ in range(10)] for _ in range(10)],
        "unlocked_quadrants": ["NW"],
    }
    return {
        "player": 0,
        "step": step,
        "farms": [farm, farm.copy()],
        "private": {"shed": shed or {}, "inventories": [{}], "seeds": {}},
        "market": {"prices": {"MELON": 250, "WHEAT": 25}},
    }


def test_adaptive_policy_matches_replay_before_final_day():
    obs = _observation(ENDGAME_START_STEP - 1)

    assert agent(obs) == replay_agent(obs)


def test_adaptive_policy_liquidates_remaining_sellable_inventory():
    obs = _observation(ENDGAME_START_STEP, {"MELON": 3, "WHEAT": 2})

    action = agent(obs)
    sells = {order[1]: order[2] for order in action["market"] if order[0] == "SELL"}

    assert sells["MELON"] == 3
    assert sells["WHEAT"] == 2


def test_pass_repair_does_not_change_a_pass_on_an_empty_tile():
    obs = _observation(100)
    obs["day"] = 100
    assert pass_repair_agent(obs) == replay_agent(obs)


def test_pass_repair_harvests_a_ready_plant_under_a_pass(monkeypatch):
    obs = _observation(100)
    obs["day"] = 100
    farm = obs["farms"][0]
    farm["farmer"] = [4, 4]
    farm["tiles"][4][4] = {
        "kind": "PLANT",
        "crop": "WHEAT",
        "watered_today": True,
        "yield_units": 2,
        "planted_day": 90,
    }
    monkeypatch.setattr(
        "kaggriculture_agent.pass_repair_policy.replay_with_endgame_agent",
        lambda _obs: {"farmer": ["PASS"], "hands": [], "market": []},
    )
    repaired = pass_repair_agent(obs)
    assert repaired["farmer"] == ["HARVEST"]
