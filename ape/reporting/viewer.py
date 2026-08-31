"""The client-facing viewer — the page behind the emailed link.

Three panes, mirroring the product mockup:

    section nav │ the report document │ "Ask about your report"

The right pane is the conversation. Highlight-to-ask works two ways:
  - click any section  -> that block becomes the question's context
  - select text inside -> the exact words travel with the question

Both resolve to a `data-block-id`, which the server maps to the block's
`source_refs` — the localisation that makes every answer grounded in the
facts behind the thing the client is pointing at.

WHAT THE CLIENT NEVER SEES
---------------------------
Template names, arms, selection methods, report ids. Templates belong to
the advisor's control plane; the client gets a document and a
conversation. The page's JS also emits the engagement events (opened,
dwell, downloaded) that the learning loop feeds on — silently, because
asking a client to rate a report is itself a presentation choice they
never asked for.

PDF: the Download button prints the document pane through a print
stylesheet — same HTML, same figures, no second rendering path to drift.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from ape.reporting.generate import DOC_CSS, render_body, _esc


# Two about the content, two about what the chat can draw — the same
# split the follow-ups use after every answer, so the row never changes
# shape mid-conversation.
N_CONTENT, N_CAPABILITY = 2, 2

OPENING_CONTENT = [
    ("Give me a quick summary of this report.", "Quick summary"),
    ("Explain the fees I paid this period.", "Explain my fees"),
    ("How did I do against the benchmark?", "vs benchmark"),
]


def _opening_chips(snapshot=None, locale: str = "") -> str:
    """The chips a client sees before they have asked anything.

    Half say what the document covers; half say what can be DRAWN from it.
    Most people do not know they can ask a report for a chart, and a chip
    is how an interface says what it can do — but only for subjects this
    client's own data can fill, so a chip never leads to "sorry, not
    enough data".

    Falls back to content-only when the snapshot is missing or too thin to
    draw anything, rather than showing a control that cannot deliver.
    """
    # These are the FIRST words a client reads in the chat pane, so an
    # English chip on a Dutch report is the first thing they notice.
    def _tr(text):
        if not locale or locale == "en":
            return text
        from ape.reporting.labels import t as _t
        return _t(text, locale)

    chips = [(_tr(q), lab, "content") for q, lab in OPENING_CONTENT[:N_CONTENT]]
    if snapshot is not None:
        try:
            from ape.reporting import chat_widgets as cw
            for binding in cw.chip_bindings(snapshot)[:N_CAPABILITY]:
                c = cw.chip(binding, locale)
                # "Fee breakdown", not "See it as a chart". A generic label
                # makes every chip look identical and says nothing about
                # which one answers the question the client actually has.
                if c:
                    chips.append((c["q"], c["label"], "capability"))
        except Exception:
            pass
    if len(chips) < N_CONTENT + N_CAPABILITY:
        for q, lab in OPENING_CONTENT[N_CONTENT:]:
            if len(chips) >= N_CONTENT + N_CAPABILITY:
                break
            chips.append((_tr(q), lab, "content"))
    return "\n".join(
        f'    <button data-q="{_esc(q)}"'
        f'{" class=chip-draw" if kind == "capability" else ""}'
        f'>{_esc(q)}</button>'
        for q, _label, kind in chips[:N_CONTENT + N_CAPABILITY])


def render_viewer(report: Dict[str, Any], token: str, snapshot=None) -> str:
    doc = render_body(report, internal=False)
    first_name = _esc(str(report.get("client_name", "")).split(" ")[0])
    rid = _esc(report["report_id"])

    # Section nav from the numbered, titled blocks.
    #
    # Built from the ORIGINAL report, which still holds English titles —
    # render_body translates a copy, so its work is invisible here. The nav
    # has to translate for itself or a Dutch report gets an English index
    # down the side of Dutch headings.
    _nav_locale = report.get("language") or ""
    if _nav_locale and _nav_locale != "en":
        from ape.reporting.labels import t as _tt
    else:
        _tt = lambda text, _loc: text          # noqa: E731

    nav_items = []
    for b in report["blocks"]:
        if b.get("title") and b["type"] not in ("narrative", "callout",
                                                "disclosures", "explainer"):
            nav_items.append(
                f'<a href="#" data-goto="{_esc(b["block_id"])}">'
                f'{_esc(_tt(b["title"], _nav_locale))}</a>')
    nav = "\n".join(nav_items)

    period = _esc(report.get("period", ""))
    rtype = _esc(str(report.get("report_type", "")).replace("_", " ").title())

    return VIEWER_TEMPLATE \
        .replace("__DOC_CSS__", DOC_CSS) \
        .replace("__DOC__", doc) \
        .replace("__NAV__", nav) \
        .replace("__FIRST_NAME__", first_name) \
        .replace("__PERIOD__", period) \
        .replace("__RTYPE__", rtype) \
        .replace("__RID__", rid) \
        .replace("__CHIPS__", _opening_chips(snapshot, _nav_locale)) \
        .replace("__TOKEN__", _esc(token))


VIEWER_TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Your __PERIOD__ report</title>
<link rel="stylesheet" href="/static/widgets.css">
<script defer src="/static/vendor/echarts.min.js"></script>
<script defer src="/static/widgets.js"></script>
<style>
__DOC_CSS__
 html,body{height:100%;margin:0}
 body{display:flex;background:#f1f5f9}
 .side{width:200px;min-width:200px;background:#0f172a;color:#e2e8f0;
   display:flex;flex-direction:column;padding:18px 0}
 .side .brand{font-weight:700;font-size:15px;padding:0 18px 16px;color:#fff;
   border-bottom:1px solid #1e293b;margin-bottom:10px}
 .side a{display:block;color:#94a3b8;text-decoration:none;font-size:12.5px;
   padding:8px 18px;border-left:3px solid transparent}
 .side a:hover{color:#fff;background:#1e293b;border-left-color:#3b82f6}
 .side .foot{margin-top:auto;padding:12px 18px;font-size:11px;color:#475569}
 .mid{flex:1;overflow-y:auto;padding:22px 26px}
 .mid .bar{max-width:760px;margin:0 auto 12px;display:flex;align-items:center;
   justify-content:space-between}
 .mid .bar h2{font-size:16px;margin:0;color:#0f172a}
 .mid .bar .sub{font-size:12px;color:#64748b}
 .btn{border:1px solid #cbd5e1;background:#fff;border-radius:6px;
   padding:7px 13px;font-size:12.5px;cursor:pointer;color:#0f172a}
 .btn:hover{border-color:#94a3b8}
 .btn[disabled]{opacity:.65;cursor:default}
 /* The heading must not be squeezed by the buttons. It gets the leftover
    space and a floor; the actions keep their natural width and wrap below
    on a narrow screen rather than crushing the text beside them. */
 .mid .bar{flex-wrap:wrap;gap:10px}
 .mid .bar > div:first-child{flex:1 1 260px;min-width:220px}
 .bar-actions{display:flex;gap:8px;align-items:center;flex:0 0 auto}
 /* One status line for both media, under the toolbar. Quiet: the client
    did not ask for a progress bar, they asked for a podcast. */
 .mediastat{max-width:760px;margin:0 auto 10px;font-size:12px;color:#64748b}
 .mediastat::before{content:"";display:inline-block;width:7px;height:7px;
   margin-right:7px;border-radius:50%;background:#3b82f6;
   animation:podpulse 1.4s ease-in-out infinite;vertical-align:middle}
 @keyframes podpulse{0%,100%{opacity:.25}50%{opacity:1}}
 @media (prefers-reduced-motion: reduce){
   .mediastat::before{animation:none;opacity:.8}
 }
 /* The player sits with the document, not in the chat rail: it is a way to
    consume THIS report, not a conversation about it. */
 .podwrap{max-width:760px;margin:0 auto 14px;padding:12px 14px;
   border:1px solid #e2e8f0;border-radius:8px;background:#fff}
 .podhd{display:flex;gap:10px;align-items:baseline;margin-bottom:8px;
   font-size:13px;color:#0f172a}
 .podhd span{font-size:12px;color:#b45309}
 .poddl{margin-left:auto;font-size:12px;color:#1d4ed8;text-decoration:none}
 .poddl:hover{text-decoration:underline}
 .podwrap audio{width:100%}
 /* The video is 1280x720 of SLIDES — text and charts, not faces. Squeezed
    into the 760px document column it was rendering bullet text at a size
    nobody would choose to read, which rather defeats a presentation.
    So the panel breaks out of the column when it is open, and the player
    fills it. Native fullscreen is available in the controls on top of
    this; the point here is that it should be legible without it. */
 #vidwrap{max-width:min(1180px, 96vw)}
 .podwrap video{width:100%;max-height:min(70vh, 660px);display:block;
   background:#0f172a;border-radius:6px}
 .podwrap details{margin-top:8px}
 .podwrap summary{font-size:12px;color:#64748b;cursor:pointer}
 .podwrap pre{white-space:pre-wrap;font-size:12px;line-height:1.5;
   color:#334155;margin:8px 0 0;max-height:220px;overflow:auto}
 .doc{min-height:auto;box-shadow:0 1px 4px rgba(15,23,42,.08);border-radius:8px}
 section[data-block-id]{cursor:pointer;border-radius:4px}
 section[data-block-id].sel{outline:2px solid #2563eb;outline-offset:8px;
   position:relative;background:#f8fbff}
 .secx{position:absolute;top:-11px;right:-11px;width:22px;height:22px;
   border-radius:50%;border:1.5px solid #2563eb;background:#fff;color:#2563eb;
   font-size:14px;line-height:1;cursor:pointer;padding:0;z-index:4;
   box-shadow:0 1px 4px rgba(37,99,235,.28)}
 .secx:hover{background:#2563eb;color:#fff}
 mark.selq{background:#fde68a;padding:1px 0;border-radius:2px}
 .askhl{position:absolute;z-index:20;border:0;border-radius:14px;
   background:#2563eb;color:#fff;font-family:inherit;font-size:11.5px;
   font-weight:650;padding:5px 12px;cursor:pointer;
   box-shadow:0 3px 10px rgba(37,99,235,.35)}
 .askhl:hover{background:#1d4ed8}
 .chat{width:340px;min-width:280px;max-width:70vw;background:#fff;
   border-left:1px solid #e2e8f0;display:flex;flex-direction:column;
   position:relative;flex-shrink:0}
 .grip{position:absolute;left:-3px;top:0;bottom:0;width:6px;cursor:col-resize;
   z-index:5}
 .grip:hover,.grip.on{background:#bfdbfe}
 /* A quieter header. It names the panel once; it does not need to be the
    boldest thing in the column. */
 .chat .hd2{padding:13px 16px;border-bottom:1px solid #eef2f6;font-weight:600;
   font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:#64748b;
   background:#fcfdfe}
 .chat .ctx{display:none;margin:10px 14px 0;background:#eff6ff;
   border:1px solid #bfdbfe;border-radius:6px;padding:7px 10px;font-size:11.5px;
   color:#1d4ed8}
 .chat .ctx b{display:block;font-size:11px}
 .chat .ctx button{float:right;border:0;background:none;color:#60a5fa;
   cursor:pointer;font-size:12px}
 /* Turns need air between them more than they need boxes around them.
    The old panel packed 10px gaps around bordered cards, which made a
    three-message exchange read as one grey mass. */
 .msgs{flex:1;overflow-y:auto;padding:16px 14px 20px;display:flex;
   flex-direction:column;gap:18px;scroll-behavior:smooth}
 .m-hint{background:#f8fafc;border:1px solid #eef2f6;border-radius:10px;
   padding:11px 13px;font-size:12.5px;color:#64748b;line-height:1.55}
 .m-hint.resumed{background:none;border:0;text-align:center;padding:2px 0;
   font-size:10.5px;color:#94a3b8;text-transform:uppercase;
   letter-spacing:.05em}
 /* The question is short and already obvious as the client's - it does
    not need to be the loudest element on screen. Softened from a solid
    #2563eb block to something that sits behind the answer it prompted. */
 .m-q{align-self:flex-end;background:#eef2ff;color:#312e81;
   border:1px solid #e0e7ff;border-radius:14px 14px 4px 14px;
   padding:9px 13px;font-size:13px;line-height:1.45;max-width:84%;
   font-weight:500}
 /* THE ANSWER IS THE PAGE, SO IT LOSES THE BOX.
    A bordered grey card around every reply made the panel look like a form.
    The answer is what the client came for; it gets full width, a larger
    size and a taller line, and is separated by space rather than by a
    border. A thin rule on the left marks where a turn begins without
    enclosing it. */
 .m-a{align-self:stretch;background:none;border:0;border-left:2px solid #e0e7ff;
   border-radius:0;padding:1px 0 1px 13px;font-size:13.5px;max-width:100%;
   color:#0f172a;line-height:1.62}
 .m-a strong{font-weight:650;color:#0b1220}
 .m-a table{margin:6px 0;font-size:12px;border-collapse:collapse;width:100%}
 .m-a th,.m-a td{border-bottom:1px solid #e2e8f0;padding:4px 6px;text-align:left}
 .m-a th{font-size:10.5px;text-transform:uppercase;color:#94a3b8}
 .m-a p{margin:0 0 7px} .m-a p:last-child{margin-bottom:0}
 .m-a ul,.m-a ol{margin:6px 0;padding-left:18px}
 .m-a li{margin-bottom:3px}
 .m-a code{background:#eef2f7;padding:1px 4px;border-radius:3px;font-size:11.5px}
 .m-a strong{font-weight:600}
 .m-a h1,.m-a h2,.m-a h3{font-size:13px;margin:8px 0 4px;font-weight:600}
 .src{margin-top:8px;font-size:11px;color:#94a3b8}
 .src a{color:#2563eb;text-decoration:none;border-bottom:1px dotted #93c5fd}
 .src a:hover{color:#1d4ed8;border-bottom-style:solid}
 section.flash{animation:flash 1.4s ease}
 @keyframes flash{0%,100%{background:transparent}
   25%{background:#fef9c3}70%{background:#fef9c3}}
 /* Suggestions are an offer, not a menu. Four full-width bordered bars
    under every answer competed with the answer itself; these read as
    quiet links until pointed at. */
 .chips.inline{padding:0;margin-top:12px;padding-top:10px;
   border-top:1px dashed #e8edf3;flex-direction:column;align-items:flex-start;
   gap:2px}
 .chips.inline button{font-size:12px;padding:5px 0;width:auto;
   white-space:normal;text-align:left;line-height:1.45;border-radius:0;
   border:0;background:none;color:#475569}
 .chips.inline button:hover{background:none;color:#1d4ed8}
 /* No marker: the rule above the group, the indent and the hover state
    already say these are suggestions. A bullet added noise to the one
    part of the panel that most needed less of it. */
 /* A chip that DRAWS something stays distinguishable from one that only
    asks - that difference is the whole reason capability chips exist. */
 .chips button.chip-draw{border-color:#c7d2fe;background:#eef2ff;color:#4338ca}
 .chips button.chip-draw:hover{border-color:#4F46E5;background:#e0e7ff}
 .chips.inline button.chip-draw{background:none;color:#4338ca}
 .chips.inline button.chip-draw:hover{color:#3730a3}
 /* Feedback is useful but it is not part of the answer. It fades in on
    hover, so it is there when wanted and invisible while reading. */
 .fb{display:flex;gap:6px;margin-top:10px;opacity:.35;
   transition:opacity .16s ease}
 .m-a:hover .fb,.fb:focus-within{opacity:1}
 .cw-ans{margin:9px 0 2px;border:1px solid #e2e8f0;border-radius:8px;
   background:#fff;padding:7px 8px 2px}
 .cw-ans>span{display:block;font-size:10px;text-transform:uppercase;
   letter-spacing:.05em;color:#94a3b8;font-weight:700;margin-bottom:2px}
 .cw-ans .ecw{height:168px;margin:0}
 .fb button{border:1px solid #e2e8f0;background:#fff;border-radius:5px;
   padding:2px 9px;font-size:12px;cursor:pointer;color:#64748b}
 .fb button:hover{border-color:#94a3b8}
 .fb button.on{background:#eff6ff;border-color:#2563eb;color:#1d4ed8}
 .chips{padding:0 14px 8px;display:flex;flex-direction:column;
   align-items:stretch;gap:5px}
 .chips button{white-space:normal;text-align:left;line-height:1.4}
 .chips button{border:1px solid #dbe4f0;background:#f8fafc;border-radius:14px;
   padding:5px 11px;font-size:11.5px;color:#334155;cursor:pointer}
 .chips button:hover{border-color:#2563eb;color:#1d4ed8}
 /* ONE CONTROL, NOT FOUR.
    The row had grown to a field plus three separate bordered buttons, all
    the same size and weight, so none of them read as the primary action.
    They are now inside a single rounded field: the two voice controls sit
    quietly at the right edge, and send is the only filled thing in the
    panel. */
 .ask{display:flex;align-items:center;gap:7px;padding:11px 13px 13px;
   border-top:1px solid #eef2f6;background:#fff}
 .ask .field{flex:1;display:flex;align-items:center;gap:2px;
   border:1px solid #dbe3ec;border-radius:22px;padding:3px 5px 3px 4px;
   background:#fff;transition:border-color .15s ease,box-shadow .15s ease}
 .ask .field:focus-within{border-color:#4f46e5;
   box-shadow:0 0 0 3px rgba(79,70,229,.10)}
 .ask input{flex:1;border:0;border-radius:18px;padding:9px 12px;
   font-size:13.5px;outline:none;background:none;min-width:0}
 /* Inside the field, so they belong to the question being typed rather
    than competing with it. */
 .ask #mic{border:0;background:none;border-radius:50%;
   width:32px;height:32px;cursor:pointer;font-size:14px;line-height:1;padding:0;
   opacity:.62;flex:none;transition:opacity .15s ease,background .15s ease}
 .ask #mic:hover{background:#f1f5f9;opacity:1}
 /* Recording has to be unmistakable — a live microphone that LOOKS idle is
    the one state this must never present. Colour plus motion, so it still
    reads when the colour does not (reduced motion keeps the colour). */
 .ask #mic.rec{background:#dc2626;border-color:#dc2626;color:#fff;
   animation:micpulse 1.1s ease-in-out infinite}
 @keyframes micpulse{50%{opacity:.55}}
 @media (prefers-reduced-motion:reduce){ .ask #mic.rec{animation:none} }
 /* Transcribing: no longer listening, not yet ready. */
 .ask #mic.busy{color:#64748b;cursor:default}
 .ask #voice{border:0;background:none;border-radius:50%;
   width:32px;height:32px;cursor:pointer;font-size:13px;line-height:1;padding:0;
   color:#4f46e5;opacity:.72;flex:none;
   transition:opacity .15s ease,background .15s ease}
 .ask #voice:hover{background:#eef2ff;opacity:1}
 /* The one filled control in the panel: pressing it is the action. */
 .ask #send{border:0;background:#4f46e5;color:#fff;border-radius:50%;
   width:38px;height:38px;cursor:pointer;font-size:14px;line-height:1;
   padding:0;flex:none;transition:background .15s ease}
 .ask #send:hover{background:#4338ca}
 .ask #send:disabled{background:#c7d2fe;cursor:default}

 /* ── voice mode ─────────────────────────────────────────────────────
    A separate surface rather than a panel inside the chat: while it is
    open the client is talking, not reading, and anything else on screen
    is something they cannot use with their hands full. */
 /* Absolute, not fixed: the panel is the frame. .chat is already
    position:relative, so this fills the column and nothing else. */
 .vx{position:absolute;inset:0;z-index:30;display:flex;flex-direction:column;
   align-items:center;justify-content:center;gap:18px;padding:20px;
   box-sizing:border-box;
   background:radial-gradient(120% 90% at 50% 0%,#f8fafc 0%,#eef2f7 55%,#e6ebf3 100%);
   animation:vxin .28s ease-out}
 @keyframes vxin{from{opacity:0}to{opacity:1}}
 .vx[hidden]{display:none}

 /* The orb is the only moving thing, so it carries the whole state
    signal: what it is doing, and that it is still alive. */
 .vx-orb{width:min(140px,42vw);height:min(140px,42vw);border-radius:50%;position:relative;flex:none;
   background:radial-gradient(circle at 34% 28%,#c7d2fe 0%,#6366f1 52%,#4338ca 100%);
   box-shadow:0 14px 40px rgba(67,56,202,.30),0 0 0 9px rgba(99,102,241,.07);
   transform:scale(1);transition:transform .09s ease-out,background .5s ease}
 .vx-orb::after{content:"";position:absolute;inset:-3px;border-radius:50%;
   background:conic-gradient(from 0deg,transparent,rgba(255,255,255,.5),transparent 45%);
   animation:vxspin 7s linear infinite;opacity:.55}
 @keyframes vxspin{to{transform:rotate(360deg)}}
 /* Thinking: colour drains, motion slows. Nothing is being heard. */
 .vx-orb.think{background:radial-gradient(circle at 34% 28%,#e2e8f0 0%,#94a3b8 55%,#64748b 100%);
   animation:vxthink 1.5s ease-in-out infinite}
 @keyframes vxthink{50%{transform:scale(.94)}}
 /* Speaking: a different hue, so it never looks like it is listening. */
 .vx-orb.talk{background:radial-gradient(circle at 34% 28%,#99f6e4 0%,#14b8a6 52%,#0f766e 100%)}
 .vx-orb.muted{background:radial-gradient(circle at 34% 28%,#e5e7eb 0%,#9ca3af 55%,#6b7280 100%)}
 @media (prefers-reduced-motion:reduce){
   .vx-orb,.vx-orb::after,.vx-orb.think{animation:none;transition:none}
 }

 .vx-state{font:600 12px/1.4 -apple-system,Segoe UI,Roboto,Arial,sans-serif;
   color:#475569;letter-spacing:.03em;text-transform:uppercase}
 /* What we heard, shown back before it is sent. A voice interface that
    never shows its transcript gives the client no way to tell a bad
    answer from a misheard question. */
 /* Scrolls rather than pushing the controls off the bottom: an answer
    can be several sentences and the buttons must stay reachable. */
 .vx-said{width:100%;max-width:100%;text-align:center;min-height:2.4em;
   max-height:34%;overflow-y:auto;
   font:400 15px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#0f172a}
 .vx-said .vx-reply{color:#475569;font-size:14px}
 .vx-bar{display:flex;gap:14px;margin-top:2px}
 .vx-btn{width:46px;height:46px;border-radius:50%;border:1px solid #cbd5e1;
   background:#fff;cursor:pointer;font-size:16px;line-height:1;flex:none;
   box-shadow:0 2px 8px rgba(15,23,42,.08)}
 .vx-btn:hover{background:#f8fafc}
 .vx-btn.off{background:#e2e8f0;color:#64748b}
 .vx-end{background:#0f172a;color:#fff;border-color:#0f172a}
 .vx-end:hover{background:#1e293b}
 .vx-note{font:400 11.5px/1.45 -apple-system,Segoe UI,Roboto,Arial,sans-serif;
   color:#94a3b8;max-width:100%;text-align:center}

 .ask button{border:0;background:#2563eb;color:#fff;border-radius:7px;
   width:38px;cursor:pointer;font-size:15px}
 .ask button:disabled{background:#93c5fd}
 .rfb{display:flex;align-items:center;gap:8px;padding:8px 14px;
   border-top:1px solid #e2e8f0;font-size:12px;color:#475569}
 .rfb button{border:1px solid #e2e8f0;background:#fff;border-radius:6px;
   padding:4px 10px;font-size:12px;cursor:pointer;color:#64748b}
 .rfb button:hover{border-color:#94a3b8}
 .rfb button.on{background:#eff6ff;border-color:#2563eb;color:#1d4ed8}
 .note{padding:0 14px 10px;font-size:10.5px;color:#94a3b8}
 .typing{align-self:flex-start;color:#94a3b8;font-size:12px;padding:4px 2px}
 /* The document must never be squeezed to an unreadable column. Below
    these widths the side panes give way rather than compete: the nav goes
    first (it is a convenience), then the chat moves under the document —
    which is the phone layout, and these links get opened on phones. */
 .mid{min-width:0}
 @media (max-width:1180px){ .side{display:none} }
 @media (max-width:900px){
   body{flex-direction:column;height:auto}
   .mid{order:1;overflow:visible}
   .chat{order:2;width:auto!important;max-width:none;min-width:0;
     border-left:0;border-top:1px solid #e2e8f0;height:70vh;
     position:sticky;bottom:0}
   .grip{display:none}
   .doc{border-radius:0}
 }
 @media print{
   .side,.chat,.mid .bar{display:none!important}
   body{display:block;background:#fff}
   .mid{overflow:visible;padding:0}
   .doc{box-shadow:none;max-width:none}
   section[data-block-id]{cursor:auto}
   section[data-block-id]:hover{outline:none}
 }
</style></head><body>

<div class="side">
  <div class="brand">Your report</div>
  __NAV__
  <div class="foot">__RTYPE__ &middot; __PERIOD__<br>Figures are personal
    to you. Link expires automatically.</div>
</div>

<div class="mid">
  <div class="bar">
    <div><h2>Hello __FIRST_NAME__</h2>
      <div class="sub">Click any section to ask about it, or select the
        exact words you mean.</div></div>
    <div class="bar-actions">
      <button class="btn" id="pod">&#127911; Listen</button>
      <button class="btn" id="vid">&#127916; Presentation</button>
      <button class="btn" id="dl">Download PDF</button>
    </div>
  </div>
  <!-- Progress belongs on its OWN line, under the toolbar.
       Sitting inline beside the buttons, two of these plus their timers
       made the action row wider than the page: the heading collapsed into
       a one-word-per-line column and "Preparing... 86s" appeared twice, as
       if two different things were happening. One line, one message. -->
  <div id="mediastat" class="mediastat" hidden><span id="mediastat-txt"></span></div>
  <div id="podwrap" class="podwrap" hidden>
    <!-- No download link here on purpose: the player's own three-dot menu
         already offers Download, because nothing sets controlsList to
         nodownload. A second control for the same action is just clutter. -->
    <div class="podhd"><b>Your report as a podcast</b><span id="podnote"></span></div>
    <audio id="podaudio" controls preload="none"></audio>
    <details id="poddet"><summary>Read the script</summary>
      <pre id="podscript"></pre></details>
  </div>
  <div id="vidwrap" class="podwrap" hidden>
    <div class="podhd"><b>Your report as a presentation</b>
      <span id="vidnote"></span></div>
    <video id="vidplayer" controls preload="none" playsinline></video>
  </div>
  __DOC__
</div>

<div class="chat" id="chat">
  <div class="grip" id="grip" title="Drag to resize"></div>
  <!-- Voice mode covers the chat column only. The report stays visible
       behind it, because the client is asking about something they are
       looking at. -->
  <div class="vx" id="vx" hidden>
    <div class="vx-orb" id="vxorb"></div>
    <div class="vx-state" id="vxstate">Listening</div>
    <div class="vx-said" id="vxsaid"></div>
    <div class="vx-bar">
      <button class="vx-btn" id="vxmute" type="button"
              aria-label="Mute the microphone">&#127908;</button>
      <button class="vx-btn vx-end" id="vxend" type="button"
              aria-label="Leave voice mode">&#10005;</button>
    </div>
    <div class="vx-note">Speak naturally, then pause.</div>
  </div>
  <div class="hd2">Ask about your report</div>
  <div class="ctx" id="ctx"><button id="ctxoff">clear</button>
    <b>Asking about:</b><span id="ctxlabel"></span></div>
  <div class="msgs" id="msgs">
    <div class="m-hint">I can answer questions about this report. Highlight
      any section or chart to ask about it — I'll answer from your own
      figures, nothing else.</div>
  </div>
  <div class="chips" id="chips">
__CHIPS__
  </div>
  <div class="ask">
    <div class="field">
      <input id="q" placeholder="Ask a follow up question..." autocomplete="off">
      <button id="mic" type="button" hidden
              aria-label="Dictate your question">&#127908;</button>
      <button id="voice" type="button" hidden
              aria-label="Talk to your report">&#9673;</button>
    </div>
    <button id="send" aria-label="Send">&#10148;</button>
  </div>
  <div class="rfb" id="rfb">
    <span>Was this report helpful?</span>
    <button id="rfb-yes">&#128077; yes</button>
    <button id="rfb-no">&#128078; not really</button>
  </div>
  <div class="note">Answers come from your report's own figures. For advice,
    contact your adviser. Answers may contain mistakes.</div>
</div>

<script>
var RID = "__RID__", TOKEN = "__TOKEN__";
var conversationId = null, selBlock = null, selText = "";

function post(path, body){
  body.token = TOKEN;
  return fetch("/r/" + RID + path, {method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify(body)}).then(function(r){ return r.json(); });
}
function ev(type, extra){
  var b = {event_type: type}; for (var k in (extra||{})) b[k] = extra[k];
  post("/events", b);
}

ev("report_opened", {});
setTimeout(function(){ ev("dwell_60s", {}); }, 60000);

// Restore the conversation. Every turn has always been written to SQL,
// but nothing ever read it back, so a refresh looked like the thread had
// been thrown away. Restored answers show their text only: sources,
// suggestions and charts were never stored, and inventing them now would
// put things under an old answer that it never actually came with.
(function(){
  fetch("/r/" + RID + "/history?token=" + encodeURIComponent(TOKEN) +
        "&limit=40", {cache: "no-store"})
    .then(function(r){ return r.ok ? r.json() : null; })
    .then(function(d){
      if (!d || !d.messages || !d.messages.length) return;
      conversationId = d.conversation_id || null;
      var hint = document.querySelector(".m-hint");
      if (hint) hint.remove();
      d.messages.forEach(function(m){
        if (m.role === "client") { add("m-q", m.content); return; }
        var el = add("m-a", "");
        el.innerHTML = md(m.content);
        // Sources and the chart were stored with the answer, so a restored
        // reply is the reply. Follow-up chips were not, on purpose: they
        // suggested what to ask next, and next already happened.
        if (m.sources && m.sources.length) el.appendChild(sourceRow(m.sources));
        if (m.widget && m.widget.svg) el.appendChild(chartBox(m.widget));
      });
      if (window.apeEnhanceWidgets) window.apeEnhanceWidgets(msgs);
      var mark = document.createElement("div");
      mark.className = "m-hint resumed";
      mark.textContent = "Earlier in this conversation ↑";
      msgs.insertBefore(mark, msgs.firstChild);
      msgs.scrollTop = msgs.scrollHeight;
    })
    .catch(function(){ /* a lost history must never cost the page */ });
})();

document.getElementById("dl").onclick = function(){
  ev("pdf_downloaded", {}); window.print();
};

// The instant a job began, according to the server. Falls back to now when
// the server did not say — a restarted timer is wrong, a missing one worse.
function startedMs(j){
  return (j && j.started_at) ? j.started_at * 1000 : Date.now();
}

// ── One status line, shared by both media ───────────────────────────────
// Each medium used to own a status span next to its own button. With both
// running, the toolbar carried two timers reading the same number and the
// heading was crushed to one word per line. A client does not need to know
// which of two background jobs is at which stage; they need to know
// something is coming.
var MediaStatus = (function(){
  var el = document.getElementById("mediastat");
  var txt = document.getElementById("mediastat-txt");
  var jobs = {};                       // name -> message
  function paint(){
    var msgs = Object.keys(jobs).map(function(k){ return jobs[k]; });
    if (!msgs.length) { if (el) el.hidden = true; return; }
    if (el) el.hidden = false;
    if (txt) txt.textContent = msgs[0];
  }
  return {
    set: function(name, msg){ jobs[name] = msg; paint(); },
    clear: function(name){ delete jobs[name]; paint(); }
  };
})();

// ── Listen: one click, report to podcast ────────────────────────────────
// Generation runs well over a minute (a cold service, then roughly 1.5
// minutes of rendering per minute of audio), so the button has to say so.
// A silent button that looks broken for two minutes gets clicked again,
// and every click is another billed generation.
(function(){
  var btn = document.getElementById("pod");
  if (!btn) return;
  var wrap = document.getElementById("podwrap"),
      audio = document.getElementById("podaudio"),
      note = document.getElementById("podnote"),
      pre  = document.getElementById("podscript");

  // The audio is normally rendered when the report is generated, so the
  // usual case is "already there". Ask first; only offer to build one if
  // there genuinely isn't one.
  // The audio may be ready long before anyone asks for it, so "we have it"
  // and "the client wants to see it" are two different things. Keeping them
  // apart is what lets the button be a toggle instead of a one-way door.
  var haveAudio = false;
  var wanted = false;

  function load(j){
    // A stored url is a PATH, with no token in it — the row must not be
    // frozen to a credential that expires. This page has a live one.
    var url = j.audio_url || "";
    if (!url) return;
    if (url.charAt(0) === "/") {
      url += (url.indexOf("?") < 0 ? "?" : "&") + "token=" + encodeURIComponent(TOKEN);
    }
    if (audio.src !== url) audio.src = url;
    note.textContent = j.note || "";
    pre.textContent = j.script || "";
    haveAudio = true;
    if (timer) { clearInterval(timer); timer = null; }
    MediaStatus.clear("podcast");
    btn.disabled = false;
    btn.textContent = "🎧 Listen";
    if (wanted) reveal();
  }

  function reveal(){
    wanted = true;
    wrap.hidden = false;
    btn.textContent = "🎧 Hide";
    audio.scrollIntoView({behavior: "smooth", block: "nearest"});
  }

  function hide(){
    wanted = false;
    wrap.hidden = true;
    btn.textContent = "🎧 Listen";
    // Stop the audio on the way out. Leaving it playing behind a closed
    // panel gives the client a voice they can hear and cannot pause.
    try { audio.pause(); } catch (e) {}
  }

  // Kept so the older call sites read the same way.
  function show(j){ load(j); reveal(); }

  // Asked ONCE, on load, and never polled. The podcast is built when
  // someone asks for it, so "not there yet" is the normal state and not
  // something to sit watching — a spinner for audio nobody requested is
  // just a page that looks busy. If a previous listen already rendered it,
  // this finds it and the player is simply there.
  fetch("/r/" + RID + "/podcast?token=" + encodeURIComponent(TOKEN))
    .then(function(r){ return r.json(); })
    .then(function(j){
      // Ready is LOADED, not OPENED. The client came to read their report;
      // an audio player that unfurls by itself is the page deciding for
      // them. Loading it now just means the button is instant when they do
      // ask.
      if (j.status === "ready") { load(j); return; }
      // A render already running — started at send, or by a click before a
      // refresh. Show that it is coming, but still do not open the panel.
      // Count from when the SERVER started the job. Counting from page
      // load meant every refresh reset the timer to zero, so a render
      // three minutes in looked like it had only just begun.
      if (j.status === "working") waitFor(startedMs(j));
    })
    .catch(function(){ /* the button still works */ });

  // Asking the server "ready yet?" until it is.
  //
  // Nothing here ever shows the client why a render failed. A 502 from a
  // TaskGroup is our problem to read in a log; theirs is only whether they
  // can listen yet. Worst case this says it did not work and offers the
  // button again.
  var timer = null;

  function waitFor(t0){
    if (timer) clearInterval(timer);
    btn.disabled = true;
    // The panel stays HIDDEN while this runs. Showing an audio element
    // with no source gives the client a dead scrubber and a greyed play
    // button, which reads as broken rather than as working.
    wrap.hidden = true;

    // The LABEL stays. Replacing it with a ticking number made the button
    // change width every second and told the client nothing they could act
    // on; the stage and the elapsed time belong on the status line.
    var paint = function(){
      var s = Math.round((Date.now() - t0) / 1000);
      MediaStatus.set("podcast", "Preparing your podcast — "
        + ((s < 25) ? "writing the script"
                    : (s < 70 ? "checking every figure against your report"
                              : "recording the audio"))
        + " (" + s + "s)");
    };
    paint();
    timer = setInterval(paint, 1000);

    var stop = function(msg){
      clearInterval(timer); timer = null;
      btn.disabled = false;
      btn.textContent = "🎧 Listen";
      if (msg) MediaStatus.set("podcast", msg);
      else MediaStatus.clear("podcast");
    };

    (function ask(){
      fetch("/r/" + RID + "/podcast?token=" + encodeURIComponent(TOKEN))
        .then(function(r){ return r.json(); })
        .then(function(j){
          if (j.status === "ready") {
            clearInterval(timer); timer = null;
            // load() opens it only if the client asked. A render that
            // finishes while they are reading, having never pressed
            // Listen, should not throw a player across the page.
            load(j);
            ev("podcast_ready", {});
            return;
          }
          if (Date.now() - t0 > 12 * 60 * 1000) {
            stop("That took longer than expected. Please try again in a few minutes.");
            return;
          }
          setTimeout(ask, 5000);
        })
        .catch(function(){ setTimeout(ask, 8000); });
    })();
  }

  btn.onclick = function(){
    if (btn.disabled) return;

    // Open, close, open again. The panel carries a player and the full
    // script, which is a lot of page for someone who only wanted to check
    // one figure — being able to put it away matters as much as opening it.
    if (!wrap.hidden) { hide(); return; }
    if (haveAudio) { reveal(); return; }

    // Nothing rendered yet: ask for one and open it when it arrives.
    ev("podcast_requested", {});
    wanted = true;
    waitFor(Date.now());
    fetch("/r/" + RID + "/podcast", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({token: TOKEN, minutes: 2})
    }).catch(function(){ /* the poll above is what actually matters */ });
  };
})();

// ── Presentation: the same report as narrated slides ────────────────────
//
// Deliberately a near-copy of the podcast block rather than a shared
// abstraction over both. They differ in the ways that matter — a <video>
// element instead of <audio>, no script pane, roughly double the render
// time — and folding them together would produce a parameterised function
// whose branches are harder to follow than these forty lines.
(function(){
  var btn  = document.getElementById("vid");
  if (!btn) return;
  var wrap = document.getElementById("vidwrap"),
      player = document.getElementById("vidplayer"),
      note = document.getElementById("vidnote");

  var haveVideo = false, wanted = false, timer = null;

  function load(j){
    var url = j.video_url || "";
    if (!url) return;
    if (url.charAt(0) === "/") {
      url += (url.indexOf("?") < 0 ? "?" : "&") + "token=" + encodeURIComponent(TOKEN);
    }
    if (player.src !== url) player.src = url;
    note.textContent = j.note || "";
    haveVideo = true;
    if (timer) { clearInterval(timer); timer = null; }
    MediaStatus.clear("video");
    btn.disabled = false;
    btn.textContent = "🎬 Presentation";
    if (wanted) reveal();
  }

  function reveal(){
    wanted = true;
    wrap.hidden = false;
    btn.textContent = "🎬 Hide";
    player.scrollIntoView({behavior: "smooth", block: "nearest"});
  }

  function hide(){
    wanted = false;
    wrap.hidden = true;
    btn.textContent = "🎬 Presentation";
    try { player.pause(); } catch (e) {}
  }

  function waitFor(t0){
    if (timer) clearInterval(timer);
    btn.disabled = true;
    wrap.hidden = true;               // never an empty player

    var paint = function(){
      var s = Math.round((Date.now() - t0) / 1000);
      // Slides take longer than audio — narration plus rendering — so the
      // wording promises minutes rather than "a moment".
      MediaStatus.set("video", "Preparing your presentation — "
        + ((s < 30) ? "writing the slides"
                    : (s < 90 ? "checking every figure and every chart"
                              : "rendering the video"))
        + " (" + s + "s)");
    };
    paint();
    timer = setInterval(paint, 1000);

    var stop = function(msg){
      clearInterval(timer); timer = null;
      btn.disabled = false;
      btn.textContent = "🎬 Presentation";
      if (msg) MediaStatus.set("video", msg);
      else MediaStatus.clear("video");
    };

    (function ask(){
      fetch("/r/" + RID + "/video?token=" + encodeURIComponent(TOKEN))
        .then(function(r){ return r.json(); })
        .then(function(j){
          if (j.status === "ready") { clearInterval(timer); timer = null; load(j); return; }
          if (Date.now() - t0 > 20 * 60 * 1000) {
            stop("That took longer than expected. Please try again shortly.");
            return;
          }
          setTimeout(ask, 6000);
        })
        .catch(function(){ setTimeout(ask, 9000); });
    })();
  }

  fetch("/r/" + RID + "/video?token=" + encodeURIComponent(TOKEN))
    .then(function(r){ return r.json(); })
    .then(function(j){
      if (j.status === "ready") { load(j); return; }   // loaded, not opened
      // Count from when the SERVER started the job. Counting from page
      // load meant every refresh reset the timer to zero, so a render
      // three minutes in looked like it had only just begun.
      if (j.status === "working") waitFor(startedMs(j));
    })
    .catch(function(){});

  btn.onclick = function(){
    if (btn.disabled) return;
    if (!wrap.hidden) { hide(); return; }
    if (haveVideo) { reveal(); return; }
    ev("presentation_requested", {});
    wanted = true;
    waitFor(Date.now());
    fetch("/r/" + RID + "/video", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({token: TOKEN})
    }).catch(function(){});
  };
})();

(function(){
  var yes = document.getElementById("rfb-yes"),
      no  = document.getElementById("rfb-no");
  function vote(kind, btn){
    if (yes.disabled) return;
    yes.disabled = no.disabled = true;
    btn.classList.add("on");
    ev(kind, {});
  }
  yes.onclick = function(){ vote("report_helpful", yes); };
  no.onclick  = function(){ vote("report_unhelpful", no); };
})();

var sections = document.querySelectorAll("section[data-block-id]");
function titleOf(sec){
  var h = sec.querySelector("h3");
  return h ? h.textContent.replace(/^\\d+\\.\\s*/, "") : "this section";
}
// The × that clears the selection, mounted ON the chosen section. The
// chat pane's banner already offered one, but a client looking at the
// document had no way to tell what was selected or how to undo it without
// looking away.
function clearMark(){
  document.querySelectorAll("mark.selq").forEach(function(m){
    m.replaceWith(document.createTextNode(m.textContent));
  });
  var x = document.getElementById("secx");
  if (x) x.remove();
}

// Wrap the client's own selection so it stays visible after the browser
// drops the native highlight. Without this, "what does this mean?" against
// a phrase looked identical to asking about the whole section.
function markSelection(sec){
  var s = window.getSelection && window.getSelection();
  if (!s || s.isCollapsed || !s.rangeCount) return;
  var r = s.getRangeAt(0);
  if (!sec.contains(r.commonAncestorContainer)) return;
  try {
    var m = document.createElement("mark");
    m.className = "selq";
    r.surroundContents(m);          // throws if the range spans elements
    s.removeAllRanges();
  } catch (e) { /* partial selection across tags — the outline still shows */ }
}

function setCtx(sec){
  sections.forEach(function(s){ s.classList.remove("sel"); });
  clearMark();
  if (!sec){ selBlock = null; selText = "";
    document.getElementById("ctx").style.display = "none"; return; }
  sec.classList.add("sel");
  if (selText) markSelection(sec);

  var x = document.createElement("button");
  x.id = "secx"; x.className = "secx"; x.type = "button";
  x.title = "Stop asking about this section";
  x.setAttribute("aria-label", "Clear selection");
  x.textContent = "×";
  x.onclick = function(e){ e.stopPropagation(); setCtx(null); };
  sec.appendChild(x);

  selBlock = sec.getAttribute("data-block-id");
  document.getElementById("ctx").style.display = "block";
  document.getElementById("ctxlabel").textContent = " " + titleOf(sec) +
    (selText ? ' — "' + selText.slice(0, 60) +
      (selText.length > 60 ? "…" : "") + '"' : "");
  ev("block_highlighted", {block_id: selBlock});
  document.getElementById("q").focus();
}
// A floating "Explain this" that follows a text selection. Selecting words
// and then hunting for where to type is two steps; the button puts the
// action where the client's attention already is — the same reasoning as
// the x that clears a section.
var askBtn = null;
function hideAsk(){ if (askBtn){ askBtn.remove(); askBtn = null; } }

function showAsk(sec, sel){
  hideAsk();
  var r = sel.getRangeAt(0).getBoundingClientRect();
  if (!r || (!r.width && !r.height)) return;

  // Snapshot the TEXT, not the live Selection. The click that follows a
  // drag reaches the section's own handler, which marks the passage and
  // calls removeAllRanges — so by the time this button is pressed the
  // live selection is empty, and reading it then would send nothing.
  //
  // Trim to whole words: a drag starts and ends mid-word, and "olio ended
  // 2025 Q4 valued at" is a worse question than the passage it came from.
  var parts = String(sel).trim().split(/ +/);
  if (parts.length > 2) parts = parts.slice(1, parts.length - 1);
  var joined = parts.join(' ');
  var captured = joined.length > 3 ? joined : String(sel).trim();

  askBtn = document.createElement("button");
  askBtn.className = "askhl";
  askBtn.type = "button";
  askBtn.textContent = "Explain this";
  askBtn.style.top  = (window.scrollY + r.bottom + 6) + "px";
  askBtn.style.left = (window.scrollX + r.left) + "px";
  askBtn.onmousedown = function(e){ e.preventDefault(); };   // keep the range
  askBtn.onclick = function(e){
    e.stopPropagation();
    selText = captured;
    setCtx(sec);
    selText = captured;      // setCtx must not clear what we captured
    hideAsk();
    // Travels as selected_text, which the prompt labels as what they are
    // POINTING AT. Pasting it into the question makes the fragment the
    // question, which is a different and worse thing to ask.
    ask("Explain this");
  };
  document.body.appendChild(askBtn);
}

document.addEventListener("mouseup", function(e){
  if (askBtn && askBtn.contains(e.target)) return;
  var sel = window.getSelection && window.getSelection();
  if (!sel || sel.isCollapsed || !sel.rangeCount) { hideAsk(); return; }
  var node = sel.getRangeAt(0).commonAncestorContainer;
  var sec = (node.nodeType === 1 ? node : node.parentElement);
  sec = sec && sec.closest && sec.closest("section[data-block-id]");
  if (!sec || String(sel).trim().length < 4) { hideAsk(); return; }
  showAsk(sec, sel);
});
// Deliberately no scroll handler. setCtx focuses the question box, which
// scrolls the page, so hiding on scroll deleted the button a few hundred
// milliseconds after every selection — the button appeared and then
// vanished on its own. It is cleared on the next selection or click
// instead, which is when it stops being relevant anyway.

sections.forEach(function(sec){
  sec.addEventListener("click", function(){
    var t = window.getSelection ? String(window.getSelection()) : "";
    selText = (t && t.trim().length > 3) ? t.trim() : "";
    setCtx(sec);
  });
});
document.getElementById("ctxoff").onclick = function(){ setCtx(null); };

// Delegated: source links are created inside answer bubbles long after
// this runs, so binding to the nav's links alone would leave every
// citation dead.
document.addEventListener("click", function(e){
  var a = e.target.closest && e.target.closest("a[data-goto]");
  if (!a) return;
  e.preventDefault();
  var sec = document.querySelector(
    'section[data-block-id="' + a.getAttribute("data-goto") + '"]');
  if (sec){
    sec.scrollIntoView({behavior: "smooth", block: "center"});
    sec.classList.add("flash");
    setTimeout(function(){ sec.classList.remove("flash"); }, 1400);
  }
});

document.querySelectorAll(".side a[data-goto]").forEach(function(a){
  a.onclick = function(e){ e.preventDefault();
    var sec = document.querySelector(
      'section[data-block-id="' + a.getAttribute("data-goto") + '"]');
    if (sec){ sec.scrollIntoView({behavior:"smooth", block:"start"});
      setCtx(sec); }
  };
});

var msgs = document.getElementById("msgs");
function add(cls, text){
  var d = document.createElement("div"); d.className = cls;
  d.textContent = text; msgs.appendChild(d);
  msgs.scrollTop = msgs.scrollHeight; return d;
}

// Minimal markdown, escaped FIRST so a model that emits raw HTML cannot
// inject it. Only the constructs answers actually use are supported:
// tables, lists, bold, code, paragraphs.
function esc(t){
  return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function md(src){
  var lines = esc(src).split(/\\r?\\n/), out = [], i = 0;
  function inline(t){
    return t.replace(/\\*\\*([^*]+)\\*\\*/g, "<strong>$1</strong>")
            .replace(/(^|[^*])\\*([^*\\n]+)\\*/g, "$1<em>$2</em>")
            .replace(/`([^`]+)`/g, "<code>$1</code>");
  }
  while (i < lines.length){
    var ln = lines[i];
    // table: header row, separator, body
    if (/^\\s*\\|.*\\|\\s*$/.test(ln) && i + 1 < lines.length &&
        /^\\s*\\|[\\s:|-]+\\|\\s*$/.test(lines[i+1])){
      var cells = function(r){
        return r.trim().replace(/^\\||\\|$/g, "").split("|")
                .map(function(c){ return inline(c.trim()); });
      };
      var head = cells(ln); i += 2;
      var body = [];
      while (i < lines.length && /^\\s*\\|.*\\|\\s*$/.test(lines[i])){
        body.push(cells(lines[i])); i++;
      }
      out.push("<table><thead><tr>" +
        head.map(function(c){ return "<th>" + c + "</th>"; }).join("") +
        "</tr></thead><tbody>" +
        body.map(function(r){
          return "<tr>" + r.map(function(c){ return "<td>" + c + "</td>"; })
                           .join("") + "</tr>"; }).join("") +
        "</tbody></table>");
      continue;
    }
    // list
    var m = ln.match(/^\\s*([-*]|\\d+\\.)\\s+(.*)$/);
    if (m){
      var ordered = /\\d/.test(m[1]), items = [];
      while (i < lines.length){
        var mm = lines[i].match(/^\\s*([-*]|\\d+\\.)\\s+(.*)$/);
        if (!mm) break;
        items.push("<li>" + inline(mm[2]) + "</li>"); i++;
      }
      out.push((ordered ? "<ol>" : "<ul>") + items.join("") +
               (ordered ? "</ol>" : "</ul>"));
      continue;
    }
    // heading
    var h = ln.match(/^\\s*#{1,3}\\s+(.*)$/);
    if (h){ out.push("<h3>" + inline(h[1]) + "</h3>"); i++; continue; }
    // paragraph
    if (ln.trim()){
      var para = [];
      while (i < lines.length && lines[i].trim() &&
             !/^\\s*([-*]|\\d+\\.)\\s+/.test(lines[i]) &&
             !/^\\s*\\|/.test(lines[i]) && !/^\\s*#{1,3}\\s/.test(lines[i])){
        para.push(lines[i]); i++;
      }
      out.push("<p>" + inline(para.join(" ")) + "</p>");
      continue;
    }
    i++;
  }
  return out.join("");
}
// Shared by live answers and restored ones, so a reply from ten minutes
// ago looks exactly like one from ten seconds ago.
function sourceRow(list){
  var src = document.createElement("div");
  src.className = "src";
  src.appendChild(document.createTextNode("From: "));
  list.forEach(function(s, i){
    if (i) src.appendChild(document.createTextNode(" · "));
    var a = document.createElement("a");
    a.href = "#"; a.setAttribute("data-goto", s.block_id);
    a.textContent = s.title;
    src.appendChild(a);
  });
  return src;
}

function chartBox(w){
  var wrap = document.createElement("div"); wrap.className = "cw-ans";
  var cap = document.createElement("span"); cap.textContent = w.title;
  wrap.appendChild(cap);
  var box = document.createElement("div");
  box.className = "ecw";
  box.setAttribute("data-kind", w.kind);
  if (w.option) box.setAttribute("data-opt", JSON.stringify(w.option));
  box.innerHTML = '<div class="ecw-live"></div>' +
                  '<div class="ecw-fallback">' + w.svg + '</div>';
  wrap.appendChild(box);
  return wrap;
}

function addAnswer(res){
  var d = add("m-a", "");
  d.innerHTML = md(res.answer);
  // A chart the client asked for, built server-side from the same frozen
  // snapshot the report was. Same two layers as the document: the SVG is
  // written in directly, and the runtime upgrades it if it is there.
  if (res.widget && res.widget.svg){
    d.appendChild(chartBox(res.widget));
    if (window.apeEnhanceWidgets) window.apeEnhanceWidgets(d);
  }
  // Where the answer came from. Clicking scrolls the document to that
  // section and flashes it, so a client can check any figure against the
  // report rather than taking the chat's word for it.
  if (res.sources && res.sources.length) d.appendChild(sourceRow(res.sources));

  // Follow-ups belong to THIS answer, so they sit under it rather than in
  // a fixed row at the bottom of the pane. A client reading a reply sees
  // what to ask next without their eye leaving the reply.
  if (res.followups && res.followups.length) d.appendChild(chipRow(res.followups));

  var fb = document.createElement("div"); fb.className = "fb";
  var up = document.createElement("button"); up.textContent = "\\uD83D\\uDC4D helpful";
  var dn = document.createElement("button"); dn.textContent = "\\uD83D\\uDC4E not really";
  function vote(kind, btn){
    if (up.disabled) return; up.disabled = dn.disabled = true;
    btn.classList.add("on");
    ev(kind, {message_id: res.message_id,
              metadata: {strategy: res.strategy}});
  }
  up.onclick = function(){ vote("answer_helpful", up); };
  dn.onclick = function(){ vote("answer_unhelpful", dn); };
  fb.appendChild(up); fb.appendChild(dn); d.appendChild(fb);
  msgs.scrollTop = msgs.scrollHeight;
}

var busy = false;
function ask(question, onDone, onDelta){
  // onDone(answerText) fires when the answer is complete, or with null
  // if it failed. Voice mode uses it to speak the reply; the typed box
  // passes nothing and is unaffected.
  if (busy || !question.trim()){ if (onDone) onDone(null); return; }
  busy = true; document.getElementById("send").disabled = true;
  // The opening row exists only before there is an answer to sit under.
  // Left in place it would show one set of suggestions while each reply
  // shows another.
  var opening = document.getElementById("chips");
  if (opening) opening.remove();
  add("m-q", question);
  var t = add("typing", "thinking…");

  var bubble = null, text = "";
  function ensure(){
    if (!bubble){ t.remove(); bubble = add("m-a", ""); }
    return bubble;
  }
  function paint(){
    // Re-render the markdown each time rather than appending raw text: a
    // table or list is only correct once its whole block has arrived, and
    // half-parsed markdown looks broken in a way plain text does not.
    ensure().innerHTML = md(text);
    msgs.scrollTop = msgs.scrollHeight;
  }
  function fail(){
    if (bubble) bubble.remove(); else t.remove();
    add("m-a", "Something went wrong — please try again.");
    if (onDone){ onDone(null); onDone = null; }
  }

  fetch("/r/__RID__/chat/stream", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({token: TOKEN, question: question,
                          block_id: selBlock, selected_text: selText,
                          conversation_id: conversationId,
                          // Voice turns skip the follow-up chips: they are
                          // a model call whose only output is buttons, and
                          // in voice mode nobody is looking at buttons.
                          voice: !!onDelta})
  }).then(function(r){
    if (!r.ok || !r.body) throw new Error("stream failed");
    var reader = r.body.getReader(), dec = new TextDecoder(), buf = "";

    function handle(evt, data){
      if (evt === "delta"){
        text += data.text; paint();
        // Voice mode listens here rather than waiting for "final".
        // After the answer finishes streaming the server still runs
        // follow-up suggestions and preference extraction - two more
        // model calls - before it sends "final". Waiting for that was
        // several seconds of silence after the answer already existed.
        if (onDelta) onDelta(text);
      }
      else if (evt === "reset"){
        // The server abandoned the answer mid-flight: something it was
        // about to say could not be grounded. What was shown is replaced,
        // not appended to.
        text = data.text; paint();
      }
      else if (evt === "final"){
        conversationId = data.conversation_id;
        if (bubble){ bubble.remove(); bubble = null; }
        addAnswer(data);
        if (onDone){ onDone(data.answer || text); onDone = null; }
      }
      else if (evt === "error"){ fail(); if (onDone){ onDone(null); onDone = null; } }
    }

    function pump(){
      return reader.read().then(function(res){
        if (res.done) return;
        buf += dec.decode(res.value, {stream: true});
        var frames = buf.split("\\n\\n");
        buf = frames.pop();                    // keep the partial frame
        frames.forEach(function(f){
          var evt = "message", data = null;
          f.split("\\n").forEach(function(line){
            if (line.indexOf("event:") === 0) evt = line.slice(6).trim();
            else if (line.indexOf("data:") === 0){
              try { data = JSON.parse(line.slice(5).trim()); } catch(e){}
            }
          });
          if (data) handle(evt, data);
        });
        return pump();
      });
    }
    return pump();
  }).catch(fail)
    .then(function(){ busy = false;
      document.getElementById("send").disabled = false; });
}

// ---------------------------------------------- dictation
//
// Records, then asks the server what was said. The transcription runs on
// OUR machine (faster-whisper, see transcribe.py), so the recording reaches
// the backend and stops there.
//
// This replaced the browser's own SpeechRecognition, which had two faults.
// It cannot detect a language: it transcribes against one tag fixed in
// advance, so a client asking in a language other than their report's got
// nonsense back, because the recogniser was not translating - it was trying
// to hear one language as another. And in Chrome it is not local; the audio
// goes to Google. Whisper identifies the language from the audio itself,
// and Firefox gets a microphone at all.
//
// WHAT IT DOES NOT DO IS SEND.
//
// The text lands in the box for the client to read first. The suggestion
// chips already work this way on purpose - a question that fires on touch
// takes away the chance to change a word - and a transcript needs that
// latitude more, because a recogniser mishears where a chip cannot.
(function(){
  var btn = document.getElementById("mic");
  var box = document.getElementById("q");
  if (!btn || !box) return;
  // getUserMedia is a secure-context feature, absent over plain http to a
  // remote host. Localhost counts as secure so development works; a real
  // deployment needs https, and until then the button stays hidden rather
  // than appearing and failing when pressed.
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia ||
      typeof MediaRecorder === "undefined") return;
  btn.hidden = false;

  var recorder = null, chunks = [], stream = null;
  var IDLE = 0, REC = 1, BUSY = 2;
  var state = IDLE;

  function paint(s){
    state = s;
    btn.classList.toggle("rec", s === REC);
    btn.classList.toggle("busy", s === BUSY);
    btn.disabled = (s === BUSY);
    btn.setAttribute("aria-label",
      s === REC ? "Stop recording"
      : s === BUSY ? "Transcribing your question"
      : "Record your question");
    btn.textContent = (s === BUSY) ? "⋯" : "🎤";
  }

  // The recording light must never outlive the recording.
  function release(){
    if (stream){ stream.getTracks().forEach(function(t){ t.stop(); }); }
    stream = null;
  }

  btn.onclick = function(){
    if (state === BUSY) return;
    if (state === REC){ if (recorder) recorder.stop(); return; }

    navigator.mediaDevices.getUserMedia({audio: true}).then(function(s){
      stream = s; chunks = [];
      try { recorder = new MediaRecorder(s); }
      catch (e) { release(); paint(IDLE); return; }

      recorder.ondataavailable = function(e){
        if (e.data && e.data.size) chunks.push(e.data);
      };
      recorder.onstop = function(){
        release();
        var kind = chunks.length ? chunks[0].type : "audio/webm";
        var blob = new Blob(chunks, {type: kind});
        // A tap that caught nothing should return the button to rest, not
        // post an empty body and surface a server error at the client.
        if (!blob.size){ paint(IDLE); return; }
        paint(BUSY);
        fetch("/r/" + RID + "/transcribe?token=" + encodeURIComponent(TOKEN),
              {method: "POST", body: blob})
          .then(function(r){
            if (!r.ok) throw new Error("http " + r.status);
            return r.json();
          })
          .then(function(j){
            var said = (j.text || "").trim();
            if (said){
              // Appended, so speaking never destroys a half-typed question.
              var head = box.value ? box.value.replace(/\\s+$/, "") + " " : "";
              box.value = head + said;
              box.focus();
              box.setSelectionRange(box.value.length, box.value.length);
            }
            paint(IDLE);
          })
          .catch(function(){ paint(IDLE); });
      };
      recorder.start();
      paint(REC);
    }).catch(function(){
      // Permission refused, or no microphone present. Leaving the button
      // lit would suggest we are listening when we are not.
      release(); paint(IDLE);
    });
  };
})();

// ---------------------------------------------- voice mode
//
// A hands-free conversation over the SAME /chat/stream the typed box uses.
// The question arrives as speech and the answer is spoken back; everything
// between is unchanged, so a spoken answer is grounded exactly as a typed
// one is and cannot say anything the written chat would not.
//
// TURN-TAKING IS THE WHOLE PROBLEM.
//
// There is no push-to-talk here, so the page has to work out when a
// sentence has ended. It watches the microphone's level: speech starts when
// the level crosses a threshold, and the turn ends after a stretch of quiet
// long enough to be a full stop rather than a breath. Too short and it cuts
// people off mid-thought; too long and it feels broken. QUIET_MS is that
// judgement and it is the first thing to change if the feel is wrong.
//
// AND IT MUST NOT LISTEN TO ITSELF.
//
// While the answer is being spoken the microphone is ignored entirely.
// Without that the orb hears its own voice, transcribes it, and asks the
// report a question the client never asked - a loop that looks like the
// page has gone haywire.
(function(){
  var open = document.getElementById("voice");
  var vx    = document.getElementById("vx");
  if (!open || !vx) return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia ||
      typeof MediaRecorder === "undefined") return;
  open.hidden = false;

  var orb   = document.getElementById("vxorb");
  var label = document.getElementById("vxstate");
  var said  = document.getElementById("vxsaid");
  var mute  = document.getElementById("vxmute");
  var endBt = document.getElementById("vxend");

  // Speech is "clearly louder than this room is when nobody is talking",
  // measured, rather than a fixed number that assumes a microphone.
  // Proportional to the room, PLUS a fixed margin, PLUS an absolute floor.
  // The multiplier alone fails on a low-gain microphone: scaling a tiny
  // noise floor by 3.2 still lands above the client's actual speech, and
  // they talk to an orb that never reacts. Simulated across quiet/loud mics
  // and quiet/noisy rooms before it went in.
  var OVER_FLOOR   = 2.2;    // proportional part
  var FLOOR_MARGIN = 0.006;  // fixed headroom above the room
  var ABS_MIN      = 0.010;  // a digitally-silent mic must not hear everything
  var FLOOR_MIN    = 0.002;  // the floor estimate itself cannot go below this
  var CALIBRATE_MS= 700;     // listen this long before reacting to anything
  var QUIET_MS    = 1100;    // silence that ends a turn
  var MIN_SPEECH  = 350;     // ignore a cough or a door

  // MediaRecorder.start() WITHOUT a timeslice hands over ONE blob at stop(),
  // containing everything since start(). So a turn's upload spanned from the
  // moment the mic opened to the end of speech - every second the client
  // spent thinking, recorded and sent. Whisper then transcribed minutes of
  // near-silence for a three-second question, and because vad_filter strips
  // that silence it often came back empty, which lands on the "no text"
  // branch and returns to listening WITHOUT ANSWERING. Both reported
  // symptoms, one cause.
  //
  // Trimming the chunk list clientside cannot fix it: the first chunk
  // carries the WebM header, so dropping anything from the front leaves a
  // blob nothing can decode. Instead the recorder is recycled while the room
  // is quiet - every recording stays a complete, self-contained file, and
  // the silence in front of speech is bounded by RECYCLE_MS.
  var RECYCLE_MS  = 4000;    // discard a recording that has heard nothing
  var RECYCLE_CALM= 1500;    // ...and only once well clear of speech

  // A turn ends when the room goes quiet - which assumes the room DOES go
  // quiet below the threshold. On a low-gain mic, or in a room whose noise
  // floor sits near where speech lands, it may not: `speaking` latches true,
  // the quiet branch never runs, stop() is never called and NOTHING IS EVER
  // SENT. That failure is silent and looks exactly like the feature hanging.
  // A ceiling turns it into a merely-clipped question, which is visible on
  // screen and can be corrected, instead of a dead microphone.
  var MAX_TURN_MS = 15000;

  // Peak level seen this turn, reported next to the threshold that judged
  // it. Whether the gate is set right for a given microphone is not a thing
  // anyone can hear - it has to be read.
  var peakRms = 0;

  var floorLevel = FLOOR_MIN, calibUntil = 0, calibPeak = 0;

  function speechLevel(){
    return Math.max(floorLevel * OVER_FLOOR + FLOOR_MARGIN, ABS_MIN);
  }

  var stream=null, ctx=null, analyser=null, data=null, raf=null;
  var recorder=null, chunks=[];
  var live=false, muted=false, speaking=false, heardAt=0, startedAt=0;
  var recStarted=0, recycling=false;

  function diag(msg){
    try { console.log("[voice] " + msg); } catch (e) {}
  }
  var player=null, audioUrl=null;
  // Sentence pipeline: what is queued, what is playing, whether the
  // answer has finished arriving, and how much of it we have consumed.
  var sayQueue=[], playing=false, streamDone=true, spokenBuf="";
  var seenChars=0, answerLang="en", barged=false, loudSince=0;
  var phase="idle";

  function setPhase(p, msg){
    phase = p;
    orb.classList.toggle("think", p === "think");
    orb.classList.toggle("talk",  p === "talk");
    orb.classList.toggle("muted", muted && p === "listen");
    label.textContent = msg || (p === "listen" ? (muted ? "Muted" : "Listening")
                        : p === "think" ? "Thinking" : "Speaking");
  }

  function show(who, txt){
    said.innerHTML = "";
    var d = document.createElement("div");
    if (who === "reply") d.className = "vx-reply";
    d.textContent = txt;
    said.appendChild(d);
  }

  // ── the level loop ────────────────────────────────────────────────
  function loop(){
    raf = requestAnimationFrame(loop);
    if (!analyser) return;
    analyser.getByteTimeDomainData(data);
    var sum = 0;
    for (var i = 0; i < data.length; i++){
      var v = (data[i] - 128) / 128;
      sum += v * v;
    }
    var rms = Math.sqrt(sum / data.length);

    // The orb tracks the voice even when we are not recording, so the
    // client can see the microphone is live before they commit to a
    // sentence.
    if (phase === "listen" && !muted){
      orb.style.transform = "scale(" + (1 + Math.min(rms * 2.4, 0.34)) + ")";
    } else if (phase === "talk"){
      orb.style.transform = "scale(" + (1.04 + Math.sin(Date.now() / 190) * 0.035) + ")";

      // BARGE-IN. Talking over the answer stops it, the way it would stop a
      // person. Echo cancellation removes the answer from what the mic
      // hears, but not perfectly, so the bar is set higher than for normal
      // speech and has to be held - a single spike is a door, not a
      // sentence.
      if (!muted){
        if (rms > speechLevel() * 1.9){
          if (!loudSince) loudSince = Date.now();
          if (Date.now() - loudSince > 260) bargeIn();
        } else {
          loudSince = 0;
        }
      }
    } else {
      orb.style.transform = "scale(1)";
    }

    if (phase !== "listen" || muted || !recorder) return;

    var now = Date.now();

    // Opening moments: learn the room before reacting to it. Reacting
    // during this window would treat the client's own "hello" as the
    // baseline and then never hear them again.
    if (now < calibUntil){
      calibPeak = Math.max(calibPeak, rms);
      return;
    }
    if (calibPeak > 0){
      floorLevel = Math.max(calibPeak, FLOOR_MIN);
      calibPeak = 0;
    }

    // Keep following the room while it is quiet, so a fan or a street that
    // starts up later raises the bar instead of holding a conversation.
    if (!speaking && rms < speechLevel()){
      floorLevel = Math.max(FLOOR_MIN, floorLevel * 0.995 + rms * 0.005);
    }

    // Nothing said for a while: throw the recording away and begin a fresh
    // one, so what eventually gets sent is the question rather than the wait
    // before it. Only well clear of speech, so onset is never clipped.
    if (!speaking && !recycling && recorder.state === "recording"
        && (now - recStarted) > RECYCLE_MS
        && (now - heardAt) > RECYCLE_CALM){
      recycling = true;
      try { recorder.stop(); } catch (e) { recycling = false; }
      return;
    }

    if (rms > peakRms) peakRms = rms;

    if (rms > speechLevel()){
      if (!speaking){ speaking = true; startedAt = now; chunks = []; }
      heardAt = now;
      // Speech that never stops (or a room the gate cannot see past) must
      // still produce a turn rather than recording until the tab closes.
      if ((now - startedAt) > MAX_TURN_MS){
        speaking = false;
        if (recorder.state === "recording"){
          diag("turn capped at " + (MAX_TURN_MS / 1000) + "s");
          recorder.stop();
        }
      }
    } else if (speaking && (now - heardAt) > QUIET_MS){
      speaking = false;
      if ((heardAt - startedAt) < MIN_SPEECH){ return; }   // too brief
      if (recorder.state === "recording") recorder.stop();
    }
  }

  // ── one turn ──────────────────────────────────────────────────────
  function sendTurn(blob){
    setPhase("think");
    show("said", "");
    fetch("/r/" + RID + "/transcribe?token=" + encodeURIComponent(TOKEN),
          {method: "POST", body: blob})
      .then(function(r){ if (!r.ok) throw new Error("stt"); return r.json(); })
      .then(function(j){
        var q = (j.text || "").trim();
        if (!q){ resume(); return; }
        show("said", q);
        // Straight into the ordinary chat. Voice adds no path of its own.
        answerLang = j.language || "en";
        spokenBuf = ""; seenChars = 0; streamDone = false; barged = false;
        ask(q,
            function(answer){
              if (!answer){ streamDone = true; if (!playing && !sayQueue.length) resume(); return; }
              speak(answer, answerLang);
            },
            onAnswerDelta);
      })
      .catch(function(){ resume(); });
  }

  // ── speaking, a sentence at a time ────────────────────────────────
  //
  // The answer is spoken AS IT ARRIVES rather than after it is complete.
  // Whisper, the model and piper are each fast; what made voice mode feel
  // slow was doing them strictly one after another, so the client heard
  // nothing until the whole answer existed. Now the first sentence is being
  // synthesised while the rest is still being written.
  //
  // Order matters more than speed here: sentences must be heard in the
  // order they were written, so each is queued and the queue is drained one
  // at a time, never in parallel.
  function enqueue(sentence){
    if (!sentence) return;
    sayQueue.push(sentence);
    pump();
  }

  function pump(){
    if (!live || playing || !sayQueue.length) return;
    var next = sayQueue.shift();
    playing = true;
    setPhase("talk");
    fetch("/r/" + RID + "/speak?token=" + encodeURIComponent(TOKEN), {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text: next, language: answerLang || "en"})
    })
      .then(function(r){ if (!r.ok) throw new Error("tts"); return r.blob(); })
      .then(function(b){
        if (!live || barged){ playing = false; return; }
        audioUrl = URL.createObjectURL(b);
        player = new Audio(audioUrl);
        player.onended = function(){
          playing = false;
          releaseUrl();
          // Nothing left AND the answer is finished: hand the turn back.
          if (!sayQueue.length && streamDone) resume(); else pump();
        };
        player.onerror = function(){ playing = false; releaseUrl(); pump(); };
        player.play().catch(function(){
          playing = false; releaseUrl(); pump();
        });
      })
      .catch(function(){
        playing = false;
        if (!sayQueue.length && streamDone) resume(); else pump();
      });
  }

  // Split off whatever complete sentences have arrived, leaving any partial
  // one in the buffer. Speaking half a sentence and then pausing to fetch
  // the rest is worse than waiting for the full stop.
  // A SCAN, NOT A REGEX, AND THE REASON IS MONEY.
  //
  // The obvious pattern - split on . ! ? - breaks every Dutch and German
  // figure in the report. "3.496.695,36" contains two full stops, so the
  // client heard "three. four hundred ninety six. six ninety five point
  // three six" read as three separate sentences. A period only ends a
  // sentence when whitespace or the end of the answer follows it; between
  // digits it is a thousands separator.
  //
  // CJK stops are different: 。！？ end a sentence with no space after
  // them, because those languages do not put one there.
  //
  // The earlier version also never consumed the buffer - lastIndex is zero
  // once exec returns null - so every sentence was spoken again on every
  // delta. Both faults were found by simulating a streamed answer rather
  // than by listening to one.
  function drainSentences(force){
    var out = [], start = 0, i = 0;
    while (i < spokenBuf.length){
      var c = spokenBuf.charAt(i);
      var cjk = (c === "\u3002" || c === "\uFF01" || c === "\uFF1F");
      var ascii = (c === "." || c === "!" || c === "?");
      if (!cjk && !ascii){ i++; continue; }
      if (ascii){
        var nxt = (i + 1 < spokenBuf.length) ? spokenBuf.charAt(i + 1) : null;
        if (nxt !== null && !/[\\s]/.test(nxt)){ i++; continue; }
        // A trailing stop may just be mid-number; wait for more.
        if (nxt === null && !force){ i++; continue; }
      }
      var j = i + 1;
      while (j < spokenBuf.length &&
             /[.!?\u3002\uFF01\uFF1F\\s]/.test(spokenBuf.charAt(j))) j++;
      var s = spokenBuf.slice(start, j).replace(/^[\\s]+|[\\s]+$/g, "");
      if (s) out.push(s);
      start = j; i = j;
    }
    spokenBuf = spokenBuf.slice(start);
    if (force && spokenBuf.replace(/[\\s]/g, "")){
      out.push(spokenBuf.replace(/^[\\s]+|[\\s]+$/g, ""));
      spokenBuf = "";
    }
    return out;
  }

  function onAnswerDelta(full){
    if (!live || barged) return;
    // Only the newly-arrived tail is ever added to the buffer.
    var fresh = full.slice(seenChars);
    seenChars = full.length;
    spokenBuf += stripMd(fresh);
    drainSentences(false).forEach(enqueue);
  }

  function stripMd(t){
    return String(t).replace(/[*_`#>|]/g, " ").replace(/[\\s]+/g, " ");
  }

  function speak(answer, lang){
    show("reply", stripMd(answer).trim());
    streamDone = true;
    // Anything after the last full stop, plus the case where the whole
    // answer had no sentence-ending punctuation at all.
    drainSentences(true).forEach(enqueue);
    if (!playing && !sayQueue.length){ resume(); return; }
    pump();
    return;

  }

  // Playback owns two things that must be released: the element, and the
  // blob URL behind it, which leaks for the life of the page otherwise.
  function stopAudio(){
    if (player){
      try { player.pause(); } catch (e) {}
      player.onended = null; player.onerror = null;
      player = null;
    }
    releaseUrl();
  }

  // A blob URL survives the element that used it, so it is revoked
  // explicitly; otherwise every sentence spoken leaks one for the life
  // of the page.
  function releaseUrl(){
    if (audioUrl){
      try { URL.revokeObjectURL(audioUrl); } catch (e) {}
      audioUrl = null;
    }
  }

  // Stop talking immediately and start listening. Everything queued is
  // dropped: the client interrupted because they did not want the rest.
  function bargeIn(){
    if (!live || phase !== "talk") return;
    barged = true; loudSince = 0;
    sayQueue = []; playing = false;
    stopAudio();
    resume();
  }

  function resume(){
    if (!live) return;
    barged = false; loudSince = 0;
    sayQueue = []; playing = false; spokenBuf = ""; seenChars = 0;
    streamDone = true;
    setPhase("listen");
    speaking = false; chunks = [];
    // Re-measure on every turn: the client may have moved closer, or the
    // room may have changed while the answer was playing.
    calibUntil = Date.now() + CALIBRATE_MS; calibPeak = 0;
    if (recorder && recorder.state === "inactive"){
      try { recorder.start(); recStarted = Date.now(); } catch (e) {}
    }
  }

  // ── open / close ──────────────────────────────────────────────────
  function start(){
    // Echo cancellation is what makes interruption possible at all: it
    // subtracts what the speakers are playing from what the microphone
    // hears, so the client can talk over the answer without the page
    // transcribing its own voice back to itself.
    navigator.mediaDevices.getUserMedia({audio: {
      echoCancellation: true, noiseSuppression: true, autoGainControl: true
    }}).then(function(s){
      stream = s; live = true; muted = false;
      vx.hidden = false;
      mute.classList.remove("off");

      var AC = window.AudioContext || window.webkitAudioContext;
      ctx = new AC();
      analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      data = new Uint8Array(analyser.fftSize);
      ctx.createMediaStreamSource(s).connect(analyser);

      try { recorder = new MediaRecorder(s); }
      catch (e) { stop(); return; }
      recorder.ondataavailable = function(e){
        if (e.data && e.data.size) chunks.push(e.data);
      };
      recorder.onstop = function(){
        var blob = new Blob(chunks, {type: chunks.length ? chunks[0].type : "audio/webm"});
        chunks = [];
        if (recycling){                     // a discarded wait, not a turn
          recycling = false;
          if (live && !muted){
            try { recorder.start(); recStarted = Date.now(); } catch (e) {}
          }
          return;
        }
        if (!live) return;
        diag("turn: " + blob.size + "B over "
             + ((Date.now() - recStarted) / 1000).toFixed(1) + "s | peak rms "
             + peakRms.toFixed(4) + " vs gate " + speechLevel().toFixed(4)
             + " | floor " + floorLevel.toFixed(4));
        peakRms = 0;
        if (blob.size > 1200) sendTurn(blob); else resume();
      };
      recorder.start(); recStarted = Date.now();
      setPhase("listen");
      show("said", "");
      calibUntil = Date.now() + CALIBRATE_MS; calibPeak = 0;
      loop();
    }).catch(function(){ /* refused: stay where we are */ });
  }

  function stop(){
    live = false;
    stopAudio();
    if (raf) cancelAnimationFrame(raf); raf = null;
    if (recorder && recorder.state === "recording"){
      try { recorder.stop(); } catch (e) {}
    }
    recorder = null;
    if (ctx){ try { ctx.close(); } catch (e) {} ctx = null; }
    analyser = null;
    // The microphone light in the browser chrome must go out with the UI.
    if (stream){ stream.getTracks().forEach(function(t){ t.stop(); }); }
    stream = null;
    vx.hidden = true;
    setPhase("idle");
  }

  open.onclick = start;
  endBt.onclick = stop;
  mute.onclick = function(){
    muted = !muted;
    mute.classList.toggle("off", muted);
    if (muted && recorder && recorder.state === "recording"){
      try { recorder.stop(); } catch (e) {}
      speaking = false;
    } else if (!muted){
      resume();
    }
    setPhase(phase);
  };
  // Escape leaves, because a full-screen surface with a live microphone
  // needs the exit every other full-screen surface has.
  document.addEventListener("keydown", function(e){
    if (e.key === "Escape" && live) stop();
  });
})();


document.getElementById("send").onclick = function(){
  var q = document.getElementById("q");
  ask(q.value); q.value = "";
};
document.getElementById("q").addEventListener("keydown", function(e){
  // "Enter" is the standard key value; "Return" and keyCode 13 cover the
  // synthetic and legacy senders that still say it the old way. The
  // isComposing guard matters for CJK and other IME input: Enter there
  // commits the composition, and sending on it would fire a half-typed
  // question the client never finished.
  var isEnter = e.key === "Enter" || e.key === "Return" || e.keyCode === 13;
  if (isEnter && !e.isComposing){
    e.preventDefault();
    ask(this.value); this.value = "";
  }
});
// Delegated at the document, because chips are now created inside every
// answer bubble rather than living in one container that could own a
// listener.
// Clicking a suggestion LOADS it into the box rather than sending it.
// A chip is a starting point — the client may want to change a word, and
// a question that fires on touch takes that away.
document.addEventListener("click", function(e){
  var el = e.target.closest && e.target.closest("[data-q]");
  if (!el) return;
  var box = document.getElementById("q");
  box.value = el.getAttribute("data-q");
  box.focus();
  box.setSelectionRange(box.value.length, box.value.length);
});

// Chips come from the server, built from the blocks THIS report contains
// and what has already been asked — so they stop repeating and stay
// relevant to the document in front of the client.
function chipRow(list){
  var box = document.createElement("div");
  box.className = "chips inline";
  list.forEach(function(c){
    // Server sends {q, label, kind}. Older shapes sent a bare string;
    // tolerated so a cached page mid-deploy still renders something.
    var q = (typeof c === "string") ? c : c.q;
    var label = (typeof c === "string") ? c : (c.label || c.q);
    var b = document.createElement("button");
    b.setAttribute("data-q", q);
    b.className = (c && c.kind === "capability") ? "chip-draw" : "";
    // The whole question, not a truncated label. These stack one per row,
    // so there is room for it — and the client is about to see this exact
    // text land in the input, which a shortened label would not match.
    b.textContent = q;
    box.appendChild(b);
  });
  return box;
}

// Drag the divider to widen the conversation. Persisted so the choice
// survives a reload — a client who wants a big chat pane wants it every time.
(function(){
  var chat = document.getElementById("chat"), grip = document.getElementById("grip");
  var saved = localStorage.getItem("ape_chat_w");
  if (saved) chat.style.width = saved + "px";
  var dragging = false;
  grip.addEventListener("mousedown", function(e){
    dragging = true; grip.classList.add("on");
    document.body.style.userSelect = "none"; e.preventDefault();
  });
  window.addEventListener("mousemove", function(e){
    if (!dragging) return;
    var w = Math.min(Math.max(window.innerWidth - e.clientX, 280),
                     window.innerWidth * 0.7);
    chat.style.width = w + "px";
  });
  window.addEventListener("mouseup", function(){
    if (!dragging) return;
    dragging = false; grip.classList.remove("on");
    document.body.style.userSelect = "";
    localStorage.setItem("ape_chat_w", parseInt(chat.style.width, 10));
  });
})();
</script></body></html>"""
