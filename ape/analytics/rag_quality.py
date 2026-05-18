"""
RAG quality analytics — surfaces TOPICS where our knowledge base / retrieval
is failing, based on user reactions to specific topics.

Different from instruction_quality (which groups by strategy+version, asking
"which instruction to rewrite?"). This module asks "which topic's RAG
retrieval needs work?" — same underlying signals, different aggregation.

Two signal types are RAG-diagnostic:

  content_correction     — user explicitly told us a fact is wrong. STRONG
                            evidence of factual gap or stale content in RAG.

  reask_same_question    — user re-asked the same question, meaning the
                            answer didn't land. Could be format clarity OR
                            content thinness. Moderate RAG signal — likely
                            true when re-asks cluster on specific topics.

NOT used here (different concerns):

  format_compliance_fail — synthesizer-instruction mismatch, not a RAG issue.
                           That's instruction_quality's domain.

Output per topic:
  - total turns on this topic in window
  - count of content_corrections (strong)
  - count of reask_same_questions (moderate)
  - rag_failure_rate = (content_corrections + 0.5·reasks) / turns
                       (weighted because content_correction is stronger evidence)
  - tier:  CRITICAL ≥ 25%  ·  HIGH ≥ 12%  ·  MEDIUM ≥ 5%  ·  LOW < 5%
  - sample failing turns: actual queries that broke, so admin can see
    exactly what content was missing or wrong
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List


# Signals that indicate a RAG / content-quality issue at the topic level
RAG_PROBLEM_SIGNALS = {
    "content_correction":   1.0,    # weight — strong evidence
    "reask_same_question":  0.5,    # weight — moderate evidence
}

# Tier thresholds (failure_rate computed using weights above)
TIER_CRITICAL = 0.25
TIER_HIGH     = 0.12
TIER_MEDIUM   = 0.05


def _tier(failure_rate: float, total: int, min_turns: int) -> str:
    if total < min_turns:
        return "EXPLORING"
    if failure_rate >= TIER_CRITICAL:
        return "CRITICAL"
    if failure_rate >= TIER_HIGH:
        return "HIGH"
    if failure_rate >= TIER_MEDIUM:
        return "MEDIUM"
    return "LOW"


def _problem_signals_on_row(row: Dict[str, Any]) -> List[str]:
    """Return list of RAG-relevant problem signals that fired on this turn.
    Scans both pending_signals[] and the final signal field."""
    found = set()
    for sig in row.get("pending_signals") or []:
        s = sig.get("signal")
        if s in RAG_PROBLEM_SIGNALS:
            found.add(s)
    final = row.get("signal")
    if final in RAG_PROBLEM_SIGNALS:
        found.add(final)
    return sorted(found)


def compute_rag_quality(
    store,
    days: int = 14,
    min_turns: int = 5,
    sample_limit: int = 5,
) -> Dict[str, Any]:
    """Aggregate RAG-diagnostic signals per topic.

    Args:
      store:        MongoStore instance
      days:         look-back window
      min_turns:    min turns on a topic to assign a tier
      sample_limit: how many sample failing queries to include per topic

    Returns:
      {
        "window_days":    14,
        "as_of":          "2026-05-18T...",
        "total_turns":    412,
        "total_failures": 23,
        "overall_rate":   0.056,
        "min_turns_for_tier": 5,
        "tier_thresholds":   {...},
        "topics": [
          {
            "topic":                 "wash_sale_rules",
            "total_turns":           18,
            "content_corrections":   4,
            "reask_same_questions":  3,
            "weighted_failures":     5.5,    # 4*1.0 + 3*0.5
            "failure_rate":          0.306,
            "tier":                  "CRITICAL",
            "samples": [{...}, ...]
          }, ...
        ]
      }
    """
    cutoff_dt = datetime.utcnow() - timedelta(days=int(days))
    cutoff_iso = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%S")

    rows = list(
        store.db["ape_turn_record"].find(
            {
                "ts": {"$gte": cutoff_iso},
                "reward_status": {"$ne": "PENDING"},
            },
            projection={
                "response_id":          1,
                "ts":                   1,
                "topic":                1,
                "intent":               1,
                "selected_strategy":    1,
                "instruction_version":  1,
                "signal":               1,
                "pending_signals":      1,
                "query":                1,
                "_id":                  0,
            },
        )
    )

    grouped: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "topic":                 None,
        "total_turns":           0,
        "content_corrections":   0,
        "reask_same_questions":  0,
        "weighted_failures":     0.0,
        "samples":               [],
    })

    overall_weighted_failures = 0.0

    for r in rows:
        topic = r.get("topic") or "_unknown"
        bucket = grouped[topic]
        bucket["topic"] = topic
        bucket["total_turns"] += 1

        problems = _problem_signals_on_row(r)
        if not problems:
            continue

        weight = 0.0
        for sig in problems:
            if sig == "content_correction":
                bucket["content_corrections"] += 1
            elif sig == "reask_same_question":
                bucket["reask_same_questions"] += 1
            weight += RAG_PROBLEM_SIGNALS.get(sig, 0.0)

        bucket["weighted_failures"] += weight
        overall_weighted_failures += weight

        if len(bucket["samples"]) < sample_limit:
            bucket["samples"].append({
                "response_id":         r.get("response_id"),
                "ts":                  r.get("ts"),
                "intent":              r.get("intent"),
                "query":               r.get("query") or "",
                "selected_strategy":   r.get("selected_strategy"),
                "instruction_version": r.get("instruction_version"),
                "signals":             problems,
            })

    topics: List[Dict[str, Any]] = []
    for bucket in grouped.values():
        total = bucket["total_turns"]
        rate = (bucket["weighted_failures"] / total) if total > 0 else 0.0
        bucket["failure_rate"] = round(rate, 4)
        bucket["weighted_failures"] = round(bucket["weighted_failures"], 2)
        bucket["tier"] = _tier(rate, total, min_turns)
        topics.append(bucket)

    # Sort: tier severity then failure_rate desc then total_turns desc
    tier_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "EXPLORING": 4}
    topics.sort(key=lambda t: (
        tier_rank.get(t["tier"], 99),
        -t["failure_rate"],
        -t["total_turns"],
    ))

    total_turns = sum(t["total_turns"] for t in topics)
    overall_rate = (overall_weighted_failures / total_turns) if total_turns else 0.0

    return {
        "window_days":          int(days),
        "as_of":                datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_turns":          total_turns,
        "total_failures":       round(overall_weighted_failures, 2),
        "overall_rate":         round(overall_rate, 4),
        "min_turns_for_tier":   int(min_turns),
        "tier_thresholds":      {
            "CRITICAL": TIER_CRITICAL,
            "HIGH":     TIER_HIGH,
            "MEDIUM":   TIER_MEDIUM,
        },
        "signal_weights":       RAG_PROBLEM_SIGNALS,
        "topics":               topics,
    }
