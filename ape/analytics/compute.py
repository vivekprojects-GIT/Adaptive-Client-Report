"""
Business-analytics aggregations derived from ape_turn_record.

Two outputs land in dedicated collections so dashboards / CRMs / next-best-action
engines can read them without touching the runtime path:

  ape_user_topic_interest  — per-user topic profile with interest_score
  ape_topic_trend_daily    — daily topic activity with trend_score

Recompute jobs are idempotent (upsert by unique key). Safe to call on demand or
on a cron schedule.

Privacy note: we read only normalized fields (`topic`, `intent`,
`normalized_reward`, `ts`, etc.). Raw query text and assistant responses are
NEVER aggregated — they stay in ape_messages and are deletable independently.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..store import MongoStore
from ..store.mongo_schema import (
    COL_TOPIC_TREND_DAILY,
    COL_USER_TOPIC_INTEREST,
    REWARD_STATUS_APPLIED,
)


# ----------------------------------------------------------------------------
# Scoring formulas (tunable)
# ----------------------------------------------------------------------------
#
# interest_score = 0.40 * frequency
#                + 0.25 * recency
#                + 0.25 * engagement
#                + 0.10 * followup_depth
#
# trend_score    = 0.5 * normalized_count_7d
#                + 0.3 * unique_user_density
#                + 0.2 * avg_reward
# ----------------------------------------------------------------------------

W_FREQ      = 0.40
W_RECENCY   = 0.25
W_ENGAGE    = 0.25
W_FOLLOWUP  = 0.10

DEFAULT_REWARD_FLOOR = 0.5   # neutral prior when no reward signals exist yet


# ----------------------------------------------------------------------------
# User interest aggregation
# ----------------------------------------------------------------------------

def compute_user_topic_interest(
    store: MongoStore,
    user_id_hash: Optional[str] = None,
    now: Optional[datetime] = None,
) -> int:
    """Recompute user_topic_interest rows.

    If `user_id_hash` is None, recomputes for ALL users that have turn records.
    Otherwise only that user.

    Returns the number of (user, topic) rows written.
    """
    now = now or datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago  = now - timedelta(days=7)

    match: Dict[str, Any] = {"ts": {"$gte": _iso(thirty_days_ago)}}
    if user_id_hash:
        match["user_id_hash"] = user_id_hash

    pipeline: List[Dict[str, Any]] = [
        {"$match": match},
        {"$group": {
            "_id": {
                "user_id_hash": "$user_id_hash",
                "domain":       "$domain",
                "topic":        "$topic",
            },
            "count_30d":      {"$sum": 1},
            "count_7d":       {"$sum": {"$cond": [
                {"$gte": ["$ts", _iso(seven_days_ago)]}, 1, 0]}},
            "last_seen_at":   {"$max": "$ts"},
            "first_seen_at":  {"$min": "$ts"},
            "rewarded_count": {"$sum": {"$cond": [
                {"$eq": ["$reward_status", REWARD_STATUS_APPLIED]}, 1, 0]}},
            "reward_sum":     {"$sum": {"$ifNull": ["$normalized_reward", 0]}},
            "positive_signals": {"$sum": {"$cond": [
                {"$gte": [{"$ifNull": ["$normalized_reward", 0]}, 0.75]}, 1, 0]}},
        }},
    ]

    rows = list(store.turn_record.aggregate(pipeline))

    # Compute per-user max count_30d so frequency is normalized PER USER.
    # A user's most-asked topic gets frequency=1; others scale down from that.
    max_count_per_user: Dict[str, int] = {}
    for r in rows:
        uid = r["_id"]["user_id_hash"]
        c = r["count_30d"]
        if c > max_count_per_user.get(uid, 0):
            max_count_per_user[uid] = c

    written = 0
    for r in rows:
        uid     = r["_id"]["user_id_hash"]
        domain  = r["_id"]["domain"]
        topic   = r["_id"]["topic"]
        c30     = r["count_30d"]
        c7      = r["count_7d"]
        last    = r["last_seen_at"]
        rew_n   = r["rewarded_count"]
        rew_sum = r["reward_sum"]

        avg_reward = (rew_sum / rew_n) if rew_n > 0 else DEFAULT_REWARD_FLOOR

        # Frequency: this topic's count_30d as a fraction of user's max
        max_c = max_count_per_user.get(uid, 1) or 1
        frequency_score = c30 / max_c

        # Recency: exp(-days_since_last / 7), so today=1.0, week ago=~0.37
        days_since = _days_since(last, now)
        recency_score = math.exp(-days_since / 7.0)

        # Engagement: avg_reward already in [0,1]
        engagement_score = avg_reward

        # Followup depth: recent activity ratio
        followup_depth_score = (c7 / c30) if c30 > 0 else 0.0

        interest_score = (
            W_FREQ     * frequency_score
            + W_RECENCY * recency_score
            + W_ENGAGE  * engagement_score
            + W_FOLLOWUP * followup_depth_score
        )

        store.db[COL_USER_TOPIC_INTEREST].update_one(
            {"user_id_hash": uid, "domain": domain, "topic": topic},
            {"$set": {
                "user_id_hash":         uid,
                "domain":               domain,
                "topic":                topic,
                "count_7d":             c7,
                "count_30d":            c30,
                "last_seen_at":         last,
                "first_seen_at":        r["first_seen_at"],
                "rewarded_count":       rew_n,
                "positive_signals":     r["positive_signals"],
                "avg_reward":           round(avg_reward, 3),
                "frequency_score":      round(frequency_score, 3),
                "recency_score":        round(recency_score, 3),
                "engagement_score":     round(engagement_score, 3),
                "followup_depth_score": round(followup_depth_score, 3),
                "interest_score":       round(interest_score, 3),
                "computed_at":          _iso(now),
            }},
            upsert=True,
        )
        written += 1
    return written


# ----------------------------------------------------------------------------
# Topic trend aggregation
# ----------------------------------------------------------------------------

def compute_topic_trends(
    store: MongoStore,
    days: int = 14,
    now: Optional[datetime] = None,
) -> int:
    """Recompute daily topic trends for the last `days` days.

    For each (date, domain, topic), aggregates total_turns, unique_users,
    avg_reward, and computes a trend_score for the latest day relative
    to the previous 7-day average.

    Returns the number of (date, topic) rows written.
    """
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    pipeline: List[Dict[str, Any]] = [
        {"$match": {"ts": {"$gte": _iso(start)}}},
        {"$addFields": {
            "_date": {"$substr": ["$ts", 0, 10]},   # YYYY-MM-DD
        }},
        {"$group": {
            "_id": {
                "date":   "$_date",
                "domain": "$domain",
                "topic":  "$topic",
            },
            "total_turns":  {"$sum": 1},
            "users":        {"$addToSet": "$user_id_hash"},
            "rewarded_count": {"$sum": {"$cond": [
                {"$eq": ["$reward_status", REWARD_STATUS_APPLIED]}, 1, 0]}},
            "reward_sum":   {"$sum": {"$ifNull": ["$normalized_reward", 0]}},
        }},
        {"$project": {
            "date":         "$_id.date",
            "domain":       "$_id.domain",
            "topic":        "$_id.topic",
            "total_turns":  1,
            "unique_users": {"$size": "$users"},
            "avg_reward":   {"$cond": [
                {"$gt": ["$rewarded_count", 0]},
                {"$divide": ["$reward_sum", "$rewarded_count"]},
                DEFAULT_REWARD_FLOOR,
            ]},
            "_id":          0,
        }},
    ]
    rows = list(store.turn_record.aggregate(pipeline))

    # Compute trend_score: today's total / 7-day-average across same topic
    # We do this in Python because it needs lookups across rows.
    by_topic: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        key = f"{r['domain']}#{r['topic']}"
        by_topic.setdefault(key, []).append(r)

    # Per-topic max for normalization
    max_total_in_window = max((r["total_turns"] for r in rows), default=1) or 1

    today_str = _iso(now)[:10]
    written = 0
    for r in rows:
        key = f"{r['domain']}#{r['topic']}"
        peers = by_topic[key]
        # 7-day rolling average around r.date for this topic
        target_date = r["date"]
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        window_start = target_dt - timedelta(days=7)
        window_counts = [
            p["total_turns"]
            for p in peers
            if window_start.strftime("%Y-%m-%d") <= p["date"] < target_date
        ]
        prior_avg = (sum(window_counts) / len(window_counts)) if window_counts else 0

        # Trend components:
        #  - normalized_count:   today's count / max in window
        #  - growth_ratio:       today's count / prior_avg (capped at 3.0)
        #  - density:            unique_users / total_turns
        normalized_count = r["total_turns"] / max_total_in_window
        growth_ratio     = min(r["total_turns"] / prior_avg, 3.0) if prior_avg > 0 else (
            1.0 if r["total_turns"] > 0 else 0.0)
        density          = r["unique_users"] / r["total_turns"] if r["total_turns"] else 0
        engagement       = r["avg_reward"]

        trend_score = (
            0.4 * normalized_count
            + 0.3 * (growth_ratio / 3.0)        # normalize growth into [0,1]
            + 0.2 * density
            + 0.1 * engagement
        )

        store.db[COL_TOPIC_TREND_DAILY].update_one(
            {"date": r["date"], "domain": r["domain"], "topic": r["topic"]},
            {"$set": {
                "date":          r["date"],
                "domain":        r["domain"],
                "topic":         r["topic"],
                "total_turns":   r["total_turns"],
                "unique_users":  r["unique_users"],
                "avg_reward":    round(r["avg_reward"], 3),
                "prior_7d_avg":  round(prior_avg, 2),
                "growth_ratio":  round(growth_ratio, 3),
                "density":       round(density, 3),
                "trend_score":   round(trend_score, 3),
                "is_today":      r["date"] == today_str,
                "computed_at":   _iso(now),
            }},
            upsert=True,
        )
        written += 1
    return written


def recompute_all(store: MongoStore, days: int = 14) -> Dict[str, int]:
    """Run both aggregations in sequence. Returns counts."""
    return {
        "user_topic_interest_rows": compute_user_topic_interest(store),
        "topic_trend_daily_rows":   compute_topic_trends(store, days=days),
    }


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _days_since(iso_string: str, now: datetime) -> float:
    try:
        t = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return max(0.0, (now - t).total_seconds() / 86400.0)
    except (ValueError, AttributeError):
        return 30.0  # stale fallback
