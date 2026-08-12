"""Report generation — snapshot + template -> blocks -> HTML.

═══════════════════════════════════════════════════════════════════════════
WHY MOST BLOCKS NEED NO LLM
═══════════════════════════════════════════════════════════════════════════

Of the ten approved block types, eight are pure PROJECTIONS of the snapshot:

    kpi_grid · allocation_donut · performance_line · comparison_chart
    comparison_table · holdings_table · fees_table · risk_card

They restate figures that already exist in the source. Building them in code
means they are grounded BY CONSTRUCTION — there is no path by which a wrong
number can appear, because no model ever touches them.

Only two block types are written:

    narrative · callout

So the grounding validator has a small, well-defined surface: prose only.
That is a much better position than validating an entire generated document,
and it is why Phase 1 works end to end with no LLM at all — the deterministic
builder below stands in until the writer is wired up, and the structural
blocks never change afterwards.

The TEMPLATE decides WHICH blocks appear and in what order. The SNAPSHOT
decides what they contain. Those two never mix: presentation adapts, facts
do not.
"""

from __future__ import annotations

import html
import uuid
from typing import Any, Dict, List, Optional

from .charts import KINDS as CHART_KINDS, render_chart
from .csv_source import ClientSnapshot

_CURRENCY = "£"


def _money(v: float) -> str:
    return f"{_CURRENCY}{v:,.2f}"


def _pct(v: float) -> str:
    return f"{v:+.2f}%" if v else "0.00%"


# ---------------------------------------------------------------------------
# Block builders — one per approved widget type
# ---------------------------------------------------------------------------

def _kpi_grid(s: ClientSnapshot, n: int) -> Dict[str, Any]:
    return {
        "block_id": f"kpi_grid_{n:02d}",
        "type": "kpi_grid",
        "title": "At a glance",
        "data": {"items": [
            {"label": "Portfolio value", "value": s.portfolio_value, "format": "currency"},
            {"label": "Return", "value": s.quarter_return_pct, "format": "percent"},
            {"label": "Benchmark", "value": s.benchmark_return_pct, "format": "percent"},
            {"label": "Risk level", "value": s.risk_level, "format": "text"},
        ]},
        "source_refs": ["portfolio_value", "quarter_return_pct",
                        "benchmark_return_pct"],
    }


def _allocation_donut(s: ClientSnapshot, n: int) -> Optional[Dict[str, Any]]:
    if not s.allocations:
        return None
    return {
        "block_id": f"allocation_donut_{n:02d}",
        "type": "allocation_donut",
        "title": "Asset allocation",
        "data": {"segments": [{"label": a["asset_class"], "value_pct": a["weight_pct"]}
                              for a in s.allocations]},
        "source_refs": [f"alloc.{a['asset_class']}" for a in s.allocations],
    }


def _comparison_chart(s: ClientSnapshot, n: int) -> Dict[str, Any]:
    return {
        "block_id": f"comparison_chart_{n:02d}",
        "type": "comparison_chart",
        "title": "Performance vs benchmark",
        "data": {"portfolio": s.quarter_return_pct,
                 "benchmark": s.benchmark_return_pct,
                 "label": "Return", "unit": "percent"},
        "source_refs": ["quarter_return_pct", "benchmark_return_pct"],
    }


def _comparison_table(s: ClientSnapshot, n: int) -> Dict[str, Any]:
    rows = [{"label": "Portfolio return", "value": s.quarter_return_pct,
             "benchmark_value": s.benchmark_return_pct}]
    for a in s.attribution:
        rows.append({"label": a["driver"], "value": a["contribution_pct"],
                     "benchmark_value": None})
    return {
        "block_id": f"comparison_table_{n:02d}",
        "type": "comparison_table",
        "title": "Contribution to return",
        "data": {"rows": rows},
        "source_refs": (["quarter_return_pct", "benchmark_return_pct"]
                        + [f"attr.{a['driver']}" for a in s.attribution]),
    }


def _fees_table(s: ClientSnapshot, n: int) -> Dict[str, Any]:
    adv = s.fees.get("advisory", 0.0)
    fnd = s.fees.get("fund", 0.0)
    return {
        "block_id": f"fees_table_{n:02d}",
        "type": "fees_table",
        "title": "Fees and costs",
        "data": {"rows": [{"label": "Advisory fee", "amount": adv},
                          {"label": "Fund expenses", "amount": fnd}],
                 "total": round(adv + fnd, 2)},
        "source_refs": ["fees.advisory", "fees.fund", "fees.total"],
    }


