"""Turn a finished report into a two-voice podcast.

═══════════════════════════════════════════════════════════════════════════
THE ORDER OF OPERATIONS IS THE WHOLE DESIGN
═══════════════════════════════════════════════════════════════════════════

Text-to-speech reads "£1,249,327.22" badly, so the natural instruction is
"spell the figures out in words". Do that in the PROMPT and the grounding
gate stops working — silently.

The validator finds claims by matching DIGIT strings against the snapshot.
A script that says "two point seven six percent" contains no digits, so
extract_numbers returns nothing, validate_block reports no findings, and
the script "passes" having been checked for exactly nothing. It is a green
light that means the light was never on — the most dangerous failure this
system can have, because audio is the one artifact nobody proofreads.

So the pipeline is:

    1. the model writes the dialogue WITH DIGITS
    2. the grounding gate checks it, the same gate every block goes through
    3. only then does CODE convert the digits to spoken words
    4. the spoken form goes to TTS

Step 3 is deterministic code, never the model. A model asked to "say these
numbers as words" can drop a digit and nothing downstream would catch it,
because by then the digits it would be checked against are gone.

═══════════════════════════════════════════════════════════════════════════
LANGUAGE
═══════════════════════════════════════════════════════════════════════════

The TTS engine (piper) ships en_US and en_GB voices only. A Dutch report
therefore cannot become a Dutch podcast today. Rather than feed Dutch text
to an English voice — which produces confident nonsense — the script is
written in English and the client is told so. When the engine gains voices,
`SPOKEN_LOCALES` is where that changes.

═══════════════════════════════════════════════════════════════════════════
WHAT LEAVES THE BUILDING
═══════════════════════════════════════════════════════════════════════════

The script is sent to a third-party MCP server to be rendered. That script
contains the client's portfolio figures. This is a real disclosure, not a
footnote — see PRIVACY_NOTE, which the caller is expected to surface.
"""

from __future__ import annotations

import asyncio
import threading
import re
from typing import Any, Dict, List, Optional, Tuple

from .grounding import derived_facts, validate_block

MCP_URL = "https://podcast-mcp-yr3m.onrender.com/mcp"

# Free Render instances sleep. The first call after a quiet spell pays a
# cold start, and generation runs ~1.5 min per minute of audio, so the
# budget is generous on purpose — a timeout here means a failed podcast,
# not a slow one.
MCP_TIMEOUT_SECONDS = 600

# Languages we can actually SPEAK. Everything else gets an English script.
SPOKEN_LOCALES = {"en"}

PRIVACY_NOTE = (
    "Audio is rendered by an external service. The dialogue script, which "
    "contains this client's figures, is sent to that service."
)

MAX_ATTEMPTS = 3

# Serialises every render this process makes. See generate_for_report.
_RENDER_LOCK = threading.Lock()

_SPEAKER_RE = re.compile(r"^\s*(HOST|GUEST)\s*:\s*(.+)$", re.I)


# ─────────────────────────────────────────────────────── numbers → words

_ONES = ("zero one two three four five six seven eight nine ten eleven twelve "
         "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = ("", "", "twenty", "thirty", "forty", "fifty",
         "sixty", "seventy", "eighty", "ninety")
_SCALES = ((1_000_000_000, "billion"), (1_000_000, "million"), (1_000, "thousand"))

_CURRENCY = {"£": ("pound", "pounds"), "$": ("dollar", "dollars"),
             "€": ("euro", "euros")}


