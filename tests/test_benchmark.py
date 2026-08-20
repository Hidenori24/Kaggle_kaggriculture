from types import SimpleNamespace

from scripts.benchmark import _diagnostics


def _observation(*, shed_units, animals, day=10):
    return {
        "hour": 0,
        "day": day,
        "private": {"shed": {"WHEAT": shed_units}},
        "farms": [
            {"tiles": [[{"animal": "COW"}]]},
            {"tiles": [[{"animal": "SHEEP"}] * animals]},
        ],
    }


def test_benchmark_diagnostics_use_the_requested_seat():
    steps = [[
        {"observation": _observation(shed_units=7, animals=1)},
        {"observation": _observation(shed_units=83, animals=4)},
    ]]

    result = _diagnostics(SimpleNamespace(steps=steps), seat=1)

    assert result == {
        "peak_shed_units": 83,
        "final_animals": 4,
        "min_animals_after_day10": 4,
    }
