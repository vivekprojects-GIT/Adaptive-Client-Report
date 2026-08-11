"""Grounding validator tests.

The one that matters: a deliberately fabricated number must be REJECTED.
Everything else guards against the opposite failure — rejecting figures that
are legitimately written a different way, which would make the validator
useless in practice because nobody would trust it.

    python scripts/test_grounding.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ape.reporting.csv_source import ClientSnapshot  # noqa: E402
from ape.reporting.generate import build_report  # noqa: E402
from ape.reporting.grounding import (  # noqa: E402
    derived_facts, extract_numbers, validate_block, validate_report,
)

SNAP = ClientSnapshot(
    client_id="C1001", display_name="Jordan Lee", email="j@example.com",
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
)
FACTS = derived_facts(SNAP.numeric_facts())

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail else ""))


def prose(text):
    return {"block_id": "n_01", "type": "narrative",
            "data": {"text": text}, "source_refs": ["portfolio_value"]}


def main():
    print("1. NUMBER EXTRACTION + NORMALISATION")
    cases = [
        ("£1,240,000.00", 1_240_000.0), ("$1.24M", 1_240_000.0),
        ("1.24 million", 1_240_000.0), ("4.8%", 4.8),
        ("£2,150", 2150.0), ("15,000", 15000.0), ("-0.20%", -0.20),
    ]
    for raw, want in cases:
        got = extract_numbers(raw)
        check(f"parse {raw!r} -> {want:g}",
              bool(got) and abs(got[0][0] - want) < 0.01,
              f"got {got[0][0]:g}" if got else "no match")

    print("\n2. FABRICATED NUMBERS ARE REJECTED")
    bad = [
        ("wrong portfolio value", "Your portfolio was valued at £1,300,000.00."),
        ("wrong return", "Your portfolio returned 7.20% this quarter."),
        ("invented fee", "Total fees were £9,940 this period."),
        ("invented allocation", "US Equity represents 62.0% of the portfolio."),
        ("plausible but absent", "Your portfolio returned 4.85% this quarter."),
        # Direction matters as much as magnitude: fees DRAGGED 0.20%, so
        # claiming they added 0.20% is a misstatement, not a rounding.
        ("sign flipped on a real figure", "Fees added 0.20% to your return."),
    ]
    for label, text in bad:
        f = validate_block(prose(text), FACTS)
        check(f"reject: {label}", any(x.kind == "ungrounded_number" for x in f),
              f.pop().detail if f else "NOT REJECTED")

    print("\n3. LEGITIMATE FIGURES ARE ACCEPTED")
    good = [
        ("exact currency", "Your portfolio was valued at £1,240,000.00."),
        ("rounded millions", "Your portfolio is worth $1.24M."),
        ("written millions", "Your portfolio is worth 1.24 million."),
        ("percent", "Your portfolio returned 4.80% against 5.40%."),
        ("derived excess", "That is 0.60% behind the benchmark."),
        ("derived fee total", "Total fees were £2,870.00 this period."),
        ("derived net flow", "Net contributions were £10,000.00."),
        ("attribution", "US Equity added 2.90%."),
        ("counting words", "Your portfolio holds four asset classes."),
        ("a year", "This covers the period ending 2026."),
        ("signed negative", "Fees contributed -0.20% this quarter."),
        ("magnitude with a direction word", "Fees dragged 0.20% off the return."),
        ("a date is not a claim", "Figures are as at 2026-06-30."),
    ]
    for label, text in good:
        f = validate_block(prose(text), FACTS)
        offenders = [x for x in f if x.kind == "ungrounded_number"]
        check(f"accept: {label}", not offenders,
              offenders[0].detail if offenders else "")

    print("\n4. SOURCE REFS")
    blk = {"block_id": "b1", "type": "narrative",
           "data": {"text": "Valued at £1,240,000.00."},
           "source_refs": ["portfolio_value", "made_up_ref"]}
    f = validate_block(blk, FACTS)
    check("unknown source_ref flagged",
          any(x.kind == "unknown_source_ref" for x in f))
    blk2 = {"block_id": "b2", "type": "narrative",
            "data": {"text": "No figures here."}, "source_refs": []}
    check("missing source_refs flagged",
          any(x.kind == "no_source_refs" for x in validate_block(blk2, FACTS)))

    print("\n5. WHOLE REPORT — every generated block passes")
    tpl = {"template_id": "t", "strategy": "s", "brief": "",
           "required_blocks": ["kpi_grid", "chart:donut", "comparison_table",
                               "holdings_table", "fees_table", "narrative",
                               "callout", "allocation_donut", "comparison_chart",
                               "performance_line", "risk_card"]}
    rep = build_report(SNAP, tpl, "quarterly_portfolio_review")
    v = validate_report(rep, SNAP.numeric_facts())
    check("all code-built blocks grounded", v.ok,
          v.summary() + ("" if v.ok else " :: " + v.findings[0].detail))

    print("\n6. A TAMPERED REPORT IS CAUGHT")
    tampered = build_report(SNAP, tpl, "quarterly_portfolio_review")
    for b in tampered["blocks"]:
        if b["type"] == "kpi_grid":
            b["data"]["items"][0]["value"] = 9_999_999.0   # fabricate
            break
    v2 = validate_report(tampered, SNAP.numeric_facts())
    check("tampered KPI rejected", not v2.ok and len(v2.rejected) == 1,
          v2.summary())
    check("rejected block is excluded from accepted",
          all(b["type"] != "kpi_grid" for b in v2.accepted))

    print("\n" + "-" * 56)
    print(f"passed {len(PASS)} / {len(PASS) + len(FAIL)}")
    if FAIL:
        print("\nFAILURES:")
        for f in FAIL:
            print(f"   ! {f}")
        raise SystemExit(1)
    print("GROUNDING VALIDATOR WORKS")


if __name__ == "__main__":
    main()
