"""Inline-SVG renderers for every registered chart kind.

No external chart library and no client-side JS: a report has to render
identically in the browser, in an emailed HTML body, and in a headless
Chromium PDF pass. Anything requiring a runtime would render in the first
and silently break in the other two.

Every renderer takes the block's `data` dict and returns an SVG string.
Kinds are grouped by the DATA SHAPE they need — that shape is what the
generator must supply and what the validator checks:

    categorical   x_categories + series[{label, values}]
    parts         items[{label, value}]
    delta         items[{label, value}]     (values are deltas)
    xy / xyz      series[{label, values:[[x,y]] }]
    single        value (+ optional min/max)
    matrix        x_labels + y_labels + matrix[[...]]

An unknown kind renders a visible placeholder rather than nothing, so a
mis-specified chart is obvious in review instead of leaving a silent gap.
"""

from __future__ import annotations

import html
import math
from typing import Any, Dict, List, Sequence

W, H = 320.0, 150.0          # viewBox; CSS scales it to the column
PAD_L, PAD_R, PAD_T, PAD_B = 34.0, 8.0, 12.0, 22.0

PALETTE = ["#3b82f6", "#0f766e", "#6d28d9", "#b45309", "#be185d",
           "#0891b2", "#4d7c0f", "#9333ea"]
GRID = "#e2e8f0"
AXIS = "#94a3b8"
INK = "#0f172a"


def _e(v: Any) -> str:
    return html.escape(str(v))


def _plot() -> tuple:
    return PAD_L, PAD_T, W - PAD_L - PAD_R, H - PAD_T - PAD_B


def _svg(body: str) -> str:
    return (f'<svg viewBox="0 0 {W:.0f} {H:.0f}" class="cw" '
            f'xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, sans-serif">'
            f'{body}</svg>')


def _nums(vals: Sequence[Any]) -> List[float]:
    out = []
    for v in vals:
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            out.append(0.0)
    return out


def _series(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    s = d.get("series") or []
    if s:
        return [{"label": x.get("label", ""), "values": _nums(x.get("values") or [])}
                for x in s]
    # A single unlabelled series may be given as items[] — accept it rather
    # than rejecting a chart that is otherwise well formed.
    items = d.get("items") or []
    return [{"label": "", "values": _nums([i.get("value") for i in items])}] if items else []


def _cats(d: Dict[str, Any]) -> List[str]:
    c = d.get("x_categories")
    if c:
        return [str(x) for x in c]
    return [str(i.get("label", "")) for i in (d.get("items") or [])]


def _axes(maxv: float, minv: float = 0.0) -> str:
    x0, y0, w, h = _plot()
    parts = [f'<line x1="{x0}" y1="{y0+h}" x2="{x0+w}" y2="{y0+h}" '
             f'stroke="{AXIS}" stroke-width="1"/>']
    span = (maxv - minv) or 1.0
    for i in range(3):
        v = minv + span * i / 2.0
        y = y0 + h - (v - minv) / span * h
        parts.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+w}" y2="{y:.1f}" '
                     f'stroke="{GRID}" stroke-width="1"/>')
        parts.append(f'<text x="{x0-4}" y="{y+3:.1f}" font-size="7" fill="{AXIS}" '
                     f'text-anchor="end">{v:.1f}</text>')
    return "".join(parts)


def _cat_labels(cats: List[str]) -> str:
    x0, y0, w, h = _plot()
    if not cats:
        return ""
    step = w / len(cats)
    out = []
    for i, c in enumerate(cats):
        label = c if len(c) <= 9 else c[:8] + "…"
        out.append(f'<text x="{x0 + step*(i+0.5):.1f}" y="{y0+h+11:.1f}" font-size="7" '
                   f'fill="{AXIS}" text-anchor="middle">{_e(label)}</text>')
    return "".join(out)


# ---------------------------------------------------------------------------
# categorical
# ---------------------------------------------------------------------------

