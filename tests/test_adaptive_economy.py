from kaggriculture_agent.adaptive_economy import (
    apply_adaptive_economy,
    preferred_optional_crop,
)


def _observation(*, carrot=70, wheat=40, cash=5000, shed_units=20, carrot_seeds=0):
    shed = {"WHEAT": 20, "FERTILIZER": 0}
    if shed_units > 20:
        shed["STRAWBERRY"] = shed_units - 20
    return {
        "day": 12,
        "step": 288,
        "player": 1,
        "farms": [
            {"money": 3000, "hands": [], "tiles": []},
            {"money": cash, "hands": [], "tiles": [[None]]},
        ],
        "private": {
            "shed": shed,
            "seeds": {"WHEAT": 2, "CARROT": carrot_seeds},
        },
        "market": {
            "prices": {"CARROT": carrot, "WHEAT": wheat, "STRAWBERRY": 120, "MELON": 150},
            "shedCapacity": 100,
        },
    }


def test_preferred_crop_requires_a_meaningful_price_advantage():
    state = {"prices": {"CARROT": 70, "WHEAT": 40, "STRAWBERRY": 120, "MELON": 150}}

    assert preferred_optional_crop(state) == "CARROT"


def test_adaptive_layer_replaces_one_market_slot_without_reordering():
    observation = _observation()
    action = {
        "farmer": ["PASS"],
        "hands": [["PLANT", "STRAWBERRY"]],
        "market": [["BUY_PRODUCT", "WHEAT", 1], ["HIRE"]],
    }

    result = apply_adaptive_economy(
        observation,
        action,
        future_feed=8,
        future_fertilizer=4,
        future_wheat_plants=8,
    )

    assert result["market"] == [["BUY_SEED", "CARROT", 1], ["HIRE"]]


def test_adaptive_layer_does_not_insert_or_split_market_orders():
    observation = _observation()
    action = {
        "farmer": ["PASS"],
        "hands": [["PASS"]],
        "market": [["HIRE"], ["BUY_PRODUCT", "WHEAT", 3], ["SELL", "WHEAT", 2]],
    }

    result = apply_adaptive_economy(
        observation,
        action,
        future_feed=8,
        future_fertilizer=4,
        future_wheat_plants=8,
    )

    assert result["market"] == action["market"]
    assert result["hands"] == action["hands"]


def test_adaptive_layer_can_fund_a_future_crop_slot():
    observation = _observation()
    action = {
        "farmer": ["PASS"],
        "hands": [["PASS"]],
        "market": [["BUY_PRODUCT", "WHEAT", 1], ["HIRE"]],
    }

    result = apply_adaptive_economy(
        observation,
        action,
        future_feed=8,
        future_fertilizer=4,
        future_wheat_plants=8,
    )

    assert result["market"] == [["BUY_SEED", "CARROT", 1], ["HIRE"]]


def test_adaptive_layer_does_not_change_full_shed():
    observation = _observation(shed_units=79)
    action = {"farmer": ["PASS"], "hands": [], "market": [["BUY_PRODUCT", "WHEAT", 3]]}

    result = apply_adaptive_economy(
        observation,
        action,
        future_feed=8,
        future_fertilizer=4,
        future_wheat_plants=8,
    )

    assert result["market"] == action["market"]


def test_adaptive_layer_reuses_observed_seed_for_one_plant():
    observation = _observation(carrot_seeds=2)
    action = {
        "farmer": ["PASS"],
        "hands": [["PLANT", "STRAWBERRY"]],
        "market": [],
    }

    result = apply_adaptive_economy(
        observation,
        action,
        future_feed=8,
        future_fertilizer=4,
        future_wheat_plants=8,
    )

    assert result["hands"] == [["PLANT", "CARROT"]]


def test_adaptive_layer_can_switch_a_wheat_slot_when_carrot_is_already_funded():
    observation = _observation(carrot_seeds=1)
    action = {
        "farmer": ["PASS"],
        "hands": [["PLANT", "WHEAT"]],
        "market": [],
    }

    result = apply_adaptive_economy(
        observation,
        action,
        future_feed=8,
        future_fertilizer=4,
        future_wheat_plants=8,
    )

    assert result["hands"] == [["PLANT", "CARROT"]]
