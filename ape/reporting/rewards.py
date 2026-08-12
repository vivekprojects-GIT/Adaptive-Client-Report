"""Signals -> rewards -> the two decisions, and the preference profile.

═══════════════════════════════════════════════════════════════════════════
ONE EVENT, THREE POSSIBLE DESTINATIONS
═══════════════════════════════════════════════════════════════════════════

Every client action lands in `events` verbatim. From there it may move up
to three things, and the routing is explicit because mixing them corrupts
all three:

  D2 arm   — thumbs on an ANSWER. Rewards the answer strategy that wrote
             it, in the intent context it was selected for. Nothing else.
  D1 arm   — engagement with the REPORT. Opened it, stayed with it, talked
             to it, said it helped. Rewards the template arm that produced
             the document.
  profile  — HOW they engaged. Asked for a table, asked for less jargon,
             thumbed-up an analogy. Moves the presentation dimensions the
             next report is written from.

A thumbs-down is evidence, not a reward: the Beta posterior needs to know
the arm was tried and disappointed, which is exactly reward 0.0.

═══════════════════════════════════════════════════════════════════════════
D1 REWARD IS CAPPED PER REPORT
═══════════════════════════════════════════════════════════════════════════

Engagement events accumulate into at most 1.0 per report, tracked on the
Report row. Without the cap, a chatty client would teach D1 that their
template is world-beating by asking eleven questions — volume of clicks
would masquerade as quality of document.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ape.db.models import ApeState, ClientPreference, Event, Message, Report

# ---------------------------------------------------------------------------
# Event vocabulary. Weights are the D1 engagement contribution.
# ---------------------------------------------------------------------------

D1_WEIGHTS = {
    "report_opened":    0.20,
    "dwell_60s":        0.20,   # stayed with the document
    "question_asked":   0.20,   # it provoked a conversation
    "pdf_downloaded":   0.15,   # kept it
    "report_helpful":   0.25,   # said so explicitly
}
# Explicit negative feedback zeroes nothing retroactively; it simply adds
# no reward and is preserved as evidence in the event row.

VALID_EVENTS = set(D1_WEIGHTS) | {
    "report_unhelpful", "block_highlighted", "answer_helpful",
    "answer_unhelpful", "section_viewed",
}


def record_event(session: Session, client_id: str, event_type: str,
                 report_id: str = "", block_id: str = "",
                 message_id: str = "", metadata: Optional[Dict] = None) -> Dict:
    """Store the raw event, then route its consequences."""
    if event_type not in VALID_EVENTS:
        return {"stored": False, "reason": f"unknown event '{event_type}'"}

    session.add(Event(
        event_id=f"ev_{uuid.uuid4().hex[:12]}", client_id=client_id,
        report_id=report_id, block_id=block_id, message_id=message_id,
        event_type=event_type,
        applies_to=("D2" if event_type.startswith("answer_") else "D1"),
        metadata_json=metadata or {}))

    out = {"stored": True, "event": event_type}
    if event_type in ("answer_helpful", "answer_unhelpful") and message_id:
        out["d2"] = _reward_d2(session, message_id,
                               1.0 if event_type == "answer_helpful" else 0.0)
    if event_type in D1_WEIGHTS or event_type == "report_unhelpful":
        out["d1"] = _reward_d1(session, report_id, event_type)
    dims = _dims_from_event(event_type, metadata or {})
    if dims:
        out["profile"] = update_preferences(session, client_id, dims)
    return out


# ---------------------------------------------------------------------------
# D2 — Beta update on the exact arm that wrote the answer
# ---------------------------------------------------------------------------

def _reward_d2(session: Session, message_id: str, reward: float) -> Dict:
    msg = session.get(Message, message_id)
    if msg is None or not msg.answer_strategy:
        return {"applied": False, "reason": "message or strategy not found"}
    row = session.scalars(select(ApeState).where(
        ApeState.decision == "D2", ApeState.scope_type == "GLOBAL",
        ApeState.context == msg.content_intent,
        ApeState.arm_id == msg.answer_strategy)).first()
    if row is None:
        row = ApeState(scope_type="GLOBAL", scope_id="_global",
                       decision="D2", context=msg.content_intent,
                       arm_id=msg.answer_strategy,
                       alpha=1.0, beta=1.0, selection_count=0,
                       reward_count=0, total_reward=0.0)
        session.add(row)
    row.reward_count += 1
    row.total_reward += reward
    row.updated_at = datetime.utcnow()
    return {"applied": True, "intent": msg.content_intent,
            "arm": msg.answer_strategy, "reward": reward,
            "arm_totals": {"rewards": row.reward_count,
                           "total": round(row.total_reward, 2)}}


# ---------------------------------------------------------------------------
# D1 — capped engagement accrual against the template arm (Mongo state,
# where D1 selection reads it)
# ---------------------------------------------------------------------------

def _reward_d1(session: Session, report_id: str, event_type: str) -> Dict:
    rep = session.get(Report, report_id)
    if rep is None:
        return {"applied": False, "reason": "report not in SQL"}

    already = rep.normalized_reward or 0.0
    weight = D1_WEIGHTS.get(event_type, 0.0)

    # Each event type pays out once per report. The events table is the
    # dedupe source of truth — this event was just added, so >1 means seen.
    n_same = session.scalar(
        select(Event.event_id).where(
            Event.report_id == report_id,
            Event.event_type == event_type).limit(2).offset(1))
    if n_same is not None:
        return {"applied": False, "reason": "event already rewarded",
                "accrued": already}

    delta = min(weight, 1.0 - already)
    rep.normalized_reward = round(already + delta, 4)
    rep.reward_status = "ACCRUING"
    if delta <= 0:
        return {"applied": False, "reason": "report reward capped at 1.0",
                "accrued": already}

    # The mongo store is where D1 selection reads count/total_reward.
    applied_mongo = False
    try:
        # The API process already holds the connected store; reuse it rather
        # than opening a second Mongo client per event.
        from ape import api as _api
        from ape.reporting.d1 import cell_key
        store = _api.STORE
        store.bandit_state.update_one(
            {"cell_key": cell_key(rep.report_type),
             "strategy": rep.template_arm},
            {"$inc": {"total_reward": delta}}, upsert=True)
        applied_mongo = True
    except Exception:
        pass                     # SQL keeps the truth; mongo catches up later

    return {"applied": True, "arm": rep.template_arm, "delta": delta,
            "accrued": rep.normalized_reward, "mongo": applied_mongo}


# ---------------------------------------------------------------------------
# Preference profile — the bridge to next quarter's report
# ---------------------------------------------------------------------------

# What each event says about HOW this client wants to be written to.
# Direction: +1 pushes the dimension toward 1, -1 toward 0.
_EVENT_DIMS = {
    "pdf_downloaded": {},        # keeping the report says nothing about style
}

_FORMAT_CUES = [
    (("table", "in a table", "as a table"),            "table", +1),
    (("chart", "graph", "visual", "picture", "show me"), "visual", +1),
    (("short", "brief", "briefly", "quick", "tl;dr",
      "one line", "in short"),                         "concise", +1),
    (("more detail", "in detail", "explain more", "elaborate",
      "break it down", "walk me through"),             "detail", +1),
    (("walk me through", "step by step", "one step"),  "step_by_step", +1),
    (("exact", "precise", "decimal", "exactly"),       "numeric_precision", +1),
    (("compare", "versus", "vs", "against", "benchmark"), "comparison", +1),
    (("simpler", "plain english", "layman", "jargon",
      "simple terms", "don't understand", "confus"),   "technical_depth", -1),
]

# A thumbs-up on an answer endorses the STYLE of that answer.
_STRATEGY_DIMS = {
    "bullet_summary":        [("concise", +1)],
    "one_liner":             [("concise", +1)],
    "short_paragraph":       [("concise", +1)],
    "step_by_step_reasoning": [("step_by_step", +1), ("detail", +1)],
    "numbered_steps":        [("step_by_step", +1)],
    "analogy_explanation":   [("technical_depth", -1), ("narrative", +1)],
    "definition_plus_example": [("technical_depth", -1)],
    "pros_cons_table":       [("table", +1), ("comparison", +1)],
    "bullet_contrast":       [("comparison", +1)],
    "decision_card":         [("concise", +1), ("numeric_precision", +1)],
}


def dims_from_question(question: str) -> Dict[str, int]:
    q = question.lower()
    dims: Dict[str, int] = {}
    for cues, dim, direction in _FORMAT_CUES:
        if any(c in q for c in cues):
            dims[dim] = direction
    return dims


def dims_from_strategy_feedback(strategy: str, positive: bool) -> Dict[str, int]:
    """Thumbs-up endorses the style; thumbs-down pushes gently away."""
    out = {}
    for dim, direction in _STRATEGY_DIMS.get(strategy, []):
        out[dim] = direction if positive else -direction
    return out


def _dims_from_event(event_type: str, metadata: Dict) -> Dict[str, int]:
    if event_type == "question_asked":
        return dims_from_question(str(metadata.get("question", "")))
    if event_type in ("answer_helpful", "answer_unhelpful"):
        return dims_from_strategy_feedback(
            str(metadata.get("strategy", "")),
            event_type == "answer_helpful")
    return {}


_COLUMN = {"table": "table_pref"}     # SQL-reserved word workaround


def update_preferences(session: Session, client_id: str,
                       dims: Dict[str, int]) -> Dict:
    """Move each named dimension toward its target with a step that shrinks
    as evidence accumulates:

        step = 1 / (n + 4)         n = meaningful signals so far

    First signals move the profile visibly (n=0 -> 0.20 of the distance);
    the fiftieth barely nudges it. That is the same philosophy as the
    evidence weight w = n/(n+20) used at selection time: early evidence is
    provisional, late evidence is stable, and no single event ever owns
    the profile.
    """
    pref = session.get(ClientPreference, client_id)
    if pref is None:
        pref = ClientPreference(client_id=client_id)
        session.add(pref)
    n = pref.meaningful_signal_count
    step = 1.0 / (n + 4)
    moved = {}
    for dim, direction in dims.items():
        col = _COLUMN.get(dim, dim)
        if not hasattr(pref, col):
            continue
        old = getattr(pref, col)
        target = 1.0 if direction > 0 else 0.0
        new = round(old + step * (target - old), 4)
        setattr(pref, col, new)
        moved[dim] = {"from": round(old, 3), "to": new}
    if moved:
        pref.meaningful_signal_count = n + 1
        pref.updated_at = datetime.utcnow()
    return {"signals_so_far": pref.meaningful_signal_count, "moved": moved}
