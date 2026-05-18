"""
Offer recommender — looks up `entity_type=offer_policy` rows in ape_config and
matches them against a user's topic interest scores.

Policy doc shape:
  {
    entity_type:               "offer_policy",
    entity_id:                 "<topic_normalized>",
    domain:                    "finance",
    offer_type:                "retirement_planning_consultation",
    description:               "Schedule a 30-min retirement planning call",
    min_interest_score:        0.80,
    status:                    "ACTIVE",

    # Optional per-offer weight overrides (else fall back to compute.W_*).
    # Each weight is non-negative; we normalize so they sum to 1 before
    # applying so the operator can think in raw "importance" terms rather
    # than fractions.
    weight_frequency:          0.40,
    weight_recency:            0.25,
    weight_engagement:         0.25,
    weight_followup:           0.10,
  }

We deliberately keep this layer thin — it surfaces eligible offers but the
actual decision to contact a user must still go through downstream compliance
(do_not_contact lists, jurisdictional rules, etc.) before any outreach fires.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..store import MongoStore
from ..store.mongo_schema import (
    COL_USER_TOPIC_INTEREST,
    ENTITY_OFFER_POLICY,
    STATUS_ACTIVE,
)
from .compute import W_ENGAGE, W_FOLLOWUP, W_FREQ, W_RECENCY


def _resolve_weights(policy: Dict[str, Any]) -> Dict[str, float]:
    """Pick the per-offer weights, falling back to the global defaults.

    Returns the four weights normalized so they sum to 1.0 — that way the
    computed `interest_score` stays comparable across offers regardless of
    whether the admin entered raw percentages (40/25/25/10) or "importance"
    numbers (4/2.5/2.5/1) — both produce the same effective ratio.
    """
    def _get(key: str, default: float) -> float:
        v = policy.get(key)
        try:
            return max(0.0, float(v)) if v is not None else default
        except (TypeError, ValueError):
            return default

    raw = {
        "frequency":  _get("weight_frequency",  W_FREQ),
        "recency":    _get("weight_recency",    W_RECENCY),
        "engagement": _get("weight_engagement", W_ENGAGE),
        "followup":   _get("weight_followup",   W_FOLLOWUP),
    }
    total = sum(raw.values())
    if total <= 0:
        # Pathological case — fall back entirely to defaults
        return {
            "frequency":  W_FREQ,
            "recency":    W_RECENCY,
            "engagement": W_ENGAGE,
            "followup":   W_FOLLOWUP,
        }
    return {k: v / total for k, v in raw.items()}


def _score_for_offer(
    interest_row: Optional[Dict[str, Any]],
    weights: Dict[str, float],
) -> Tuple[float, Optional[Dict[str, float]]]:
    """Apply this offer's weights to the user's stored sub-scores.

    Returns (interest_score, breakdown) where breakdown shows each component's
    contribution. None if the user has no interest row for this topic yet.
    """
    if interest_row is None:
        return 0.0, None

    freq   = float(interest_row.get("frequency_score", 0.0))
    rec    = float(interest_row.get("recency_score", 0.0))
    eng    = float(interest_row.get("engagement_score", 0.0))
    foll   = float(interest_row.get("followup_depth_score", 0.0))

    breakdown = {
        "frequency":  round(weights["frequency"]  * freq, 4),
        "recency":    round(weights["recency"]    * rec,  4),
        "engagement": round(weights["engagement"] * eng,  4),
        "followup":   round(weights["followup"]   * foll, 4),
    }
    score = sum(breakdown.values())
    return round(score, 4), breakdown


def eligible_offers_for_user(
    store: MongoStore,
    user_id_hash: str,
    domain: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return offers the user is eligible for, sorted by their interest_score.

    Eligibility is now gated by THREE checks:
      1. score >= min_interest_score    (interest gate)
      2. compliance_eligible == True    (jurisdictional / regulatory)
      3. do_not_contact == False        (hard user opt-out)

    The reason string explains exactly which check failed (or all passed).
    """
    # 1. Pull all active offer policies
    q: Dict[str, Any] = {"entity_type": ENTITY_OFFER_POLICY, "status": STATUS_ACTIVE}
    if domain:
        q["domain"] = domain
    policies = list(store.config.find(q))
    if not policies:
        return []

    # 2. Pull the user's topic interest scores
    interest_rows = list(
        store.db[COL_USER_TOPIC_INTEREST].find({"user_id_hash": user_id_hash})
    )
    by_topic = {(r["domain"], r["topic"]): r for r in interest_rows}

    # 3. Pull compliance flags from the directory (one lookup per user)
    directory = store.get_directory_entry(user_id_hash) or {}
    do_not_contact = bool(directory.get("do_not_contact", False))
    compliance_ok  = bool(directory.get("compliance_eligible", True))

    results: List[Dict[str, Any]] = []
    for p in policies:
        topic   = p["entity_id"]
        d       = p.get("domain", domain or "")
        threshold = float(p.get("min_interest_score", 0.7))

        interest = by_topic.get((d, topic))

        # Per-offer reweighting — apply this offer's weights to the user's
        # stored sub-scores. If the user has no interest row yet, score=0.
        weights = _resolve_weights(p)
        score, breakdown = _score_for_offer(interest, weights)

        score_ok = score >= threshold
        eligible = score_ok and compliance_ok and not do_not_contact

        # Most specific failure reason wins
        if do_not_contact:
            reason = "user has do_not_contact set — outreach blocked"
        elif not compliance_ok:
            reason = "user failed compliance check — not eligible for outreach"
        elif not score_ok:
            reason = (
                f"interest_score {score:.2f} below threshold {threshold:.2f} "
                f"— nurture before offering"
            )
        else:
            # Build a positive narrative for eligible offers
            top_components = sorted(
                (breakdown or {}).items(), key=lambda kv: -kv[1]
            )[:2]
            top_contrib = ", ".join(
                f"{k} contributes {v:.2f}" for k, v in top_components
            )
            reason = (
                f"score {score:.2f} ≥ {threshold:.2f} threshold; "
                f"{top_contrib}; compliance + consent gates pass"
            )

        results.append({
            "offer_type":         p.get("offer_type"),
            "description":        p.get("description", ""),
            "topic":              topic,
            "domain":             d,
            "min_interest_score": threshold,
            "interest_score":     round(score, 3),

            # Eligibility (3-way gated)
            "eligible":           eligible,
            "reason":             reason,
            "score_ok":           score_ok,
            "compliance_ok":      compliance_ok,
            "do_not_contact":     do_not_contact,

            # Scoring transparency
            "weights":            {k: round(v, 3) for k, v in weights.items()},
            "score_breakdown":    breakdown,
        })

    # Sort: eligible first, then by score
    results.sort(key=lambda r: (not r["eligible"], -r["interest_score"]))
    return results
