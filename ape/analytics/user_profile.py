"""
User Cognitive Profile — per-user summary of all 12 behavioral facets.

A "cognitive facet" is a *behavioral / product* observation about a user,
NEVER a psychological label. We say "user is in evaluation stage" or "prefers
comparison tables", not "user is anxious" or "user is risk-averse".

Inputs (only normalized metadata — never raw queries):
  • ape_turn_record           — intent / topic / strategy / signal / reward / ts
  • ape_user_bandit_state     — per-cell pull count + avg_reward
  • ape_user_topic_interest   — precomputed (user, topic) interest scores

Output is one dict with all 12 facets, suitable for:
  • the analytics-page Cognitive Profile card
  • CRM enrichment / call-list generation
  • next-best-action triggers (gated downstream by consent/compliance)

The 12 facets:
   1. Topic interest                  — top topic + score
   2. Intent pattern                  — dominant intent + distribution
   3. Decision stage                  — Awareness/Exploration/Evaluation/Action-ready/Support
   4. Engagement depth                — High/Medium/Low + max followups
   5. Format preference               — best strategy by reward-weighted-count
   6. Structured-thinking preference  — Structured vs Paragraph vs Mixed
   7. Clarity need                    — count of clarity-related signals
   8. Friction / confusion            — count of negative signals
   9. Positive engagement             — count of positive signals
  10. Recency momentum                — last-3d-rate vs last-30d-rate ratio
  11. Offer readiness                 — composite score 0..1
  12. Learning confidence             — based on total bandit pulls
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from ..store import MongoStore
from ..store.mongo_schema import COL_USER_TOPIC_INTEREST


# --------------------------------------------------------------------------
# Strategy taxonomy — used by facets #5 and #6.
# Easy to extend as new strategies are added via the admin page.
# --------------------------------------------------------------------------
STRUCTURED_STRATEGIES: Set[str] = {
    "comparison_table",
    "pros_cons_table",
    "decision_card",
    "numbered_steps",
    "checklist",
    "bullet_summary",
    "phased_workflow",
    "bullet_contrast",
    "step_by_step_reasoning",
}
PARAGRAPH_STRATEGIES: Set[str] = {
    "standard_llm",
    "short_paragraph",
    "one_liner",
    "analogy_explanation",
    "definition_plus_example",
    "definition_with_pointer",
}

# --------------------------------------------------------------------------
# Signal taxonomy — used by facets #7 / #8 / #9.
# Mirror of ape_config signal_routing entries; kept here to avoid an extra
# round-trip on every profile compute.
# --------------------------------------------------------------------------
# Current 9-signal catalog names first; legacy names (regenerate_click,
# session_abandon, copy_save) kept so pre-migration turn records still count.
CLARITY_SIGNALS: Set[str]  = {"format_change_request", "reask_same_question", "regenerate_click"}
FRICTION_SIGNALS: Set[str] = {"thumbs_down", "format_change_request", "content_correction",
                              "regenerate_click", "session_abandon"}
POSITIVE_SIGNALS: Set[str] = {"thumbs_up", "format_praise_explicit", "it_worked_statement",
                              "deeper_question", "copy_save"}


def compute_user_cognitive_profile(
    store: MongoStore,
    user_id_hash: str,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a single per-user profile dict with all 12 facets."""
    # ---------- 1. Pull source data ----------
    q_user: Dict[str, Any] = {"user_id_hash": user_id_hash}
    if domain:
        q_user["domain"] = domain

    bandit_rows   = list(store.bandit_state.find(q_user))
    turn_rows     = list(store.turn_record.find(q_user))
    interest_rows = list(store.db[COL_USER_TOPIC_INTEREST].find(q_user))

    # ---------- 1. Topic interest ----------
    interest_rows.sort(key=lambda r: -float(r.get("interest_score", 0.0)))
    top_topic_row = interest_rows[0] if interest_rows else None
    top_topic     = top_topic_row["topic"] if top_topic_row else None
    topic_interest_score = float(top_topic_row["interest_score"]) if top_topic_row else 0.0

    # ---------- 2. Intent pattern ----------
    intent_counts = Counter(r["intent"] for r in turn_rows if r.get("intent"))
    if not intent_counts:
        # Fall back to bandit cells so admin still sees something useful when
        # turn_records are sparse (e.g. seeded-only state).
        intent_counts = Counter(r["intent"] for r in bandit_rows if r.get("intent"))
    dominant_intent = intent_counts.most_common(1)[0][0] if intent_counts else None
    intent_distribution = dict(intent_counts.most_common(6))

    # ---------- 3. Decision stage ----------
    recent_intents = [
        r["intent"]
        for r in sorted(turn_rows, key=lambda r: r.get("ts", ""), reverse=True)[:10]
        if r.get("intent")
    ]
    decision_stage, decision_stage_score = _infer_decision_stage(recent_intents, intent_counts)

    # ---------- 4. Engagement depth ----------
    max_count_30d = max((int(r.get("count_30d", 0)) for r in interest_rows), default=0)
    if max_count_30d >= 8:
        engagement_depth, engagement_score = "High", 1.0
    elif max_count_30d >= 3:
        engagement_depth, engagement_score = "Medium", 0.6
    else:
        engagement_depth, engagement_score = "Low", 0.2

    # ---------- 5. Format preference ----------
    pulled_bandit = [r for r in bandit_rows if int(r.get("count", 0)) > 0]
    if pulled_bandit:
        def _weight(r):
            cnt = int(r.get("count", 0))
            avg = float(r.get("avg_reward", 0.0))
            return avg * min(cnt / 5.0, 1.0)
        best = max(pulled_bandit, key=_weight)
        preferred_format = best["strategy"]
        preferred_format_avg_reward = round(float(best.get("avg_reward", 0.0)), 3)
        preferred_format_count = int(best.get("count", 0))
    else:
        preferred_format = None
        preferred_format_avg_reward = 0.0
        preferred_format_count = 0

    # ---------- 6. Structured-thinking preference ----------
    s_avg, s_count = _weighted_avg(pulled_bandit, STRUCTURED_STRATEGIES)
    p_avg, p_count = _weighted_avg(pulled_bandit, PARAGRAPH_STRATEGIES)
    structured_pref, structured_score = _classify_structured_pref(s_avg, s_count, p_avg, p_count)

    # ---------- 7. Clarity need ----------
    clarity_count = sum(1 for r in turn_rows if r.get("signal") in CLARITY_SIGNALS)
    clarity_need = "High" if clarity_count >= 5 else "Medium" if clarity_count >= 2 else "Low"

    # ---------- 8. Friction / confusion ----------
    friction_count = sum(
        1 for r in turn_rows
        if r.get("signal") in FRICTION_SIGNALS
        or (r.get("normalized_reward") is not None and float(r["normalized_reward"]) < -0.3)
    )

    # ---------- 9. Positive engagement ----------
    positive_count = sum(
        1 for r in turn_rows
        if r.get("signal") in POSITIVE_SIGNALS
        or (r.get("normalized_reward") is not None and float(r["normalized_reward"]) >= 0.5)
    )

    # ---------- 10. Recency momentum ----------
    now = datetime.now(timezone.utc)
    cutoff_3d  = (now - timedelta(days=3)).isoformat()
    cutoff_30d = (now - timedelta(days=30)).isoformat()
    count_3d   = sum(1 for r in turn_rows if (r.get("ts") or "") >= cutoff_3d)
    count_30d  = sum(1 for r in turn_rows if (r.get("ts") or "") >= cutoff_30d)

    if count_30d > 0:
        # Per-day rate in the recent 3-day window vs the 30-day baseline.
        # A value of 2.0 means 2× the typical daily activity.
        rate_recent   = count_3d  / 3.0
        rate_baseline = count_30d / 30.0
        momentum_ratio = (rate_recent / rate_baseline) if rate_baseline > 0 else 0.0
    else:
        momentum_ratio = 0.0

    if momentum_ratio >= 1.5:
        recency_momentum, recency_score = "High", min(momentum_ratio / 3.0, 1.0)
    elif momentum_ratio >= 0.7:
        recency_momentum, recency_score = "Medium", 0.6
    else:
        recency_momentum, recency_score = "Low", 0.2

    # ---------- 11. Offer readiness (composite, stage-gated) ----------
    #
    # Strength factors (how interested/engaged is the user?):
    #   raw = 0.35×interest + 0.30×recency + 0.20×engagement + 0.15×stage_score
    #
    # Then we GATE by decision_stage_score — a user in Awareness shouldn't be
    # "Ready" no matter how active. So:
    #   offer_readiness = raw * decision_stage_score
    #
    # This makes the formula multiplicative on stage, which matches business
    # intuition: outreach lands best on users who've already moved from learning
    # to evaluating or deciding.
    pos_engagement_norm = min(positive_count / 8.0, 1.0)
    raw_strength = (
        0.35 * topic_interest_score
      + 0.30 * recency_score
      + 0.20 * pos_engagement_norm
      + 0.15 * decision_stage_score
    )
    offer_readiness = round(raw_strength * decision_stage_score, 3)
    if offer_readiness >= 0.70:
        offer_readiness_label = "Ready"
    elif offer_readiness >= 0.50:
        offer_readiness_label = "Likely"
    elif offer_readiness >= 0.30:
        offer_readiness_label = "Nurture"
    else:
        offer_readiness_label = "Too early"

    # ---------- 12. Learning confidence ----------
    total_pulls = sum(int(r.get("count", 0)) for r in bandit_rows)
    if total_pulls >= 20:
        learning_confidence, learning_confidence_score = "High", 1.0
    elif total_pulls >= 8:
        learning_confidence, learning_confidence_score = "Medium", 0.6
    else:
        learning_confidence, learning_confidence_score = "Low", 0.3

    # ---------- Last activity ----------
    last_activity_ts = None
    if turn_rows:
        last_activity_ts = max((r.get("ts") or "") for r in turn_rows)
    elif bandit_rows:
        last_activity_ts = max((r.get("last_updated_at") or "") for r in bandit_rows)

    # ---------- Display name (join against ape_user_directory) ----------
    directory_entry = store.get_directory_entry(user_id_hash) or {}
    display_name = directory_entry.get("display_name") or user_id_hash

    return {
        "user_id_hash": user_id_hash,
        "display_name": display_name,
        "domain":       domain or "all",

        # 1
        "top_topic":             top_topic,
        "topic_interest_score":  round(topic_interest_score, 3),
        "tracked_topics":        len(interest_rows),

        # 2
        "dominant_intent":       dominant_intent,
        "intent_distribution":   intent_distribution,

        # 3
        "decision_stage":        decision_stage,
        "decision_stage_score":  decision_stage_score,

        # 4
        "engagement_depth":      engagement_depth,
        "engagement_score":      round(engagement_score, 3),
        "max_followups_30d":     max_count_30d,

        # 5
        "preferred_format":      preferred_format,
        "preferred_format_avg_reward": preferred_format_avg_reward,
        "preferred_format_count":      preferred_format_count,

        # 6
        "structured_preference":         structured_pref,
        "structured_score":              round(structured_score, 3),
        "structured_avg_reward":         round(s_avg, 3),
        "structured_pull_count":         s_count,
        "paragraph_avg_reward":          round(p_avg, 3),
        "paragraph_pull_count":          p_count,

        # 7
        "clarity_need":          clarity_need,
        "clarity_signal_count":  clarity_count,

        # 8
        "friction_signal_count": friction_count,

        # 9
        "positive_signal_count": positive_count,

        # 10
        "recency_momentum":      recency_momentum,
        "recency_score":         round(recency_score, 3),
        "turns_last_3d":         count_3d,
        "turns_last_30d":        count_30d,

        # 11
        "offer_readiness_score": offer_readiness,
        "offer_readiness_label": offer_readiness_label,

        # 12
        "learning_confidence":       learning_confidence,
        "learning_confidence_score": round(learning_confidence_score, 3),
        "total_bandit_pulls":        total_pulls,

        # meta
        "last_activity_ts":      last_activity_ts,
        "computed_at":           datetime.now(timezone.utc).isoformat(),
    }


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _infer_decision_stage(
    recent_intents: List[str],
    all_intents: Counter,
) -> Tuple[str, float]:
    """Infer the user's current decision stage from intent sequence.

    Heuristic — recent intents dominate the verdict. The accompanying score
    in [0, 1] feeds into offer_readiness.
    """
    target = recent_intents or list(all_intents.elements())
    if not target:
        return "Unknown", 0.5

    c = Counter(target)
    n = sum(c.values())

    def frac(*intents: str) -> float:
        return sum(c.get(i, 0) for i in intents) / n if n else 0.0

    # Most action-y intents first (precedence-ordered)
    if c.get("Troubleshooting", 0) / n >= 0.40:
        return "Support-needed", 0.30
    if frac("Decision", "Recommendation") >= 0.40:
        return "Action-ready", 1.00
    if frac("Comparison", "Evaluation") >= 0.40:
        return "Evaluation",   0.75
    if frac("Definitional") >= 0.50:
        return "Awareness",    0.20
    # Mixed/general
    return "Exploration", 0.50


