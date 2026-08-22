from kaggriculture_agent.urgent_jobs_policy import apply_urgent_jobs


def _obs(tile, inventory=None):
    return {
        "player": 0,
        "step": 10,
        "private": {"shed": {}, "inventories": [inventory or {}]},
        "farms": [{
            "farmer": [0, 0],
            "hands": [],
            "money": 1000,
            "tiles": [[tile]],
        }],
    }


def test_ready_crop_replaces_idle_route_action():
    result = apply_urgent_jobs(_obs({"kind": "PLANT", "yield_units": 2}), {
        "farmer": ["EAST"], "hands": [], "market": []
    })
    assert result["farmer"] == ["HARVEST"]


def test_unwatered_crop_replaces_pass():
    result = apply_urgent_jobs(_obs({"kind": "PLANT", "yield_units": 0, "watered_today": False}), {
        "farmer": ["PASS"], "hands": [], "market": []
    })
    assert result["farmer"] == ["WATER"]


def test_loaded_actor_is_not_reassigned():
    result = apply_urgent_jobs(_obs({"kind": "PLANT", "yield_units": 2}, {"MELON": 1}), {
        "farmer": ["PASS"], "hands": [], "market": []
    })
    assert result["farmer"] == ["PASS"]
