"""Seed the full report catalogue — 16 report types and their template arms.

═══════════════════════════════════════════════════════════════════════════
THE STRUCTURE
═══════════════════════════════════════════════════════════════════════════

    ARM  = a presentation style (balanced, concise, visual, numeric,
           narrative, comparison). The SAME six names mean the same thing
           in every report type.

    TEMPLATE = one (report_type, style) pair, with blocks and a writing
           brief specific to that report's content.

Why the arm names are shared but the templates are not:

  • Shared names let a client's learned preference TRANSFER. Someone who
    keeps asking for tables in their quarterly review should get the numeric
    variant of their risk report too. If quarterly called it `visual_first`
    and risk called it `chart_heavy`, that transfer would be guesswork.

  • Per-type templates keep each report fit for purpose. A risk report's
    "visual" is a risk_card plus a concentration chart; a fees report's
    "visual" is a cost breakdown. Same style, different content.

  • Each report type offers only the styles that make sense for it. An
    executive summary has no "detailed narrative" variant — that would not
    be an executive summary.

    python scripts/seed_report_catalog.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

from ape.config import ConfigManager  # noqa: E402
from ape.store import MongoStore  # noqa: E402

D = ["concise", "detail", "visual", "table", "comparison",
     "numeric_precision", "narrative", "step_by_step", "technical_depth"]



# ---------------------------------------------------------------------------
# The six presentation styles — the ARM vocabulary, shared across every
# report type so client preference transfers between them.
# ---------------------------------------------------------------------------
STYLES = {
    "balanced": dict(
        label="Balanced",
        blocks=["kpi_grid", "chart:bar", "comparison_chart", "narrative"],
        brief="Balance visuals and prose evenly. Lead with the headline figures, "
              "then the main visual, then two or three sentences of plain "
              "interpretation per section."
    ),
    "concise": dict(
        label="Concise",
        blocks=["kpi_grid", "callout"],
        brief="At most one page. Lead with the headline figures, then a single "
              "short paragraph. No section may exceed three sentences."
    ),
    "visual": dict(
        label="Visual",
        blocks=["kpi_grid", "chart:donut", "chart:line", "comparison_chart"],
        brief="Lead every section with its visual. One or two sentences of "
              "interpretation beneath. Never more than three sentences per section."
    ),
    "numeric": dict(
        label="Numeric",
        blocks=["kpi_grid", "comparison_table", "holdings_table", "fees_table"],
        brief="Figures go in tables. Prose only to flag what changed. Full "
              "precision, two decimal places, no rounding in summary figures."
    ),
    "narrative": dict(
        label="Plain English",
        blocks=["narrative", "kpi_grid", "callout"],
        brief="Two to three short paragraphs per section. State the figure, then "
              "explain it. No jargon; define any unavoidable term inline."
    ),
    "comparison": dict(
        label="Comparison",
        blocks=["kpi_grid", "comparison_chart", "chart:waterfall", "comparison_table"],
        brief="Frame every figure against its reference point. Side by side, with "
              "the difference stated explicitly. Prose explains the gap, not the "
              "absolute number."
    ),
}

# ---------------------------------------------------------------------------
# The 16 report types.
#   (id, label, personalisable, cadence, required_blocks,
#    styles offered, notes)
#
# `styles` is the set of templates seeded for that type. Types offer only the styles
# that make sense for them — an executive summary has no detailed-narrative
# variant, because that would not be an executive summary.
# ---------------------------------------------------------------------------
K, AD, PL, CC, CT, HT, FT, RC, NA, CO = (
    "kpi_grid", "allocation_donut", "performance_line", "comparison_chart",
    "comparison_table", "holdings_table", "fees_table", "risk_card",
    "narrative", "callout")

REPORTS = [
    ("quarterly_portfolio_review", "Quarterly Portfolio Review", True, "quarterly",
     [K, PL, NA], [AD, CC, CT, HT, FT, RC, CO],
     ["balanced", "concise", "visual", "numeric", "narrative", "comparison"],
     "Highest volume. The v1 report type."),

    ("annual_portfolio_review", "Annual Portfolio Review", True, "annual",
     [K, PL, NA], [AD, CC, CT, HT, FT, RC, CO],
     ["balanced", "visual", "numeric", "narrative"],
     "Full-year performance and year-over-year review."),

    ("performance_report", "Performance Report", True, "on_demand",
     [K, PL, CT], [CC, NA, AD, CO],
     ["visual", "numeric", "narrative", "comparison"],
     "Deep dive into returns and attribution."),

    ("benchmark_comparison_report", "Benchmark Comparison", True, "on_demand",
     [K, CC, CT], [PL, NA, CO],
     ["visual", "numeric", "comparison", "concise"],
     "Portfolio versus benchmark or index."),

    ("asset_allocation_report", "Asset Allocation Report", True, "on_demand",
     [K, AD, CT], [HT, NA, CO],
     ["visual", "numeric", "comparison", "narrative"],
     "Current versus target allocation and drift."),

    ("risk_report", "Risk Report", True, "on_demand",
     [K, RC, NA], [CT, AD, HT, CO],
     ["visual", "numeric", "narrative", "concise"],
     "Risk level, volatility, concentration, contributors."),

    ("holdings_report", "Holdings Report", True, "on_demand",
     [K, HT], [CT, AD, NA, CO],
     ["numeric", "comparison", "visual", "concise"],
     "Holdings, weights, contributors and detractors."),

    ("fees_cost_report", "Fees & Costs Report", True, "on_demand",
     [K, FT], [CT, NA, CO],
     ["numeric", "narrative", "concise", "comparison"],
     "Advisory fees, fund expenses, other costs."),

    ("cash_flow_report", "Cash Flow Report", True, "on_demand",
     [K, CT], [PL, NA, CO],
     ["numeric", "visual", "narrative", "concise"],
     "Contributions, withdrawals, distributions."),

    ("income_report", "Income Report", True, "on_demand",
     [K, CT], [PL, HT, NA, CO],
     ["numeric", "visual", "narrative", "concise"],
     "Dividends, interest, distributions."),

    ("goal_progress_report", "Goal Progress Report", True, "on_demand",
     [K, CC, NA], [PL, CT, CO],
     ["visual", "narrative", "concise", "balanced"],
     "Progress toward a defined financial goal."),

    ("retirement_progress_report", "Retirement Progress Report", True, "annual",
     [K, CC, NA], [PL, CT, RC, CO],
     ["visual", "narrative", "balanced", "numeric"],
     "Retirement portfolio progress and metrics."),

    ("portfolio_change_report", "Portfolio Change Report", True, "on_demand",
     [K, CT, NA], [HT, AD, CO],
     ["comparison", "numeric", "narrative", "concise"],
     "What changed between two reporting periods."),

    ("executive_summary_report", "Executive Summary", True, "on_demand",
     [K, CO], [NA, PL],
     ["concise", "visual", "balanced"],
     "Very high-level overview. No detailed variant by definition."),

    ("advisor_review_report", "Advisor Review", True, "quarterly",
     [K, PL, CT, HT, RC], [AD, FT, NA, CC, CO],
     ["numeric", "comparison", "balanced", "narrative"],
     "Adviser-facing. Denser and more technical than client reports."),

    # PRESCRIBED — format set by regulation, exactly one mandated template.
    ("tax_summary_report", "Tax Summary", False, "annual",
     [K, CT, HT], [],
     ["mandated"],
     "PRESCRIBED. Tax reporting format is set by regulation — never enters D1."),
]

MANDATED = dict(
    label="Statutory (mandated)",
    blocks=["kpi_grid", "comparison_table", "holdings_table"],
    brief="Follow the mandated statutory layout exactly. Section order, headings "
          "and wording are fixed. Do not summarise, reorder, reword or omit any "
          "section, and add no commentary or interpretation. Figures are "
          "reproduced verbatim with no rounding."
)


def prune(store, cfg) -> None:
    """Remove report types and templates not in the declared catalogue.

    Seeding must CONVERGE, not accumulate. Without this, re-running with a
    changed catalogue leaves the old entries behind and a report type ends
    up with two competing arm sets — which silently doubles the arms the
    bandit explores and halves how fast it learns anything.

    Also drops bandit rows for arms that no longer exist, so the Bandit
    State view does not fill with phantom history.
    """
    from ape.store.mongo_schema import ENTITY_REPORT_TYPE, ENTITY_TEMPLATE

    want_types = {r[0] for r in REPORTS}
    want_templates = {
        f"{r[0]}__{style}_v1" for r in REPORTS for style in r[6]
    }
    cfgcol = store.config

    dead_types = sorted({
        d["entity_id"] for d in cfgcol.find({"entity_type": ENTITY_REPORT_TYPE})
        if d.get("entity_id") not in want_types
    })
    dead_templates = sorted({
        d["entity_id"] for d in cfgcol.find({"entity_type": ENTITY_TEMPLATE})
        if d.get("entity_id") not in want_templates
    })

    if dead_types:
        cfgcol.delete_many({"entity_type": ENTITY_REPORT_TYPE,
                            "entity_id": {"$in": dead_types}})
    if dead_templates:
        cfgcol.delete_many({"entity_type": ENTITY_TEMPLATE,
                            "entity_id": {"$in": dead_templates}})

    live_arms = sorted({style for r in REPORTS for style in r[6]})
    n_arms = store.bandit_state.delete_many(
        {"strategy": {"$nin": live_arms}}).deleted_count

    if dead_types or dead_templates or n_arms:
        print(f"pruned       : {len(dead_types)} report types, "
              f"{len(dead_templates)} templates, {n_arms} stale bandit rows")
        if dead_types:
            print(f"               types: {', '.join(dead_types)}")


def main() -> None:
    store = MongoStore()
    cfg = ConfigManager(store)

    prune(store, cfg)

    for rid, label, pers, cadence, req, opt, styles, notes in REPORTS:
        cfg.upsert_report_type(report_type=rid, label=label, personalisable=pers,
                               cadence=cadence, notes=notes,
                               changed_by="seed_catalog")

    n_tpl = 0
    for rid, label, pers, cadence, req, opt, styles, notes in REPORTS:
        for style in styles:
            spec = MANDATED if style == "mandated" else STYLES[style]
            pool = set(req) | set(opt)
            # A block spec may be "type" or "type:option" ("chart:waterfall").
            # Match on the BASE type — comparing the whole spec against a pool
            # of plain type names silently drops every parameterised block.
            # `chart` is universally available: it is generic and binds to
            # whatever the snapshot carries.
            chosen = [b for b in spec["blocks"]
                      if str(b).partition(":")[0] in pool
                      or str(b).partition(":")[0] == "chart"]
            base = {str(b).partition(":")[0] for b in chosen}
            if "kpi_grid" in pool and "kpi_grid" not in base:
                chosen.insert(0, "kpi_grid")     # every report needs a headline
            if not chosen:
                chosen = list(req)               # fall back to the type's own set
            leftover = [b for b in (req + opt) if b not in base]
            cfg.upsert_template(
                template_id=f"{rid}__{style}_v1",
                strategy=style,                 # arm key — shared vocabulary
                report_type=rid,
                label=spec["label"],
                description=f"{label} — {spec['label'].lower()} presentation.",
                brief=spec["brief"],
                required_blocks=chosen,
                changed_by="seed_catalog",
            )
            n_tpl += 1

    print(f"report types : {len(REPORTS)}")
    print(f"templates    : {n_tpl}")
    print()

    problems = []
    for rid, label, pers, *_rest, styles, notes in [
        (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]) for r in REPORTS
    ]:
        n = len(styles)
        if pers and n < 2:
            problems.append(f"{rid}: personalisable but only {n} arm(s)")
        if not pers and n != 1:
            problems.append(f"{rid}: prescribed but has {n} arm(s), must be exactly 1")
        gate = "personalisable" if pers else "PRESCRIBED"
        print(f"  {rid:<30} {n} arms  {gate:<15} {', '.join(styles)}")

    print()
    if problems:
        print("INVARIANT VIOLATIONS:")
        for p in problems:
            print("  ! " + p)
        raise SystemExit(1)
    print("invariants OK")


if __name__ == "__main__":
    main()
