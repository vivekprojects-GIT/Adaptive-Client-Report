"""Deterministic synthetic portfolio data.

Same `(client_id, period)` always produces the same snapshot. That matters
more than it sounds: it means a report can be regenerated in a different
template and the figures are provably identical, which is the Phase 1
milestone. It also makes tests stable and demos repeatable.

═══════════════════════════════════════════════════════════════════════════
HOW THE ARITHMETIC IS MADE TO CLOSE
═══════════════════════════════════════════════════════════════════════════

Naively generating each figure independently produces documents whose parts
do not sum to their totals. We avoid that by generating the *parts* and
deriving the *totals* from them, always at display precision:

  weights      → drawn, rounded to 1dp, largest adjusted so they sum to 100.0
  returns      → drawn per sleeve, rounded to 1dp
  contribution → weight × return, rounded to 1dp
  PORTFOLIO RETURN := sum of the rounded contributions  ← derived, not drawn
  sleeve values→ weight × closing, rounded to 2dp, largest adjusted to sum
  closing      := opening + net_flow + investment_gain  ← derived

So every total a client reads is literally the sum of the parts printed
beside it.

KNOWN SIMPLIFICATIONS (deliberate — this is demo data, not an attribution
engine):
  • Attribution uses current weights rather than beginning-of-period weights.
    Real attribution is more involved; the arithmetic here is internally
    consistent, which is what the pipeline needs.
  • Investment gain is computed on the opening value, ignoring the timing of
    cash flows within the period (no time-weighting).
  • Selection/allocation effects are a plausible split of the excess return,
    not a Brinson decomposition.
"""

from __future__ import annotations

import hashlib
import random
from typing import Dict, List, Tuple

from .schema import (
    AssetClassLine,
    Client,
    Fees,
    Flows,
    Holding,
    Performance,
    Period,
    PortfolioSnapshot,
    Risk,
)

ASSET_CLASSES = ["Equity", "Fixed income", "Property", "Alternatives", "Cash"]


# ---------------------------------------------------------------------------
# Personas — archetypes, not random draws.
#
# Distinct personas matter for two reasons: demos read as real, and the
# learning layer has genuinely different clients to differentiate between.
# A book of statistically identical clients would give personalisation
# nothing to latch onto.
# ---------------------------------------------------------------------------

PERSONAS: Dict[str, Dict] = {
    "cautious_retiree": {
        "risk_profile":   "Cautious",
        "target_weights": {"Equity": 30, "Fixed income": 45, "Property": 10,
                           "Alternatives": 5, "Cash": 10},
        "value_range":    (380_000, 950_000),
        "benchmark":      "Cautious 30/70 blended",
        "flow_bias":      "withdraw",     # drawing an income
        "vol_range":      (4.0, 7.0),
        "mgmt_rate":      0.0075,
        "fund_rate":      0.0022,
    },
    "engaged_professional": {
        "risk_profile":   "Balanced",
        "target_weights": {"Equity": 60, "Fixed income": 25, "Property": 5,
                           "Alternatives": 5, "Cash": 5},
        "value_range":    (180_000, 620_000),
        "benchmark":      "Balanced 60/40 blended",
        "flow_bias":      "contribute",   # still accumulating
        "vol_range":      (8.0, 12.0),
        "mgmt_rate":      0.0085,
        "fund_rate":      0.0028,
    },
    "hnw_complex": {
        "risk_profile":   "Growth",
        "target_weights": {"Equity": 45, "Fixed income": 20, "Property": 12,
                           "Alternatives": 18, "Cash": 5},
        "value_range":    (2_400_000, 8_500_000),
        "benchmark":      "Growth 70/30 blended",
        "flow_bias":      "mixed",
        "vol_range":      (9.0, 14.0),
        "mgmt_rate":      0.0060,
        "fund_rate":      0.0035,
    },
}

_FIRST = ["Margaret", "James", "Priya", "Thomas", "Anne", "David", "Yusuf",
          "Claire", "Rohan", "Eleanor", "Michael", "Fatima", "Stephen",
          "Grace", "Alistair", "Nadia"]
_LAST = ["Ellison", "Hartley", "Raman", "Whitcombe", "Bevan", "Okafor",
         "Lindqvist", "Prasad", "Moreau", "Stanhope", "Ashworth", "Mbeki"]
_ADVISERS = ["Daniel Reece", "Sophie Alderton", "Marcus Vane", "Helena Prow"]

