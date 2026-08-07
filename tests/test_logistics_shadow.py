from kaggriculture_agent.logistics_shadow import diagnose_step, summarize_diagnostics


def _obs():
    return {
        "player": 0,
        "step": 10,
        "day": 0,
        "hour": 10,
        "farms": [
            {
                "money": 1234,
                "farmer": [4, 4],
                "hands": [[3, 4]],
                "hires_today": 1,
                "unlocked_quadrants": ["NW"],
                "tiles": [[None for _ in range(10)] for _ in range(10)],
            },
            {},
        ],
        "private": {
            "shed": {"MELON": 2},
            "inventories": [{"MELON": 1}, {}],
            "seeds": {"MELON": 2},
        },
    }


def test_diagnose_step_is_json_serializable():
    row = diagnose_step(_obs(), {"farmer": ["PASS"], "hands": [["PASS"]], "market": []})
    assert row["money"] == 1234
    assert row["inventory_total"] == 1
    assert row["shed_total"] == 2
    assert row["shadow_error"] is None
    assert "carrying_inventory" in row["bottlenecks"]


def test_summary_groups_phases_and_counts_differences():
    rows = [
        {"day": 0, "action_differs": True, "shadow_error": None, "money": 100, "inventory_total": 1, "shed_total": 0, "hands": 1, "unlocked_quadrants": ["NW"], "actual_counts": {"PASS": 1}, "shadow_counts": {}, "bottlenecks": ["carrying_inventory"]},
        {"day": 12, "action_differs": False, "shadow_error": None, "money": 200, "inventory_total": 0, "shed_total": 2, "hands": 2, "unlocked_quadrants": ["NW", "NE"], "actual_counts": {}, "shadow_counts": {}, "bottlenecks": []},
    ]
    summary = summarize_diagnostics(rows)
    assert summary["steps"] == 2
    assert summary["different_steps"] == 1
    assert [item["phase"] for item in summary["phase_summary"]] == ["early", "growth"]
    assert summary["phase_summary"][0]["actual_action_counts"] == {"PASS": 1}
    assert summary["phase_summary"][0]["bottleneck_counts"] == {"carrying_inventory": 1}
