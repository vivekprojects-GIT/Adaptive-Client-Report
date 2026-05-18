"""
SQLite schema definitions for APE's three tables.

Tables:
  1. sessions       — chat threads (UI metadata)
  2. turn_record    — append-only audit log (one row per finalized turn)
  3. bandit_state   — per-user learning state, PK = (user, topic, intent, strategy)

Design invariants:
  - turn_record is append-only; never UPDATE
  - bandit_state can be REBUILT from turn_record (cache, not source of truth)
  - sessions don't partition the bandit; they only group turns for the UI
"""

from __future__ import annotations


CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id      TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    last_active_at  TEXT NOT NULL,
    ended_at        TEXT,
    title           TEXT,
    turn_count      INTEGER NOT NULL DEFAULT 0
);
"""


CREATE_TURN_RECORD = """
CREATE TABLE IF NOT EXISTS turn_record (
    turn_id              TEXT PRIMARY KEY,
    session_id           TEXT NOT NULL,
    user_id              TEXT NOT NULL,
    ts                   TEXT NOT NULL,

    -- Classification
    topic                TEXT,
    intent               TEXT NOT NULL,
    intent_confidence    REAL NOT NULL,
    low_confidence_flag  INTEGER NOT NULL DEFAULT 0,
    unmapped_name        TEXT,

    -- Selection
    selected_strategy    TEXT NOT NULL,
    selection_method     TEXT NOT NULL,

    -- Generation
    suggested_format     TEXT NOT NULL,
    rendered_format      TEXT NOT NULL,
    format_compliance    INTEGER NOT NULL,

    -- Signals + rewards
    ui_signal            TEXT,
    llm_signal           TEXT,
    signal               TEXT,
    raw_ui_signals       TEXT,
    format_relevant      INTEGER NOT NULL DEFAULT 0,
    content_relevant     INTEGER NOT NULL DEFAULT 0,
    format_reward        INTEGER,
    content_reward       INTEGER,

    -- Conversation content
    query_text           TEXT,
    response_text        TEXT,

    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
"""


CREATE_BANDIT_STATE = """
CREATE TABLE IF NOT EXISTS bandit_state (
    user_id              TEXT NOT NULL,
    topic                TEXT NOT NULL,
    intent               TEXT NOT NULL,
    strategy             TEXT NOT NULL,

    format_count         INTEGER NOT NULL DEFAULT 0,
    format_total_reward  INTEGER NOT NULL DEFAULT 0,
    format_avg_reward    REAL    NOT NULL DEFAULT 0.0,

    content_count        INTEGER NOT NULL DEFAULT 0,
    content_total_reward INTEGER NOT NULL DEFAULT 0,
    content_avg_reward   REAL    NOT NULL DEFAULT 0.0,

    last_updated_at      TEXT,

    PRIMARY KEY (user_id, topic, intent, strategy)
);
"""


CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sessions_user_active ON sessions (user_id, last_active_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_tr_session   ON turn_record (session_id, ts);",
    "CREATE INDEX IF NOT EXISTS idx_tr_user_ts   ON turn_record (user_id, ts DESC);",
    "CREATE INDEX IF NOT EXISTS idx_tr_user_cell ON turn_record (user_id, topic, intent);",
    "CREATE INDEX IF NOT EXISTS idx_tr_intent    ON turn_record (intent);",
    "CREATE INDEX IF NOT EXISTS idx_bs_cell      ON bandit_state (user_id, topic, intent);",
]


ALL_CREATES = [CREATE_SESSIONS, CREATE_TURN_RECORD, CREATE_BANDIT_STATE]


# Required columns for each table — used by migrations to detect drift.
EXPECTED_TURN_RECORD_COLS = {
    "turn_id", "session_id", "user_id", "ts", "topic", "intent",
    "intent_confidence", "low_confidence_flag", "unmapped_name",
    "selected_strategy", "selection_method",
    "suggested_format", "rendered_format", "format_compliance",
    "ui_signal", "llm_signal", "signal", "raw_ui_signals",
    "format_relevant", "content_relevant", "format_reward", "content_reward",
    "query_text", "response_text",
}

EXPECTED_BANDIT_STATE_COLS = {
    "user_id", "topic", "intent", "strategy",
    "format_count", "format_total_reward", "format_avg_reward",
    "content_count", "content_total_reward", "content_avg_reward",
    "last_updated_at",
}

EXPECTED_SESSIONS_COLS = {
    "session_id", "user_id", "started_at", "last_active_at",
    "ended_at", "title", "turn_count",
}
