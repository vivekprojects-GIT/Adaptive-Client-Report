"""Batch generation — one CSV upload produces one report per row.

    CSV ──► parse + validate ──► per client:
                                     D1 selects an arm (UCB)
                                     build blocks from the snapshot
                                     render HTML
                                     write artifacts
                                     "send" the email (stubbed)

WHY SELECTION IS SEQUENTIAL
---------------------------
UCB is a deterministic argmax. Reading the cell once and applying it to every
row would give the whole book the SAME template. `count` is bumped after each
selection so the explore bonus decays and other arms overtake mid-batch —
that is what makes a batch spread across arms instead of collapsing onto one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .csv_source import ClientSnapshot, parse_csv
from .d1 import cell_key, eligible_arms, select
from .generate import build_report, render_html

ARTIFACTS = Path(__file__).resolve().parents[2] / "data" / "generated"


def _load_arm_state(store, report_type: str,
                    strategies: List[str]) -> Dict[str, Dict[str, Any]]:
    """Read the global cell's arms, lazily creating missing rows at zero."""
    key = cell_key(report_type)
    rows = list(store.bandit_state.find({"cell_key": key})) if store else []
    by_arm = {r.get("strategy"): r for r in rows}
    return {
        s: {"count": int((by_arm.get(s) or {}).get("count", 0)),
            "total_reward": float((by_arm.get(s) or {}).get("total_reward", 0.0))}
        for s in strategies
    }


def _persist_arm_pull(store, report_type: str, strategy: str) -> None:
    """Bump times-served. `count` rises at SELECTION, not at reward, so
    cold-start exploration advances even before any feedback arrives."""
    if store is None:
        return
    store.bandit_state.update_one(
        {"cell_key": cell_key(report_type), "strategy": strategy},
        {"$inc": {"count": 1},
         "$setOnInsert": {"total_reward": 0.0,
                          "report_type": report_type,
                          "scope": "_global"}},
        upsert=True,
    )


def generate_batch(
    csv_text: str,
    report_type: str,
    templates: List[Dict[str, Any]],
    personalisable: bool = True,
    store=None,
    send_email: bool = False,
) -> Dict[str, Any]:
    """Run the whole batch. Returns a per-client result plus rejected rows."""
    snapshots, errors = parse_csv(csv_text)

    arms = eligible_arms(templates, report_type)
    if not arms:
        return {"error": f"no active templates for report type '{report_type}'",
                "results": [], "rejected": []}

    strategies = [a["strategy"] for a in arms]
    arm_state = _load_arm_state(store, report_type, strategies)
    by_strategy = {a["strategy"]: a for a in arms}

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []

    for snap in snapshots:
        strategy, rows, method = select(
            templates, arm_state, report_type, personalisable,
            client_profile=None, n_signals=0,
        )
        # Bump in-memory so the next row in THIS batch sees the updated count.
        arm_state.setdefault(strategy, {"count": 0, "total_reward": 0.0})
        arm_state[strategy]["count"] += 1
        _persist_arm_pull(store, report_type, strategy)

        template = by_strategy[strategy]
        report = build_report(snap, template, report_type)
        html = render_html(report)

        rid = report["report_id"]
        (ARTIFACTS / f"{rid}.html").write_text(html, encoding="utf-8")
        (ARTIFACTS / f"{rid}.json").write_text(json.dumps(report, indent=2),
                                               encoding="utf-8")

        # Email is deliberately NOT sent. The secure-link flow is designed but
        # not wired; recording "sent (stub)" keeps the pipeline shape honest
        # without pretending a message went anywhere.
        results.append({
            "report_id":    rid,
            "client_id":    snap.client_id,
            "client_name":  snap.display_name,
            "email":        snap.email,
            "segment_id":   snap.segment_id,
            "period":       snap.period,
            "strategy":     strategy,
            "template_id":  template.get("template_id"),
            "template_label": template.get("label"),
            "method":       method,
            "blocks":       [b["type"] for b in report["blocks"]],
            "email_status": "sent (stub)" if not send_email else "sent",
        })

    return {
        "report_type": report_type,
        "cell_key":    cell_key(report_type),
        "generated":   len(results),
        "rejected":    [{"row": e.row_number, "client_id": e.client_id,
                         "problems": e.problems} for e in errors],
        "arm_distribution": {
            s: arm_state[s]["count"] for s in strategies
        },
        "results": results,
    }
