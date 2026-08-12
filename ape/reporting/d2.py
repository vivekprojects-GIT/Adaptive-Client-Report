"""D2 — how a question about the report gets answered.

D1 chose what the report looks like. D2 chooses what an ANSWER looks like,
one question at a time. Different decision, different evidence, different
reward — a thumbs-down on an answer says nothing about whether the report
should have been a table, which is why the two never share state.

═══════════════════════════════════════════════════════════════════════════
LOCALISATION IS THE GROUNDING STORY
═══════════════════════════════════════════════════════════════════════════

When the client highlights a block, that block's `source_refs` name the
snapshot facts in scope. The answer is generated from those facts plus the
block's own numbers — no retrieval, no similarity search, no chance of
pulling in another client's figures. "I don't understand this section" is
answerable precisely because the highlight says which section.

With no highlight, the whole report's facts are in scope — still only this
client's frozen snapshot. Questions the snapshot cannot answer get a
truthful decline and a pointer to the adviser, not an improvisation. This
is a regulated conversation; "I don't know" is a feature.

═══════════════════════════════════════════════════════════════════════════
THE DECISION
═══════════════════════════════════════════════════════════════════════════

context  = question intent (classified, closed vocabulary)
arms     = answer strategies from the catalogue for that intent
policy   = contextual UCB over reward means in SQL `ape_state`
           (decision="D2", scope GLOBAL for now; client scope arrives with
           evidence, same as D1)
reward   = thumbs on the answer, follow-up behaviour

Every answer records which arm produced it on the Message row, so the
thumb that arrives minutes later can find its way back.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from ape.db.models import ApeState, Conversation, Message
from ape.reporting.csv_source import ClientSnapshot
from ape.reporting.grounding import derived_facts, extract_numbers, _matches

# ---------------------------------------------------------------------------
# Intent classification — closed vocabulary, keyword-first
# ---------------------------------------------------------------------------
# Keywords answer most questions instantly and cost nothing. The LLM is only
# consulted when keywords say nothing, and its output is snapped to the same
# closed vocabulary so a hallucinated label cannot enter the system.

INTENT_KEYWORDS: List[Tuple[str, Tuple[str, ...]]] = [
    ("fees_cashflow_question", ("fee", "fees", "cost", "charge", "expense",
                                "contribution", "withdrawal", "deposit")),
    ("benchmark_comparison",   ("benchmark", "compare", "compared", "versus",
                                "vs", "index", "outperform", "underperform",
                                "behind", "ahead")),
    ("allocation_question",    ("allocation", "allocated", "mix", "weight",
                                "diversif", "asset class", "rebalanc",
                                "target")),
    ("risk_question",          ("risk", "volatil", "safe", "safety", "worried",
                                "worry", "lose", "drawdown", "protect")),
    ("holdings_question",      ("holding", "holdings", "position", "stock",
                                "fund", "own", "invested in")),
    ("performance_question",   ("return", "performance", "gain", "loss",
                                "grew", "growth", "decline", "went down",
                                "went up", "why did", "drop")),
    ("report_summary",         ("summary", "summarise", "summarize",
                                "overview", "in short", "tl;dr", "overall")),
]

BLOCK_INTENT_HINT = {
    "fees_table": "fees_cashflow_question",
    "comparison_chart": "benchmark_comparison",
    "comparison_table": "performance_question",
    "allocation_donut": "allocation_question",
    "allocation_vs_target": "allocation_question",
    "holdings_table": "holdings_question",
    "top_contributors": "performance_question",
    "top_detractors": "performance_question",
    "returns_table": "performance_question",
    "performance_line": "performance_question",
    "risk_card": "risk_question",
    "kpi_grid": "report_summary",
    "key_takeaways": "report_summary",
}


def classify_intent(question: str, block_type: Optional[str] = None) -> str:
    q = question.lower()
    for intent, words in INTENT_KEYWORDS:
        if any(w in q for w in words):
            return intent
    # "What does this mean?" against a highlighted block: the block itself
    # is the intent.
    if block_type:
        if any(w in q for w in ("what", "explain", "mean", "understand",
                                "this", "why")):
            return BLOCK_INTENT_HINT.get(block_type,
                                         "explain_selected_content")
    return "other_report_question"


# ---------------------------------------------------------------------------
# Strategy selection — Thompson over SQL ape_state
# ---------------------------------------------------------------------------

PRIOR_STRENGTH = 2.0   # fallback; the live values are admin-editable


def _live_params() -> Tuple[float, float]:
    from ape.reporting.policy_config import selection_params
    v = selection_params()
    return v["prior_strength_d2"], v["exploration_c"]


def select_strategy(session: Session, intent: str,
                    arms: List[str], rng=None) -> Tuple[str, List[Dict]]:
    """One Beta draw per arm; highest draw answers. State rows are created
    lazily at first selection so the admin table only shows arms that have
    actually been in play."""
    strength, c = _live_params()
    rows = {r.arm_id: r for r in session.scalars(
        select(ApeState).where(ApeState.decision == "D2",
                               ApeState.scope_type == "GLOBAL",
                               ApeState.context == intent))}
    n_total = sum(r.selection_count for r in rows.values())
    table = []
    best, best_score = arms[0], -1.0
    for arm in arms:
        r = rows.get(arm)
        count = r.selection_count if r else 0
        reward = r.total_reward if r else 0.0
        # Neutral 0.5 prior as pseudo-observations; the mean uses rewarded
        # turns, the bonus decays with how often the arm has been SERVED —
        # an arm that answers constantly but never earns a thumb loses its
        # optimism, which is exactly right.
        n_eff = count + strength
        mean = (strength * 0.5 + reward) / (strength + (r.reward_count if r else 0))
        score = mean + c * math.sqrt(
            2.0 * math.log(max(n_total, 0) + strength + 1.0) / n_eff)
        table.append({"arm": arm, "ucb": round(score, 4),
                      "count": count,
                      "rewards": r.reward_count if r else 0,
                      "total_reward": round(reward, 2) if r else 0.0})
        if score > best_score:
            best, best_score = arm, score

    row = rows.get(best)
    if row is None:
        row = ApeState(scope_type="GLOBAL", scope_id="_global", decision="D2",
                       context=intent, arm_id=best,
                       alpha=1.0, beta=1.0, selection_count=0,
                       reward_count=0, total_reward=0.0)
        session.add(row)
    row.selection_count += 1
    row.updated_at = datetime.utcnow()
    return best, table


STRATEGY_STYLE = {
    # The six live arms — these names MUST match ape_config strategies and
    # INTENT_STRATEGIES in the catalogue. A name that matches nothing here
    # silently gets the default style, which is how a mismatch hides.
    "concise_direct":     "One short, direct paragraph. Lead with the figure.",
    "structured_bullets": "3-5 bullets, one fact each, no preamble.",
    "detailed_narrative": ("A flowing explanation of the why behind the "
                           "figures, the way an adviser would talk it "
                           "through. 4-6 sentences."),
    "comparison_table":   ("A small markdown table comparing the relevant "
                           "figures (portfolio vs benchmark, this period vs "
                           "last, or fee vs fee), then one sentence of "
                           "interpretation."),
    "visual_explanation": ("Describe what the relevant chart in the report "
                           "shows and point them to it; give the key figures "
                           "in words."),
    "step_by_step":       ("Walk through the calculation step by step, one "
                           "numbered line each, using their own figures."),
}


# ---------------------------------------------------------------------------
# Grounded answering
# ---------------------------------------------------------------------------

_ANSWER_SYSTEM = """You answer a wealth-management client's question about
their own report. Rules, in order:

