"""Turn a finished report into a narrated slide video.

Sibling of podcast.py, and it inherits that module's central rule: every
figure is checked against the frozen snapshot BEFORE anything is rendered.
Read the ordering argument there; it applies here unchanged.

═══════════════════════════════════════════════════════════════════════════
SHARED FACTS, SEPARATE SCRIPTS
═══════════════════════════════════════════════════════════════════════════

                        the frozen snapshot
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
            podcast.py                presentation.py
            HOST / GUEST              one narrator
            questions and answers     declarative statements
            can wander a little       tied to the slide on screen
                    │                     │
                    ▼                     ▼
                   MP3               slides + MP4

Both read the SAME facts. Neither reuses the other's words, and that is
deliberate rather than duplication waiting to be factored out.

A podcast works because someone asks the question the listener has. A
slide narration works because it describes what the viewer is looking at
right now. Forcing one script to serve both gives a video whose voice asks
questions of nobody while a chart sits there unexplained, and a podcast
that reads out bullet points. The scripts differ because the two formats
fail in opposite directions.

What IS shared is everything factual: the snapshot, derived_facts, the
grounding gate, the locale-formatted fact sheet, the render lock. The
duplication is in register, not in truth.

═══════════════════════════════════════════════════════════════════════════
WHAT IS DIFFERENT, AND WHY IT MATTERS MORE
═══════════════════════════════════════════════════════════════════════════

A podcast is prose. A slide is prose PLUS numbers drawn as objects:

    {"visual": {"type": "bar_chart", "data": {"Portfolio": 2.41,
                                              "Benchmark": 3.77}}}

Those two floats become the bars a client looks at, with the values printed
beside them. They are exactly as much a factual claim as a sentence saying
"you returned 2.41%" — and they arrive as JSON numbers, not as text, so a
prose-only check walks straight past them.

So this module checks BOTH: the narration and key_points as prose, and
every value in every visual against the same allowlist. A chart is the last
place a wrong figure should be able to hide, because a bar is believed
faster than a sentence and questioned less.

═══════════════════════════════════════════════════════════════════════════
LANGUAGE
═══════════════════════════════════════════════════════════════════════════

Narration follows the report's language, like the podcast. ON-SLIDE TEXT
STAYS ENGLISH for non-Latin scripts: the renderer's font has no Devanagari,
Arabic or CJK glyphs, so those would draw as empty boxes — worse than an
English label, because a client cannot even tell what was meant.
"""

from __future__ import annotations

import asyncio
import json
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from .grounding import derived_facts, validate_block
from .podcast import (MCP_URL, MCP_TIMEOUT_SECONDS, _COLD_START_SECONDS,
                      _COLD_RETRY_SECONDS,
                      _explain, _log_fetch, wake_renderer,
                      fetch_audio, language_note)

MAX_ATTEMPTS = 3

# ── THE LENGTH BUDGET ───────────────────────────────────────────────────
#
# The renderer is one CPU and 512MB. Video cost scales with narration
# length twice over: synthesis time, then a frame-by-frame encode of the
# result. A five-minute presentation is not "a bit slower" than a
# two-minute one — it is the difference between finishing and being killed
# for memory.
#
# So the length is a BUDGET ENFORCED IN CODE, not a request in a prompt.
# The model is told the limit and usually respects it; _fit_budget then
# holds it to the number regardless, because "usually" is not a guarantee
# and the failure mode is a dead job rather than a long one.
#
# Roughly 150 words per minute of speech, so ~220 words lands near 90
# seconds of narration and comfortably inside the 1-3 minute range.
MAX_SECTIONS = 4
MAX_WORDS_PER_SECTION = 45
MAX_TOTAL_WORDS = 220
MAX_KEY_POINTS = 3
WORDS_PER_MINUTE = 150.0


def _words(text: str) -> List[str]:
    return [w for w in re.split(r"\s+", str(text or "").strip()) if w]


def estimate_seconds(sections: List[Dict[str, Any]]) -> float:
    """Roughly how long the finished video will run.

    Narration time plus a beat per slide for the transition. Used to log
    what we are about to ask for, so a job that overruns is diagnosable
    afterwards rather than mysterious.
    """
    words = sum(len(_words(s.get("narration", ""))) for s in sections)
    return words / WORDS_PER_MINUTE * 60.0 + 1.5 * len(sections)


