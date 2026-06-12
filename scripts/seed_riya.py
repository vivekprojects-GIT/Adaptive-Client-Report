"""
Clear demo_user's runtime data and seed a synthetic user "Riya" whose data is
fully consistent with the CURRENT system semantics:

  - count            = PULL counter (bumped at selection, not reward)
  - rewards          = vg evidence tiers: explicit +-2, inferred +-1
  - avg_reward       = total_reward / count
  - cached_ucb       = avg + sqrt(2 * ln N / count)   (display cache)
  - selection_method = round_robin for each arm's first pull, ucb after
  - turn records     = one per pull, APPLIED with signal + category + reward
  - chat history     = two sessions of realistic Q&A in ape_messages
  - analytics        = user_topic_interest + topic_trend_daily recomputed

Persona: Riya — engaged, structure-loving learner. Loves comparison tables,
numbered steps, and worked examples; dislikes plain-paragraph answers.

Run from repo root:
  python scripts/seed_riya.py
"""

from __future__ import annotations

import math
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

from ape.orchestrator import hash_user_id                       # noqa: E402
from ape.store import MongoStore, REWARD_STATUS_APPLIED        # noqa: E402
from ape.strategies.instructions import FORMAT_EXPECTATIONS    # noqa: E402

DOMAIN     = "finance"
POLICY_VER = "v1"
NOW        = datetime.now(timezone.utc)
USER_ID    = "Riya"

# ---------------------------------------------------------------------------
# Signal -> (reward_category, format reward) under the vg evidence-tier model.
# Exactly the vg catalog: only thumbs + LLM text signals exist. Signals with
# no format-axis routing (no_signal) produce NO bandit reward — the counter
# simply isn't bumped on that axis.
# ---------------------------------------------------------------------------
SIGNAL_REWARD: Dict[str, Tuple[str, float]] = {
    "thumbs_up":              ("inferred_positive", +1.0),
    "format_praise_explicit": ("explicit_positive", +2.0),
    "thumbs_down":            ("inferred_negative", -1.0),
    "format_change_request":  ("explicit_negative", -2.0),
}

# How Riya reacts to a strategy she loves / tolerates / dislikes.
# (signal, probability) — drawn per pull. "no_signal" = no reaction; the
# pull still counts (count bumps at selection) but no reward lands.
PROFILES: Dict[str, List[Tuple[str, float]]] = {
    "loved": [
        ("thumbs_up",              0.50),
        ("format_praise_explicit", 0.20),
        ("no_signal",              0.30),
    ],
    "okay": [
        ("thumbs_up",              0.25),
        ("no_signal",              0.60),
        ("thumbs_down",            0.15),
    ],
    "disliked": [
        ("thumbs_down",            0.40),
        ("format_change_request",  0.30),
        ("no_signal",              0.30),
    ],
}

# Cells: (intent, topic, [(strategy, pulls, profile), ...])
# Strategy/intent combos mirror the seeded policies; topics are in the
# finance whitelist so canonicalization keeps them intact.
CELLS: List[Tuple[str, str, List[Tuple[str, int, str]]]] = [
    ("Comparison", "roth_vs_traditional_ira", [
        ("comparison_table", 9, "loved"),
        ("bullet_contrast",  3, "okay"),
        ("standard_llm",     2, "disliked"),
    ]),
    ("Definitional", "roth_ira", [
        ("definition_plus_example", 6, "loved"),
        ("one_liner",               3, "okay"),
    ]),
    ("Instructional", "open_brokerage_account", [
        ("numbered_steps",  7, "loved"),
        ("checklist",       3, "okay"),
        ("phased_workflow", 2, "disliked"),
    ]),
    ("Explanation", "compound_interest", [
        ("analogy_explanation", 5, "loved"),
        ("short_paragraph",     2, "disliked"),
    ]),
    ("Decision", "retirement_accounts", [
        ("decision_card",   6, "loved"),
        ("pros_cons_table", 3, "okay"),
        ("standard_llm",    1, "disliked"),
    ]),
]

RECENCY_BIAS = 0.6   # 60% of activity in the last 3 days