def _say_int(n: int) -> str:
    """Integer to words. Deterministic, and the inverse is testable."""
    if n < 0:
        return "minus " + _say_int(-n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        tens, rest = divmod(n, 10)
        return _TENS[tens] + ("-" + _ONES[rest] if rest else "")
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        out = _ONES[hundreds] + " hundred"
        return out + (" and " + _say_int(rest) if rest else "")
    for value, name in _SCALES:
        if n >= value:
            count, rest = divmod(n, value)
            out = _say_int(count) + " " + name
            if not rest:
                return out
            # "one million and forty" reads better than "one million forty"
            joiner = " and " if rest < 100 else " "
            return out + joiner + _say_int(rest)
    return str(n)


def _say_digits(s: str) -> str:
    """Digits one at a time — how a decimal fraction is actually read."""
    return " ".join(_ONES[int(c)] for c in s if c.isdigit())


def _spoken_number(raw: str) -> str:
    """One matched figure, as a person would say it.

    Handles the three shapes a report produces: a percentage, a currency
    amount, and a bare number. Anything unrecognised is returned unchanged
    rather than mangled — an unspoken digit is a blemish, a wrong one is a
    lie.
    """
    m = re.fullmatch(r"(?P<cur>[£$€])?\s*(?P<num>-?[\d,]+(?:\.\d+)?)(?P<pct>%)?", raw.strip())
    if not m:
        return raw
    cur, num, pct = m.group("cur"), m.group("num").replace(",", ""), m.group("pct")
    neg = num.startswith("-")
    num = num.lstrip("-")
    whole, _, frac = num.partition(".")

    if pct:
        out = _say_int(int(whole))
        if frac and int(frac):
            out += " point " + _say_digits(frac)
        out += " percent"
    elif cur:
        singular, plural = _CURRENCY[cur]
        n = int(whole)
        out = _say_int(n) + " " + (singular if n == 1 else plural)
        # Pence/cents are noise in a portfolio figure and TTS reads them
        # as a second number, so they are dropped from the SPOKEN form
        # only. The written script keeps them, and the written script is
        # what the grounding gate checked.
    else:
        out = _say_int(int(whole))
        if frac and int(frac):
            out += " point " + _say_digits(frac)

    return ("minus " + out) if neg else out


# A figure, and only a figure.
#
#   (?<![\w.])      not glued to the end of a word or another number
#   (?:[£$€]\s?)?   a currency symbol may own the space after itself, but a
#                   bare number must NOT swallow the space before it, or the
#                   replacement runs into the previous word ("returnedtwo")
#   \d[\d,]*        must START with a digit — "[\d,]+" alone matches a lone
#                   comma in ordinary prose, and int("") then raises
#   (?![\w])        not the head of something like "2026Q2", which is a
#                   period code and must be left exactly as it is
_FIGURE_RE = re.compile(r"(?<![\w.])(?:[£$€]\s?)?-?\d[\d,]*(?:\.\d+)?%?(?![\w])")


def to_spoken(text: str) -> str:
    """Rewrite every figure in a validated script into words.

    Runs AFTER validation, never before. See the module docstring.
    """
    return _FIGURE_RE.sub(lambda m: _spoken_number(m.group(0)), text)


# ───────────────────────────────────────────────────────── script writing

_SYSTEM = """You are writing a short two-voice podcast about ONE client's \
portfolio report.

FORMAT
- Every line begins with "HOST:" or "GUEST:".
- The HOST asks the questions a client would ask. The GUEST is the adviser \
and explains.
- No preamble, no headings, no markdown. Only dialogue lines.
- Around {lines} lines total.

FACTS — THIS IS THE PART THAT MATTERS
- Use ONLY figures from the fact sheet below. Every number you write is \
checked against it automatically and a single invented figure rejects the \
whole script.
- Write figures EXACTLY as they appear in the fact sheet, with digits: \
2.76%, £1,249,327.22. Do NOT spell numbers out as words and do NOT round, \
re-punctuate or convert them. They are converted for speech afterwards.
- Do not compute new numbers. If it is not in the fact sheet, do not say it.
- No advice, no predictions, no recommendations. Explain what happened.

TONE
Warm and plain. The listener is an intelligent person who is not a \
financial professional."""


def _fact_sheet(facts: Dict[str, float]) -> str:
    keep = []
    for k, v in sorted(facts.items()):
        # Handing over every derived fact — hundreds once subset sums exist
        # — invites the model to browse, combine and round. A two-minute
        # podcast wants the headline numbers and the attribution and
        # nothing else; a shorter sheet is a smaller target.
        if k.startswith("derived.group_"):
            continue
        if k.startswith("hold.") or k.startswith("hist."):
            continue
        keep.append(f"  {k} = {v}")
    return "\n".join(keep)


def build_script(anthropic_client, model: str, report: Dict[str, Any],
                 snap, minutes: int = 2) -> Tuple[Optional[str], str]:
    """Write a grounded dialogue script. Returns (script_or_None, detail).

    The script comes back with DIGITS intact so it can be checked. The
    caller converts it for speech.
    """
    facts = derived_facts(snap.numeric_facts())
    labels = snap.label_terms()
    lines = max(8, int(minutes * 9))

    user = (
        f"Client: {report.get('client_name', '')}\n"
        f"Period: {report.get('period', '')}\n"
        f"Benchmark: {getattr(snap, 'benchmark_name', '') or 'the benchmark'}\n\n"
        f"FACT SHEET (the only figures you may use)\n{_fact_sheet(facts)}\n"
    )

    feedback = ""
    detail = "no attempt made"
    for attempt in range(MAX_ATTEMPTS):
        try:
            resp = anthropic_client.messages.create(
                model=model,
                max_tokens=2000,
                system=_SYSTEM.format(lines=lines),
                messages=[{"role": "user", "content": feedback + user}],
            )
            script = "".join(getattr(c, "text", "") for c in resp.content).strip()
        except Exception as exc:
            return None, f"{type(exc).__name__}: {str(exc)[:120]}"

        script = _keep_dialogue(script)
        if not script:
            feedback = "Your last reply had no HOST:/GUEST: lines. Try again.\n"
            detail = "model returned no dialogue lines"
            continue

        # THE GATE. Same validator, same facts, same rules as a report block.
        # The script still has its digits at this point, which is the only
        # reason this check means anything.
        block = {
            "block_id": "podcast_script",
            "block_type": "narrative",
            "source_refs": sorted(facts.keys())[:40] or ["portfolio_value"],
            "data": {"text": script},
        }
        findings = [f for f in validate_block(block, facts, labels=labels,
                                              locale="en")
                    if f.kind == "ungrounded_number"]
        if not findings:
            return script, f"grounded on attempt {attempt + 1}"

        quoted = "; ".join(f.detail for f in findings[:3])
        detail = f"ungrounded — {quoted[:140]}"
        feedback = (f"Your previous script was rejected by the fact checker: "
                    f"{quoted}. Every figure must appear in the fact sheet "
                    f"exactly, written with digits.\n")

    # Out of attempts. Ship the code-built dialogue rather than nothing: it
    # is grounded by construction, and a plainer podcast beats a button that
    # returns an error for a report whose figures were fine all along.
    # Observed the model rounding 1.94 to "about 1.6%" and losing all three
    # attempts — the gate was right, and the client still deserves audio.
    return code_built_script(report, snap), f"code-built ({detail})"


def code_built_script(report: Dict[str, Any], snap) -> str:
    """A dialogue assembled from the snapshot, with no model involved.

    Grounded by construction: every figure is interpolated straight from the
    snapshot, so there is nothing for the gate to reject and no way for a
    number to be invented.

    This exists because the alternative is failing. Observed the model
    rounding 1.94 to "about 1.6%" and losing all three attempts, which left
    a client clicking Listen and getting an error — for a report whose
    figures were sitting right there. Every other writer in this system
    degrades to a code-built block rather than failing; audio should not be
    the exception.
    """
    f = snap.numeric_facts()
    cur = "£"
    pv = f.get("portfolio_value")
    qr = f.get("quarter_return_pct")
    br = f.get("benchmark_return_pct")
    period = report.get("period", "this period")
    name = (report.get("client_name") or "").split(" ")[0] or "there"
    bench = getattr(snap, "benchmark_name", "") or "the benchmark"

    ahead = qr is not None and br is not None and qr >= br
    gap = abs(round((qr or 0) - (br or 0), 2))

    lines = [
        f"HOST: Welcome. Today we're walking through {name}'s {period} portfolio review.",
        f"GUEST: Happy to. Let's start with where things stand.",
    ]
    if pv is not None:
        lines.append(f"HOST: What is the portfolio worth?")
        lines.append(f"GUEST: At the end of {period} it was valued at {cur}{pv:,.2f}.")
    if qr is not None:
        lines.append(f"HOST: And how did it perform?")
        lines.append(f"GUEST: It returned {qr:.2f}% over the period.")
    if br is not None:
        lines.append(f"HOST: How does that compare to the benchmark?")
        lines.append(
            f"GUEST: {bench} returned {br:.2f}%. That puts the portfolio "
            f"{'ahead by' if ahead else 'behind by'} {gap:.2f}%.")

    drivers = sorted(((k[5:], v) for k, v in f.items() if k.startswith("attr.")),
                     key=lambda kv: kv[1], reverse=True)
    if drivers:
        top, tv = drivers[0]
        lines.append("HOST: What drove that?")
        lines.append(f"GUEST: The largest contributor was {top}, adding {tv:.2f}%.")
        if len(drivers) > 1 and drivers[-1][1] < 0:
            bot, bv = drivers[-1]
            lines.append(f"GUEST: The biggest drag was {bot}, at {bv:.2f}%.")

    total_fees = f.get("fees.total")
    if total_fees is not None:
        lines.append("HOST: And what did all this cost?")
        lines.append(f"GUEST: Total fees for the period came to {cur}{total_fees:,.2f}.")

    lines.append("HOST: Anything the listener should do with this?")
    lines.append("GUEST: Nothing here is advice — it's a summary of what "
                 "happened. For anything about your plan, speak to your adviser.")
    lines.append("HOST: Thanks for walking us through it.")
    return "\n".join(lines)


def _keep_dialogue(text: str) -> str:
    """Strip anything that is not a speaker line.

    Models like to open with "Here is your podcast script:". That line
    would be read aloud.
    """
    kept = []
    for line in text.splitlines():
        m = _SPEAKER_RE.match(line)
        if m:
            kept.append(f"{m.group(1).upper()}: {m.group(2).strip()}")
    return "\n".join(kept)


# ────────────────────────────────────────────────────────── MCP synthesis

async def _call_mcp(script: str, title: str) -> Dict[str, Any]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(MCP_URL, timeout=MCP_TIMEOUT_SECONDS) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool(
                "generate_podcast_from_script",
                {"script": script, "title": title},
            )
            return result.structuredContent or {}


def _explain(exc: BaseException, depth: int = 0) -> str:
    """Flatten an exception into something a human can act on.

    The MCP client runs its transport in an anyio TaskGroup, so anything
    that goes wrong arrives as "ExceptionGroup: unhandled errors in a
    TaskGroup (1 sub-exception)" — a message that names the wrapper and
    hides the error. Debugging from that string alone is guesswork, and
    guesswork is what this function exists to stop.
    """
    parts = [f"{type(exc).__name__}: {str(exc)[:160]}"]
    if depth < 4:
        for sub in (getattr(exc, "exceptions", None) or []):
            parts.append("<- " + _explain(sub, depth + 1))
        if exc.__cause__ is not None:
            parts.append("<- caused by " + _explain(exc.__cause__, depth + 1))
    return " ".join(parts)


def _unpack(out: Dict[str, Any]) -> Tuple[Optional[str], str]:
    url = out.get("audio_url") or out.get("url")
    if not url:
        return None, f"no audio_url in response: {str(out)[:160]}"
    return url, "ok"


async def synthesize_async(script: str, title: str) -> Tuple[Optional[str], str]:
    """Render a spoken script to an MP3 URL, from inside an event loop.

    This is the form the API uses. asyncio.run() raises outright when there
    is already a loop running — which there always is under FastAPI — so a
    sync-only version of this could never have worked from an endpoint.
    """
    try:
        return _unpack(await _call_mcp(script, title))
    except BaseException as exc:          # ExceptionGroup is not an Exception
        return None, _explain(exc)


def synthesize(script: str, title: str) -> Tuple[Optional[str], str]:
    """Same, for callers with no event loop — scripts, tests, a CLI."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass                      # no loop, asyncio.run is correct here
    else:
        raise RuntimeError("synthesize() called from an event loop; "
                           "await synthesize_async() instead")
    try:
        return _unpack(asyncio.run(_call_mcp(script, title)))
    except BaseException as exc:
        return None, _explain(exc)


def generate_for_report(anthropic_client, model: str, report: Dict[str, Any],
                        snap, minutes: int = 2,
                        attempts: int = 3) -> Dict[str, Any]:
    """Write, check and render the podcast for one report. Blocking.

    Meant to run ONCE, when the report is generated, not once per client
    click. Three reasons, in order of how much they matter:

    1. A client pressing Listen should get audio, not a two-minute wait
       with a spinner and a chance of failure at the end.
    2. The renderer is a free single-worker instance. Two overlapping
       requests make the second one 502 — which is exactly what on-demand
       generation produces the moment two people read their reports at
       once, and it is what we observed under repeated testing.
    3. Every click was another billed generation of identical audio.

    Retries here are cheap and invisible; retries in front of a waiting
    client are neither. Returns the dict to store on the report; on total
    failure it returns an "error" entry rather than raising, because a
    missing podcast must never fail a report that is otherwise fine.
    """
    import time

    script, detail = build_script(anthropic_client, model, report, snap, minutes)
    if not script:
        script, detail = code_built_script(report, snap), "code-built (no script)"

    spoken = to_spoken(script)
    title = f"{report.get('client_name', 'Your')} — {report.get('period', '')}"

    last = "not attempted"
    # ONE render at a time, process-wide.
    #
    # The renderer is a single free instance and a render takes about as
    # long as the audio it produces. Send it a second job while the first
    # is running and the proxy returns 502 — which is what a batch of
    # reports would do immediately, and what repeated testing did here.
    # Serialising costs wall-clock time in a background thread nobody is
    # waiting on, and buys a job that actually succeeds.
    with _RENDER_LOCK:
        for i in range(attempts):
            url, why = synthesize(spoken, title)
            if url:
                return {"audio_url": url, "script": script, "spoken": spoken,
                        "grounding": detail, "attempts": i + 1,
                        "note": language_note(report.get("language") or "en")}
            last = why
            if i + 1 < attempts:
                # Backoff measured against how long a render takes, not
                # against a web request. Five seconds was hopeless: the
                # instance is busy for minutes, so a short retry just
                # collects three 502s and calls it a failure.
                time.sleep(45 * (i + 1))
    return {"error": last, "script": script, "grounding": detail}


def language_note(locale_code: str) -> str:
    """What to tell a client whose report is not in English."""
    if (locale_code or "en") in SPOKEN_LOCALES:
        return ""
    return ("Audio is available in English only. Your written report stays "
            "in your own language.")