1. Use ONLY figures from the FACTS section. If the facts cannot answer the
   question, say so plainly and suggest they ask their adviser — never
   estimate, never use outside knowledge, never predict.
2. No advice, no recommendations, no opinions on what they should do.
3. Warm, plain English. Address them as "you". Keep it brief.
4. If SELECTED CONTENT is present, the client highlighted it — answer about
   that specifically.
5. Money is in pounds (£1,234.56), never dollars."""


def _facts_for_scope(snap: ClientSnapshot,
                     block: Optional[Dict]) -> Tuple[str, Dict[str, float]]:
    """(prompt text, allowlist) for either one block's scope or the whole
    report. The allowlist is what the answer's numbers are checked against
    afterwards — same derived arithmetic as report validation."""
    all_facts = derived_facts(snap.numeric_facts())
    lines = [f"client: {snap.display_name}, period {snap.period}"]
    if block:
        refs = block.get("source_refs") or []
        scoped = {k: v for k, v in snap.numeric_facts().items() if k in refs}
        for k, v in scoped.items():
            lines.append(f"{k} = {v}")
        data = block.get("content_json") or block.get("data") or {}
        text = json.dumps({k: v for k, v in data.items()
                           if k != "_author"}, default=str)
        lines.append(f"SELECTED CONTENT ({block.get('block_type') or block.get('type')}): "
                     f"{text[:1200]}")
        # Whole-snapshot headline facts stay available so "how does that
        # compare to my total return" still works from a fees highlight.
        for k in ("portfolio_value", "quarter_return_pct",
                  "benchmark_return_pct", "excess_return_pct", "fees.total"):
            if k in all_facts:
                lines.append(f"{k} = {all_facts[k]}")
    else:
        for k, v in snap.numeric_facts().items():
            lines.append(f"{k} = {v}")
    return "\n".join(lines), all_facts


def _check_answer(text: str, facts: Dict[str, float],
                  labels: List[str]) -> List[str]:
    """Every number in the answer must be in the allowlist. Returns the
    offending fragments; empty means grounded."""
    from ape.reporting.grounding import _label_spans, _inside, _is_prose_number
    spans = _label_spans(text, labels)
    allowed = set(facts.values())
    bad = []
    for val, dp, raw, start in extract_numbers(text):
        if _is_prose_number(val, dp, raw) or _inside(start, spans):
            continue
        if _matches(val, dp, allowed) or _matches(-val, dp, allowed):
            continue
        bad.append(raw)
    return bad


DECLINE = ("I can only speak to what's in your report, and it doesn't "
           "contain what I'd need to answer that properly. Your adviser "
           "will be able to help — you can reach them from this page.")


def answer_question(
    session: Session,
    snap: ClientSnapshot,
    report_id: str,
    question: str,
    block: Optional[Dict] = None,
    selected_text: str = "",
    conversation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """The full D2 turn. Returns the answer plus everything the UI and the
    learning loop need to reference it later."""
    from ape.strategies.catalog import INTENT_STRATEGIES

    block_type = (block or {}).get("block_type") or (block or {}).get("type")
    intent = classify_intent(question, block_type)
    arms = INTENT_STRATEGIES.get(intent) or INTENT_STRATEGIES.get(
        "other_report_question", ["standard_llm"])
    strategy, table = select_strategy(session, intent, list(arms))

    facts_text, allowlist = _facts_for_scope(snap, block)
    if selected_text:
        facts_text += f'\nCLIENT HIGHLIGHTED THIS TEXT: "{selected_text[:400]}"'

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    answer, author = DECLINE, "no_key"
    if api_key:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
        style = STRATEGY_STYLE.get(strategy, STRATEGY_STYLE["concise_direct"])
        prompt = (f"FACTS:\n{facts_text}\n\nQUESTION: {question}\n\n"
                  f"Answer format: {style}")
        feedback = ""
        for attempt in range(2):
            try:
                resp = client.messages.create(
                    model=model, max_tokens=600, system=_ANSWER_SYSTEM,
                    messages=[{"role": "user", "content": prompt + feedback}])
                candidate = resp.content[0].text.strip()
            except Exception:
                break
            bad = _check_answer(candidate, allowlist, snap.label_terms())
            if not bad:
                answer, author = candidate, ("llm" if attempt == 0
                                             else "llm_retry")
                break
            feedback = (f"\n\nYour previous answer contained figures not in "
                        f"the FACTS: {', '.join(bad[:4])}. Use only listed "
                        f"figures, or say the report does not contain the "
                        f"answer.")
        else:
            pass
        if author == "no_key":
            # Both attempts stated unlisted numbers -> the safe decline.
            author = "declined_ungrounded"

    # Persist the exchange. The strategy on the assistant message is the
    # reward address for the thumb that may arrive later.
    conv_id = conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
    if session.get(Conversation, conv_id) is None:
        session.add(Conversation(conversation_id=conv_id,
                                 client_id=snap.client_id,
                                 report_id=report_id))
    session.flush()
    q_id = f"msg_{uuid.uuid4().hex[:12]}"
    a_id = f"msg_{uuid.uuid4().hex[:12]}"
    session.add(Message(message_id=q_id, conversation_id=conv_id,
                        client_id=snap.client_id, report_id=report_id,
                        role="client", content=question,
                        content_intent=intent,
                        block_ids=[b for b in
                                   [(block or {}).get("block_id")] if b]))
    session.add(Message(message_id=a_id, conversation_id=conv_id,
                        client_id=snap.client_id, report_id=report_id,
                        role="assistant", content=answer,
                        content_intent=intent, answer_strategy=strategy,
                        block_ids=[b for b in
                                   [(block or {}).get("block_id")] if b]))

    return {"answer": answer, "intent": intent, "strategy": strategy,
            "author": author, "conversation_id": conv_id,
            "message_id": a_id, "arms": table,
            "grounded_in": (block or {}).get("block_id") or "whole_report"}
