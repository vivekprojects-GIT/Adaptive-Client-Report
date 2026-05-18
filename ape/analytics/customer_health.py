"""
Customer health analytics — the three signal consumers the catalog
declared but never implemented:

  retention    — cohort return-rate analysis (D1 / D7 / D30 by signup week)
  satisfaction — NPS-style score from thumbs_up / thumbs_down ratio
  engagement   — per-user behavioral segmentation
                 (deep_divers / explorers / power_users / one_and_done / casual)

Single computation function `compute_customer_health()` returns all three
in one dict so the analytics page can fetch them with one request.

Why bundled: the three views share the same source data (turn_record) and
similar window semantics. Three separate endpoints would re-fetch the same
rows three times. One endpoint + one in-memory pass is materially cheaper.

Heuristics chosen pragmatically — these are reasonable defaults rather than
empirically calibrated thresholds. When data scale supports it, move to
measured cutoffs (Stage 2 calibration).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


# ─── Engagement segment thresholds (pragmatic defaults) ────────────────────
SEGMENT_RULES = [
    # Order matters — first match wins
    {"name": "deep_divers",
     "criteria": ">5 deeper_questions on ≤3 topics",
     "test": lambda u: u["deeper_q_count"] > 5 and u["unique_topics"] <= 3},

    {"name": "explorers",
     "criteria": ">3 topics covered",
     "test": lambda u: u["unique_topics"] > 3},

    {"name": "power_users",
     "criteria": ">20 turns AND >2 sessions",
     "test": lambda u: u["total_turns"] > 20 and u["unique_sessions"] > 2},

    {"name": "one_and_done",
     "criteria": "≤2 turns lifetime",
     "test": lambda u: u["total_turns"] <= 2},

    {"name": "casual",
     "criteria": "everything else",
     "test": lambda u: True},
]


def _iso_date(ts: str) -> Optional[str]:
    """Extract YYYY-MM-DD from an ISO timestamp string."""
    if not ts or len(ts) < 10:
        return None
    return ts[:10]


def _week_start(date_str: str) -> str:
    """Return Monday of the week containing date_str (YYYY-MM-DD)."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        monday = dt - timedelta(days=dt.weekday())
        return monday.strftime("%Y-%m-%d")
    except Exception:
        return date_str


def _days_between(d1: str, d2: str) -> int:
    """Day delta between two YYYY-MM-DD strings. Negative if d1 > d2."""
    try:
        dt1 = datetime.strptime(d1, "%Y-%m-%d")
        dt2 = datetime.strptime(d2, "%Y-%m-%d")
        return (dt2 - dt1).days
    except Exception:
        return 0


# ─── RETENTION ─────────────────────────────────────────────────────────────

