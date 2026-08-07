"""Low-risk adaptive layer around the validated replay policy.

The replay-derived policy remains the source of all normal actions. This module
only changes the market queue during the final day of the season so products
left in the shed are sold before the terminal state is scored.
"""

from __future__ import annotations

from typing import Any

from .replay_policy import _ACTIONS, _safe_market, _step, _terminal_market
from .replay_policy import agent as replay_agent

SEASON_STEPS = len(_ACTIONS)
ENDGAME_START_STEP = max(0, SEASON_STEPS - 24)


def agent(obs: Any) -> dict[str, Any]:
    """Return the validated action with a final-day sell safeguard."""
    action = replay_agent(obs)
    if _step(obs) >= ENDGAME_START_STEP:
        action = _terminal_market(obs, action)
        action = _safe_market(obs, action)
    return action


def _kaggle_submission_entrypoint(obs: Any) -> dict[str, Any]:
    return agent(obs)