def _holdings_table(s: ClientSnapshot, n: int) -> Optional[Dict[str, Any]]:
    """Derived from allocations — the CSV carries asset classes, not holdings."""
    if not s.allocations:
        return None
    return {
        "block_id": f"holdings_table_{n:02d}",
        "type": "holdings_table",
        "title": "Allocation detail",
        "data": {"rows": [{
            "name": a["asset_class"], "asset_class": a["asset_class"],
            "weight_pct": a["weight_pct"],
            "value": round(s.portfolio_value * a["weight_pct"] / 100.0, 2),
        } for a in s.allocations]},
        "source_refs": [f"alloc.{a['asset_class']}" for a in s.allocations]
                       + ["portfolio_value"],
    }


def _risk_card(s: ClientSnapshot, n: int) -> Dict[str, Any]:
    return {
        "block_id": f"risk_card_{n:02d}",
        "type": "risk_card",
        "title": "Risk",
        "data": {"risk_level": s.risk_level},
        "source_refs": ["portfolio_value"],
    }


def _performance_line(s: ClientSnapshot, n: int) -> Dict[str, Any]:
    """Single-period series. A real feed would carry history; the CSV does
    not, so we plot the one point we can actually evidence rather than
    inventing a trend."""
    return {
        "block_id": f"performance_line_{n:02d}",
        "type": "performance_line",
        "title": "Return this period",
        "data": {"series": [
            {"label": "Portfolio", "points": [{"period": s.period, "value": s.quarter_return_pct}]},
            {"label": "Benchmark", "points": [{"period": s.period, "value": s.benchmark_return_pct}]},
        ]},
        "source_refs": ["quarter_return_pct", "benchmark_return_pct"],
    }


def _narrative(s: ClientSnapshot, n: int, brief: str) -> Dict[str, Any]:
    """The one block a writer would produce. Until the LLM is wired in this
    states only figures taken directly from the snapshot, so it is grounded
    by construction like the rest."""
    ahead = s.excess_return_pct >= 0
    top = max(s.attribution, key=lambda a: a["contribution_pct"], default=None)
    parts = [
        f"Your portfolio was valued at {_money(s.portfolio_value)} at the end of "
        f"{s.period}, a return of {s.quarter_return_pct:.2f}% for the period.",
        f"That is {abs(s.excess_return_pct):.2f}% "
        f"{'ahead of' if ahead else 'behind'} the benchmark return of "
        f"{s.benchmark_return_pct:.2f}%.",
    ]
    if top:
        parts.append(
            f"{top['driver']} was the largest contributor, adding "
            f"{top['contribution_pct']:.2f}%."
        )
    return {
        "block_id": f"narrative_{n:02d}",
        "type": "narrative",
        "title": None,
        "data": {"text": " ".join(parts)},
        "source_refs": ["portfolio_value", "quarter_return_pct",
                        "benchmark_return_pct", "excess_return_pct"],
        "_brief": brief,
    }


def _callout(s: ClientSnapshot, n: int) -> Dict[str, Any]:
    ahead = s.excess_return_pct >= 0
    return {
        "block_id": f"callout_{n:02d}",
        "type": "callout",
        "title": None,
        "data": {"tone": "positive" if ahead else "info",
                 "text": f"Return {s.quarter_return_pct:.2f}% versus benchmark "
                         f"{s.benchmark_return_pct:.2f}%."},
        "source_refs": ["quarter_return_pct", "benchmark_return_pct"],
    }



def _chart(s: ClientSnapshot, n: int, kind: str = "donut") -> Optional[Dict[str, Any]]:
    """Generic chart block. The template picks the KIND; the data binding is
    chosen from the snapshot to match the shape that kind needs."""
    if kind in ("pie", "donut", "treemap", "funnel"):
        if not s.allocations:
            return None
        data = {"kind": kind,
                "items": [{"label": a["asset_class"], "value": a["weight_pct"]}
                          for a in s.allocations]}
        refs = [f"alloc.{a['asset_class']}" for a in s.allocations]
    elif kind == "waterfall":
        if not s.attribution:
            return None
        data = {"kind": kind,
                "items": [{"label": a["driver"], "value": a["contribution_pct"]}
                          for a in s.attribution]}
        refs = [f"attr.{a['driver']}" for a in s.attribution]
    elif kind in ("gauge", "progress"):
        data = {"kind": kind, "value": s.quarter_return_pct,
                "min": 0, "max": max(10.0, s.quarter_return_pct * 1.5)}
        refs = ["quarter_return_pct"]
    else:
        cats = [a["driver"] for a in s.attribution] or                [a["asset_class"] for a in s.allocations]
        vals = [a["contribution_pct"] for a in s.attribution] or                [a["weight_pct"] for a in s.allocations]
        if not cats:
            return None
        data = {"kind": kind, "x_categories": cats,
                "series": [{"label": "Contribution", "values": vals}]}
        refs = ([f"attr.{a['driver']}" for a in s.attribution]
                or [f"alloc.{a['asset_class']}" for a in s.allocations])
    return {"block_id": f"chart_{n:02d}", "type": "chart",
            "title": None, "data": data, "source_refs": refs}



