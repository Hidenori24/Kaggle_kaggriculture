from __future__ import annotations

from typing import Any

from .replay_policy import agent as choose_replay_action


def kaggriculture_agent(obs: Any, configuration: Any = None) -> dict[str, Any]:
    """Kaggle-compatible entry point for the validated replay-derived policy."""
    return choose_replay_action(obs)
