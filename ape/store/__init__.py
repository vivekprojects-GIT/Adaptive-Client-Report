"""Store package — MongoDB-backed persistence (primary) plus the legacy SQLite store."""

# Primary store (per the production design)
from .mongo_store import (
    MongoStore,
    new_response_id,
    new_message_id,
    new_session_id,
    utcnow_iso,
    make_attribution_pk,
    COLD_START_AVG_REWARD,
    COLD_START_UCB_SCORE,
)
from .mongo_schema import (
    COL_CONFIG,
    COL_BANDIT_STATE,
    COL_TURN_RECORD,
    COL_MESSAGES,
    COL_ADMIN_AUDIT,
    ENTITY_INTENT,
    ENTITY_STRATEGY,
    ENTITY_REPORT_TYPE,
    ENTITY_TEMPLATE,
    ENTITY_INSTRUCTION,
    ENTITY_POLICY,
    ENTITY_SIGNAL_RULE,
    ENTITY_REWARD_RULE,
    REWARD_STATUS_PENDING,
    REWARD_STATUS_APPLIED,
    REWARD_STATUS_SKIPPED,
    STATUS_ACTIVE,
    STATUS_INACTIVE,
    STATUS_DRAFT,
)

# Legacy SQLite store kept for reference / migration. Not used at runtime.
from .store import SqliteStore, new_turn_id

__all__ = [
    # MongoDB
    "MongoStore",
    "new_response_id",
    "new_message_id",
    "new_session_id",
    "utcnow_iso",
    "make_attribution_pk",
    "COLD_START_AVG_REWARD",
    "COLD_START_UCB_SCORE",
    "COL_CONFIG", "COL_BANDIT_STATE", "COL_TURN_RECORD", "COL_MESSAGES", "COL_ADMIN_AUDIT",
    "ENTITY_INTENT", "ENTITY_STRATEGY", "ENTITY_INSTRUCTION",
    "ENTITY_POLICY", "ENTITY_SIGNAL_RULE", "ENTITY_REWARD_RULE",
    "REWARD_STATUS_PENDING", "REWARD_STATUS_APPLIED", "REWARD_STATUS_SKIPPED",
    "STATUS_ACTIVE", "STATUS_INACTIVE", "STATUS_DRAFT",
    # Legacy SQLite
    "SqliteStore",
    "new_turn_id",
]