# ---------------------------------------------------------------------------
# Depth blocks — these need holdings / history / targets, and return None
# when the source cannot supply them. A thinner report is correct; an
# invented one is not.
# ---------------------------------------------------------------------------

TOP_N = 5


def _contributors(s: ClientSnapshot, n: int, detractors: bool = False):
    """What actually drove the return, holding by holding.

    A client asking "why" is asking this. Asset-class attribution answers it
    at one remove; naming the positions answers it directly.
    """
    if not s.holdings:
        return None
    ranked = sorted(s.holdings, key=lambda h: h.get("contribution_pct", 0.0),
                    reverse=not detractors)
    picked = [h for h in ranked
              if (h.get("contribution_pct", 0.0) < 0) == detractors][:TOP_N]
    if not picked:
        return None

    rows = [{"name": h.get("name", h["symbol"]), "symbol": h["symbol"],
             "contribution_pct": h.get("contribution_pct", 0.0),
             "return_pct": h.get("return_pct", 0.0),
             "weight_pct": h.get("weight_pct", 0.0)} for h in picked]
    # "Others" is the residual of everything not named, so the column still
    # sums to the group total and a client can reconcile it themselves.
    named = {h["symbol"] for h in picked}
    rest = [h for h in s.holdings
            if h["symbol"] not in named
            and (h.get("contribution_pct", 0.0) < 0) == detractors]
    kind = "detractors" if detractors else "contributors"
    return {
        "block_id": f"top_{kind}_{n:02d}",
        "type": f"top_{kind}",
        "title": ("Top detractors from return" if detractors
                  else "Top contributors to return"),
        "subtitle": s.period,
        "data": {"rows": rows,
                 "others_pct": round(sum(h.get("contribution_pct", 0.0)
                                         for h in rest), 2),
                 "total_pct": round(sum(h.get("contribution_pct", 0.0)
                                        for h in picked + rest), 2)},
        "source_refs": [f"hold.{h['symbol']}.contribution" for h in picked],
    }


def _top_contributors(s: ClientSnapshot, n: int):
    return _contributors(s, n, detractors=False)


def _top_detractors(s: ClientSnapshot, n: int):
    return _contributors(s, n, detractors=True)


def _allocation_vs_target(s: ClientSnapshot, n: int):
    """Where the portfolio sits against its strategic target. Drift is the
    part an advisor gets asked about, so it is shown rather than left to be
    inferred from two numbers side by side."""
    if not s.targets or not s.allocations:
        return None
    rows = []
    for a in s.allocations:
        ac = a["asset_class"]
        if ac not in s.targets:
            continue
        rows.append({"label": ac, "value": a["weight_pct"],
                     "benchmark_value": s.targets[ac],
                     "drift_pct": round(a["weight_pct"] - s.targets[ac], 2)})
    if not rows:
        return None
    return {
        "block_id": f"allocation_vs_target_{n:02d}",
        "type": "allocation_vs_target",
        "title": "Allocation vs strategic target",
        "subtitle": f"as at {s.as_of}",
        "data": {"rows": rows},
        "source_refs": ([f"alloc.{r['label']}" for r in rows]
                        + [f"target.{r['label']}" for r in rows]),
    }


def _returns_table(s: ClientSnapshot, n: int):
    """Quarter by quarter, plus the compounded total. Needs real history —
    with a single period there is no trend to show."""
    if len(s.history or []) < 2:
        return None
    facts = s.numeric_facts()
    rows = [{"label": h["period"], "value": h.get("portfolio", 0.0),
             "benchmark_value": h.get("benchmark", 0.0),
             "excess_pct": h.get("excess", 0.0)} for h in s.history]
    cum = facts.get("hist.cumulative", 0.0)
    cum_bm = facts.get("hist.cumulative_benchmark", 0.0)
    rows.append({"label": "Cumulative", "value": cum, "benchmark_value": cum_bm,
                 "excess_pct": round(cum - cum_bm, 2), "emphasis": True})
    return {
        "block_id": f"returns_table_{n:02d}",
        "type": "returns_table",
        "title": "Return by period",
        "subtitle": "Portfolio vs benchmark",
        "data": {"rows": rows},
        "source_refs": ([f"hist.{h['period']}.portfolio" for h in s.history]
                        + ["hist.cumulative", "hist.cumulative_benchmark"]),
    }


