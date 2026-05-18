"""
SqliteStore — persistence for sessions, turn_record, and bandit_state.

API surface:
  - upsert_session(session_id, user_id, ts)
  - bump_session_activity(session_id, ts)
  - get_or_create_cell(user_id, topic, intent, strategies) -> snapshot
  - record_turn(turn: dict)
  - clear_user(user_id)
  - clear_all()
  - rebuild_bandit_state_from_turns()
  - db_snapshot(user_id, limit)

All writes go through a process-local lock. WAL journaling allows concurrent reads.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .schema import ALL_CREATES, CREATE_INDEXES


class SqliteStore:
    def __init__(self, path: str = "ape.db") -> None:
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    # ---- Schema lifecycle --------------------------------------------------

    def _init_schema(self) -> None:
        with self._lock:
            for ddl in ALL_CREATES:
                self.conn.executescript(ddl)
            for idx in CREATE_INDEXES:
                self.conn.execute(idx)
            self.conn.commit()

    # ---- Sessions ----------------------------------------------------------

    def upsert_session(self, session_id: str, user_id: str, ts: str) -> None:
        """Insert a session row if it doesn't exist; bump last_active_at if it does."""
        with self._lock:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO sessions (session_id, user_id, started_at, last_active_at, turn_count)
                    VALUES (?, ?, ?, ?, 0)
                    ON CONFLICT (session_id) DO UPDATE SET last_active_at = excluded.last_active_at
                    """,
                    (session_id, user_id, ts, ts),
                )

    def bump_session_activity(self, session_id: str, ts: str) -> None:
        with self._lock:
            with self.conn:
                self.conn.execute(
                    """
                    UPDATE sessions
                       SET last_active_at = ?,
                           turn_count     = turn_count + 1
                     WHERE session_id = ?
                    """,
                    (ts, session_id),
                )

    def end_session(self, session_id: str, ts: str) -> None:
        with self._lock:
            with self.conn:
                self.conn.execute(
                    "UPDATE sessions SET ended_at = ? WHERE session_id = ? AND ended_at IS NULL",
                    (ts, session_id),
                )

    # ---- Bandit cell read --------------------------------------------------

    def get_or_create_cell(
        self,
        user_id: str,
        topic: str,
        intent: str,
        strategies: List[str],
    ) -> Dict[str, Any]:
        """Lazy-init the cell's strategy rows, then return a snapshot.

        Snapshot shape:
          {
            "strategies": {
              name: { "format_count": int, "format_avg_reward": float,
                      "content_count": int, "content_avg_reward": float, ... },
              ...
            }
          }
        """
        with self._lock:
            with self.conn:
                for s in strategies:
                    self.conn.execute(
                        """
                        INSERT OR IGNORE INTO bandit_state
                          (user_id, topic, intent, strategy)
                        VALUES (?, ?, ?, ?)
                        """,
                        (user_id, topic, intent, s),
                    )

                rows = self.conn.execute(
                    """
                    SELECT strategy, format_count, format_total_reward, format_avg_reward,
                           content_count, content_total_reward, content_avg_reward
                    FROM bandit_state
                    WHERE user_id = ? AND topic = ? AND intent = ?
                    """,
                    (user_id, topic, intent),
                ).fetchall()

        return {
            "strategies": {
                r["strategy"]: {
                    "format_count":         r["format_count"],
                    "format_total_reward":  r["format_total_reward"],
                    "format_avg_reward":    r["format_avg_reward"],
                    "content_count":        r["content_count"],
                    "content_total_reward": r["content_total_reward"],
                    "content_avg_reward":   r["content_avg_reward"],
                }
                for r in rows
            },
        }

    # ---- Turn finalize (atomic write) --------------------------------------

    def record_turn(self, turn: Dict[str, Any]) -> None:
        """Persist a finalized turn and update bandit aggregates atomically.

        Rules:
          - Always: insert audit row into turn_record.
          - If format_relevant AND format_reward is not None: bump format_* on bandit_state.
          - If content_relevant AND content_reward is not None: bump content_* on bandit_state.
          - Bump sessions.turn_count and last_active_at.
        """
        user_id  = turn["user_id"]
        topic    = turn.get("topic") or "general"
        intent   = turn["intent"]
        strategy = turn["selected_strategy"]
        ts       = turn["ts"]

        with self._lock:
            cur = self.conn.cursor()
            cur.execute("BEGIN")
            try:
                # 1) Audit row
                cur.execute(
                    """
                    INSERT INTO turn_record (
                      turn_id, session_id, user_id, ts,
                      topic, intent, intent_confidence, low_confidence_flag, unmapped_name,
                      selected_strategy, selection_method,
                      suggested_format, rendered_format, format_compliance,
                      ui_signal, llm_signal, signal, raw_ui_signals,
                      format_relevant, content_relevant, format_reward, content_reward,
                      query_text, response_text
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        turn["turn_id"], turn["session_id"], user_id, ts,
                        topic, intent, float(turn["intent_confidence"]),
                        int(turn.get("low_confidence_flag", 0)),
                        turn.get("unmapped_name"),
                        strategy, turn["selection_method"],
                        turn["suggested_format"], turn["rendered_format"], int(turn["format_compliance"]),
                        turn.get("ui_signal"), turn.get("llm_signal"), turn.get("signal"),
                        json.dumps(turn.get("raw_ui_signals") or []),
                        int(turn.get("format_relevant", 0)), int(turn.get("content_relevant", 0)),
                        turn.get("format_reward"), turn.get("content_reward"),
                        turn.get("query_text"), turn.get("response_text"),
                    ),
                )

                # 2) Format-axis update
                if turn.get("format_relevant") and turn.get("format_reward") is not None:
                    fr = int(turn["format_reward"])
                    cur.execute(
                        """
                        UPDATE bandit_state
                           SET format_count        = format_count + 1,
                               format_total_reward = format_total_reward + ?,
                               format_avg_reward   = (format_total_reward + ?) * 1.0 / (format_count + 1),
                               last_updated_at     = ?
                         WHERE user_id = ? AND topic = ? AND intent = ? AND strategy = ?
                        """,
                        (fr, fr, ts, user_id, topic, intent, strategy),
                    )

                # 3) Content-axis update
                if turn.get("content_relevant") and turn.get("content_reward") is not None:
                    cr = int(turn["content_reward"])
                    cur.execute(
                        """
                        UPDATE bandit_state
                           SET content_count        = content_count + 1,
                               content_total_reward = content_total_reward + ?,
                               content_avg_reward   = (content_total_reward + ?) * 1.0 / (content_count + 1),
                               last_updated_at      = ?
                         WHERE user_id = ? AND topic = ? AND intent = ? AND strategy = ?
                        """,
                        (cr, cr, ts, user_id, topic, intent, strategy),
                    )

                # 4) Session bookkeeping
                cur.execute(
                    """
                    UPDATE sessions
                       SET last_active_at = ?,
                           turn_count     = turn_count + 1
                     WHERE session_id = ?
                    """,
                    (ts, turn["session_id"]),
                )

                cur.execute("COMMIT")
            except Exception:
                cur.execute("ROLLBACK")
                raise

    # ---- Admin -------------------------------------------------------------

    def clear_user(self, user_id: str) -> Dict[str, int]:
        """Delete all of a user's data (sessions, turns, bandit state)."""
        with self._lock:
            with self.conn:
                tr = self.conn.execute("DELETE FROM turn_record WHERE user_id = ?", (user_id,))
                bs = self.conn.execute("DELETE FROM bandit_state WHERE user_id = ?", (user_id,))
                ss = self.conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        return {
            "turn_record_deleted": tr.rowcount,
            "bandit_state_deleted": bs.rowcount,
            "sessions_deleted": ss.rowcount,
        }

    def clear_all(self) -> None:
        with self._lock:
            with self.conn:
                self.conn.execute("DELETE FROM turn_record")
                self.conn.execute("DELETE FROM bandit_state")
                self.conn.execute("DELETE FROM sessions")

    def rebuild_bandit_state_from_turns(self) -> int:
        """Rebuild bandit_state by re-aggregating turn_record.

        Useful after changing the reward function or repairing drift.
        Returns the number of rows written.
        """
        with self._lock:
            with self.conn:
                self.conn.execute("DELETE FROM bandit_state")
                self.conn.execute(
                    """
                    INSERT INTO bandit_state (
                      user_id, topic, intent, strategy,
                      format_count, format_total_reward, format_avg_reward,
                      content_count, content_total_reward, content_avg_reward
                    )
                    SELECT
                      user_id, topic, intent, selected_strategy,
                      COALESCE(SUM(CASE WHEN format_relevant = 1 AND format_reward IS NOT NULL
                                        THEN 1 ELSE 0 END), 0),
                      COALESCE(SUM(CASE WHEN format_relevant = 1 AND format_reward IS NOT NULL
                                        THEN format_reward ELSE 0 END), 0),
                      COALESCE(AVG(CASE WHEN format_relevant = 1 AND format_reward IS NOT NULL
                                        THEN format_reward ELSE NULL END), 0.0),
                      COALESCE(SUM(CASE WHEN content_relevant = 1 AND content_reward IS NOT NULL
                                        THEN 1 ELSE 0 END), 0),
                      COALESCE(SUM(CASE WHEN content_relevant = 1 AND content_reward IS NOT NULL
                                        THEN content_reward ELSE 0 END), 0),
                      COALESCE(AVG(CASE WHEN content_relevant = 1 AND content_reward IS NOT NULL
                                        THEN content_reward ELSE NULL END), 0.0)
                    FROM turn_record
                    WHERE topic IS NOT NULL
                    GROUP BY user_id, topic, intent, selected_strategy
                    """
                )
                rebuilt = self.conn.execute("SELECT COUNT(*) FROM bandit_state").fetchone()[0]
        return int(rebuilt)

    # ---- Read helpers (used by API admin endpoints) ------------------------

    def db_snapshot(self, user_id: Optional[str] = None, limit: int = 30) -> Dict[str, Any]:
        """Aggregated view used by the chat sidebar's DB inspector."""
        conn = self.conn
        stats_rows = conn.execute(
            """
            SELECT user_id, topic, intent, strategy,
                   format_count, format_avg_reward, content_count, content_avg_reward
            FROM bandit_state
            WHERE format_count > 0 OR content_count > 0
              AND (? IS NULL OR user_id = ?)
            ORDER BY user_id, intent, topic, strategy
            """,
            (user_id, user_id),
        ).fetchall()

        turns_rows: List[sqlite3.Row] = []
        if user_id:
            turns_rows = conn.execute(
                """
                SELECT ts, topic, intent, selected_strategy, selection_method,
                       suggested_format, rendered_format, format_compliance,
                       signal, format_reward, content_reward,
                       substr(query_text, 1, 80) AS qt
                FROM turn_record
                WHERE user_id = ?
                ORDER BY ts DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

        return {
            "bandit_state": [dict(r) for r in stats_rows],
            "turns":        [dict(r) for r in turns_rows],
            "user_id":      user_id,
        }


def new_turn_id() -> str:
    return str(uuid.uuid4())


def new_session_id(user_id: str) -> str:
    return f"sess_{user_id}_{uuid.uuid4().hex[:10]}"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
