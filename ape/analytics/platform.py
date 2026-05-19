"""
Platform Overview — cross-user aggregates for the analytics dashboard.

Answers macro questions like:
  • Which topics is the user base most interested in overall?
  • Which strategies are winning across users?
  • What's the intent mix across all turns in the window?
  • How are users distributed across decision stages and readiness tiers?

Date window:
  Same `days` semantics as /analytics/active-users:
    0    = since start of today
    7    = last 7 days
    3650 = effectively all-time

Privacy: aggregates only — no raw queries, no per-user_id_hash data in the
response. The individual user view is still gated by Inspect.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..store import MongoStore
from ..store.mongo_schema import (
    COL_USER_TOPIC_INTEREST,
    ENTITY_OFFER_POLICY,
    REWARD_STATUS_APPLIED,
    STATUS_ACTIVE,
)
from .recommender import eligible_offers_for_user
from .user_profile import compute_user_cognitive_profile


def compute_platform_overview(
    store: MongoStore,
    days: int = 30,
    domain: Optional[str] = None,
    top_n: int = 8,
) -> Dict[str, Any]:
    """Aggregate dashboard for the whole user base."""

    # -------- 1. Resolve time window --------
    now = datetime.now(timezone.utc)
    if days <= 0:
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        since = now - timedelta(days=days)
    since_iso = since.isoformat()

    # -------- 2. Pull source data scoped to the window --------
    turn_q: Dict[str, Any] = {"ts": {"$gte": since_iso}}
    if domain:
        turn_q["domain"] = domain
    turn_rows = list(store.turn_record.find(turn_q))

    bandit_q: Dict[str, Any] = {"count": {"$gt": 0}}
    if domain:
        bandit_q["domain"] = domain
    bandit_rows = list(store.bandit_state.find(bandit_q))

    interest_q: Dict[str, Any] = {}
    if domain:
        interest_q["domain"] = domain
    interest_rows = list(store.db[COL_USER_TOPIC_INTEREST].find(interest_q))

    # Unique users active in the window
    active_user_hashes = {r["user_id_hash"] for r in turn_rows if r.get("user_id_hash")}
    total_active_users = len(active_user_hashes)
    total_known_users  = len({r["user_id_hash"] for r in interest_rows})

    # -------- 3. Top topics across users --------
    # We rank by: cumulative interest_score (across users) × log(unique users)
    # so a topic loved by 5 users beats one loved at the same depth by 1.
    topic_agg: Dict[str, Dict[str, Any]] = {}
    for r in interest_rows:
        t = r["topic"]
        e = topic_agg.setdefault(t, {
            "topic":              t,
            "total_users":        0,
            "sum_interest_score": 0.0,
            "max_interest_score": 0.0,
            "sum_turns_30d":      0,
        })
        e["total_users"]        += 1
        e["sum_interest_score"] += float(r.get("interest_score", 0.0))
        e["max_interest_score"]  = max(e["max_interest_score"], float(r.get("interest_score", 0.0)))
        e["sum_turns_30d"]      += int(r.get("count_30d", 0))

    # Turn-count + avg_reward by topic from the actual events
    topic_turn_count: Counter = Counter()
    topic_reward_sum: Dict[str, float] = {}
    topic_reward_n:   Dict[str, int]   = {}
    for r in turn_rows:
        t = r.get("topic")
        if not t:
            continue
        topic_turn_count[t] += 1
        nr = r.get("normalized_reward")
        if nr is not None:
            topic_reward_sum[t] = topic_reward_sum.get(t, 0.0) + float(nr)
            topic_reward_n[t]   = topic_reward_n.get(t, 0) + 1

    for t, e in topic_agg.items():
        e["turns_in_window"] = int(topic_turn_count.get(t, 0))
        n = topic_reward_n.get(t, 0)
        e["avg_reward"] = round(topic_reward_sum.get(t, 0.0) / n, 3) if n else 0.0
        e["avg_interest_score"] = round(e["sum_interest_score"] / max(e["total_users"], 1), 3)

    by_topic = sorted(
        topic_agg.values(),
        key=lambda e: (-e["total_users"], -e["sum_interest_score"]),
    )[:top_n]

    # -------- 4. Top strategies (winning arms across users) --------
    strat_agg: Dict[str, Dict[str, Any]] = {}
    for r in bandit_rows:
        s = r.get("strategy")
        if not s:
            continue
        e = strat_agg.setdefault(s, {
            "strategy":     s,
            "total_pulls":  0,
            "total_reward": 0.0,
            "unique_users": set(),
            "unique_cells": set(),
        })
        cnt = int(r.get("count", 0))
        e["total_pulls"]   += cnt
        e["total_reward"]  += float(r.get("avg_reward", 0.0)) * cnt
        if r.get("user_id_hash"):
            e["unique_users"].add(r["user_id_hash"])
        e["unique_cells"].add((r.get("intent"), r.get("topic")))

    by_strategy_full = []
    for s, e in strat_agg.items():
        if e["total_pulls"] < 1:
            continue
        avg_r = e["total_reward"] / e["total_pulls"]
        by_strategy_full.append({
            "strategy":     s,
            "total_pulls":  e["total_pulls"],
            "avg_reward":   round(avg_r, 3),
            "unique_users": len(e["unique_users"]),
            "unique_cells": len(e["unique_cells"]),
        })
    # Sort: avg_reward × log(pulls) — popularity-weighted reward
    import math as _math
    by_strategy_full.sort(
        key=lambda e: -(e["avg_reward"] * _math.log(e["total_pulls"] + 1)),
    )
    by_strategy = by_strategy_full[:top_n]

    # -------- 5. Intent mix --------
    intent_counts = Counter(r["intent"] for r in turn_rows if r.get("intent"))
    intent_total = sum(intent_counts.values()) or 1
    intent_mix = [
        {
            "intent": k,
            "count":  v,
            "pct":    round(100 * v / intent_total, 1),
        }
        for k, v in intent_counts.most_common()
    ]

    # -------- 6. Stage funnel + readiness funnel --------
    # We piggy-back on the per-user profile compute for active users only —
    # cheap because we already have the data in memory above (bandit_rows is
    # the join). For larger fleets we'd cache profiles.
    stage_counter = Counter()
    readiness_counter = Counter()
    user_profiles: List[Dict[str, Any]] = []

    for uh in active_user_hashes:
        try:
            p = compute_user_cognitive_profile(store, user_id_hash=uh, domain=domain)
        except Exception:
            continue
        stage_counter[p.get("decision_stage", "Unknown")] += 1
        readiness_counter[p.get("offer_readiness_label", "Too early")] += 1
        user_profiles.append(p)

    stage_funnel = [
        {"stage": k, "count": v}
        for k, v in stage_counter.most_common()
    ]
    readiness_funnel = [
        {"tier": k, "count": v}
        for k, v in readiness_counter.most_common()
    ]

    # -------- 6b. Outreach summary (global) --------
    # • active_policies: how many outreach actions are turned on (status=ACTIVE)
    # • eligible_matches: total (user × outreach) pairs where the user passes
    #   the three-way gate (score · compliance · do_not_contact). Counts the
    #   actionable outreach opportunities across the whole user base.
    # • users_with_any_match: distinct users with at least one eligible outreach.
    outreach_q: Dict[str, Any] = {
        "entity_type": ENTITY_OFFER_POLICY,
        "status":      STATUS_ACTIVE,
    }
    if domain:
        outreach_q["domain"] = domain
    active_policies = store.config.count_documents(outreach_q)

    eligible_matches = 0
    users_with_any_match = 0
    for uh in active_user_hashes:
        try:
            offers = eligible_offers_for_user(store, user_id_hash=uh, domain=domain)
        except Exception:
            continue
        user_eligible = sum(1 for o in offers if o.get("eligible"))
        eligible_matches += user_eligible
        if user_eligible:
            users_with_any_match += 1

    outreach_summary = {
        "active_policies":      active_policies,
        "eligible_matches":     eligible_matches,
        "users_with_any_match": users_with_any_match,
    }

    # -------- 7. Signal mix (every signal that fired across applied turns) --------
    # Previously this counted only the final `signal` field (the resolver's
    # chosen LABEL). That undercounts dramatically — auto-fired signals like
    # format_compliance_pass and session_continue fire on most turns but lose
    # the resolver tie-break, so they never showed up. Now we count every
    # entry in pending_signals[] PLUS the winning composite label if any.
    signal_counts: Counter = Counter()
    for r in turn_rows:
        if r.get("reward_status") != REWARD_STATUS_APPLIED:
            continue
        # Count every atomic signal that was buffered on this response
        for s in r.get("pending_signals") or []:
            sname = s.get("signal")
            if sname:
                signal_counts[sname] += 1
        # If the final label is a composite (not in pending_signals), count it too
        winner = r.get("signal")
        if winner and winner.startswith("pattern_"):
            signal_counts[winner] += 1
        # Older rows without pending_signals: fall back to the final label
        elif winner and not r.get("pending_signals"):
            signal_counts[winner] += 1

    signal_total = sum(signal_counts.values()) or 1
    signal_mix = [
        {
            "signal": k,
            "count":  v,
            "pct":    round(100 * v / signal_total, 1),
        }
        for k, v in signal_counts.most_common(25)   # show every catalog signal
    ]

    return {
        "window_days":       days,
        "since":             since_iso,
        "total_active_users": total_active_users,
        "total_known_users":  total_known_users,
        "total_turns":        len(turn_rows),
        "total_topics":       len(topic_agg),
        "total_strategies":   len(strat_agg),
        "by_topic":           by_topic,
        "by_strategy":        by_strategy,
        "intent_mix":         intent_mix,
        "signal_mix":         signal_mix,
        "stage_funnel":       stage_funnel,
        "readiness_funnel":   readiness_funnel,
        "outreach_summary":   outreach_summary,
    }