def _performance_history(s: ClientSnapshot, n: int):
    """The trend line, when there is genuinely a trend on file."""
    if len(s.history or []) < 2:
        return None
    return {
        "block_id": f"performance_history_{n:02d}",
        "type": "performance_line",
        "title": "Return over time",
        "subtitle": f"{s.history[0]['period']} to {s.history[-1]['period']}",
        "data": {"series": [
            {"label": "Portfolio",
             "points": [{"period": h["period"], "value": h.get("portfolio", 0.0)}
                        for h in s.history]},
            {"label": "Benchmark",
             "points": [{"period": h["period"], "value": h.get("benchmark", 0.0)}
                        for h in s.history]},
        ]},
        "source_refs": ([f"hist.{h['period']}.portfolio" for h in s.history]
                        + [f"hist.{h['period']}.benchmark" for h in s.history]),
    }


def _key_takeaways(s: ClientSnapshot, n: int):
    """The "so what". Each takeaway is a claim plus the figure behind it.

    Written from the snapshot rather than by the model, so it is grounded by
    construction — and when the LLM writes these instead, the validator holds
    it to exactly the same standard.
    """
    facts = s.numeric_facts()
    ahead = s.excess_return_pct >= 0
    items = [{
        "title": "Ahead of benchmark" if ahead else "Behind benchmark",
        "tone": "positive" if ahead else "caution",
        "text": (f"Your portfolio returned {s.quarter_return_pct:.2f}% against a "
                 f"benchmark of {s.benchmark_return_pct:.2f}%, "
                 f"{abs(s.excess_return_pct):.2f}% "
                 f"{'ahead' if ahead else 'behind'} for {s.period}."),
    }]

    drivers = [a for a in s.attribution if a["driver"] != "Fees"]
    if drivers:
        top = max(drivers, key=lambda a: a["contribution_pct"])
        weight = next((a["weight_pct"] for a in s.allocations
                       if a["asset_class"] == top["driver"]), None)
        detail = (f" It is {weight:.1f}% of the portfolio." if weight is not None
                  else "")
        items.append({
            "title": f"{top['driver']} led the return",
            "tone": "info",
            "text": (f"{top['driver']} contributed {top['contribution_pct']:.2f}% "
                     f"of the total.{detail}"),
        })
        worst = min(drivers, key=lambda a: a["contribution_pct"])
        if worst["contribution_pct"] < 0 and worst["driver"] != top["driver"]:
            items.append({
                "title": f"{worst['driver']} held the return back",
                "tone": "caution",
                "text": (f"{worst['driver']} reduced the return by "
                         f"{abs(worst['contribution_pct']):.2f}% this period."),
            })

    items.append({
        "title": "What you paid",
        "tone": "info",
        "text": (f"Total fees were {_money(facts.get('fees.total', 0.0))}, "
                 f"which reduced your return by "
                 f"{facts.get('fees.drag_pct', 0.0):.2f}%."),
    })

    return {
        "block_id": f"key_takeaways_{n:02d}",
        "type": "key_takeaways",
        "title": "Key takeaways",
        "data": {"items": items[:4]},
        "source_refs": ["quarter_return_pct", "benchmark_return_pct",
                        "excess_return_pct", "fees.total", "fees.drag_pct"],
    }


def _explainer(s: ClientSnapshot, n: int):
    """Plain-English definitions for the terms used above.

    Wealth reports routinely assume the reader knows what a benchmark or an
    attribution is. Many do not, and the ones who do can skip it.
    """
    return {
        "block_id": f"explainer_{n:02d}",
        "type": "explainer",
        "title": "What these terms mean",
        "data": {"items": [
            {"term": "Benchmark",
             "text": (f"A reference mix ({s.benchmark_name or 'market index'}) "
                      "used to judge performance. Beating it means your "
                      "portfolio did better than the market did at that level "
                      "of risk.")},
            {"term": "Contribution",
             "text": ("How much each part of the portfolio added to, or took "
                      "from, the total return. Contributions add up to the "
                      "return you actually received.")},
            {"term": "Strategic target",
             "text": ("The long-term mix agreed for your risk profile. "
                      "Holdings drift away from it as markets move, and are "
                      "brought back at rebalancing.")},
            {"term": "Net of fees",
             "text": ("Every return shown is after fees have been deducted, so "
                      "it reflects what you actually earned.")},
        ]},
        "source_refs": ["portfolio_value"],
    }


