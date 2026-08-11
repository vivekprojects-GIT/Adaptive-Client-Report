"""Delete the old general-chat vocabulary. This is a different application.

Removes, in dependency order, anything that is not part of the report-chat
(D2) or report-shape (D1) vocabulary:

    instructions  ->  for strategies being removed
    policies      ->  referencing a removed intent or strategy
    strategies    ->  chat arms that no longer exist
    intents       ->  chat intents that no longer exist
    bandit_state  ->  rows for arms that no longer exist

Order matters. Deleting a strategy while a policy still references it leaves
an orphan that would put a nonexistent arm back into the bandit menu — the
selection path reads policies to build the candidate list, so a dangling
policy row is not inert.

    python scripts/purge_chat_vocab.py --dry-run     # show what would go
    python scripts/purge_chat_vocab.py --yes         # actually delete
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

from ape.store import MongoStore  # noqa: E402
from ape.store.mongo_schema import (  # noqa: E402
    ENTITY_INSTRUCTION, ENTITY_INTENT, ENTITY_POLICY, ENTITY_STRATEGY,
)

# The vocabulary this application actually uses.
KEEP_INTENTS = {
    "report_summary", "performance_question", "benchmark_comparison",
    "allocation_question", "risk_question", "holdings_question",
    "fees_cashflow_question", "explain_selected_content",
    "other_report_question", "unmapped",
}
KEEP_STRATEGIES = {
    "concise_direct", "structured_bullets", "comparison_table",
    "step_by_step", "visual_explanation", "detailed_narrative",
}


def main() -> None:
    dry = "--yes" not in sys.argv
    store = MongoStore()
    cfg = store.config

    dead_intents = sorted({
        d.get("entity_id") for d in cfg.find({"entity_type": ENTITY_INTENT})
        if d.get("entity_id") not in KEEP_INTENTS
    })
    dead_strats = sorted({
        d.get("entity_id") for d in cfg.find({"entity_type": ENTITY_STRATEGY})
        if d.get("entity_id") not in KEEP_STRATEGIES
    })

    # A policy entity_id is "<intent>#<topic>#<strategy_id>". Match on the
    # stored fields rather than parsing the id, which is more robust.
    dead_policies = [
        d for d in cfg.find({"entity_type": ENTITY_POLICY})
        if d.get("intent") in dead_intents or d.get("strategy_id") in dead_strats
    ]
    dead_instructions = [
        d for d in cfg.find({"entity_type": ENTITY_INSTRUCTION})
        if (d.get("strategy_id") or d.get("entity_id")) in dead_strats
    ]
    dead_arms = list(store.bandit_state.find(
        {"strategy": {"$nin": sorted(KEEP_STRATEGIES)}}
    ))

    print(f"intents      : {len(dead_intents):>4}  {', '.join(dead_intents) or '-'}")
    print(f"strategies   : {len(dead_strats):>4}  {', '.join(dead_strats[:8])}"
          f"{' …' if len(dead_strats) > 8 else ''}")
    print(f"instructions : {len(dead_instructions):>4}")
    print(f"policies     : {len(dead_policies):>4}")
    print(f"bandit rows  : {len(dead_arms):>4}  (arms that no longer exist)")

    if dry:
        print("\nDRY RUN — nothing deleted. Re-run with --yes to apply.")
        return

    n_i = cfg.delete_many({"entity_type": ENTITY_INSTRUCTION,
                           "entity_id": {"$in": [d.get("entity_id") for d in dead_instructions]}}).deleted_count
    n_p = cfg.delete_many({"entity_type": ENTITY_POLICY,
                           "entity_id": {"$in": [d.get("entity_id") for d in dead_policies]}}).deleted_count
    n_s = cfg.delete_many({"entity_type": ENTITY_STRATEGY,
                           "entity_id": {"$in": dead_strats}}).deleted_count
    n_n = cfg.delete_many({"entity_type": ENTITY_INTENT,
                           "entity_id": {"$in": dead_intents}}).deleted_count
    n_b = store.bandit_state.delete_many(
        {"strategy": {"$nin": sorted(KEEP_STRATEGIES)}}).deleted_count

    store.log_admin_action(
        action_type="PURGE_CHAT_VOCAB",
        entity_type="config",
        entity_id="bulk",
        changed_by="purge_chat_vocab",
        before={"intents": dead_intents, "strategies": dead_strats,
                "policies": n_p, "instructions": n_i, "bandit_rows": n_b},
        after=None,
    )

    print(f"\ndeleted: {n_n} intents, {n_s} strategies, {n_i} instructions, "
          f"{n_p} policies, {n_b} bandit rows")

    print("\nREMAINING ACTIVE")
    for et, label in ((ENTITY_INTENT, "intents"), (ENTITY_STRATEGY, "strategies")):
        ids = sorted({d.get("entity_id") for d in cfg.find({"entity_type": et})})
        print(f"  {label:<12} {len(ids)}  {', '.join(ids)}")


if __name__ == "__main__":
    main()
