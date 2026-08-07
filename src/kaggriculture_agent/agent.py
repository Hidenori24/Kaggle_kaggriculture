from __future__ import annotations

from typing import Any

from .pass_repair_policy import agent as choose_adaptive_action


def kaggriculture_agent(obs: Any, configuration: Any = None) -> dict[str, Any]:
    """Kaggle-compatible entry point for the PASS-repair experiment."""
    return choose_adaptive_action(obs)
