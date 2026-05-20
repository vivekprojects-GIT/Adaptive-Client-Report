"""
Unmapped-intent backlog — the review queue for growing the intent taxonomy.

Every turn that resolves to "unmapped" still records the classifier's
best-guess label as `suggested_intent` (see orchestrator._suggested_intent_for):
  • classifier said "unmapped"      → its snake_case unmapped_name guess
  • classifier named a real intent
    that isn't an ACTIVE config doc  → that intent name (never created / disabled)

This module rolls those turns up by suggested_intent so an admin can see
which unseen intents are worth promoting to first-class config entities.

Privacy: aggregates only — counts, the (already-canonicalized) topics each
suggestion showed up under, and timestamps. No raw queries are read or
returned (raw queries are never persisted in the first place).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..store import MongoStore


def compute_unmapped_intents(
    store: MongoStore,
    days: int = 30,
    domain: Optional[str] = None,
    limit: int = 50,
    topics_per_intent: int = 6,
) -> Dict[str, Any]:
    """Roll up unmapped turns by suggested_intent, most frequent first."""

    # -------- 1. Resolve time window --------
    now = datetime.now(timezone.utc)
    if days <= 0:
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        since = now - timedelta(days=days)
    since_iso = since.isoformat()

    # -------- 2. Pull unmapped turns in the window --------
    q: Dict[str, Any] = {
        "ts": {"$gte": since_iso},
        "intent": "unmapped",
        "suggested_intent": {"$nin": [None, ""]},
    }
    if domain:
        q["domain"] = domain
    rows = list(
        store.turn_record.find(
            q,
            {
                "suggested_intent": 1,
                "topic": 1,
                "ts": 1,
                "intent_confidence": 1,
                "user_id_hash": 1,
            },
        )
    )

    # -------- 3. Group by suggested_intent --------
    agg: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        name = (r.get("suggested_intent") or "").strip()
        if not name:
            continue
        e = agg.setdefault(name, {
            "suggested_intent": name,
            "count":            0,
            "topic_counts":     {},     # topic -> hits
            "users":            set(),  # distinct user_id_hash
            "conf_sum":         0.0,
            "first_seen":       r.get("ts"),
            "last_seen":        r.get("ts"),
        })
        e["count"] += 1
        topic = r.get("topic") or "general"
        e["topic_counts"][topic] = e["topic_counts"].get(topic, 0) + 1
        if r.get("user_id_hash"):
            e["users"].add(r["user_id_hash"])
        e["conf_sum"] += float(r.get("intent_confidence", 0.0))
        ts = r.get("ts")
        if ts:
            if not e["first_seen"] or ts < e["first_seen"]:
                e["first_seen"] = ts
            if not e["last_seen"] or ts > e["last_seen"]:
                e["last_seen"] = ts

    # -------- 4. Shape the output --------
    suggestions: List[Dict[str, Any]] = []
    for e in agg.values():
        top_topics = sorted(
            e["topic_counts"].items(), key=lambda kv: kv[1], reverse=True
        )[:topics_per_intent]
        suggestions.append({
            "suggested_intent": e["suggested_intent"],
            "count":            e["count"],
            "unique_users":     len(e["users"]),
            "avg_confidence":   round(e["conf_sum"] / e["count"], 3) if e["count"] else 0.0,
            "top_topics":       [{"topic": t, "count": c} for t, c in top_topics],
            "first_seen":       e["first_seen"],
            "last_seen":        e["last_seen"],
        })

    suggestions.sort(key=lambda s: (s["count"], s["unique_users"]), reverse=True)

    return {
        "window_days":      days,
        "domain":           domain or None,
        "total_unmapped":   len(rows),
        "distinct_intents": len(suggestions),
        "suggestions":      suggestions[:limit],
    }
