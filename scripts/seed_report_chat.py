"""Seed the D2 config for report chat — intents, answer strategies, policies.

WHY THIS EXISTS
---------------
The app arrived with the vocabulary of a general finance assistant: intents
like Decision / Explanation / Instructional, and 22 chat strategies. The
bandit machinery around them is exactly what we need and is reused unchanged.
The *vocabulary* is not — a client asking about their own quarterly report
asks a narrower, more specific set of things.

So this replaces the D2 vocabulary with the report-chat one from the spec:

  content intents   what the client is asking about (9)
  answer strategies how we answer them  — these are D2's ARMS (6)
  policies          which arms are candidates for which intent

The old chat intents/strategies are PAUSED, not deleted. Pausing keeps their
accumulated bandit history for audit and is reversible from the admin UI in
one click; deleting would throw away real learning and break attribution on
any turn record that still references them.

    python scripts/seed_report_chat.py            # seed + pause old
    python scripts/seed_report_chat.py --keep-old # seed only
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
from ape.store.mongo_schema import (  # noqa: E402
    ENTITY_INTENT, ENTITY_STRATEGY, STATUS_INACTIVE,
)

DOMAIN = "finance"
TOPIC = "_default"

# ---------------------------------------------------------------------------
# D2 content intents — what a client asks about their own report
# ---------------------------------------------------------------------------
INTENTS = [
    ("report_summary",         "Asking for the overall picture — 'how did I do this quarter?'"),
    ("performance_question",   "About returns, gains or losses, and what drove them."),
    ("benchmark_comparison",   "Comparing the portfolio against its benchmark."),
    ("allocation_question",    "About asset mix, weights, or diversification."),
    ("risk_question",          "About volatility, drawdown, or risk level."),
    ("holdings_question",      "About specific funds or positions held."),
    ("fees_cashflow_question", "About fees charged, contributions, or withdrawals."),
    ("explain_selected_content", "Explain a highlighted passage, chart or table."),
    ("other_report_question",  "Anything else answerable from this report."),
]

# ---------------------------------------------------------------------------
# D2 answer strategies — the ARMS the bandit chooses between when answering
# ---------------------------------------------------------------------------
STRATEGIES = [
    ("concise_direct",     "paragraph"),
    ("structured_bullets", "bulleted_list"),
    ("comparison_table",   "comparison_table"),
    ("step_by_step",       "numbered_steps"),
    ("visual_explanation", "hybrid"),
    ("detailed_narrative", "paragraph"),
]

# ---------------------------------------------------------------------------
# Candidate arms per intent.
#
# Not every arm suits every question. Offering a comparison_table for "what is
# volatility?" wastes a pull on an arm that cannot win, which slows learning
# on the arms that can. Each intent gets 3-4 genuinely plausible answers.
# ---------------------------------------------------------------------------
POLICIES = {
    "report_summary":          ["concise_direct", "structured_bullets", "detailed_narrative"],
    "performance_question":    ["concise_direct", "comparison_table", "detailed_narrative", "visual_explanation"],
    "benchmark_comparison":    ["comparison_table", "concise_direct", "visual_explanation"],
    "allocation_question":     ["visual_explanation", "comparison_table", "structured_bullets"],
    "risk_question":           ["detailed_narrative", "concise_direct", "structured_bullets"],
    "holdings_question":       ["comparison_table", "structured_bullets", "concise_direct"],
    "fees_cashflow_question":  ["comparison_table", "concise_direct", "structured_bullets"],
    "explain_selected_content": ["detailed_narrative", "concise_direct", "step_by_step"],
    "other_report_question":   ["concise_direct", "structured_bullets", "detailed_narrative"],
    # Kept so an unrecognised question still has somewhere safe to land.
    "unmapped":                ["concise_direct"],
}

KEEP = {"unmapped"}


def main() -> None:
    keep_old = "--keep-old" in sys.argv
    store = MongoStore()
    cfg = ConfigManager(store)

    for intent_id, desc in INTENTS:
        cfg.upsert_intent(intent_id=intent_id, description=desc,
                          changed_by="seed_report_chat")
    print(f"intents      : {len(INTENTS)}")

    for sid, fmt in STRATEGIES:
        cfg.upsert_strategy(strategy_id=sid, format_type=fmt,
                            changed_by="seed_report_chat")
    print(f"strategies   : {len(STRATEGIES)}")

    n_pol = 0
    for intent, arms in POLICIES.items():
        for arm in arms:
            cfg.upsert_policy(domain=DOMAIN, intent=intent, topic=TOPIC,
                              strategy_id=arm, changed_by="seed_report_chat")
            n_pol += 1
    print(f"policies     : {n_pol}")

    new_intents = {i for i, _ in INTENTS} | KEEP
    new_strats = {s for s, _ in STRATEGIES}

    if not keep_old:
        paused_i = paused_s = 0
        for row in cfg.list_intents():
            iid = row.get("intent_id") or row.get("entity_id")
            if iid not in new_intents and row.get("status") == "ACTIVE":
                store.set_config_status(ENTITY_INTENT, iid, STATUS_INACTIVE)
                paused_i += 1
        for row in cfg.list_strategies():
            sid = row.get("strategy_id") or row.get("entity_id")
            if sid not in new_strats and row.get("status") == "ACTIVE":
                store.set_config_status(ENTITY_STRATEGY, sid, STATUS_INACTIVE)
                paused_s += 1
        print(f"paused       : {paused_i} old intents, {paused_s} old strategies "
              f"(reversible from the admin UI)")

    print()
    print("ACTIVE D2 vocabulary")
    for row in cfg.list_intents():
        if row.get("status") == "ACTIVE":
            iid = row.get("intent_id") or row.get("entity_id")
            print(f"  {iid:<26} -> {', '.join(POLICIES.get(iid, []))}")


if __name__ == "__main__":
    main()
