Exit code: 0
Wall time: 1 seconds
Output:
from __future__ import annotations

from typing import Any

from .strategy import BaselineConfig, choose_action


def kaggriculture_agent(obs: Any, configuration: Any = None) -> dict[str, Any]:
    """Kaggle-compatible agent entry point."""
    return choose_action(obs, BaselineConfig())

