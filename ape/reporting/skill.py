"""Client skill — what this person's own behaviour has taught us.

The bandit learns by rewarding an ARM. A composed layout is not an arm, so
composition had no way to improve: every report started from the same blank
sheet no matter how many the client had already read.

This closes that loop with a different mechanism. Instead of a scalar
reward attached to a fixed choice, it accumulates a written brief from what
the client actually did — which sections they highlighted, what they asked
for in words, which layouts held their attention — and hands that brief to
the composer next time. Learning by accumulated instruction rather than by
arm reward.

WHY A BRIEF RATHER THAN MORE NUMBERS
------------------------------------
The nine preference dimensions already carry the numeric signal, and the
composer receives them. What they cannot express is specificity: that this
client returns to the fees section every quarter, or asked twice for a
table. A brief can say that, and a model can act on it. It is also
readable, so an advisor can check what the system believes about a client
and correct it — which a vector of nine floats is not.

WHAT IT MAY AND MAY NOT INFLUENCE
---------------------------------
Presentation only, exactly like every other learned signal: which blocks,
what order, how much explanation. It never reaches the facts, and a skill
claiming a client "does not care about fees" still cannot remove the fees
table — the coverage gate appends it regardless.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ape.db.models import (ClientPreference, ClientSkill, Event, Message,
                           Report, ReportBlock)

# Below this, a client's own behaviour is too thin to generalise from and
# the brief says so rather than inventing a personality from two clicks.
MIN_EVIDENCE = 3

# Phrases worth quoting back to the composer verbatim. A request in the
# client's own words carries more than the dimension it nudged.
_REQUEST_PATTERNS = [
    (r"\b(table|tabular)\b", "asked for information in a table"),
    (r"\b(chart|graph|visual|picture|show me)\b", "asked to see it visually"),
    (r"\b(simple|simpler|plain english|layman|jargon)\b",
     "asked for simpler language"),
    (r"\b(short|brief|quick|summary|tl;dr)\b", "asked for a shorter answer"),
    (r"\b(detail|explain more|elaborate|break it down|walk me through)\b",
     "asked for more detail"),
    (r"\b(compare|versus|vs\b|against|benchmark)\b",
     "asked for comparison against the benchmark"),
    (r"\b(exact|precise|decimal)\b", "asked for exact figures"),
]


def _block_family(block_id: str) -> str:
    """fees_table_06 -> fees_table. Block ids carry a position suffix that
    changes between reports, so raw ids cannot be counted across them."""
    return re.sub(r"_\d+$", "", block_id or "")


def gather_evidence(session: Session, client_id: str) -> Dict[str, Any]:
    """Everything this client's behaviour says, as structured counts."""
    highlights = Counter()
    for bid, n in session.execute(
            select(Event.block_id, func.count())
            .where(Event.client_id == client_id, Event.block_id != "")
            .group_by(Event.block_id)).all():
        highlights[_block_family(bid)] += n

    questions = list(session.scalars(
        select(Message).where(Message.client_id == client_id,
                              Message.role == "client")
        .order_by(Message.created_at.desc()).limit(40)))

    requests = Counter()
    for m in questions:
        low = (m.content or "").lower()
        for pattern, phrase in _REQUEST_PATTERNS:
            if re.search(pattern, low):
                requests[phrase] += 1

    intents = Counter(m.content_intent for m in questions if m.content_intent)

    reports = list(session.scalars(
        select(Report).where(Report.client_id == client_id)
        .order_by(Report.created_at.desc()).limit(12)))
    engaged = [(r.template_arm, r.normalized_reward or 0.0, r.report_id)
               for r in reports if r.normalized_reward]

    # Blocks that were SENT but never once highlighted or asked about.
    sent = Counter()
    for rb in session.scalars(select(ReportBlock)
                              .where(ReportBlock.client_id == client_id)):
        sent[_block_family(rb.block_id)] += 1
    ignored = [b for b, n in sent.items()
               if n >= 2 and highlights.get(b, 0) == 0
               and b not in ("disclosures", "explainer")]

    # Charts the client asked for in the chat, as (subject, treatment)
    # pairs. This is the strongest evidence in here: everything else is
    # inferred from behaviour, whereas this is the client stating outright
    # how they want a particular subject shown. Declines are counted apart
    # — they say what the client wanted, not what worked.
    visuals, unmet = Counter(), Counter()
    for ev in session.scalars(
            select(Event).where(Event.client_id == client_id,
                                Event.event_type == "visual_requested")
            .order_by(Event.created_at.desc()).limit(40)):
        meta = ev.metadata_json or {}
        if meta.get("drawn") and meta.get("binding"):
            visuals[(meta["binding"], meta.get("kind", ""))] += 1
        elif meta.get("reason"):
            unmet[str(meta["reason"])] += 1

    pref = session.get(ClientPreference, client_id)
    return {
        "highlights": highlights, "requests": requests, "intents": intents,
        "engaged": engaged, "ignored": sorted(ignored),
        "visuals": visuals, "unmet": unmet,
        "n_questions": len(questions),
        "signals": pref.meaningful_signal_count if pref else 0,
        "dimensions": pref.as_dimensions() if pref else {},
    }