def _compute_retention(
    user_rows: Dict[str, List[Dict]],
    cohort_weeks: int,
) -> Dict[str, Any]:
    """Group users by first-seen week; compute D1/D7/D30 retention per cohort.

    Retention = "user had AT LEAST one turn in the lookback window after
    their first_seen day". So D1 retention means they came back within 24h.

    We only count cohorts whose lookback window has had time to mature
    (e.g. for D30 retention, the cohort must be at least 30 days old).
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")

    cohorts: Dict[str, Dict[str, Any]] = {}
    for user_hash, rows in user_rows.items():
        if not rows:
            continue
        # Find first-seen date for this user
        dates = sorted({_iso_date(r["ts"]) for r in rows if r.get("ts")})
        if not dates:
            continue
        first = dates[0]
        cohort_key = _week_start(first)

        # Initialize cohort bucket
        if cohort_key not in cohorts:
            cohorts[cohort_key] = {
                "week_start":   cohort_key,
                "size":         0,
                "active_d1":    0,
                "active_d7":    0,
                "active_d30":   0,
                "cohort_age_days": _days_between(cohort_key, today),
            }
        c = cohorts[cohort_key]
        c["size"] += 1

        # Retention checks — did the user have any activity AFTER first day?
        active_dates = set(dates) - {first}
        for d in active_dates:
            delta = _days_between(first, d)
            if 0 < delta <= 1:
                c["active_d1"] += 1
                break
        for d in active_dates:
            delta = _days_between(first, d)
            if 0 < delta <= 7:
                c["active_d7"] += 1
                break
        for d in active_dates:
            delta = _days_between(first, d)
            if 0 < delta <= 30:
                c["active_d30"] += 1
                break

    cohort_list = sorted(cohorts.values(), key=lambda c: c["week_start"])
    # Limit to the most recent `cohort_weeks` cohorts
    if len(cohort_list) > cohort_weeks:
        cohort_list = cohort_list[-cohort_weeks:]

    # Compute rates per cohort
    for c in cohort_list:
        size = max(1, c["size"])
        c["rate_d1"]  = round(c["active_d1"]  / size, 3)
        c["rate_d7"]  = round(c["active_d7"]  / size, 3)
        c["rate_d30"] = round(c["active_d30"] / size, 3)
        # Mature flags — only meaningful if the cohort is old enough
        c["mature_d1"]  = c["cohort_age_days"] >= 1
        c["mature_d7"]  = c["cohort_age_days"] >= 7
        c["mature_d30"] = c["cohort_age_days"] >= 30

    # Overall (weighted by cohort size) — only counting mature cohorts
    def _weighted_rate(attr: str, mature_attr: str) -> float:
        total = 0
        actives = 0
        for c in cohort_list:
            if not c.get(mature_attr):
                continue
            total += c["size"]
            actives += c[attr]
        return round(actives / total, 3) if total else 0.0

    return {
        "cohort_weeks":         int(cohort_weeks),
        "cohorts":              cohort_list,
        "overall_d1_retention":  _weighted_rate("active_d1",  "mature_d1"),
        "overall_d7_retention":  _weighted_rate("active_d7",  "mature_d7"),
        "overall_d30_retention": _weighted_rate("active_d30", "mature_d30"),
    }


# ─── SATISFACTION (NPS-style) ──────────────────────────────────────────────

def _signal_appeared(row: Dict[str, Any], signal_name: str) -> bool:
    """True iff signal_name is in pending_signals[] or the final signal."""
    if row.get("signal") == signal_name:
        return True
    for s in row.get("pending_signals") or []:
        if s.get("signal") == signal_name:
            return True
    return False


def _compute_satisfaction(
    rows_in_window: List[Dict],
    window_days: int,
) -> Dict[str, Any]:
    """Compute thumbs_up / thumbs_down rate and a NPS-style score.

    NPS-style score = (positive% - negative%) × 100, range [-100, +100].
    Anything above +50 is "very satisfied", 0-50 is "mixed", below 0 is "concerning".
    """
    total_up = 0
    total_down = 0
    weekly_buckets: Dict[str, Dict[str, int]] = defaultdict(lambda: {"up": 0, "down": 0})

    for r in rows_in_window:
        ts = r.get("ts", "")
        wk = _week_start(_iso_date(ts) or "")
        if _signal_appeared(r, "thumbs_up"):
            total_up += 1
            weekly_buckets[wk]["up"] += 1
        if _signal_appeared(r, "thumbs_down"):
            total_down += 1
            weekly_buckets[wk]["down"] += 1

    total_rated = total_up + total_down
    positive_rate = (total_up / total_rated) if total_rated else 0.0
    negative_rate = (total_down / total_rated) if total_rated else 0.0
    nps_score = round((positive_rate - negative_rate) * 100, 1)

    weekly_trend = []
    for wk, counts in sorted(weekly_buckets.items()):
        wk_total = counts["up"] + counts["down"]
        weekly_trend.append({
            "week_start": wk,
            "up":         counts["up"],
            "down":       counts["down"],
            "rate":       round(counts["up"] / wk_total, 3) if wk_total else 0.0,
        })

    # Verdict band for quick admin glance
    if nps_score >= 50:
        verdict = "very_satisfied"
    elif nps_score >= 0:
        verdict = "mixed"
    else:
        verdict = "concerning"

    return {
        "window_days":   int(window_days),
        "thumbs_up":     total_up,
        "thumbs_down":   total_down,
        "total_rated":   total_rated,
        "positive_rate": round(positive_rate, 3),
        "negative_rate": round(negative_rate, 3),
        "nps_score":     nps_score,
        "verdict":       verdict,
        "weekly_trend":  weekly_trend,
    }


# ─── ENGAGEMENT SEGMENTATION ──────────────────────────────────────────────

def _compute_engagement(
    user_rows: Dict[str, List[Dict]],
    window_days: int,
) -> Dict[str, Any]:
    """Bucket each active user into a behavioral segment.

    Per-user features computed from in-window turn_record:
      - total_turns
      - unique_sessions
      - unique_topics
      - deeper_q_count (count of turns where signal=deeper_question or
                       it's in pending_signals)
    """
    segment_counts: Dict[str, int] = defaultdict(int)
    user_segments: Dict[str, str] = {}

    for user_hash, rows in user_rows.items():
        if not rows:
            continue
        sessions = {r.get("session_id_optional") for r in rows if r.get("session_id_optional")}
        topics   = {r.get("topic") for r in rows if r.get("topic")}
        deeper_q = sum(1 for r in rows if _signal_appeared(r, "deeper_question"))

        features = {
            "total_turns":     len(rows),
            "unique_sessions": len(sessions),
            "unique_topics":   len(topics),
            "deeper_q_count":  deeper_q,
        }

        # First matching rule wins
        for rule in SEGMENT_RULES:
            if rule["test"](features):
                segment_counts[rule["name"]] += 1
                user_segments[user_hash] = rule["name"]
                break

    total = sum(segment_counts.values())
    segments = []
    for rule in SEGMENT_RULES:
        n = segment_counts.get(rule["name"], 0)
        segments.append({
            "segment":  rule["name"],
            "count":    n,
            "pct":      round(n / total, 3) if total else 0.0,
            "criteria": rule["criteria"],
        })

    return {
        "window_days":   int(window_days),
        "total_users":   total,
        "segments":      segments,
    }


# ─── PUBLIC ENTRY POINT ────────────────────────────────────────────────────

def compute_customer_health(
    store,
    days: int = 30,
    cohort_weeks: int = 4,
) -> Dict[str, Any]:
    """Single pass over turn_record → retention + satisfaction + engagement.

    The three views share the same source rows; computing them together
    avoids three round-trips to MongoDB.
    """
    cutoff_dt = datetime.utcnow() - timedelta(days=int(days))
    cutoff_iso = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%S")

    rows = list(
        store.db["ape_turn_record"].find(
            {"ts": {"$gte": cutoff_iso}},
            projection={
                "user_id_hash":          1,
                "session_id_optional":   1,
                "ts":                    1,
                "topic":                 1,
                "signal":                1,
                "pending_signals":       1,
                "_id":                   0,
            },
        )
    )

    # For retention, we need EVERY turn ever from each user (not just window)
    # to find their actual first_seen date. So do a second pass for the user
    # list we observed in-window.
    in_window_users = sorted({r["user_id_hash"] for r in rows if r.get("user_id_hash")})
    user_rows_full: Dict[str, List[Dict]] = defaultdict(list)
    if in_window_users:
        full_rows = list(
            store.db["ape_turn_record"].find(
                {"user_id_hash": {"$in": in_window_users}},
                projection={"user_id_hash": 1, "ts": 1, "_id": 0},
            )
        )
        for r in full_rows:
            user_rows_full[r["user_id_hash"]].append(r)

    # Bucket in-window rows by user for engagement segmentation
    user_rows_window: Dict[str, List[Dict]] = defaultdict(list)
    for r in rows:
        u = r.get("user_id_hash")
        if u:
            user_rows_window[u].append(r)

    retention    = _compute_retention(user_rows_full, cohort_weeks=cohort_weeks)
    satisfaction = _compute_satisfaction(rows, window_days=days)
    engagement   = _compute_engagement(user_rows_window, window_days=days)

    return {
        "as_of":        datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days":  int(days),
        "retention":    retention,
        "satisfaction": satisfaction,
        "engagement":   engagement,
    }
