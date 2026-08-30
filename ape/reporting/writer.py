"""LLM writer — the model writes the prose blocks, the validator decides
whether a client ever sees them.

═══════════════════════════════════════════════════════════════════════════
WHAT THE MODEL WRITES, AND WHAT IT NEVER TOUCHES
═══════════════════════════════════════════════════════════════════════════

The LLM writes PROSE: the narrative, the callout, the key-takeaway cards.
It fills block JSON — never HTML, never widget data. Charts and tables are
bound to the snapshot by code, so there is nothing for a model to get wrong
in them. Prose is where fabrication lives, so prose is what goes through
the gate.

The flow per block:

    facts + style brief ──> LLM ──> candidate block
                                        │
                              grounding validator
                              │                 │
                          grounded          ungrounded
                              │                 │
                        rendered        RETRY once with the
                                        rejection quoted, then
                                        FALL BACK to code-built
                                              │
                                        rendered (always grounded
                                        by construction)

The fallback means a bad model day degrades style, never truth: the client
gets a plainer sentence, not a wrong number and not a missing section.

═══════════════════════════════════════════════════════════════════════════
WHERE THE STYLE BRIEF COMESS FROM
═══════════════════════════════════════════════════════════════════════════

The control plane. Template strategy (concise/visual/numeric/narrative/...)
plus the client's presentation dimensions, rendered into plain instructions.
Stated preferences and learned preferences arrive through the same dict, so
the writer cannot tell them apart — which is the point: learning upgrades
the source of the values, not the machinery that uses them.
"""

from __future__ import annotations

import json
import sys
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from ape.reporting.csv_source import ClientSnapshot
from ape.reporting.grounding import derived_facts, validate_block

# One retry. If the model cannot write a grounded sentence given the
# rejection verbatim, more attempts only spend money on the same failure.
MAX_ATTEMPTS = 2

_STYLE_LINES = {
    "concise":   ("Keep every sentence short. Two or three sentences total. "
                  "No preamble."),
    "detail":    ("Explain the why behind each figure, not only the what. "
                  "Four to six sentences are fine."),
    "visual":    ("The numbers are already shown in charts nearby, so refer "
                  "to what the charts show rather than repeating every "
                  "figure."),
    "numeric":   ("Lead with the figures. State them exactly as given, to "
                  "two decimal places."),
    "narrative": ("Write it as a flowing account of the quarter, the way an "
                  "adviser would talk a client through it."),
    "comparison": ("Frame everything relative to the benchmark — ahead or "
                   "behind, and by how much."),
    "balanced":  ("Plain, warm, professional. A figure and a reason for "
                  "each point."),
}


def style_brief(strategy: str, dimensions: Optional[Dict[str, float]] = None) -> str:
    """Control plane -> plain instructions the model can actually follow."""
    lines = [_STYLE_LINES.get(strategy, _STYLE_LINES["balanced"])]
    d = dimensions or {}
    # Only dimensions that have moved off neutral say anything. A profile
    # nobody has learned yet must not fabricate a personality.
    if d.get("technical_depth", 0.5) < 0.35:
        lines.append("Avoid jargon entirely; assume no financial background.")
    elif d.get("technical_depth", 0.5) > 0.65:
        lines.append("Financial terminology is fine; the reader knows it.")
    if d.get("concise", 0.5) > 0.65:
        lines.append("Shorter than you think you need.")
    if d.get("numeric_precision", 0.5) > 0.65:
        lines.append("Give exact figures, never rounded ones.")
    if d.get("comparison", 0.5) > 0.65:
        lines.append("Always anchor against the benchmark.")
    return " ".join(lines)


def _fact_sheet(snap: ClientSnapshot) -> str:
    """The ONLY numbers the model is given — and therefore the only numbers
    it can legitimately use. Formatted as labelled lines, not JSON, because
    models copy figures more reliably from prose-like input."""
    f = snap.numeric_facts()
    rows = [
        f"portfolio value at end of {snap.period}: {f['portfolio_value']:.2f}",
        f"return this period: {f['quarter_return_pct']:.2f}%",
        f"benchmark return: {f['benchmark_return_pct']:.2f}%",
        f"difference vs benchmark: {f['excess_return_pct']:.2f}%",
        f"total fees: {f['fees.total']:.2f}"
        + (f" ({f['fees.drag_pct']:.2f}% of the portfolio)"
           if "fees.drag_pct" in f else ""),
    ]
    for a in snap.allocations:
        rows.append(f"allocation {a['asset_class']}: {a['weight_pct']:.1f}%")
    for a in snap.attribution:
        rows.append(f"contribution from {a['driver']}: "
                    f"{a['contribution_pct']:.2f}%")
    if snap.history and len(snap.history) > 1:
        for h in snap.history:
            rows.append(f"return in {h['period']}: {h['portfolio']:.2f}% "
                        f"(benchmark {h['benchmark']:.2f}%)")
    if snap.benchmark_name:
        rows.append(f"benchmark name: {snap.benchmark_name}")
    return "\n".join(rows)