def _bar(d, horizontal=False, contiguous=False):
    cats, series = _cats(d), _series(d)
    if not series:
        return _empty("no series")
    vals = series[0]["values"]
    x0, y0, w, h = _plot()
    hi, lo = max(vals + [0.0]), min(vals + [0.0])
    span = (hi - lo) or 1.0

    if horizontal:
        step = h / max(len(vals), 1)
        bh = step * 0.62
        bars = []
        for i, v in enumerate(vals):
            bw = abs(v) / span * w
            y = y0 + step * i + (step - bh) / 2
            bx = x0 if v >= 0 else x0 - bw
            bars.append(f'<rect x="{bx:.1f}" y="{y:.1f}" width="{bw:.1f}" '
                        f'height="{bh:.1f}" rx="2" fill="{PALETTE[0]}"/>')
            bars.append(f'<text x="{bx+bw+3:.1f}" y="{y+bh/2+2.5:.1f}" font-size="7" '
                        f'fill="{INK}">{v:g}</text>')
            lab = cats[i] if i < len(cats) else ""
            bars.append(f'<text x="{x0-4}" y="{y+bh/2+2.5:.1f}" font-size="7" '
                        f'fill="{AXIS}" text-anchor="end">{_e(lab[:11])}</text>')
        return _svg("".join(bars))

    step = w / max(len(vals), 1)
    bw = step * (0.98 if contiguous else 0.6)
    zero = y0 + h - (0 - lo) / span * h
    bars = [_axes(hi, lo), _cat_labels(cats)]
    for i, v in enumerate(vals):
        bh = abs(v) / span * h
        y = zero - bh if v >= 0 else zero
        bars.append(f'<rect x="{x0 + step*i + (step-bw)/2:.1f}" y="{y:.1f}" '
                    f'width="{bw:.1f}" height="{max(bh,1):.1f}" '
                    f'rx="{0 if contiguous else 2}" fill="{PALETTE[0]}"/>')
    return _svg("".join(bars))


def _line(d, area=False):
    cats, series = _cats(d), _series(d)
    if not series:
        return _empty("no series")
    x0, y0, w, h = _plot()
    allv = [v for s in series for v in s["values"]] or [0.0]
    hi, lo = max(allv), min(allv + [0.0])
    span = (hi - lo) or 1.0
    parts = [_axes(hi, lo), _cat_labels(cats)]
    for si, s in enumerate(series):
        vals = s["values"]
        if not vals:
            continue
        step = w / max(len(vals) - 1, 1)
        pts = [(x0 + step * i, y0 + h - (v - lo) / span * h) for i, v in enumerate(vals)]
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        col = PALETTE[si % len(PALETTE)]
        if area:
            parts.append(f'<polygon points="{x0:.1f},{y0+h:.1f} {path} '
                         f'{pts[-1][0]:.1f},{y0+h:.1f}" fill="{col}" fill-opacity=".18"/>')
        parts.append(f'<polyline points="{path}" fill="none" stroke="{col}" '
                     f'stroke-width="1.8" stroke-linejoin="round"/>')
        for x, y in pts:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.9" fill="{col}"/>')
    return _svg("".join(parts) + _legend(series))


def _stacked(d):
    cats, series = _cats(d), _series(d)
    if not series:
        return _empty("no series")
    x0, y0, w, h = _plot()
    n = max(len(s["values"]) for s in series)
    totals = [sum(s["values"][i] if i < len(s["values"]) else 0 for s in series)
              for i in range(n)]
    hi = max(totals + [1.0])
    step = w / max(n, 1)
    bw = step * 0.6
    parts = [_axes(hi), _cat_labels(cats)]
    for i in range(n):
        acc = 0.0
        for si, s in enumerate(series):
            v = s["values"][i] if i < len(s["values"]) else 0.0
            bh = v / hi * h
            y = y0 + h - (acc + v) / hi * h
            parts.append(f'<rect x="{x0+step*i+(step-bw)/2:.1f}" y="{y:.1f}" '
                         f'width="{bw:.1f}" height="{max(bh,0.5):.1f}" '
                         f'fill="{PALETTE[si % len(PALETTE)]}"/>')
            acc += v
    return _svg("".join(parts) + _legend(series))


def _combo(d):
    series = _series(d)
    if len(series) < 2:
        return _bar(d)
    cats = _cats(d)
    x0, y0, w, h = _plot()
    allv = [v for s in series for v in s["values"]] or [0.0]
    hi = max(allv + [1.0])
    bars, line = series[0]["values"], series[1]["values"]
    step = w / max(len(bars), 1)
    bw = step * 0.55
    parts = [_axes(hi), _cat_labels(cats)]
    for i, v in enumerate(bars):
        bh = v / hi * h
        parts.append(f'<rect x="{x0+step*i+(step-bw)/2:.1f}" y="{y0+h-bh:.1f}" '
                     f'width="{bw:.1f}" height="{max(bh,1):.1f}" rx="2" fill="{PALETTE[0]}"/>')
    pts = " ".join(f"{x0+step*(i+0.5):.1f},{y0+h-v/hi*h:.1f}" for i, v in enumerate(line))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{PALETTE[2]}" stroke-width="1.8"/>')
    return _svg("".join(parts) + _legend(series))


