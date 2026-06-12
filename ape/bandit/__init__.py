"""Bandit package — round-robin → live-UCB1 selection + reward computation."""

import math

from .selection import (
    select_strategy_from_rows,
    build_selection_payload,
    compute_ucb,
)
from .reward import compute_rewards
from ..strategies import INTENT_STRATEGIES


def select_strategy(cell, intent, exploration_constant=1.0):
    """Legacy SQLite test helper for selecting from an in-memory bandit cell."""
    strategies = INTENT_STRATEGIES[intent]
    rows = cell.get("strategies", {})
    total_pulls = sum(int(rows.get(s, {}).get("format_count", 0)) for s in strategies)

    best_strategy = None
    best_score = float("-inf")
    breakdown = {}
    for strategy in strategies:
        state = rows.get(strategy, {})
        count = int(state.get("format_count", 0))
        avg_reward = float(state.get("format_avg_reward", 0.0))
        if count == 0:
            score = 999.0
        else:
            explore = exploration_constant * math.sqrt(math.log(max(total_pulls, 1)) / count)
            score = avg_reward + explore
        breakdown[strategy] = {
            "count": count,
            "avg_reward": avg_reward,
            "ucb": score,
        }
        if score > best_score:
            best_strategy = strategy
            best_score = score

    return {
        "selected_strategy": best_strategy,
        "selection_method": "ucb",
        "ucb_at_selection": best_score,
        "score_breakdown": breakdown,
    }

__all__ = [
    "select_strategy",
    "select_strategy_from_rows",
    "build_selection_payload",
    "compute_rewards",
]