def pick_signal(rng: random.Random, profile: str) -> str:
    r = rng.random()
    acc = 0.0
    for sig, p in PROFILES[profile]:
        acc += p
        if r <= acc:
            return sig
    return PROFILES[profile][-1][0]


def sample_ts(rng: random.Random) -> datetime:
    days_back = rng.uniform(0, 3) if rng.random() < RECENCY_BIAS else rng.uniform(3, 30)
    return NOW - timedelta(days=days_back, hours=rng.randint(0, 23),
                           minutes=rng.randint(0, 59), seconds=rng.randint(0, 59))


def seed_riya(store: MongoStore, seed: int = 42) -> Tuple[int, int]:
    rng = random.Random(seed)
    user_hash = hash_user_id(USER_ID)

    # Idempotent: wipe any previous Riya state first
    store.clear_user(user_hash)

    bandit_n = 0
    turn_n = 0
    last_response_per_cell: Dict[Tuple[str, str], str] = {}

    for (intent, topic, strategies) in CELLS:
        n_total = sum(s[1] for s in strategies)

        for (strategy, pulls, profile) in strategies:
            rewards: List[float] = []
            pos = neg = 0

            for pull_idx in range(pulls):
                ts = sample_ts(rng)
                signal = pick_signal(rng, profile)
                category, reward = SIGNAL_REWARD.get(signal, (None, None))
                if reward is not None:
                    rewards.append(reward)
                    if reward > 0:
                        pos += 1
                    else:
                        neg += 1

                response_id = f"demo_riya_{uuid.uuid4().hex[:10]}"
                selection_method = "round_robin" if pull_idx == 0 else "ucb"
                store.turn_record.insert_one({
                    "response_id":           response_id,
                    "user_id_hash":          user_hash,
                    "session_id_optional":   None,
                    "ts":                    ts.isoformat(),
                    "domain":                DOMAIN,
                    "intent":                intent,
                    "topic":                 topic,
                    "selected_strategy":     strategy,
                    "selection_method":      selection_method,
                    "rendered_format":       FORMAT_EXPECTATIONS.get(strategy, "paragraph"),
                    "format_compliance":     1 if rng.random() > 0.10 else 0,
                    "ucb_at_selection":      0.0,
                    "instruction_version":   "v1",
                    "attribution_bandit_pk": {
                        "user_id_hash": user_hash,
                        "domain":       DOMAIN,
                        "intent":       intent,
                        "topic":        topic,
                    },
                    "attribution_bandit_sk": strategy,
                    "reward_status":         REWARD_STATUS_APPLIED,
                    "signal":                signal,
                    "reward_category":       category,
                    "normalized_reward":     reward,
                    "pending_signals":       [],
                })
                turn_n += 1
                last_response_per_cell[(intent, topic)] = response_id

            # Bandit row — count is the PULL counter; every pull above also
            # landed a reward, so total = sum(rewards), avg = total / count.
            total_reward = round(sum(rewards), 6)
            avg = round(total_reward / pulls, 6)
            ucb = round(avg + math.sqrt(2.0 * math.log(max(n_total, 2)) / pulls), 4)
            store.bandit_state.update_one(
                {"user_id_hash": user_hash, "domain": DOMAIN,
                 "intent": intent, "topic": topic, "strategy": strategy},
                {"$set": {
                    "user_id_hash":    user_hash,
                    "domain":          DOMAIN,
                    "intent":          intent,
                    "topic":           topic,
                    "strategy":        strategy,
                    "count":           pulls,
                    "total_reward":    total_reward,
                    "avg_reward":      avg,
                    "positive_count":  pos,
                    "negative_count":  neg,
                    "cached_ucb":      ucb,
                    "policy_version":  POLICY_VER,
                    "ucb_algorithm":   "UCB",
                    "last_updated_at": NOW.isoformat(),
                }},
                upsert=True,
            )
            bandit_n += 1

    # ---- Chat history: two realistic sessions -----------------------------
    sessions = [
        ("Roth vs Traditional IRA", [
            ("Should I open a Roth IRA or a Traditional IRA?",
             "| Feature | Roth IRA | Traditional IRA |\n|---|---|---|\n| Tax on contributions | Paid now | Deducted now |\n| Tax on withdrawals | Tax-free | Taxed as income |\n| Best when | Tax rate rises later | Tax rate falls later |\n\nIf you expect higher income later, Roth usually wins.",
             "Comparison", "roth_vs_traditional_ira", "comparison_table"),
            ("What exactly is a Roth IRA?",
             "A Roth IRA is a retirement account funded with after-tax money. Example: you invest $6,000 of already-taxed salary; decades later you withdraw the grown balance — contributions and gains — completely tax-free after age 59 1/2.",
             "Definitional", "roth_ira", "definition_plus_example"),
        ]),
        ("Getting started with investing", [
            ("How do I open a brokerage account?",
             "1. Pick a broker (compare fees and minimums)\n2. Gather ID, SSN/PAN, and bank details\n3. Complete the online application\n4. Fund the account via bank transfer\n5. Place your first order once funds settle",
             "Instructional", "open_brokerage_account", "numbered_steps"),
            ("Can you explain compound interest simply?",
             "Think of compound interest like a snowball rolling downhill: each rotation it picks up snow, and the bigger it gets, the more snow each rotation adds. Your money earns returns, and those returns themselves start earning returns.",
             "Explanation", "compound_interest", "analogy_explanation"),
        ]),
    ]

    msg_n = 0
    for s_idx, (title, exchanges) in enumerate(sessions):
        session_id = f"sess_riya_{uuid.uuid4().hex[:10]}"
        base_ts = NOW - timedelta(days=s_idx, hours=2)
        for e_idx, (q, a, intent, topic, strategy) in enumerate(exchanges):
            q_ts = base_ts + timedelta(minutes=e_idx * 7)
            a_ts = q_ts + timedelta(seconds=6)
            response_id = last_response_per_cell.get((intent, topic))
            store.append_message(
                message_id=f"msg_{uuid.uuid4().hex[:12]}",
                user_id_hash=user_hash, session_id=session_id,
                role="user", content=q, ts=q_ts.isoformat(),
            )
            store.append_message(
                message_id=f"msg_{uuid.uuid4().hex[:12]}",
                user_id_hash=user_hash, session_id=session_id,
                role="assistant", content=a, ts=a_ts.isoformat(),
                response_id=response_id,
                rendered_format=FORMAT_EXPECTATIONS.get(strategy, "paragraph"),
                meta={
                    "intent":            intent,
                    "topic":             topic,
                    "selected_strategy": strategy,
                    "selection_method":  "ucb",
                    "ucb_at_selection":  1.25,
                },
            )
            msg_n += 2

    # ---- Directory entry (display name for analytics / outreach) ----------
    store.upsert_user_directory_entry(
        user_id_hash=user_hash,
        display_name="Riya",
        email="riya@example.com",
        source="demo_seed",
        do_not_contact=False,
        compliance_eligible=True,
    )

    print(f"  Riya seeded: hash={user_hash}")
    print(f"    bandit_rows={bandit_n}  turn_records={turn_n}  messages={msg_n}")
    return bandit_n, turn_n


def main() -> None:
    store = MongoStore()

    # 1) Clear demo_user runtime data
    demo_hash = hash_user_id("demo_user")
    deleted = store.clear_user(demo_hash)
    print(f"Cleared demo_user ({demo_hash}): {deleted}")

    # 2) Seed Riya
    seed_riya(store)

    # 3) Recompute analytics aggregates
    print("Recomputing analytics aggregates...")
    from ape.analytics import compute_user_topic_interest, compute_topic_trends
    n_interest = compute_user_topic_interest(store, user_id_hash=hash_user_id(USER_ID))
    n_trend = compute_topic_trends(store, days=30)
    print(f"  user_topic_interest rows: {n_interest}")
    print(f"  topic_trend_daily rows:   {n_trend}")

    print("\nDone. Type 'Riya' as the user in the chat sidebar, or open the")
    print("analytics page and Inspect 'Riya' in the Active customers table.")


if __name__ == "__main__":
    main()
