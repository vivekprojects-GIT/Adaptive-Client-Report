"""
MongoStore — persistence for APE on MongoDB.

Implements the 4-collection design from APE_Final_DynamoDB_Production_Design_UCB_Corrected.docx:

  1. ape_config           — admin-managed configuration
  2. ape_user_bandit_state — per-user bandit cells
  3. ape_turn_record      — response-level records with attribution
  4. ape_admin_audit      — config change audit log

Critical invariants enforced by this layer:

  - Reward attribution is response-id-targeted. Path B looks up turn_record
    by response_id; the bandit row to update is denormalized into
    attribution_bandit_pk/sk on the response record.

  - reward_status starts at PENDING (Path A write) and transitions to
    APPLIED (Path B write). A conditional update prevents double-rewarding.

  - cached_ucb is a serving cache. format_count + total_reward + avg_reward
    are the source of truth. After every reward, Path B recomputes
    cached_ucb for ALL strategies in the same cell (because the explore
    bonus depends on N = sum of counts in the cell).

  - Raw queries are NOT stored. Only classification + attribution metadata.
"""

from __future__ import annotations

import math
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError
from pymongo.server_api import ServerApi

from .mongo_schema import (
    COL_ADMIN_AUDIT,
    COL_BANDIT_STATE,
    COL_CONFIG,
    COL_MESSAGES,
    COL_TURN_RECORD,
    COL_USER_DIRECTORY,
    REWARD_STATUS_APPLIED,
    REWARD_STATUS_PENDING,
    REWARD_STATUS_SKIPPED,
    STATUS_ACTIVE,
    apply_indexes,
)


# ----------------------------------------------------------------------------
# Cold-start prior for new bandit cells
# ----------------------------------------------------------------------------
COLD_START_AVG_REWARD = 0.5     # neutral prior
COLD_START_UCB_SCORE  = 999.0   # high exploration → picked first


# ----------------------------------------------------------------------------
# JSON-safety helpers for the audit log
#
# Mongo docs carry an `_id: ObjectId(...)` that breaks FastAPI's jsonable
# encoder. Strip it from anything we plan to send back over the wire.
# ----------------------------------------------------------------------------

def _strip_mongo_id(d):
    if d is None:
        return None
    if not isinstance(d, dict):
        return d
    out = {k: v for k, v in d.items() if k != "_id"}
    return out


def _scrub_audit_row(r):
    """Drop _id at the top level and inside the nested before/after snapshots."""
    if r is None:
        return None
    r = _strip_mongo_id(r)
    if "before" in r:
        r["before"] = _strip_mongo_id(r["before"])
    if "after" in r:
        r["after"] = _strip_mongo_id(r["after"])
    return r


# ----------------------------------------------------------------------------
# MongoStore class
# ----------------------------------------------------------------------------

