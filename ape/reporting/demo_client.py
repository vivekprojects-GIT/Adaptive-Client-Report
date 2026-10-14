"""A fictional client for template previews.

Template previews (the gallery and the template editor) show what a layout
looks like. They must never show a real client's portfolio: an adviser
browsing layouts, or a screenshot of one, would otherwise expose someone's
holdings. This module builds one invented client, John Doe, through the
same CSV parser real uploads use, then adds the detail an upload cannot
carry (positions, past quarters, strategic targets) so every section of
every template has something to draw.

The figures are internally consistent (allocations sum to 100, history
ends on this quarter's return) so the grounding gate passes them like any
real snapshot. They describe nobody.
"""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache

from .csv_source import ClientSnapshot, parse_csv

DEMO_CLIENT_ID = "DEMO-0001"

_HEADER = (
    "client_id,display_name,email,segment_id,period,as_of,portfolio_value,"
    "quarter_return_pct,benchmark_return_pct,risk_level,"
    "alloc_alternatives,alloc_cash,alloc_fixed_income,alloc_intl_equity,alloc_real_assets,alloc_us_equity,"
    "attr_alternatives,attr_cash,attr_fixed_income,attr_intl_equity,attr_real_assets,attr_us_equity,attr_fees,"
    "fee_advisory,fee_fund,flow_contributions,flow_withdrawals,beginning_value,"
    "income_dividends,income_interest,income_estimated_annual,realized_gain,realized_gain_ytd,"
    "unrealized_gain,cost_basis,return_ytd_pct,benchmark_ytd_pct,return_1y_pct,benchmark_1y_pct,"
    "return_3y_pct,benchmark_3y_pct,return_itd_pct,benchmark_itd_pct,inception_date,"
    "volatility_pct,sharpe_ratio,beta,max_drawdown_pct,goal_name,goal_target_value,goal_target_year,"
    "goal_status,isa_subscribed,isa_allowance,isa_tax_year,adviser_name,adviser_phone,next_review_date"
)
_ROW = (
    f"{DEMO_CLIENT_ID},John Doe,john.doe@example.com,balanced_growth,2026Q2,2026-06-30,1250000.00,"
    "2.40,2.10,Moderate,"
    "5.0,5.0,30.0,20.0,5.0,35.0,"
    "0.06,0.02,0.18,0.52,0.08,1.82,-0.28,"
    "2812.50,937.50,15000.0,5000.0,1210000.00,"
    "6200.00,2100.00,31500.00,4800.00,9600.00,"
    "148500.00,1101500.00,4.85,4.40,9.60,8.90,"
    "6.30,5.95,7.10,6.70,March 2019,"
    "9.4,0.78,0.92,-11.6,Retire at 62,2000000,2041,"
    "On track,12000,20000,2026/27,Alex Morgan,020 7946 0000,15 January 2027"
)

# Positions by asset class, in pounds. Generic fund names on purpose:
# a preview must not read as advice to hold any real security.
_HOLDINGS = [
    ("DMUS1", "US Large Cap Index Fund",        "Us Equity",    22.0,  2.9),
    ("DMUS2", "US Quality Growth Fund",         "Us Equity",    13.0,  2.6),
    ("DMIN1", "Developed Markets ex-US Fund",   "Intl Equity",  12.0,  2.7),
    ("DMIN2", "Emerging Markets Equity Fund",   "Intl Equity",   8.0, -1.8),
    ("DMFI1", "Global Aggregate Bond Fund",     "Fixed Income", 14.0,  0.7),
    ("DMFI2", "UK Gilts 2032",                  "Fixed Income",  9.0,  0.5),
    ("DMFI3", "Short-Dated Corporate Bond Fund","Fixed Income",  7.0,  0.6),
    ("DMRA1", "Global Property Securities Fund","Real Assets",   5.0, -0.9),
    ("DMAL1", "Multi-Strategy Alternatives Fund","Alternatives", 5.0,  1.2),
    ("DMCA1", "Sterling Cash",                  "Cash",          5.0,  0.4),
]

_HISTORY = [
    ("2025Q1", 1.10, 1.25), ("2025Q2", 2.05, 1.80), ("2025Q3", 1.45, 1.60),
    ("2025Q4", 3.20, 2.95), ("2026Q1", -0.95, -1.10), ("2026Q2", 2.40, 2.10),
]

_TARGETS = {"Us Equity": 33.0, "Intl Equity": 22.0, "Fixed Income": 30.0,
            "Real Assets": 5.0, "Alternatives": 5.0, "Cash": 5.0}


@lru_cache(maxsize=1)
def demo_snapshot() -> ClientSnapshot:
    snaps, errors = parse_csv(_HEADER + "\n" + _ROW + "\n")
    if errors or not snaps:
        raise RuntimeError(f"demo client did not parse: {errors}")
    base = snaps[0]
    value = base.portfolio_value
    holdings = [
        {"symbol": sym, "name": name, "asset_class": ac, "weight_pct": w,
         "value": round(value * w / 100.0, 2), "return_pct": r,
         "contribution_pct": round(w * r / 100.0, 2)}
        for sym, name, ac, w, r in _HOLDINGS]
    history = [{"period": p, "portfolio": a, "benchmark": b, "excess": round(a - b, 2)}
               for p, a, b in _HISTORY]
    # Set directly as well as in the row: not every parser version reads it.
    return replace(base, holdings=holdings, history=history, targets=dict(_TARGETS),
                   benchmark_name="60/40 Global Balanced",
                   volatility_pct=base.volatility_pct or 9.4)
