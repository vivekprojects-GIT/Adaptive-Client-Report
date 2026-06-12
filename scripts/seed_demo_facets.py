"""
Seed synthetic bandit_state + turn_record rows for `demo_user` so the full
analytics page lights up — cognitive facets, recency momentum, intent
distribution, signals, the User Cognitive Profile card, etc.

Run from repo root:
  python scripts/seed_demo_facets.py
"""

from __future__ import annotations

import os
import random
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure we can import the `ape` package whether we run from repo root or scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from ape.orchestrator import hash_user_id          # noqa: E402
from ape.store import MongoStore                   # noqa: E402
from ape.strategies.instructions import FORMAT_EXPECTATIONS, compute_format_compliance  # noqa: E402

USER_ID    = "demo_user"
DOMAIN     = "finance"
POLICY_VER = "v1"
NOW        = datetime.now(timezone.utc)


# ------------------------------------------------------------------------
# Each cell defines: intent, topic, and a list of (strategy, count, avg_reward)
# tuples. avg_reward is in [-1, +1] just like the real bandit. We pick numbers
# that produce HIGH / MODERATE / LOW confidence tiers so the dashboard demo
# shows all three.
#
# Confidence formula (see ape/analytics/facets.py):
#   confidence_score = round(100 × (
#       0.4 × min(total_count/20, 1)             # volume_factor
#     + 0.3 × min(|lead_avg − runner_avg|, 1)    # gap_factor
#     + 0.3 × max(0, (lead_avg + 1)/2)           # leader_strength
#   ))
#   HIGH      if total ≥ 10 and score ≥ 75
#   MODERATE  if total ≥  4 and score ≥ 50
#   LOW       otherwise
# ------------------------------------------------------------------------

CELLS = [
    # ───── HIGH ─────  total=22, gap=0.65, leader=+0.85
    # volume=1.0, gap=0.65, leader_str=0.925 → ~88
    {
        "intent": "Decision",
        "topic":  "portfolio_rebalancing",
        "minutes_ago": 18,
        "strategies": [
            ("decision_card",       14,  0.85),
            ("pros_cons_table",      6,  0.20),
            ("standard_llm",         2, -0.10),
        ],
    },

    # ───── HIGH ─────  total=18, gap=0.6, leader=+0.78
    {
        "intent": "Explanation",
        "topic":  "compound_interest",
        "minutes_ago": 90,
        "strategies": [
            ("analogy_explanation", 12,  0.78),
            ("short_paragraph",      4,  0.18),
            ("bullet_summary",       2,  0.05),
        ],
    },

    # ───── MODERATE ─────  total=11, gap=0.38, leader=+0.55
    # volume=0.55, gap=0.38, leader_str=0.775 → ~57
    {
        "intent": "Comparison",
        "topic":  "etf_vs_mutual_fund",
        "minutes_ago": 240,
        "strategies": [
            ("comparison_table",     7,  0.55),
            ("bullet_contrast",      4,  0.17),
        ],
    },

    # ───── MODERATE ─────  total=8, gap=0.30, leader=+0.50
    # volume=0.40, gap=0.30, leader_str=0.75 → ~48 → may slip to LOW; bump count
    {
        "intent": "Instructional",
        "topic":  "open_brokerage_account",
        "minutes_ago": 360,
        "strategies": [
            ("numbered_steps",       7,  0.62),
            ("checklist",            4,  0.28),
            ("phased_workflow",      1, -0.20),
        ],
    },

    # ───── LOW ─────  total=4, gap=0.10, leader=+0.20
    # volume=0.20, gap=0.10, leader_str=0.60 → ~29
    {
        "intent": "Evaluation",
        "topic":  "crypto_allocation",
        "minutes_ago": 1440,
        "strategies": [
            ("affirm_with_calibration", 2,  0.20),
            ("concerned_pushback",      2,  0.10),
        ],
    },

    # ───── LOW (single strategy) ─────  shows the empty-runner-up placeholder
    {
        "intent": "Definitional",
        "topic":  "expense_ratio",
        "minutes_ago": 720,
        "strategies": [
            ("definition_plus_example", 3, 0.60),
        ],
    },
]


def cached_ucb(count: int, avg_reward: float, total_pulls_in_cell: int, c: float = 1.0) -> float:
    """UCB score: avg_reward + c × sqrt(2 × ln(total) / count). Approximate."""
    import math
    if count == 0:
        return 999.0
    total = max(total_pulls_in_cell, 1)
    exploration = c * math.sqrt(2.0 * math.log(total) / count)
    return round(avg_reward + exploration, 4)


