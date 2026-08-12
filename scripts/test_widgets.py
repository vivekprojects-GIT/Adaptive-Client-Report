"""Render every registered widget and every chart kind. Fail loudly.

Checks each one actually produces output rather than silently rendering
nothing — the failure mode that made components "not open". A widget that
returns an empty string, or a chart that falls through to the placeholder,
is a FAIL here rather than a gap someone notices in a client document.

    python scripts/test_widgets.py            # report + write gallery
    python scripts/test_widgets.py --open     # also print the gallery path
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ape.reporting.charts import KINDS, render_chart  # noqa: E402
from ape.reporting.csv_source import ClientSnapshot  # noqa: E402
from ape.reporting.echarts_opts import build_option  # noqa: E402
from ape.reporting.generate import (BUILDERS, _ecw, _narrative,  # noqa: E402
                                    _render_block, render_html)

SNAP = ClientSnapshot(
    client_id="C1001", display_name="Jordan Lee", email="jordan@example.com",
    segment_id="balanced_growth", period="2026Q2", as_of="2026-06-30",
    portfolio_value=1_240_000.0, quarter_return_pct=4.80,
    benchmark_return_pct=5.40, risk_level="Moderate",
    allocations=[{"asset_class": "US Equity", "weight_pct": 48.0},
                 {"asset_class": "Fixed Income", "weight_pct": 30.0},
                 {"asset_class": "Intl Equity", "weight_pct": 14.0},
                 {"asset_class": "Cash", "weight_pct": 8.0}],
    attribution=[{"driver": "US Equity", "contribution_pct": 2.90},
                 {"driver": "Fixed Income", "contribution_pct": 0.90},
                 {"driver": "Intl Equity", "contribution_pct": 1.20},
                 {"driver": "Fees", "contribution_pct": -0.20}],
    fees={"advisory": 2150.0, "fund": 720.0},
    cash_flows={"contributions": 15000.0, "withdrawals": 5000.0},

    # Depth the CSV path cannot supply. Included so the blocks that need
    # holdings, history or targets are actually exercised — without it they
    # correctly return None and the gallery silently stops covering them.
    # One holding is deliberately negative so top_detractors has something
    # to show.
    holdings=[
        {"symbol": "VTI", "name": "Total US Market Index", "asset_class": "US Equity",
         "weight_pct": 30.0, "value": 372_000.0, "return_pct": 6.20,
         "contribution_pct": 1.86},
        {"symbol": "SPX500", "name": "US Large Cap Core", "asset_class": "US Equity",
         "weight_pct": 18.0, "value": 223_200.0, "return_pct": 5.80,
         "contribution_pct": 1.04},
        {"symbol": "AGGB", "name": "Aggregate Bond Index", "asset_class": "Fixed Income",
         "weight_pct": 30.0, "value": 372_000.0, "return_pct": 3.00,
         "contribution_pct": 0.90},
        {"symbol": "EMKT", "name": "Emerging Markets", "asset_class": "Intl Equity",
         "weight_pct": 14.0, "value": 173_600.0, "return_pct": -2.50,
         "contribution_pct": -0.35},
        {"symbol": "CASH", "name": "Cash and Equivalents", "asset_class": "Cash",
         "weight_pct": 8.0, "value": 99_200.0, "return_pct": 1.00,
         "contribution_pct": 0.08},
    ],
    history=[
        {"period": "2025Q3", "portfolio": 1.83, "benchmark": 2.10, "excess": -0.27},
        {"period": "2025Q4", "portfolio": 3.85, "benchmark": 3.40, "excess": 0.45},
        {"period": "2026Q1", "portfolio": -1.33, "benchmark": -0.90, "excess": -0.43},
        {"period": "2026Q2", "portfolio": 4.80, "benchmark": 5.40, "excess": -0.60},
    ],
    targets={"US Equity": 40.0, "Fixed Income": 30.0, "Intl Equity": 15.0,
             "Cash": 7.0},
    benchmark_name="60/40 Balanced Composite",
    volatility_pct=9.62,
)

# Shapes that need data the snapshot does not carry, so the chart builder
# cannot supply them. Exercised here with explicit fixtures so every kind is
# still proven to render.
EXTRA = {
    "scatter": {"kind": "scatter", "series": [
        {"label": "Risk vs return", "values": [[1, 2.1], [2, 3.4], [3, 2.8],
                                               [4, 5.1], [5, 4.4], [6, 6.2]]}]},
    "bubble": {"kind": "bubble", "series": [
        {"label": "Holdings", "values": [[1, 2.1, 5], [2, 3.4, 12],
                                         [3, 2.8, 8], [4, 5.1, 20]]}]},
    "heatmap": {"kind": "heatmap",
                "x_labels": ["Q1", "Q2", "Q3", "Q4"],
                "y_labels": ["Equity", "Bonds", "Cash"],
                "matrix": [[2.1, 3.4, 1.2, 4.0],
                           [0.8, 0.9, 1.1, 0.4],
                           [0.1, 0.2, 0.1, 0.2]]},
    "radar": {"kind": "radar",
              "x_categories": ["Growth", "Income", "Risk", "Liquidity", "ESG"],
              "series": [{"label": "Portfolio", "values": [8, 5, 6, 7, 4]},
                         {"label": "Benchmark", "values": [6, 6, 5, 8, 5]}]},
    "combo": {"kind": "combo",
              "x_categories": ["Q1", "Q2", "Q3", "Q4"],
              "series": [{"label": "Value", "values": [4.2, 4.8, 5.1, 5.6]},
                         {"label": "Return", "values": [1.1, 2.4, 1.8, 3.0]}]},
    "stacked": {"kind": "stacked",
                "x_categories": ["Q1", "Q2", "Q3"],
                "series": [{"label": "Equity", "values": [2.1, 2.6, 3.0]},
                           {"label": "Bonds", "values": [0.9, 0.7, 1.1]},
                           {"label": "Cash", "values": [0.2, 0.1, 0.2]}]},
}


def _source_numbers(data: dict) -> set[float]:
    """Every figure the source dict actually contains, plus the two forms a
    chart is allowed to derive from them: the absolute value, and a running
    total (which is what a waterfall's invisible support bars are)."""
    raw: list[float] = []
    for it in (data.get("items") or []):
        try:
            raw.append(float(it.get("value")))
        except (TypeError, ValueError):
            pass
    for s in (data.get("series") or []):
        for v in (s.get("values") or []):
            if isinstance(v, (list, tuple)):
                raw.extend(float(x) for x in v
                           if isinstance(x, (int, float)))
            elif isinstance(v, (int, float)):
                raw.append(float(v))
    for row in (data.get("matrix") or []):
        raw.extend(float(v) for v in row if isinstance(v, (int, float)))
    for k in ("value", "min", "max"):
        if isinstance(data.get(k), (int, float)):
            raw.append(float(data[k]))

    allowed = {0.0}
    run = 0.0
    for v in raw:
        allowed.add(round(v, 4))
        allowed.add(round(abs(v), 4))
        run += v
        allowed.add(round(run, 4))
        allowed.add(round(min(run, run - v), 4))
    return allowed


def _option_numbers(opt: dict, kind: str) -> set[float]:
    """The figures the option will actually put in front of a reader.

    Styling numbers are not collected — only what lands in series data.
    A heatmap cell is [column, row, value]; the first two are positions in
    the grid, not measurements, so only the third is taken.
    """
    out: set[float] = set()

    def take(v):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return
        out.add(round(float(v), 4))

    for s in (opt.get("series") or []):
        for entry in (s.get("data") or []):
            val = entry.get("value") if isinstance(entry, dict) else entry
            if isinstance(val, (list, tuple)):
                if kind == "heatmap":
                    take(val[-1])
                else:
                    for x in val:
                        take(x)
            else:
                take(val)
    return out


def _invented_values(data: dict, opt: dict) -> set[float]:
    kind = str(data.get("kind", ""))
    # A radar's indicator maxima and a visualMap's bounds are axis extents,
    # not readings, and are deliberately not collected above.
    return _option_numbers(opt, kind) - _source_numbers(data)


def main() -> None:
    failures: list[str] = []
    cards: list[str] = []

    # ---- 1. every registered block builder ----------------------------
    print("BLOCK BUILDERS")
    for name in sorted(BUILDERS):
        try:
            block = (BUILDERS[name](SNAP, 1, "donut") if name == "chart"
                     else BUILDERS[name](SNAP, 1))
            if block is None:
                failures.append(f"{name}: builder returned None")
                print(f"  FAIL  {name:<20} builder returned None"); continue
            html_out = _render_block(block)
            if not html_out or len(html_out) < 40:
                failures.append(f"{name}: rendered empty")
                print(f"  FAIL  {name:<20} rendered empty"); continue
            if 'data-block-id' not in html_out:
                failures.append(f"{name}: missing data-block-id")
                print(f"  FAIL  {name:<20} no data-block-id"); continue
            print(f"  ok    {name:<20} {len(html_out):>5} chars")
            cards.append(f'<div class="card"><h4>{name}</h4>{html_out}</div>')
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
            print(f"  FAIL  {name:<20} {type(exc).__name__}: {exc}")

    # narrative is built separately (it takes the template brief)
    try:
        nb = _narrative(SNAP, 1, "brief")
        h = _render_block(nb)
        print(f"  ok    {'narrative':<20} {len(h):>5} chars")
        cards.append(f'<div class="card"><h4>narrative</h4>{h}</div>')
    except Exception as exc:
        failures.append(f"narrative: {exc}")
        print(f"  FAIL  narrative {exc}")

    # ---- 2. every chart kind ------------------------------------------
    print("\nCHART KINDS")
    for kind in KINDS:
        data = EXTRA.get(kind)
        if data is None:
            built = BUILDERS["chart"](SNAP, 1, kind)
            data = built["data"] if built else {"kind": kind}
        try:
            svg = render_chart(data)
            bad = ("unsupported" in svg or "no series" in svg
                   or "no values" in svg or "no points" in svg or "needs " in svg)
            if bad:
                failures.append(f"chart:{kind} fell through to placeholder")
                print(f"  FAIL  {kind:<12} placeholder"); continue
            if "<svg" not in svg:
                failures.append(f"chart:{kind} produced no SVG")
                print(f"  FAIL  {kind:<12} no SVG"); continue
            # Structural check: a chart must draw something. Byte-length alone
            # passes an SVG that renders blank, which is how "not opening"
            # went unnoticed. Two drawable elements is the floor — a gauge is
            # legitimately just a track, a fill and a label.
            drawn = sum(svg.count("<" + tag)
                        for tag in ("rect", "path", "circle",
                                    "polyline", "polygon", "line"))
            if drawn < 2:
                failures.append(f"chart:{kind} drew {drawn} element(s)")
                print(f"  FAIL  {kind:<12} drew only {drawn}"); continue
            # The interactive layer is checked separately from the SVG: a
            # kind that loses its option silently falls back forever, which
            # looks like nothing being wrong.
            opt = build_option(data)
            if opt is None:
                failures.append(f"chart:{kind} has no interactive option")
                print(f"  FAIL  {kind:<12} no ECharts option"); continue
            try:
                json.dumps(opt, allow_nan=False)
            except (TypeError, ValueError) as exc:
                failures.append(f"chart:{kind} option not JSON: {exc}")
                print(f"  FAIL  {kind:<12} option not JSON"); continue
            # The interactive layer re-encodes figures that are already
            # bound to the frozen snapshot. It must not introduce one that
            # is not in the source: a tooltip showing a number the report
            # cannot evidence is the same failure as prose doing it, and
            # the grounding validator never sees inside a chart option.
            missing = _invented_values(data, opt)
            if missing:
                failures.append(f"chart:{kind} option has values absent from "
                                f"the source data: {sorted(missing)[:6]}")
                print(f"  FAIL  {kind:<12} invented {sorted(missing)[:4]}")
                continue
            print(f"  ok    {kind:<12} {len(svg):>5} svg  +opt  facts-ok")
            cards.append(f'<div class="card"><h4>chart · {kind}</h4>'
                         f'{_ecw(opt, svg, kind)}</div>')
        except Exception as exc:
            failures.append(f"chart:{kind} {type(exc).__name__}: {exc}")
            print(f"  FAIL  {kind:<12} {type(exc).__name__}: {exc}")

    # ---- gallery ------------------------------------------------------
    out = ROOT / "data" / "generated" / "_widget_gallery.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        '<!doctype html><meta charset="utf-8"><title>Widget gallery</title>'
        # Relative, not "/static/...": the gallery is opened as a file, so
        # an absolute path would resolve against the filesystem root and
        # every card would silently show its fallback — which is exactly
        # the failure this gallery exists to catch.
        '<link rel="stylesheet" href="../../ape/static/widgets.css">'
        '<script defer src="../../ape/static/vendor/echarts.min.js"></script>'
        '<script defer src="../../ape/static/widgets.js"></script>'
        '<style>body{font-family:"Segoe UI",system-ui,Arial,sans-serif;background:#f1f5f9;'
        'margin:0;padding:20px;color:#0f172a}h1{font-size:17px;margin:0 0 14px}'
        '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:12px}'
        '.card{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:12px}'
        '.card h4{margin:0 0 8px;font-size:11px;text-transform:uppercase;'
        'letter-spacing:.06em;color:#94a3b8}'
        '.cw{width:100%;height:auto}section{margin:0}'
        'table{width:100%;border-collapse:collapse;font-size:12px}'
        'th{text-align:left;font-size:10px;color:#94a3b8;border-bottom:1.5px solid #cbd5e1;padding:0 6px 4px 0}'
        'td{padding:5px 6px 5px 0;border-bottom:1px solid #e2e8f0}td.n,th.n{text-align:right}'
        '.kpis{display:grid;grid-template-columns:repeat(2,1fr);gap:6px}'
        '.kpi{background:#f8fafc;border:1px solid #e2e8f0;border-radius:5px;padding:6px 8px}'
        '.kpi span{display:block;font-size:9px;text-transform:uppercase;color:#94a3b8}'
        '.kpi b{font-size:13px}.alloc,.cmp>div,.risk,.series{display:flex;gap:8px;'
        'align-items:center;font-size:11.5px;margin-bottom:4px}'
        '.alloc span,.cmp span,.risk span,.series span{width:96px;color:#334155}'
        '.alloc i,.cmp i{height:8px;background:#3b82f6;border-radius:3px;display:block}'
        '.cmp i.bm{background:#94a3b8}.alloc b,.cmp b{margin-left:auto}'
        '.callout{padding:8px 11px;border-radius:6px;background:#eff6ff;'
        'border-left:3px solid #1d4ed8;font-size:12px}'
        '.callout.positive{background:#ecfdf5;border-color:#047857}</style>'
        f'<h1>Widget gallery — {len(cards)} components rendered</h1>'
        f'<div class="grid">{"".join(cards)}</div>',
        encoding="utf-8")

    print(f"\n{'-'*54}")
    print(f"rendered : {len(cards)}")
    print(f"failures : {len(failures)}")
    for f in failures:
        print(f"   ! {f}")
    print(f"gallery  : {out}")
    if failures:
        raise SystemExit(1)
    print("ALL WIDGETS RENDER")


if __name__ == "__main__":
    main()