_SYSTEM = """You write one section of a wealth-management client report.

Absolute rules:
1. Use ONLY numbers from the fact sheet. Never compute, estimate, round
   beyond two decimals, or introduce any figure not listed. If a leading
   minus appears in the fact sheet, keep it or use a direction word
   (fell, declined, behind).
2. Never give advice, predictions, or opinions about the future.
3. Address the client as "you"; warm and professional, never salesy.
4. Money is in pounds: write amounts as £1,234.56. Never use $ — the
   charts and tables around your text all show £, and a mixed-currency
   report reads as an error.
5. Return ONLY the JSON asked for. No markdown fences, no commentary."""


def _language_rule(locale) -> str:
    """Rule 6, added only when the client does not read English.

    Appended to the SYSTEM prompt rather than the user turn so it sits with
    the other absolute rules — the number-format half of it has to carry
    the same weight as rule 1, or the model translates the words and leaves
    the figures in English separators, which then fails the locale-aware
    grounding check.
    """
    name = locale.prompt_name
    return (
        "\n6. Write in " + name + ". Use " + name +
        " number formatting: '" + locale.thousands + "' as the thousands "
        "separator and '" + locale.decimal + "' as the decimal separator. "
        "Do not change any figure's VALUE — only how it is written."
    )


def _call(client, model: str, prompt: str, max_tokens: int = 700,
          locale=None) -> str:
    system = _SYSTEM
    if locale is not None and locale.code != "en":
        system = _SYSTEM + _language_rule(locale)
    resp = client.messages.create(
        model=model, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": prompt}])
    return resp.content[0].text.strip()


def _parse_json(text: str) -> Optional[dict]:
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        v = json.loads(text)
        return v if isinstance(v, dict) else None
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Per-block prompts. Each asks for the block's data payload only — block_id,
# type and source_refs stay code-owned so the model cannot break addressing.
# ---------------------------------------------------------------------------

def _prompt_narrative(snap: ClientSnapshot, brief: str, feedback: str) -> str:
    return (f"Fact sheet for {snap.display_name}:\n{_fact_sheet(snap)}\n\n"
            f"Style: {brief}\n{feedback}"
            'Write the opening narrative of the report. Return JSON: '
            '{"text": "..."}')


def _prompt_callout(snap: ClientSnapshot, brief: str, feedback: str) -> str:
    return (f"Fact sheet:\n{_fact_sheet(snap)}\n\nStyle: {brief}\n{feedback}"
            "Write ONE sentence for a highlight banner — the single most "
            "important thing about this period. Return JSON: "
            '{"text": "...", "tone": "positive" | "info" | "caution"}')


def _prompt_takeaways(snap: ClientSnapshot, brief: str, feedback: str) -> str:
    return (f"Fact sheet:\n{_fact_sheet(snap)}\n\nStyle: {brief}\n{feedback}"
            "Write 3 or 4 key takeaways. Each is a short title plus one or "
            "two sentences that state a figure AND what it means for the "
            "client. Return JSON: "
            '{"items": [{"title": "...", "tone": "positive" | "info" | '
            '"caution", "text": "..."}]}')


_PROMPTS = {
    "narrative": _prompt_narrative,
    "callout": _prompt_callout,
    "key_takeaways": _prompt_takeaways,
}

# The blocks the writer is allowed to touch. Everything else is data-bound
# by code and would gain nothing from a model except risk.
WRITABLE = tuple(_PROMPTS)


def _log(msg: str) -> None:
    """Diagnostic print that can never take down a generation.

    These lines quote the model's rejected draft back, so on a non-English
    report they carry Arabic, Japanese, Thai or Greek text. Python picks the
    console encoding for stdout, and on Windows that is cp1252 — printing a
    rejected ARABIC draft raised UnicodeEncodeError from inside the writer
    and turned a perfectly ordinary fallback into a 500 with no report at
    all. The gate had done its job; the LOG is what broke the request.

    Latin-script languages never hit it, because their rejection text
    encodes fine — which is exactly why it survived the English testing.
    """
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        enc = (getattr(sys.stdout, "encoding", None) or "ascii")
        print(msg.encode(enc, "replace").decode(enc, "replace"), flush=True)
    except Exception:
        pass          # a diagnostic is never worth an exception


def write_block(
    anthropic_client,
    model: str,
    block_type: str,
    snap: ClientSnapshot,
    brief: str,
    fallback_block: Dict[str, Any],
    locale=None,
) -> Tuple[Dict[str, Any], str]:
    """Return (block, author) where author is 'llm', 'llm_retry' or
    'fallback'. The returned block is ALWAYS grounded — either the model's
    text survived validation or it is the code-built original."""
    facts = derived_facts(snap.numeric_facts())
    labels = snap.label_terms()
    feedback = ""

    reason = ""
    for attempt in range(MAX_ATTEMPTS):
        try:
            raw = _call(anthropic_client, model,
                        _PROMPTS[block_type](snap, brief, feedback),
                        locale=locale)
        except Exception as exc:
            # Falling back is right — the client still gets a grounded block.
            # Doing it SILENTLY was not: a rate-limited batch and a model
            # inventing figures produced identical output, so neither could
            # be told apart afterwards. Name the cause.
            reason = f"{type(exc).__name__}: {str(exc)[:110]}"
            _log(f"[writer] {block_type}: LLM call failed, using code-built "
                 f"block ({reason})")
            break
        data = _parse_json(raw)
        if not data:
            feedback = ("Your last reply was not valid JSON. Return only "
                        "the JSON object.\n")
            continue

        candidate = dict(fallback_block)
        candidate["data"] = {**fallback_block.get("data", {}), **data}

        findings = [f for f in validate_block(candidate, facts, labels=labels,
                                              locale=(locale.code if locale else None))
                    if f.kind == "ungrounded_number"]
        if not findings:
            candidate["_author"] = "llm" if attempt == 0 else "llm_retry"
            return candidate, candidate["_author"]

        # Quote the exact rejection back. Models fix concrete complaints
        # far more reliably than "try again".
        quoted = "; ".join(f.detail for f in findings[:3])
        reason = f"ungrounded — {quoted[:110]}"
        feedback = (f"Your previous draft was rejected by the fact checker: "
                    f"{quoted}. Every number must appear in the fact sheet "
                    f"exactly.\n")
        if attempt == MAX_ATTEMPTS - 1:
            _log(f"[writer] {block_type}: draft rejected twice, using "
                 f"code-built block ({quoted[:100]})")

    out = dict(fallback_block)
    out["_author"] = "fallback"
    out["_fallback_reason"] = reason or "model returned no usable JSON"
    return out, "fallback"


def write_prose_blocks(
    report: Dict[str, Any],
    snap: ClientSnapshot,
    strategy: str,
    dimensions: Optional[Dict[str, float]] = None,
) -> Dict[str, str]:
    """Rewrite every writable block in the report in place.

    Returns {block_id: author} so the API can report exactly who wrote what
    — an advisor reviewing a draft deserves to know which sentences are the
    model's.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {b["block_id"]: "fallback (no api key)"
                for b in report["blocks"] if b["type"] in WRITABLE}

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
    brief = style_brief(strategy, dimensions)

    # The client's language, taken from the snapshot the facts came from —
    # so the prose and the figures inside it are written and then validated
    # under the same convention.
    from ape.reporting.locales import get as _get_locale
    _loc = _get_locale(getattr(snap, "language", None))

    authors: Dict[str, str] = {}
    for i, block in enumerate(report["blocks"]):
        if block["type"] not in WRITABLE:
            continue
        written, author = write_block(client, model, block["type"], snap,
                                      brief, block, locale=_loc)
        report["blocks"][i] = written
        # A fallback carries WHY, so an advisor reviewing a draft can tell a
        # rate-limited batch from a model that invented a figure.
        authors[block["block_id"]] = (
            f"{author} ({written['_fallback_reason']})"
            if author == "fallback" and written.get("_fallback_reason")
            else author)
    return authors
