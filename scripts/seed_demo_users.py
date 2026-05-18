"""
Seed 5 synthetic users with distinct cognitive-facet signatures so the
analytics dashboard demonstrates the full range of behaviors:

  1. alex_retiree    — Action-ready, retirement-focused, high offer readiness
  2. maya_learner    — Awareness stage, lots of definitional questions
  3. dan_evaluator   — Evaluation stage, comparison-heavy, decisive
  4. riya_struggler  — High clarity-need, friction on tax topics
  5. sam_explorer    — Exploration stage, broad but shallow, cold-start

Each persona has:
  • A list of bandit cells (intent, topic, [(strategy, count, avg_reward), ...])
  • A `recency_bias`  — fraction of activity in the last 3 days (0..1)
  • A persona blurb (printed at end)

The script:
  • Wipes prior synthetic data for these users (idempotent)
  • Writes bandit_state + turn_record rows for each cell
  • Recomputes ape_user_topic_interest per user
  • Recomputes ape_topic_trend_daily globally

Run from repo root:
  python scripts/seed_demo_users.py
"""

from __future__ import annotations

import math
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from ape.orchestrator import hash_user_id          # noqa: E402
from ape.store import MongoStore                   # noqa: E402
from ape.strategies.instructions import FORMAT_EXPECTATIONS, compute_format_compliance  # noqa: E402


DOMAIN     = "finance"
POLICY_VER = "v1"
NOW        = datetime.now(timezone.utc)


# ==========================================================================
# PERSONAS
# Each cell = (intent, topic, [(strategy, count, avg_reward), ...])
# The empirical mean of generated turn rewards will approximate avg_reward.
# ==========================================================================

PERSONAS: List[Dict[str, Any]] = [
    # ---------- 1. ALEX — action-ready retirement planner ----------
    {
        "user_id":     "alex_retiree",
        "display_name":"Alex Chen",
        "email":       "alex.chen@example.com",
        "blurb":       "Action-ready · loves decision cards · 19 retirement turns · ready for outreach",
        "recency_bias": 0.65,
        "cells": [
            ("Decision", "retirement_accounts", [
                ("decision_card",       16,  0.88),
                ("pros_cons_table",      4,  0.30),
                ("standard_llm",         2, -0.10),
            ]),
            ("Comparison", "retirement_accounts", [
                ("comparison_table",    12,  0.85),
                ("bullet_contrast",      3,  0.30),
            ]),
            ("Decision", "portfolio_rebalancing", [
                ("decision_card",        8,  0.78),
                ("pros_cons_table",      2,  0.15),
            ]),
            ("Evaluation", "annuity_options", [
                ("pros_cons_table",      5,  0.65),
                ("decision_card",        2,  0.55),
            ]),
        ],
    },

    # ---------- 2. MAYA — awareness-stage learner ----------
    {
        "user_id":     "maya_learner",
        "display_name":"Maya Patel",
        "email":       "maya.patel@example.com",
        "blurb":       "Awareness stage · definitions + analogies · early in journey · positive engagement",
        "recency_bias": 0.50,
        "cells": [
            ("Definitional", "credit_score", [
                ("definition_plus_example", 8,  0.72),
                ("one_liner",                3,  0.42),
            ]),
            ("Definitional", "expense_ratio", [
                ("definition_plus_example", 5,  0.68),
                ("definition_with_pointer", 2,  0.45),
            ]),
            ("Definitional", "roth_ira", [
                ("analogy_explanation",      6,  0.82),
                ("one_liner",                3,  0.48),
            ]),
            ("Explanation", "compound_interest", [
                ("analogy_explanation",      7,  0.80),
                ("short_paragraph",          2,  0.50),
            ]),
            ("Definitional", "dividend_yield", [
                ("definition_plus_example", 3,  0.55),
            ]),
        ],
    },

    # ---------- 3. DAN — evaluating, comparison-heavy ----------
    {
        "user_id":     "dan_evaluator",
        "display_name":"Dan Mueller",
        "email":       "dan.mueller@example.com",
        "blurb":       "Evaluation stage · comparison-table loyalist · drilling into ETF vs MF",
        "recency_bias": 0.60,
        "cells": [
            ("Comparison", "etf_vs_mutual_fund", [
                ("comparison_table",     14,  0.82),
                ("bullet_contrast",       4,  0.38),
                ("standard_llm",          2,  0.05),
            ]),
            ("Comparison", "roth_vs_traditional_ira", [
                ("comparison_table",      9,  0.75),
                ("pros_cons_table",       4,  0.55),
            ]),
            ("Evaluation", "crypto_allocation", [
                ("pros_cons_table",       5,  0.45),
                ("comparison_table",      2,  0.30),
            ]),
            ("Comparison", "stocks_vs_bonds", [
                ("comparison_table",      6,  0.70),
                ("bullet_contrast",       2,  0.40),
            ]),
        ],
    },

    # ---------- 4. RIYA — friction-heavy, needs clearer help ----------
    {
        "user_id":      "riya_struggler",
        "display_name": "Riya Singh",
        "email":        "riya.singh@example.com",
        "blurb":        "High clarity need · friction on tax topics · regenerates often · needs simpler formats",
        "recency_bias": 0.55,
        # Compliance: failed jurisdictional check — gate should block outreach
        # regardless of interest score.
        "compliance_eligible": False,
        "cells": [
            ("Instructional", "tax_implications", [
                ("numbered_steps",        6,  0.10),
                ("phased_workflow",       4, -0.20),
                ("checklist",             3, -0.35),
            ]),
            ("Definitional", "tax_implications", [
                ("one_liner",             5, -0.30),
                ("definition_plus_example", 3,  0.15),
            ]),
            ("Instructional", "open_brokerage_account", [
                ("numbered_steps",        5,  0.40),
                ("checklist",             3,  0.20),
            ]),
            ("Explanation", "capital_gains", [
                ("analogy_explanation",   3,  0.20),
                ("short_paragraph",       2, -0.15),
            ]),
        ],
    },

    # ---------- 5. SAM — broad explorer, low pulls per cell ----------
    {
        "user_id":      "sam_explorer",
        "display_name": "Sam Rodriguez",
        "email":        "sam.rodriguez@example.com",
        "blurb":        "Exploration stage · breadth over depth · cold-start across many topics · opted out of outreach",
        "recency_bias": 0.40,
        # Hard opt-out — should show "Do not contact" badge even if score is high.
        "do_not_contact": True,
        "cells": [
            ("Definitional", "dividends", [
                ("one_liner",             2,  0.45),
            ]),
            ("Explanation", "inflation", [
                ("analogy_explanation",   3,  0.55),
                ("short_paragraph",       1,  0.20),
            ]),
            ("Comparison", "stocks_vs_bonds", [
                ("comparison_table",      3,  0.60),
            ]),
            ("Definitional", "ipo", [
                ("definition_plus_example", 2,  0.50),
            ]),
            ("Definitional", "yield_curve", [
                ("definition_with_pointer", 2,  0.30),
            ]),
            ("Explanation", "market_volatility", [
                ("analogy_explanation",   2,  0.50),
            ]),
        ],
    },
]


