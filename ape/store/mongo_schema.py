"""
MongoDB schema for APE — 8 collections (7 APE-owned + 1 optional directory).

Each collection has a clearly scoped role. The three keys that flow through
the system play distinct, non-overlapping parts:

  user_id_hash   personalization key       (bandit state, analytics scope)
  response_id    reward attribution key    (Path B targets one exact response)
  session_id     conversation grouping     (UI resume / debugging ONLY — never
                                            a learning or reward key)

═════════════════════════════════════════════════════════════════════════════
LAYERS
═════════════════════════════════════════════════════════════════════════════

1. CHAT HISTORY (raw content lives here — and only here)

   ape_messages         Conversation transcript for UI resume + debugging.
                        message_id (PK), session_id, user_id_hash, role,
                        content (RAW user text + assistant text), ts,
                        response_id (assistant rows only — joins to turn_record).
                        Indexed by (session_id, ts) for one-query thread load.

                        ⚠ Privacy boundary: raw text is stored ONLY here.
                          It is NEVER copied into bandit state, turn records,
                          or analytics aggregates. The analytics recompute
                          reads ape_turn_record exclusively — it does not
                          scan messages. In production, this collection
                          should have:
                             • TTL / retention policy
                             • At-rest encryption
                             • Access control distinct from analytics readers
                             • Be excluded from analytics ETL jobs

2. RUNTIME LEARNING (structured metadata only — no raw text)

   ape_user_bandit_state  Personalized bandit cells.
                          PK = (user_id_hash, domain, intent, topic)
                          SK = strategy
                          Fields: count, total_reward, avg_reward, cached_ucb,
                                  policy_version, ucb_algorithm,
                                  last_updated_at.
                          One row per (user × cell × strategy arm).

   ape_turn_record        Response-level attribution & reward log.
                          PK = response_id (UUID — exact reward target)
                          Fields: user_id_hash, session_id (grouping only,
                                  not used for learning), ts, domain, intent,
                                  topic, selected_strategy, rendered_format,
                                  format_compliance, attribution_bandit_pk/sk,
                                  ucb_at_selection, instruction_version,
                                  reward_status (PENDING → APPLIED),
                                  signal, reward_category, normalized_reward.

                          This is the source of truth for analytics recompute.

3. ADMIN CONFIG (versioned, status-gated)

   ape_config           All admin-managed config, discriminated by entity_type:
                        intent · strategy · instruction · policy ·
                        signal_routing · reward_scale · offer_policy
                        PK = (entity_type, entity_id, version)
                        Status: ACTIVE / INACTIVE / DRAFT — runtime reads
                        filter on status=ACTIVE.

   ape_admin_audit      Append-only audit log of every config change.
                        action_id (PK), date, ts, action_type, entity_type,
                        entity_id, before, after, changed_by.

4. ANALYTICS AGGREGATES (derived, admin-recomputed from ape_turn_record)

   ape_user_topic_interest  Per-(user, topic) precomputed interest.
                            PK = (user_id_hash, domain, topic)
                            interest_score = 0.40·freq + 0.25·recency +
                                             0.25·engagement + 0.10·followup
                            Drives: offer eligibility, topic interest table,
                                    active customers, offer readiness facet.

   ape_topic_trend_daily    Per-(date, topic) daily roll-up.
                            PK = (date, domain, topic)
                            trend_score = 0.4·norm_count + 0.3·growth/3 +
                                          0.2·density + 0.1·avg_reward
                            Drives: trending topics, platform overview.

5. DISPLAY JOIN (optional, sensitive)

   ape_user_directory   user_id_hash → display_name, email, compliance flags.
                        PK = user_id_hash
                        Used by admin UI to surface human names alongside
                        hashes. In PRODUCTION this should come from the CRM
                        or identity service — not be embedded in analytics
                        storage. The dashboard must still function when only
                        hashes are available (graceful fallback).

═════════════════════════════════════════════════════════════════════════════
ATTRIBUTION & PERSONALIZATION RULES (load-bearing)
═════════════════════════════════════════════════════════════════════════════

1. Feedback always targets `response_id`, never `session_id` or `user_id`.
   The bandit row to update is denormalized into the turn_record as
   `attribution_bandit_pk` + `attribution_bandit_sk` so Path B does an exact
   lookup instead of guessing.

2. Bandit learning is keyed by `user_id_hash` (per-user), not by session_id.
   A user resuming an old session continues their personalized cells; a user
   in a new session ALSO continues their personalized cells. Sessions are a
   UI construct, not a learning construct.

3. Analytics recompute reads `ape_turn_record` (structured metadata) — never
   `ape_messages` (raw text). This keeps the privacy boundary enforceable
   and makes the recompute fast (no NLP over message bodies).

4. Status gating: runtime reads (`get_active_config`, `get_policy_strategies`,
   `eligible_offers_for_user`, classifier intent lookup) all filter on
   `status=ACTIVE`. Admin pauses are reflected immediately in runtime
   behavior without deleting data.
"""

