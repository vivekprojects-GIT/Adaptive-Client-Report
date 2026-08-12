"""Add one client with a full, coherent history.

    python scripts/add_client.py --id C1013 --name "Ruthuhasa" \
        --email someone@example.com --persona balanced_growth --value 1450000

A bare client row is not enough to report on: the depth blocks need
holdings, prior quarters and strategic targets, and the grounding
validator will drop anything those cannot evidence. So this reuses the
synthetic generator's build_snapshot — the same bottom-up arithmetic that
guarantees allocations total 100, attribution reconciles to the stated
return, and value compounds across quarters.

The advisor's real path is a CSV upload; this exists for adding a single
client to a running demo without rebuilding the book.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ape.db.models import Client  # noqa: E402
from ape.db.session import init_db, session_scope  # noqa: E402
from scripts.seed_sql_synthetic import (  # noqa: E402
    ADVISERS, PERIODS, PERSONAS, RISK_BY_PERSONA, build_snapshot, verify,
    write_rows,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--email", required=True)
    ap.add_argument("--persona", default="balanced_growth",
                    choices=sorted(PERSONAS))
    ap.add_argument("--value", type=float, default=1_400_000.0,
                    help="opening portfolio value at the first period")
    ap.add_argument("--contribution", type=float, default=5_000.0)
    ap.add_argument("--withdrawal", type=float, default=0.0)
    args = ap.parse_args()

    if "@" not in args.email:
        sys.exit(f"'{args.email}' is not an email address")

    init_db()
    # Seeded from the client id, so re-running produces the same history
    # rather than silently rewriting the client's past.
    rng = random.Random(sum(ord(c) for c in args.id))

    client = Client(
        client_id=args.id, name=args.name, email=args.email,
        segment_id=args.persona, persona=args.persona,
        risk_profile=RISK_BY_PERSONA[args.persona],
        adviser=ADVISERS[0], status="active")

    value, snaps, problems = args.value, [], []
    for period, as_of in PERIODS:
        s = build_snapshot(args.id, args.persona, period, as_of, value,
                           args.contribution, args.withdrawal, rng)
        problems += [f"{period}: {p}" for p in verify(s)]
        snaps.append(s)
        value = s["closing_value"]

    if problems:
        print("REFUSING — generated history does not reconcile:")
        for p in problems[:5]:
            print("   !", p)
        raise SystemExit(1)

    with session_scope() as db:
        existing = db.get(Client, args.id)
        if existing is not None:
            print(f"note: {args.id} exists ({existing.name}) — updating")
        write_rows(db, client, snaps)

    print(f"{args.name} <{args.email}>")
    print(f"  id       {args.id}")
    print(f"  segment  {args.persona} ({RISK_BY_PERSONA[args.persona]})")
    print(f"  periods  {len(snaps)}  "
          + "  ".join(f"{s['period']} {s['quarter_return_pct']:+.2f}%"
                      for s in snaps))
    print(f"  value    {args.value:,.0f} -> {snaps[-1]['closing_value']:,.0f}")
    print("  all snapshots reconcile")


if __name__ == "__main__":
    main()
