"""
Reward computation — convert a resolved signal into per-axis rewards.

Pure function. Reads SIGNAL_ROUTING and REWARD_SCALE; no DB access.

Returns:
  (content_relevant, format_relevant, content_reward, format_reward)

Where each reward is an int in {-2, -1, +1, +2} or None (NOT_RECORDED).
"""

from __future__ import annotations

from typing import Optional, Tuple

from ..signals import SIGNAL_ROUTING, REWARD_SCALE


def compute_rewards(signal: str) -> Tuple[bool, bool, Optional[int], Optional[int]]:
    """Look up a signal's (content_relevant, format_relevant, content_reward, format_reward).

    Unknown signals fall back to "no_signal" semantics — both axes
    NOT_RECORDED, no bandit update should occur.
    """
    entry = SIGNAL_ROUTING.get(signal, SIGNAL_ROUTING["no_signal"])
    format_strength, content_strength = entry

    format_reward = REWARD_SCALE.get(format_strength)
    content_reward = REWARD_SCALE.get(content_strength)

    return (
        content_strength is not None,   # content_relevant
        format_strength is not None,    # format_relevant
        content_reward,
        format_reward,
    )