# ---------------------------------------------------------------------------
# part-to-whole
# ---------------------------------------------------------------------------

def _arc(cx, cy, r, a0, a1, inner=0.0):
    x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    large = 1 if (a1 - a0) > math.pi else 0
    if inner <= 0:
        return f"M{cx:.1f},{cy:.1f} L{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 {large} 1 {x1:.1f},{y1:.1f} Z"
    ix0, iy0 = cx + inner * math.cos(a1), cy + inner * math.sin(a1)
    ix1, iy1 = cx + inner * math.cos(a0), cy + inner * math.sin(a0)
    return (f"M{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 {large} 1 {x1:.1f},{y1:.1f} "
            f"L{ix0:.1f},{iy0:.1f} A{inner:.1f},{inner:.1f} 0 {large} 0 {ix1:.1f},{iy1:.1f} Z")


def _pie(d, donut=False):
    items = d.get("items") or []
    if not items:
        s = _series(d)
        cats = _cats(d)
        if s:
            items = [{"label": cats[i] if i < len(cats) else "",
                      "value": v} for i, v in enumerate(s[0]["values"])]
    vals = _nums([i.get("value") for i in items])
    total = sum(abs(v) for v in vals)
    if total <= 0:
        return _empty("no values")
    cx, cy, r = 62.0, H / 2, 50.0
    a = -math.pi / 2
    parts = []
    for i, v in enumerate(vals):
        sweep = abs(v) / total * 2 * math.pi
        parts.append(f'<path d="{_arc(cx, cy, r, a, a+sweep, r*0.58 if donut else 0)}" '
                     f'fill="{PALETTE[i % len(PALETTE)]}"/>')
        a += sweep
    for i, it in enumerate(items[:6]):
        y = 20 + i * 15
        pct = abs(vals[i]) / total * 100
        parts.append(f'<rect x="128" y="{y-6}" width="7" height="7" rx="1.5" '
                     f'fill="{PALETTE[i % len(PALETTE)]}"/>')
        parts.append(f'<text x="140" y="{y}" font-size="8" fill="{INK}">'
                     f'{_e(str(it.get("label",""))[:16])}</text>')
        parts.append(f'<text x="{W-PAD_R}" y="{y}" font-size="8" fill="{AXIS}" '
                     f'text-anchor="end">{pct:.1f}%</text>')
    return _svg("".join(parts))


def _funnel(d):
    items = d.get("items") or []
    vals = _nums([i.get("value") for i in items])
    if not vals:
        return _empty("no values")
    hi = max(vals) or 1.0
    x0, y0, w, h = _plot()
    step = h / len(vals)
    parts = []
    for i, v in enumerate(vals):
        top = abs(v) / hi * w * 0.72
        nxt = abs(vals[i + 1]) / hi * w * 0.72 if i + 1 < len(vals) else top * 0.72
        cx = x0 + w * 0.42
        y = y0 + step * i
        parts.append(f'<polygon points="{cx-top/2:.1f},{y:.1f} {cx+top/2:.1f},{y:.1f} '
                     f'{cx+nxt/2:.1f},{y+step*0.82:.1f} {cx-nxt/2:.1f},{y+step*0.82:.1f}" '
                     f'fill="{PALETTE[i % len(PALETTE)]}" fill-opacity=".85"/>')
        parts.append(f'<text x="{x0+w*0.88:.1f}" y="{y+step*0.5:.1f}" font-size="7.5" '
                     f'fill="{INK}">{_e(str(items[i].get("label",""))[:12])} {v:g}</text>')
    return _svg("".join(parts))


def _treemap(d):
    items = d.get("items") or []
    vals = _nums([i.get("value") for i in items])
    total = sum(abs(v) for v in vals)
    if total <= 0:
        return _empty("no values")
    x0, y0, w, h = _plot()
    parts, x, row_y, row_h = [], x0, y0, h
    # Simple slice-and-dice: adequate for the 4-6 categories a report shows.
    for i, v in enumerate(vals):
        cw = abs(v) / total * w
        parts.append(f'<rect x="{x:.1f}" y="{row_y:.1f}" width="{max(cw-1.5,1):.1f}" '
                     f'height="{row_h:.1f}" rx="2" fill="{PALETTE[i % len(PALETTE)]}" '
                     f'fill-opacity=".88"/>')
        if cw > 34:
            parts.append(f'<text x="{x+4:.1f}" y="{row_y+13:.1f}" font-size="7.5" '
                         f'fill="#fff">{_e(str(items[i].get("label",""))[:10])}</text>')
            parts.append(f'<text x="{x+4:.1f}" y="{row_y+24:.1f}" font-size="8" '
                         f'fill="#fff" font-weight="700">{v:g}</text>')
        x += cw
    return _svg("".join(parts))


