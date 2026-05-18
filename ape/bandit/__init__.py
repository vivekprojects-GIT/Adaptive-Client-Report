"""Bandit package — UCB selection from cached_ucb + reward computation."""

from .selection import (
    select_strategy_from_rows,
    build_selection_payload,
)
from .reward import compute_rewards

__all__ = [
    "select_strategy_from_rows",
    "build_selection_payload",
    "compute_rewards",
]
