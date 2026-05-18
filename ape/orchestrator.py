"""
Orchestrator — implements the production query-flow design.

Per-turn flow (Path A — strategy selection for current response):

  A1. Validate intent (read APE_Config / intent entity)
  A2. Read allowed strategies for (domain, intent, topic) (policy lookup)
  A3. Read strategy metadata + active instruction version
  A4. Query the user-personalized bandit state for this cell
  A5. Pick highest cached_ucb (lazy-create cell if missing)
  A6. Synthesizer LLM call → answer text + rendered_format
  A7. Write APE_Turn_Record with reward_status=PENDING and
      attribution_bandit_pk/sk denormalized for fast Path B lookup

Reward flow (Path B — applies to an exact response_id):

  B1. Read the response record by response_id (exact)
  B2. Validate user_id_hash + reward_status=PENDING (prevents double rewards)
  B3. Read signal routing rule (from config)
  B4. Read reward scale (from config)
  B5. Atomically mark response APPLIED with signal + reward
  B6. Apply reward to the strategy row pointed to by attribution_bandit_pk/sk
  B7. Refresh cached_ucb for ALL strategies in the cell

Raw queries are NOT stored. Only classification + attribution metadata.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

import anthropic

from .bandit.selection import build_selection_payload, select_strategy_from_rows
from .llm import classify_and_detect, generate_response
from .llm.synthesizer import generate_response_stream
from .signals import canonicalize_topic
from .store import (
    MongoStore,
    REWARD_STATUS_APPLIED,
    REWARD_STATUS_PENDING,
    make_attribution_pk,
    new_message_id,
    new_response_id,
    new_session_id,
    utcnow_iso,
)
from .strategies import INTENT_STRATEGIES, compute_format_compliance


# ----------------------------------------------------------------------------
# ApeOrchestrator
# ----------------------------------------------------------------------------

class ApeOrchestrator:
    """Stateless orchestrator over (Anthropic client, MongoStore)."""

    def __init__(
        self,
        client: anthropic.Anthropic,
        model: str,
        store: MongoStore,
        domain: str = "finance",
    ) -> None:
        self.client = client
        self.model = model
        self.store = store
        self.domain = domain

    # ==================================================================
    # PATH A — Strategy selection for the current response
    # ==================================================================

    def handle_turn(
        self,
        user_id: str,
        query: str,
        session_id: Optional[str] = None,
        generate: bool = True,
        history_limit: int = 30,
    ) -> Dict[str, Any]:
        """Path A — process one user message end-to-end.

        Conversation history is read from MongoDB (ape_messages collection)
        keyed by session_id — the client no longer sends a history array.
        After the response is generated, both the user query and the assistant
        answer are persisted as messages for future turns + UI history loads.

        Latency is broken down per step into `timings_ms` on the response so
        admins can see exactly where time is spent (almost always: LLM calls).
        """
        import time as _time
        timings: Dict[str, float] = {}
        t0 = _time.monotonic()

        def _tick(label: str, t_start: float) -> float:
            """Record elapsed ms since t_start under `label`; return current time."""
            now = _time.monotonic()
            timings[label] = round((now - t_start) * 1000.0, 1)
            return now

        ts = utcnow_iso()
        user_id_hash = hash_user_id(user_id)
        if not session_id:
            session_id = new_session_id(user_id_hash)

        # Read history from MongoDB (server is authoritative now)
        history = self.store.history_for_llm(session_id, limit=history_limit)
        t = _tick("load_history", t0)

        # Append the new user message FIRST so it lands in the audit log even
        # if generation later fails. We don't include it in `history` because
        # the classifier prompt distinguishes "current message" from prior turns.
        self.store.append_message(
            message_id=new_message_id(),
            user_id_hash=user_id_hash,
            session_id=session_id,
            role="user",
            content=query,
            ts=ts,
        )
        t = _tick("append_user_msg", t)

        # A2-equivalent: classifier extracts intent + topic + signal
        cls = classify_and_detect(self.client, self.model, query, history, prev_format=None)
        intent = cls["intent"]
        topic  = canonicalize_topic(cls.get("topic"))
        t = _tick("classifier_llm", t)

        # A1: validate intent (intent must exist as an active config entity)
        intent_cfg = self.store.get_active_config("intent", intent)
        if intent_cfg is None:
            intent = "unmapped"
        t = _tick("intent_validate", t)

        # A2: resolve candidate strategies for this cell
        candidate_strategies = self._resolve_candidate_strategies(intent, topic)
        t = _tick("policy_lookup", t)

        # A3: load active instruction for each candidate (just the version
        #     and uri — the actual instruction text is read at synth time)
        instruction_versions = self._load_active_instructions(candidate_strategies)
        t = _tick("load_instructions", t)

        # A4: read the user's bandit state for this cell (lazy-create rows)
        bandit_rows = self.store.get_or_create_bandit_cell(
            user_id_hash=user_id_hash,
            domain=self.domain,
            intent=intent,
            topic=topic,
            strategies=candidate_strategies,
        )
        t = _tick("load_bandit_cell", t)

        # A5: pick highest cached_ucb
        selected_row = select_strategy_from_rows(bandit_rows)
        if selected_row is None:
            # Should never happen unless strategies list is empty
            raise RuntimeError(f"No bandit rows for cell intent={intent} topic={topic}")
        selection = build_selection_payload(
            rows=bandit_rows,
            selected_row=selected_row,
            candidate_strategies=candidate_strategies,
            policy_version=selected_row.get("policy_version", "v1"),
        )
        t = _tick("ucb_select", t)

        # ------------------------------------------------------------------
        # Everything above is the SELECTION PATH. The sum of its timings is
        # how long it took APE to pick the strategy + hand it to the synth.
        # ------------------------------------------------------------------
        timings["select_and_handoff_total"] = round(
            sum(v for k, v in timings.items() if k != "classifier_llm")
            + timings.get("classifier_llm", 0.0),
            1,
        )
        timings["select_and_handoff_excluding_classifier"] = round(
            timings["select_and_handoff_total"] - timings.get("classifier_llm", 0.0),
            1,
        )

        # A6: synthesizer LLM call
        answer = ""
        rendered_format = "paragraph"
        if generate:
            rendered_format, answer = generate_response(
                self.client, self.model, query,
                selection["selected_strategy"], history,
            )
        t = _tick("synthesizer_llm", t)

        # Compute format_compliance (suggested vs rendered)
        suggested = selection["selected_strategy"]
        compliance = compute_format_compliance(suggested, rendered_format)
        instr_version = instruction_versions.get(suggested, "v1")

        # A7: write the response record as PENDING with full attribution
        response_id = new_response_id()
        attribution_pk = make_attribution_pk(user_id_hash, self.domain, intent, topic)

        self.store.write_pending_response({
            "response_id":             response_id,
            "user_id_hash":            user_id_hash,
            "session_id_optional":     session_id,
            "ts":                      ts,
            "domain":                  self.domain,
            "intent":                  intent,
            "intent_confidence":       float(cls.get("intent_confidence", 0.0)),
            "topic":                   topic,
            "selected_strategy":       suggested,
            "selection_method":        "ucb",
            "suggested_format":        suggested,
            "rendered_format":         rendered_format,
            "format_compliance":       int(bool(compliance)),
            "ucb_at_selection":        selection["ucb_at_selection"],
            "policy_version":          selection["policy_version"],
            "instruction_version":     instr_version,
            "attribution_bandit_pk":   attribution_pk,
            "attribution_bandit_sk":   suggested,
        })

        # Persist the assistant message to conversation history
        assistant_msg_id = new_message_id()
        self.store.append_message(
            message_id=assistant_msg_id,
            user_id_hash=user_id_hash,
            session_id=session_id,
            role="assistant",
            content=answer,
            ts=utcnow_iso(),
            response_id=response_id,
            rendered_format=rendered_format,
            meta={
                "intent":            intent,
                "topic":             topic,
                "selected_strategy": suggested,
                "ucb_at_selection":  selection["ucb_at_selection"],
            },
        )

        _tick("post_writes", t)
        timings["total"] = round((_time.monotonic() - t0) * 1000.0, 1)

        return {
            "response_id":         response_id,
            "session_id":          session_id,
            "assistant_message_id": assistant_msg_id,
            "classification":      cls,
            "selection":           selection,
            "answer":              answer,
            "rendered_format":     rendered_format,
            "timings_ms":          timings,
        }

    # ==================================================================
    # PATH A (streaming) — same as handle_turn but yields SSE-shaped events
    # ==================================================================

    def handle_turn_streaming(
        self,
        user_id: str,
        query: str,
        session_id: Optional[str] = None,
        history_limit: int = 30,
    ):
        """Generator version of handle_turn.

        Yields a sequence of event dicts (the API layer converts these to SSE):

          {"event":"metadata", ...}   — once, after selection completes
          {"event":"delta", "text":"..."}   — many, while synthesizer streams
          {"event":"done",   ...}     — once, after writes complete (includes
                                        response_id, rendered_format, full
                                        answer, timings_ms)

        The selection-side work (history load, classifier, policy lookup,
        bandit cell load, UCB) runs synchronously BEFORE the first event so
        the metadata event arrives with the picked strategy already known.
        Then the synthesizer streams; once it finishes we do the writes and
        emit `done`.
        """
        import time as _time
        timings: Dict[str, float] = {}
        t0 = _time.monotonic()

        def _tick(label: str, t_start: float) -> float:
            now = _time.monotonic()
            timings[label] = round((now - t_start) * 1000.0, 1)
            return now

        ts = utcnow_iso()
        user_id_hash = hash_user_id(user_id)
        if not session_id:
            session_id = new_session_id(user_id_hash)

        history = self.store.history_for_llm(session_id, limit=history_limit)
        t = _tick("load_history", t0)

        self.store.append_message(
            message_id=new_message_id(),
            user_id_hash=user_id_hash,
            session_id=session_id,
            role="user",
            content=query,
            ts=ts,
        )
        t = _tick("append_user_msg", t)

        cls = classify_and_detect(self.client, self.model, query, history, prev_format=None)
        intent = cls["intent"]
        topic  = canonicalize_topic(cls.get("topic"))
        t = _tick("classifier_llm", t)

        intent_cfg = self.store.get_active_config("intent", intent)
        if intent_cfg is None:
            intent = "unmapped"
        t = _tick("intent_validate", t)

        candidate_strategies = self._resolve_candidate_strategies(intent, topic)
        t = _tick("policy_lookup", t)

        instruction_versions = self._load_active_instructions(candidate_strategies)
        t = _tick("load_instructions", t)

        bandit_rows = self.store.get_or_create_bandit_cell(
            user_id_hash=user_id_hash,
            domain=self.domain,
            intent=intent,
            topic=topic,
            strategies=candidate_strategies,
        )
        t = _tick("load_bandit_cell", t)

        selected_row = select_strategy_from_rows(bandit_rows)
        if selected_row is None:
            raise RuntimeError(f"No bandit rows for cell intent={intent} topic={topic}")
        selection = build_selection_payload(
            rows=bandit_rows,
            selected_row=selected_row,
            candidate_strategies=candidate_strategies,
            policy_version=selected_row.get("policy_version", "v1"),
        )
        t = _tick("ucb_select", t)
        suggested = selection["selected_strategy"]

        # --- Pre-allocate the response_id so the client can store it for /feedback
        #     immediately, before any token streams ---
        response_id = new_response_id()

        # ---- EVENT 1: metadata (admin can show "Selected: decision_card" ASAP)
        yield {
            "event":            "metadata",
            "response_id":      response_id,
            "session_id":       session_id,
            "intent":           intent,
            "topic":            topic,
            "selected_strategy": suggested,
            "candidate_strategies": candidate_strategies,
            "select_timings_ms": dict(timings),
        }

        # ---- Synthesizer streaming ----
        synth_t0 = _time.monotonic()
        answer_text = ""
        rendered_format = "paragraph"
        try:
            for evt in generate_response_stream(
                self.client, self.model, query, suggested, history,
            ):
                if evt["type"] == "delta":
                    # Note: this is the RAW LLM text including the JSON wrapper.
                    # The frontend strips the wrapper for display; we still
                    # forward each chunk so admins can see progress.
                    yield {"event": "delta", "text": evt["text"]}
                elif evt["type"] == "done":
                    answer_text = evt["response"]
                    rendered_format = evt["rendered_format"]
        except Exception as exc:
            yield {"event": "error", "message": str(exc)}
            return
        timings["synthesizer_llm"] = round((_time.monotonic() - synth_t0) * 1000.0, 1)
        t = _time.monotonic()

        # ---- Compliance + writes ----
        compliance = compute_format_compliance(suggested, rendered_format)
        instr_version = instruction_versions.get(suggested, "v1")
        attribution_pk = make_attribution_pk(user_id_hash, self.domain, intent, topic)

        self.store.write_pending_response({
            "response_id":             response_id,
            "user_id_hash":            user_id_hash,
            "session_id_optional":     session_id,
            "ts":                      ts,
            "domain":                  self.domain,
            "intent":                  intent,
            "intent_confidence":       float(cls.get("intent_confidence", 0.0)),
            "topic":                   topic,
            "selected_strategy":       suggested,
            "selection_method":        "ucb",
            "suggested_format":        suggested,
            "rendered_format":         rendered_format,
            "format_compliance":       int(bool(compliance)),
            "ucb_at_selection":        selection["ucb_at_selection"],
            "policy_version":          selection["policy_version"],
            "instruction_version":     instr_version,
            "attribution_bandit_pk":   attribution_pk,
            "attribution_bandit_sk":   suggested,
        })

        assistant_msg_id = new_message_id()
        self.store.append_message(
            message_id=assistant_msg_id,
            user_id_hash=user_id_hash,
            session_id=session_id,
            role="assistant",
            content=answer_text,
            ts=utcnow_iso(),
            response_id=response_id,
            rendered_format=rendered_format,
            meta={
                "intent":            intent,
                "topic":             topic,
                "selected_strategy": suggested,
                "ucb_at_selection":  selection["ucb_at_selection"],
            },
        )
        _tick("post_writes", t)
        timings["total"] = round((_time.monotonic() - t0) * 1000.0, 1)

        # ---- EVENT FINAL: done ----
        yield {
            "event":                "done",
            "response_id":          response_id,
            "session_id":           session_id,
            "assistant_message_id": assistant_msg_id,
            "answer":               answer_text,
            "rendered_format":      rendered_format,
            "format_compliance":    int(bool(compliance)),
            "selection":            selection,
            "classification":      cls,
            "timings_ms":           timings,
        }

    # ==================================================================
    # PATH B — Reward update for an EXACT response_id
    # ==================================================================

    def apply_feedback(
        self,
        user_id: str,
        response_id: str,
        signal_name: str,
    ) -> Dict[str, Any]:
        """Apply a UI-supplied signal to the exact response_id.

        Returns a result dict explaining what happened (applied/skipped/rejected).
        """
        user_id_hash = hash_user_id(user_id)

        # B1: read the response record (exact lookup by response_id)
        resp = self.store.get_response(response_id)
        if resp is None:
            return {"status": "rejected", "reason": "response_not_found", "response_id": response_id}

        # B2: validate user_id matches and reward is still pending
        if resp.get("user_id_hash") != user_id_hash:
            return {"status": "rejected", "reason": "user_mismatch", "response_id": response_id}
        if resp.get("reward_status") != REWARD_STATUS_PENDING:
            return {"status": "rejected", "reason": "already_finalized",
                    "current_status": resp.get("reward_status"), "response_id": response_id}

        # B3: read the signal routing rule
        routing = self.store.get_signal_routing(signal_name)
        if routing is None:
            self.store.mark_response_skipped(response_id, user_id_hash, "unknown_signal")
            return {"status": "skipped", "reason": "unknown_signal", "signal": signal_name}

        format_relevant  = bool(routing.get("format_relevant", False))
        format_category  = routing.get("format_category")

        # B4: read the reward scale for the format axis
        normalized_reward: Optional[float] = None
        if format_relevant and format_category:
            scale = self.store.get_reward_scale(format_category)
            if scale is None:
                self.store.mark_response_skipped(response_id, user_id_hash, "unknown_reward_category")
                return {"status": "skipped", "reason": "unknown_reward_category", "category": format_category}
            normalized_reward = float(scale["normalized_reward"])

        # B5: atomically mark the response APPLIED with signal + reward
        rewarded = self.store.mark_response_rewarded(
            response_id=response_id,
            user_id_hash=user_id_hash,
            signal=signal_name,
            reward_category=format_category if format_relevant else None,
            normalized_reward=normalized_reward,
        )
        if rewarded is None:
            # Conditional update lost the race (already APPLIED by another request)
            return {"status": "rejected", "reason": "race_already_applied", "response_id": response_id}

        # B6: apply the reward to the bandit row pointed to by attribution
        if format_relevant and normalized_reward is not None:
            updated_row = self.store.update_strategy_reward(
                attribution_pk=resp["attribution_bandit_pk"],
                attribution_sk=resp["attribution_bandit_sk"],
                normalized_reward=normalized_reward,
            )
            # B7: refresh cached_ucb for ALL strategies in this cell
            self.store.refresh_cell_ucb_cache(resp["attribution_bandit_pk"])
        else:
            updated_row = None

        return {
            "status":            "applied" if format_relevant else "applied_no_format_update",
            "response_id":       response_id,
            "signal":            signal_name,
            "reward_category":   format_category if format_relevant else None,
            "normalized_reward": normalized_reward,
            "strategy_row_after": _clean(updated_row),
        }

    # ==================================================================
    # Internal helpers
    # ==================================================================

    def _resolve_candidate_strategies(self, intent: str, topic: str) -> List[str]:
        """Look up the allowed strategies for (intent, topic) from policies.

        Falls back to the hardcoded INTENT_STRATEGIES catalog if no policy
        rows exist (e.g. fresh DB or new intent the admin hasn't configured).
        """
        # Try topic-specific policy first
        rows = self.store.get_policy_strategies(self.domain, intent, topic)
        if not rows:
            # Fall back to _default topic
            rows = self.store.get_policy_strategies(self.domain, intent, "_default")
        if rows:
            return sorted({r["strategy_id"] for r in rows})
        # Last resort — hardcoded catalog
        return INTENT_STRATEGIES.get(intent, INTENT_STRATEGIES["unmapped"])

    def _load_active_instructions(self, strategies: List[str]) -> Dict[str, str]:
        """Return {strategy_id: active_version} for each strategy."""
        out: Dict[str, str] = {}
        for s in strategies:
            doc = self.store.config.find_one({
                "entity_type": "instruction",
                "entity_id":   s,
                "status":      "ACTIVE",
            })
            out[s] = (doc or {}).get("version", "v1")
        return out


# ----------------------------------------------------------------------------
# Identity helpers
# ----------------------------------------------------------------------------

def hash_user_id(user_id: str) -> str:
    """Stable, privacy-friendly hash of the raw user_id.

    The design specifies user_id_hash to avoid storing raw user identifiers
    in the bandit key. SHA-256, truncated to 16 hex chars (64 bits) — plenty
    of entropy for a personal-data partition key.
    """
    return "u_" + hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]


def _clean(doc):
    if doc is None:
        return None
    out = dict(doc)
    out.pop("_id", None)
    return out
