from kaggriculture_agent.macro_transport import apply_transport_plans, build_transport_plans


def _obs(inventory, position=(0, 0), shed_units=0):
    return {
        "step": 10,
        "day": 0,
        "player": 0,
        "private": {"shed": {"WHEAT": shed_units}, "inventories": [inventory]},
        "farms": [{
            "money": 1000,
            "farmer": list(position),
            "hands": [],
            "tiles": [[None] * 10 for _ in range(10)],
        }],
    }


def test_plan_routes_safe_cargo_toward_nearest_shed_access():
    obs = _obs({"MILK": 1}, position=(0, 0))
    base = {"farmer": ["PASS"], "hands": [], "market": []}
    plans = build_transport_plans(obs, base)
    assert len(plans) == 1
    assert plans[0].target == (4, 4)
    assert plans[0].next_action == ("EAST",)
    assert apply_transport_plans(obs, base)["farmer"] == ["EAST"]


def test_plan_drops_only_after_arriving_at_shed_access():
    obs = _obs({"MILK": 1}, position=(4, 4))
    base = {"farmer": ["PASS"], "hands": [], "market": []}
    assert build_transport_plans(obs, base)[0].next_action == ("DROP",)
    assert apply_transport_plans(obs, base)["farmer"] == ["DROP"]


def test_plan_does_not_interrupt_non_pass_or_overfill_shed():
    obs = _obs({"MILK": 1}, position=(0, 0), shed_units=100)
    assert build_transport_plans(obs, {"farmer": ["PASS"], "hands": [], "market": []}) == ()
    obs = _obs({"MILK": 1}, position=(0, 0))
    assert build_transport_plans(obs, {"farmer": ["HARVEST"], "hands": [], "market": []}) == ()
