"""
Seed the ape_config collection with default intents, strategies, instructions,
policies, signal routing, and reward scale.

Run once at startup (idempotent — uses upsert). Admins can then mutate via
the Config API; each change is logged in ape_admin_audit.

Sources of the defaults:
  - INTENT_STRATEGIES from ape/strategies/catalog.py
  - STRATEGY_INSTRUCTIONS from ape/strategies/instructions.py
  - SIGNAL_ROUTING from ape/signals/routing.py
  - REWARD_SCALE from ape/signals/reward_scale.py

After seeding, the runtime reads these from MongoDB (so admins can change them
without redeploying code).
"""

from __future__ import annotations

from ..signals.reward_scale import REWARD_SCALE
from ..signals.routing import SIGNAL_ROUTING
from ..strategies.catalog import INTENT_STRATEGIES
from ..strategies.instructions import FORMAT_EXPECTATIONS, STRATEGY_INSTRUCTIONS
from ..store import MongoStore


DEFAULT_DOMAIN = "finance"


def seed_all(store: MongoStore, domain: str = DEFAULT_DOMAIN, default_topic: str = "_default") -> dict:
    """Seed all 6 config entity types. Returns a count summary.

    Topic for default policies is `_default` — meaning "applies when no
    topic-specific policy is registered." Admins should register
    topic-specific overrides via the Config API.
    """
    counts = {
        "intents":         0,
        "strategies":      0,
        "instructions":    0,
        "policies":        0,
        "signal_rules":    0,
        "reward_rules":    0,
    }

    # ---- 1. Intents ----------------------------------------------------
    for intent in INTENT_STRATEGIES.keys():
        store.upsert_config(
            entity_type="intent",
            entity_id=intent,
            fields={"intent_id": intent, "description": _intent_description(intent)},
        )
        counts["intents"] += 1

    # ---- 2. Strategies + 3. Instructions --------------------------------
    for strategy, instruction_text in STRATEGY_INSTRUCTIONS.items():
        format_type = FORMAT_EXPECTATIONS.get(strategy, "paragraph")
        store.upsert_config(
            entity_type="strategy",
            entity_id=strategy,
            fields={
                "strategy_id":     strategy,
                "format_type":     format_type,
                "expected_format": format_type,
            },
        )
        counts["strategies"] += 1

        store.upsert_config(
            entity_type="instruction",
            entity_id=strategy,
            version="v1",
            fields={
                "instruction_text": instruction_text,
                "instruction_uri":  None,  # could point to S3 in production
                "strategy_id":      strategy,
            },
        )
        counts["instructions"] += 1

    # ---- 4. Policies ---------------------------------------------------
    # One policy doc per (domain, intent, _default, strategy) listing the
    # default candidate set. Admins can add topic-specific overrides.
    for intent, strategies in INTENT_STRATEGIES.items():
        for strategy in strategies:
            store.upsert_config(
                entity_type="policy",
                entity_id=f"{intent}#{default_topic}#{strategy}",
                fields={
                    "domain":               domain,
                    "intent":               intent,
                    "topic":                default_topic,
                    "strategy_id":          strategy,
                    "policy_version":       "v1",
                    "exploration_constant": 1.0,
                    "ucb_algorithm":        "UCB",
                },
            )
            counts["policies"] += 1

    # ---- 5. Signal routing ---------------------------------------------
    for signal_name, (fmt_strength, ctn_strength) in SIGNAL_ROUTING.items():
        store.upsert_config(
            entity_type="signal_routing",
            entity_id=signal_name,
            fields={
                "signal_name":      signal_name,
                "format_relevant":  fmt_strength is not None,
                "content_relevant": ctn_strength is not None,
                "format_category":  fmt_strength,
                "content_category": ctn_strength,
            },
        )
        counts["signal_rules"] += 1

    # ---- 6. Reward scale -----------------------------------------------
    for category, value in REWARD_SCALE.items():
        if category is None:
            # NOT_RECORDED isn't a stored row — it's the absence of category
            continue
        store.upsert_config(
            entity_type="reward_scale",
            entity_id=category,
            fields={
                "reward_category":   category,
                "raw_reward":        value,
                # Normalize to [-1.0, 1.0] for UCB math
                "normalized_reward": float(value) / 2.0 if isinstance(value, (int, float)) else None,
            },
        )
        counts["reward_rules"] += 1

    return counts


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _intent_description(intent: str) -> str:
    return {
        "Decision":      "User wants a recommendation they can act on.",
        "Explanation":   "User wants to understand how something works.",
        "Comparison":    "User wants two or more options compared side by side.",
        "Instructional": "User wants step-by-step instructions.",
        "Definitional":  "User wants a quick definition.",
        "Evaluation":    "User wants validation of a plan they have already formed.",
        "unmapped":      "None of the DECIDE labels fit — fallback intent.",
    }.get(intent, "")
