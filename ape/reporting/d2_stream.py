"""Streaming variant of the D2 answer, with the grounding gate intact.

WHY THIS IS NOT A PASSTHROUGH OF THE MODEL'S TOKENS
---------------------------------------------------
The grounding gate is the core safety property of this system: no figure
reaches a client unless it traces to the frozen snapshot. Piping the
model's stream straight to the browser would defeat it. The check runs on
a finished answer, so an ungrounded figure would already be on screen by
the time it failed, and "we replaced it a moment later" is not a defence
when the client has read it, screenshotted it, or acted on it.

So text is released only once it can be judged:

    tokens -> buffer -> cut at the last whitespace
                          |
                     every COMPLETED figure in that slice checked
                     against the same allowlist the non-streaming
                     path uses
                          |
                     clean -> emitted    failed -> stream stops,
                                                  answer replaced

A number still being typed — "£4,14" on its way to "£4,145.90" — never
leaves the server, because the validator cannot judge a figure it has not
finished reading.

In the common case, which is nearly all answers, the client sees text
arriving continuously instead of waiting for the whole reply. In the rare
failing case they see the opening of an answer replaced by the safe
decline, which is the same outcome the non-streaming path produces, just
visible.

WHAT THIS DELIBERATELY GIVES UP
-------------------------------
The retry. answer_question gets a second attempt with the rejected figures
quoted back, and that recovers most violations. It cannot here: by the
time a violation is known, text is on screen, and a silent second attempt
would rewrite words the client has already read. Streaming therefore
declines where the buffered path would have recovered — the trade is
lower perceived latency against a slightly higher decline rate, and it is
why answer_question is still the default for anything that is not the
live chat.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Iterator, Optional, Tuple

from sqlalchemy.orm import Session

from ape.db.models import Conversation, Message
from ape.reporting.chat_widgets import wants_visual
from ape.reporting.csv_source import ClientSnapshot
from ape.reporting.d2 import (DECLINE, STRATEGY_STYLE, _ANSWER_SYSTEM,
                              _check_answer, _choose_widget, _facts_for_scope,
                              classify_intent, select_strategy, source_blocks)


def _safe_prefix(buf: str) -> int:
    """How much of the buffer is safe to judge, and therefore to release.

    Everything up to the last whitespace. Anything after it may be half a
    word or half a number, and a partial figure cannot be validated.
    """
    cut = max(buf.rfind(" "), buf.rfind("\n"))
    return cut + 1 if cut >= 0 else 0


def stream_answer(
    session: Session,
    snap: ClientSnapshot,
    report_id: str,
    question: str,
    block: Optional[Dict] = None,
    selected_text: str = "",
    conversation_id: Optional[str] = None,
    report_json: Optional[Dict[str, Any]] = None,
) -> Iterator[Tuple[str, Any]]:
    """Yield ("delta", text) as the answer forms, then ("final", payload).

    The payload carries everything the non-streaming path returns, so the
    two remain interchangeable from the caller's side.
    """
    from ape.strategies.catalog import INTENT_STRATEGIES

    block_type = (block or {}).get("block_type") or (block or {}).get("type")
    intent = classify_intent(question, block_type)
    arms = INTENT_STRATEGIES.get(intent) or INTENT_STRATEGIES.get(
        "other_report_question", ["standard_llm"])
    strategy, table = select_strategy(session, intent, list(arms))

    facts_text, allowlist = _facts_for_scope(snap, block)
    if selected_text:
        facts_text += f'\nCLIENT HIGHLIGHTED THIS TEXT: "{selected_text[:400]}"'

    # Resolved before the answer is written, for the same reason as the
    # buffered path: the writer has to know a chart is coming, or it
    # apologises for being unable to draw one.
    widget, declined = None, ""
    if wants_visual(question):
        try:
            widget, declined = _choose_widget(question, intent,
                                              block_type or "", snap)
        except Exception:
            widget, declined = None, ""

    answer, author = DECLINE, "no_key"
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if api_key:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        style = STRATEGY_STYLE.get(strategy, STRATEGY_STYLE["concise_direct"])
        if widget:
            visual = ('\n\nA {kind} chart titled "{title}" is being shown '
                      'directly beneath your answer. Write text that '
                      'complements it — do not describe the chart, and never '
                      'say you cannot produce charts.').format(
                          kind=widget["kind"], title=widget["title"])
        elif declined:
            visual = ("\n\nNo chart can be drawn for this. Answer in words "
                      "only. Do not offer to draw one and do not explain why "
                      "— that is handled separately.")
        else:
            visual = ""
        prompt = (f"FACTS:\n{facts_text}\n\nQUESTION: {question}\n\n"
                  f"Answer format: {style}{visual}")

        buf, released, tripped = "", "", False
        try:
            with client.messages.stream(
                    model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
                    max_tokens=600, system=_ANSWER_SYSTEM,
                    messages=[{"role": "user",
                               "content": prompt}]) as stream:
                for piece in stream.text_stream:
                    buf += piece
                    cut = _safe_prefix(buf)
                    if not cut:
                        continue
                    chunk, buf = buf[:cut], buf[cut:]
                    # Validate what has been said SO FAR, not the chunk
                    # alone: a figure's context — the label that exempts a
                    # proper name, the sign in front of it — can sit in an
                    # earlier chunk.
                    if _check_answer(released + chunk, allowlist,
                                     snap.label_terms()):
                        tripped = True
                        break
                    released += chunk
                    yield ("delta", chunk)

                if not tripped:
                    candidate = (released + buf).strip()
                    if _check_answer(candidate, allowlist, snap.label_terms()):
                        tripped = True
                    else:
                        if buf:
                            yield ("delta", buf)
                        answer, author = candidate, "llm_stream"
        except Exception:
            tripped = True

        if tripped:
            # Nothing ungrounded was ever released. What WAS released is
            # the opening of an answer now being abandoned, so the client
            # is told to discard it rather than left with a fragment.
            answer, author = DECLINE, "declined_ungrounded"
            yield ("reset", DECLINE)

    if declined and answer != DECLINE:
        tail = (f"\n\nI can't chart that here — {declined}. Everything above "
                f"is what the report does record on it; your adviser can "
                f"supply the rest.")
        answer += tail
        yield ("delta", tail)

    # Persist exactly what was shown, for the same reason the buffered path
    # appends the decline before saving: a transcript that differs from
    # what the client read is a transcript of a different conversation.
    conv_id = conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
    if session.get(Conversation, conv_id) is None:
        session.add(Conversation(conversation_id=conv_id,
                                 client_id=snap.client_id,
                                 report_id=report_id))
    session.flush()
    a_id = f"msg_{uuid.uuid4().hex[:12]}"
    bids = [b for b in [(block or {}).get("block_id")] if b]
    session.add(Message(message_id=f"msg_{uuid.uuid4().hex[:12]}",
                        conversation_id=conv_id, client_id=snap.client_id,
                        report_id=report_id, role="client", content=question,
                        content_intent=intent, block_ids=bids))
    session.add(Message(message_id=a_id, conversation_id=conv_id,
                        client_id=snap.client_id, report_id=report_id,
                        role="assistant", content=answer,
                        content_intent=intent, answer_strategy=strategy,
                        block_ids=bids))

    try:
        sources = source_blocks(report_json or {}, snap, answer, block, intent)
    except Exception:
        sources = []

    yield ("final", {
        "answer": answer, "intent": intent, "strategy": strategy,
        "author": author, "conversation_id": conv_id, "message_id": a_id,
        "arms": table, "widget": widget, "widget_declined": declined,
        "sources": sources,
        "grounded_in": (block or {}).get("block_id") or "whole_report",
    })
