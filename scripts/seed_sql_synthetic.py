"""Synthetic client book — 12 clients x 4 quarters of coherent portfolio data.

    python scripts/seed_sql_synthetic.py --reset

═══════════════════════════════════════════════════════════════════════════
WHY THE ARITHMETIC IS BUILT BOTTOM-UP
═══════════════════════════════════════════════════════════════════════════

The obvious way to fake this data is to draw each figure independently:
a portfolio value, a return, some allocation weights, some attribution. That
produces data which looks fine in a table and is internally impossible —
attribution that doesn't sum to the return, weights that total 98.3%, a
value that ignores last quarter's performance.

Incoherent data is not a cosmetic problem here. Every generated report is
checked against the snapshot by the grounding validator, so a report built
on contradictory facts is faithfully, verifiably wrong. And the reconcilers
in csv_source.py would reject the rows anyway.

So everything is derived, in this order:

    holdings  ->  asset-class weight and return
              ->  contribution = weight x return
              ->  gross return = sum of contributions
              ->  net return = gross - fee drag
              ->  next quarter's opening value = value x (1+net) + flows

Each figure is a consequence of the ones before it. Allocations sum to
exactly 100.00, attribution reconciles to the stated return exactly, and
the value series compounds across the four quarters.

═══════════════════════════════════════════════════════════════════════════
SHARED MARKET, DIFFERENT OUTCOMES
═══════════════════════════════════════════════════════════════════════════

All 12 clients live through the same four quarters: two up, one down
(2026Q1), one recovery. Returns differ because allocations differ, not
because of unrelated random draws. That is what makes the book useful for
testing — a conservative client and an aggressive one diverge for a reason
you can point at, and 2026Q1 gives real negative-return reports to check
that narrative tone and grounding both hold when the news is bad.

The generator is seeded, so the book is identical on every run.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ape.db.models import (  # noqa: E402
    Allocation, CashFlow, Client, ClientPreference, Fee, Holding, Performance,
    ReportSnapshot,
)
from ape.db.session import database_url, init_db, session_scope  # noqa: E402

SEED = 20260630
PERIODS = [("2025Q3", "2025-09-30"), ("2025Q4", "2025-12-31"),
           ("2026Q1", "2026-03-31"), ("2026Q2", "2026-06-30")]

# Asset-class mean return (%) per quarter. Shared by every client — one
# market, experienced differently depending on what you hold.
REGIME: Dict[str, Dict[str, float]] = {
    "2025Q3": {"US Equity": 3.2, "Intl Equity": 2.1, "Fixed Income": 0.9,
               "Real Assets": 1.4, "Alternatives": 1.0, "Cash": 1.1},
    "2025Q4": {"US Equity": 6.8, "Intl Equity": 4.9, "Fixed Income": 1.2,
               "Real Assets": 2.6, "Alternatives": 2.2, "Cash": 1.1},
    "2026Q1": {"US Equity": -3.4, "Intl Equity": -1.8, "Fixed Income": 1.8,
               "Real Assets": -0.9, "Alternatives": 0.4, "Cash": 1.0},
    "2026Q2": {"US Equity": 5.1, "Intl Equity": 3.6, "Fixed Income": 0.6,
               "Real Assets": 2.0, "Alternatives": 1.6, "Cash": 1.0},
}

# Dispersion of individual holdings around their asset class. Equities
# scatter; cash does not.
DISPERSION = {"US Equity": 2.4, "Intl Equity": 2.2, "Fixed Income": 0.7,
              "Real Assets": 1.8, "Alternatives": 1.5, "Cash": 0.05}

UNIVERSE: Dict[str, List[Tuple[str, str]]] = {
    "US Equity": [("VTI", "Total US Market Index"), ("SPX500", "US Large Cap Core"),
                  ("USMID", "US Mid Cap Growth"), ("USDIV", "US Dividend Leaders")],
    "Intl Equity": [("VXUS", "International Developed"), ("EMKT", "Emerging Markets"),
                    ("EURST", "European Equity")],
    "Fixed Income": [("AGGB", "Aggregate Bond Index"), ("GILT", "Government Bond Fund"),
                     ("CORPB", "Investment Grade Corporate"), ("MUNI", "Municipal Income")],
    "Real Assets": [("REIT", "Global Real Estate"), ("INFRA", "Listed Infrastructure")],
    "Alternatives": [("ALTS", "Diversified Alternatives"), ("GOLD", "Precious Metals")],
    "Cash": [("CASH", "Cash and Equivalents")],
}

# strategic target weights per persona; also the benchmark mix.
PERSONAS: Dict[str, Dict[str, float]] = {
    "conservative_income": {"Fixed Income": 55, "US Equity": 20, "Intl Equity": 8,
                            "Real Assets": 7, "Cash": 10},
    "retirement_drawdown": {"Fixed Income": 45, "US Equity": 25, "Intl Equity": 10,
                            "Real Assets": 8, "Cash": 12},
    "balanced_growth":     {"US Equity": 40, "Fixed Income": 30, "Intl Equity": 15,
                            "Real Assets": 8, "Cash": 7},
    "esg_tilt":            {"US Equity": 45, "Fixed Income": 22, "Intl Equity": 20,
                            "Real Assets": 8, "Cash": 5},
    "growth_equity":       {"US Equity": 55, "Intl Equity": 20, "Fixed Income": 15,
                            "Real Assets": 5, "Cash": 5},
    "aggressive_growth":   {"US Equity": 62, "Intl Equity": 22, "Fixed Income": 8,
                            "Alternatives": 5, "Cash": 3},
}

RISK_BY_PERSONA = {
    "conservative_income": "Conservative", "retirement_drawdown": "Conservative",
    "balanced_growth": "Moderate", "esg_tilt": "Moderate",
    "growth_equity": "Growth", "aggressive_growth": "Aggressive",
}

BENCHMARK_NAME = {
    "Conservative": "20/80 Conservative Composite",
    "Moderate": "60/40 Balanced Composite",
    "Growth": "80/20 Growth Composite",
    "Aggressive": "Global Equity Composite",
}

# name, persona, opening value, quarterly contribution, quarterly withdrawal
BOOK = [
    ("C1001", "Jordan Lee",        "balanced_growth",     1_180_000,  6_000,      0),
    ("C1002", "Priya Raman",       "growth_equity",       2_450_000, 12_000,      0),
    ("C1003", "Marcus Whitfield",  "conservative_income",   870_000,      0,  4_500),
    ("C1004", "Elena Vasquez",     "aggressive_growth",   3_920_000, 25_000,      0),
    ("C1005", "Thomas Okafor",     "retirement_drawdown", 1_640_000,      0, 14_000),
    ("C1006", "Sarah Lindqvist",   "esg_tilt",            1_310_000,  8_000,      0),
    ("C1007", "David Chen",        "balanced_growth",       620_000,  3_500,      0),
    ("C1008", "Amara Diallo",      "growth_equity",       5_180_000, 30_000,      0),
    ("C1009", "Robert Ashworth",   "conservative_income",   740_000,      0,  6_000),
    ("C1010", "Yuki Tanaka",       "balanced_growth",     2_060_000,  9_000,  2_000),
    ("C1011", "Fatima Al-Rashid",  "aggressive_growth",     980_000, 15_000,      0),
    ("C1012", "Grace Mbeki",       "retirement_drawdown", 3_140_000,      0, 22_000),
]

ADVISERS = ["Alison Reid", "Michael Torres", "Sunita Kapoor"]

ADVISORY_BPS = 0.0025      # 25bp per quarter (~1.0% annual)
FUND_BPS = 0.0009          # 9bp per quarter


# ---------------------------------------------------------------------------
# Weight helpers — everything must land on exact totals
# ---------------------------------------------------------------------------

def _normalise(weights: Dict[str, float], total: float = 100.0,
               dp: int = 1) -> Dict[str, float]:
    """Scale to `total`, round, then push the rounding residual into the
    largest bucket. Without the last step the weights sum to 99.9 or 100.1
    and the CSV reconciler rejects the row."""
    s = sum(weights.values())
    scaled = {k: round(v * total / s, dp) for k, v in weights.items()}
    residual = round(total - sum(scaled.values()), dp)
    if residual:
        biggest = max(scaled, key=lambda k: scaled[k])
        scaled[biggest] = round(scaled[biggest] + residual, dp)
    return scaled


def _split(total: float, n: int, rng: random.Random, dp: int = 1) -> List[float]:
    """Split a class weight across n holdings, summing to exactly `total`."""
    raw = [rng.uniform(0.6, 1.4) for _ in range(n)]
    s = sum(raw)
    parts = [round(total * r / s, dp) for r in raw]
    parts[0] = round(parts[0] + round(total - sum(parts), dp), dp)
    return parts


def _drift(target: Dict[str, float], rng: random.Random) -> Dict[str, float]:
    """Portfolios drift from their strategic target between rebalances."""
    return _normalise({k: max(0.5, v * rng.uniform(0.88, 1.12))
                       for k, v in target.items()})


# ---------------------------------------------------------------------------
# One snapshot
# ---------------------------------------------------------------------------

def build_snapshot(client_id: str, persona: str, period: str, as_of: str,
                   opening_value: float, contribution: float, withdrawal: float,
                   rng: random.Random) -> dict:
    target = PERSONAS[persona]
    weights = _drift(target, rng)
    regime = REGIME[period]

    holdings: List[dict] = []
    allocations: List[dict] = []
    attribution: List[dict] = []

    for asset_class, class_weight in weights.items():
        pool = UNIVERSE[asset_class]
        k = min(len(pool), 1 if asset_class == "Cash" else rng.randint(2, len(pool)))
        picks = pool[:1] if asset_class == "Cash" else rng.sample(pool, k)
        parts = _split(class_weight, len(picks), rng)

        mean, sd = regime[asset_class], DISPERSION[asset_class]
        class_num = 0.0
        for (symbol, name), w in zip(picks, parts):
            ret = round(rng.gauss(mean, sd), 2)
            class_num += w * ret
            holdings.append({
                "symbol": symbol, "name": name, "asset_class": asset_class,
                "weight_pct": w, "return_pct": ret,
                "market_value": round(opening_value * w / 100.0, 2),
                "contribution_pct": round(w * ret / 100.0, 2),
            })
        class_return = round(class_num / class_weight, 2) if class_weight else 0.0
        contribution_pct = round(class_weight * class_return / 100.0, 2)

        allocations.append({
            "asset_class": asset_class, "weight_pct": class_weight,
            "target_weight_pct": round(float(target[asset_class]), 1),
            "return_pct": class_return, "contribution_pct": contribution_pct,
            "market_value": round(opening_value * class_weight / 100.0, 2),
        })
        attribution.append({"driver": asset_class, "contribution_pct": contribution_pct})

    gross = round(sum(a["contribution_pct"] for a in attribution), 2)

    advisory = round(opening_value * ADVISORY_BPS, 2)
    fund = round(opening_value * FUND_BPS, 2)
    fee_drag = -round((advisory + fund) / opening_value * 100.0, 2)
    attribution.append({"driver": "Fees", "contribution_pct": fee_drag})

    # Net return IS the sum of the attribution rows. Defined this way rather
    # than drawn separately, so the two can never disagree.
    quarter_return = round(gross + fee_drag, 2)

    # Benchmark = strategic mix at market returns, no drift, no selection,
    # no fees. Excess return is then genuinely attributable to the two
    # things a manager controls.
    bench_mix = _normalise(dict(target))
    benchmark_return = round(
        sum(w * regime[ac] for ac, w in bench_mix.items()) / 100.0, 2)

    closing = round(opening_value * (1 + quarter_return / 100.0)
                    + contribution - withdrawal, 2)

    return {
        "client_id": client_id, "period": period, "as_of": as_of,
        "portfolio_value": opening_value,
        "quarter_return_pct": quarter_return,
        "benchmark_return_pct": benchmark_return,
        "excess_return_pct": round(quarter_return - benchmark_return, 2),
        "volatility_pct": round(abs(rng.gauss(9.0, 2.2)), 2),
        "risk_level": RISK_BY_PERSONA[persona],
        "benchmark_name": BENCHMARK_NAME[RISK_BY_PERSONA[persona]],
        "holdings": holdings, "allocations": allocations,
        "attribution": attribution,
        "fees": {"advisory": advisory, "fund": fund},
        "cash_flows": {"contributions": float(contribution),
                       "withdrawals": float(withdrawal)},
        "closing_value": closing,
    }


# ---------------------------------------------------------------------------
# Verification — the generator must not be trusted, only checked
# ---------------------------------------------------------------------------

def verify(snap: dict) -> List[str]:
    problems = []
    alloc_total = round(sum(a["weight_pct"] for a in snap["allocations"]), 2)
    if abs(alloc_total - 100.0) > 0.01:
        problems.append(f"allocations sum to {alloc_total}, not 100")

    hold_total = round(sum(h["weight_pct"] for h in snap["holdings"]), 2)
    if abs(hold_total - 100.0) > 0.05:
        problems.append(f"holdings sum to {hold_total}, not 100")

    attr_total = round(sum(a["contribution_pct"] for a in snap["attribution"]), 2)
    if abs(attr_total - snap["quarter_return_pct"]) > 0.02:
        problems.append(f"attribution {attr_total} != return "
                        f"{snap['quarter_return_pct']}")

    for ac in snap["allocations"]:
        hw = round(sum(h["weight_pct"] for h in snap["holdings"]
                       if h["asset_class"] == ac["asset_class"]), 2)
        if abs(hw - ac["weight_pct"]) > 0.05:
            problems.append(f"{ac['asset_class']} holdings {hw} != "
                            f"class weight {ac['weight_pct']}")
    return problems


# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------

def write_rows(session, client_row: Client, snaps: List[dict]) -> None:
    session.merge(client_row)
    for s in snaps:
        sid = f"snap_{s['client_id']}_{s['period']}_v1"
        session.merge(ReportSnapshot(
            snapshot_id=sid, client_id=s["client_id"], period=s["period"],
            as_of_date=s["as_of"], version=1,
            portfolio_value=s["portfolio_value"], risk_level=s["risk_level"],
            source_version="synthetic-v1",
            created_at=datetime.strptime(s["as_of"], "%Y-%m-%d") + timedelta(days=5),
        ))
        for h in s["holdings"]:
            session.add(Holding(snapshot_id=sid, client_id=s["client_id"], **h))
        for a in s["allocations"]:
            session.add(Allocation(snapshot_id=sid, client_id=s["client_id"], **a))
        session.add(Performance(
            snapshot_id=sid, client_id=s["client_id"], period=s["period"],
            portfolio_return_pct=s["quarter_return_pct"],
            benchmark_name=s["benchmark_name"],
            benchmark_return_pct=s["benchmark_return_pct"],
            excess_return_pct=s["excess_return_pct"],
            volatility_pct=s["volatility_pct"]))
        for k, v in s["fees"].items():
            session.add(Fee(snapshot_id=sid, client_id=s["client_id"],
                            fee_type=k, amount=v))
        for k, v in s["cash_flows"].items():
            if v:
                session.add(CashFlow(snapshot_id=sid, client_id=s["client_id"],
                                     flow_type=k, amount=v))


def export_csv(snaps: List[dict], clients: Dict[str, Client], path: Path,
               period: str) -> int:
    """Emit one period as the advisor-upload CSV, so the existing ingest path
    is exercised by the same data the database holds."""
    rows = [s for s in snaps if s["period"] == period]
    asset_classes = sorted({a["asset_class"] for s in rows for a in s["allocations"]})
    drivers = asset_classes + ["Fees"]

    def col(prefix, name):
        return f"{prefix}_{name.lower().replace(' ', '_')}"

    header = (["client_id", "display_name", "email", "segment_id", "period",
               "as_of", "portfolio_value", "quarter_return_pct",
               "benchmark_return_pct", "risk_level"]
              + [col("alloc", a) for a in asset_classes]
              + [col("attr", d) for d in drivers]
              + ["fee_advisory", "fee_fund", "flow_contributions", "flow_withdrawals"])

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for s in rows:
            c = clients[s["client_id"]]
            alloc = {a["asset_class"]: a["weight_pct"] for a in s["allocations"]}
            attr = {a["driver"]: a["contribution_pct"] for a in s["attribution"]}
            w.writerow(
                [c.client_id, c.name, c.email, c.segment_id, s["period"], s["as_of"],
                 s["portfolio_value"], s["quarter_return_pct"],
                 s["benchmark_return_pct"], s["risk_level"]]
                + [alloc.get(a, 0.0) for a in asset_classes]
                + [attr.get(d, 0.0) for d in drivers]
                + [s["fees"]["advisory"], s["fees"]["fund"],
                   s["cash_flows"]["contributions"], s["cash_flows"]["withdrawals"]])
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true",
                    help="drop and recreate every table first")
    ap.add_argument("--csv", default="data/synthetic_2026Q2.csv",
                    help="also write this period as an upload CSV")
    ap.add_argument("--csv-period", default="2026Q2")
    args = ap.parse_args()

    print(f"database : {database_url()}")
    init_db(drop=args.reset)
    if args.reset:
        print("tables   : dropped and recreated")

    rng = random.Random(SEED)
    all_snaps: List[dict] = []
    clients: Dict[str, Client] = {}
    problems: List[str] = []

    with session_scope() as session:
        for i, (cid, name, persona, opening, contrib, withdraw) in enumerate(BOOK):
            slug = name.lower().replace(" ", ".").replace("'", "")
            client = Client(
                client_id=cid, name=name, email=f"{slug}@example.com",
                segment_id=persona, persona=persona,
                risk_profile=RISK_BY_PERSONA[persona],
                adviser=ADVISERS[i % len(ADVISERS)], status="active")
            clients[cid] = client

            value = float(opening)
            snaps = []
            for period, as_of in PERIODS:
                s = build_snapshot(cid, persona, period, as_of, value,
                                   contrib, withdraw, rng)
                bad = verify(s)
                problems += [f"{cid} {period}: {p}" for p in bad]
                snaps.append(s)
                value = s["closing_value"]     # compounds into the next quarter
            write_rows(session, client, snaps)
            all_snaps += snaps

            # Neutral starting preferences. Deliberately NOT pre-filled with
            # fabricated tendencies — a preference profile that was never
            # learned would make the adaptation look like it works when
            # nothing has been observed yet.
            session.merge(ClientPreference(client_id=cid,
                                           meaningful_signal_count=0))

    print(f"clients  : {len(BOOK)}")
    print(f"snapshots: {len(all_snaps)}  ({len(PERIODS)} quarters each)")
    print(f"holdings : {sum(len(s['holdings']) for s in all_snaps)}")

    if args.csv:
        n = export_csv(all_snaps, clients, ROOT / args.csv, args.csv_period)
        print(f"csv      : {args.csv}  ({n} rows, {args.csv_period})")

    print("\nCOHERENCE")
    if problems:
        print(f"  {len(problems)} PROBLEM(S):")
        for p in problems[:12]:
            print(f"    ! {p}")
        raise SystemExit(1)
    print(f"  ok  all {len(all_snaps)} snapshots reconcile "
          f"(weights=100, attribution=return, holdings=class weights)")

    print("\nBOOK")
    print(f"  {'client':<20}{'persona':<22}" +
          "".join(f"{p:>10}" for p, _ in PERIODS) + f"{'closing':>14}")
    for cid, name, persona, *_ in BOOK:
        rows = [s for s in all_snaps if s["client_id"] == cid]
        line = f"  {name:<20}{persona:<22}"
        line += "".join(f"{s['quarter_return_pct']:>9.2f}%" for s in rows)
        line += f"{rows[-1]['closing_value']:>14,.0f}"
        print(line)


if __name__ == "__main__":
    main()