# ==========================================================================
# Helpers
# ==========================================================================

def cached_ucb(count: int, avg_reward: float, total_pulls_in_cell: int, c: float = 1.0) -> float:
    if count == 0:
        return 999.0
    total = max(total_pulls_in_cell, 1)
    exploration = c * math.sqrt(2.0 * math.log(total) / count)
    return round(avg_reward + exploration, 4)


def signal_from_reward(r: float) -> Tuple[str, str]:
    if r >= 0.7:   return "thumbs_up",        "strong_positive"
    if r >= 0.3:   return "copy_save",        "weak_positive"
    if r >= 0.0:   return "deeper_question",  "weak_positive"
    if r >= -0.3:  return "no_signal",        "neutral"
    if r >= -0.6:  return "regenerate_click", "weak_negative"
    return            "thumbs_down",          "strong_negative"


def sample_ts(rng: random.Random, recency_bias: float) -> datetime:
    """Pick a timestamp biased toward the recent window.

    `recency_bias` fraction of points land in the last 3 days; the rest
    spread evenly across the prior 27.
    """
    if rng.random() < recency_bias:
        days_back = rng.uniform(0, 3)
    else:
        days_back = rng.uniform(3, 30)
    return NOW - timedelta(
        days=days_back,
        hours=rng.randint(0, 23),
        minutes=rng.randint(0, 59),
        seconds=rng.randint(0, 59),
    )


