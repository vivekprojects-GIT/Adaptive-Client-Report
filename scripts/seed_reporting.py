"""Seed the D1 config — report types and their template arms.

Idempotent: re-running upserts the same entities rather than duplicating.
Additive: touches only the new `report_type` and `template` entity types,
never the existing intents / strategies / policies that serve D2.

    python scripts/seed_reporting.py
"""

from __future__ import annotations

import os
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


REPORT_TYPES = [
    dict(report_type="quarterly_portfolio_review", label="Quarterly Portfolio Review",
         personalisable=True, cadence="quarterly",
         notes="Highest volume, most room for presentation choice. The v1 report type."),
    dict(report_type="annual_review", label="Annual Review",
         personalisable=True, cadence="annual",
         notes="Same shape family as the quarterly review. Inherits the client profile."),
    dict(report_type="rebalancing_proposal", label="Rebalancing Proposal",
         personalisable=True, cadence="ad_hoc",
         notes="Too rare to learn its own arms. Depends on profile transfer from the quarterly review."),
    dict(report_type="tax_pack", label="Annual Tax Pack",
         personalisable=False, cadence="annual",
         notes="PRESCRIBED. Format set by regulation — must never reach D1."),
    dict(report_type="valuation_statement", label="Valuation Statement",
         personalisable=False, cadence="on_demand",
         notes="A list of holdings and values. No meaningful presentation choice."),
]

Q = "quarterly_portfolio_review"
A = "annual_review"
R = "rebalancing_proposal"

TEMPLATES = [
    dict(template_id="balanced_default_v1", strategy="balanced_default", report_type=Q,
         label="Balanced",
         description="The safe middle. Serves as the population default before anything is known about a client.",
         brief="Balance visuals and prose evenly. Lead with headline figures, then one chart, then two or three sentences of plain interpretation per section.",
         required_blocks=["kpi_grid", "allocation_donut", "performance_line", "narrative"]),

    dict(template_id="concise_summary_v1", strategy="concise_summary", report_type=Q,
         label="Concise",
         description="One page. Headline numbers and a single takeaway.",
         brief="At most one page. Lead with four headline figures, then one short paragraph. No section may exceed three sentences.",
         required_blocks=["kpi_grid", "callout", "narrative"]),

    dict(template_id="visual_first_v1", strategy="visual_first", report_type=Q,
         label="Visual",
         description="Charts carry the story. Prose only captions what the chart shows.",
         brief="Lead every section with the visual. One or two sentences of interpretation beneath. Never more than three sentences per section.",
         required_blocks=["kpi_grid", "allocation_donut", "performance_line", "comparison_chart"]),

    dict(template_id="comparison_focused_v1", strategy="comparison_focused", report_type=Q,
         label="Comparison",
         description="Everything measured against the benchmark.",
         brief="Frame every figure against its benchmark. Portfolio beside benchmark, difference stated explicitly. Prose explains the gap, not the absolute number.",
         required_blocks=["kpi_grid", "comparison_chart", "comparison_table", "narrative"]),

    dict(template_id="narrative_explanatory_v1", strategy="narrative_explanatory", report_type=Q,
         label="Plain English",
         description="Written as prose. What happened, why, what it cost, what we're watching.",
         brief="Two to three short paragraphs per section. State the figure, then explain it. No jargon; define any unavoidable term inline.",
         required_blocks=["narrative", "kpi_grid", "callout"]),

    dict(template_id="numeric_detail_v1", strategy="numeric_detail", report_type=Q,
         label="Numeric",
         description="Tables and full precision. For clients who reconcile against their own spreadsheet.",
         brief="Figures go in tables. Prose only to flag what changed since last quarter. Full precision, two decimal places, no rounding in summary figures.",
         required_blocks=["kpi_grid", "holdings_table", "fees_table", "comparison_table"]),

    dict(template_id="annual_narrative_v1", strategy="annual_narrative", report_type=A,
         label="Year in Review",
         description="The year as a story — what changed, what it meant, what comes next.",
         brief="Tell the year as a narrative arc across four sections. Reference quarters only where something changed materially.",
         required_blocks=["narrative", "kpi_grid", "performance_line", "callout"]),

    dict(template_id="annual_numeric_v1", strategy="annual_numeric", report_type=A,
         label="Annual Statement",
         description="Full-year figures in tables, quarter by quarter.",
         brief="Tabular throughout. Show each quarter as a row. Full precision. Prose only for material changes.",
         required_blocks=["kpi_grid", "comparison_table", "holdings_table", "fees_table"]),

    dict(template_id="annual_visual_v1", strategy="annual_visual", report_type=A,
         label="Annual Visual Recap",
         description="The year in charts. Performance line, allocation drift, contribution breakdown.",
         brief="Charts carry the year. One caption per chart, never more than two sentences.",
         required_blocks=["kpi_grid", "performance_line", "allocation_donut", "comparison_chart"]),

    # ---- Rebalancing proposal ---------------------------------------------
    # A proposal is a different document from a review: it argues for a
    # CHANGE. The axis that separates these arms is not charts-vs-prose but
    # whether the recommendation leads or the reasoning does — which is a
    # genuine preference difference between clients, and one the chat reveals
    # ("just tell me what you're suggesting" vs "why are you suggesting it?").
    dict(template_id="rebalance_recommendation_first_v1",
         strategy="rebalance_recommendation_first", report_type=R,
         label="Recommendation First",
         description="Leads with what we propose and what it costs. Reasoning follows for those who want it.",
         brief="Open with the proposed change stated plainly in one sentence, then the "
               "current-vs-proposed table, then the cost. Reasoning comes last and stays "
               "under three sentences per point. Never bury the recommendation.",
         required_blocks=["callout", "comparison_table", "fees_table", "narrative"]),

    dict(template_id="rebalance_reasoning_first_v1",
         strategy="rebalance_reasoning_first", report_type=R,
         label="Reasoning First",
         description="Builds the case — what changed, why it matters — then arrives at the proposal.",
         brief="Explain what changed in the portfolio or the market, why it matters for this "
               "client's objectives, and only then state the proposed change. Two to three "
               "short paragraphs per step. Define any unavoidable term inline.",
         required_blocks=["narrative", "comparison_table", "callout"]),

    dict(template_id="rebalance_side_by_side_v1",
         strategy="rebalance_side_by_side", report_type=R,
         label="Side by Side",
         description="Current versus proposed, every line, with the delta. For clients who want to check the arithmetic.",
         brief="Present current and proposed allocations side by side with an explicit delta "
               "column. Full precision. Prose only to flag anything that breaches an agreed "
               "band. No recommendation language — let the numbers make the case.",
         required_blocks=["comparison_table", "allocation_donut", "holdings_table", "fees_table"]),

    # ---- PRESCRIBED types --------------------------------------------------
    # These still need a template — a report has to be generated somehow —
    # but they get exactly ONE. INVARIANT: a prescribed report type has
    # exactly one ACTIVE template. More than one would imply a choice that
    # must not exist, and regulation not product decides their format.
    dict(template_id="tax_pack_statutory_v1", strategy="tax_pack_statutory",
         report_type="tax_pack",
         label="Statutory Tax Pack (mandated)",
         description="The prescribed tax-pack layout. Fixed by regulation — no presentation choice exists.",
         brief="Follow the mandated statutory layout exactly. Section order, headings and "
               "wording are fixed. Do not summarise, reorder, reword, or omit any section. "
               "Do not add commentary, interpretation, or recommendations. Figures are "
               "reproduced verbatim from the source with no rounding.",
         required_blocks=["kpi_grid", "holdings_table", "fees_table", "comparison_table"]),

    dict(template_id="valuation_statutory_v1", strategy="valuation_statutory",
         report_type="valuation_statement",
         label="Valuation Statement (mandated)",
         description="Holdings and values as at the valuation date. Fixed layout, no interpretation.",
         brief="Reproduce holdings and values as at the valuation date in the mandated order. "
               "No commentary, no interpretation, no performance narrative. Full precision, "
               "no rounding.",
         required_blocks=["kpi_grid", "holdings_table"]),
]


