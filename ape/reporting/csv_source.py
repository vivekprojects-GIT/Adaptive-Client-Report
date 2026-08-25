"""CSV ingest — the data source for report generation.

An advisor uploads one CSV. Each ROW is one client, and carries both the
delivery details (email) and the frozen portfolio facts for the period. One
upload therefore produces one report per row.

═══════════════════════════════════════════════════════════════════════════
EXPECTED COLUMNS
═══════════════════════════════════════════════════════════════════════════

  identity     client_id, display_name, email, segment_id
  period       period, as_of
  headline     portfolio_value, quarter_return_pct, benchmark_return_pct,
               risk_level
  allocation   alloc_<asset_class>          e.g. alloc_us_equity
  attribution  attr_<driver>                e.g. attr_us_equity
  fees         fee_advisory, fee_fund
  flows        flow_contributions, flow_withdrawals

The alloc_/attr_ prefixes are read dynamically, so a firm can add asset
classes without a code change.

═══════════════════════════════════════════════════════════════════════════
WHY VALIDATION IS STRICT
═══════════════════════════════════════════════════════════════════════════

Every figure in every generated report is grounded against this snapshot.
If the CSV itself is internally inconsistent — allocations that sum to 97%,
attribution that does not reconcile to the stated return — then the report
will faithfully reproduce incoherent numbers and look correct while being
wrong. Rows that do not reconcile are REJECTED with a reason rather than
silently generated, because a plausible-looking wrong report is worse than
no report.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

REQUIRED_COLUMNS = (
    "client_id", "display_name", "email", "period",
    "portfolio_value", "quarter_return_pct", "benchmark_return_pct",
)

# Allocation weights must sum to ~100 and attribution must reconcile to the
# stated return. Tolerance allows for values rounded to 1dp in the source.
ALLOC_TOLERANCE = 0.6
ATTR_TOLERANCE = 0.35


@dataclass
class RowError:
    row_number: int
    client_id: str
    problems: List[str] = field(default_factory=list)


@dataclass
class ClientSnapshot:
    """One client's frozen facts for one period. Immutable once built."""

    client_id: str
    display_name: str
    email: str
    segment_id: str
    period: str
    as_of: str

    portfolio_value: float
    quarter_return_pct: float
    benchmark_return_pct: float
    risk_level: str

    allocations: List[Dict[str, Any]]
    attribution: List[Dict[str, Any]]
    fees: Dict[str, float]
    cash_flows: Dict[str, float]

    # ── Optional depth, present when the source can supply it ──────────────
    # A CSV upload carries asset classes for one period. A database-backed
    # snapshot also carries individual holdings, prior quarters and the
    # strategic targets. Blocks that need this detail return None when it is
    # absent rather than inventing it, so the same template degrades to the
    # thinner report instead of producing a fabricated one.
    holdings: List[Dict[str, Any]] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)
    targets: Dict[str, float] = field(default_factory=dict)
    # Which language this client reads. Drives BOTH the words and the
    # number separators, so it travels with the facts rather than being
    # looked up separately at each use — a snapshot that formats its own
    # figures one way and validates them another is the failure mode.
    language: str = ""
    benchmark_name: str = ""
    volatility_pct: Optional[float] = None

    @property
    def snapshot_id(self) -> str:
        return f"snap_{self.client_id}_{self.period}_v1"

    @property
    def excess_return_pct(self) -> float:
        return round(self.quarter_return_pct - self.benchmark_return_pct, 2)

    def numeric_facts(self) -> Dict[str, float]:
        """THE GROUNDING ALLOWLIST — every number a report may legitimately
        state. Anything else is rejected before render."""
        f: Dict[str, float] = {
            "portfolio_value":      self.portfolio_value,
            "quarter_return_pct":   self.quarter_return_pct,
            "benchmark_return_pct": self.benchmark_return_pct,
            "excess_return_pct":    self.excess_return_pct,
            "fees.advisory":        self.fees.get("advisory", 0.0),
            "fees.fund":            self.fees.get("fund", 0.0),
            "fees.total":           round(self.fees.get("advisory", 0.0)
                                          + self.fees.get("fund", 0.0), 2),
            "flows.contributions":  self.cash_flows.get("contributions", 0.0),
            "flows.withdrawals":    self.cash_flows.get("withdrawals", 0.0),
            "flows.net":            round(self.cash_flows.get("contributions", 0.0)
                                          - self.cash_flows.get("withdrawals", 0.0), 2),
        }
        # Fee drag as a percentage, stated positively. Attribution carries it
        # as a negative contribution; a takeaway naturally says "fees cost
        # 0.28%", and both renderings must be groundable.
        if self.portfolio_value:
            f["fees.drag_pct"] = round(f["fees.total"] / self.portfolio_value * 100.0, 2)

        for a in self.allocations:
            f[f"alloc.{a['asset_class']}"] = a["weight_pct"]
        for a in self.attribution:
            f[f"attr.{a['driver']}"] = a["contribution_pct"]

        for ac, w in (self.targets or {}).items():
            f[f"target.{ac}"] = w
            if f"alloc.{ac}" in f:
                f[f"drift.{ac}"] = round(f[f"alloc.{ac}"] - w, 2)

        for h in (self.holdings or []):
            key = h.get("symbol") or h.get("name")
            f[f"hold.{key}.weight"] = h.get("weight_pct", 0.0)
            f[f"hold.{key}.value"] = h.get("value", h.get("market_value", 0.0))
            f[f"hold.{key}.return"] = h.get("return_pct", 0.0)
            f[f"hold.{key}.contribution"] = h.get("contribution_pct", 0.0)

        cumulative = 1.0
        for row in (self.history or []):
            f[f"hist.{row['period']}.portfolio"] = row.get("portfolio", 0.0)
            f[f"hist.{row['period']}.benchmark"] = row.get("benchmark", 0.0)
            f[f"hist.{row['period']}.excess"] = row.get("excess", 0.0)
            cumulative *= 1 + row.get("portfolio", 0.0) / 100.0
        if self.history:
            f["hist.cumulative"] = round((cumulative - 1) * 100.0, 2)
            bench_cum = 1.0
            for row in self.history:
                bench_cum *= 1 + row.get("benchmark", 0.0) / 100.0
            f["hist.cumulative_benchmark"] = round((bench_cum - 1) * 100.0, 2)

        if self.volatility_pct is not None:
            f["volatility_pct"] = self.volatility_pct
        return f

    def label_terms(self) -> List[str]:
        """Proper names that contain digits.

        "60/40 Balanced Composite" and "S&P 500" are names this firm gave
        these things, not figures a report is claiming. Without listing them
        the validator reads the 60, the 40 and the 500 as unsourced numbers
        and rejects a correct sentence. Only names carrying digits are
        returned — the rest cannot cause a false match.
        """
        candidates = [self.benchmark_name]
        candidates += [a["asset_class"] for a in self.allocations]
        for h in (self.holdings or []):
            candidates += [str(h.get("name", "")), str(h.get("symbol", ""))]
        return sorted({c for c in candidates if c and any(ch.isdigit() for ch in c)},
                      key=len, reverse=True)


