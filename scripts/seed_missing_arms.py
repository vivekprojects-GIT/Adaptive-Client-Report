"""Every personalisable report type gets the full six strategy arms.

    python scripts/seed_missing_arms.py

balanced · concise · visual · numeric · narrative · comparison

The six arms are the shared style vocabulary — identical across report
types — and that sameness is what lets a client's preference TRANSFER: a
client who thumbs toward tables on their quarterly review should start
from the numeric arm on their risk report too. A type missing arms is a
type where that transfer silently cannot happen, and where UCB is
choosing from a poorer menu for no stated reason.

tax_summary_report stays at exactly one mandated template: prescribed
types are not a bandit decision.

Idempotent: only creates what is missing, never touches existing docs.
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
from scripts.seed_config_selection import FOCUS, blocks_for, dedupe  # noqa: E402

FULL = ["balanced", "concise", "visual", "numeric", "narrative", "comparison"]

# Canonical style profiles — one per strategy, shared by every report type.
# These are the declared fits UCB scores against a client's learned
# dimensions, so they must mean the same thing everywhere.
STYLE = {
    "balanced":  {"concise": .5, "detail": .5, "visual": .5, "table": .5,
                  "comparison": .5, "numeric_precision": .5, "narrative": .5,
                  "step_by_step": .5, "technical_depth": .5},
    "concise":   {"concise": .9, "detail": .2, "visual": .4, "table": .5,
                  "comparison": .4, "numeric_precision": .5, "narrative": .3,
                  "step_by_step": .3, "technical_depth": .5},
    "visual":    {"concise": .5, "detail": .5, "visual": .9, "table": .3,
                  "comparison": .5, "numeric_precision": .4, "narrative": .4,
                  "step_by_step": .4, "technical_depth": .4},
    "numeric":   {"concise": .5, "detail": .7, "visual": .3, "table": .9,
                  "comparison": .6, "numeric_precision": .9, "narrative": .3,
                  "step_by_step": .5, "technical_depth": .7},
    "narrative": {"concise": .2, "detail": .8, "visual": .4, "table": .3,
                  "comparison": .4, "numeric_precision": .4, "narrative": .9,
                  "step_by_step": .5, "technical_depth": .4},
    "comparison": {"concise": .5, "detail": .5, "visual": .6, "table": .7,
                   "comparison": .9, "numeric_precision": .6, "narrative": .4,
                   "step_by_step": .4, "technical_depth": .5},
}

LABEL = {"balanced": "Balanced", "concise": "Concise", "visual": "Visual",
         "numeric": "Numeric", "narrative": "Narrative",
         "comparison": "Comparison"}

BRIEF = {
    "balanced":  "Balance visuals and prose evenly. Headline figures first, "
                 "then the main visual, then measured explanation.",
    "concise":   "Short. Headline figures, the essential blocks only, tight "
                 "prose. Every fact category still present.",
    "visual":    "Charts lead. Prose refers to what the charts show rather "
                 "than repeating every figure.",
    "numeric":   "Tables lead. Exact figures to two decimal places; prose "
                 "interprets rather than restates.",
    "narrative": "A flowing account of the period, the way an adviser would "
                 "talk it through. Figures woven into sentences.",
    "comparison": "Everything anchored against the benchmark or the prior "
                  "period: ahead or behind, and by how much.",
}


def main() -> None:
    store = MongoStore()
    db = store.db["ape_config"]
    now = datetime.now(timezone.utc).isoformat()

    created, per_type = 0, {}
    for rt in sorted(FOCUS):
        if rt == "tax_summary_report":
            continue                       # prescribed: one mandated template
        have = set(db.distinct("strategy", {"entity_type": "template",
                                            "report_type": rt}))
        missing = [a for a in FULL if a not in have]
        for strat in missing:
            tid = f"{rt}__{strat}_v1"
            rt_label = rt.replace("_", " ").title()
            db.update_one(
                {"entity_type": "template", "entity_id": tid},
                {"$set": {
                    "entity_type": "template", "entity_id": tid,
                    "template_id": tid, "version": "_", "status": "ACTIVE",
                    "report_type": rt, "strategy": strat,
                    "label": LABEL[strat],
                    "description": f"{rt_label} — "
                                   f"{LABEL[strat].lower()} presentation.",
                    "brief": BRIEF[strat],
                    "style_profile": STYLE[strat],
                    "required_blocks": dedupe(blocks_for(rt, strat)),
                    "optional_blocks": [],
                    "ts": now,
                }},
                upsert=True)
            created += 1
        per_type[rt] = (len(have), len(missing))

    print(f"created {created} templates\n")
    for rt in sorted(per_type):
        have, added = per_type[rt]
        n = db.count_documents({"entity_type": "template", "report_type": rt,
                                "status": "ACTIVE"})
        flag = "ok " if n == 6 else "?? "
        print(f"  {flag}{rt:<34} {have} -> {n} arms"
              + (f"  (+{added})" if added else ""))
    n_tax = db.count_documents({"entity_type": "template",
                                "report_type": "tax_summary_report"})
    print(f"  ok tax_summary_report{'':<15} {n_tax} arm (mandated, by design)")


if __name__ == "__main__":
    main()
