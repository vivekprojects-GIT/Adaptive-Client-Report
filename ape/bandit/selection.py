"""
Strategy selection — round-robin → UCB (ported from vg_mvp_v1.0).

Per the MVP1 spec: every candidate strategy is pulled at least once before
UCB starts trading off exploration vs exploitation.

Selection rule:
  1. ROUND-ROBIN cold start — walk `rows` in input order and return the
     first arm whose count == 0. The caller is responsible for feeding
     rows in the catalog/policy order it wants visited (the orchestrator
     reorders rows to match the candidate_strategies list).
  2. UCB — once every arm has count >= 1, pick the row with the highest
     UCB1 score computed LIVE from (count, total_reward, N).
     Ties broken deterministically by strategy name so the same state
     always picks the same arm.

`count` is a PULL counter — the store bumps it at selection time (Path A),
not at reward time. `total_reward` accumulates on Path B. avg = total/count.

`cached_ucb` is no longer consulted by selection (it's recomputed after each
pull/reward purely for the admin/analytics display, which sorts arms by it).
For unpulled arms UCB is mathematically undefined; compute_ucb returns +inf
as a safety net, but round-robin handles those before UCB ever runs.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


# ----------------------------------------------------------------------------
# Pure UCB1 helper — used by select_strategy_from_rows AND by the store's
# cache refresh + read-side endpoints that show the current score per arm.
# ----------------------------------------------------------------------------

# ── UCB formula parameters (admin-tunable at runtime) ────────────────────────
# The full score is:
#     ucb = avg_reward + c * width * sqrt( 2 * ln(N) / count )
#
#   width (REWARD_RANGE_WIDTH) — reward range (b-a). Rewards span [-2, +2] so
#     the default is 4; this Hoeffding correction keeps the bonus on the same
#     scale as the rewards (textbook UCB1 assumes width 1).
#   c (UCB_EXPLORATION_C) — exploration constant. c=1 is textbook-balanced
#     (explore-heavy on this scale); c<1 commits to the learned winner faster
#     (more exploitation), which suits sparse human feedback.
#
# These are DEFAULTS. The live values live in `_ucb_params` and are refreshed
# from the admin config (bandit_config/ucb in MongoDB) at startup and whenever
# the admin updates them via POST /config/ucb — no redeploy needed. Selection
# and the display cache both read get_ucb_params(), so they never diverge.
REWARD_RANGE_WIDTH = 4.0
UCB_EXPLORATION_C = 1.0

_ucb_params = {"c": UCB_EXPLORATION_C, "width": REWARD_RANGE_WIDTH}


def set_ucb_params(c: float | None = None, width: float | None = None) -> dict:
    """Update the live UCB parameters (called on startup + admin edits)."""
    if c is not None:
        _ucb_params["c"] = float(c)
    if width is not None:
        _ucb_params["width"] = float(width)
    return dict(_ucb_params)


def get_ucb_params() -> dict:
    """Current live UCB parameters: {"c": float, "width": float}."""
    return dict(_ucb_params)


def compute_ucb(count: int, total_reward: float, n_total: int) -> float:
    """UCB1 score for one arm.

      ucb(arm) = avg_reward(arm) + c * width * sqrt( 2 * ln(N) / count(arm) )

    where N is the sum of counts across ALL arms in the cell, and (c, width)
    are the live admin-tunable parameters (see get_ucb_params). With c=1 and
    width=1 this reduces to textbook UCB1.

    Edge cases:
      count == 0   → +inf. The arm is unpulled. Round-robin should have
                     picked it before we got here; +inf is a safety net so
                     argmax(ucb) still selects it.
      n_total <= 0 → return avg only (no log(0)) — completely cold cell,
                     round-robin handles it before UCB runs.
    """
    if count == 0:
        return float("inf")
    avg = total_reward / count
    if n_total <= 0:
        return avg
    c = _ucb_params["c"]
    width = _ucb_params["width"]
    return avg + c * width * math.sqrt(2.0 * math.log(n_total) / count)


def _cell_n_total(rows: List[Dict[str, Any]]) -> int:
    """Sum of counts across all arms in the cell — the N in UCB1."""
    return sum(int(r.get("count", 0)) for r in rows)


# ----------------------------------------------------------------------------
# Selection — round-robin first, then live-UCB argmax
# ----------------------------------------------------------------------------

def select_strategy_from_rows(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Pick one arm. Returns None if `rows` is empty.

    Each row must contain at least: strategy, count, total_reward.
    """
    if not rows:
        return None

    # 1) Round-robin cold start — first unpulled arm in input order wins.
    for r in rows:
        if int(r.get("count", 0)) == 0:
            return r

    # 2) UCB — compute live from (count, total_reward, N). Tie-break on
    #    strategy name for determinism.
    n_total = _cell_n_total(rows)
    return max(
        rows,
        key=lambda r: (
            compute_ucb(
                int(r.get("count", 0)),
                float(r.get("total_reward", 0.0)),
                n_total,
            ),
            -ord_str(r["strategy"]),
        ),
    )


def build_selection_payload(
    rows: List[Dict[str, Any]],
    selected_row: Dict[str, Any],
    candidate_strategies: List[str],
    policy_version: str,
) -> Dict[str, Any]:
    """Build the dict returned by Path A to be persisted on the response record.

    `ucb_at_selection` is computed live — the score the bandit saw at the
    moment of picking, captured for replayable audit. Round-robin picks
    have ucb = +inf which we serialize as 0.0 (the UCB value didn't matter
    for the pick — round-robin overrides UCB).
    """
    n_total = _cell_n_total(rows)
    raw_ucb = compute_ucb(
        int(selected_row.get("count", 0)),
        float(selected_row.get("total_reward", 0.0)),
        n_total,
    )
    selection_ucb = raw_ucb if math.isfinite(raw_ucb) else 0.0

    return {
        "selected_strategy":     selected_row["strategy"],
        "selection_method":      "round_robin" if int(selected_row.get("count", 0)) == 0
                                  else "ucb",
        "ucb_at_selection":      float(selection_ucb),
        "count_at_selection":    int(selected_row.get("count", 0)),
        "policy_version":        policy_version,
        "strategies_available":  candidate_strategies,
        # Per-arm breakdown for audit/debug — live computed, not cached.
        # ("cached_ucb" key kept as an alias for older UI readers.)
        "score_breakdown":       {
            r["strategy"]: {
                "count":      int(r.get("count", 0)),
                "avg_reward": float(r.get("avg_reward", 0.0)),
                "ucb":        _safe_finite(compute_ucb(
                    int(r.get("count", 0)),
                    float(r.get("total_reward", 0.0)),
                    n_total,
                )),
                "cached_ucb": _safe_finite(compute_ucb(
                    int(r.get("count", 0)),
                    float(r.get("total_reward", 0.0)),
                    n_total,
                )),
            }
            for r in rows
        },
    }


def _safe_finite(x: float) -> float:
    """Serialize +inf as 0.0 — JSON has no infinity literal."""
    return x if math.isfinite(x) else 0.0


def ord_str(s: str) -> int:
    """Convert a string to a comparable int for stable tie-breaking."""
    return sum(ord(c) for c in (s or ""))
