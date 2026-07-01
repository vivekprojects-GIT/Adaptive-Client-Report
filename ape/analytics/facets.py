"""
Cognitive facets — rich per-cell view for the analytics dashboard.

A "facet" is one (intent, topic) cell in a user's bandit. For each facet we
expose:
  - interaction_count           total format_count across strategies
  - leading_strategy + α, β     highest-avg strategy with Beta(α, β) approximation
  - runner_up_strategy + α, β   second-highest
  - confidence_score            0..100 (informally; based on count + reward gap)
  - confidence_tier             HIGH / MODERATE / LOW
  - insight_text                short auto-generated description
  - last_activity_ts            most recent turn in this cell

Beta parameter approximation:
  - We track avg_reward in [-1, +1] (normalized reward axis).
  - To visualize as Beta(α, β): treat each pull as a Bernoulli trial where
    success_prob = (avg_reward + 1) / 2 ∈ [0, 1].
    α = round(count × success_prob)
    β = count - α
  - This is a *visualization* device, not a re-derivation of the bandit math.
    The underlying UCB statistics are unchanged.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..bandit.selection import display_selection_score
from ..store import MongoStore


# Confidence bucketing thresholds (interaction_count, confidence_score)
HIGH_TIER     = {"min_interactions": 10, "min_score": 75}
MODERATE_TIER = {"min_interactions":  4, "min_score": 50}


def compute_cognitive_facets(
    store: MongoStore,
    user_id_hash: Optional[str] = None,
    domain: Optional[str] = None,
    min_interactions: int = 1,
) -> List[Dict[str, Any]]:
    """Build the per-(intent, topic) facet view.

    Scope:
      - user_id_hash != None  → per-user view (one user's bandit cells)
      - user_id_hash is None  → GLOBAL view: aggregate every user's bandit_state
                                rows together per (intent, topic, strategy).
                                Each facet then carries an extra `unique_users`
                                count so admin sees how many people contributed.

    Returns rows sorted by confidence_score descending.
    """
    is_global = user_id_hash is None
    q: Dict[str, Any] = {}
    if user_id_hash:
        q["user_id_hash"] = user_id_hash
    if domain:
        q["domain"] = domain

    raw_rows = list(store.bandit_state.find(q))
    if not raw_rows:
        return []

    # ----- GLOBAL: keep raw rows for the contributor list, but also aggregate
    # per (domain, intent, topic, strategy) for the leader/runner-up math.
    # ------------------------------------------------------------------
    # cell_contributors[(domain, intent, topic)] = {user_hash: {pulls, best_strategy, ...}}
    cell_contributors: Dict[tuple, Dict[str, Dict[str, Any]]] = {}

    if is_global:
        aggregated: Dict[tuple, Dict[str, Any]] = {}
        users_per_strategy: Dict[tuple, set] = {}
        for r in raw_rows:
            key = (r["domain"], r["intent"], r["topic"], r["strategy"])
            cell_key = (r["domain"], r["intent"], r["topic"])
            cnt = int(r.get("count", 0))
            if cnt == 0:
                continue
            tot = float(r.get("total_reward", 0.0))
            avg = float(r.get("avg_reward", 0.0))
            uh  = r.get("user_id_hash")

            # ---- aggregate by (cell, strategy) for the leader math ----
            if key not in aggregated:
                aggregated[key] = {
                    "domain":       r["domain"],
                    "intent":       r["intent"],
                    "topic":        r["topic"],
                    "strategy":     r["strategy"],
                    "count":        0,
                    "total_reward": 0.0,
                    "last_updated_at": "",
                }
                users_per_strategy[key] = set()
            aggregated[key]["count"]        += cnt
            aggregated[key]["total_reward"] += tot
            ts = r.get("last_updated_at") or ""
            if ts > aggregated[key]["last_updated_at"]:
                aggregated[key]["last_updated_at"] = ts
            if uh:
                users_per_strategy[key].add(uh)

            # ---- contributor accumulator per cell ----
            if uh:
                contribs = cell_contributors.setdefault(cell_key, {})
                u = contribs.setdefault(uh, {
                    "user_id_hash":   uh,
                    "pulls_in_cell":  0,
                    "best_strategy":  None,
                    "best_strategy_count": 0,
                    "best_strategy_avg_reward": -2.0,   # ensure first update wins
                    "last_active":    "",
                })
                u["pulls_in_cell"] += cnt
                # The user's "best" strategy in this cell = the row with the
                # highest avg_reward they contributed to. If tied on reward,
                # prefer the one with more pulls.
                if (avg > u["best_strategy_avg_reward"] or
                    (avg == u["best_strategy_avg_reward"] and cnt > u["best_strategy_count"])):
                    u["best_strategy"]            = r["strategy"]
                    u["best_strategy_count"]      = cnt
                    u["best_strategy_avg_reward"] = round(avg, 3)
                if ts > u["last_active"]:
                    u["last_active"] = ts

        rows = []
        for key, agg in aggregated.items():
            cnt = agg["count"]
            agg["avg_reward"] = round(agg["total_reward"] / cnt, 4) if cnt else 0.0
            agg["cached_ucb"] = 0.0   # not used in facet rendering
            agg["_unique_users_for_strategy"] = len(users_per_strategy[key])
            rows.append(agg)

        # Resolve display names in bulk from the directory
        all_user_hashes = {uh for contribs in cell_contributors.values() for uh in contribs}
        name_map = store.get_display_names(all_user_hashes)
        for contribs in cell_contributors.values():
            for uh, u in contribs.items():
                u["display_name"] = name_map.get(uh, uh)
    else:
        rows = raw_rows

    # Group by (domain, intent, topic)
    cells: Dict[tuple, List[Dict[str, Any]]] = {}
    for r in rows:
        key = (r["domain"], r["intent"], r["topic"])
        cells.setdefault(key, []).append(r)

    facets: List[Dict[str, Any]] = []
    for (d, intent, topic), strategy_rows in cells.items():
        # Only consider strategies with actual pulls
        pulled = [r for r in strategy_rows if int(r.get("count", 0)) > 0]
        if not pulled:
            continue

        total_count = sum(int(r["count"]) for r in pulled)
        if total_count < min_interactions:
            continue

        # Sort by avg_reward descending
        pulled.sort(key=lambda r: -float(r.get("avg_reward", 0.0)))
        leading = pulled[0]
        runner_up = pulled[1] if len(pulled) > 1 else None

        # Confidence score: combines volume + lead gap
        # volume_factor ∈ [0,1]: capped at 20 interactions for full credit
        volume_factor = min(total_count / 20.0, 1.0)
        # gap_factor ∈ [0,1]: how clearly the leader beats runner-up
        if runner_up is not None:
            gap = abs(leading["avg_reward"] - runner_up["avg_reward"])
            gap_factor = min(gap, 1.0)
        else:
            gap_factor = 0.5   # only one strategy tried — neutral
        # leader_strength ∈ [0,1]: positive avg = stronger evidence
        leader_strength = max(0.0, (leading["avg_reward"] + 1.0) / 2.0)

        confidence_score = round(100 * (
            0.4 * volume_factor +
            0.3 * gap_factor +
            0.3 * leader_strength
        ))

        if total_count >= HIGH_TIER["min_interactions"] and confidence_score >= HIGH_TIER["min_score"]:
            tier = "HIGH"
        elif total_count >= MODERATE_TIER["min_interactions"] and confidence_score >= MODERATE_TIER["min_score"]:
            tier = "MODERATE"
        else:
            tier = "LOW"

        # Beta(α, β) approximation for the leader and runner-up
        leading_ab  = _beta_params(leading)
        runner_ab   = _beta_params(runner_up) if runner_up else None

        # Insight text generation
        insight = _generate_insight(intent, topic, leading, runner_up, total_count)

        # Most recent activity
        last_ts = max((r.get("last_updated_at") or "") for r in strategy_rows)

        # In global mode each row carries _unique_users_for_strategy; union
        # those into a single "unique_users" count for the cell.
        cell_unique_users = None
        contributors: Optional[List[Dict[str, Any]]] = None
        if is_global:
            cell_key = (d, intent, topic)
            cell_unique_users = len(cell_contributors.get(cell_key, {}))
            # Sort contributors by pulls_in_cell desc — the most-active first
            contributors = sorted(
                cell_contributors.get(cell_key, {}).values(),
                key=lambda u: (-u["pulls_in_cell"], u["display_name"]),
            )

        facets.append({
            "scope":              "global" if is_global else "user",
            "domain":             d,
            "intent":             intent,
            "topic":              topic,
            "facet_name":         _facet_name(intent, topic),
            "interaction_count":  total_count,
            "unique_users":       cell_unique_users,   # null in per-user mode
            "contributors":       contributors,         # null in per-user mode
            "confidence_score":   confidence_score,
            "confidence_tier":    tier,
            "leading_strategy":   {
                "name":  leading["strategy"],
                "count": int(leading["count"]),
                "avg_reward": round(float(leading["avg_reward"]), 3),
                "alpha":       leading_ab["alpha"],
                "beta":        leading_ab["beta"],
                "unique_users": leading.get("_unique_users_for_strategy"),
            },
            "runner_up_strategy": ({
                "name":  runner_up["strategy"],
                "count": int(runner_up["count"]),
                "avg_reward": round(float(runner_up["avg_reward"]), 3),
                "alpha":       runner_ab["alpha"],
                "beta":        runner_ab["beta"],
                "unique_users": runner_up.get("_unique_users_for_strategy"),
            } if runner_up is not None else None),
            "insight_text":       insight,
            "last_activity_ts":   last_ts,
            "all_strategies":     [
                {
                    "name":       r["strategy"],
                    "count":      int(r["count"]),
                    "avg_reward": round(float(r["avg_reward"]), 3),
                    # Live selection score (no cache) — computed from the cell's
                    # N (total_count) with the current c/width params.
                    "cached_ucb": display_selection_score(
                        int(r["count"]),
                        float(r.get("total_reward", float(r["avg_reward"]) * int(r["count"]))),
                        total_count,
                    ),
                    "unique_users": r.get("_unique_users_for_strategy"),
                }
                for r in pulled
            ],
        })

    facets.sort(key=lambda f: -f["confidence_score"])
    return facets


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _beta_params(row: Optional[Dict[str, Any]]) -> Dict[str, int]:
    """Approximate Beta(α, β) from (count, avg_reward).

    Maps avg_reward ∈ [-1, +1] to success_prob ∈ [0, 1], then splits the
    pull count into successes (α) and failures (β). Rounded to integers
    so the BETA(α, β) label reads cleanly.
    """
    if row is None:
        return {"alpha": 1, "beta": 1}
    count = int(row["count"])
    p_success = max(0.0, min(1.0, (float(row["avg_reward"]) + 1.0) / 2.0))
    alpha = max(1, round(count * p_success))
    beta  = max(1, count - alpha + 1)   # the +1 keeps β >= 1 even if all wins
    # Re-balance so α + β ≈ count + 2 (so the curve still has a real shape)
    return {"alpha": alpha, "beta": beta}


def _facet_name(intent: str, topic: str) -> str:
    """Human-readable name combining intent + topic."""
    pretty_intent = intent.replace("_", " ").title()
    pretty_topic  = topic.replace("_", " ").title() if topic and topic != "general" else None
    if pretty_topic:
        return f"{pretty_intent}: {pretty_topic}"
    return pretty_intent


def _generate_insight(
    intent: str,
    topic: str,
    leading: Dict[str, Any],
    runner_up: Optional[Dict[str, Any]],
    total: int,
) -> str:
    """Auto-generated qualitative description of this cell's pattern."""
    lead_name = leading["strategy"].replace("_", " ")
    avg = float(leading["avg_reward"])

    if avg > 0.7:
        tone = f"Strong preference for {lead_name}"
    elif avg > 0.3:
        tone = f"Tends toward {lead_name}"
    elif avg > -0.3:
        tone = f"Mixed signal on {lead_name}"
    else:
        tone = f"Negative response to {lead_name}"

    follow = ""
    if runner_up is not None:
        runner_name = runner_up["strategy"].replace("_", " ")
        gap = float(leading["avg_reward"]) - float(runner_up["avg_reward"])
        if gap > 0.5:
            follow = f" — clearly outperforms {runner_name}."
        elif gap > 0.2:
            follow = f" — slightly ahead of {runner_name}."
        else:
            follow = f" — only marginally ahead of {runner_name}."
    elif total < 3:
        follow = " — early signal, more pulls needed for confidence."

    return tone + follow