# ---------------------------------------------------------------------------
# delta / relationship / single / matrix
# ---------------------------------------------------------------------------

def _waterfall(d):
    items = d.get("items") or []
    vals = _nums([i.get("value") for i in items])
    if not vals:
        return _empty("no values")
    run, tops = 0.0, []
    for v in vals:
        tops.append((run, run + v))
        run += v
    hi = max([t[1] for t in tops] + [t[0] for t in tops] + [0.0])
    lo = min([t[1] for t in tops] + [t[0] for t in tops] + [0.0])
    span = (hi - lo) or 1.0
    x0, y0, w, h = _plot()
    step = w / max(len(vals), 1)
    bw = step * 0.6
    parts = [_axes(hi, lo), _cat_labels([str(i.get("label", "")) for i in items])]
    for i, (a, b) in enumerate(tops):
        top, bot = max(a, b), min(a, b)
        y = y0 + h - (top - lo) / span * h
        bh = (top - bot) / span * h
        col = "#047857" if vals[i] >= 0 else "#b91c1c"
        parts.append(f'<rect x="{x0+step*i+(step-bw)/2:.1f}" y="{y:.1f}" width="{bw:.1f}" '
                     f'height="{max(bh,1):.1f}" rx="1.5" fill="{col}" fill-opacity=".85"/>')
    return _svg("".join(parts))


def _scatter(d, bubble=False):
    series = d.get("series") or []
    pts = []
    for si, s in enumerate(series):
        for p in (s.get("values") or []):
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                pts.append((float(p[0]), float(p[1]),
                            float(p[2]) if bubble and len(p) > 2 else 3.0, si))
    if not pts:
        return _empty("no points")
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, y0, w, h = _plot()
    xr = (max(xs) - min(xs)) or 1.0
    yr = (max(ys) - min(ys)) or 1.0
    rmax = max(p[2] for p in pts) or 1.0
    parts = [_axes(max(ys), min(ys))]
    for x, y, r, si in pts:
        cx = x0 + (x - min(xs)) / xr * w
        cy = y0 + h - (y - min(ys)) / yr * h
        rr = (2.0 + r / rmax * 7.0) if bubble else 2.6
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr:.1f}" '
                     f'fill="{PALETTE[si % len(PALETTE)]}" fill-opacity=".7"/>')
    return _svg("".join(parts))


def _gauge(d, bar=False):
    v = float(d.get("value", 0) or 0)
    lo = float(d.get("min", 0) or 0)
    hi = float(d.get("max", 100) or 100)
    frac = 0.0 if hi == lo else max(0.0, min(1.0, (v - lo) / (hi - lo)))
    if bar:
        x0, y0, w, h = _plot()
        y = y0 + h / 2 - 7
        return _svg(
            f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="14" rx="7" fill="{GRID}"/>'
            f'<rect x="{x0}" y="{y}" width="{w*frac:.1f}" height="14" rx="7" fill="{PALETTE[0]}"/>'
            f'<text x="{x0+w/2:.1f}" y="{y+38:.1f}" font-size="13" font-weight="700" '
            f'fill="{INK}" text-anchor="middle">{v:g}</text>')
    cx, cy, r = W / 2, H - 34, 54.0
    a0, a1 = math.pi, math.pi + math.pi * frac
    return _svg(
        f'<path d="{_arc(cx, cy, r, math.pi, 2*math.pi, r*0.66)}" fill="{GRID}"/>'
        f'<path d="{_arc(cx, cy, r, a0, a1, r*0.66)}" fill="{PALETTE[0]}"/>'
        f'<text x="{cx}" y="{cy-6}" font-size="16" font-weight="700" fill="{INK}" '
        f'text-anchor="middle">{v:g}</text>')


