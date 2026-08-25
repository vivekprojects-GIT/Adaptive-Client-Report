"""Widgets the report chat can draw in an answer.

A client reading their report can ask to see something rather than read it
— "show me that as a pie chart", "can I see the fees broken down". This is
the registry that makes such a request answerable, and the record of it
that teaches the composer what to build next time.

    question -> is a visual being asked for?
                      |
             binding + kind, chosen from THIS registry
                      |
             data bound in code from the frozen snapshot
                      |
             SVG + ECharts option, returned with the answer
                      |
             the ask is recorded, and skill.py turns it into a brief line

THE MODEL PICKS THE WIDGET, NEVER THE NUMBERS
---------------------------------------------
This is the same split the composer uses, for the same reason. The model
chooses a BINDING NAME and a KIND from the catalogue below; the numbers are
then read out of the snapshot by the functions here. There is no path by
which a figure in a chat chart can be anything other than what the report
was frozen against — not because we validate the model's arithmetic, but
because the model is never asked to do any.

That matters more here than anywhere else in the system. A chart in a chat
answer looks exactly as authoritative as a chart in the report, and the
grounding validator only reads prose.

WHY A BINDING IS NOT JUST A KIND
--------------------------------
"Show me a pie chart" is under-specified: a pie of what? The binding is the
subject (allocation, fees, attribution) and the kind is the treatment. A
client usually names one and implies the other, so both are resolved
separately and each has a fallback.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from ape.reporting.csv_source import ClientSnapshot

# Kinds grouped by the data shape they can render. A binding advertises its
# shape, and only kinds from the matching group may be applied to it — a
# client asking for a line chart of their asset allocation is asking for
# something that would misrepresent the data, and gets the nearest honest
# rendering instead.
SHAPE_KINDS = {
    "parts":       ("donut", "pie", "treemap", "bar", "hbar", "funnel"),
    "categorical": ("bar", "hbar", "waterfall", "treemap"),
    "timeseries":  ("line", "area", "bar", "combo"),
    "paired":      ("bar", "hbar", "radar"),
}

DEFAULT_KIND = {"parts": "donut", "categorical": "bar",
                "timeseries": "line", "paired": "bar"}

# What the client can ask to see, and the phrases that mean it.
BINDINGS: Dict[str, Dict[str, Any]] = {
    "allocation": {
        "shape": "parts", "title": "How your portfolio is invested",
        "words": ("allocat", "asset class", "invested", "mix", "split",
                  "breakdown", "diversif", "weight"),
    },
    "allocation_vs_target": {
        "shape": "paired", "title": "Where you sit against your target",
        # The long phrases matter: "allocation against target" also
        # contains "allocat", and scoring by matched LENGTH is what stops
        # the more specific subject losing to the more general one.
        "words": ("against target", "vs target", "versus target",
                  "compared to target", "target allocation", "target weight",
                  "target", "drift", "rebalanc", "off target", "strategic"),
    },
    "attribution": {
        "shape": "categorical", "title": "What drove your return",
        "words": ("drove", "driver", "contribut", "attribut", "why",
                  "detract", "helped", "hurt"),
    },
    "holdings": {
        "shape": "parts", "title": "Your largest holdings",
        "words": ("holding", "position", "stock", "fund", "own", "largest"),
    },
    "performance_history": {
        "shape": "timeseries", "title": "Your return over time",
        "words": ("over time", "history", "trend", "past", "quarter on",
                  "previous", "track record", "since"),
    },
    "portfolio_vs_benchmark": {
        "shape": "paired", "title": "You against your benchmark",
        "words": ("benchmark", "versus", "vs", "compare", "against",
                  "index", "market"),
    },
    "fees": {
        "shape": "parts", "title": "What you paid",
        "words": ("fee", "cost", "charge", "paid", "expense"),
    },
    "cash_flows": {
        "shape": "parts", "title": "Money in and out",
        "words": ("cash flow", "money in and out", "in and out", "cash",
                  "contribut", "withdraw", "deposit", "paid in",
                  "took out", "flow"),
    },
}

# A client naming a chart type by name. Checked before the model is asked,
# because "as a pie chart" is not a judgement call.
# Chart names as clients actually write them, in every language the system
# reports in. Several European languages COMPOUND the word — a Dutch client
# writes "donutdiagram", a German "Tortendiagramm" — so these deliberately
# do not require a word boundary after the chart name.
_KIND_WORDS = [
    (r"\bpie\b|taart|torten|grafico a torta", "pie"),
    (r"\bdonut|doughnut", "donut"),
    (r"\btreemap\b|boomkaart|baumkarte", "treemap"),
    (r"\bfunnel\b|trechter|trichter", "funnel"),
    (r"\bwaterfall\b|waterval|wasserfall|cascade", "waterfall"),
    (r"\bradar|spider\b|spinnen", "radar"),
    (r"\bline (chart|graph)|\btrend line\b|lijndiagram|liniendiagramm"
     r"|courbe|grafico a linee|gráfico de líneas", "line"),
    (r"\barea (chart|graph)\b|vlakdiagram|flächendiagramm", "area"),
    (r"\bbar (chart|graph)|\bcolumn (chart|graph)\b|staafdiagram"
     r"|balkendiagramm|säulendiagramm|histogramme|grafico a barre"
     r"|gráfico de barras", "bar"),
    (r"\bhorizontal bar\b|horizontale staaf", "hbar"),
]

# Wanting to SEE something, as opposed to asking what it is.
# Multilingual for the same reason the kind words are. A Dutch client asking
# "laat mijn verdeling zien als een donutdiagram" was getting prose and no
# chart — which silently removed the draw-it-on-request capability for every
# non-English client, while the feature looked fine in testing because the
# tests were in English.
#
# `diagram` and its cognates are left unbounded on the right so the compounds
# match (donutdiagram, staafdiagram, Tortendiagramm).
_VISUAL_ASK = re.compile(
    r"(\b(chart|graph|plot|visuali[sz]|picture|pie|donut|doughnut|"
    r"treemap|waterfall|radar|show me|draw|display|see (it|this|that)|"
    r"as a (chart|graph|pie|bar)|breakdown|break it down)\b"
    r"|diagram|diagramm|grafiek|grafico|gráfico|graphique"
    r"|laat .{0,24}zien|\btoon\b|\bzeig|\bmontre|\bmuestra|\bmostra"
    r"|visualis)", re.I)


def wants_visual(question: str) -> bool:
    """Whether the client is asking to be shown something.

    Deliberately a keyword test rather than a model call: an unrequested
    chart is worse than no chart, and this decides whether we spend a
    request at all.
    """
    return bool(_VISUAL_ASK.search(question or ""))


def named_kind(question: str) -> Optional[str]:
    """A chart type the client named outright. Honoured over any inference
    — being asked for a pie chart and returning a bar chart is not a
    judgement call, it is not listening."""
    low = (question or "").lower()
    for pattern, kind in _KIND_WORDS:
        if re.search(pattern, low):
            return kind
    return None


# ---------------------------------------------------------------------------
# Data binding — every number below is read from the snapshot
# ---------------------------------------------------------------------------

def _parts(items: List[Tuple[str, float]], unit: str, dp: int = 1):
    return {"items": [{"label": l, "value": v} for l, v in items],
            "unit": unit, "dp": dp}


def _bind(binding: str, snap: ClientSnapshot) -> Optional[Dict[str, Any]]:
    if binding == "allocation":
        if not snap.allocations:
            return None
        return (_parts([(a["asset_class"], a["weight_pct"])
                        for a in snap.allocations], "%"),
                [f"alloc.{a['asset_class']}" for a in snap.allocations])

    if binding == "allocation_vs_target":
        rows = [(a["asset_class"], a["weight_pct"], snap.targets[a["asset_class"]])
                for a in snap.allocations
                if a["asset_class"] in (snap.targets or {})]
        if not rows:
            return None
        return ({"x_categories": [r[0] for r in rows], "unit": "%", "dp": 1,
                 "series": [{"label": "Actual", "values": [r[1] for r in rows]},
                            {"label": "Target", "values": [r[2] for r in rows]}]},
                [f"alloc.{r[0]}" for r in rows])

    if binding == "attribution":
        if not snap.attribution:
            return None
        return ({"x_categories": [a["driver"] for a in snap.attribution],
                 "unit": "%", "dp": 2,
                 "items": [{"label": a["driver"], "value": a["contribution_pct"]}
                           for a in snap.attribution],
                 "series": [{"label": "Contribution",
                             "values": [a["contribution_pct"]
                                        for a in snap.attribution]}]},
                [f"attr.{a['driver']}" for a in snap.attribution])

    if binding == "holdings":
        hs = sorted(snap.holdings or [],
                    key=lambda h: -float(h.get("weight_pct") or 0))[:8]
        if not hs:
            return None
        return (_parts([(str(h.get("name") or h.get("symbol")),
                         float(h.get("weight_pct") or 0)) for h in hs], "%"),
                [f"hold.{h.get('symbol') or h.get('name')}.weight" for h in hs])

    if binding == "performance_history":
        hist = snap.history or []
        if len(hist) < 2:
            return None
        return ({"x_categories": [str(h.get("period", "")) for h in hist],
                 "unit": "%", "dp": 2,
                 "series": [
                     {"label": "Portfolio",
                      "values": [float(h.get("portfolio") or 0) for h in hist]},
                     {"label": "Benchmark",
                      "values": [float(h.get("benchmark") or 0) for h in hist]}]},
                ["quarter_return_pct", "benchmark_return_pct"])

    if binding == "portfolio_vs_benchmark":
        return ({"x_categories": ["Portfolio", "Benchmark"], "unit": "%", "dp": 2,
                 "items": [{"label": "Portfolio", "value": snap.quarter_return_pct},
                           {"label": "Benchmark", "value": snap.benchmark_return_pct}],
                 "series": [{"label": "Return",
                             "values": [snap.quarter_return_pct,
                                        snap.benchmark_return_pct]}]},
                ["quarter_return_pct", "benchmark_return_pct"])

    if binding == "fees":
        f = snap.fees or {}
        items = [(k.replace("_", " ").title(), float(v))
                 for k, v in f.items() if float(v or 0) > 0]
        if not items:
            return None
        return (_parts(items, "£", 2), [f"fees.{k}" for k in f])

    if binding == "cash_flows":
        cf = snap.cash_flows or {}
        items = [(k.replace("_", " ").title(), abs(float(v)))
                 for k, v in cf.items() if float(v or 0)]
        if not items:
            return None
        return (_parts(items, "£", 2), [f"cash.{k}" for k in cf])

    return None


# How much data each shape needs before the chart is worth drawing.
#
# These are not cosmetic. A pie with one slice states that one thing is
# 100% of something; a "trend" through a single point states a direction
# that was never measured. Both are charts that say more than the data
# does, which is worse than no chart — so below these floors we decline
# and explain, rather than draw something technically valid and
# substantively misleading.
MIN_POINTS = {"parts": 2, "categorical": 2, "timeseries": 2, "paired": 2}

# What is missing, in the client's terms rather than ours.
_NEEDS = {
    "allocation": "a breakdown of your portfolio by asset class",
    "allocation_vs_target": "the strategic targets for your asset classes",
    "attribution": "the individual drivers behind your return",
    "holdings": "your individual holdings",
    "performance_history": "returns from more than one period",
    "portfolio_vs_benchmark": "your return and your benchmark's return",
    "fees": "an itemised breakdown of the fees you paid",
    "cash_flows": "the money paid in and taken out over the period",
}


def _points(data: Dict[str, Any]) -> int:
    """How many things the chart would actually plot."""
    if data.get("items"):
        return len(data["items"])
    series = data.get("series") or []
    if series:
        return max(len(s.get("values") or []) for s in series)
    return 0


def unavailable_reason(snap: ClientSnapshot, binding: str) -> Optional[str]:
    """Why this chart cannot be drawn, in a sentence a client can act on.

    Returns None when it can be drawn. The wording names the data that is
    missing rather than the internal reason, because "your report does not
    carry X" is something a client can raise with their adviser, and
    "binding returned None" is not.
    """
    if binding not in BINDINGS:
        return "that is not something this report can chart"
    need = _NEEDS.get(binding, "the underlying detail")
    bound = _bind(binding, snap)
    if bound is None:
        return f"your report does not carry {need}"
    floor = MIN_POINTS[BINDINGS[binding]["shape"]]
    if _points(bound[0]) < floor:
        return (f"your report carries only one line of {need}, and a chart "
                f"of a single value would suggest a comparison that has not "
                f"been measured")
    return None


def available(snap: ClientSnapshot) -> List[str]:
    """The bindings this client's data can actually fill.

    Availability is checked by building and counting, not by guessing from
    which fields are non-empty: a binding that would render an empty or
    single-valued chart must not be on the menu the model chooses from.
    """
    return [b for b in BINDINGS if unavailable_reason(snap, b) is None]


def catalogue(snap: ClientSnapshot) -> str:
    """The menu, as the model sees it."""
    lines = []
    for b in available(snap):
        spec = BINDINGS[b]
        kinds = ", ".join(SHAPE_KINDS[spec["shape"]])
        lines.append(f"  {b} — {spec['title']} (can be drawn as: {kinds})")
    return "\n".join(lines)


# What a client was looking at, and what they were asking about, mapped to
# the subject they most likely want drawn. Module-level so the follow-up
# chips and the resolver agree by construction — a chip that resolved to a
# different chart than it offered would be worse than no chip.
BINDING_BY_BLOCK = {
    "allocation_donut": "allocation",
    "allocation_vs_target": "allocation_vs_target",
    "fees_table": "fees", "holdings_table": "holdings",
    "top_contributors": "attribution", "top_detractors": "attribution",
    "comparison_chart": "portfolio_vs_benchmark",
    "comparison_table": "portfolio_vs_benchmark",
    "performance_history": "performance_history",
    "performance_line": "performance_history",
}

BINDING_BY_INTENT = {
    "fees_cashflow_question": "fees",
    "allocation_question": "allocation",
    "performance_question": "portfolio_vs_benchmark",
    "benchmark_comparison": "portfolio_vs_benchmark",
    "holdings_question": "holdings",
    "report_summary": "allocation",
}

# The chip text offered for each subject. Written so that feeding it back
# through wants_visual / guess_binding / named_kind returns this same
# binding and this same kind — enforced by test_widgets, because a chip
# that draws something other than what it promised is a broken control.
CHIPS = {
    "allocation": "Show me my asset allocation as a donut chart.",
    "allocation_vs_target": "Show me my allocation against target as a bar chart.",
    "attribution": "Show me what drove my return as a waterfall chart.",
    "holdings": "Show me my largest holdings as a treemap.",
    "performance_history": "Plot my return over time as a line chart.",
    "portfolio_vs_benchmark": "Chart my return against the benchmark as a bar chart.",
    "fees": "Show me what I paid as a donut chart.",
    "cash_flows": "Show me my cash flow in and out as a donut chart.",
}


# The short label shown ON the chip. Names the subject and the chart, so
# a client reads what they will get rather than "see it as a chart" — a
# generic label makes every chip look identical and tells them nothing
# about which one answers the question they have.
CHIP_LABELS = {
    "allocation":            "Allocation donut",
    "allocation_vs_target":  "Actual vs target",
    "attribution":           "Return drivers",
    "holdings":              "Holdings treemap",
    "performance_history":   "Return over time",
    "portfolio_vs_benchmark": "You vs benchmark",
    "fees":                  "Fee breakdown",
    "cash_flows":            "Money in and out",
}


def chip(binding: str, locale: Optional[str] = None) -> Optional[Dict[str, str]]:
    """The question to send and the label to show, for one subject.

    Both translate. A chip whose label is Dutch but whose question is
    English sends an English question the moment it is clicked, and the
    conversation drifts back to English one click at a time.

    The KIND is resolved from the ENGLISH question before translating —
    the chart-type keywords are matched against the canonical wording, so
    resolution never depends on how well a translation preserved them.
    """
    q = CHIPS.get(binding)
    if not q:
        return None
    kind = resolve_kind(binding, named_kind(q))
    label = CHIP_LABELS.get(binding, binding.replace("_", " "))
    if locale and locale != "en":
        from ape.reporting.labels import t as _t
        q, label = _t(q, locale), _t(label, locale)
    return {"q": q, "label": label,
            "kind": "capability", "chart": kind, "binding": binding}


def chip_bindings(snap: ClientSnapshot, intent: str = "",
                  block_type: str = "") -> List[str]:
    """Subjects worth offering as a chart, most relevant first.

    Only bindings this client's data can actually fill are returned, so a
    chip can never lead to the decline path — offering a chart and then
    explaining why it cannot be drawn is a worse experience than never
    offering it.
    """
    options = available(snap)
    ordered: List[str] = []
    for cand in (BINDING_BY_BLOCK.get(block_type or ""),
                 BINDING_BY_INTENT.get(intent or "")):
        if cand and cand in options and cand not in ordered:
            ordered.append(cand)
    ordered += [b for b in options if b not in ordered]
    return ordered


def guess_binding(question: str, intent: str, block_type: str,
                  options: List[str]) -> Optional[str]:
    """Resolve the subject without a model call where the wording allows.

    Scored by the LENGTH of the wording each binding matches, not the
    count. "Show me my allocation against target" matches "allocat" for
    allocation and "against target" for allocation_vs_target; counting
    would tie them and hand it to whichever came first, which is how a
    request for drift silently returned a plain allocation chart. The
    longer match is the more specific subject, and specificity is what
    the client actually said.

    A question naming two subjects ("how do my fees compare to the
    benchmark") resolves to whichever it names more strongly, which is not
    always the one a human would pick. That is tolerable because this is
    the FALLBACK: the model picks first, with the whole catalogue in front
    of it, and this only runs when that call is unavailable or returns
    something not on the menu.
    """
    if not options:
        return None
    low = (question or "").lower()
    best, best_score = None, 0
    for b in options:
        score = sum(len(w) for w in BINDINGS[b]["words"] if w in low)
        if score > best_score:
            best, best_score = b, score
    if best:
        return best
    # Nothing named. Fall back to what the client was looking at, then to
    # what they were asking about.
    cand = BINDING_BY_BLOCK.get(block_type or "")
    if cand in options:
        return cand
    cand = BINDING_BY_INTENT.get(intent or "")
    return cand if cand in options else options[0]


def resolve_kind(binding: str, asked: Optional[str]) -> str:
    """The kind to draw. A named kind wins if the data shape supports it;
    otherwise the shape's default, because rendering allocation as a line
    would misstate the data to satisfy the wording of a request."""
    allowed = SHAPE_KINDS[BINDINGS[binding]["shape"]]
    if asked and asked in allowed:
        return asked
    return DEFAULT_KIND[BINDINGS[binding]["shape"]]


def build(snap: ClientSnapshot, binding: str,
          kind: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """The rendered widget, or None if this client's data cannot draw it.

    Returns the SVG and the ECharts option together, exactly as a report
    block does — the chat answer gets the same static floor and the same
    interactive upgrade, not a lesser version of either.
    """
    if unavailable_reason(snap, binding) is not None:
        return None
    bound = _bind(binding, snap)
    if bound is None:
        return None
    data, refs = bound
    k = resolve_kind(binding, kind)
    data = dict(data, kind=k)

    # Translate the SERIES AND CATEGORY LABELS before drawing, so the chart
    # inside a Dutch answer reads "Amerikaanse aandelen" and not "US Equity".
    # Done on a copy and only on the display text — `refs` still carries the
    # English fact keys the grounding gate matches against, exactly as the
    # report's own blocks do.
    lang = getattr(snap, "language", "") or ""
    if lang and lang != "en":
        from ape.reporting.labels import t as _t
        data = dict(data)
        for field in ("items", "segments", "series", "bars", "points"):
            rows = data.get(field)
            if isinstance(rows, list):
                data[field] = [
                    (dict(r, label=_t(r["label"], lang))
                     if isinstance(r, dict) and isinstance(r.get("label"), str)
                     else r)
                    for r in rows]
        if isinstance(data.get("labels"), list):
            data["labels"] = [_t(x, lang) if isinstance(x, str) else x
                              for x in data["labels"]]

    from ape.reporting.charts import render_chart
    from ape.reporting.echarts_opts import build_option
    svg = render_chart(data)
    if "<svg" not in svg:
        return None
    return {"binding": binding, "kind": k,
            "title": BINDINGS[binding]["title"],
            "svg": svg, "option": build_option(data),
            "source_refs": refs}
