from kaggriculture_agent.logistics_state import extract_state, job_candidates, resource_plan


def _observation():
    return {
        "step": 48,
        "day": 2,
        "player": 0,
        "private": {
            "shed": {"WHEAT": 3, "FERTILIZER": 1},
            "seeds": {"WHEAT": 4},
            "inventories": [{}, {"WHEAT": 1}],
        },
        "market": {"prices": {"WHEAT": 30, "CARROT": 40}},
        "farms": [{
            "money": 500,
            "hands": [[1, 0]],
            "farmer": [0, 0],
            "unlocked_quadrants": ["NW"],
            "tiles": [[
                {"kind": "PLANT", "yield_units": 2},
                {"animal": "COW", "fed_today": False, "cared_today": False},
            ]],
        }],
    }


def test_extract_state_counts_resources_and_units():
    state = extract_state(_observation())
    assert state.animals == 1
    assert state.shed_units == 4
    assert state.units[1].inventory_units == 1
    assert state.unlocked_quadrants == ("NW",)


def test_resource_plan_reserves_feed_and_reports_shed_room():
    plan = resource_plan(extract_state(_observation()), horizon_days=3)
    assert plan["feed_required"] == 3
    assert plan["feed_deficit"] == 1
    assert plan["shed_free"] == 96


def test_job_candidates_prioritise_harvest_before_other_local_jobs():
    jobs = job_candidates(_observation())
    assert jobs[0].kind == "HARVEST"
    assert {job.kind for job in jobs} == {"HARVEST", "FEED"}


def test_job_candidates_are_deterministically_sorted():
    first = job_candidates(_observation())
    second = job_candidates(_observation())
    assert first == second