from __future__ import annotations


# ---- Collection names ------------------------------------------------------
COL_CONFIG              = "ape_config"
COL_BANDIT_STATE        = "ape_user_bandit_state"
COL_TURN_RECORD         = "ape_turn_record"
COL_MESSAGES            = "ape_messages"
COL_ADMIN_AUDIT         = "ape_admin_audit"
COL_USER_TOPIC_INTEREST = "ape_user_topic_interest"
COL_TOPIC_TREND_DAILY   = "ape_topic_trend_daily"
COL_USER_DIRECTORY      = "ape_user_directory"  # display-name lookup (separate from analytics; would live in CRM in prod)


# ---- Entity types within ape_config ---------------------------------------
ENTITY_INTENT       = "intent"
ENTITY_STRATEGY     = "strategy"
ENTITY_INSTRUCTION  = "instruction"
ENTITY_POLICY       = "policy"
ENTITY_SIGNAL_RULE  = "signal_routing"
ENTITY_REWARD_RULE  = "reward_scale"
ENTITY_OFFER_POLICY = "offer_policy"
ENTITY_BANDIT_CONFIG = "bandit_config"   # global UCB params (entity_id="ucb")

# ---- Adaptive client reporting (D1) ---------------------------------------
# The existing intent/strategy pair serves D2 — question intent -> answer
# format. D1 is a separate decision with its own vocabulary:
#
#   report_type   the kind of report. This is D1's DECISION CONTEXT, not an
#                 intent: it is selected when a report is requested, never
#                 inferred from language. `personalisable=False` marks
#                 prescribed reports whose format is set by regulation; they
#                 must never reach the bandit.
#   template      one approved report shape. This is D1's ARM. Arms are
#                 scoped to a report_type — a quarterly review's templates
#                 are not an annual review's. Carries a style_profile vector
#                 over the shared presentation dimensions, which is what lets
#                 a chat signal reach a template the client never received.
ENTITY_REPORT_TYPE  = "report_type"
ENTITY_TEMPLATE     = "template"


# ---- Index specifications --------------------------------------------------
#
# (collection, [(field, direction), ...], options)
# direction: 1 = ASC, -1 = DESC
#
# Run apply_indexes(db) on startup; pymongo will skip if already present.
# ---------------------------------------------------------------------------

