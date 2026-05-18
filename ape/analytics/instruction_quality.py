"""
Instruction quality analytics — surfaces which (strategy, instruction_version)
pairs are producing problem signals so admins know which instructions to
rewrite.

Reads three problem-signal types from ape_turn_record:
  1. format_compliance_fail   — auto-fires when synthesizer diverges from
                                strategy.format_type. The strongest indicator
                                that an instruction isn't tight enough.
  2. content_correction       — LLM-detected: user said "actually that's wrong"
                                etc. Indicates factual/content failure rooted
                                in the instruction or RAG retrieval.
  3. reask_same_question      — LLM-detected: user re-asked the same thing.
                                Indicates the original answer didn't land —
                                could be content thinness or format unclarity.

Both `pending_signals[]` and the final `signal` field are scanned so a problem
signal still counts even if a composite pattern won the resolver (e.g. when
content_correction is buffered alongside thumbs_down, the composite
pattern_content_failure_confirmed wins but the original correction signal is
still there to count).

Output per (strategy, version):
  - total turns served in window
  - failure counts per signal type
  - failure rate (any problem signal / total)
  - tier:  CRITICAL > 30%  ·  HIGH > 15%  ·  MEDIUM > 5%  ·  LOW <= 5%
  - sample failing turns (up to 5) with query / signal / ts for context
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


# Signals that indicate an instruction-level quality issue
PROBLEM_SIGNALS = {
    "format_compliance_fail",
    "content_correction",
    "reask_same_question",
}

# Tier thresholds (as decimal fractions, e.g. 0.30 = 30%)
TIER_CRITICAL = 0.30
TIER_HIGH     = 0.15
TIER_MEDIUM   = 0.05


def _tier(failure_rate: float, total: int) -> str:
    """Bucket a failure rate into severity tier. Below min_turns → EXPLORING."""
    if total < 5:
        return "EXPLORING"
    if failure_rate >= TIER_CRITICAL:
        return "CRITICAL"
    if failure_rate >= TIER_HIGH:
        return "HIGH"
    if failure_rate >= TIER_MEDIUM:
        return "MEDIUM"
    return "LOW"


def _has_problem_signal_in_pending(row: Dict[str, Any]) -> List[str]:
    """Return the list of problem signal names that fired on this turn.
    Looks at both `pending_signals[]` (the full buffered history) and
    the final `signal` (the resolver winner)."""
    found = set()
    # Buffered signals
    for sig in row.get("pending_signals") or []:
        s_name = sig.get("signal")
        if s_name in PROBLEM_SIGNALS:
            found.add(s_name)
    # Final winning signal (in case it's a problem signal directly)
    final = row.get("signal")
    if final in PROBLEM_SIGNALS:
        found.add(final)
    return sorted(found)


def compute_instruction_quality(
    store,
    days: int = 14,
    min_turns: int = 5,
    sample_limit: int = 5,
) -> Dict[str, Any]:
    """Aggregate problem-signal incidence per (strategy, instruction_version).

    Args:
      store:        MongoStore instance
      days:         look-back window in days
      min_turns:    require at least this many turns to assign a tier
      sample_limit: how many example failing turns to attach per pair

    Returns a dict shaped:
      {
        "window_days":    14,
        "as_of":          "2026-05-18T...",
        "total_turns":    412,
        "total_failures": 47,
        "overall_rate":   0.114,
        "pairs": [
          {
            "strategy":            "comparison_table",
            "instruction_version": "v2",
            "total_turns":         53,
            "failures": {
              "format_compliance_fail": 8,
              "content_correction":     1,
              "reask_same_question":    0,
            },
            "total_failures":      9,
            "failure_rate":        0.169,
            "tier":                "HIGH",
            "samples": [
              {"response_id": "r_...", "query": "...",
               "signals": ["format_compliance_fail"], "ts": "..."},
              ...
            ],
          },
          ...
        ],
      }
    """
    cutoff_dt = datetime.utcnow() - timedelta(days=int(days))
    cutoff_iso = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%S")

    # Pull every turn record in window that has reward_status not pending
    # (we want finalized turns only — pending ones haven't had reward applied
    # yet so we can't trust their signal history).
    rows = list(
        store.db["ape_turn_record"].find(
            {
                "ts": {"$gte": cutoff_iso},
                "reward_status": {"$ne": "PENDING"},
            },
            projection={
                "response_id":          1,
                "ts":                   1,
                "selected_strategy":    1,
                "instruction_version":  1,
                "intent":               1,
                "topic":                1,
                "signal":               1,
                "pending_signals":      1,
                "query":                1,   # may be absent — older rows didn't store
                "_id":                  0,
            },
        )
    )

    # Group by (strategy, instruction_version)
    grouped: Dict[tuple, Dict[str, Any]] = defaultdict(lambda: {
        "strategy":            None,
        "instruction_version": None,
        "total_turns":         0,
        "failures": {sig: 0 for sig in PROBLEM_SIGNALS},
        "total_failures":      0,
        "samples":             [],
    })

    overall_failures = 0

    for r in rows:
        strategy = r.get("selected_strategy") or "_unknown"
        version  = r.get("instruction_version") or "_unknown"
        key = (strategy, version)
        bucket = grouped[key]
        bucket["strategy"] = strategy
        bucket["instruction_version"] = version
        bucket["total_turns"] += 1

        problems = _has_problem_signal_in_pending(r)
        if not problems:
            continue

        bucket["total_failures"] += 1
        overall_failures += 1
        for sig in problems:
            if sig in bucket["failures"]:
                bucket["failures"][sig] += 1

        # Sample up to N failing turns per pair
        if len(bucket["samples"]) < sample_limit:
            bucket["samples"].append({
                "response_id": r.get("response_id"),
                "ts":          r.get("ts"),
                "intent":      r.get("intent"),
                "topic":       r.get("topic"),
                "signals":     problems,
                "query":       r.get("query") or "",
            })

    # Compute failure_rate + tier and sort
    pairs: List[Dict[str, Any]] = []
    for bucket in grouped.values():
        total = bucket["total_turns"]
        fail  = bucket["total_failures"]
        rate  = (fail / total) if total > 0 else 0.0
        bucket["failure_rate"] = round(rate, 4)
        bucket["tier"] = _tier(rate, total)
        pairs.append(bucket)

    # Sort: tier severity first, then failure_rate desc, then total_turns desc
    tier_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "EXPLORING": 4}
    pairs.sort(key=lambda p: (
        tier_rank.get(p["tier"], 99),
        -p["failure_rate"],
        -p["total_turns"],
    ))

    total_turns = sum(p["total_turns"] for p in pairs)
    overall_rate = (overall_failures / total_turns) if total_turns else 0.0

    return {
        "window_days":    int(days),
        "as_of":          datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_turns":    total_turns,
        "total_failures": overall_failures,
        "overall_rate":   round(overall_rate, 4),
        "min_turns_for_tier": int(min_turns),
        "tier_thresholds": {
            "CRITICAL": TIER_CRITICAL,
            "HIGH":     TIER_HIGH,
            "MEDIUM":   TIER_MEDIUM,
        },
        "pairs":          pairs,
    }
