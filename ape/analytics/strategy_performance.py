"""
Strategy performance — admin diagnostic to answer:

  • Which strategies are winning across the whole user base?
  • For one specific user, which strategies work for them?
  • Which strategies have enough data to trust, and which are still cold-start?

Performance tier (0-100 scale, mapped from avg_reward ∈ [-1, +1]):
    performance_pct = (avg_reward + 1) / 2 × 100

  HIGH       performance_pct ≥ 80    (avg_reward ≥ 0.60)
  MEDIUM     50 ≤ performance_pct < 80
  LOW        performance_pct < 50    (avg_reward < 0.00)
  EXPLORING  total_pulls < min_pulls (insufficient data to tier)

This gives the admin a clear signal:
  HIGH  → keep, maybe promote
  MEDIUM → refine instruction
  LOW   → consider pausing or rewriting
  EXPLORING → wait for more data
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from ..store import MongoStore


# Tier thresholds on the 0-100 scale
HIGH_THRESHOLD   = 80.0
MEDIUM_THRESHOLD = 50.0
DEFAULT_MIN_PULLS_FOR_TIER = 3   # avoid noisy tiering on tiny samples


def _tier_for(performance_pct: float, total_pulls: int, min_pulls: int) -> str:
    if total_pulls < min_pulls:
        return "EXPLORING"
    if performance_pct >= HIGH_THRESHOLD:
        return "HIGH"
    if performance_pct >= MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def _aggregate(
    rows: List[Dict[str, Any]],
    min_pulls: int,
) -> Dict[str, Dict[str, Any]]:
    """Group bandit_state rows by strategy → return summary per strategy."""
    by_strategy: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        s = r.get("strategy")
        if not s:
            continue
        cnt = int(r.get("count", 0))
        if cnt < 1:
            continue
        avg = float(r.get("avg_reward", 0.0))

        e = by_strategy.setdefault(s, {
            "strategy":      s,
            "total_pulls":   0,
            "total_reward":  0.0,
            "unique_users":  set(),
            "unique_cells":  set(),
            "cell_rewards":  [],   # for picking best-cell + intent/topic breakdown
        })
        e["total_pulls"]  += cnt
        e["total_reward"] += avg * cnt
        if r.get("user_id_hash"):
            e["unique_users"].add(r["user_id_hash"])
        cell_key = (r.get("intent"), r.get("topic"))
        e["unique_cells"].add(cell_key)
        e["cell_rewards"].append({
            "intent":     r.get("intent"),
            "topic":      r.get("topic"),
            "count":      cnt,
            "avg_reward": avg,
        })

    # Compute derived stats + tier
    out: Dict[str, Dict[str, Any]] = {}
    for s, e in by_strategy.items():
        pulls = e["total_pulls"]
        if pulls == 0:
            continue
        avg = e["total_reward"] / pulls
        perf = round(((avg + 1.0) / 2.0) * 100, 1)

        # Best cell — where this strategy is most effective
        best = max(e["cell_rewards"], key=lambda c: c["avg_reward"]) if e["cell_rewards"] else None
        # Worst cell — where it bombs (admin signal to refine)
        worst = min(e["cell_rewards"], key=lambda c: c["avg_reward"]) if e["cell_rewards"] else None

        out[s] = {
            "strategy":        s,
            "total_pulls":     pulls,
            "avg_reward":      round(avg, 3),
            "performance_pct": perf,
            "tier":            _tier_for(perf, pulls, min_pulls),
            "unique_users":    len(e["unique_users"]),
            "unique_cells":    len(e["unique_cells"]),
            "best_cell": (
                {
                    "intent": best["intent"], "topic": best["topic"],
                    "avg_reward": round(best["avg_reward"], 3), "count": best["count"],
                } if best else None
            ),
            "worst_cell": (
                {
                    "intent": worst["intent"], "topic": worst["topic"],
                    "avg_reward": round(worst["avg_reward"], 3), "count": worst["count"],
                } if worst else None
            ),
        }
    return out


def compute_strategy_performance(
    store: MongoStore,
    user_id_hash: Optional[str] = None,
    domain: Optional[str] = None,
    min_pulls: int = DEFAULT_MIN_PULLS_FOR_TIER,
) -> Dict[str, Any]:
    """Return global + (optionally) per-user strategy performance summary.

    Sorted within each scope: by tier (HIGH > MEDIUM > LOW > EXPLORING),
    then by avg_reward × log(pulls) (popularity-weighted reward).
    """
    # --- Global aggregate (ALL users) ---
    global_q: Dict[str, Any] = {"count": {"$gt": 0}}
    if domain:
        global_q["domain"] = domain
    global_rows = list(store.bandit_state.find(global_q))
    global_by_strategy = _aggregate(global_rows, min_pulls=min_pulls)

    # --- Per-user aggregate (filter the same rows) ---
    per_user_by_strategy: Optional[Dict[str, Dict[str, Any]]] = None
    if user_id_hash:
        user_rows = [r for r in global_rows if r.get("user_id_hash") == user_id_hash]
        per_user_by_strategy = _aggregate(user_rows, min_pulls=min_pulls)

    def sort_key(s: Dict[str, Any]) -> tuple:
        tier_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "EXPLORING": 3}
        return (
            tier_order.get(s["tier"], 9),
            -s["avg_reward"] * math.log(s["total_pulls"] + 1),
        )

    return {
        "tier_thresholds": {
            "high":   HIGH_THRESHOLD,
            "medium": MEDIUM_THRESHOLD,
            "min_pulls_for_tier": min_pulls,
        },
        "global": sorted(global_by_strategy.values(), key=sort_key),
        "per_user": (
            sorted(per_user_by_strategy.values(), key=sort_key)
            if per_user_by_strategy is not None else None
        ),
        "user_id_hash": user_id_hash,
    }
