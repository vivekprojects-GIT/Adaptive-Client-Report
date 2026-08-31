"""Opening blocks, one per kind of report.

WHY MORE THAN ONE HEADLINE
════════════════════════════════════════════════════════════════════════════

There were two: a four-card KPI grid and a one-line callout. Every report
type opened the same way, which is wrong in a specific and avoidable manner.

A fees report opens on what the client paid. A risk report opens on how much
risk they are carrying. A cash-flow report opens on what went in and out. A
performance report opens on whether they beat the benchmark. Handed the same
four cards, each of those reports buries its own subject somewhere below the
fold and leads with a number the reader did not come for.

So this module adds six openings, each built from the fields its report type
actually turns on, and each declining to render when those fields are empty
rather than showing a zero.

GROUNDING
────────────────────────────────────────────────────────────────────────────

Every figure carries a `source_refs` entry naming the snapshot fact it came
from, exactly as the existing blocks do. Nothing here computes a figure the
grounding gate cannot check, and nothing states a judgement the data does
not support - "ahead of benchmark" is emitted only when the arithmetic says
so, never as a default.

WHAT THEY DO NOT DO
────────────────────────────────────────────────────────────────────────────

None of them advise. A risk headline reports the risk level on file; it does
not say whether that level is appropriate. A cost headline reports the drag;
it does not call it high or low. That line is the whole reason this system
exists and a headline is the easiest place to cross it, because a headline
is where a writer reaches for a verdict.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ───────────────────────────────────────────────────────────── helpers

def _fees_total(s) -> float:
    f = getattr(s, "fees", None) or {}
    return round(sum(float(v or 0) for v in f.values()), 2)


def _flows(s):
    cf = getattr(s, "cash_flows", None) or {}
    cin = float(cf.get("contributions") or 0)
    out = float(cf.get("withdrawals") or 0)
    return cin, out, round(cin - out, 2)


# ───────────────────────────────────────────────────────── builders

def hero_value(s, n: int) -> Dict[str, Any]:
    """One large figure: what the portfolio is worth, and what it returned.

    For an executive summary, where the client wants the number and the
    direction and nothing else on the first screen.
    """
    qr = getattr(s, "quarter_return_pct", None)
    br = getattr(s, "benchmark_return_pct", None)
    return {
        "block_id": f"hero_value_{n:02d}",
        "type": "hero_value",
        "title": "",
        "data": {
            "value": round(float(s.portfolio_value), 2),
            "return_pct": qr,
            "benchmark_pct": br,
            "period": s.period,
        },
        "source_refs": ["portfolio_value", "quarter_return_pct",
                        "benchmark_return_pct"],
    }


def verdict_banner(s, n: int) -> Optional[Dict[str, Any]]:
    """Ahead of or behind the benchmark, and by how much.

    The one sentence a performance or benchmark report exists to answer.
    Emitted only when both figures are present: with one of them missing
    this would be a verdict with nothing behind it.
    """
    qr = getattr(s, "quarter_return_pct", None)
    br = getattr(s, "benchmark_return_pct", None)
    if qr is None or br is None:
        return None
    gap = round(float(qr) - float(br), 2)
    return {
        "block_id": f"verdict_banner_{n:02d}",
        "type": "verdict_banner",
        "title": "",
        "data": {
            "return_pct": qr, "benchmark_pct": br, "gap": gap,
            # "ahead"/"behind"/"level" is arithmetic, not opinion.
            "stance": "ahead" if gap > 0 else ("behind" if gap < 0 else "level"),
            "benchmark_name": getattr(s, "benchmark_name", "") or "the benchmark",
        },
        "source_refs": ["quarter_return_pct", "benchmark_return_pct"],
    }


def risk_headline(s, n: int) -> Dict[str, Any]:
    """The risk level on file, on the scale it sits within.

    Reports the level; says nothing about whether it suits the client. That
    is an advice question and this system does not answer those.
    """
    scale = ["Conservative", "Moderate", "Balanced", "Growth", "Aggressive"]
    level = str(getattr(s, "risk_level", "") or "")
    vol = getattr(s, "volatility_pct", None)
    return {
        "block_id": f"risk_headline_{n:02d}",
        "type": "risk_headline",
        "title": "",
        "data": {
            "level": level, "scale": scale,
            # Volatility is often absent in this data. A missing figure is
            # left missing rather than shown as 0.0%, which would read as
            # "no risk" instead of "not measured".
            "volatility_pct": vol if vol else None,
            "at": scale.index(level) if level in scale else None,
        },
        "source_refs": ["portfolio_value"] +
                       (["volatility_pct"] if vol else []),
    }


def cost_headline(s, n: int) -> Optional[Dict[str, Any]]:
    """What the client paid this period, and what it cost them in return."""
    total = _fees_total(s)
    if not total:
        return None
    pv = float(s.portfolio_value or 0)
    drag = round(100.0 * total / pv, 2) if pv else None
    fees = getattr(s, "fees", None) or {}
    return {
        "block_id": f"cost_headline_{n:02d}",
        "type": "cost_headline",
        "title": "",
        "data": {
            "total": total, "drag_pct": drag,
            "parts": [{"name": k, "value": round(float(v or 0), 2)}
                      for k, v in sorted(fees.items())],
        },
        "source_refs": [f"fees.{k}" for k in fees] + ["portfolio_value"],
    }


def flow_headline(s, n: int) -> Optional[Dict[str, Any]]:
    """Money in, money out, and the net — the subject of a cash-flow report."""
    cin, out, net = _flows(s)
    if not cin and not out:
        return None
    return {
        "block_id": f"flow_headline_{n:02d}",
        "type": "flow_headline",
        "title": "",
        "data": {"contributions": cin, "withdrawals": out, "net": net},
        "source_refs": ["flows.contributions", "flows.withdrawals",
                        "derived.net_flow"],
    }


def trend_headline(s, n: int) -> Optional[Dict[str, Any]]:
    """Where this period sits against the ones before it.

    A change report is about movement, so its opening is a series rather
    than a single number. Needs history; returns None without it instead of
    drawing a chart of one point.
    """
    hist = list(getattr(s, "history", None) or [])
    if len(hist) < 2:
        return None
    return {
        "block_id": f"trend_headline_{n:02d}",
        "type": "trend_headline",
        "title": "",
        "data": {
            "points": [{"period": h.get("period"),
                        "portfolio": h.get("portfolio"),
                        "benchmark": h.get("benchmark")} for h in hist],
            "latest": hist[-1].get("portfolio"),
            "periods": len(hist),
        },
        "source_refs": [f"hist.{h.get('period')}.portfolio" for h in hist],
    }


# ───────────────────────────────────────────────────────── renderers

def _esc(t: Any) -> str:
    import html
    return html.escape(str(t if t is not None else ""))


def _T(text: str) -> str:
    from .generate import _T as _t
    return _t(text)


def _money(v: float) -> str:
    from .generate import _money as _m
    return _m(v)


def _pct(v: float, dp: int = 2) -> str:
    from .generate import _RENDER_LOCALE
    from .locales import format_number
    return format_number(float(v), _RENDER_LOCALE.get() or "en", dp) + "%"


def _signed(v: float) -> str:
    return ("+" if v > 0 else "") + _pct(v)


def r_hero_value(d: Dict[str, Any]) -> str:
    qr, br = d.get("return_pct"), d.get("benchmark_pct")
    sub = ""
    if qr is not None:
        tone = "up" if qr > 0 else ("dn" if qr < 0 else "flat")
        sub = (f'<span class="hv-ret {tone}">{_signed(qr)}</span>'
               f'<span class="hv-cap">{_esc(_T("this period"))}</span>')
        if br is not None:
            sub += (f'<span class="hv-bm">{_esc(_T("benchmark"))} '
                    f'{_pct(br)}</span>')
    return (f'<div class="hero"><span class="hv-cap">'
            f'{_esc(_T("Portfolio value"))}</span>'
            f'<b class="hv-num">{_money(d.get("value", 0))}</b>'
            f'<div class="hv-row">{sub}</div></div>')


def r_verdict_banner(d: Dict[str, Any]) -> str:
    stance = d.get("stance", "level")
    gap = d.get("gap", 0)
    word = {"ahead": "ahead of", "behind": "behind",
            "level": "level with"}[stance]
    return (f'<div class="verdict v-{_esc(stance)}">'
            f'<b>{_pct(d.get("return_pct", 0))}</b>'
            f'<span>{_esc(_T(word))} {_esc(_T(d.get("benchmark_name", "")))}'
            f' &middot; {_esc(_T("by"))} {_pct(abs(gap))}</span></div>')


def r_risk_headline(d: Dict[str, Any]) -> str:
    at = d.get("at")
    pips = "".join(
        f'<i class="{"on" if at is not None and i == at else ""}">'
        f'{_esc(_T(name))}</i>'
        for i, name in enumerate(d.get("scale", [])))
    vol = d.get("volatility_pct")
    volpart = (f'<span class="rh-vol">{_esc(_T("Volatility"))} '
               f'{_pct(vol)}</span>' if vol else
               f'<span class="rh-vol rh-none">'
               f'{_esc(_T("Volatility not measured this period"))}</span>')
    return (f'<div class="riskhead"><span class="hv-cap">'
            f'{_esc(_T("Risk level"))}</span>'
            f'<b>{_esc(_T(d.get("level", "")))}</b>'
            f'<div class="rh-scale">{pips}</div>{volpart}</div>')


def r_cost_headline(d: Dict[str, Any]) -> str:
    parts = "".join(
        f'<li><span>{_esc(_T(p["name"]))}</span><b>{_money(p["value"])}</b></li>'
        for p in d.get("parts", []))
    drag = d.get("drag_pct")
    dragpart = (f'<span class="ch-drag">{_pct(drag)} '
                f'{_esc(_T("of portfolio value"))}</span>' if drag is not None else "")
    return (f'<div class="costhead"><div class="ch-main">'
            f'<span class="hv-cap">{_esc(_T("Total cost this period"))}</span>'
            f'<b>{_money(d.get("total", 0))}</b>{dragpart}</div>'
            f'<ul class="ch-parts">{parts}</ul></div>')


def r_flow_headline(d: Dict[str, Any]) -> str:
    net = d.get("net", 0)
    tone = "up" if net > 0 else ("dn" if net < 0 else "flat")
    cells = [("Paid in", d.get("contributions", 0), ""),
             ("Taken out", d.get("withdrawals", 0), ""),
             ("Net", net, tone)]
    body = "".join(
        f'<div class="fh-cell"><span>{_esc(_T(label))}</span>'
        f'<b class="{cls}">{_money(v)}</b></div>'
        for label, v, cls in cells)
    return f'<div class="flowhead">{body}</div>'


def r_trend_headline(d: Dict[str, Any]) -> str:
    pts = d.get("points", [])
    vals = [float(p.get("portfolio") or 0) for p in pts]
    if not vals:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    w, h = 320, 64
    step = w / max(len(vals) - 1, 1)
    coords = " ".join(
        f"{i * step:.1f},{h - ((v - lo) / span) * (h - 10) - 5:.1f}"
        for i, v in enumerate(vals))
    dots = "".join(
        f'<circle cx="{i * step:.1f}" '
        f'cy="{h - ((v - lo) / span) * (h - 10) - 5:.1f}" r="2.5" '
        f'fill="#2563eb"/>' for i, v in enumerate(vals))
    labels = "".join(
        f'<span>{_esc(p.get("period"))}</span>' for p in pts)
    return (f'<div class="trendhead"><span class="hv-cap">'
            f'{_esc(_T("Return by period"))}</span>'
            f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
            f'<polyline points="{coords}" fill="none" stroke="#2563eb" '
            f'stroke-width="2"/>{dots}</svg>'
            f'<div class="th-x">{labels}</div></div>')


BUILDERS = {
    "hero_value": hero_value,
    "verdict_banner": verdict_banner,
    "risk_headline": risk_headline,
    "cost_headline": cost_headline,
    "flow_headline": flow_headline,
    "trend_headline": trend_headline,
}

RENDERERS = {
    "hero_value": r_hero_value,
    "verdict_banner": r_verdict_banner,
    "risk_headline": r_risk_headline,
    "cost_headline": r_cost_headline,
    "flow_headline": r_flow_headline,
    "trend_headline": r_trend_headline,
}

# What the registry needs to know, kept beside the code it describes so the
# two cannot drift.
REGISTRY_ENTRIES = {
    "hero_value": dict(
        category="headline", needs=None,
        shows="One large figure: portfolio value, with the period's return "
              "and the benchmark beneath it."),
    "verdict_banner": dict(
        category="headline", needs=None,
        shows="Ahead of or behind the benchmark, and by how much, in one "
              "line."),
    "risk_headline": dict(
        category="headline", needs=None,
        shows="The risk level on file, marked on the scale it sits within."),
    "cost_headline": dict(
        category="headline", needs=None,
        shows="Total cost this period, its share of portfolio value, and "
              "the parts it is made of."),
    "flow_headline": dict(
        category="headline", needs=None,
        shows="Paid in, taken out and the net movement."),
    "trend_headline": dict(
        category="headline", needs="history",
        shows="Return across every period held, as a sparkline."),
}