def seed_one_persona(store: MongoStore, persona: Dict[str, Any], seed: int) -> Tuple[int, int]:
    """Returns (bandit_rows_written, turn_rows_written)."""
    rng = random.Random(seed)
    user_id   = persona["user_id"]
    user_hash = hash_user_id(user_id)

    # Clear prior synthetic state for this user
    store.bandit_state.delete_many({"user_id_hash": user_hash})
    store.turn_record.delete_many({"user_id_hash": user_hash})

    bandit_n = 0
    turn_n   = 0

    for (intent, topic, strategies) in persona["cells"]:
        total_in_cell = sum(s[1] for s in strategies)
        cell_anchor_ts = NOW - timedelta(minutes=rng.randint(15, 6000))

        for (strategy, count, avg) in strategies:
            # --- bandit_state row ---
            total_reward = round(avg * count, 6)
            store.bandit_state.update_one(
                {
                    "user_id_hash": user_hash,
                    "domain":       DOMAIN,
                    "intent":       intent,
                    "topic":        topic,
                    "strategy":     strategy,
                },
                {"$set": {
                    "user_id_hash":    user_hash,
                    "domain":          DOMAIN,
                    "intent":          intent,
                    "topic":           topic,
                    "strategy":        strategy,
                    "count":           count,
                    "total_reward":    total_reward,
                    "avg_reward":      avg,
                    "cached_ucb":      cached_ucb(count, avg, total_in_cell),
                    "policy_version":  POLICY_VER,
                    "ucb_algorithm":   "UCB",
                    "last_updated_at": cell_anchor_ts.isoformat(),
                }},
                upsert=True,
            )
            bandit_n += 1

            # --- one turn_record per pull, scattered across the window ---
            expected_format = FORMAT_EXPECTATIONS.get(strategy, "paragraph")

            for _ in range(count):
                ts = sample_ts(rng, persona["recency_bias"])
                noise   = rng.uniform(-0.15, 0.15)
                reward  = max(-1.0, min(1.0, avg + noise))
                signal, category = signal_from_reward(reward)

                # Simulate occasional non-compliance — the synthesizer LLM
                # doesn't always honor the requested format. 10% of the time
                # we render as paragraph regardless of what was selected.
                rendered = expected_format if rng.random() > 0.10 else "paragraph"
                compliance = compute_format_compliance(strategy, rendered)

                store.turn_record.insert_one({
                    "response_id":           f"demo_{user_id}_{uuid.uuid4().hex[:10]}",
                    "user_id_hash":          user_hash,
                    "session_id_optional":   None,
                    "ts":                    ts.isoformat(),
                    "domain":                DOMAIN,
                    "intent":                intent,
                    "topic":                 topic,
                    "selected_strategy":     strategy,
                    "rendered_format":       rendered,
                    "format_compliance":     int(bool(compliance)),
                    "ucb_at_selection":      0.0,
                    "instruction_version":   "v1",
                    "attribution_bandit_pk": {
                        "user_id_hash": user_hash,
                        "domain":       DOMAIN,
                        "intent":       intent,
                        "topic":        topic,
                    },
                    "attribution_bandit_sk": strategy,
                    "reward_status":         "APPLIED",
                    "signal":                signal,
                    "reward_category":       category,
                    "normalized_reward":     round(reward, 3),
                })
                turn_n += 1

    return bandit_n, turn_n


# ==========================================================================
# Main
# ==========================================================================

def main() -> None:
    uri = os.environ.get("APE_MONGO_URI")
    db_name = os.environ.get("APE_MONGO_DB", "ape")
    if not uri:
        sys.exit("APE_MONGO_URI is not set in .env")

    store = MongoStore(uri=uri, db_name=db_name)

    print(f"Seeding {len(PERSONAS)} personas into db={db_name}\n")

    for i, persona in enumerate(PERSONAS):
        user_id   = persona["user_id"]
        user_hash = hash_user_id(user_id)
        b, t = seed_one_persona(store, persona, seed=100 + i)

        # Display-name + compliance directory entry — separate from analytics
        # collections, joined into active-users + user-profile + offers.
        store.upsert_user_directory_entry(
            user_id_hash=user_hash,
            display_name=persona.get("display_name", user_id),
            email=persona.get("email", ""),
            source="demo_seed",
            do_not_contact=persona.get("do_not_contact", False),
            compliance_eligible=persona.get("compliance_eligible", True),
        )

        total_cells = len(persona["cells"])
        print(f"  ✓ {persona.get('display_name', user_id):18s}  hash={user_hash}")
        print(f"      cells={total_cells:2d}  bandit_rows={b:3d}  turn_records={t:3d}  blurb: {persona['blurb']}")
        print()

    # Recompute analytics aggregates
    print("Recomputing analytics aggregates…")
    from ape.analytics import compute_user_topic_interest, compute_topic_trends
    total_interest = 0
    for persona in PERSONAS:
        n = compute_user_topic_interest(store, user_id_hash=hash_user_id(persona["user_id"]))
        total_interest += n
    trend_n = compute_topic_trends(store, days=30)
    print(f"  user_topic_interest: {total_interest} rows across {len(PERSONAS)} users")
    print(f"  topic_trend_daily:   {trend_n} rows")

    print("\n────────────────────────────────────────────────────────────")
    print("Done. Open the analytics page, set Window = 30 days, and click")
    print("'Inspect' on any user in the Active customers table to see their")
    print("cognitive profile + per-(intent, topic) facet cards.")
    print("────────────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