def _num(raw: Any, default: Optional[float] = None) -> Optional[float]:
    """Parse a CSV cell into a number, tolerating currency and thousands
    separators. Returns None when unparseable so the caller can report it
    rather than silently coercing to zero — a fee of 0 and a fee we could
    not read are very different things."""
    if raw is None:
        return default
    s = str(raw).strip().replace(",", "").replace("$", "").replace("£", "").replace("%", "")
    if s == "":
        return default
    try:
        return float(s)
    except ValueError:
        return None


def _pretty(key: str) -> str:
    return key.replace("_", " ").title()


def parse_csv(text: str) -> Tuple[List[ClientSnapshot], List[RowError]]:
    """Parse an uploaded CSV. Returns (valid snapshots, rejected rows)."""
    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip() for h in (reader.fieldnames or [])]

    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        return [], [RowError(0, "-", [f"missing required columns: {', '.join(missing)}"])]

    alloc_cols = [h for h in headers if h.startswith("alloc_")]
    attr_cols = [h for h in headers if h.startswith("attr_")]

    good: List[ClientSnapshot] = []
    bad: List[RowError] = []

    for i, raw in enumerate(reader, start=2):   # row 1 is the header
        row = {k.strip(): (v or "").strip() for k, v in raw.items() if k}
        cid = row.get("client_id", "").strip()
        problems: List[str] = []

        if not cid:
            problems.append("client_id is empty")
        email = row.get("email", "").strip()
        if "@" not in email:
            problems.append(f"email looks invalid: {email!r}")

        pv = _num(row.get("portfolio_value"))
        qr = _num(row.get("quarter_return_pct"))
        br = _num(row.get("benchmark_return_pct"))
        for name, val in (("portfolio_value", pv), ("quarter_return_pct", qr),
                          ("benchmark_return_pct", br)):
            if val is None:
                problems.append(f"{name} is missing or not a number")

        allocations = []
        for c in alloc_cols:
            v = _num(row.get(c))
            if v is None:
                problems.append(f"{c} is not a number")
            else:
                allocations.append({"asset_class": _pretty(c[len("alloc_"):]),
                                    "weight_pct": round(v, 2)})
        if allocations:
            total = round(sum(a["weight_pct"] for a in allocations), 2)
            if abs(total - 100.0) > ALLOC_TOLERANCE:
                problems.append(f"allocations sum to {total}%, expected 100%")
        else:
            # A row with no alloc_ columns passed every other check and
            # produced a report of zeros: no holdings, no allocation, every
            # figure 0.00. A client must never receive that, and the
            # importer is the right place to stop it — refusing here costs
            # one rejected row, refusing later costs a sent report.
            problems.append("no alloc_* columns — a report cannot be built "
                            "from a row with no allocation")

        attribution = []
        for c in attr_cols:
            v = _num(row.get(c))
            if v is None:
                problems.append(f"{c} is not a number")
            else:
                attribution.append({"driver": _pretty(c[len("attr_"):]),
                                    "contribution_pct": round(v, 2)})
        if attribution and qr is not None:
            total = round(sum(a["contribution_pct"] for a in attribution), 2)
            if abs(total - qr) > ATTR_TOLERANCE:
                problems.append(
                    f"attribution sums to {total}% but quarter_return_pct is {qr}%"
                )

        if problems:
            bad.append(RowError(i, cid or f"row {i}", problems))
            continue

        good.append(ClientSnapshot(
            client_id=cid,
            display_name=row.get("display_name") or cid,
            email=email,
            segment_id=row.get("segment_id") or "unsegmented",
            period=row.get("period") or "unknown",
            as_of=row.get("as_of") or "",
            portfolio_value=round(pv, 2),
            quarter_return_pct=round(qr, 2),
            benchmark_return_pct=round(br, 2),
            risk_level=row.get("risk_level") or "Moderate",
            allocations=allocations,
            attribution=attribution,
            fees={"advisory": _num(row.get("fee_advisory"), 0.0) or 0.0,
                  "fund": _num(row.get("fee_fund"), 0.0) or 0.0},
            cash_flows={"contributions": _num(row.get("flow_contributions"), 0.0) or 0.0,
                        "withdrawals": _num(row.get("flow_withdrawals"), 0.0) or 0.0},
        ))

    return good, bad
