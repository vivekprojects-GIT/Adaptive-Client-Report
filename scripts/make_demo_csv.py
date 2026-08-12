"""Generate an upload-ready CSV for the real demo recipients.

    python scripts/make_demo_csv.py --out data/demo_clients.csv

Rows are built with the same bottom-up generator the synthetic book uses,
so every row reconciles: allocations total exactly 100, attribution
(including the fee drag) sums to the stated return. A hand-written CSV
almost never satisfies both, and the importer rejects rows that don't.

Each recipient gets a different persona so the generated reports differ
visibly — useful when showing several people the same system.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ape.db.models import Client  # noqa: E402
from scripts.seed_sql_synthetic import (  # noqa: E402
    ADVISERS, PERIODS, RISK_BY_PERSONA, build_snapshot, export_csv, verify,
)

# (client_id, name, email, persona, opening value, contribution, withdrawal)
BOOK = [
    ("C2001", "Rajesh Rangarajan", "rajesh.k-rangarajan@capgemini.com",
     "growth_equity",       2_150_000, 10_000,      0),
    ("C2002", "Sai Vivek Katkuri", "sai-vivek.katkuri@capgemini.com",
     "balanced_growth",     1_480_000,  6_500,      0),
    ("C2003", "Vivek Katkuri",     "saivivek0192@gmail.com",
     "aggressive_growth",   3_260_000, 18_000,      0),
    ("C2004", "S V Katkuri",       "saivivekkatkuri@gmail.com",
     "conservative_income",   920_000,      0,  4_000),
    # Matches the client already created via add_client.py, so re-importing
    # updates that record instead of creating a duplicate person.
    ("C1013", "Ruthuhasa",         "ruthuhasa03@gmail.com",
     "retirement_drawdown", 1_450_000,      0,  8_000),
    ("C2005", "Sachin Singh",      "sachin.a.singh@capgemini.com",
     "esg_tilt",            1_760_000,  7_500,      0),
    ("C2006", "Kamraj Mani",       "kamraj.mani@capgemini.com",
     "balanced_growth",     2_640_000, 11_000,      0),
    ("C2007", "Sudhanshu Singh",   "sudhanshu-kumar.singh@capgemini.com",
     "growth_equity",         840_000,  4_500,      0),
    ("C2008", "Riya Varghese",     "riya.a.varghese@capgemini.com",
     "conservative_income", 1_180_000,      0,  5_500),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/demo_clients.csv")
    ap.add_argument("--period", default="2026Q2",
                    help="a CSV carries ONE period; upload one per quarter "
                         "to build history")
    args = ap.parse_args()

    as_of = dict(PERIODS).get(args.period)
    if as_of is None:
        sys.exit(f"unknown period '{args.period}'; "
                 f"expected one of {[p for p, _ in PERIODS]}")

    snaps, clients, problems = [], {}, []
    for i, (cid, name, email, persona, value, contrib, withdraw) in enumerate(BOOK):
        # Seeded per client so the file is identical on every run.
        rng = random.Random(sum(ord(c) for c in cid))
        # Walk from the first period so this quarter's opening value is the
        # product of real prior performance, not an arbitrary number.
        v = float(value)
        snap = None
        for period, when in PERIODS:
            snap = build_snapshot(cid, persona, period, when, v,
                                  contrib, withdraw, rng)
            if period == args.period:
                break
            v = snap["closing_value"]
        problems += [f"{cid}: {p}" for p in verify(snap)]
        snaps.append(snap)
        clients[cid] = Client(
            client_id=cid, name=name, email=email, segment_id=persona,
            persona=persona, risk_profile=RISK_BY_PERSONA[persona],
            adviser=ADVISERS[i % len(ADVISERS)], status="active")

    if problems:
        print("REFUSING — rows do not reconcile:")
        for p in problems[:5]:
            print("   !", p)
        raise SystemExit(1)

    out = ROOT / args.out
    n = export_csv(snaps, clients, out, args.period)
    print(f"{out}  ({n} rows, {args.period})\n")
    for (cid, name, email, persona, *_), s in zip(BOOK, snaps):
        print(f"  {cid}  {name:<19} {email:<36} {persona:<20} "
              f"{s['quarter_return_pct']:+.2f}%")


if __name__ == "__main__":
    main()
