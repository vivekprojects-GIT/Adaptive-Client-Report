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
from ape.reporting.chat_widgets import wants_visual
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
        # STRICT. A highlight is a SCOPE, not a hint. Only the facts this
        # block cites are offered, and — critically — only those are
        # ALLOWED, because the returned allowlist is what the grounding
        # check enforces afterwards.
        #
        # This used to add the whole-snapshot headline figures as well,
        # "so 'how does that compare to my total return' still works from
        # a fees highlight". The effect was that pointing at the fees
        # table and asking about returns produced a full performance
        # answer — the highlight meant nothing, and convenience quietly
        # overrode the one control a client has over scope.
        refs = block.get("source_refs") or []
        scoped = {k: v for k, v in all_facts.items() if k in refs}
        for k, v in scoped.items():
            lines.append(f"{k} = {v}")
        data = block.get("content_json") or block.get("data") or {}
        text = json.dumps({k: v for k, v in data.items()
                           if k != "_author"}, default=str)
        lines.append(f"SELECTED CONTENT ({block.get('block_type') or block.get('type')}): "
                     f"{text[:1200]}")
        lines.append(
            "SCOPE: the client has selected ONE section, and the figures "
            "above are the only ones in it. If they ask about anything "
            "else, say plainly that it is not in the section they have "
            "selected and that clearing the selection (the x on the "
            "section) lets them ask about the whole report. Never answer "
            "such a question from memory, and never estimate.")
        # Derived arithmetic over the scoped facts stays legal: a fee total
        # computed from its parts is still this section's own number.
        return "\n".join(lines), derived_facts(scoped)

    for k, v in snap.numeric_facts().items():
        lines.append(f"{k} = {v}")
    return "\n".join(lines), all_facts


def _check_answer(text: str, facts: Dict[str, float],
                  labels: List[str]) -> List[str]:
    """Every number in the answer must be in the allowlist. Returns the
    offending fragments; empty means grounded."""
    from ape.reporting.grounding import (_MULT_SUFFIX, _inside,
                                         _is_prose_number, _label_spans)
    spans = _label_spans(text, labels)
    allowed = set(facts.values())
    bad = []
    for val, dp, raw, start in extract_numbers(text):
        if _is_prose_number(val, dp, raw) or _inside(start, spans):
            continue
        # A figure written with a multiplier ("£14.3K") is deliberately
        # rounded and earns the relative tolerance; one written to the penny
        # is claiming that precision and is held to it. Same rule the report
        # validator applies — the two must not diverge, or an answer could
        # state a figure the report itself would have rejected.
        rounded = bool(_MULT_SUFFIX.search(raw))
        if (_matches(val, dp, allowed, rounded)
                or _matches(-val, dp, allowed, rounded)):
            continue
        bad.append(raw)
    return bad


DECLINE = ("I can only speak to what's in your report, and it doesn't "
           "contain what I'd need to answer that properly. Your adviser "
           "will be able to help — you can reach them from this page.")


# Follow-ups a client can actually ask HERE. Generated from the blocks this
# report contains and the intent just answered — a fixed list would offer
# "what drove returns" on a report with no attribution section, which
# teaches the client the assistant is not really reading their document.
_FOLLOWUP_BY_BLOCK = {
    "fees_table":           ["Is that a normal level of fees?",
                             "How do fees compare with my return?"],
    "top_contributors":     ["Which holding helped most?",
                             "Why did that one do well?"],
    "top_detractors":       ["What lost me money this period?",
                             "Should I be worried about that?"],
    "allocation_donut":     ["Why am I invested this way?",
                             "What is my biggest holding?"],
    "allocation_vs_target": ["Am I off my target mix?",
                             "What does drift mean?"],
    "returns_table":        ["How have I done over time?",
                             "Which quarter was best?"],
    "performance_line":     ["How have I done over time?"],
    "comparison_chart":     ["How did I do against the benchmark?",
                             "What is my benchmark?"],
    "comparison_table":     ["What drove my return?"],
    "holdings_table":       ["What do I actually own?"],
    "risk_card":            ["How risky is my portfolio?"],
    "key_takeaways":        ["Explain the main point in simple terms."],
}

# Asked one thing, likely to ask this next.
_FOLLOWUP_BY_INTENT = {
    "fees_cashflow_question":  "What am I getting for those fees?",
    "performance_question":    "Which holdings drove that?",
    "benchmark_comparison":    "Why did I differ from the benchmark?",
    "allocation_question":     "Should my mix change?",
    "risk_question":           "How does my risk compare to last quarter?",
    "holdings_question":       "Which holding is my largest?",
    "report_summary":          "Explain that in simpler terms.",
}