def _disclosures(s: ClientSnapshot, n: int):
    return {
        "block_id": f"disclosures_{n:02d}",
        "type": "disclosures",
        "title": None,
        "data": {"text": ("Past performance is not indicative of future results. "
                          "Figures are net of fees unless stated otherwise."),
                 "source": (f"Valuations as at {s.as_of}. Source: portfolio "
                            f"accounting system, snapshot {s.snapshot_id}.")},
        "source_refs": ["portfolio_value"],
    }


BUILDERS = {
    "chart": _chart,
    "kpi_grid": _kpi_grid,
    "allocation_donut": _allocation_donut,
    "performance_line": _performance_line,
    "comparison_chart": _comparison_chart,
    "comparison_table": _comparison_table,
    "holdings_table": _holdings_table,
    "fees_table": _fees_table,
    "risk_card": _risk_card,
    "callout": _callout,
    "top_contributors": _top_contributors,
    "top_detractors": _top_detractors,
    "allocation_vs_target": _allocation_vs_target,
    "returns_table": _returns_table,
    "performance_history": _performance_history,
    "key_takeaways": _key_takeaways,
    "explainer": _explainer,
    "disclosures": _disclosures,
}


def build_report(
    snapshot: ClientSnapshot,
    template: Dict[str, Any],
    report_type: str,
) -> Dict[str, Any]:
    """Assemble report.json for one client under one template."""
    blocks: List[Dict[str, Any]] = []
    n = 0
    for spec in (template.get("required_blocks") or []):
        n += 1
        # A block spec is "type" or "type:option". The option lets a template
        # say WHICH chart it wants — "chart:waterfall" rather than just
        # "chart", which would always fall back to the default kind.
        block_type, _, option = str(spec).partition(":")
        block_type, option = block_type.strip(), option.strip()

        if block_type == "narrative":
            blocks.append(_narrative(snapshot, n, template.get("brief", "")))
            continue

        builder = BUILDERS.get(block_type)
        if builder is None:
            continue                      # unknown type -> dropped, never rendered

        if block_type == "chart":
            block = builder(snapshot, n, option or "donut")
        else:
            block = builder(snapshot, n)
        if block:
            blocks.append(block)

    return {
        "report_id": f"R_{snapshot.client_id}_{snapshot.period}",
        "client_id": snapshot.client_id,
        "client_name": snapshot.display_name,
        "email": snapshot.email,
        "period": snapshot.period,
        "snapshot_id": snapshot.snapshot_id,
        "report_type": report_type,
        "template_id": template.get("template_id"),
        "template_strategy": template.get("strategy"),
        "template_label": template.get("label"),
        "report_version": 1,
        "blocks": blocks,
    }


# ---------------------------------------------------------------------------
# HTML rendering — every visible block carries data-block-id so a highlight
# in the viewer resolves to a known block without any text matching.
# ---------------------------------------------------------------------------

def _esc(v: Any) -> str:
    return html.escape(str(v))


def _fmt(value: Any, fmt: str) -> str:
    if fmt == "currency":
        return _money(float(value))
    if fmt == "percent":
        return f"{float(value):.2f}%"
    return _esc(value)


