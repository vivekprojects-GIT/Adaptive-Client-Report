"""
Composite signal detection — recognizes meaningful multi-signal patterns.

The bandit reward pipeline calls `detect_composite()` BEFORE the atomic
resolver. If a composite pattern matches the buffered signals, its name
replaces the atomic winner — preserving the richer multi-signal label so
analytics and instruction-quality consumers see the real pattern.

This module is the SECOND layer of the two-layer signal architecture:

  Layer 1  — atomic signals (routing.py):       single user action / system event
  Layer 2  — composite patterns (this file):    detected combinations / sequences

Each composite has a `triggers` function returning True/False for a given
buffered signal list. Functions are kept simple and pure so they're easy
to test, audit, and extend.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from .routing import COMPOSITE_PRIORITY, SIGNAL_CATALOG


# ---------------------------------------------------------------------------
# Semantic direction sets — used for consensus composites.
#
# These are HARDCODED by semantic intent, not derived from reward routing.
# Why hardcoded? Because thumbs_up/down are correctly routed to None on
# both reward axes (they're ambiguous about cause), but they're still
# positive/negative SEMANTICALLY — and a consensus composite like
# "engaged_positive" should count them.
#
# If you add new atomic signals, list them in the appropriate set below.
# Composite signals themselves are excluded — they never participate in
# consensus checks (we don't want pattern_engaged_positive to recurse).
# ---------------------------------------------------------------------------

POSITIVE_ATOMICS: Set[str] = {
    # UI
    "thumbs_up",
    "copy_save",
    # LLM-detected text
    "format_keep_request",
    "it_worked_statement",
    "deeper_question",
    # Derived / automatic
    "format_compliance_pass",
    "session_continue",
}

NEGATIVE_ATOMICS: Set[str] = {
    # UI
    "thumbs_down",
    "regenerate_click",
    # LLM-detected text
    "format_change_request",
    "content_correction",
    "reask_same_question",
    # Derived / automatic
    "format_compliance_fail",
    "session_abandon",
}


# ---------------------------------------------------------------------------
# Trigger functions — one per composite. All take the same shape:
#
#   pending: List[Dict] where each entry is
#            {"signal": str, "source": str, "ts": iso_str, "age_sec": float}
#   age_seconds_response: float (how long since the response was rendered)
#
# Returns True iff the composite pattern matches.
# ---------------------------------------------------------------------------

def _names(pending: List[Dict]) -> List[str]:
    return [p["signal"] for p in pending]


def _has(pending: List[Dict], name: str) -> bool:
    return any(p["signal"] == name for p in pending)


def _ts_of(pending: List[Dict], name: str) -> Optional[float]:
    """Return age-in-seconds-since-response of the FIRST occurrence of name."""
    for p in pending:
        if p["signal"] == name:
            return p.get("age_sec", 0.0)
    return None


# Tier 1 — Axis-explicit consensus

def trig_explicit_format_consensus_neg(pending: List[Dict], age: float) -> bool:
    return _has(pending, "format_change_request") and (
        _has(pending, "regenerate_click") or _has(pending, "thumbs_down")
    )


def trig_explicit_format_consensus_pos(pending: List[Dict], age: float) -> bool:
    return _has(pending, "format_keep_request") and (
        _has(pending, "copy_save") or _has(pending, "session_continue")
    )


def trig_content_failure_confirmed(pending: List[Dict], age: float) -> bool:
    return _has(pending, "content_correction") and (
        _has(pending, "regenerate_click") or _has(pending, "thumbs_down")
    )


# Tier 2 — Temporal mind-changes

def trig_regret(pending: List[Dict], age: float) -> bool:
    """thumbs_up THEN regenerate_click within 60s"""
    if not (_has(pending, "thumbs_up") and _has(pending, "regenerate_click")):
        return False
    t_up = _ts_of(pending, "thumbs_up")
    t_regen = _ts_of(pending, "regenerate_click")
    if t_up is None or t_regen is None:
        return False
    return t_regen > t_up and (t_regen - t_up) <= 60


def trig_change_of_heart(pending: List[Dict], age: float) -> bool:
    """thumbs_down THEN thumbs_up within 60s"""
    if not (_has(pending, "thumbs_down") and _has(pending, "thumbs_up")):
        return False
    t_down = _ts_of(pending, "thumbs_down")
    t_up = _ts_of(pending, "thumbs_up")
    if t_down is None or t_up is None:
        return False
    return t_up > t_down and (t_up - t_down) <= 60


def trig_abandoned_after_approval(pending: List[Dict], age: float) -> bool:
    """thumbs_up THEN session_abandon within 120s"""
    if not (_has(pending, "thumbs_up") and _has(pending, "session_abandon")):
        return False
    t_up = _ts_of(pending, "thumbs_up")
    t_abandon = _ts_of(pending, "session_abandon")
    if t_up is None or t_abandon is None:
        return False
    return t_abandon > t_up and (t_abandon - t_up) <= 120


# Tier 3 — Behavioral consensus

def trig_format_endorsed_through_behavior(pending: List[Dict], age: float) -> bool:
    """copy_save AND session_continue within 90s of response"""
    if not (_has(pending, "copy_save") and _has(pending, "session_continue")):
        return False
    return age <= 90


def trig_confused_negative(pending: List[Dict], age: float) -> bool:
    """regenerate_click AND reask_same_question on same response"""
    return _has(pending, "regenerate_click") and _has(pending, "reask_same_question")


# Tier 4 — Weak consensus / catch-alls

def trig_engaged_positive(pending: List[Dict], age: float) -> bool:
    """≥3 positive atomic signals on the same response"""
    n_positive = sum(1 for p in pending if p["signal"] in POSITIVE_ATOMICS)
    return n_positive >= 3


def trig_silent_acceptance(pending: List[Dict], age: float) -> bool:
    """ONLY session_continue fired — no UI clicks, no LLM signals"""
    names = set(_names(pending))
    return names == {"session_continue"} and age <= 120


# Dispatch table — keep in same order as COMPOSITE_PRIORITY
COMPOSITE_TRIGGERS = {
    "pattern_explicit_format_consensus_neg":   trig_explicit_format_consensus_neg,
    "pattern_explicit_format_consensus_pos":   trig_explicit_format_consensus_pos,
    "pattern_content_failure_confirmed":       trig_content_failure_confirmed,
    "pattern_regret":                          trig_regret,
    "pattern_change_of_heart":                 trig_change_of_heart,
    "pattern_abandoned_after_approval":        trig_abandoned_after_approval,
    "pattern_format_endorsed_through_behavior": trig_format_endorsed_through_behavior,
    "pattern_confused_negative":               trig_confused_negative,
    "pattern_engaged_positive":                trig_engaged_positive,
    "pattern_silent_acceptance":               trig_silent_acceptance,
}


def detect_composite(pending: List[Dict], age_seconds_response: float) -> Optional[str]:
    """Run composite detection in priority order. Return first match, or None.

    Args:
      pending:               list of fired signal dicts buffered on the response
      age_seconds_response:  seconds since the response was rendered

    Returns:
      Composite signal name (one of COMPOSITE_PRIORITY) or None.
    """
    for name in COMPOSITE_PRIORITY:
        trigger = COMPOSITE_TRIGGERS.get(name)
        if trigger is None:
            continue
        try:
            if trigger(pending, age_seconds_response):
                return name
        except Exception:
            # Trigger functions should be defensive — skip silently if one
            # raises so a bad pattern doesn't block reward application.
            continue
    return None
