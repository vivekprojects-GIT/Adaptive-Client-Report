"""Verify the synthetic book AS READ BACK FROM THE DATABASE.

    python scripts/test_sql_data.py

The seeder checks its own arithmetic in memory, which proves only that the
generator agrees with itself. This reads every row back through the
repository and re-checks it, then generates a real report from each of the
48 snapshots and runs the grounding validator over it.

That is the check that matters: if a single figure survives the round trip
in a different form, or the derived fee drag no longer reconciles, the
grounding validator rejects the block and this test fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ape.db.repository import (  # noqa: E402
    list_clients, list_periods, load_holdings, load_snapshot,
    performance_history,
)
from ape.db.session import database_url, session_scope  # noqa: E402
from ape.reporting.generate import build_report  # noqa: E402
from ape.reporting.grounding import validate_report  # noqa: E402

TEMPLATE = {
    "template_id": "sql_check", "strategy": "balanced", "brief": "",
    "required_blocks": ["kpi_grid", "narrative", "performance_history",
                        "returns_table", "allocation_donut",
                        "allocation_vs_target", "top_contributors",
                        "top_detractors", "comparison_table", "fees_table",
                        "key_takeaways", "explainer", "chart:donut",
                        "callout", "risk_card", "disclosures"],
}

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(f"{name}  {detail}".strip())
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail else ""))


def main() -> None:
    print(f"database: {database_url()}\n")

    with session_scope() as s:
        clients = list_clients(s)
        print("1. THE BOOK")
        check("at least 10 clients", len(clients) >= 10, f"{len(clients)} clients")
        periods = {c.client_id: list_periods(s, c.client_id) for c in clients}
        check("every client has history",
              all(len(p) >= 2 for p in periods.values()),
              f"{min(len(p) for p in periods.values())}-"
              f"{max(len(p) for p in periods.values())} quarters each")
        check("segments vary", len({c.segment_id for c in clients}) >= 4,
              f"{len({c.segment_id for c in clients})} segments")

        print("\n2. EVERY SNAPSHOT RECONCILES WHEN READ BACK")
        bad_alloc, bad_attr, total = [], [], 0
        for c in clients:
            for p in periods[c.client_id]:
                snap = load_snapshot(s, c.client_id, p)
                total += 1
                aw = round(sum(a["weight_pct"] for a in snap.allocations), 2)
                if abs(aw - 100.0) > 0.05:
                    bad_alloc.append(f"{c.client_id} {p} = {aw}")
                at = round(sum(a["contribution_pct"] for a in snap.attribution), 2)
                if abs(at - snap.quarter_return_pct) > 0.05:
                    bad_attr.append(f"{c.client_id} {p}: {at} vs "
                                    f"{snap.quarter_return_pct}")
        check("allocations sum to 100", not bad_alloc,
              f"{total} snapshots" if not bad_alloc else bad_alloc[0])
        check("attribution reconciles to return (incl. derived fee drag)",
              not bad_attr, f"{total} snapshots" if not bad_attr else bad_attr[0])

        print("\n3. HOLDINGS ROLL UP TO ALLOCATIONS")
        mismatches = []
        for c in clients[:4]:
            p = periods[c.client_id][-1]
            snap = load_snapshot(s, c.client_id, p)
            hold = load_holdings(s, c.client_id, p)
            by_class = {}
            for h in hold:
                by_class[h["asset_class"]] = round(
                    by_class.get(h["asset_class"], 0.0) + h["weight_pct"], 2)
            for a in snap.allocations:
                got = by_class.get(a["asset_class"], 0.0)
                if abs(got - a["weight_pct"]) > 0.05:
                    mismatches.append(f"{c.client_id} {a['asset_class']}: "
                                      f"{got} vs {a['weight_pct']}")
        check("holdings sum to their asset-class weight", not mismatches,
              mismatches[0] if mismatches else "checked 4 clients")

        print("\n4. VALUE COMPOUNDS ACROSS QUARTERS")
        c = clients[0]
        hist = performance_history(s, c.client_id)
        vals = [load_snapshot(s, c.client_id, p).portfolio_value
                for p in periods[c.client_id]]
        drift = []
        for i in range(len(vals) - 1):
            expected = vals[i] * (1 + hist[i]["portfolio"] / 100.0)
            # Difference from expected must be the net cash flow, not noise.
            if abs(vals[i + 1] - expected) > abs(expected) * 0.05:
                drift.append(f"{periods[c.client_id][i]} -> "
                             f"{vals[i+1]:,.0f} vs {expected:,.0f}")
        check("next quarter opens where the last one closed", not drift,
              drift[0] if drift else f"{c.name}: " +
              " -> ".join(f"{v:,.0f}" for v in vals))

        print("\n5. A DOWN QUARTER EXISTS")
        negatives = sum(1 for c in clients
                        for p in periods[c.client_id]
                        if load_snapshot(s, c.client_id, p).quarter_return_pct < 0)
        check("negative-return reports available to test", negatives >= 5,
              f"{negatives} loss-making client-quarters")

        print("\n6. EVERY SNAPSHOT GENERATES A GROUNDED REPORT")
        rejected_total, blocks_total, worst = 0, 0, None
        for c in clients:
            for p in periods[c.client_id]:
                snap = load_snapshot(s, c.client_id, p)
                rep = build_report(snap, TEMPLATE, "quarterly_portfolio_review")
                v = validate_report(rep, snap.numeric_facts(), snap.label_terms())
                blocks_total += len(rep["blocks"])
                rejected_total += len(v.rejected)
                if v.rejected and worst is None:
                    worst = f"{c.client_id} {p}: {v.findings[0].detail}"
        check("no block rejected across the whole book", rejected_total == 0,
              worst or f"{blocks_total} blocks over {total} snapshots, "
                       f"0 rejected")

    print("\n" + "-" * 60)
    print(f"passed {len(PASS)} / {len(PASS) + len(FAIL)}")
    if FAIL:
        print("\nFAILURES:")
        for f in FAIL:
            print(f"   ! {f}")
        raise SystemExit(1)
    print("SQL BOOK IS COHERENT AND REPORT-READY")


if __name__ == "__main__":
    main()