def _render_block(b: Dict[str, Any], number: Optional[int] = None) -> str:
    t, d = b["type"], b.get("data", {})
    head = ""
    if b.get("title"):
        num = f'<span class="num">{number}.</span> ' if number else ""
        head = f"<h3>{num}{_esc(b['title'])}</h3>"
        if b.get("subtitle"):
            head += f'<div class="sub">{_esc(b["subtitle"])}</div>'

    if t == "chart":
        body = render_chart(d)

    elif t == "kpi_grid":
        items = "".join(
            f'<div class="kpi"><span>{_esc(i["label"])}</span>'
            f'<b>{_fmt(i["value"], i.get("format", "text"))}</b></div>'
            for i in d.get("items", []))
        body = f'<div class="kpis">{items}</div>'

    elif t == "allocation_donut":
        total = sum(s["value_pct"] for s in d.get("segments", [])) or 1
        bars = "".join(
            f'<div class="alloc"><span>{_esc(s["label"])}</span>'
            f'<i style="width:{s["value_pct"] / total * 100:.1f}%"></i>'
            f'<b>{s["value_pct"]:.1f}%</b></div>'
            for s in d.get("segments", []))
        body = f'<div class="allocs">{bars}</div>'

    elif t == "comparison_chart":
        p, bm = float(d.get("portfolio", 0)), float(d.get("benchmark", 0))
        top = max(abs(p), abs(bm)) or 1
        body = (f'<div class="cmp">'
                f'<div><span>Portfolio</span><i style="width:{abs(p)/top*100:.0f}%"></i>'
                f'<b>{p:.2f}%</b></div>'
                f'<div><span>Benchmark</span><i class="bm" style="width:{abs(bm)/top*100:.0f}%"></i>'
                f'<b>{bm:.2f}%</b></div></div>')

    elif t in ("comparison_table", "holdings_table", "fees_table"):
        rows = d.get("rows", [])
        if t == "fees_table":
            trs = "".join(f"<tr><td>{_esc(r['label'])}</td>"
                          f"<td class='n'>{_money(r['amount'])}</td></tr>" for r in rows)
            if d.get("total") is not None:
                trs += (f"<tr class='tot'><td>Total</td>"
                        f"<td class='n'>{_money(d['total'])}</td></tr>")
            body = f"<table><tbody>{trs}</tbody></table>"
        elif t == "holdings_table":
            trs = "".join(f"<tr><td>{_esc(r['name'])}</td>"
                          f"<td class='n'>{r['weight_pct']:.1f}%</td>"
                          f"<td class='n'>{_money(r['value'])}</td></tr>" for r in rows)
            body = ("<table><thead><tr><th>Asset class</th><th class='n'>Weight</th>"
                    f"<th class='n'>Value</th></tr></thead><tbody>{trs}</tbody></table>")
        else:
            cells = []
            for r in rows:
                bench = r.get("benchmark_value")
                bench_cell = "" if bench is None else f"{float(bench):.2f}%"
                cells.append(
                    f"<tr><td>{_esc(r['label'])}</td>"
                    f"<td class='n'>{float(r['value']):.2f}%</td>"
                    f"<td class='n'>{bench_cell}</td></tr>"
                )
            trs = "".join(cells)
            body = ("<table><thead><tr><th></th><th class='n'>Value</th>"
                    f"<th class='n'>Benchmark</th></tr></thead><tbody>{trs}</tbody></table>")

    elif t == "performance_line":
        parts = "".join(
            f'<div class="series"><span>{_esc(s["label"])}</span>'
            + "".join(f'<b>{p["value"]:.2f}%</b>' for p in s.get("points", []))
            + "</div>" for s in d.get("series", []))
        body = f'<div class="lines">{parts}</div>'

    elif t == "risk_card":
        body = f'<div class="risk"><span>Risk level</span><b>{_esc(d.get("risk_level"))}</b></div>'

    elif t == "narrative":
        body = f"<p>{_esc(d.get('text', ''))}</p>"

    elif t == "callout":
        body = f'<div class="callout {_esc(d.get("tone", "info"))}">{_esc(d.get("text", ""))}</div>'


    elif t in ("top_contributors", "top_detractors"):
        rows = d.get("rows", [])
        span = max([abs(float(r["contribution_pct"])) for r in rows] or [1]) or 1
        cls = "neg" if t == "top_detractors" else "pos"
        trs = "".join(
            f"<tr><td>{_esc(r['name'])} <em>{_esc(r['symbol'])}</em></td>"
            f"<td class='n'>{float(r['contribution_pct']):+.2f}%</td>"
            f"<td class='bar'><i class='{cls}' "
            f"style=\"width:{abs(float(r['contribution_pct']))/span*100:.0f}%\"></i></td>"
            "</tr>" for r in rows)
        if d.get("others_pct"):
            trs += (f"<tr><td>Others</td><td class='n'>{d['others_pct']:+.2f}%</td>"
                    "<td class='bar'></td></tr>")
        trs += (f"<tr class='tot'><td>Total</td>"
                f"<td class='n'>{d.get('total_pct', 0.0):+.2f}%</td>"
                "<td class='bar'></td></tr>")
        body = ("<table><thead><tr><th>Holding</th><th class='n'>Contribution</th>"
                f"<th class='bar'>Impact</th></tr></thead><tbody>{trs}</tbody></table>")

    elif t == "allocation_vs_target":
        rows = d.get("rows", [])
        span = max([max(float(r["value"]), float(r["benchmark_value"]))
                    for r in rows] or [1]) or 1
        parts = []
        for r in rows:
            drift = float(r.get("drift_pct", 0.0))
            tone = "over" if drift > 0 else ("under" if drift < 0 else "")
            parts.append(
                f'<div class="vs"><span>{_esc(r["label"])}</span>'
                f'<div class="tracks">'
                f'<i style="width:{float(r["value"])/span*100:.0f}%"></i>'
                f'<i class="bm" style="width:{float(r["benchmark_value"])/span*100:.0f}%"></i>'
                f'</div><b>{float(r["value"]):.1f}%</b>'
                f'<u class="{tone}">{drift:+.1f}</u></div>')
        body = ('<div class="vslist">' + "".join(parts) +
                '</div><div class="lgd"><i></i>Actual <i class="bm"></i>Target '
                '&middot; last column is drift from target</div>')

    elif t == "returns_table":
        trs = "".join(
            f"<tr{' class=tot' if r.get('emphasis') else ''}>"
            f"<td>{_esc(r['label'])}</td>"
            f"<td class='n'>{float(r['value']):+.2f}%</td>"
            f"<td class='n'>{float(r['benchmark_value']):+.2f}%</td>"
            f"<td class='n {'up' if float(r.get('excess_pct', 0)) >= 0 else 'dn'}'>"
            f"{float(r.get('excess_pct', 0)):+.2f}%</td></tr>"
            for r in d.get("rows", []))
        body = ("<table><thead><tr><th>Period</th><th class='n'>Portfolio</th>"
                "<th class='n'>Benchmark</th><th class='n'>Difference</th>"
                f"</tr></thead><tbody>{trs}</tbody></table>")

    elif t == "key_takeaways":
        cards = "".join(
            f'<div class="take {_esc(i.get("tone", "info"))}">'
            f'<b>{_esc(i.get("title", ""))}</b>'
            f'<p>{_esc(i.get("text", ""))}</p></div>'
            for i in d.get("items", []))
        body = f'<div class="takes">{cards}</div>'

    elif t == "explainer":
        items = "".join(f"<dt>{_esc(i.get('term', ''))}</dt>"
                        f"<dd>{_esc(i.get('text', ''))}</dd>"
                        for i in d.get("items", []))
        body = f'<dl class="expl">{items}</dl>'

    elif t == "disclosures":
        body = (f'<div class="disc"><p>{_esc(d.get("text", ""))}</p>'
                f'<p class="src">{_esc(d.get("source", ""))}</p></div>')

    else:
        return ""

    return f'<section data-block-id="{_esc(b["block_id"])}">{head}{body}</section>'