# Which block types answer which intent. The inverse of BLOCK_INTENT_HINT,
# and the reliable backbone of a citation: a fees question is answered by
# the fees table whether or not a figure from it survived into the prose.
_BLOCKS_FOR_INTENT: Dict[str, Tuple[str, ...]] = {
    "fees_cashflow_question": ("fees_table",),
    "benchmark_comparison":   ("comparison_chart", "comparison_table"),
    "performance_question":   ("returns_table", "performance_line",
                               "performance_history", "top_contributors",
                               "top_detractors", "comparison_table"),
    "allocation_question":    ("allocation_donut", "allocation_vs_target"),
    "holdings_question":      ("holdings_table",),
    "risk_question":          ("risk_card",),
    "report_summary":         ("kpi_grid", "key_takeaways"),
}

MAX_SOURCES = 3


def source_blocks(report: Dict[str, Any], snap: ClientSnapshot,
                  answer: str, block: Optional[Dict] = None,
                  intent: str = "") -> List[Dict[str, str]]:
    """Which sections of the report this answer came from.

    Three passes, strongest evidence first:

      1. The block the client HIGHLIGHTED. They pointed at it and the
         answer was scoped to it, so it is a source whether or not one of
         its figures survived into the prose.
      2. Blocks whose TYPE answers this intent. A fees question is
         answered by the fees table; that is structural, not a guess.
      3. Blocks carrying a DISTINCTIVE figure the answer quotes.

    Pass 3 alone was the first implementation and was both too noisy and
    too weak: a fees answer cited "Return over time" because a percentage
    coincidentally matched, while a holdings answer cited nothing at all
    because it quoted a value the block's refs did not name. Round numbers
    and small integers are now excluded from matching for exactly that
    reason — "5" appears in every report and identifies nothing.
    """
    cited: List[Dict[str, str]] = []
    seen: set = set()
    blocks = report.get("blocks", [])

    def cite(b):
        bid = b.get("block_id")
        if not bid or bid in seen or len(cited) >= MAX_SOURCES:
            return
        seen.add(bid)
        cited.append({"block_id": bid,
                      "title": b.get("title") or
                               str(b.get("type", "")).replace("_", " ").title()})

    # 1. what they pointed at
    if block and block.get("block_id"):
        match = next((b for b in blocks
                      if b.get("block_id") == block["block_id"]), None)
        if match:
            cite(match)
        else:
            cite({"block_id": block["block_id"],
                  "title": str(block.get("block_type") or "")
                           .replace("_", " ").title()})

    # 2. what structurally answers this intent
    for want in _BLOCKS_FOR_INTENT.get(intent, ()):
        for b in blocks:
            if b.get("type") == want:
                cite(b)

    # 3. what quotes a distinctive figure
    if len(cited) < MAX_SOURCES:
        facts = derived_facts(snap.numeric_facts())
        # A figure is distinctive if it has decimals or is large. Bare
        # small integers ("5 asset classes") match everything and mean
        # nothing.
        used = [(v, dp) for v, dp, _raw, _pos in extract_numbers(answer or "")
                if dp > 0 or abs(v) >= 1000]
        if used:
            for b in blocks:
                refs = [r for r in (b.get("source_refs") or []) if r in facts]
                if not refs:
                    continue
                allowed = [facts[r] for r in refs]
                if any(_matches(v, dp, allowed) for v, dp in used):
                    cite(b)
    return cited


_FOLLOWUP_SYSTEM = """You suggest what a wealth client might ask NEXT.

You are given the question they just asked and the CONTENTS of the report
sections that answer came from.

Suggest what to ask next about THOSE SECTIONS. Work from the section
contents, not from the wording of any answer — the sections are what the
report can actually evidence, and a question the data supports is worth
more than one the prose happened to imply.

Rules:
- Each suggestion must be answerable from the SECTION CONTENTS shown.
  Never suggest asking about data they do not carry — a suggestion the
  system will then refuse is worse than none.
- Ask about figures and rows actually present. "Which holding cost the
  most?" is good when the holdings are listed; "how did this compare to
  2019?" is not, whatever any answer implied.
- Never suggest comparing to anything OUTSIDE this report — industry
  averages, typical fees, other clients, market data, what a peer pays.
  The report holds one client's own figures and nothing else, so those
  questions can only be declined.
- READ THE ANSWER FOR LIMITS. If it says something is not available, not
  in the report, or only covers one period, do NOT suggest asking for it
  again in another form. Being told "I can only see this quarter" and
  then offered "what about last quarter?" makes the system look like it
  is not listening to itself.
- Short. Under nine words, in the client's voice, ending in a question
  mark.
- Never suggest asking for a chart. Something else offers those.

Return ONLY JSON: {"questions": ["...", "..."]}"""


