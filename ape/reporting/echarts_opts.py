"""ECharts option builders — the interactive layer over the same block data.

Every chart in a report is rendered TWICE from one `data` dict:

    charts.py        -> inline SVG      (always present, never needs JS)
    echarts_opts.py  -> an option dict  (upgraded in place when JS runs)

The SVG is the floor, not a placeholder. A report opened with scripting
blocked, saved to disk, or forwarded as a plain HTML file still shows every
chart — it simply shows the static one. Where JS does run (the client
viewer, and the headless-Chromium PDF pass) the runtime swaps in the
interactive chart: hover readouts, legend toggling, animated entry, zoom on
long series.

WHY ECHARTS AND NOT D3 OR PLOTLY
--------------------------------
D3 is a drawing toolkit, so every one of these eighteen kinds would have to
be authored twice — once in Python for the fallback, once in JS — and the
two would drift. Plotly ships ~3.5MB and its default chrome fights the
document. ECharts is declarative: one JSON-serialisable option per kind,
which is the same shape our renderer registry already has, and it carries
tooltips, legend toggling and animation without imperative code. It is
vendored locally (ape/static/vendor) rather than pulled from a CDN, so the
viewer has no third-party runtime dependency at read time.

NO FUNCTIONS IN THESE OPTIONS
-----------------------------
The option travels to the browser as JSON in a data attribute, so it cannot
carry callbacks. Anything needing one — value formatting, bubble radius —
is expressed as data here and installed by widgets.js on the other side,
via the `_ape` meta key.

FACTS ARE UNCHANGED
-------------------
These builders re-encode numbers that are already bound to the frozen
snapshot; they never compute new ones. A tooltip shows the same figure the
SVG plots and the table lists. Presentation only, exactly like every other
adaptive mechanism here.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

# ---------------------------------------------------------------------------
# Visual system
#
# Eight hues that stay distinguishable next to each other and legible on
# white, chosen to read as considered rather than as a default ramp. Gains
# and losses get their own two colours and never borrow from the series
# palette — in a financial document green/red carry meaning, so they must
# not land on an asset class by position.
# ---------------------------------------------------------------------------

PALETTE = ["#4F46E5", "#0D9488", "#F59E0B", "#E11D48",
           "#0891B2", "#7C3AED", "#65A30D", "#DB2777"]
POS, NEG = "#059669", "#DC2626"
INK, MUTED, GRID = "#0F172A", "#64748B", "#E2E8F0"

_FONT = ('"Segoe UI", system-ui, -apple-system, "Helvetica Neue", '
         'Arial, sans-serif')


def _grad(color: str, vertical: bool = True, to: float = 0.15) -> Dict[str, Any]:
    """A linear gradient from the solid colour to a faded tail of itself.

    Kept subtle on purpose: the gradient is there to give a bar or an area
    some depth, not to become the thing you notice about the chart.
    """
    x2, y2 = (0, 1) if vertical else (1, 0)
    return {"type": "linear", "x": 0, "y": 0, "x2": x2, "y2": y2,
            "colorStops": [{"offset": 0, "color": color},
                           {"offset": 1, "color": _fade(color, to)}]}


def _fade(hexcolor: str, alpha: float) -> str:
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha:.2f})"


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
        return [{"label": x.get("label", ""),
                 "values": _nums(x.get("values") or [])} for x in s]
    items = d.get("items") or []
    return ([{"label": "", "values": _nums([i.get("value") for i in items])}]
            if items else [])


def _cats(d: Dict[str, Any]) -> List[str]:
    c = d.get("x_categories")
    if c:
        return [str(x) for x in c]
    return [str(i.get("label", "")) for i in (d.get("items") or [])]


def _items(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = d.get("items") or []
    if items:
        return [{"label": str(i.get("label", "")),
                 "value": _nums([i.get("value")])[0]} for i in items]
    s, cats = _series(d), _cats(d)
    if not s:
        return []
    return [{"label": cats[i] if i < len(cats) else f"#{i + 1}", "value": v}
            for i, v in enumerate(s[0]["values"])]


# ---------------------------------------------------------------------------
# Shared option scaffolding
# ---------------------------------------------------------------------------

def _base(d: Dict[str, Any]) -> Dict[str, Any]:
    """Everything every chart shares: type, animation, and the `_ape` meta
    block the browser runtime reads to install formatters."""
    return {
        "color": PALETTE,
        "textStyle": {"fontFamily": _FONT, "color": INK, "fontSize": 11},
        "animationDuration": 620,
        "animationEasing": "cubicOut",
        "animationDelay": 0,
        # Not an ECharts key. Our runtime strips it and uses it to install
        # the value formatter, which cannot be expressed in JSON.
        "_ape": {"unit": str(d.get("unit", "") or ""),
                 "dp": int(d.get("dp", 2) or 2)},
    }


def _tooltip(trigger: str = "item", **kw) -> Dict[str, Any]:
    t = {"trigger": trigger,
         "backgroundColor": "rgba(15,23,42,.94)",
         "borderWidth": 0,
         "padding": [7, 10],
         "textStyle": {"color": "#F8FAFC", "fontSize": 11.5,
                       "fontFamily": _FONT},
         "extraCssText": "border-radius:7px;box-shadow:0 6px 18px rgba(15,23,42,.22)"}
    if trigger == "axis":
        t["axisPointer"] = {"type": "line",
                            "lineStyle": {"color": "#94A3B8", "width": 1,
                                          "type": "dashed"}}
    t.update(kw)
    return t


def _legend(labels: List[str]) -> Optional[Dict[str, Any]]:
    """Only when there is a choice to make. A legend for one series is
    furniture: it costs vertical space and toggles nothing useful."""
    named = [l for l in labels if l]
    if len(named) < 2:
        return None
    return {"data": named, "top": 0, "left": 0, "itemGap": 14,
            "itemWidth": 11, "itemHeight": 7, "icon": "roundRect",
            "textStyle": {"color": MUTED, "fontSize": 10.5,
                          "fontFamily": _FONT},
            "inactiveColor": "#CBD5E1"}


def _grid(has_legend: bool, left: int = 46) -> Dict[str, Any]:
    return {"left": left, "right": 14, "bottom": 26,
            "top": 26 if has_legend else 12, "containLabel": False}


def _cat_axis(cats: List[str]) -> Dict[str, Any]:
    return {"type": "category", "data": cats,
            "axisLine": {"lineStyle": {"color": "#CBD5E1"}},
            "axisTick": {"show": False},
            "axisLabel": {"color": MUTED, "fontSize": 10, "hideOverlap": True,
                          "fontFamily": _FONT},
            "splitLine": {"show": False}}


def _val_axis(name: str = "") -> Dict[str, Any]:
    return {"type": "value", "name": name,
            "nameTextStyle": {"color": MUTED, "fontSize": 10},
            "axisLine": {"show": False},
            "axisTick": {"show": False},
            "axisLabel": {"color": MUTED, "fontSize": 10,
                          "fontFamily": _FONT},
            "splitLine": {"lineStyle": {"color": GRID, "type": "dashed"}}}


def _zoom(n: int) -> List[Dict[str, Any]]:
    """Long series get a brush-and-drag range. Short ones do not — a zoom
    control under eight points is a control that does nothing."""
    if n <= 12:
        return []
    return [{"type": "inside", "throttle": 40},
            {"type": "slider", "height": 14, "bottom": 4,
             "borderColor": "transparent", "backgroundColor": "#F1F5F9",
             "fillerColor": _fade(PALETTE[0], .16),
             "handleStyle": {"color": PALETTE[0]},
             "dataBackground": {"lineStyle": {"color": "#CBD5E1"},
                                "areaStyle": {"color": "#E2E8F0"}},
             "textStyle": {"color": MUTED, "fontSize": 9}}]


# ---------------------------------------------------------------------------
# categorical
# ---------------------------------------------------------------------------

def _o_bar(d, horizontal=False, contiguous=False):
    cats, series = _cats(d), _series(d)
    if not series:
        return None
    vals = series[0]["values"]
    # A bar per category reads better coloured per category when the
    # categories are the subject (asset classes, drivers). One colour for
    # all of them would make the chart a shape rather than a comparison.
    data = [{"value": v,
             "itemStyle": {"color": _grad(PALETTE[i % len(PALETTE)],
                                          vertical=not horizontal)}}
            for i, v in enumerate(vals)]
    radius = ([0, 4, 4, 0] if horizontal else [4, 4, 0, 0]) if not contiguous else 0
    opt = _base(d)
    opt.update({
        "tooltip": _tooltip("axis"),
        "grid": _grid(False, left=86 if horizontal else 46),
        "series": [{"type": "bar", "data": data,
                    "barMaxWidth": "62%" if not contiguous else "100%",
                    "barCategoryGap": "6%" if contiguous else "34%",
                    "itemStyle": {"borderRadius": radius},
                    "emphasis": {"focus": "series",
                                 "itemStyle": {"shadowBlur": 10,
                                               "shadowColor": _fade(PALETTE[0], .45)}},
                    "animationDelay": 0}],
    })
    if horizontal:
        opt["xAxis"], opt["yAxis"] = _val_axis(), _cat_axis(cats)
        opt["yAxis"]["inverse"] = True
    else:
        opt["xAxis"], opt["yAxis"] = _cat_axis(cats), _val_axis()
        if z := _zoom(len(vals)):
            opt["dataZoom"] = z
    return opt


def _o_line(d, area=False):
    cats, series = _cats(d), _series(d)
    if not series:
        return None
    out = []
    for si, s in enumerate(series):
        col = PALETTE[si % len(PALETTE)]
        spec = {"type": "line", "name": s["label"] or f"Series {si + 1}",
                "data": s["values"], "smooth": 0.32,
                "showSymbol": True, "symbolSize": 6,
                "lineStyle": {"width": 2.4, "color": col,
                              "shadowBlur": 8,
                              "shadowColor": _fade(col, .30),
                              "shadowOffsetY": 3},
                "itemStyle": {"color": col, "borderColor": "#fff",
                              "borderWidth": 1.6},
                "emphasis": {"focus": "series", "scale": 1.7}}
        if area:
            spec["areaStyle"] = {"color": _grad(col, to=0.02), "opacity": .55}
        out.append(spec)
    opt = _base(d)
    opt.update({"tooltip": _tooltip("axis"), "xAxis": _cat_axis(cats),
                "yAxis": _val_axis(), "series": out,
                "grid": _grid(bool(_legend([s["label"] for s in series])))})
    if lg := _legend([s["label"] for s in series]):
        opt["legend"] = lg
    if z := _zoom(max(len(s["values"]) for s in series)):
        opt["dataZoom"] = z
        opt["grid"]["bottom"] = 44
    return opt


def _o_stacked(d):
    cats, series = _cats(d), _series(d)
    if not series:
        return None
    out = [{"type": "bar", "stack": "total",
            "name": s["label"] or f"Series {si + 1}",
            "data": s["values"],
            "itemStyle": {"color": PALETTE[si % len(PALETTE)],
                          "borderRadius": [3, 3, 0, 0] if si == len(series) - 1 else 0},
            "emphasis": {"focus": "series"},
            "barMaxWidth": "58%"}
           for si, s in enumerate(series)]
    opt = _base(d)
    lg = _legend([s["label"] for s in series])
    opt.update({"tooltip": _tooltip("axis"), "xAxis": _cat_axis(cats),
                "yAxis": _val_axis(), "series": out, "grid": _grid(bool(lg))})
    if lg:
        opt["legend"] = lg
    return opt


def _o_combo(d):
    cats, series = _cats(d), _series(d)
    if len(series) < 2:
        return _o_bar(d)
    bars, line = series[0], series[1]
    opt = _base(d)
    lg = _legend([bars["label"], line["label"]])
    opt.update({
        "tooltip": _tooltip("axis"), "xAxis": _cat_axis(cats),
        "yAxis": _val_axis(), "grid": _grid(bool(lg)),
        "series": [
            {"type": "bar", "name": bars["label"] or "Value",
             "data": bars["values"], "barMaxWidth": "48%",
             "itemStyle": {"color": _grad(PALETTE[0]),
                           "borderRadius": [4, 4, 0, 0]},
             "emphasis": {"focus": "series"}},
            {"type": "line", "name": line["label"] or "Trend",
             "data": line["values"], "smooth": 0.32, "symbolSize": 6,
             "lineStyle": {"width": 2.4, "color": PALETTE[3]},
             "itemStyle": {"color": PALETTE[3], "borderColor": "#fff",
                           "borderWidth": 1.6},
             "emphasis": {"focus": "series", "scale": 1.7}}],
    })
    if lg:
        opt["legend"] = lg
    return opt


# ---------------------------------------------------------------------------
# part-to-whole
# ---------------------------------------------------------------------------

def _o_pie(d, donut=False):
    items = _items(d)
    if not items or sum(abs(i["value"]) for i in items) <= 0:
        return None
    data = [{"name": i["label"], "value": abs(i["value"]),
             "itemStyle": {"color": PALETTE[n % len(PALETTE)],
                           "borderColor": "#fff", "borderWidth": 2}}
            for n, i in enumerate(items)]
    opt = _base(d)
    opt.update({
        "tooltip": _tooltip("item"),
        "legend": {"type": "scroll", "orient": "vertical", "right": 4,
                   "top": "middle", "itemWidth": 10, "itemHeight": 7,
                   "icon": "roundRect", "itemGap": 9,
                   "textStyle": {"color": MUTED, "fontSize": 10.5,
                                 "fontFamily": _FONT},
                   "inactiveColor": "#CBD5E1"},
        "series": [{
            "type": "pie", "data": data,
            "radius": ["52%", "78%"] if donut else ["0%", "76%"],
            "center": ["34%", "52%"],
            "avoidLabelOverlap": True,
            "padAngle": 1.2 if donut else 0.6,
            "itemStyle": {"borderRadius": 4},
            "label": {"show": False},
            # The centre of a donut is free space that can hold the reading
            # for whatever the pointer is on. Filled by the runtime.
            "emphasis": {"scale": True, "scaleSize": 6,
                         "label": {"show": bool(donut), "fontSize": 15,
                                   "fontWeight": 700, "color": INK,
                                   "formatter": "{b}"},
                         "itemStyle": {"shadowBlur": 16,
                                       "shadowColor": "rgba(15,23,42,.20)"}},
            "animationType": "scale", "animationEasing": "elasticOut",
        }],
    })
    return opt


def _o_funnel(d):
    items = _items(d)
    if not items:
        return None
    opt = _base(d)
    opt.update({
        "tooltip": _tooltip("item"),
        "series": [{
            "type": "funnel", "left": "6%", "right": "6%", "top": 12,
            "bottom": 10, "minSize": "22%", "gap": 2,
            "data": [{"name": i["label"], "value": abs(i["value"]),
                      "itemStyle": {"color": PALETTE[n % len(PALETTE)]}}
                     for n, i in enumerate(items)],
            "label": {"show": True, "position": "inside", "color": "#fff",
                      "fontSize": 10.5, "fontWeight": 600,
                      "formatter": "{b}"},
            "itemStyle": {"borderColor": "#fff", "borderWidth": 1.5,
                          "opacity": .93},
            "emphasis": {"label": {"fontSize": 12},
                         "itemStyle": {"opacity": 1}},
        }],
    })
    return opt


def _o_treemap(d):
    items = _items(d)
    if not items:
        return None
    opt = _base(d)
    opt.update({
        "tooltip": _tooltip("item"),
        "series": [{
            "type": "treemap", "roam": False, "nodeClick": False,
            "breadcrumb": {"show": False},
            "left": 2, "right": 2, "top": 2, "bottom": 2,
            "itemStyle": {"borderColor": "#fff", "borderWidth": 2,
                          "borderRadius": 4, "gapWidth": 2},
            "label": {"show": True, "color": "#fff", "fontSize": 11,
                      "fontWeight": 600, "overflow": "truncate",
                      "formatter": "{b}"},
            "upperLabel": {"show": False},
            "emphasis": {"itemStyle": {"borderColor": "#0F172A",
                                       "borderWidth": 2}},
            "data": [{"name": i["label"], "value": abs(i["value"]),
                      "itemStyle": {"color": PALETTE[n % len(PALETTE)]}}
                     for n, i in enumerate(items)],
            "animationEasing": "quarticOut",
        }],
    })
    return opt


# ---------------------------------------------------------------------------
# delta
# ---------------------------------------------------------------------------

def _o_waterfall(d):
    """Built the standard ECharts way: an invisible support bar carries each
    step up to where the visible bar starts."""
    items = _items(d)
    if not items:
        return None
    support, rise, fall, run = [], [], [], 0.0
    for it in items:
        v = it["value"]
        support.append(round(min(run, run + v), 6))
        rise.append(abs(v) if v >= 0 else "-")
        fall.append(abs(v) if v < 0 else "-")
        run += v
    opt = _base(d)
    opt.update({
        "tooltip": _tooltip("axis"),
        "xAxis": _cat_axis([i["label"] for i in items]),
        "yAxis": _val_axis(), "grid": _grid(False),
        "series": [
            {"type": "bar", "stack": "wf", "name": "_support",
             "data": support, "silent": True,
             "itemStyle": {"color": "transparent"},
             "emphasis": {"itemStyle": {"color": "transparent"}},
             "barMaxWidth": "56%"},
            {"type": "bar", "stack": "wf", "name": "Added",
             "data": rise, "barMaxWidth": "56%",
             "itemStyle": {"color": _grad(POS), "borderRadius": [4, 4, 0, 0]},
             "emphasis": {"focus": "series"}},
            {"type": "bar", "stack": "wf", "name": "Reduced",
             "data": fall, "barMaxWidth": "56%",
             "itemStyle": {"color": _grad(NEG), "borderRadius": [0, 0, 4, 4]},
             "emphasis": {"focus": "series"}},
        ],
        "legend": {"data": ["Added", "Reduced"], "top": 0, "left": 0,
                   "itemWidth": 11, "itemHeight": 7, "icon": "roundRect",
                   "textStyle": {"color": MUTED, "fontSize": 10.5,
                                 "fontFamily": _FONT}},
    })
    opt["grid"]["top"] = 26
    return opt


# ---------------------------------------------------------------------------
# relationship
# ---------------------------------------------------------------------------

def _o_scatter(d, bubble=False):
    series = d.get("series") or []
    out, sizes = [], []
    for s in series:
        for p in (s.get("values") or []):
            if isinstance(p, (list, tuple)) and len(p) >= 3:
                sizes.append(abs(float(p[2])))
    rmax = max(sizes) if sizes else 1.0
    for si, s in enumerate(series):
        col = PALETTE[si % len(PALETTE)]
        pts = []
        for p in (s.get("values") or []):
            if not isinstance(p, (list, tuple)) or len(p) < 2:
                continue
            x, y = float(p[0]), float(p[1])
            if bubble and len(p) > 2:
                # symbolSize must be a number here: the option is JSON and
                # cannot carry the sizing callback ECharts would normally use.
                r = 8 + (abs(float(p[2])) / (rmax or 1.0)) * 26
                pts.append({"value": [x, y, float(p[2])],
                            "symbolSize": round(r, 1)})
            else:
                pts.append({"value": [x, y], "symbolSize": 11})
        if not pts:
            continue
        out.append({"type": "scatter", "name": s.get("label") or f"Series {si + 1}",
                    "data": pts,
                    "itemStyle": {"color": _fade(col, .72),
                                  "borderColor": col, "borderWidth": 1.4},
                    "emphasis": {"focus": "series",
                                 "itemStyle": {"color": col,
                                               "shadowBlur": 12,
                                               "shadowColor": _fade(col, .5)}}})
    if not out:
        return None
    opt = _base(d)
    lg = _legend([s["name"] for s in out])
    opt.update({
        "tooltip": _tooltip("item"),
        "xAxis": dict(_val_axis(), splitLine={"lineStyle": {"color": GRID,
                                                            "type": "dashed"}}),
        "yAxis": _val_axis(), "series": out, "grid": _grid(bool(lg)),
    })
    if lg:
        opt["legend"] = lg
    return opt


# ---------------------------------------------------------------------------
# single value
# ---------------------------------------------------------------------------

def _o_gauge(d, bar=False):
    v = float(d.get("value", 0) or 0)
    lo = float(d.get("min", 0) or 0)
    hi = float(d.get("max", 100) or 100)
    if hi <= lo:
        hi = lo + 1.0
    unit = str(d.get("unit", "") or "")
    frac = max(0.0, min(1.0, (v - lo) / (hi - lo)))

    if bar:
        # A progress bar is a gauge with the dial removed: same reading,
        # far less ink, which is the point of asking for this kind.
        opt = _base(d)
        opt.update({
            "tooltip": _tooltip("item"),
            "grid": {"left": 10, "right": 10, "top": "42%", "bottom": "34%"},
            "xAxis": {"type": "value", "max": hi, "min": lo, "show": False},
            "yAxis": {"type": "category", "data": [""], "show": False},
            "series": [
                {"type": "bar", "data": [hi], "barWidth": 18, "silent": True,
                 "itemStyle": {"color": "#EEF2F7", "borderRadius": 9},
                 "z": 1, "animation": False},
                {"type": "bar", "data": [v], "barWidth": 18,
                 "barGap": "-100%",
                 "itemStyle": {"color": _grad(PALETTE[0], vertical=False, to=.85),
                               "borderRadius": 9},
                 "z": 2,
                 "label": {"show": True, "position": "insideRight",
                           "color": "#fff", "fontWeight": 700,
                           "fontSize": 11,
                           "formatter": f"{v:g}{unit}"},
                 "emphasis": {"disabled": True}},
            ],
        })
        return opt

    col = POS if frac >= .5 else (PALETTE[2] if frac >= .25 else NEG)
    opt = _base(d)
    opt.update({
        "series": [{
            "type": "gauge", "min": lo, "max": hi,
            "startAngle": 200, "endAngle": -20,
            "radius": "94%", "center": ["50%", "62%"],
            "progress": {"show": True, "width": 13, "roundCap": True,
                         "itemStyle": {"color": col}},
            "axisLine": {"lineStyle": {"width": 13, "color": [[1, "#EEF2F7"]]}},
            "pointer": {"show": False},
            "axisTick": {"show": False},
            "splitLine": {"show": False},
            "axisLabel": {"show": True, "distance": -4, "fontSize": 9,
                          "color": MUTED},
            "anchor": {"show": False},
            "title": {"show": False},
            "detail": {"valueAnimation": True, "fontSize": 22,
                       "fontWeight": 700, "color": INK, "offsetCenter": [0, "-6%"],
                       "formatter": f"{{value}}{unit}"},
            "data": [{"value": round(v, 2)}],
        }],
    })
    return opt


# ---------------------------------------------------------------------------
# multi-axis / matrix
# ---------------------------------------------------------------------------

def _o_radar(d):
    cats, series = _cats(d), _series(d)
    if not series or not cats:
        return None
    hi = max([v for s in series for v in s["values"]] + [1.0]) * 1.12
    opt = _base(d)
    lg = _legend([s["label"] for s in series])
    opt.update({
        "tooltip": _tooltip("item"),
        "radar": {
            "indicator": [{"name": c, "max": round(hi, 3)} for c in cats],
            "radius": "66%", "center": ["50%", "56%"],
            "shape": "polygon", "splitNumber": 4,
            "axisName": {"color": MUTED, "fontSize": 10,
                         "fontFamily": _FONT},
            "splitLine": {"lineStyle": {"color": GRID}},
            "splitArea": {"areaStyle": {"color": ["#FFFFFF", "#F8FAFC"]}},
            "axisLine": {"lineStyle": {"color": GRID}},
        },
        "series": [{
            "type": "radar", "symbolSize": 5,
            "emphasis": {"focus": "series", "lineStyle": {"width": 3}},
            "data": [{"name": s["label"] or f"Series {si + 1}",
                      "value": s["values"],
                      "lineStyle": {"width": 2.2,
                                    "color": PALETTE[si % len(PALETTE)]},
                      "itemStyle": {"color": PALETTE[si % len(PALETTE)]},
                      "areaStyle": {"color": _fade(PALETTE[si % len(PALETTE)], .22)}}
                     for si, s in enumerate(series)],
        }],
    })
    if lg:
        opt["legend"] = lg
    return opt


def _o_heatmap(d):
    xs = [str(x) for x in (d.get("x_labels") or [])]
    ys = [str(y) for y in (d.get("y_labels") or [])]
    m = d.get("matrix") or []
    if not m or not xs or not ys:
        return None
    cells, flat = [], []
    for r, row in enumerate(m):
        for c, v in enumerate(row):
            try:
                fv = float(v)
            except (TypeError, ValueError):
                fv = 0.0
            cells.append([c, r, round(fv, 4)])
            flat.append(fv)
    hi, lo = (max(flat), min(flat)) if flat else (1.0, 0.0)
    opt = _base(d)
    opt.update({
        "tooltip": _tooltip("item"),
        "grid": {"left": 76, "right": 14, "top": 10, "bottom": 46},
        "xAxis": dict(_cat_axis(xs), splitArea={"show": True}),
        "yAxis": dict(_cat_axis(ys), splitArea={"show": True}, inverse=True),
        "visualMap": {
            "min": lo, "max": hi, "calculable": True, "orient": "horizontal",
            "left": "center", "bottom": 2, "itemWidth": 11, "itemHeight": 68,
            "textStyle": {"color": MUTED, "fontSize": 9.5,
                          "fontFamily": _FONT},
            # Diverging, because a heatmap in this document is nearly always
            # showing something that has a good and a bad direction.
            "inRange": {"color": ["#DBEAFE", "#93C5FD", "#4F46E5", "#312E81"]},
        },
        "series": [{
            "type": "heatmap", "data": cells,
            "itemStyle": {"borderColor": "#fff", "borderWidth": 1.5,
                          "borderRadius": 2},
            "emphasis": {"itemStyle": {"shadowBlur": 10,
                                       "shadowColor": "rgba(15,23,42,.35)"}},
            "progressive": 0,
        }],
    })
    return opt


# ---------------------------------------------------------------------------
# registry — mirrors charts.RENDERERS one for one
# ---------------------------------------------------------------------------

OPTIONS = {
    "bar":       lambda d: _o_bar(d),
    "hbar":      lambda d: _o_bar(d, horizontal=True),
    "histogram": lambda d: _o_bar(d, contiguous=True),
    "line":      lambda d: _o_line(d),
    "area":      lambda d: _o_line(d, area=True),
    "stacked":   _o_stacked,
    "combo":     _o_combo,
    "pie":       lambda d: _o_pie(d),
    "donut":     lambda d: _o_pie(d, donut=True),
    "funnel":    _o_funnel,
    "treemap":   _o_treemap,
    "waterfall": _o_waterfall,
    "scatter":   lambda d: _o_scatter(d),
    "bubble":    lambda d: _o_scatter(d, bubble=True),
    "gauge":     lambda d: _o_gauge(d),
    "progress":  lambda d: _o_gauge(d, bar=True),
    "radar":     _o_radar,
    "heatmap":   _o_heatmap,
}


def build_option(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The interactive option for a chart block, or None.

    None is a normal outcome, not a failure: it means this chart keeps its
    static SVG. Returning None on any error is deliberate — a chart that
    cannot be upgraded must still be a chart, and the SVG is already there.
    """
    kind = str(data.get("kind", "bar")).lower()
    fn = OPTIONS.get(kind)
    if fn is None:
        return None
    try:
        return fn(data)
    except Exception:
        return None