def _signal_from_reward(r: float) -> tuple[str, str]:
    """Pick a plausible (signal, reward_category) for a given normalized reward.

    Mirrors the real signal_routing config so the profile facets (clarity,
    friction, positive) get realistic input.
    """
    if r >= 0.7:   return "thumbs_up",        "explicit_positive"
    if r >= 0.3:   return "copy_save",        "inferred_positive"
    if r >= 0.0:   return "deeper_question",  "inferred_positive"
    if r >= -0.3:  return "no_signal",        "neutral"
    if r >= -0.6:  return "regenerate_click", "inferred_negative"
    return            "thumbs_down",          "explicit_negative"


def seed_bandit_rows(store, user_hash: str) -> int:
    """Insert / upsert one bandit_state row per (cell, strategy)."""
    total_rows = 0
    for cell in CELLS:
        intent = cell["intent"]
        topic  = cell["topic"]
        ts     = NOW - timedelta(minutes=cell["minutes_ago"])
        total_in_cell = sum(s[1] for s in cell["strategies"])

        for (strategy, count, avg) in cell["strategies"]:
            total_reward = round(avg * count, 6)
            doc = {
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
                "last_updated_at": ts.isoformat(),
            }
            store.bandit_state.update_one(
                {
                    "user_id_hash": user_hash,
                    "domain":       DOMAIN,
                    "intent":       intent,
                    "topic":        topic,
                    "strategy":     strategy,
                },
                {"$set": doc},
                upsert=True,
            )
            total_rows += 1
    return total_rows


def seed_turn_records(store, user_hash: str) -> int:
    """Insert one turn_record per bandit pull, timestamped across the last
    30 days. Most activity weighted toward the recent few days so the
    "recency_momentum" facet reads High.
    """
    rng = random.Random(42)   # deterministic for reproducible demos
    rows = 0

    for cell in CELLS:
        intent = cell["intent"]
        topic  = cell["topic"]
        for (strategy, count, avg) in cell["strategies"]:
            expected_format = FORMAT_EXPECTATIONS.get(strategy, "paragraph")
            for i in range(count):
                # Bias 60% of activity into the last 3 days; rest spread over 30
                if rng.random() < 0.60:
                    days_back = rng.uniform(0, 3)
                else:
                    days_back = rng.uniform(3, 30)
                ts = NOW - timedelta(days=days_back,
                                     hours=rng.randint(0, 23),
                                     minutes=rng.randint(0, 59))

                # Add jitter to the per-turn reward (keep ~avg per cell)
                noise   = rng.uniform(-0.15, 0.15)
                reward  = max(-1.0, min(1.0, avg + noise))
                signal, category = _signal_from_reward(reward)

                # 10% non-compliance — simulates the synthesizer ignoring format hint
                rendered = expected_format if rng.random() > 0.10 else "paragraph"
                compliance = compute_format_compliance(strategy, rendered)

                store.turn_record.insert_one({
                    "response_id":           f"demo_resp_{uuid.uuid4().hex[:12]}",
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
                rows += 1
    return rows


def main() -> None:
    uri = os.environ.get("APE_MONGO_URI")
    db_name = os.environ.get("APE_MONGO_DB", "ape")
    if not uri:
        sys.exit("APE_MONGO_URI is not set in .env")

    store = MongoStore(uri=uri, db_name=db_name)
    user_hash = hash_user_id(USER_ID)
    print(f"Seeding for user_id={USER_ID}  hash={user_hash}  db={db_name}")

    # Clear so the script is idempotent
    bdel = store.bandit_state.delete_many({"user_id_hash": user_hash}).deleted_count
    tdel = store.turn_record.delete_many({"user_id_hash": user_hash}).deleted_count
    print(f"  cleared {bdel} bandit rows, {tdel} turn_records for this user")

    bandit_rows = seed_bandit_rows(store, user_hash)
    turn_rows   = seed_turn_records(store, user_hash)

    # Display-name directory entry
    store.upsert_user_directory_entry(
        user_id_hash=user_hash,
        display_name="Demo User",
        email="demo@example.com",
        source="demo_seed",
    )

    print(f"  bandit_state:  {bandit_rows} rows across {len(CELLS)} cells")
    print(f"  turn_record:   {turn_rows} rows")
    print(f"  user_directory: 1 entry  ({user_hash} → 'Demo User')")

    # Recompute interest scores so the profile + active-users views light up.
    from ape.analytics import compute_user_topic_interest, compute_topic_trends
    interest_n = compute_user_topic_interest(store, user_id_hash=user_hash)
    trend_n    = compute_topic_trends(store, days=30)
    print(f"  user_topic_interest: {interest_n} rows recomputed")
    print(f"  topic_trend_daily:   {trend_n} rows recomputed")

    print("\nDone. Reload the analytics page (Inspect user = demo_user).")


if __name__ == "__main__":
    main()