def _weighted_avg(
    rows: List[Dict[str, Any]],
    strategies: Set[str],
) -> Tuple[float, int]:
    """Pull-count-weighted avg_reward over the subset of rows in `strategies`.

    Returns (weighted_avg, total_count). avg=0 when no pulls — keep at 0
    rather than NaN so downstream comparisons are simple.
    """
    total_count   = 0
    total_reward  = 0.0
    for r in rows:
        if r.get("strategy") in strategies:
            cnt = int(r.get("count", 0))
            avg = float(r.get("avg_reward", 0.0))
            total_count  += cnt
            total_reward += avg * cnt
    if total_count == 0:
        return 0.0, 0
    return total_reward / total_count, total_count


def _classify_structured_pref(
    s_avg: float, s_count: int,
    p_avg: float, p_count: int,
    min_evidence: int = 3,
) -> Tuple[str, float]:
    """Compare structured vs paragraph weighted reward; return (label, score)."""
    # Not enough data yet — say so, neutral score.
    if s_count + p_count < min_evidence:
        return "Unknown", 0.5
    if s_count == 0:
        return "Paragraph (only)", max(0.0, (p_avg + 1.0) / 2.0)
    if p_count == 0:
        return "Structured (only)", max(0.0, (s_avg + 1.0) / 2.0)

    gap = s_avg - p_avg
    # Score on [0, 1]: 0.5 is neutral; higher = structured preference
    score = max(0.0, min(1.0, 0.5 + gap / 2.0))
    if gap > 0.20:
        return "Structured", score
    if gap < -0.20:
        return "Paragraph", score
    return "Mixed", score
