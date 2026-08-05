import pytest


def test_official_sdk_can_create_environment():
    make = pytest.importorskip("kaggle_environments").make
    env = make("kaggriculture", configuration={"episodeSteps": 2, "seed": 0})
    assert env.name == "kaggriculture"

