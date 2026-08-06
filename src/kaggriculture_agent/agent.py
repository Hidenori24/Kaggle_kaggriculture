from __future__ import annotations

from typing import Any

from .full_strategy import choose_action as choose_full_action
from .strategy import BaselineConfig, choose_action as choose_baseline_action


FULL_POLICY_START_DAY = 24


def kaggriculture_agent(obs: Any, configuration: Any = None) -> dict[str, Any]:
    """Kaggle-compatible agent entry point."""
    day = int(obs.get("day", 0) if isinstance(obs, dict) else getattr(obs, "day", 0) or 0)
    if day < FULL_POLICY_START_DAY:
        return choose_baseline_action(obs, BaselineConfig(enable_expansion=False))
    return choose_full_action(obs)

