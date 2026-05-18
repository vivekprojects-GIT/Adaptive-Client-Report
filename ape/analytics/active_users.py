"""
Active-users view — admin-facing slice that answers
"which customers were active in window X, on what topics, and are they
contact-ready?"

This is the bridge between the bandit/analytics state and downstream outreach.
We do NOT decide here whether to contact a user — that always goes through the
compliance pipeline (do_not_contact, jurisdictional rules, consent on file).
We just surface the candidate set sorted by interest_score.

Data sources:
  ape_turn_record           — raw activity events with ts, topic, intent
  ape_user_topic_interest   — precomputed interest_score per (user, topic)

Returned shape (one row per user, joined with their strongest topic in window):
  {
    "user_id_hash":      "u_d747...",
    "turn_count":        7,
    "topic_count":       3,
    "last_activity_ts":  "2026-05-17T...",
    "topics":            ["roth_ira", "etf_vs_mutual_fund", ...],
    "top_topic":         "roth_ira",
    "top_interest_score": 0.87,
    "contact_ready":     true,
    "applied_rewards":   4,
    "positive_rewards":  3,
  }
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..store import MongoStore
from ..store.mongo_schema import (
    COL_USER_TOPIC_INTEREST,
    REWARD_STATUS_APPLIED,
)


CONTACT_READY_THRESHOLD = 0.7   # interest_score gate for "good outreach target"


def active_users_in_window(
    store: MongoStore,
    days: int = 1,
    domain: Optional[str] = None,
    min_interest: float = 0.0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List users active in the last `days` days, with their top topic.

    `days = 1` means "since 24 hours ago"; `days = 0` means "since start of today";
    larger values widen the window. Sorted by top_interest_score desc.
    """
    now = datetime.now(timezone.utc)

    if days <= 0:
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        since = now - timedelta(days=days)
    since_iso = since.isoformat()

    # --------------------------------------------------------------
    # 1. Aggregate raw activity from turn_record in the window
    # --------------------------------------------------------------
    match_stage: Dict[str, Any] = {"ts": {"$gte": since_iso}}
    if domain:
        match_stage["domain"] = domain

    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": "$user_id_hash",
                "turn_count":        {"$sum": 1},
                "topics":            {"$addToSet": "$topic"},
                "intents":           {"$addToSet": "$intent"},
                "last_activity_ts":  {"$max": "$ts"},
                "applied_rewards":   {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$reward_status", REWARD_STATUS_APPLIED]},
                            1, 0,
                        ],
                    },
                },
                "positive_rewards": {
                    "$sum": {
                        "$cond": [
                            {"$and": [
                                {"$eq": ["$reward_status", REWARD_STATUS_APPLIED]},
                                {"$gt": ["$normalized_reward", 0]},
                            ]},
                            1, 0,
                        ],
                    },
                },
            },
        },
        {"$sort": {"last_activity_ts": -1}},
        {"$limit": int(limit) * 3},  # over-fetch; we'll re-rank by interest_score
    ]

    activity = list(store.turn_record.aggregate(pipeline))
    if not activity:
        return []

    # --------------------------------------------------------------
    # 2. For each active user, find their strongest topic via the
    #    precomputed user_topic_interest collection. We restrict to topics
    #    they actually touched in this window (intersection).
    # --------------------------------------------------------------
    user_hashes = [a["_id"] for a in activity]

    interest_q: Dict[str, Any] = {"user_id_hash": {"$in": user_hashes}}
    if domain:
        interest_q["domain"] = domain
    interest_rows = list(store.db[COL_USER_TOPIC_INTEREST].find(interest_q))

    # Index by (user_hash, topic) -> score
    by_user_topic: Dict[tuple, float] = {}
    for r in interest_rows:
        by_user_topic[(r["user_id_hash"], r["topic"])] = float(r.get("interest_score", 0.0))

    # --------------------------------------------------------------
    # 2.5. Bulk directory lookup — display name + compliance flags
    # --------------------------------------------------------------
    directory_map = store.get_directory_entries([a["_id"] for a in activity])

    results: List[Dict[str, Any]] = []
    for a in activity:
        uh = a["_id"]
        topics = [t for t in a["topics"] if t]
        directory = directory_map.get(uh, {})

        # Best topic for this user, restricted to ones they touched in window
        best_topic, best_score = None, 0.0
        for t in topics:
            s = by_user_topic.get((uh, t), 0.0)
            if s > best_score:
                best_topic, best_score = t, s

        # If user has activity but no interest_score yet (interest aggregator
        # hasn't run), fall back to first topic so the row still appears.
        if best_topic is None and topics:
            best_topic = topics[0]

        if best_score < min_interest:
            continue

        # Compliance gates — outreach is only "ready" if all three pass
        do_not_contact     = bool(directory.get("do_not_contact", False))
        compliance_ok      = bool(directory.get("compliance_eligible", True))
        score_ok           = best_score >= CONTACT_READY_THRESHOLD
        outreach_ready     = score_ok and compliance_ok and not do_not_contact

        # Narrative "why" — explains in plain English why we surfaced this user.
        intents_list = sorted([i for i in (a.get("intents") or []) if i])
        recommendation_reason = _build_reason(
            display_name        = directory.get("display_name") or uh[:10],
            turn_count          = int(a["turn_count"]),
            topic_count         = len(topics),
            top_topic           = best_topic,
            top_interest_score  = best_score,
            intents             = intents_list,
            positive_rewards    = int(a.get("positive_rewards", 0)),
            applied_rewards     = int(a.get("applied_rewards", 0)),
            do_not_contact      = do_not_contact,
            compliance_ok       = compliance_ok,
            score_ok            = score_ok,
        )

        results.append({
            "user_id_hash":          uh,
            "display_name":          directory.get("display_name") or uh,
            "turn_count":            int(a["turn_count"]),
            "topic_count":           len(topics),
            "last_activity_ts":      a["last_activity_ts"],
            "topics":                sorted(topics),
            "intents":               intents_list,
            "top_topic":             best_topic,
            "top_interest_score":    round(best_score, 3),

            # Eligibility (compliance-gated)
            "contact_ready":         outreach_ready,
            "do_not_contact":        do_not_contact,
            "compliance_eligible":   compliance_ok,
            "last_contacted_at":     directory.get("last_contacted_at"),

            "applied_rewards":       int(a.get("applied_rewards", 0)),
            "positive_rewards":      int(a.get("positive_rewards", 0)),
            "recommendation_reason": recommendation_reason,
        })

    # Sort: contact_ready first, then by interest score desc
    results.sort(key=lambda r: (not r["contact_ready"], -r["top_interest_score"], -r["turn_count"]))
    return results[:limit]


