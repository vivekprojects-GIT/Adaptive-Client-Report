"""
UCB strategy selection (production design).

Reads `cached_ucb` from each bandit_state document. Cached UCB is the serving
cache; format_count + total_reward + avg_reward are the source of truth.

After each reward, Path B refreshes cached_ucb for every strategy in the cell
(because the explore bonus depends on N = sum of counts).

Selection rule:
  1. If ANY strategy has count = 0 → it's flagged cold-start with a very
     high cached_ucb (default 999.0), so unpulled arms naturally win first.
  2. Otherwise → argmax(cached_ucb).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def select_strategy_from_rows(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Pick the row with the highest cached_ucb. Returns None if rows is empty.

    Each row must contain at least: strategy, count, avg_reward, cached_ucb.
    Sorted deterministically — ties broken by 'strategy' name to keep selection
    reproducible.
    """
    if not rows:
        return None
    best = max(rows, key=lambda r: (float(r.get("cached_ucb", 0.0)), -ord_str(r["strategy"])))
    return best


def build_selection_payload(
    rows: List[Dict[str, Any]],
    selected_row: Dict[str, Any],
    candidate_strategies: List[str],
    policy_version: str,
) -> Dict[str, Any]:
    """Build the dict returned by Path A to be persisted on the response record."""
    return {
        "selected_strategy":     selected_row["strategy"],
        "selection_method":      "ucb",
        "ucb_at_selection":      float(selected_row.get("cached_ucb", 0.0)),
        "count_at_selection":    int(selected_row.get("count", 0)),
        "policy_version":        policy_version,
        "strategies_available":  candidate_strategies,
        "score_breakdown":       {
            r["strategy"]: {
                "count":      int(r.get("count", 0)),
                "avg_reward": float(r.get("avg_reward", 0.0)),
                "cached_ucb": float(r.get("cached_ucb", 0.0)),
            }
            for r in rows
        },
    }


def ord_str(s: str) -> int:
    """Convert a string to a comparable int for stable tie-breaking."""
    return sum(ord(c) for c in (s or ""))