INDEX_SPECS = [
    # Config — uniqueness on entity-specific key (entity_type + sub keys)
    (COL_CONFIG, [("entity_type", 1), ("entity_id", 1), ("version", 1)],
     {"unique": True, "name": "uniq_config_entity"}),
    (COL_CONFIG, [("entity_type", 1), ("status", 1)],
     {"name": "by_entity_status"}),
    (COL_CONFIG, [("entity_type", 1), ("domain", 1), ("intent", 1), ("topic", 1)],
     {"sparse": True, "name": "by_policy_cell"}),

    # Bandit state — composite unique on the cell+strategy key
    (COL_BANDIT_STATE,
     [("user_id_hash", 1), ("domain", 1), ("intent", 1), ("topic", 1), ("strategy", 1)],
     {"unique": True, "name": "uniq_bandit_cell_strategy"}),
    (COL_BANDIT_STATE,
     [("user_id_hash", 1), ("domain", 1), ("intent", 1), ("topic", 1)],
     {"name": "by_cell_for_query"}),

    # Turn record — exact-lookup by response_id is the unique key
    (COL_TURN_RECORD, [("response_id", 1)], {"unique": True, "name": "uniq_response_id"}),
    (COL_TURN_RECORD, [("user_id_hash", 1), ("ts", -1)], {"name": "by_user_time"}),
    (COL_TURN_RECORD, [("session_id_optional", 1), ("ts", -1)],
     {"sparse": True, "name": "by_session_time"}),
    (COL_TURN_RECORD, [("reward_status", 1)], {"name": "by_reward_status"}),

    # Messages — primary access patterns: load a session in order, list a user's sessions
    (COL_MESSAGES, [("message_id", 1)], {"unique": True, "name": "uniq_message_id"}),
    (COL_MESSAGES, [("session_id", 1), ("ts", 1)], {"name": "by_session_time"}),
    (COL_MESSAGES, [("user_id_hash", 1), ("ts", -1)], {"name": "by_user_time"}),
    (COL_MESSAGES, [("response_id", 1)], {"sparse": True, "name": "by_response_id"}),

    # Admin audit — by date for traceability
    (COL_ADMIN_AUDIT, [("date", -1), ("ts", -1)], {"name": "by_date_ts"}),
    (COL_ADMIN_AUDIT, [("entity_type", 1), ("entity_id", 1)], {"name": "by_entity"}),

    # User-topic interest — primary access: top topics for one user,
    # and "all users interested in topic X above threshold"
    (COL_USER_TOPIC_INTEREST,
     [("user_id_hash", 1), ("domain", 1), ("topic", 1)],
     {"unique": True, "name": "uniq_user_topic"}),
    (COL_USER_TOPIC_INTEREST,
     [("user_id_hash", 1), ("interest_score", -1)],
     {"name": "user_top_topics"}),
    (COL_USER_TOPIC_INTEREST,
     [("topic", 1), ("interest_score", -1)],
     {"name": "topic_top_users"}),

    # Topic trends — primary access: latest day across all topics,
    # and "trend for topic X over the last N days"
    (COL_TOPIC_TREND_DAILY,
     [("date", -1), ("domain", 1), ("topic", 1)],
     {"unique": True, "name": "uniq_date_topic"}),
    (COL_TOPIC_TREND_DAILY,
     [("date", -1), ("trend_score", -1)],
     {"name": "by_date_trend"}),

    # User directory — display-name lookup keyed by user_id_hash. Kept
    # OUTSIDE the analytics collections so the privacy boundary is explicit:
    # analytics layer reads it as a join, never the other way around.
    (COL_USER_DIRECTORY,
     [("user_id_hash", 1)],
     {"unique": True, "name": "uniq_user_directory_hash"}),
]


def apply_indexes(db) -> None:
    """Create all indexes idempotently. Safe to call on every startup."""
    for col_name, keys, options in INDEX_SPECS:
        col = db[col_name]
        col.create_index(keys, **options)


# ---- Reward status enum ----------------------------------------------------
REWARD_STATUS_PENDING = "PENDING"
REWARD_STATUS_APPLIED = "APPLIED"
REWARD_STATUS_SKIPPED = "SKIPPED"


# ---- Config status enum ----------------------------------------------------
STATUS_ACTIVE   = "ACTIVE"
STATUS_INACTIVE = "INACTIVE"
STATUS_DRAFT    = "DRAFT"