_FUND_NAMES = {
    "Equity":       ["Global Equity Fund", "UK Equity Income Fund",
                     "US Large Cap Fund", "Emerging Markets Fund"],
    "Fixed income": ["Sterling Corporate Bond Fund", "Gilt Fund",
                     "Global Aggregate Bond Fund"],
    "Property":     ["UK Commercial Property Fund", "Global REIT Fund"],
    "Alternatives": ["Diversified Alternatives Fund", "Infrastructure Fund",
                     "Absolute Return Fund"],
    "Cash":         ["Sterling Liquidity Fund"],
}


# ---------------------------------------------------------------------------
# Helpers that keep the arithmetic closed
# ---------------------------------------------------------------------------

def _seeded_rng(*parts: str) -> random.Random:
    """Deterministic RNG from string parts. Same inputs → same numbers."""
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _round_to_sum(values: List[float], target: float, dp: int) -> List[float]:
    """Round `values` to `dp` places and force them to sum to exactly `target`.

    The residual is pushed onto the largest element — it is the one where a
    rounding adjustment is least visible, and it keeps every printed figure
    at display precision while the total still ties out.
    """
    rounded = [round(v, dp) for v in values]
    residual = round(target - sum(rounded), dp)
    if abs(residual) > 0:
        idx = max(range(len(rounded)), key=lambda i: abs(rounded[i]))
        rounded[idx] = round(rounded[idx] + residual, dp)
    return rounded


def _jitter_weights(rng: random.Random, targets: Dict[str, float]) -> List[float]:
    """Drift the persona's target allocation a little, then normalise to 100."""
    raw = []
    for cls in ASSET_CLASSES:
        base = float(targets.get(cls, 0.0))
        drift = rng.uniform(-0.18, 0.18) * base
        raw.append(max(0.5, base + drift))
    total = sum(raw)
    scaled = [v * 100.0 / total for v in raw]
    return _round_to_sum(scaled, 100.0, 1)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate_snapshot(
    client_id: str,
    period: Period,
    persona: str | None = None,
    display_name: str | None = None,
) -> PortfolioSnapshot:
    """Build one coherent snapshot. Deterministic in (client_id, period)."""
    rng = _seeded_rng(client_id, period.label)

    persona = persona or rng.choice(list(PERSONAS))
    cfg = PERSONAS[persona]

    # -- identity ---------------------------------------------------------
    if display_name is None:
        display_name = f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"
    client = Client(
        client_id=client_id,
        display_name=display_name,
        persona=persona,
        risk_profile=cfg["risk_profile"],
        adviser_name=rng.choice(_ADVISERS),
    )

    # -- allocation and returns -------------------------------------------
    weights = _jitter_weights(rng, cfg["target_weights"])

    # Sleeve returns. Equity swings most, cash barely moves. One quarter.
    spread = {"Equity": (-6.0, 11.0), "Fixed income": (-2.0, 4.5),
              "Property": (-3.0, 4.0), "Alternatives": (-2.5, 5.5),
              "Cash": (0.2, 1.4)}
    returns = [round(rng.uniform(*spread[c]), 1) for c in ASSET_CLASSES]

    # Contribution = weight × return. The portfolio return is DERIVED from
    # these, so the parts always sum to the whole.
    contributions = [round(w / 100.0 * r, 1) for w, r in zip(weights, returns)]
    portfolio_return = round(sum(contributions), 1)

    # -- benchmark and attribution effects --------------------------------
    benchmark_return = round(portfolio_return - rng.uniform(-1.8, 2.0), 1)
    excess = round(portfolio_return - benchmark_return, 1)
    # Split the excess: most attribution is stock selection, the rest is
    # having been over/under-weight an asset class.
    selection = round(excess * rng.uniform(0.55, 0.85), 1)
    allocation_effect = round(excess - selection, 1)

    performance = Performance(
        portfolio_return_pct=portfolio_return,
        benchmark_name=cfg["benchmark"],
        benchmark_return_pct=benchmark_return,
        excess_return_pct=excess,
        selection_effect_pct=selection,
        allocation_effect_pct=allocation_effect,
    )

    # -- values and flows --------------------------------------------------
    opening = round(rng.uniform(*cfg["value_range"]), 2)

    bias = cfg["flow_bias"]
    if bias == "withdraw":
        contributions_in = round(rng.choice([0.0, 0.0, rng.uniform(2_000, 9_000)]), 2)
        withdrawals = round(opening * rng.uniform(0.008, 0.022), 2)
    elif bias == "contribute":
        contributions_in = round(rng.uniform(2_500, 14_000), 2)
        withdrawals = round(rng.choice([0.0, 0.0, rng.uniform(500, 3_000)]), 2)
    else:
        contributions_in = round(rng.uniform(0, 60_000), 2)
        withdrawals = round(rng.uniform(0, 45_000), 2)

    net_flow = round(contributions_in - withdrawals, 2)
    income = round(opening * rng.uniform(0.002, 0.009), 2)
    flows = Flows(
        contributions=contributions_in,
        withdrawals=withdrawals,
        net_flow=net_flow,
        income_received=income,
    )

    # Gain on the opening capital; closing is derived so it always ties.
    investment_gain = round(opening * portfolio_return / 100.0, 2)
    closing = round(opening + net_flow + investment_gain, 2)

    # -- per-sleeve values --------------------------------------------------
    sleeve_closing = _round_to_sum(
        [w / 100.0 * closing for w in weights], closing, 2
    )
    allocation: List[AssetClassLine] = []
    for cls, w, r, c, cv in zip(ASSET_CLASSES, weights, returns, contributions,
                                sleeve_closing):
        # Implied opening for the sleeve, before its own return.
        ov = round(cv / (1.0 + r / 100.0), 2) if r != -100.0 else cv
        allocation.append(AssetClassLine(
            asset_class=cls,
            weight_pct=w,
            opening_value=ov,
            closing_value=cv,
            return_pct=r,
            contribution_pct=c,
        ))

    # -- top holdings -------------------------------------------------------
    top_holdings = _build_holdings(rng, allocation, closing)

    # -- fees and risk ------------------------------------------------------
    mgmt = round(closing * cfg["mgmt_rate"] / 4.0, 2)      # quarterly slice
    fund = round(closing * cfg["fund_rate"] / 4.0, 2)
    total_fees = round(mgmt + fund, 2)
    fees = Fees(
        management_fee=mgmt,
        fund_costs=fund,
        total_fees=total_fees,
        total_fees_pct=round(total_fees / closing * 100.0, 2),
    )

    vol = round(rng.uniform(*cfg["vol_range"]), 1)
    risk = Risk(
        volatility_pct=vol,
        sharpe_ratio=round(rng.uniform(0.25, 1.35), 2),
        max_drawdown_pct=round(-abs(rng.uniform(1.5, vol * 1.4)), 1),
    )

    return PortfolioSnapshot(
        client=client,
        period=period,
        opening_value=opening,
        closing_value=closing,
        investment_gain=investment_gain,
        performance=performance,
        allocation=allocation,
        top_holdings=top_holdings,
        flows=flows,
        fees=fees,
        risk=risk,
    )