def _build_reason(
    display_name: str,
    turn_count: int,
    topic_count: int,
    top_topic: Optional[str],
    top_interest_score: float,
    intents,
    positive_rewards: int,
    applied_rewards: int,
    do_not_contact: bool,
    compliance_ok: bool,
    score_ok: bool,
) -> str:
    """Plain-English explanation for the admin row, in the spirit of:
        'User asked about X 8 times in the last window, mostly comparison /
         recommendation intent, positive engagement is high, readiness 0.86.'
    """
    if do_not_contact:
        return f"{display_name} has do_not_contact set — never surface for outreach."
    if not compliance_ok:
        return f"{display_name} failed compliance check — not eligible for outreach."

    parts = []
    if top_topic:
        parts.append(f"asked about {top_topic} across {turn_count} turns")
    else:
        parts.append(f"{turn_count} turns in window")
    if topic_count > 1:
        parts.append(f"spanning {topic_count} topics")
    if intents:
        intents_text = " / ".join(intents[:3])
        parts.append(f"mostly {intents_text} intent")
    if applied_rewards > 0:
        positive_pct = 100 * positive_rewards / applied_rewards
        parts.append(
            f"{positive_rewards}/{applied_rewards} positive rewards "
            f"({positive_pct:.0f}% positive engagement)"
        )
    parts.append(f"top interest_score = {top_interest_score:.2f}")

    tail = (
        " — ready for outreach." if score_ok
        else " — score below 0.7, nurture rather than contact."
    )
    return f"{display_name}: " + "; ".join(parts) + tail