# Blocks that read as running commentary rather than a numbered section of
# the document. Numbering these would make the report look like a form.
UNNUMBERED = {"narrative", "callout", "disclosures", "explainer", "kpi_grid"}


def doc_css() -> str:
    """The document stylesheet, shared by the advisor preview, the client
    viewer and the print/PDF path — one look everywhere, by construction."""
    return DOC_CSS


DOC_CSS = """ body{font-family:"Segoe UI",system-ui,Arial,sans-serif;color:#0f172a;margin:0;
   background:#f8fafc;font-size:14px;line-height:1.5}
 .doc{max-width:760px;margin:0 auto;background:#fff;padding:32px 40px;
   min-height:100vh;box-shadow:0 0 24px rgba(15,23,42,.06)}
 .hd{border-bottom:2px solid #0f172a;padding-bottom:14px;margin-bottom:22px}
 .hd h1{margin:0 0 4px;font-size:20px} .hd .m{color:#64748b;font-size:12.5px}
 .badge{display:inline-block;background:#eff6ff;color:#1d4ed8;font-size:11px;
   font-weight:700;padding:2px 8px;border-radius:4px;margin-left:8px}
 section{margin-bottom:22px} h3{font-size:14px;margin:0 0 8px}
 .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
 .kpi{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:9px 11px}
 .kpi span{display:block;font-size:10.5px;text-transform:uppercase;
   letter-spacing:.05em;color:#94a3b8}
 .kpi b{font-size:16px}
 .alloc,.cmp>div{display:flex;align-items:center;gap:9px;margin-bottom:6px;font-size:12.5px}
 .alloc span,.cmp span{width:130px;color:#334155}
 .alloc i,.cmp i{height:9px;background:#3b82f6;border-radius:3px;display:block}
 .cmp i.bm{background:#94a3b8}
 .alloc b,.cmp b{margin-left:auto;font-variant-numeric:tabular-nums}
 table{width:100%;border-collapse:collapse;font-size:12.5px}
 th{text-align:left;font-size:10.5px;text-transform:uppercase;color:#94a3b8;
   border-bottom:1.5px solid #cbd5e1;padding:0 8px 5px 0}
 td{padding:6px 8px 6px 0;border-bottom:1px solid #e2e8f0}
 td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
 tr.tot td{font-weight:700;border-top:1.5px solid #cbd5e1}
 .callout{padding:10px 14px;border-radius:6px;background:#eff6ff;
   border-left:3px solid #1d4ed8;font-size:13px}
 .callout.positive{background:#ecfdf5;border-color:#047857}
 .risk,.series{display:flex;gap:10px;font-size:12.5px;align-items:baseline}
 .risk span,.series span{width:130px;color:#334155}
 .series b{margin-right:14px;font-variant-numeric:tabular-nums}
 .num{color:#94a3b8;font-weight:600}
 .sub{color:#94a3b8;font-size:11.5px;margin:-4px 0 8px}
 td em{color:#94a3b8;font-style:normal;font-size:11px;margin-left:4px}
 td.bar,th.bar{width:90px}
 td.bar i{display:block;height:8px;border-radius:3px;background:#059669}
 td.bar i.neg{background:#dc2626}
 td.n.up{color:#047857} td.n.dn{color:#b91c1c}
 .vs{display:flex;align-items:center;gap:9px;margin-bottom:7px;font-size:12.5px}
 .vs span{width:118px;color:#334155}
 .vs .tracks{flex:1;display:flex;flex-direction:column;gap:2px}
 .vs .tracks i{height:7px;border-radius:3px;background:#3b82f6;display:block}
 .vs .tracks i.bm{background:#cbd5e1}
 .vs b{width:52px;text-align:right;font-variant-numeric:tabular-nums}
 .vs u{width:46px;text-align:right;text-decoration:none;font-size:11.5px;color:#94a3b8}
 .vs u.over{color:#b45309} .vs u.under{color:#0369a1}
 .lgd{font-size:11px;color:#94a3b8;margin-top:8px;display:flex;align-items:center;gap:5px}
 .lgd i{width:10px;height:7px;border-radius:2px;background:#3b82f6;display:inline-block}
 .lgd i.bm{background:#cbd5e1;margin-left:8px}
 .takes{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
 .take{border:1px solid #e2e8f0;border-left:3px solid #3b82f6;border-radius:6px;
   padding:10px 13px;background:#fbfdff}
 .take.positive{border-left-color:#047857;background:#f6fffb}
 .take.caution{border-left-color:#b45309;background:#fffcf5}
 .take b{display:block;font-size:12.5px;margin-bottom:3px}
 .take p{margin:0;font-size:12px;color:#475569;line-height:1.5}
 .expl{margin:0;font-size:12px}
 .expl dt{font-weight:700;margin-top:8px;color:#0f172a}
 .expl dd{margin:2px 0 0;color:#475569;line-height:1.5}
 .disc{border-top:1px solid #e2e8f0;padding-top:12px;font-size:11px;color:#94a3b8}
 .disc p{margin:0 0 4px} .disc .src{color:#cbd5e1}
 section[data-block-id]:hover{outline:2px solid #dbeafe;outline-offset:6px;border-radius:4px}"""


