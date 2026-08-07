from __future__ import annotations

from typing import Any

from .adaptive_policy import agent as choose_adaptive_action


def kaggriculture_agent(obs: Any, configuration: Any = None) -> dict[str, Any]:
    """Kaggle-compatible entry point for the validated adaptive candidate."""
    return choose_adaptive_action(obs)