def _build_holdings(
    rng: random.Random,
    allocation: List[AssetClassLine],
    closing: float,
) -> List[Holding]:
    """Pick a handful of named funds, sized within their sleeve.

    Weights are a strict subset of the portfolio — they must not exceed 100%.
    """
    holdings: List[Holding] = []
    for line in allocation:
        if line.weight_pct < 4.0:
            continue                        # too small to be a "top holding"
        names = _FUND_NAMES[line.asset_class]
        n = min(2, len(names)) if line.weight_pct > 25 else 1
        chosen = rng.sample(names, n)
        # Give the named funds ~70% of the sleeve, split UNEVENLY between
        # them. An even split produces funds with identical weights and
        # values, which reads as obviously generated.
        sleeve_share = line.weight_pct * 0.70
        if n == 1:
            splits = [sleeve_share]
        else:
            major = rng.uniform(0.55, 0.72)
            splits = [sleeve_share * major, sleeve_share * (1.0 - major)]
        for nm, share in zip(chosen, splits):
            w = round(share, 1)
            holdings.append(Holding(
                name=nm,
                asset_class=line.asset_class,
                weight_pct=w,
                value=round(w / 100.0 * closing, 2),
                return_pct=round(line.return_pct + rng.uniform(-1.6, 1.6), 1),
            ))

    holdings.sort(key=lambda h: h.weight_pct, reverse=True)
    return holdings[:6]


def generate_book(
    n_clients: int,
    period: Period,
    seed_prefix: str = "c",
) -> List[PortfolioSnapshot]:
    """Generate a whole book for one period, personas spread evenly."""
    personas = list(PERSONAS)
    out: List[PortfolioSnapshot] = []
    for i in range(n_clients):
        client_id = f"{seed_prefix}_{4000 + i}"
        persona = personas[i % len(personas)]
        out.append(generate_snapshot(client_id, period, persona=persona))
    return out


def quarter(label: str, start: str, end: str) -> Period:
    """Small convenience so callers don't build Period inline everywhere."""
    return Period(label=label, start_date=start, end_date=end)