class MongoStore:
    """MongoDB-backed persistence with the 4-collection layout from the design."""

    def __init__(
        self,
        uri: Optional[str] = None,
        db_name: Optional[str] = None,
        ucb_c: float = 1.0,
    ) -> None:
        env_uri = os.getenv("APE_MONGO_URI")
        uri = uri or env_uri or "mongodb://localhost:27017"
        db_name = db_name or os.getenv("APE_MONGO_DB", "ape")

        # Log the URI we're about to use, with credentials masked. If this
        # says "localhost:27017" in a container, the APE_MONGO_URI secret
        # isn't being read — set it in your environment / Space settings.
        masked = _mask_mongo_uri(uri)
        print(f"[MongoStore] connecting to: {masked}  db={db_name}", flush=True)
        if env_uri is None and not uri.startswith("mongodb+srv://"):
            print(
                "[MongoStore] WARNING: APE_MONGO_URI is not set — falling back "
                "to localhost. In a container/Space this will fail with "
                "'Connection refused'. Set APE_MONGO_URI in your environment.",
                flush=True,
            )

        # Atlas connection strings start with "mongodb+srv://" and benefit from
        # the stable Server API. Local mongod doesn't need it.
        is_atlas = uri.startswith("mongodb+srv://")
        if is_atlas:
            self.client = MongoClient(uri, server_api=ServerApi("1"))
        else:
            self.client = MongoClient(uri)

        self.db = self.client[db_name]
        self.ucb_c = float(os.getenv("APE_UCB_C", ucb_c))
        apply_indexes(self.db)

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------
    @property
    def config(self) -> Collection:        return self.db[COL_CONFIG]
    @property
    def bandit_state(self) -> Collection:  return self.db[COL_BANDIT_STATE]
    @property
    def turn_record(self) -> Collection:   return self.db[COL_TURN_RECORD]
    @property
    def messages(self) -> Collection:      return self.db[COL_MESSAGES]
    @property
    def admin_audit(self) -> Collection:   return self.db[COL_ADMIN_AUDIT]
    @property
    def user_directory(self) -> Collection: return self.db[COL_USER_DIRECTORY]

    # ==================================================================
    # User directory — display-name lookup keyed by user_id_hash.
    # In prod this would be a join against the CRM; we keep a thin shim
    # here so the analytics UI can show friendly names without admin
    # having to type them.
    # ==================================================================

    def upsert_user_directory_entry(
        self,
        user_id_hash: str,
        display_name: str,
        email: str = "",
        source: str = "manual",
        do_not_contact: bool = False,
        compliance_eligible: bool = True,
        last_contacted_at: Optional[str] = None,
    ) -> None:
        """Idempotent — call as many times as needed.

        Compliance gates (read by the analytics layer before surfacing a user
        as outreach-ready):
          do_not_contact      — hard opt-out; supersedes everything
          compliance_eligible — false if jurisdictional / regulatory check failed
          last_contacted_at   — ISO ts of most recent outreach; consumers can
                                enforce cooldowns based on this
        """
        from datetime import datetime, timezone
        doc = {
            "user_id_hash":         user_id_hash,
            "display_name":         display_name,
            "email":                email,
            "source":               source,
            "do_not_contact":       bool(do_not_contact),
            "compliance_eligible":  bool(compliance_eligible),
            "updated_at":           datetime.now(timezone.utc).isoformat(),
        }
        if last_contacted_at is not None:
            doc["last_contacted_at"] = last_contacted_at
        self.user_directory.update_one(
            {"user_id_hash": user_id_hash},
            {"$set": doc},
            upsert=True,
        )

    def get_display_names(self, user_id_hashes):
        """Bulk lookup: returns {user_id_hash: display_name} for the given hashes.
        Missing entries get the truncated hash as a fallback."""
        if not user_id_hashes:
            return {}
        rows = self.user_directory.find({"user_id_hash": {"$in": list(user_id_hashes)}})
        names = {r["user_id_hash"]: r.get("display_name") or r["user_id_hash"] for r in rows}
        for h in user_id_hashes:
            names.setdefault(h, h[:10] + "…" if h and len(h) > 10 else (h or "—"))
        return names

    def get_directory_entries(self, user_id_hashes):
        """Bulk lookup: returns full directory rows keyed by user_id_hash.
        Used by analytics to read compliance flags + display name in one query.
        """
        if not user_id_hashes:
            return {}
        rows = self.user_directory.find({"user_id_hash": {"$in": list(user_id_hashes)}})
        return {r["user_id_hash"]: r for r in rows}

    def get_directory_entry(self, user_id_hash: str):
        return self.user_directory.find_one({"user_id_hash": user_id_hash})

    def list_directory(self, limit: int = 200):
        return list(self.user_directory.find().limit(limit))

    # ==================================================================
    # CONFIG (admin-managed)
    # ==================================================================
    #
    # Documents in ape_config:
    #   {
    #     entity_type:  "intent" | "strategy" | "instruction" | "policy" |
    #                    "signal_routing" | "reward_scale"
    #     entity_id:    <e.g. "Comparison" | "comparison_table" | "thumbs_up">
    #     version:      "v1" / "v2" / ... (mostly for instructions; "_" for others)
    #     status:       "ACTIVE" | "INACTIVE" | "DRAFT"
    #     ...entity-specific fields...
    #     ts:           ISO-8601 UTC
    #   }
    # ==================================================================

    def upsert_config(self, entity_type: str, entity_id: str, fields: Dict[str, Any],
                      version: str = "_", status: str = STATUS_ACTIVE) -> None:
        """Insert or replace a config item by (entity_type, entity_id, version)."""
        doc = {
            "entity_type": entity_type,
            "entity_id":   entity_id,
            "version":     version,
            "status":      status,
            "ts":          utcnow_iso(),
            **fields,
        }
        self.config.update_one(
            {"entity_type": entity_type, "entity_id": entity_id, "version": version},
            {"$set": doc},
            upsert=True,
        )

    def get_active_config(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Return the active document for a config entity (by entity_type + entity_id)."""
        return self.config.find_one(
            {"entity_type": entity_type, "entity_id": entity_id, "status": STATUS_ACTIVE}
        )

    def delete_config(
        self,
        entity_type: str,
        entity_id: str,
        version: Optional[str] = None,
        extra_filter: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Hard-delete a config document.

        Composite entity_ids (e.g. policy rows keyed by domain+intent+topic+strategy)
        can pass an `extra_filter` to scope the deletion. Returns count deleted.
        """
        q: Dict[str, Any] = {"entity_type": entity_type, "entity_id": entity_id}
        if version is not None:
            q["version"] = version
        if extra_filter:
            q.update(extra_filter)
        return self.config.delete_many(q).deleted_count

    def list_active_config(self, entity_type: str) -> List[Dict[str, Any]]:
        """All ACTIVE documents of a given entity_type. Used by the runtime
        path — pausing a config doc removes it from this list."""
        return list(self.config.find({"entity_type": entity_type, "status": STATUS_ACTIVE}))

    def list_all_config(self, entity_type: str) -> List[Dict[str, Any]]:
        """ALL documents of a given entity_type regardless of status.
        Used by the admin UI so paused entries stay visible and re-activatable."""
        return list(self.config.find({"entity_type": entity_type}))

    def set_config_status(
        self,
        entity_type: str,
        entity_id: str,
        new_status: str,
        version: Optional[str] = None,
    ) -> int:
        """Flip the status field on a config doc. Returns count modified.

        Doesn't touch any other fields — preserves the document. Runtime reads
        (get_active_config, list_active_config, get_policy_strategies,
        eligible_offers_for_user) all filter on status=ACTIVE, so flipping to
        INACTIVE immediately removes the doc from the runtime path.
        """
        q: Dict[str, Any] = {"entity_type": entity_type, "entity_id": entity_id}
        if version is not None:
            q["version"] = version
        return self.config.update_many(q, {"$set": {"status": new_status}}).modified_count

    def get_signal_routing(self, signal_name: str) -> Optional[Dict[str, Any]]:
        return self.get_active_config("signal_routing", signal_name)

    def get_reward_scale(self, category: str) -> Optional[Dict[str, Any]]:
        return self.get_active_config("reward_scale", category)

    def get_policy_strategies(self, domain: str, intent: str, topic: str) -> List[Dict[str, Any]]:
        """Return policy documents listing the allowed strategies for a cell."""
        return list(self.config.find({
            "entity_type": "policy",
            "domain":      domain,
            "intent":      intent,
            "topic":       topic,
            "status":      STATUS_ACTIVE,
        }))

    # ==================================================================
    # BANDIT STATE (per-user, per-cell aggregates)
    # ==================================================================
    #
    # Each document is one strategy row in one cell:
    #   {
    #     user_id_hash, domain, intent, topic, strategy,
    #     count, total_reward, avg_reward,
    #     cached_ucb, policy_version, ucb_algorithm,
    #     last_updated_at,
    #   }
    # ==================================================================

    def get_or_create_bandit_cell(
        self,
        user_id_hash: str,
        domain: str,
        intent: str,
        topic: str,
        strategies: List[str],
        policy_version: str = "v1",
    ) -> List[Dict[str, Any]]:
        """Lazy-create one row per strategy in the cell, then return all rows.

        New rows are seeded with cold-start values so UCB exploration kicks in
        on the very first selection.
        """
        # Lazy-insert any missing strategy rows
        for s in strategies:
            self.bandit_state.update_one(
                {
                    "user_id_hash": user_id_hash,
                    "domain":       domain,
                    "intent":       intent,
                    "topic":        topic,
                    "strategy":     s,
                },
                {
                    "$setOnInsert": {
                        "count":              0,
                        "total_reward":       0.0,
                        "avg_reward":         COLD_START_AVG_REWARD,
                        "cached_ucb":         COLD_START_UCB_SCORE,
                        "policy_version":     policy_version,
                        "ucb_algorithm":      "UCB",
                        "last_updated_at":    utcnow_iso(),
                    }
                },
                upsert=True,
            )
        # Read them back
        rows = list(self.bandit_state.find({
            "user_id_hash": user_id_hash,
            "domain":       domain,
            "intent":       intent,
            "topic":        topic,
        }))
        return rows

    def update_strategy_reward(
        self,
        attribution_pk: Dict[str, str],
        attribution_sk: str,
        normalized_reward: float,
    ) -> Optional[Dict[str, Any]]:
        """Apply a single reward to one strategy row.

        attribution_pk: {user_id_hash, domain, intent, topic}
        attribution_sk: strategy name

        Returns the updated row (post-update count/total/avg).
        """
        # Read current state
        row = self.bandit_state.find_one({**attribution_pk, "strategy": attribution_sk})
        if row is None:
            return None
        new_count        = row["count"] + 1
        new_total        = row["total_reward"] + float(normalized_reward)
        new_avg          = new_total / new_count
        updated = self.bandit_state.find_one_and_update(
            {**attribution_pk, "strategy": attribution_sk},
            {"$set": {
                "count":           new_count,
                "total_reward":    new_total,
                "avg_reward":      new_avg,
                "last_updated_at": utcnow_iso(),
            }},
            return_document=ReturnDocument.AFTER,
        )
        return updated

    def refresh_cell_ucb_cache(self, attribution_pk: Dict[str, str]) -> int:
        """Recompute cached_ucb for every strategy row in the cell.

        UCB: score = avg_reward + C * sqrt(ln(N) / count)
        where N = sum of counts across the whole cell.

        Unpulled arms (count = 0) get COLD_START_UCB_SCORE so they're
        still selected first by the cold-start rule.
        """
        rows = list(self.bandit_state.find(attribution_pk))
        N = sum(int(r["count"]) for r in rows)
        if N == 0:
            return 0

        ln_N = math.log(N) if N > 1 else 0.0
        updates = 0
        for r in rows:
            cnt = int(r["count"])
            if cnt == 0:
                new_ucb = COLD_START_UCB_SCORE
            else:
                new_ucb = float(r["avg_reward"]) + self.ucb_c * math.sqrt(ln_N / cnt)
            self.bandit_state.update_one(
                {"_id": r["_id"]},
                {"$set": {"cached_ucb": new_ucb, "last_updated_at": utcnow_iso()}},
            )
            updates += 1
        return updates

    # ==================================================================
    # TURN RECORD (response-level journal with attribution)
    # ==================================================================

    def write_pending_response(self, doc: Dict[str, Any]) -> None:
        """Path A — write the response record with reward_status=PENDING.

        Required fields in doc:
          response_id, user_id_hash, session_id_optional, ts,
          intent, topic, selected_strategy, rendered_format,
          ucb_at_selection, instruction_version,
          attribution_bandit_pk, attribution_bandit_sk
        """
        doc = {
            **doc,
            "reward_status": REWARD_STATUS_PENDING,
            "signal":            None,
            "reward_category":   None,
            "normalized_reward": None,
        }
        self.turn_record.insert_one(doc)

    def get_response(self, response_id: str) -> Optional[Dict[str, Any]]:
        return self.turn_record.find_one({"response_id": response_id})

    def mark_response_rewarded(
        self,
        response_id: str,
        user_id_hash: str,
        signal: str,
        reward_category: Optional[str],
        normalized_reward: Optional[float],
    ) -> Optional[Dict[str, Any]]:
        """Path B — atomically mark a response as APPLIED.

        Conditional on reward_status=PENDING and user_id_hash match — prevents
        double rewards and cross-user reward injection.

        Returns the post-update document, or None if the condition failed
        (which means either: response not found, wrong user, or already rewarded).
        """
        return self.turn_record.find_one_and_update(
            {
                "response_id":   response_id,
                "user_id_hash":  user_id_hash,
                "reward_status": REWARD_STATUS_PENDING,
            },
            {"$set": {
                "signal":            signal,
                "reward_category":   reward_category,
                "normalized_reward": normalized_reward,
                "reward_status":     REWARD_STATUS_APPLIED,
                "rewarded_at":       utcnow_iso(),
            }},
            return_document=ReturnDocument.AFTER,
        )

    def mark_response_skipped(self, response_id: str, user_id_hash: str, reason: str) -> None:
        """Path B — record that we considered but did not apply a reward."""
        self.turn_record.update_one(
            {
                "response_id":   response_id,
                "user_id_hash":  user_id_hash,
                "reward_status": REWARD_STATUS_PENDING,
            },
            {"$set": {
                "reward_status": REWARD_STATUS_SKIPPED,
                "skip_reason":   reason,
                "rewarded_at":   utcnow_iso(),
            }},
        )

    # ------------------------------------------------------------------
    # Pending-signals buffer (multi-signal resolver support)
    # ------------------------------------------------------------------
    def append_pending_signal(
        self,
        response_id: str,
        signal_entry: Dict[str, Any],
    ) -> bool:
        """Append one signal record to the response's pending_signals[] array.

        signal_entry shape:
          {"signal": str, "source": "ui"|"llm"|"derived"|"composite", "ts": iso}

        Only appends if the response is still PENDING. Returns True if appended,
        False if the response is missing or already finalized.
        """
        result = self.turn_record.update_one(
            {
                "response_id":   response_id,
                "reward_status": REWARD_STATUS_PENDING,
            },
            {"$push": {"pending_signals": signal_entry}},
        )
        return result.modified_count > 0

    def find_previous_pending_response(
        self,
        user_id_hash: str,
        session_id: Optional[str],
        max_age_sec: int = 600,
    ) -> Optional[Dict[str, Any]]:
        """Find the most recent PENDING response for this user/session.

        Used at the top of /turn to identify which prior response should
        be finalized now that the user has moved on. Bounded by max_age_sec
        so we don't pick up stale unfinalized rows from yesterday.
        """
        query: Dict[str, Any] = {
            "user_id_hash":  user_id_hash,
            "reward_status": REWARD_STATUS_PENDING,
        }
        if session_id:
            query["session_id_optional"] = session_id
        # Cutoff = now − max_age_sec
        cutoff_dt = datetime.utcnow() - timedelta(seconds=max_age_sec)
        query["ts"] = {"$gte": cutoff_dt.strftime("%Y-%m-%dT00:00:00")}
        return self.turn_record.find_one(query, sort=[("ts", -1)])

    def get_response_age_seconds(self, response_id: str) -> Optional[float]:
        """Return seconds elapsed since the response was created. None if missing."""
        resp = self.turn_record.find_one(
            {"response_id": response_id},
            projection={"ts": 1, "_id": 0},
        )
        if not resp or "ts" not in resp:
            return None
        try:
            ts = resp["ts"]
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            dt = datetime.fromisoformat(ts)
            now = datetime.utcnow()
            # Strip tz info for naive subtraction
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return (now - dt).total_seconds()
        except (ValueError, TypeError):
            return None

    def list_user_responses(self, user_id_hash: str, limit: int = 50) -> List[Dict[str, Any]]:
        return list(self.turn_record.find(
            {"user_id_hash": user_id_hash}
        ).sort("ts", -1).limit(limit))

    def list_session_responses(
        self,
        session_id: str,
        limit: int = 100,
        user_id_hash: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        q: Dict[str, Any] = {"session_id_optional": session_id}
        if user_id_hash:
            q["user_id_hash"] = user_id_hash
        return list(self.turn_record.find(q).sort("ts", 1).limit(limit))

    # ==================================================================
    # CONVERSATION MESSAGES (raw user + assistant text)
    # ==================================================================
    #
    # One document per message. Roles are "user" or "assistant". Assistant
    # messages carry response_id + rendered_format so the UI can attach
    # bandit metadata chips and feedback buttons.
    # ==================================================================

    def append_message(
        self,
        message_id: str,
        user_id_hash: str,
        session_id: str,
        role: str,
        content: str,
        ts: str,
        response_id: Optional[str] = None,
        rendered_format: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        doc = {
            "message_id":      message_id,
            "user_id_hash":    user_id_hash,
            "session_id":      session_id,
            "ts":              ts,
            "role":            role,
            "content":         content,
            "response_id":     response_id,
            "rendered_format": rendered_format,
            "meta":            meta or {},
        }
        self.messages.insert_one(doc)

    def list_session_messages(
        self,
        session_id: str,
        limit: int = 200,
        user_id_hash: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return all messages in a session, ordered by ts ascending (chat order)."""
        q: Dict[str, Any] = {"session_id": session_id}
        if user_id_hash:
            q["user_id_hash"] = user_id_hash
        return list(self.messages.find(q).sort("ts", 1).limit(limit))

    def list_user_sessions(self, user_id_hash: str, limit: int = 20) -> List[Dict[str, Any]]:
        """List a user's distinct sessions with a short preview of the first user message.

        Uses an aggregation: group by session_id, capture first message text,
        last activity timestamp, and message count.
        """
        pipeline = [
            {"$match": {"user_id_hash": user_id_hash}},
            {"$sort": {"ts": 1}},
            {"$group": {
                "_id":            "$session_id",
                "session_id":     {"$first": "$session_id"},
                "started_at":     {"$first": "$ts"},
                "last_active_at": {"$last":  "$ts"},
                "first_user_message": {
                    "$first": {
                        "$cond": [{"$eq": ["$role", "user"]}, "$content", None],
                    },
                },
                "message_count": {"$sum": 1},
            }},
            {"$sort":  {"last_active_at": -1}},
            {"$limit": limit},
            {"$project": {"_id": 0}},
        ]
        return list(self.messages.aggregate(pipeline))

    def latest_session_for_user(self, user_id_hash: str) -> Optional[str]:
        """Return the user's most-recent session_id, or None."""
        doc = self.messages.find_one(
            {"user_id_hash": user_id_hash},
            sort=[("ts", -1)],
            projection={"session_id": 1, "_id": 0},
        )
        return (doc or {}).get("session_id")

    def history_for_llm(self, session_id: str, limit: int = 30) -> List[Dict[str, str]]:
        """Return the last N messages in a session as the {role, content} list
        the LLM expects. Newest at the end of the list.
        """
        rows = list(
            self.messages.find(
                {"session_id": session_id},
                projection={"role": 1, "content": 1, "_id": 0, "ts": 1},
            ).sort("ts", -1).limit(limit)
        )
        rows.reverse()
        return [{"role": r["role"], "content": r["content"]} for r in rows]

    # ==================================================================
    # ADMIN AUDIT
    # ==================================================================

    def log_admin_action(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        changed_by: str,
        before: Optional[Dict[str, Any]] = None,
        after:  Optional[Dict[str, Any]] = None,
    ) -> None:
        ts = utcnow_iso()
        self.admin_audit.insert_one({
            "action_id":   str(uuid.uuid4()),
            "date":        ts[:10],
            "ts":          ts,
            "action_type": action_type,
            "entity_type": entity_type,
            "entity_id":   entity_id,
            "changed_by":  changed_by,
            # Strip the Mongo _id from snapshot dicts — it's an ObjectId and
            # FastAPI's jsonable_encoder can't serialize that when the audit
            # log is later read back by list_audit.
            "before":      _strip_mongo_id(before),
            "after":       _strip_mongo_id(after),
        })

    def list_audit(self, date: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        q: Dict[str, Any] = {}
        if date:
            q["date"] = date
        rows = list(self.admin_audit.find(q).sort("ts", -1).limit(limit))
        # Defensive: scrub _id from each audit row + nested before/after snapshots.
        # Older entries written before the _strip_mongo_id fix still carry _id
        # in their `before` dicts, so we strip on read too.
        return [_scrub_audit_row(r) for r in rows]

    # ==================================================================
    # ADMIN / OPS HELPERS
    # ==================================================================

    def clear_user(self, user_id_hash: str) -> Dict[str, int]:
        tr = self.turn_record.delete_many({"user_id_hash": user_id_hash})
        bs = self.bandit_state.delete_many({"user_id_hash": user_id_hash})
        ms = self.messages.delete_many({"user_id_hash": user_id_hash})
        return {
            "turn_record_deleted":  tr.deleted_count,
            "bandit_state_deleted": bs.deleted_count,
            "messages_deleted":     ms.deleted_count,
        }

    def clear_user_session(self, user_id_hash: str, session_id: str) -> Dict[str, int]:
        """Delete just one session's messages — leaves the bandit state intact."""
        ms = self.messages.delete_many({
            "user_id_hash": user_id_hash,
            "session_id":   session_id,
        })
        # Also remove the response records for this session so analytics line up.
        tr = self.turn_record.delete_many({
            "user_id_hash":         user_id_hash,
            "session_id_optional":  session_id,
        })
        return {
            "messages_deleted":    ms.deleted_count,
            "turn_record_deleted": tr.deleted_count,
        }

    def clear_all_runtime(self) -> Dict[str, int]:
        """Clear runtime collections but preserve config + admin_audit."""
        return {
            "turn_record_deleted":  self.turn_record.delete_many({}).deleted_count,
            "bandit_state_deleted": self.bandit_state.delete_many({}).deleted_count,
            "messages_deleted":     self.messages.delete_many({}).deleted_count,
        }

    def db_snapshot(self, user_id_hash: Optional[str] = None, limit: int = 30) -> Dict[str, Any]:
        """Aggregated view for the chat sidebar and analytics page."""
        bandit_q: Dict[str, Any] = {"count": {"$gt": 0}}
        if user_id_hash:
            bandit_q["user_id_hash"] = user_id_hash
        bandit_rows = list(self.bandit_state.find(bandit_q).limit(500))

        turn_rows: List[Dict[str, Any]] = []
        if user_id_hash:
            turn_rows = list(self.turn_record.find(
                {"user_id_hash": user_id_hash}
            ).sort("ts", -1).limit(limit))

        return {
            "bandit_state": [_clean(r) for r in bandit_rows],
            "turns":        [_clean(r) for r in turn_rows],
            "user_id_hash": user_id_hash,
        }


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------

def _clean(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Drop Mongo's _id field for cleaner API responses."""
    out = dict(doc)
    out.pop("_id", None)
    return out


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mask_mongo_uri(uri: str) -> str:
    """Return a log-safe version of a Mongo URI with credentials redacted."""
    import re
    # Pattern: scheme://user:password@host  →  scheme://user:***@host
    return re.sub(r"://([^:/@]+):([^@]+)@", r"://\1:***@", uri)


def new_response_id() -> str:
    return f"resp_{uuid.uuid4().hex[:12]}"


def new_message_id() -> str:
    return f"msg_{uuid.uuid4().hex[:12]}"


def new_session_id(user_id_hash: str) -> str:
    return f"sess_{user_id_hash}_{uuid.uuid4().hex[:10]}"


def make_attribution_pk(user_id_hash: str, domain: str, intent: str, topic: str) -> Dict[str, str]:
    """Build the attribution_bandit_pk dict that Path B uses for exact lookup."""
    return {
        "user_id_hash": user_id_hash,
        "domain":       domain,
        "intent":       intent,
        "topic":        topic,
    }
