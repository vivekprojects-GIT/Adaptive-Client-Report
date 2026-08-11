"""The report source data model.

═══════════════════════════════════════════════════════════════════════════
WHY THIS EXISTS, AND WHY IT IS STRICT
═══════════════════════════════════════════════════════════════════════════

A `PortfolioSnapshot` is the *frozen* set of facts one report is written from.
Two things depend on it being right:

1. **Grounding.** Every number the LLM writes — in prose and in charts — must
   trace back to a value in this snapshot. `numeric_facts()` is the allowlist
   the validator checks against. If a figure is not in there, it does not
   appear in a client document.

2. **Style-independence.** The same snapshot must be renderable as a chart-led,
   table-led, or narrative report and produce *identical figures*. That is the
   Phase 1 milestone. It only holds if the snapshot is the single source.

Because of (1), the arithmetic has to close. If allocation weights sum to
99.7% or contributions do not sum to the stated portfolio return, the LLM
will faithfully reproduce incoherent numbers and the report will be wrong in a
way that looks right. `validate()` enforces coherence and is called on
construction — a snapshot that does not add up cannot be created.

ROUNDING POLICY
---------------
Everything a client sees is rounded, so we round *first* and derive the
totals from the rounded parts, rather than rounding a full-precision total.
This means `portfolio_return_pct` is defined as the sum of the rounded
per-sleeve contributions — the report can state both and they agree exactly.
The alternative (round independently) produces documents where the parts
visibly do not sum to the whole, which is the fastest way to lose a client's
trust in the whole system.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

# Tolerance for float comparison in coherence checks. Values are rounded to
# 2dp (currency) or 1dp (percentages) before summing, so anything beyond this
# is a real error rather than representation noise.
_EPS = 0.011


class SnapshotCoherenceError(ValueError):
    """Raised when a snapshot's figures do not add up.

    This is deliberately fatal. A snapshot that fails here would produce a
    client document whose parts contradict its totals.
    """


# ---------------------------------------------------------------------------
# Leaf records
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Client:
    client_id: str
    display_name: str
    persona: str            # see synthetic.PERSONAS
    risk_profile: str       # Cautious | Balanced | Growth
    adviser_name: str
    currency: str = "GBP"


@dataclass(frozen=True)
class Period:
    label: str              # "Q3 2026"
    start_date: str         # ISO date, inclusive
    end_date: str           # ISO date, inclusive


@dataclass(frozen=True)
class AssetClassLine:
    """One sleeve of the portfolio.

    `contribution_pct` is weight × return, i.e. how much of the total
    portfolio return this sleeve produced. The sleeve contributions sum to
    `Performance.portfolio_return_pct`.
    """
    asset_class: str
    weight_pct: float           # % of closing value
    opening_value: float
    closing_value: float
    return_pct: float           # the sleeve's own return over the period
    contribution_pct: float     # contribution to total portfolio return


@dataclass(frozen=True)
class Holding:
    name: str
    asset_class: str
    weight_pct: float           # % of closing value
    value: float
    return_pct: float


@dataclass(frozen=True)
class Performance:
    portfolio_return_pct: float
    benchmark_name: str
    benchmark_return_pct: float
    excess_return_pct: float        # portfolio - benchmark
    selection_effect_pct: float     # from picking within asset classes
    allocation_effect_pct: float    # from over/under-weighting classes


@dataclass(frozen=True)
class Flows:
    contributions: float
    withdrawals: float          # positive number, money leaving
    net_flow: float             # contributions - withdrawals
    income_received: float      # dividends/interest credited


@dataclass(frozen=True)
class Fees:
    management_fee: float
    fund_costs: float
    total_fees: float
    total_fees_pct: float       # of closing value


@dataclass(frozen=True)
class Risk:
    volatility_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float     # negative number


# ---------------------------------------------------------------------------
# The snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PortfolioSnapshot:
    """Everything one report may state. Nothing outside this is permitted."""

    client: Client
    period: Period

    opening_value: float
    closing_value: float
    investment_gain: float          # closing - opening - net_flow

    performance: Performance
    allocation: List[AssetClassLine]
    top_holdings: List[Holding]
    flows: Flows
    fees: Fees
    risk: Risk

    # Set by validate(); recorded so a report can cite the snapshot it used.
    schema_version: str = "1.0"
    extras: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    # -- coherence ---------------------------------------------------------

    def validate(self) -> None:
        """Assert the figures add up. Raises SnapshotCoherenceError."""
        problems: List[str] = []

        # 1. Allocation weights sum to 100%.
        wsum = round(sum(a.weight_pct for a in self.allocation), 4)
        if abs(wsum - 100.0) > _EPS:
            problems.append(f"allocation weights sum to {wsum}, expected 100.0")

        # 2. Sleeve contributions sum to the portfolio return.
        csum = round(sum(a.contribution_pct for a in self.allocation), 4)
        if abs(csum - self.performance.portfolio_return_pct) > _EPS:
            problems.append(
                f"contributions sum to {csum}, but portfolio_return_pct is "
                f"{self.performance.portfolio_return_pct}"
            )

        # 3. Sleeve closing values sum to the portfolio closing value.
        vsum = round(sum(a.closing_value for a in self.allocation), 2)
        if abs(vsum - self.closing_value) > _EPS:
            problems.append(
                f"sleeve closing values sum to {vsum}, but closing_value is "
                f"{self.closing_value}"
            )

        # 4. closing = opening + net_flow + investment_gain
        expected_close = round(
            self.opening_value + self.flows.net_flow + self.investment_gain, 2
        )
        if abs(expected_close - self.closing_value) > _EPS:
            problems.append(
                f"opening + net_flow + gain = {expected_close}, but "
                f"closing_value is {self.closing_value}"
            )

        # 5. net_flow = contributions - withdrawals
        expected_net = round(
            self.flows.contributions - self.flows.withdrawals, 2
        )
        if abs(expected_net - self.flows.net_flow) > _EPS:
            problems.append(
                f"contributions - withdrawals = {expected_net}, but net_flow "
                f"is {self.flows.net_flow}"
            )

        # 6. excess = portfolio - benchmark
        p = self.performance
        expected_excess = round(p.portfolio_return_pct - p.benchmark_return_pct, 4)
        if abs(expected_excess - p.excess_return_pct) > _EPS:
            problems.append(
                f"portfolio - benchmark = {expected_excess}, but "
                f"excess_return_pct is {p.excess_return_pct}"
            )

        # 7. selection + allocation effects explain the excess.
        effects = round(p.selection_effect_pct + p.allocation_effect_pct, 4)
        if abs(effects - p.excess_return_pct) > _EPS:
            problems.append(
                f"selection + allocation = {effects}, but excess_return_pct "
                f"is {p.excess_return_pct}"
            )

        # 8. total fees = management + fund costs
        expected_fees = round(self.fees.management_fee + self.fees.fund_costs, 2)
        if abs(expected_fees - self.fees.total_fees) > _EPS:
            problems.append(
                f"management + fund costs = {expected_fees}, but total_fees "
                f"is {self.fees.total_fees}"
            )

        # 9. Top holdings cannot exceed the portfolio.
        hsum = round(sum(h.weight_pct for h in self.top_holdings), 4)
        if hsum > 100.0 + _EPS:
            problems.append(f"top holdings weights sum to {hsum}, exceeds 100")

        if problems:
            raise SnapshotCoherenceError(
                f"snapshot for {self.client.client_id} / {self.period.label} "
                f"does not add up:\n  - " + "\n  - ".join(problems)
            )

    # -- serialisation -----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def numeric_facts(self) -> Dict[str, float]:
        """Flatten every number in the snapshot to `path -> value`.

        THIS IS THE GROUNDING ALLOWLIST. A figure in a generated report is
        permitted only if it matches one of these values (within the rounding
        tolerance the validator applies). Derived figures the model computes
        itself — "roughly a fifth of the portfolio" — are handled separately;
        this covers stated figures.
        """
        facts: Dict[str, float] = {
            "opening_value":   self.opening_value,
            "closing_value":   self.closing_value,
            "investment_gain": self.investment_gain,

            "performance.portfolio_return_pct":  self.performance.portfolio_return_pct,
            "performance.benchmark_return_pct":  self.performance.benchmark_return_pct,
            "performance.excess_return_pct":     self.performance.excess_return_pct,
            "performance.selection_effect_pct":  self.performance.selection_effect_pct,
            "performance.allocation_effect_pct": self.performance.allocation_effect_pct,

            "flows.contributions":   self.flows.contributions,
            "flows.withdrawals":     self.flows.withdrawals,
            "flows.net_flow":        self.flows.net_flow,
            "flows.income_received": self.flows.income_received,

            "fees.management_fee":  self.fees.management_fee,
            "fees.fund_costs":      self.fees.fund_costs,
            "fees.total_fees":      self.fees.total_fees,
            "fees.total_fees_pct":  self.fees.total_fees_pct,

            "risk.volatility_pct":   self.risk.volatility_pct,
            "risk.sharpe_ratio":     self.risk.sharpe_ratio,
            "risk.max_drawdown_pct": self.risk.max_drawdown_pct,
        }

        for a in self.allocation:
            key = a.asset_class.lower().replace(" ", "_")
            facts[f"allocation.{key}.weight_pct"]       = a.weight_pct
            facts[f"allocation.{key}.opening_value"]    = a.opening_value
            facts[f"allocation.{key}.closing_value"]    = a.closing_value
            facts[f"allocation.{key}.return_pct"]       = a.return_pct
            facts[f"allocation.{key}.contribution_pct"] = a.contribution_pct

        for i, h in enumerate(self.top_holdings):
            facts[f"holdings.{i}.weight_pct"] = h.weight_pct
            facts[f"holdings.{i}.value"]      = h.value
            facts[f"holdings.{i}.return_pct"] = h.return_pct

        return facts

    def fact_values(self) -> set:
        """Just the values, for fast membership testing by the validator."""
        return {round(v, 4) for v in self.numeric_facts().values()}
