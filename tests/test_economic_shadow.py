from kaggriculture_agent.economic_shadow import forecast_economy


def test_forecast_is_deterministic_and_read_only():
    observation = {
        "step": 100,
        "player": 0,
        "farms": [{
            "money": 500,
            "tiles": [[
                {"kind": "PLANT", "crop": "WHEAT", "yield_units": 3},
                {"kind": "PLANT", "crop": "MELON", "yield_units": 0},
            ]],
        }],
        "private": {"shed": {"WHEAT": 2}, "inventories": [{"WHEAT": 1}]},
        "market": {"prices": {"WHEAT": 32, "MELON": 270}},
    }

    before = repr(observation)
    first = forecast_economy(observation)
    second = forecast_economy(observation)

    assert first == second
    assert first["step"] == 100
    assert first["horizons"][24]["ready_harvest_value"] == 96
    assert first["horizons"][24]["liquidation_value"] == 96
    assert repr(observation) == before


def test_forecast_uses_day_and_hour_when_step_is_omitted():
    observation = {
        "day": 7,
        "hour": 1,
        "farms": [{"money": 0, "tiles": [[]]}],
        "private": {"shed": {}, "inventories": []},
        "market": {"prices": {}},
    }

    assert forecast_economy(observation)["step"] == 169