def dynamic_followups(question: str, answer: str, report: Dict[str, Any],
                      n: int = 2,
                      sources: Optional[List[Dict[str, str]]] = None
                      ) -> List[str]:
    """Questions that arise from the SOURCE SECTIONS this answer came from.

    Built from the sections rather than the prose on purpose. The prose is
    one rendering of the facts and can be partial, hedged, or a decline;
    the sections are what the report can actually evidence. Asking the
    model to riff on its own wording compounds whatever that wording got
    wrong, and produces suggestions the system may then have to refuse.

    The static tables underneath are keyed by intent, so every fees
    question produced the same two follow-ups regardless. Returns [] on any
    failure, and the caller falls back to them — a slow or unavailable
    model costs relevance, never the chips themselves.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or not (answer or "").strip():
        return []

    # The cited sections with their actual contents — figures, rows,
    # labels. Falling back to every section's TITLE when nothing was cited
    # keeps a suggestion possible without inventing a scope.
    ids = {x["block_id"] for x in (sources or [])}
    blocks = [b for b in report.get("blocks", [])
              if b.get("block_id") in ids] if ids else []
    if blocks:
        sections = " | ".join(
            f"[{b.get('title') or b.get('type')}] "
            f"{json.dumps(b.get('data', {}), default=str)[:700]}"
            for b in blocks)
    else:
        sections = ", ".join(sorted(
            {b.get("title") or b.get("type", "")
             for b in report.get("blocks", [])
             if b.get("type") not in ("disclosures", "explainer")}))
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
            max_tokens=180, system=_FOLLOWUP_SYSTEM,
            messages=[{"role": "user", "content":
                       f"THEY ASKED: {question[:300]}\n\n"
                       f"THE SECTIONS THAT ANSWERED IT CONTAIN:\n"
                       f"{sections[:2000]}\n\n"
                       f"Suggest {n}."}])
        raw = re.sub(r"^```(json)?|```$", "", resp.content[0].text.strip(),
                     flags=re.M).strip()
        data = json.loads(raw)
    except Exception:
        return []

    # Phrases an answer uses when the report cannot support something.
    # If one appears, follow-ups echoing the same subject are dropped —
    # the model is told not to produce them, and this catches it when it
    # does anyway.
    limited = re.search(
        r"(only (see|shows?|covers?|have)|not (available|in|shown)|"
        r"does not (contain|include|carry)|no (data|record|history))",
        answer, re.I)

    out = []
    for q in (data or {}).get("questions", [])[:n]:
        q = " ".join(str(q).split())
        if limited:
            # "last quarter", "previous period", "over time" — the shapes a
            # question takes when it asks for the thing just refused.
            if re.search(r"(last|previous|prior|earlier|other)\s+"
                         r"(quarter|period|year|month)|over time|"
                         r"histor(y|ical)", q, re.I):
                continue
        # A "question" that is a paragraph, or that asks for a chart, is
        # not what was requested and does not go in front of a client.
        if 8 <= len(q) <= 70 and q.endswith("?")                 and not wants_visual(q):
            out.append(q)
    return out


N_CONTENT = 2      # about what the report SAYS
N_CAPABILITY = 2   # about what the chat can DO with it


def suggest_followups(report: Dict[str, Any], intent: str = "",
                      asked: Optional[List[str]] = None,
                      limit: int = N_CONTENT + N_CAPABILITY,
                      snap: Optional[ClientSnapshot] = None,
                      block_type: str = "",
                      question: str = "", answer: str = "",
                      sources: Optional[List[Dict[str, str]]] = None
                      ) -> List[Dict[str, str]]:
    """Four chips: two about the content, two about what can be drawn.

    Each is {q, label, kind}: `q` is sent as the question, `label` is what
    the client reads on the chip, and `kind` is content|capability so the
    viewer can style the two differently.

    Both halves are grounded, and in different things.

    The CONTENT half is grounded in this document — drawn from the blocks
    the report actually contains and the intent just answered, so a chip
    never offers a question about a section the client was not sent.

    The CAPABILITY half is grounded in what the model can actually produce
    for THIS client's data. Most people do not know they can ask a report
    for a chart, and a chip is how an interface says what it can do — but
    only for bindings that can be filled, so a chip can never lead to the
    "cannot be drawn" path.

    The split is fixed rather than best-effort. Letting content chips win
    whenever the report is rich would mean the capabilities are advertised
    least in exactly the reports that could show them off most.
    """
    seen = {q.strip().lower() for q in (asked or [])}
    taken: set = set()

    # ---- content: grounded in the blocks THIS report carries -------------
    content: List[Dict[str, str]] = []

    def add(q, bucket):
        """Content chips label themselves: the question IS short and
        specific already ("What is my biggest holding?"), and shortening it
        further would only make it vaguer."""
        if q and q.lower() not in seen and q.lower() not in taken:
            taken.add(q.lower())
            bucket.append({"q": q, "label": q.rstrip("?.").strip(),
                           "kind": "content"})

    # What this ANSWER opens up, before anything generic. The tables below
    # are keyed by intent alone, so they hand the same two questions to
    # every fees query no matter what was said — a menu, not a
    # conversation.
    if answer or sources:
        for q in dynamic_followups(question, answer, report, N_CONTENT,
                                   sources=sources):
            add(q, content)

    add(_FOLLOWUP_BY_INTENT.get(intent), content)

    present = [b.get("type") for b in report.get("blocks", [])]
    # The highlighted block first: a client pointing at the fees table is
    # more likely to want another fees question than a generic one.
    for bt in ([block_type] if block_type else []) + present:
        if len(content) >= N_CONTENT:
            break
        for q in _FOLLOWUP_BY_BLOCK.get(bt, []):
            add(q, content)
            if len(content) >= N_CONTENT:
                break

    for q in ("Give me a quick summary of this report.",
              "Explain this in simpler terms."):
        if len(content) >= N_CONTENT:
            break
        add(q, content)

    # ---- capability: grounded in what can be drawn for this client -------
    capability: List[Dict[str, str]] = []
    if snap is not None:
        from ape.reporting import chat_widgets as cw
        order = cw.chip_bindings(snap, intent, block_type)
        # Lead with whatever the ANSWER was actually about. An answer that
        # spent four sentences on holdings should offer the holdings chart
        # first, even if the question was classified as something else.
        if answer:
            spoken = cw.guess_binding(answer, intent, block_type, order)
            if spoken in order:
                order = [spoken] + [b for b in order if b != spoken]
        for binding in order:
            if len(capability) >= N_CAPABILITY:
                break
            c = cw.chip(binding)
            # Named specifically — "Fee breakdown (donut)", not "see it as
            # a chart". Every generic label looks identical, which tells a
            # client nothing about which chip answers their question.
            if c and c["q"].lower() not in seen                     and c["q"].lower() not in taken:
                taken.add(c["q"].lower())
                capability.append(c)

    # Content first — a client came with a question, not with a curiosity
    # about the interface. Any unfilled capability slot is given back to
    # content rather than left short.
    out = content[:N_CONTENT] + capability[:N_CAPABILITY]
    if len(out) < limit:
        out += content[N_CONTENT:limit - len(out) + N_CONTENT]
    return out[:limit]


def _choose_widget(question: str, intent: str, block_type: str,
                   snap: ClientSnapshot) -> Tuple[Optional[Dict[str, Any]], str]:
    """Pick and draw a widget for a client who asked to see something.

    Returns (widget, decline_reason). Exactly one is ever populated.

    The model chooses the SUBJECT from the registry's catalogue; the kind
    comes from the client's own words where they named one, and the numbers
    are bound in code. If the call fails, is unavailable, or names anything
    not on the menu, the wording-based guess stands in — a request to see
    something should not go unanswered because a second model call did.

    When nothing on the menu can be filled, the reason comes back instead
    of a chart. A client who asked to see something and got silence has to
    guess whether we ignored them or could not do it.
    """
    from ape.reporting import chat_widgets as cw

    options = cw.available(snap)
    if not options:
        # Nothing at all is drawable. Name what they actually asked about
        # rather than a generic apology.
        wanted = cw.guess_binding(question, intent, block_type,
                                  list(cw.BINDINGS))
        return None, (cw.unavailable_reason(snap, wanted) or
                      "this report does not carry enough detail to chart")

    asked_kind = cw.named_kind(question)
    binding = None

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            resp = client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
                max_tokens=120,
                system=("You match a client's request to one chart from a "
                        "fixed menu. Reply with ONLY the binding name, "
                        "exactly as written in the menu. No other text."),
                messages=[{"role": "user", "content":
                           f"MENU:\n{cw.catalogue(snap)}\n\n"
                           f"The client is looking at: "
                           f"{block_type or 'the whole report'}\n"
                           f"They asked: {question}\n\n"
                           f"Which menu entry should be drawn?"}])
            pick = resp.content[0].text.strip().split()[0].strip(".,\"'`")
            if pick in options:
                binding = pick
        except Exception:
            binding = None

    if binding is None:
        binding = cw.guess_binding(question, intent, block_type, options)

    # The subject the client actually named may be one we cannot fill even
    # though other things are drawable. Saying "here is your allocation
    # instead" when they asked about fee history is not an answer, so the
    # unfillable subject is reported rather than quietly substituted.
    named = cw.guess_binding(question, intent, block_type, list(cw.BINDINGS))
    if named and named not in options:
        return None, (cw.unavailable_reason(snap, named) or
                      "this report does not carry that detail")

    if binding is None:
        return None, "this report does not carry enough detail to chart"
    widget = cw.build(snap, binding, asked_kind)
    if widget is None:
        return None, (cw.unavailable_reason(snap, binding) or
                      "that chart could not be drawn from this report")
    return widget, ""


def answer_question(
    session: Session,
    snap: ClientSnapshot,
    report_id: str,
    question: str,
    block: Optional[Dict] = None,
    selected_text: str = "",
    conversation_id: Optional[str] = None,
    report_json: Optional[Dict[str, Any]] = None,
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

    # Resolved BEFORE the answer is written, because the writer has to know.
    # Left until afterwards, it produced answers that apologised for being
    # unable to draw charts while a chart was being attached below them —
    # the model cannot see what the surrounding system does for it.
    widget, declined = None, ""
    if wants_visual(question):
        try:
            widget, declined = _choose_widget(question, intent,
                                              block_type or "", snap)
        except Exception:
            widget, declined = None, ""

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    answer, author = DECLINE, "no_key"
    if api_key:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
        style = STRATEGY_STYLE.get(strategy, STRATEGY_STYLE["concise_direct"])
        if widget:
            visual = (f"\n\nA {widget['kind']} chart titled "
                      f"\"{widget['title']}\" is being shown directly beneath "
                      f"your answer. Write text that complements it — do not "
                      f"describe the chart, and never say you cannot produce "
                      f"charts.")
        elif declined:
            visual = ("\n\nNo chart can be drawn for this. Answer in words "
                      "only. Do not offer to draw one and do not explain why "
                      "— that is handled separately.")
        else:
            visual = ""
        prompt = (f"FACTS:\n{facts_text}\n\nQUESTION: {question}\n\n"
                  f"Answer format: {style}{visual}")
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

    # Told plainly, in the answer itself. A client who asked to see
    # something and received only prose cannot tell whether we ignored the
    # request or could not fulfil it, and those warrant different next
    # steps on their part. Code-built rather than model-written: this
    # sentence is a claim about what the report contains, which is exactly
    # the kind of claim we do not let a model make.
    if declined and answer != DECLINE:
        answer = (f"{answer}\n\nI can't chart that here — {declined}. "
                  f"Everything above is what the report does record on it; "
                  f"your adviser can supply the rest.")

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
    assistant = Message(message_id=a_id, conversation_id=conv_id,
                        client_id=snap.client_id, report_id=report_id,
                        role="assistant", content=answer,
                        content_intent=intent, answer_strategy=strategy,
                        block_ids=[b for b in
                                   [(block or {}).get("block_id")] if b])
    session.add(assistant)

    # Where this answer came from, resolved by tracing its figures back to
    # the blocks that carry them. Mandatory: an answer about someone's
    # money should always be traceable to the part of the document behind
    # it, and a citation the client can click is the shortest form of that.
    try:
        sources = source_blocks(report_json or {}, snap, answer,
                                block, intent)
    except Exception:
        sources = []

    # Attached after the row is created rather than reordering the whole
    # function: same session, same transaction, so it lands with the rest.
    assistant.sources = sources
    assistant.widget = widget or {}

    return {"answer": answer, "intent": intent, "strategy": strategy,
            "sources": sources,
            "author": author, "conversation_id": conv_id,
            "message_id": a_id, "arms": table,
            "widget": widget, "widget_declined": declined,
            "grounded_in": (block or {}).get("block_id") or "whole_report"}