def render_body(report: Dict[str, Any], internal: bool = True) -> str:
    """The document itself: header + blocks, no <html> wrapper.

    internal=True is the ADVISOR's view and shows the control-plane detail —
    which template arm, which report id. The CLIENT's view (internal=False)
    hides all of it: templates are the advisor's machinery, and a client
    should see a report, not the mechanism that shaped it.
    """
    rendered, n = [], 0
    for b in report["blocks"]:
        if b.get("title") and b["type"] not in UNNUMBERED:
            n += 1
            rendered.append(_render_block(b, n))
        else:
            rendered.append(_render_block(b))
    blocks = "\n".join(rendered)

    badge = (f'<span class="badge">{_esc(report.get("template_label") or "")}</span>'
             if internal and report.get("template_label") else "")
    meta_bits = [_esc(str(report.get("report_type", "")).replace("_", " ").title()),
                 _esc(report.get("period", ""))]
    if internal:
        meta_bits.append(_esc(report.get("report_id", "")))
    meta = " &middot; ".join(x for x in meta_bits if x)

    return (f'<div class="doc">\n<div class="hd">\n'
            f'  <h1>{_esc(report["client_name"])}{badge}</h1>\n'
            f'  <div class="m">{meta}</div>\n'
            f'</div>\n{blocks}\n</div>')


def render_html(report: Dict[str, Any], internal: bool = True) -> str:
    return (f'<!doctype html><html><head><meta charset="utf-8">\n'
            f'<title>{_esc(report["client_name"])} — {_esc(report["period"])}</title>\n'
            f'<style>\n{DOC_CSS}\n</style></head><body>'
            f'{render_body(report, internal)}</body></html>'
            )