def render_brief(evidence: Dict[str, Any]) -> str:
    """The evidence as instructions a composer can act on."""
    total = (sum(evidence["highlights"].values()) + evidence["n_questions"])
    if total < MIN_EVIDENCE:
        return ("No meaningful interaction history yet. Use a balanced "
                "layout and do not infer preferences from nothing.")

    out: List[str] = []

    # First, because it is the only evidence here the client stated in so
    # many words. Everything below it is inference from behaviour, and
    # inference should not outrank someone telling you what they want.
    for (binding, kind), n in evidence.get("visuals", Counter()).most_common(3):
        subject = binding.replace("_", " ")
        times = f" ({n}x)" if n > 1 else ""
        out.append(f"Asked to see {subject} as a {kind} chart{times}. "
                   f"Build that view into the report so they do not have "
                   f"to ask again.")

    for reason, n in evidence.get("unmet", Counter()).most_common(2):
        out.append(f"Asked for a chart we could not draw{f' ({n}x)' if n > 1 else ''}: "
                   f"{reason}. Do not promise this view — the data is not there.")

    top = evidence["highlights"].most_common(3)
    if top:
        named = ", ".join(f"{b} ({n}x)" for b, n in top)
        out.append(f"Returns to these sections: {named}. Place them early "
                   f"and give them room.")

    if evidence["ignored"]:
        out.append(f"Has never engaged with: "
                   f"{', '.join(evidence['ignored'][:4])}. Keep them, but "
                   f"later and in their most compact form.")

    for phrase, n in evidence["requests"].most_common(3):
        out.append(f"Repeatedly {phrase} ({n}x)." if n > 1
                   else f"Once {phrase}.")

    asks = [i for i, _ in evidence["intents"].most_common(2)]
    if asks:
        out.append("Questions usually about: "
                   + ", ".join(a.replace("_", " ") for a in asks) + ".")

    if evidence["engaged"]:
        best = max(evidence["engaged"], key=lambda x: x[1])
        worst = min(evidence["engaged"], key=lambda x: x[1])
        if best[1] > worst[1]:
            out.append(f"Engaged most with a '{best[0]}' layout "
                       f"({best[1]:.0%}), least with '{worst[0]}' "
                       f"({worst[1]:.0%}).")

    return "\n".join(f"- {line}" for line in out)


def refresh_skill(session: Session, client_id: str) -> ClientSkill:
    """Recompute and persist. Persisted rather than derived on the fly so an
    advisor can read what the system believes and correct it."""
    ev = gather_evidence(session, client_id)
    brief = render_brief(ev)
    row = session.get(ClientSkill, client_id)
    if row is None:
        row = ClientSkill(client_id=client_id)
        session.add(row)
    row.brief = brief
    row.evidence_count = (sum(ev["highlights"].values()) + ev["n_questions"])
    row.top_blocks = [b for b, _ in ev["highlights"].most_common(5)]
    row.ignored_blocks = ev["ignored"][:5]
    return row


def skill_text(session: Session, client_id: str) -> str:
    """The brief for the composer prompt. Falls back to computing it if no
    row exists yet, so a first composition still benefits from any history
    already on file."""
    row = session.get(ClientSkill, client_id)
    if row is not None and row.brief:
        # An advisor override always wins: if someone has written what this
        # client wants, that is better evidence than inferred behaviour.
        return (row.advisor_note + "\n" + row.brief) if row.advisor_note \
            else row.brief
    return render_brief(gather_evidence(session, client_id))
