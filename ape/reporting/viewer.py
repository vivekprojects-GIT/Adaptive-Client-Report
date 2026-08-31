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
 .bar-actions{display:flex;gap:8px;align-items:center}
 /* The player sits with the document, not in the chat rail: it is a way to
    consume THIS report, not a conversation about it. */
 .podwrap{max-width:760px;margin:0 auto 14px;padding:12px 14px;
   border:1px solid #e2e8f0;border-radius:8px;background:#fff}
 .podhd{display:flex;gap:10px;align-items:baseline;margin-bottom:8px;
   font-size:13px;color:#0f172a}
 .podhd span{font-size:12px;color:#b45309}
 .podwrap audio{width:100%}
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
 .chat .hd2{padding:14px 16px;border-bottom:1px solid #e2e8f0;font-weight:700;
   font-size:14px;color:#0f172a}
 .chat .ctx{display:none;margin:10px 14px 0;background:#eff6ff;
   border:1px solid #bfdbfe;border-radius:6px;padding:7px 10px;font-size:11.5px;
   color:#1d4ed8}
 .chat .ctx b{display:block;font-size:11px}
 .chat .ctx button{float:right;border:0;background:none;color:#60a5fa;
   cursor:pointer;font-size:12px}
 .msgs{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;
   gap:10px}
 .m-hint{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
   padding:10px 12px;font-size:12.5px;color:#475569}
 .m-hint.resumed{background:none;border:0;text-align:center;padding:2px 0;
   font-size:10.5px;color:#94a3b8;text-transform:uppercase;
   letter-spacing:.05em}
 .m-q{align-self:flex-end;background:#2563eb;color:#fff;border-radius:12px 12px 2px 12px;
   padding:8px 12px;font-size:13px;max-width:85%}
 .m-a{align-self:flex-start;background:#f8fafc;border:1px solid #e2e8f0;
   border-radius:12px 12px 12px 2px;padding:9px 12px;font-size:13px;max-width:92%;
   color:#0f172a;line-height:1.55}
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
 .chips.inline{padding:0;margin-top:9px;padding-top:8px;
   border-top:1px solid #e2e8f0;flex-direction:column;align-items:stretch;
   gap:5px}
 .chips.inline button{font-size:11.5px;padding:6px 10px;width:100%;
   white-space:normal;text-align:left;line-height:1.4;border-radius:8px}
 .chips button.chip-draw{border-color:#c7d2fe;background:#eef2ff;color:#4338ca}
 .chips button.chip-draw:hover{border-color:#4F46E5;background:#e0e7ff}
 .fb{display:flex;gap:6px;margin-top:7px}
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
 .ask{display:flex;gap:8px;padding:12px 14px;border-top:1px solid #e2e8f0}
 .ask input{flex:1;border:1px solid #cbd5e1;border-radius:7px;padding:9px 11px;
   font-size:13px;outline:none}
 .ask input:focus{border-color:#2563eb}
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
      <button class="btn" id="dl">Download PDF</button>
    </div>
  </div>
  <div id="podwrap" class="podwrap" hidden>
    <div class="podhd"><b>Your report as a podcast</b><span id="podnote"></span></div>
    <audio id="podaudio" controls preload="none"></audio>
    <details id="poddet"><summary>Read the script</summary>
      <pre id="podscript"></pre></details>
  </div>
  __DOC__
</div>

<div class="chat" id="chat">
  <div class="grip" id="grip" title="Drag to resize"></div>
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
    <input id="q" placeholder="Ask a follow up question..." autocomplete="off">
    <button id="send">&#10148;</button>
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
  function show(j){
    audio.src = j.audio_url;
    note.textContent = j.note || "";
    pre.textContent = j.script || "";
    wrap.hidden = false;
    btn.textContent = "🎧 Listen";
    btn.disabled = false;
  }

  var polls = 0;
  (function poll(){
    fetch("/r/" + RID + "/podcast?token=" + encodeURIComponent(TOKEN))
      .then(function(r){ return r.json(); })
      .then(function(j){
        if (j.status === "ready") { show(j); return; }
        if (j.status === "pending" && polls++ < 20) {
          btn.textContent = "Preparing audio…";
          btn.disabled = true;
          setTimeout(poll, 6000);
          return;
        }
        // Nothing waiting for us — let the client ask for one.
        btn.textContent = "🎧 Listen";
        btn.disabled = false;
      })
      .catch(function(){ btn.disabled = false; });
  })();

  btn.onclick = function(){
    if (btn.disabled) return;
    btn.disabled = true;
    var t0 = Date.now(), label = btn.textContent;
    btn.textContent = "Making your podcast…";
    var tick = setInterval(function(){
      var s = Math.round((Date.now() - t0) / 1000);
      btn.textContent = "Making your podcast… " + s + "s";
    }, 1000);

    ev("podcast_requested", {});
    fetch("/r/" + RID + "/podcast", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({token: TOKEN, minutes: 2})
    }).then(function(r){
      return r.json().then(function(j){ return {ok: r.ok, body: j}; });
    }).then(function(res){
      clearInterval(tick);
      btn.disabled = false;
      btn.textContent = label;
      if (!res.ok) {
        note.textContent = (res.body && res.body.detail) || "could not make the audio";
        wrap.hidden = false;
        return;
      }
      audio.src = res.body.audio_url;
      note.textContent = res.body.note || "";
      pre.textContent = res.body.script || "";
      wrap.hidden = false;
      audio.scrollIntoView({behavior: "smooth", block: "nearest"});
      ev("podcast_ready", {});
    }).catch(function(e){
      clearInterval(tick);
      btn.disabled = false;
      btn.textContent = label;
      note.textContent = "could not reach the audio service";
      wrap.hidden = false;
    });
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
function ask(question){
  if (busy || !question.trim()) return;
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
  }

  fetch("/r/__RID__/chat/stream", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({token: TOKEN, question: question,
                          block_id: selBlock, selected_text: selText,
                          conversation_id: conversationId})
  }).then(function(r){
    if (!r.ok || !r.body) throw new Error("stream failed");
    var reader = r.body.getReader(), dec = new TextDecoder(), buf = "";

    function handle(evt, data){
      if (evt === "delta"){ text += data.text; paint(); }
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
      }
      else if (evt === "error"){ fail(); }
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

document.getElementById("send").onclick = function(){
  var q = document.getElementById("q");
  ask(q.value); q.value = "";
};
document.getElementById("q").addEventListener("keydown", function(e){
  if (e.key === "Enter"){ ask(this.value); this.value = ""; }
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