def _radar(d):
    cats, series = _cats(d), _series(d)
    if not series or not cats:
        return _empty("no series")
    cx, cy, r = W / 2, H / 2, 52.0
    n = len(cats)
    hi = max([v for s in series for v in s["values"]] + [1.0])
    parts = []
    for ring in (0.34, 0.67, 1.0):
        pts = " ".join(
            f"{cx + r*ring*math.cos(-math.pi/2 + 2*math.pi*i/n):.1f},"
            f"{cy + r*ring*math.sin(-math.pi/2 + 2*math.pi*i/n):.1f}" for i in range(n))
        parts.append(f'<polygon points="{pts}" fill="none" stroke="{GRID}" stroke-width="1"/>')
    for si, s in enumerate(series):
        pts = " ".join(
            f"{cx + r*(s['values'][i]/hi if i < len(s['values']) else 0)*math.cos(-math.pi/2 + 2*math.pi*i/n):.1f},"
            f"{cy + r*(s['values'][i]/hi if i < len(s['values']) else 0)*math.sin(-math.pi/2 + 2*math.pi*i/n):.1f}"
            for i in range(n))
        col = PALETTE[si % len(PALETTE)]
        parts.append(f'<polygon points="{pts}" fill="{col}" fill-opacity=".22" '
                     f'stroke="{col}" stroke-width="1.6"/>')
    for i, c in enumerate(cats):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        parts.append(f'<text x="{cx + (r+9)*math.cos(ang):.1f}" '
                     f'y="{cy + (r+9)*math.sin(ang)+2.5:.1f}" font-size="6.5" '
                     f'fill="{AXIS}" text-anchor="middle">{_e(c[:8])}</text>')
    return _svg("".join(parts))


def _heatmap(d):
    xs = [str(x) for x in (d.get("x_labels") or [])]
    ys = [str(y) for y in (d.get("y_labels") or [])]
    m = d.get("matrix") or []
    if not m or not xs or not ys:
        return _empty("needs x_labels, y_labels, matrix")
    flat = [float(v) for row in m for v in row] or [0.0]
    hi, lo = max(flat), min(flat)
    span = (hi - lo) or 1.0
    x0, y0, w, h = _plot()
    cw, ch = w / len(xs), h / len(ys)
    parts = []
    for r, row in enumerate(m):
        for c, v in enumerate(row):
            t = (float(v) - lo) / span
            parts.append(f'<rect x="{x0+c*cw:.1f}" y="{y0+r*ch:.1f}" '
                         f'width="{cw-1:.1f}" height="{ch-1:.1f}" rx="1.5" '
                         f'fill="{PALETTE[0]}" fill-opacity="{0.12 + t*0.85:.2f}"/>')
        parts.append(f'<text x="{x0-4}" y="{y0+r*ch+ch/2+2.5:.1f}" font-size="6.5" '
                     f'fill="{AXIS}" text-anchor="end">{_e(ys[r][:9])}</text>')
    parts.append(_cat_labels(xs))
    return _svg("".join(parts))


def _legend(series) -> str:
    labelled = [s for s in series if s.get("label")]
    if len(labelled) < 2:
        return ""
    out = []
    for i, s in enumerate(labelled[:4]):
        x = PAD_L + i * 74
        out.append(f'<rect x="{x}" y="1" width="7" height="7" rx="1.5" '
                   f'fill="{PALETTE[i % len(PALETTE)]}"/>')
        out.append(f'<text x="{x+11}" y="7.5" font-size="7" fill="{AXIS}">'
                   f'{_e(s["label"][:14])}</text>')
    return "".join(out)


def _empty(msg: str) -> str:
    return _svg(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="4" fill="#f8fafc" '
                f'stroke="{GRID}" stroke-dasharray="4 3"/>'
                f'<text x="{W/2}" y="{H/2+3}" font-size="9" fill="{AXIS}" '
                f'text-anchor="middle">{_e(msg)}</text>')


RENDERERS = {
    "bar":       lambda d: _bar(d),
    "hbar":      lambda d: _bar(d, horizontal=True),
    "histogram": lambda d: _bar(d, contiguous=True),
    "line":      lambda d: _line(d),
    "area":      lambda d: _line(d, area=True),
    "stacked":   _stacked,
    "combo":     _combo,
    "pie":       lambda d: _pie(d),
    "donut":     lambda d: _pie(d, donut=True),
    "funnel":    _funnel,
    "treemap":   _treemap,
    "waterfall": _waterfall,
    "scatter":   lambda d: _scatter(d),
    "bubble":    lambda d: _scatter(d, bubble=True),
    "gauge":     lambda d: _gauge(d),
    "progress":  lambda d: _gauge(d, bar=True),
    "radar":     _radar,
    "heatmap":   _heatmap,
}

KINDS = tuple(RENDERERS.keys())


def render_chart(data: Dict[str, Any]) -> str:
    """Render a `chart` block. Unknown kinds show a visible placeholder so a
    mis-specified chart is caught in review rather than leaving a gap."""
    kind = str(data.get("kind", "bar")).lower()
    fn = RENDERERS.get(kind)
    if fn is None:
        return _empty(f'unsupported chart kind "{kind}"')
    try:
        return fn(data)
    except Exception as exc:                      # never break a whole report
        return _empty(f"{kind}: {type(exc).__name__}")