def _trim_to_words(text: str, limit: int) -> str:
    """Shorten narration to a word budget, on SENTENCE boundaries.

    Cutting mid-sentence produces narration that stops in the middle of a
    thought, which is worse to listen to than a shorter script. Whole
    sentences only; if even the first is too long it is kept, because a
    truncated first sentence would be the one thing the client hears most.

    Trimming only REMOVES text. That is what makes it safe to run after the
    grounding check: a subset of grounded sentences is still grounded, and
    no new figure can appear.
    """
    if len(_words(text)) <= limit:
        return text
    out, used = [], 0
    for sentence in re.split(r"(?<=[.!?])\s+", str(text).strip()):
        n = len(_words(sentence))
        if out and used + n > limit:
            break
        out.append(sentence)
        used += n
    return " ".join(out) if out else text


def _fit_budget(sections: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
    """Hold the presentation to the length the free tier can actually render.

    Returns the trimmed sections and a note describing what was cut, so the
    log says "trimmed 6 sections to 4" rather than silently shipping
    something different from what the model wrote.
    """
    notes = []
    if len(sections) > MAX_SECTIONS:
        notes.append(f"{len(sections)}->{MAX_SECTIONS} sections")
        sections = sections[:MAX_SECTIONS]

    out, budget = [], MAX_TOTAL_WORDS
    for sec in sections:
        sec = dict(sec)
        allowance = min(MAX_WORDS_PER_SECTION, budget)
        if allowance <= 0:
            notes.append("dropped a section over the word budget")
            continue
        narration = _trim_to_words(sec.get("narration", ""), allowance)
        if narration != sec.get("narration"):
            notes.append("shortened narration")
        sec["narration"] = narration
        budget -= len(_words(narration))

        pts = sec.get("key_points") or []
        if len(pts) > MAX_KEY_POINTS:
            sec["key_points"] = pts[:MAX_KEY_POINTS]
            notes.append("trimmed key points")
        out.append(sec)

    return out, ("; ".join(sorted(set(notes))) if notes else "within budget")

# THE SAME LOCK THE PODCAST USES. Not a copy — the same object.
#
# The renderer is one CPU and 512MB, and it does not care which of our
# features asked. A separate lock per media type meant a podcast and a
# video could render simultaneously: two synthesis processes and an ffmpeg
# encode on a box sized for one, which is how it crosses the memory limit
# rather than merely running slowly.
#
# One lock means every render this process asks for queues behind the last
# one. Slower in wall-clock for a batch, and the difference between jobs
# that finish and jobs that get killed.
from .podcast import _RENDER_LOCK          # noqa: E402  (shared on purpose)

# Latin scripts can be drawn by the renderer's default font. Everything
# else would come out as empty boxes.
_LATIN_SCRIPT = {"en", "nl", "de", "fr", "es", "it", "pt", "sv", "da", "nb",
                 "fi", "pl", "cs", "tr", "hr", "bs", "sk", "sl", "ro", "hu",
                 "et", "lv", "lt", "is", "id", "ms", "vi", "tl", "sq", "sw"}


_SYSTEM = """You are writing NARRATION for a slide presentation about ONE \
client's portfolio report.

THIS IS NOT A CONVERSATION. There is one narrator and no second voice. Do \
not write questions, do not write "So what happened here?", do not address \
an interviewer. The podcast version of this report is a host-and-guest \
dialogue; this is the opposite register and must not read like it.

Each narration describes WHAT IS ON THE SLIDE IT BELONGS TO. If the slide \
shows a chart of two returns, the narration says what those two returns \
are and what the difference means — not background, not a story, not \
anything the viewer cannot see in front of them. Short, declarative \
sentences.

Good:  "Your portfolio returned 2.41% this quarter, against 3.77% for the \
benchmark — a shortfall of 1.36%."
Bad:   "So how did the portfolio actually do? Well, it's an interesting \
story..."

Return ONLY a JSON object:

{"sections": [{"title": "...", "narration": "...",
               "key_points": ["...", "..."],
               "visual": {"type": "bar_chart", "data": {"Label": 1.23}}}]}

LENGTH — A HARD LIMIT, NOT A PREFERENCE
- EXACTLY 3 or 4 sections. Never more.
- Each narration is AT MOST 40 words. Two or three sentences.
- At most 3 key_points per section, a few words each.
- The whole presentation must be under two minutes when spoken. Anything \
longer is cut before it is rendered, so write to the limit rather than \
past it.

RULES
- Each section has a title, one short narration paragraph, and key_points.
- "visual" is optional. Use "bar_chart" only where a comparison is the \
point, with 2-6 labelled values. Otherwise omit it.
- narration is SPOKEN and must match the slide it sits on.
- key_points are READ on screen while the narration plays, so they are \
labels, not sentences. Do not simply repeat the narration as bullets — the \
viewer is hearing that already.

FACTS — THIS IS THE PART THAT MATTERS
- Use ONLY figures from the fact sheet below. Every number, in the \
narration, in the key_points, AND in any chart, is checked against it \
automatically. One invented figure rejects the whole presentation.
- Write figures EXACTLY as the fact sheet writes them.
- Chart values must be plain numbers matching the fact sheet, e.g. 2.41.
- Do not compute new numbers. No advice, no predictions."""


def _fact_sheet(facts: Dict[str, float], locale_code: str) -> str:
    from .locales import format_number
    keep = []
    for k, v in sorted(facts.items()):
        if (k.startswith("derived.group_") or k.startswith("hold.")
                or k.startswith("hist.")):
            continue
        keep.append(f"  {k} = {format_number(float(v), locale_code, 2)}")
    return "\n".join(keep)


def _visual_numbers(sections: List[Dict[str, Any]]) -> List[Tuple[str, float]]:
    """Every number a slide will DRAW, with where it came from.

    These never appear in the prose scan, because they are JSON floats. If
    they are not checked here they are not checked at all.
    """
    out: List[Tuple[str, float]] = []
    for i, sec in enumerate(sections):
        vis = sec.get("visual") or {}
        data = vis.get("data") or {}
        if not isinstance(data, dict):
            continue
        for label, value in data.items():
            try:
                out.append((f"sections[{i}].visual.{label}", float(value)))
            except (TypeError, ValueError):
                # Unparseable is not "probably fine" — it is a number we
                # cannot verify, on a slide. Force a rejection.
                out.append((f"sections[{i}].visual.{label}", float("nan")))
    return out


def _matches_a_fact(value: float, facts: Dict[str, float]) -> bool:
    """Does this drawn value correspond to something in the snapshot?

    Compared at 2dp, the precision a slide displays. Anything that does not
    line up with a real figure is rejected — a bar is believed faster than
    a sentence, so it gets the same gate and no more latitude.
    """
    if value != value:                      # NaN
        return False
    return any(abs(value - f) < 0.005 for f in facts.values())


def build_sections(anthropic_client, model: str, report: Dict[str, Any],
                   snap) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """Write and fully check the slide sections."""
    from .locales import get as _get_locale
    loc = _get_locale(report.get("language") or "en")
    facts = derived_facts(snap.numeric_facts())
    labels = snap.label_terms()

    lang_rule = "" if loc.code == "en" else (
        f"\n\nWrite every narration in {loc.prompt_name}. "
        + ("Write titles and key_points in "
           f"{loc.prompt_name} as well."
           if loc.code in _LATIN_SCRIPT else
           "Keep section titles and key_points in ENGLISH — the slide "
           "renderer cannot draw this script and would show empty boxes.")
        + f" The fact sheet is written the way {loc.prompt_name} punctuates "
          "numbers; copy each figure exactly as it appears. Chart values "
          "stay as plain decimal numbers like 2.41.")

    user = (f"Client: {report.get('client_name', '')}\n"
            f"Period: {report.get('period', '')}\n"
            f"Benchmark: {getattr(snap, 'benchmark_name', '') or 'the benchmark'}\n\n"
            f"FACT SHEET (the only figures you may use)\n"
            f"{_fact_sheet(facts, loc.code)}\n{lang_rule}")

    feedback = ""
    detail = "no attempt made"
    for attempt in range(MAX_ATTEMPTS):
        try:
            resp = anthropic_client.messages.create(
                model=model, max_tokens=3000, system=_SYSTEM,
                messages=[{"role": "user", "content": feedback + user}])
            raw = "".join(getattr(c, "text", "") for c in resp.content)
        except Exception as exc:
            return None, f"{type(exc).__name__}: {str(exc)[:120]}"

        sections = _parse_sections(raw)
        if not sections:
            feedback = "Your last reply was not the JSON object described. Retry.\n"
            detail = "model returned no usable sections"
            continue

        problems: List[str] = []

        # 1. The words, through the ordinary gate.
        prose = "\n".join(
            " ".join([str(s.get("title", "")), str(s.get("narration", ""))]
                     + [str(p) for p in (s.get("key_points") or [])])
            for s in sections)
        block = {"block_id": "presentation", "block_type": "narrative",
                 "source_refs": sorted(facts.keys())[:40] or ["portfolio_value"],
                 "data": {"text": prose}}
        problems += [f.detail for f in
                     validate_block(block, facts, labels=labels, locale=loc.code)
                     if f.kind == "ungrounded_number"]

        # 2. The numbers the slides DRAW. Invisible to the prose scan.
        for where, value in _visual_numbers(sections):
            if not _matches_a_fact(value, facts):
                problems.append(f"chart value {value:g} at {where} "
                                f"is not in the snapshot")

        if not problems:
            return sections, f"grounded on attempt {attempt + 1}"

        quoted = "; ".join(problems[:3])
        detail = f"ungrounded — {quoted[:140]}"
        feedback = (f"Your previous draft was rejected by the fact checker: "
                    f"{quoted}. Every figure — in narration, in key_points "
                    f"and in every chart — must appear in the fact sheet "
                    f"exactly.\n")

    return None, detail


def _parse_sections(raw: str) -> Optional[List[Dict[str, Any]]]:
    """Pull the sections array out of a model reply."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(text[start:end + 1])
    except Exception:
        return None
    sections = obj.get("sections")
    if not isinstance(sections, list) or not sections:
        return None
    clean = []
    for s in sections:
        if not isinstance(s, dict):
            continue
        if not (s.get("narration") or s.get("key_points")):
            continue                       # the renderer needs one of these
        clean.append(s)
    return clean or None


def code_built_sections(report: Dict[str, Any], snap) -> List[Dict[str, Any]]:
    """Slides assembled straight from the snapshot. Grounded by construction.

    The same reasoning as the podcast's fallback: a plainer presentation
    beats a button that reports an error for a report whose figures were
    fine all along.
    """
    f = snap.numeric_facts()
    pv = f.get("portfolio_value")
    qr = f.get("quarter_return_pct")
    br = f.get("benchmark_return_pct")
    period = report.get("period", "this period")
    cur = "£"

    sections: List[Dict[str, Any]] = []

    pts = []
    if pv is not None:
        pts.append(f"Portfolio value: {cur}{pv:,.2f}")
    if qr is not None:
        pts.append(f"Return this period: {qr:.2f}%")
    # Kept short by construction. This is the fallback that ships when the
    # model could not produce a grounded script, so it must already fit the
    # free tier's budget rather than rely on the trimmer to rescue it.
    sections.append({
        "title": "At a glance",
        "narration": (f"Here is your {period} review. "
                      + (f"Your portfolio was valued at {cur}{pv:,.2f}. " if pv is not None else "")
                      + (f"It returned {qr:.2f}% over the period." if qr is not None else "")),
        "key_points": pts or ["Your portfolio review"],
    })

    if qr is not None and br is not None:
        sections.append({
            "title": "Against your benchmark",
            "narration": (f"Your portfolio returned {qr:.2f}%, while the "
                          f"benchmark returned {br:.2f}%."),
            "key_points": [f"Portfolio: {qr:.2f}%", f"Benchmark: {br:.2f}%"],
            "visual": {"type": "bar_chart",
                       "data": {"Portfolio": round(qr, 2),
                                "Benchmark": round(br, 2)}},
        })

    drivers = sorted(((k[5:], v) for k, v in f.items() if k.startswith("attr.")),
                     key=lambda kv: kv[1], reverse=True)[:4]
    if drivers:
        sections.append({
            "title": "What drove your return",
            "narration": ("The largest contributor was "
                          f"{drivers[0][0]}, adding {drivers[0][1]:.2f}%."),
            "key_points": [f"{n}: {v:.2f}%" for n, v in drivers],
            "visual": {"type": "bar_chart",
                       "data": {n: round(v, 2) for n, v in drivers}},
        })

    total_fees = f.get("fees.total")
    if total_fees is not None:
        sections.append({
            "title": "Fees and costs",
            "narration": (f"Total fees for the period came to "
                          f"{cur}{total_fees:,.2f}. Nothing here is advice — "
                          f"for anything about your plan, speak to your adviser."),
            "key_points": [f"Total fees: {cur}{total_fees:,.2f}"],
        })

    return sections


# ────────────────────────────────────────────────────────── MCP synthesis

async def _call_mcp(sections: List[Dict[str, Any]], title: str) -> Dict[str, Any]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(MCP_URL, timeout=MCP_TIMEOUT_SECONDS) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool(
                "generate_video_from_sections",
                {"sections": sections, "title": title})
            return result.structuredContent or {}


def synthesize(sections: List[Dict[str, Any]], title: str) -> Tuple[Optional[str], str]:
    try:
        out = asyncio.run(_call_mcp(sections, title))
    except BaseException as exc:
        return None, _explain(exc)
    url = out.get("video_url") or out.get("url")
    if not url:
        return None, f"no video_url in response: {str(out)[:160]}"
    return url, "ok"


def generate_for_report(anthropic_client, model: str, report: Dict[str, Any],
                        snap, attempts: int = 6) -> Dict[str, Any]:
    """Write, check and render the presentation. Blocking; run in a thread.

    Returns the dict to store; on failure returns an "error" entry rather
    than raising, because a missing video must never fail a report.
    """
    sections, detail = build_sections(anthropic_client, model, report, snap)
    if not sections:
        sections = code_built_sections(report, snap)
        detail = f"code-built ({detail})"

    # The budget is applied AFTER the gate, deliberately. Trimming only
    # removes whole sentences, so what survives is a subset of text that
    # already passed — no figure can appear that was not checked, and
    # nothing needs re-validating.
    sections, trimmed = _fit_budget(sections)
    est = estimate_seconds(sections)
    _log_fetch(f"[video] {len(sections)} sections, ~{est:.0f}s narration "
               f"({trimmed})")

    title = f"{report.get('client_name', 'Your')} — {report.get('period', '')}"

    # Rendering runs roughly 1.5-2x the narration length on a single CPU,
    # so the wall clock is generous — but bounded, because a stuck job
    # holding this lock blocks every other client's video behind it.
    deadline = time.time() + 20 * 60
    last = "not attempted"
    with _RENDER_LOCK:
        # Same lesson as the podcast: measured cold-start 502s come back in
        # under a second, and two of them are enough to wake the instance.
        # Waking it here costs a few seconds; discovering it asleep inside
        # the retry loop costs a minute of backoff per attempt.
        wake_renderer()
        for i in range(attempts):
            if time.time() > deadline:
                last = f"gave up after 20 minutes ({last})"
                break
            t0 = time.time()
            url, why = synthesize(sections, title)
            if url:
                return {"video_url": url, "sections": sections,
                        "grounding": detail, "attempts": i + 1,
                        "note": language_note(report.get("language") or "en")}
            last = why
            if i + 1 < attempts:
                elapsed = time.time() - t0
                if elapsed < _COLD_START_SECONDS:
                    # Still starting. Give it a real interval — retrying in
                    # two seconds just collects another instant 502 and
                    # spends an attempt for nothing.
                    time.sleep(_COLD_RETRY_SECONDS)
                else:
                    time.sleep((10, 30, 60)[min(i, 2)])
    return {"error": last, "sections": sections, "grounding": detail}