def main() -> None:
    store = MongoStore()
    cfg = ConfigManager(store)

    for rt in REPORT_TYPES:
        cfg.upsert_report_type(changed_by="seed_reporting", **rt)
    print(f"report types : {len(REPORT_TYPES)}")

    for t in TEMPLATES:
        cfg.upsert_template(changed_by="seed_reporting", **t)
    print(f"templates    : {len(TEMPLATES)}")

    by_type: dict = {}
    for t in cfg.list_templates():
        if t.get("status") not in (None, "ACTIVE"):
            continue
        by_type.setdefault(t.get("report_type"), []).append(t.get("strategy"))

    print()
    problems = []
    for rt in cfg.list_report_types():
        rid = rt.get("report_type")
        arms = by_type.get(rid, [])
        personalisable = bool(rt.get("personalisable"))

        if personalisable:
            gate = "personalisable"
            # Fewer than two arms means there is nothing for the bandit to
            # choose between — the type is effectively prescribed but not
            # marked as such, which hides the fact from compliance.
            if len(arms) < 2:
                problems.append(
                    f"{rid}: personalisable but has {len(arms)} active template(s); "
                    f"D1 needs at least 2 to have a choice"
                )
        else:
            gate = "PRESCRIBED - no D1"
            # Exactly one. Zero means the report cannot be generated at all;
            # more than one implies a choice that must not exist.
            if len(arms) != 1:
                problems.append(
                    f"{rid}: prescribed and must have exactly 1 active template, "
                    f"found {len(arms)}"
                )

        print(f"  {rid:<28} {len(arms)} template(s)   {gate}")

    print()
    if problems:
        print("INVARIANT VIOLATIONS:")
        for p in problems:
            print(f"  ! {p}")
        raise SystemExit(1)
    print("invariants OK: every report type can generate; "
          "prescribed types have exactly one mandated template")


if __name__ == "__main__":
    main()
