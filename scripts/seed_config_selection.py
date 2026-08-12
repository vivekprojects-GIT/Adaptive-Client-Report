"""Bring ape_config fully in line with the shipped product.

    python scripts/seed_config_thompson.py

What this fixes, and why:

1. TEMPLATES — 15 of 16 report types still carried 2-4 block skeletons from
   before the depth blocks existed. Every type now gets a per-type block
   set: the type's FOCUS block leads, and every arm still contains the
   full facts (personalisation changes HOW, never WHAT).

2. BANDIT CONFIG — contextual UCB for both decisions: exploration_c
   plus the prior strengths, editable from the admin panel.

3. SIGNALS — the routing table described the chat product. Replaced with
   the viewer's actual event vocabulary, each row naming its destination
   (D1 reward / D2 reward / preference profile).

4. REWARD SCALE — likewise: the real per-event weights the reward code
   applies, so the admin table and the code cannot quietly disagree.

5. Dead offer_policy rows deleted (the feature was removed).

Idempotent: run it twice, get the same state.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

from ape.store.mongo_store import MongoStore  # noqa: E402

now = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731

# ---------------------------------------------------------------------------
# 1. Per-report-type template blocks
# ---------------------------------------------------------------------------
# CORE appears in every arm of every type: identity, prose, takeaways,
# small print. FOCUS is what the report type is ABOUT and leads the body.
# Style arms then reorder/extend: concise trims, visual leads with charts,
# numeric leads with tables, narrative leads with prose.

CORE_TOP = ["kpi_grid", "callout", "narrative"]
CORE_END = ["key_takeaways", "disclosures"]

FOCUS = {
    "quarterly_portfolio_review": ["performance_history", "returns_table",
                                   "allocation_donut", "allocation_vs_target",
                                   "top_contributors", "top_detractors",
                                   "fees_table"],
    "annual_portfolio_review":    ["performance_history", "returns_table",
                                   "allocation_vs_target", "top_contributors",
                                   "top_detractors", "fees_table", "explainer"],
    "performance_report":         ["performance_history", "returns_table",
                                   "top_contributors", "top_detractors",
                                   "comparison_chart"],
    "benchmark_comparison_report": ["comparison_chart", "returns_table",
                                    "comparison_table", "performance_history"],
    "asset_allocation_report":    ["allocation_donut", "allocation_vs_target",
                                   "holdings_table", "chart:treemap"],
    "risk_report":                ["risk_card", "allocation_vs_target",
                                   "performance_history", "chart:gauge",
                                   "explainer"],
    "holdings_report":            ["holdings_table", "top_contributors",
                                   "top_detractors", "allocation_donut"],
    "fees_cost_report":           ["fees_table", "comparison_table",
                                   "explainer"],
    "cash_flow_report":           ["comparison_table", "fees_table",
                                   "chart:waterfall"],
    "income_report":              ["comparison_table", "holdings_table",
                                   "chart:bar"],
    "goal_progress_report":       ["chart:progress", "performance_history",
                                   "returns_table"],
    "retirement_progress_report": ["chart:progress", "performance_history",
                                   "allocation_vs_target", "explainer"],
    "portfolio_change_report":    ["returns_table", "top_contributors",
                                   "top_detractors", "allocation_vs_target"],
    "executive_summary_report":   ["returns_table", "allocation_donut"],
    "advisor_review_report":      ["performance_history", "returns_table",
                                   "allocation_vs_target", "top_contributors",
                                   "top_detractors", "fees_table"],
    "tax_summary_report":         ["fees_table", "comparison_table",
                                   "holdings_table", "explainer"],
}


# Two renderings of the same fact. Swapping along these pairs changes the
# document's character without changing what it tells the client.
AS_CHART = {
    "returns_table":        "performance_history",
    "comparison_table":     "comparison_chart",
    "holdings_table":       "chart:treemap",
    "allocation_vs_target": "chart:bar",
    "top_contributors":     "chart:hbar",
    "top_detractors":       "chart:waterfall",
    "fees_table":           "chart:donut",
}
AS_TABLE = {
    "performance_history":  "returns_table",
    "performance_line":     "returns_table",
    "comparison_chart":     "comparison_table",
    "allocation_donut":     "holdings_table",
    "chart:donut":          "holdings_table",
    "chart:bar":            "allocation_vs_target",
    "chart:treemap":        "holdings_table",
    "chart:gauge":          "comparison_table",
    "chart:progress":       "returns_table",
    "chart:waterfall":      "comparison_table",
}

# fees_table and disclosures are appended by the coverage gate regardless,
# so no arm has to carry them explicitly.


# Which fact category each block speaks to. Chart variants are listed
# individually: chartifying top_contributors yields chart:hbar, and if that
# were filed under "allocation" the attribution category would silently
# vanish from the visual arm — which is the exact failure this map exists
# to prevent.
CATEGORY = {
    "performance_history": "performance", "returns_table": "performance",
    "performance_line": "performance", "comparison_chart": "performance",
    "chart:progress": "performance",
    "allocation_donut": "allocation", "allocation_vs_target": "allocation",
    "holdings_table": "allocation", "chart:donut": "allocation",
    "chart:treemap": "allocation", "chart:bar": "allocation",
    "top_contributors": "attribution", "top_detractors": "attribution",
    "comparison_table": "attribution", "chart:hbar": "attribution",
    "chart:waterfall": "attribution",
    "risk_card": "risk", "chart:gauge": "risk",
    "fees_table": "costs",
}


def _category(spec: str) -> str:
    return CATEGORY.get(spec, CATEGORY.get(spec.split(":")[0], spec))


def _one_per_category(blocks, limit=None):
    """First block of each distinct category, order preserved."""
    out, seen = [], set()
    for b in blocks:
        c = _category(b)
        if c in seen:
            continue
        seen.add(c)
        out.append(b)
    return out[:limit] if limit else out


# Two renderings of the same fact. Swapping along these pairs changes the
# document's character without changing what it tells the client.
AS_CHART = {
    "returns_table":        "performance_history",
    "comparison_table":     "comparison_chart",
    "holdings_table":       "chart:treemap",
    "allocation_vs_target": "chart:bar",
    "top_contributors":     "chart:hbar",
    "top_detractors":       "chart:waterfall",
}
AS_TABLE = {
    "performance_history":  "returns_table",
    "performance_line":     "returns_table",
    "comparison_chart":     "comparison_table",
    "allocation_donut":     "holdings_table",
    "chart:donut":          "holdings_table",
    "chart:bar":            "allocation_vs_target",
    "chart:treemap":        "holdings_table",
    "chart:hbar":           "top_contributors",
    "chart:waterfall":      "top_detractors",
    "chart:gauge":          "comparison_table",
    "chart:progress":       "returns_table",
}


def _chartify(blocks):
    return [AS_CHART.get(b, b) for b in blocks]


def _tabulate(blocks):
    return [AS_TABLE.get(b, b) for b in blocks]


def blocks_for(report_type: str, strategy: str) -> list:
    """One arm's document.

    Every arm covers the same categories; they differ in how many blocks
    they spend per category and whether those blocks are charts, tables or
    prose. fees_table and disclosures are appended by the coverage gate, so
    no arm needs to carry them explicitly.
    """
    focus = FOCUS.get(report_type, ["returns_table", "allocation_donut"])

    if strategy == "visual":
        # Charts only — every table becomes its chart equivalent, so the
        # figures are all present, drawn rather than listed.
        body = _chartify(focus)
        if not any(b.startswith("chart") or "history" in b for b in body):
            body.insert(0, "chart:donut")
        return ["kpi_grid", "callout"] + body + ["key_takeaways"]

    if strategy == "numeric":
        # Tables only, no charts, plus holdings detail. Precision over
        # impression.
        body = [b for b in _tabulate(focus) if not b.startswith("chart")]
        if "holdings_table" not in body:
            body.append("holdings_table")
        if not any(_category(b) == "attribution" for b in body):
            body.append("comparison_table")
        return ["kpi_grid"] + body

    if strategy == "narrative":
        # Prose leads and carries the argument, with one supporting block
        # per category so nothing is merely asserted.
        return (["narrative", "kpi_grid", "callout"]
                + _one_per_category(focus) + ["key_takeaways", "explainer"])

    if strategy == "concise":
        # Short means fewer blocks PER CATEGORY, never fewer categories:
        # dropping allocation or attribution would tell this client less
        # than the next one, which is the line personalisation must not
        # cross. No narrative, no takeaways, no explainer.
        return ["kpi_grid", "callout"] + _one_per_category(_chartify(focus))

    if strategy == "comparison":
        # Everything framed against the benchmark or the prior period.
        lead = ["comparison_chart", "returns_table", "allocation_vs_target"]
        rest = _one_per_category(
            [b for b in focus if _category(b) not in
             {_category(x) for x in lead}])
        return ["kpi_grid", "callout"] + lead + rest + ["key_takeaways"]

    # balanced: the full picture, charts and tables together.
    return (["kpi_grid", "callout", "narrative"] + focus
            + ["key_takeaways", "explainer"])


def dedupe(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ---------------------------------------------------------------------------
# 2/3/4. Thompson config, signal routing, reward scale
# ---------------------------------------------------------------------------

SELECTION = {
    "entity_type": "bandit_config", "entity_id": "selection", "version": "_",
    "status": "ACTIVE", "policy": "ucb_contextual", "exploration_c": 1.0,
    # D1's style-fit prior is worth this many pseudo-observations. Bigger =
    # trusts the template's declared style longer before data outvotes it.
    "prior_strength_d1": 4.0,
    # D2 starts closer to uniform: answer strategies have no meaningful
    # declared fit, so the data should take over quickly.
    "prior_strength_d2": 2.0,
    "notes": "Both decisions score arms mean + c*sqrt(2 ln N/n); highest "
             "wins. Thumbs-down is reward 0 - evidence, not deletion.",
}

SIGNALS = [
    ("report_opened",    "D1",      "Client opened the signed link."),
    ("dwell_60s",        "D1",      "Stayed with the document for a minute."),
    ("question_asked",   "D1+profile", "Asked the report a question; wording may carry format cues."),
    ("pdf_downloaded",   "D1",      "Downloaded the PDF copy."),
    ("report_helpful",   "D1",      "Explicitly said the report helped."),
    ("report_unhelpful", "none",    "Explicit negative; recorded as evidence, adds no reward."),
    ("block_highlighted", "none",   "Selected a section; context for the next question."),
    ("answer_helpful",   "D2+profile", "Thumbs-up on an answer; rewards the exact answer arm."),
    ("answer_unhelpful", "D2+profile", "Thumbs-down; reward 0 to the arm - evidence of a miss."),
]

# Format cues stay: they document how question wording moves the profile.
KEEP_CUE_RULES = {
    "table_request", "visual_request", "comparison_request",
    "exact_numbers_request", "more_detail_request", "simplify_request",
    "concise_request", "step_by_step_request",
}
DEAD_CHAT_RULES = {
    "thumbs_up", "thumbs_down", "content_correction",
    "format_change_request", "reask_same_question", "no_signal",
    "response_copy",
}

# Signal classes: ENGAGEMENT is weak evidence, a QUESTION is ambiguous
# (its format cues route to the profile instead), QUALITY verdicts dominate.
# report_unhelpful closes the report's accrual rather than paying anything.
REWARDS = [
    ("report_opened",    "D1 engagement", 0.15),
    ("dwell_60s",        "D1 engagement", 0.15),
    ("pdf_downloaded",   "D1 engagement", 0.10),
    ("question_asked",   "D1 ambiguous",  0.10),
    ("report_helpful",   "D1 quality",    0.50),
    ("report_unhelpful", "D1 quality",    0.00),
    ("answer_helpful",   "D2 quality",    1.00),
    ("answer_unhelpful", "D2 quality",    0.00),
]
DEAD_REWARDS = {"explicit_positive", "explicit_negative",
                "inferred_positive", "inferred_negative"}


def main() -> None:
    store = MongoStore()
    db = store.db["ape_config"]

    print("1. TEMPLATES")
    touched = 0
    for t in db.find({"entity_type": "template"}):
        rt, strat = t.get("report_type"), t.get("strategy")
        if not rt or rt not in FOCUS:
            continue
        blocks = dedupe(blocks_for(rt, strat))
        if t.get("required_blocks") != blocks:
            db.update_one({"_id": t["_id"]},
                          {"$set": {"required_blocks": blocks, "ts": now()}})
            touched += 1
    print(f"   {touched} templates enriched")

    from collections import Counter
    sizes = Counter()
    for t in db.find({"entity_type": "template"}):
        n = len(t.get("required_blocks") or [])
        sizes["thin (<6)" if n < 6 else "rich"] += 1
    print(f"   now: {dict(sizes)}")

    print("2. BANDIT CONFIG -> UCB")
    deleted = db.delete_many({"entity_type": "bandit_config",
                              "entity_id": "ucb"}).deleted_count
    db.update_one({"entity_type": "bandit_config", "entity_id": "selection"},
                  {"$set": {**SELECTION, "ts": now()}}, upsert=True)
    print(f"   legacy doc deleted: {deleted}; selection doc upserted")

    print("3. SIGNAL ROUTING")
    for name, dest, desc in SIGNALS:
        db.update_one(
            {"entity_type": "signal_routing", "entity_id": name},
            {"$set": {"entity_type": "signal_routing", "entity_id": name,
                      "signal_name": name, "destination": dest,
                      "description": desc, "status": "ACTIVE",
                      "version": "_", "ts": now()}},
            upsert=True)
    dead = db.delete_many({"entity_type": "signal_routing",
                           "entity_id": {"$in": list(DEAD_CHAT_RULES)}})
    kept = db.count_documents({"entity_type": "signal_routing"})
    print(f"   9 viewer events upserted, {dead.deleted_count} chat-era rules "
          f"deleted, {kept} rules total")

    print("4. REWARD SCALE")
    for name, decision, weight in REWARDS:
        db.update_one(
            {"entity_type": "reward_scale", "entity_id": name},
            {"$set": {"entity_type": "reward_scale", "entity_id": name,
                      "category": name, "decision": decision,
                      "value": weight, "status": "ACTIVE",
                      "version": "_", "ts": now(),
                      "description": ("capped at 1.0 per report" if decision == "D1"
                                      else "Beta update on the answer arm")}},
            upsert=True)
    dead = db.delete_many({"entity_type": "reward_scale",
                           "entity_id": {"$in": list(DEAD_REWARDS)}})
    print(f"   8 weights upserted, {dead.deleted_count} chat-era rows deleted")

    print("5. DEAD OFFER POLICIES")
    dead = db.delete_many({"entity_type": "offer_policy"})
    print(f"   {dead.deleted_count} deleted")

    print("\nDONE — config now matches the shipped product.")


if __name__ == "__main__":
    main()
