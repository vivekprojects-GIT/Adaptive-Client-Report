"""
Scheduled analytics recompute.

In production this should run on a schedule (cron, Windows Task Scheduler,
GitHub Actions cron, or any orchestrator) — NOT only when the admin clicks
"Recompute now" in the UI. The admin button stays for ad-hoc debugging.

Suggested cadence:
    every 1 hour   — last 24h window, keeps dashboard near-real-time
    nightly        — last 30 days window, full backfill

What it does:
    1. Reads raw events from ape_turn_record (last `days` days)
    2. Aggregates into ape_user_topic_interest + ape_topic_trend_daily
    3. Prints a one-line summary suitable for log scraping

Usage:
    # one-off
    python scripts/cron_recompute.py
    python scripts/cron_recompute.py --days 7

    # Linux/macOS cron — hourly recompute over 24h window
    0 * * * * cd /path/to/ape_modulor_production && /usr/bin/python scripts/cron_recompute.py --days 1

    # Linux/macOS cron — nightly full rebuild at 02:30
    30 2 * * * cd /path/to/ape_modulor_production && /usr/bin/python scripts/cron_recompute.py --days 30

    # Windows Task Scheduler — run hourly
    schtasks /create /tn "APE hourly recompute" /tr "python C:\\path\\to\\scripts\\cron_recompute.py --days 1" /sc HOURLY

Idempotent — safe to re-run; uses upsert keyed by (user_id_hash, topic) and
(date, topic).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from ape.analytics import compute_topic_trends, compute_user_topic_interest  # noqa: E402
from ape.store import MongoStore                                              # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Recompute APE analytics aggregates.")
    parser.add_argument("--days", type=int, default=14,
                        help="Lookback window for topic_trend_daily (default 14)")
    parser.add_argument("--quiet", action="store_true",
                        help="Print only the one-line summary on success")
    args = parser.parse_args()

    uri = os.environ.get("APE_MONGO_URI")
    db_name = os.environ.get("APE_MONGO_DB", "ape")
    if not uri:
        print("ERROR: APE_MONGO_URI not set", file=sys.stderr)
        return 1

    start = time.monotonic()
    store = MongoStore(uri=uri, db_name=db_name)

    # Compute for ALL users (omit user_id_hash filter)
    interest_n = compute_user_topic_interest(store)
    trend_n    = compute_topic_trends(store, days=args.days)

    elapsed = time.monotonic() - start
    ts = datetime.now(timezone.utc).isoformat()
    line = (
        f"recompute ok ts={ts} elapsed={elapsed:.2f}s "
        f"interest_rows={interest_n} trend_rows={trend_n} window_days={args.days}"
    )

    if args.quiet:
        print(line)
    else:
        print(f"APE analytics recompute @ {ts}")
        print(f"  window:                {args.days} days")
        print(f"  user_topic_interest:   {interest_n} rows")
        print(f"  topic_trend_daily:     {trend_n} rows")
        print(f"  elapsed:               {elapsed:.2f}s")
        print(line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
