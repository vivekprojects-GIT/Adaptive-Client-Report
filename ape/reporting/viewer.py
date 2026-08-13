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


def _opening_chips(snapshot=None) -> str:
    """The chips a client sees before they have asked anything.

    Half say what the document covers; half say what can be DRAWN from it.
    Most people do not know they can ask a report for a chart, and a chip
    is how an interface says what it can do — but only for subjects this
    client's own data can fill, so a chip never leads to "sorry, not
    enough data".

    Falls back to content-only when the snapshot is missing or too thin to
    draw anything, rather than showing a control that cannot deliver.
    """
    chips = list(OPENING_CONTENT[:N_CONTENT])
    if snapshot is not None:
        try:
            from ape.reporting import chat_widgets as cw
            for binding in cw.chip_bindings(snapshot)[:N_CAPABILITY]:
                chip = cw.CHIPS.get(binding)
                if chip:
                    chips.append((chip, "See it as a chart"))
        except Exception:
            pass
    if len(chips) < N_CONTENT + N_CAPABILITY:
        for extra in OPENING_CONTENT[N_CONTENT:]:
            if len(chips) >= N_CONTENT + N_CAPABILITY:
                break
            chips.append(extra)
    return "\n".join(
        f'    <button data-q="{_esc(q)}">{_esc(label)}</button>'
        for q, label in chips[:N_CONTENT + N_CAPABILITY])


def render_viewer(report: Dict[str, Any], token: str, snapshot=None) -> str:
    doc = render_body(report, internal=False)
    first_name = _esc(str(report.get("client_name", "")).split(" ")[0])
    rid = _esc(report["report_id"])

    # Section nav from the numbered, titled blocks.
    nav_items = []
    for b in report["blocks"]:
        if b.get("title") and b["type"] not in ("narrative", "callout",
                                                "disclosures", "explainer"):
            nav_items.append(
                f'<a href="#" data-goto="{_esc(b["block_id"])}">'
                f'{_esc(b["title"])}</a>')
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
        .replace("__CHIPS__", _opening_chips(snapshot)) \
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
 .doc{min-height:auto;box-shadow:0 1px 4px rgba(15,23,42,.08);border-radius:8px}
 section[data-block-id]{cursor:pointer;border-radius:4px}
 section[data-block-id].sel{outline:2px solid #2563eb;outline-offset:8px}
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
 .chips{padding:0 14px 8px;display:flex;flex-wrap:wrap;gap:6px}
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
    <button class="btn" id="dl">Download PDF</button>
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

document.getElementById("dl").onclick = function(){
  ev("pdf_downloaded", {}); window.print();
};

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
function setCtx(sec){
  sections.forEach(function(s){ s.classList.remove("sel"); });
  if (!sec){ selBlock = null; selText = "";
    document.getElementById("ctx").style.display = "none"; return; }
  sec.classList.add("sel");
  selBlock = sec.getAttribute("data-block-id");
  document.getElementById("ctx").style.display = "block";
  document.getElementById("ctxlabel").textContent = " " + titleOf(sec) +
    (selText ? ' — "' + selText.slice(0, 60) +
      (selText.length > 60 ? "…" : "") + '"' : "");
  ev("block_highlighted", {block_id: selBlock});
  document.getElementById("q").focus();
}
sections.forEach(function(sec){
  sec.addEventListener("click", function(){
    var t = window.getSelection ? String(window.getSelection()) : "";
    selText = (t && t.trim().length > 3) ? t.trim() : "";
    setCtx(sec);
  });
});
document.getElementById("ctxoff").onclick = function(){ setCtx(null); };

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
function addAnswer(res){
  var d = add("m-a", "");
  d.innerHTML = md(res.answer);
  // A chart the client asked for, built server-side from the same frozen
  // snapshot the report was. Same two layers as the document: the SVG is
  // written in directly, and the runtime upgrades it if it is there.
  if (res.widget && res.widget.svg){
    var w = document.createElement("div"); w.className = "cw-ans";
    var cap = document.createElement("span");
    cap.textContent = res.widget.title;
    w.appendChild(cap);
    var box = document.createElement("div");
    box.className = "ecw";
    box.setAttribute("data-kind", res.widget.kind);
    if (res.widget.option){
      box.setAttribute("data-opt", JSON.stringify(res.widget.option));
    }
    box.innerHTML = '<div class="ecw-live"></div>' +
                    '<div class="ecw-fallback">' + res.widget.svg + '</div>';
    w.appendChild(box); d.appendChild(w);
    if (window.apeEnhanceWidgets) window.apeEnhanceWidgets(d);
  }
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
  add("m-q", question);
  var t = add("typing", "thinking…");
  post("/chat", {question: question, block_id: selBlock,
                 selected_text: selText, conversation_id: conversationId})
    .then(function(res){
      t.remove();
      if (res.answer){
        conversationId = res.conversation_id;
        addAnswer(res);
        setChips(res.followups);
      } else {
        add("m-a", "Something went wrong — please try again.");
      }
    })
    .catch(function(){ t.remove();
      add("m-a", "Something went wrong — please try again."); })
    .finally(function(){ busy = false;
      document.getElementById("send").disabled = false; });
}
document.getElementById("send").onclick = function(){
  var q = document.getElementById("q");
  ask(q.value); q.value = "";
};
document.getElementById("q").addEventListener("keydown", function(e){
  if (e.key === "Enter"){ ask(this.value); this.value = ""; }
});
document.getElementById("chips").addEventListener("click", function(e){
  var q = e.target.getAttribute && e.target.getAttribute("data-q");
  if (q) ask(q);
});

// Chips come from the server, built from the blocks THIS report contains
// and what has already been asked — so they stop repeating and stay
// relevant to the document in front of the client.
function setChips(list){
  if (!list || !list.length) return;
  var box = document.getElementById("chips");
  box.innerHTML = "";
  list.forEach(function(q){
    var b = document.createElement("button");
    b.setAttribute("data-q", q);
    b.textContent = q.length > 34 ? q.slice(0, 32) + "…" : q;
    b.title = q;
    box.appendChild(b);
  });
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
