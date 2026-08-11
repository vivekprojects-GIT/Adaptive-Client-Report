"""Reads that turn relational rows back into a ClientSnapshot.

The report pipeline takes a `ClientSnapshot` and knows nothing about where it
came from — CSV upload or database. Keeping that single shape means the
grounding validator, block builders and renderer are unchanged by the move
to SQL, and a CSV-sourced report and a database-sourced one are validated
against exactly the same allowlist.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ape.db.models import (
    Allocation, CashFlow, Client, Fee, Holding, Performance, ReportSnapshot,
)
from ape.reporting.csv_source import ClientSnapshot


def list_clients(session: Session) -> List[Client]:
    return list(session.scalars(select(Client).order_by(Client.client_id)))


def list_periods(session: Session, client_id: str) -> List[str]:
    return list(session.scalars(
        select(ReportSnapshot.period)
        .where(ReportSnapshot.client_id == client_id)
        .order_by(ReportSnapshot.period)))


def latest_period(session: Session, client_id: str) -> Optional[str]:
    periods = list_periods(session, client_id)
    return periods[-1] if periods else None


def load_snapshot(session: Session, client_id: str,
                  period: Optional[str] = None) -> ClientSnapshot:
    """Rebuild one client's frozen facts for one period.

    `period=None` means the most recent snapshot on file.
    """
    period = period or latest_period(session, client_id)
    if not period:
        raise LookupError(f"no snapshots for client {client_id}")

    snap = session.scalars(
        select(ReportSnapshot)
        .where(ReportSnapshot.client_id == client_id,
               ReportSnapshot.period == period)
        .order_by(ReportSnapshot.version.desc())).first()
    if snap is None:
        raise LookupError(f"no snapshot for {client_id} {period}")

    client = session.get(Client, client_id)
    if client is None:
        raise LookupError(f"no client {client_id}")

    perf = session.scalars(
        select(Performance).where(Performance.snapshot_id == snap.snapshot_id)).first()
    allocs = list(session.scalars(
        select(Allocation).where(Allocation.snapshot_id == snap.snapshot_id)
        .order_by(Allocation.weight_pct.desc())))
    fees = {f.fee_type: f.amount for f in session.scalars(
        select(Fee).where(Fee.snapshot_id == snap.snapshot_id))}
    flows = {c.flow_type: c.amount for c in session.scalars(
        select(CashFlow).where(CashFlow.snapshot_id == snap.snapshot_id))}

    attribution = [{"driver": a.asset_class, "contribution_pct": a.contribution_pct}
                   for a in allocs]

    # Fee drag is derived, not stored. Storing it would create a second
    # copy of a number that is fully determined by `fees` and
    # `portfolio_value`, and the two copies could then disagree.
    fee_total = round(sum(fees.values()), 2)
    if snap.portfolio_value:
        attribution.append({
            "driver": "Fees",
            "contribution_pct": -round(fee_total / snap.portfolio_value * 100.0, 2),
        })

    holdings = [
        {"symbol": h.symbol, "name": h.name, "asset_class": h.asset_class,
         "weight_pct": h.weight_pct, "value": h.market_value,
         "return_pct": h.return_pct, "contribution_pct": h.contribution_pct}
        for h in session.scalars(
            select(Holding).where(Holding.snapshot_id == snap.snapshot_id)
            .order_by(Holding.weight_pct.desc()))]

    # History stops at the period being reported. A Q1 report regenerated
    # today must not show a Q2 line that did not exist when it was written.
    history = [
        {"period": p.period, "portfolio": p.portfolio_return_pct,
         "benchmark": p.benchmark_return_pct, "excess": p.excess_return_pct}
        for p in session.scalars(
            select(Performance)
            .where(Performance.client_id == client_id,
                   Performance.period <= period)
            .order_by(Performance.period))]

    return ClientSnapshot(
        client_id=client.client_id,
        display_name=client.name,
        email=client.email,
        segment_id=client.segment_id,
        period=snap.period,
        as_of=snap.as_of_date,
        portfolio_value=snap.portfolio_value,
        quarter_return_pct=perf.portfolio_return_pct if perf else 0.0,
        benchmark_return_pct=perf.benchmark_return_pct if perf else 0.0,
        risk_level=snap.risk_level,
        allocations=[{"asset_class": a.asset_class, "weight_pct": a.weight_pct}
                     for a in allocs],
        attribution=attribution,
        fees={"advisory": fees.get("advisory", 0.0), "fund": fees.get("fund", 0.0)},
        cash_flows={"contributions": flows.get("contributions", 0.0),
                    "withdrawals": flows.get("withdrawals", 0.0)},
        holdings=holdings,
        history=history,
        targets={a.asset_class: a.target_weight_pct for a in allocs
                 if a.target_weight_pct},
        benchmark_name=perf.benchmark_name if perf else "",
        volatility_pct=perf.volatility_pct if perf else None,
    )


def load_holdings(session: Session, client_id: str, period: str) -> List[Dict]:
    """Holdings for the holdings_table block, heaviest first."""
    sid = f"snap_{client_id}_{period}_v1"
    rows = session.scalars(
        select(Holding).where(Holding.snapshot_id == sid)
        .order_by(Holding.weight_pct.desc()))
    return [{"symbol": h.symbol, "name": h.name, "asset_class": h.asset_class,
             "weight_pct": h.weight_pct, "value": h.market_value,
             "return_pct": h.return_pct} for h in rows]


def performance_history(session: Session, client_id: str) -> List[Dict]:
    """Every quarter on file — the input to a multi-period trend block."""
    rows = session.scalars(
        select(Performance).where(Performance.client_id == client_id)
        .order_by(Performance.period))
    return [{"period": p.period, "portfolio": p.portfolio_return_pct,
             "benchmark": p.benchmark_return_pct,
             "excess": p.excess_return_pct} for p in rows]
