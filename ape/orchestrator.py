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
from .signals import canonicalize_topic, resolve_signal
from .signals.composites import detect_composite
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


# ── Signals that are decisive enough to finalize eagerly (no need to wait
# for more signals to accumulate). Includes explicit format complaints,
# explicit format praise, and strong UI negatives.
_EXPLICIT_OR_STRONG_SIGNALS = {
    "format_change_request",
    "format_keep_request",
    "content_correction",
    "regenerate_click",
    "thumbs_down",
}


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

        # ── Buffered-resolver flush of the PREVIOUS PENDING response ──────
        # The classifier just produced a signal that's a reaction to the
        # previous response — feed it into that response's pending_signals
        # before finalizing. Also fire session_continue (the user clearly
        # didn't abandon — they sent another message).
        prev_pending = self.store.find_previous_pending_response(
            user_id_hash=user_id_hash,
            session_id=session_id,
            max_age_sec=600,
        )
        if prev_pending is not None:
            prev_id = prev_pending["response_id"]
            llm_sig = cls.get("signal")
            if llm_sig and llm_sig != "no_signal":
                self.store.append_pending_signal(prev_id, {
                    "signal": llm_sig,
                    "source": "llm",
                    "ts":     utcnow_iso(),
                })
            # Session continuity — user sent another message → implicit positive
            prev_age = self.store.get_response_age_seconds(prev_id) or 0.0
            if prev_age < 300:  # 5-min cutoff for "continued" vs "returned later"
                self.store.append_pending_signal(prev_id, {
                    "signal": "session_continue",
                    "source": "derived",
                    "ts":     utcnow_iso(),
                })
            # Now finalize the previous response: composite + resolver + reward
            try:
                self._finalize_response(prev_id, user_id_hash)
            except Exception as e:
                # Don't let a finalize error block the current turn
                print(f"[orchestrator] finalize_response failed for {prev_id}: {e}", flush=True)
        t = _tick("finalize_prev_response", t)

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

        # Pre-seed pending_signals with the objective format_compliance result.
        # This is the bias-free "did the synthesizer obey the strategy" signal —
        # it fires every turn automatically, gives the bandit a steady heartbeat
        # of format evidence independent of user mood, and routes per the
        # signal catalog (compliance_pass → +0.5, compliance_fail → -0.5).
        compliance_signal = (
            "format_compliance_pass" if compliance else "format_compliance_fail"
        )
        initial_pending_signals = [{
            "signal": compliance_signal,
            "source": "derived",
            "ts":     ts,
        }]

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
            "pending_signals":         initial_pending_signals,
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
        """Path B — buffer a UI signal, then finalize the response.

        Buffered-resolver behavior:
          1. Append the signal to pending_signals[] on the response row.
          2. Decide whether to finalize now (eager) or wait (deferred):
             - Eager if response age >= 5s (no more clicks expected)
             - Eager if 3+ signals already buffered (probably done)
             - Eager if the signal is a "strong/explicit" signal
             - Else: return {status: queued} and wait for next signal OR /turn flush
          3. If finalize: composite detector → resolver → apply one reward atomically.

        Returns a result dict describing what happened.
        """
        user_id_hash = hash_user_id(user_id)

        # Read the response record
        resp = self.store.get_response(response_id)
        if resp is None:
            return {"status": "rejected", "reason": "response_not_found", "response_id": response_id}
        if resp.get("user_id_hash") != user_id_hash:
            return {"status": "rejected", "reason": "user_mismatch", "response_id": response_id}
        if resp.get("reward_status") != REWARD_STATUS_PENDING:
            return {"status": "rejected", "reason": "already_finalized",
                    "current_status": resp.get("reward_status"), "response_id": response_id}

        # Reject unknown signals early so we don't pollute pending_signals with garbage
        routing = self.store.get_signal_routing(signal_name)
        if routing is None:
            return {"status": "skipped", "reason": "unknown_signal", "signal": signal_name}

        # Buffer the signal (source=ui since /feedback comes from UI clicks)
        appended = self.store.append_pending_signal(response_id, {
            "signal": signal_name,
            "source": "ui",
            "ts":     utcnow_iso(),
        })
        if not appended:
            return {"status": "rejected", "reason": "append_failed", "response_id": response_id}

        # Decide whether to finalize now
        age_sec = self.store.get_response_age_seconds(response_id) or 0.0
        pending_count = len(resp.get("pending_signals", [])) + 1   # +1 for the one we just added
        is_strong = signal_name in _EXPLICIT_OR_STRONG_SIGNALS
        should_finalize = (
            age_sec >= 5.0
            or pending_count >= 3
            or is_strong
        )
        if should_finalize:
            return self._finalize_response(response_id, user_id_hash)

        return {
            "status":         "queued",
            "response_id":    response_id,
            "signal_buffered": signal_name,
            "pending_count":  pending_count,
            "age_sec":        round(age_sec, 1),
        }

    def _finalize_response(
        self,
        response_id: str,
        user_id_hash: str,
    ) -> Dict[str, Any]:
        """Compute the winning signal from pending_signals[] and apply ONE reward.

        Order of resolution:
          1. Composite detection — if a multi-signal pattern matches, it wins.
          2. Atomic resolver — UI > LLM, priority ladder within UI.

        The winner's routing decides the reward category + magnitude. Bandit
        update is gated on `format_relevant` because the bandit is single-axis
        (format) today; content_relevant routing is logged but not consumed.
        """
        resp = self.store.get_response(response_id)
        if resp is None:
            return {"status": "rejected", "reason": "response_not_found", "response_id": response_id}
        if resp.get("reward_status") != REWARD_STATUS_PENDING:
            return {"status": "rejected", "reason": "already_finalized", "response_id": response_id}

        pending: List[Dict[str, Any]] = resp.get("pending_signals", []) or []
        age_sec = self.store.get_response_age_seconds(response_id) or 0.0

        # Decorate each entry with age_sec for composite trigger functions
        for p in pending:
            try:
                ts = p.get("ts", "")
                if ts.endswith("Z"):
                    ts = ts[:-1] + "+00:00"
                from datetime import datetime as _dt
                p_dt = _dt.fromisoformat(ts).replace(tzinfo=None)
                resp_ts = resp.get("ts", "")
                if resp_ts.endswith("Z"):
                    resp_ts = resp_ts[:-1] + "+00:00"
                r_dt = _dt.fromisoformat(resp_ts).replace(tzinfo=None)
                p["age_sec"] = max(0.0, (p_dt - r_dt).total_seconds())
            except Exception:
                p["age_sec"] = 0.0

        # 1) Try composite detection
        winner = detect_composite(pending, age_sec)
        winner_source = "composite" if winner else None

        # 2) Fall back to atomic resolver
        if not winner:
            ui_signals = {s["signal"]: 1 for s in pending if s.get("source") == "ui"}
            llm_signal = None
            for s in pending:
                if s.get("source") == "llm":
                    llm_signal = s["signal"]
                    break
            # Also consider derived signals (compliance, session) — they should
            # win over UI when no UI fired but a derived signal did, since
            # the user provided no explicit reaction but the system has evidence.
            if not ui_signals and not llm_signal:
                derived = [s["signal"] for s in pending if s.get("source") == "derived"]
                if derived:
                    winner = derived[0]
                    winner_source = "derived"
            if not winner:
                winner = resolve_signal(ui_signals, llm_signal)
                winner_source = "resolver"

        # Look up routing for the winner
        routing = self.store.get_signal_routing(winner)
        if routing is None:
            # Unknown winner — mark APPLIED with no reward so the row doesn't stay PENDING
            self.store.mark_response_rewarded(
                response_id=response_id,
                user_id_hash=user_id_hash,
                signal=winner,
                reward_category=None,
                normalized_reward=None,
            )
            return {"status": "applied_unknown_signal", "winner": winner, "response_id": response_id}

        format_relevant  = bool(routing.get("format_relevant", False))
        format_category  = routing.get("format_category")

        # Read the reward scale for the format axis (bandit is single-axis today)
        normalized_reward: Optional[float] = None
        if format_relevant and format_category:
            scale = self.store.get_reward_scale(format_category)
            if scale is None:
                # Reward category misconfigured — mark APPLIED with no reward
                self.store.mark_response_rewarded(
                    response_id=response_id,
                    user_id_hash=user_id_hash,
                    signal=winner,
                    reward_category=None,
                    normalized_reward=None,
                )
                return {"status": "applied_no_reward_scale", "winner": winner,
                        "missing_category": format_category}
            normalized_reward = float(scale["normalized_reward"])

        # Atomic CAS: PENDING → APPLIED with the winning signal + reward
        rewarded = self.store.mark_response_rewarded(
            response_id=response_id,
            user_id_hash=user_id_hash,
            signal=winner,
            reward_category=format_category if format_relevant else None,
            normalized_reward=normalized_reward,
        )
        if rewarded is None:
            return {"status": "rejected", "reason": "race_already_applied", "response_id": response_id}

        # Apply reward to the bandit cell (format axis only)
        updated_row = None
        if format_relevant and normalized_reward is not None:
            updated_row = self.store.update_strategy_reward(
                attribution_pk=resp["attribution_bandit_pk"],
                attribution_sk=resp["attribution_bandit_sk"],
                normalized_reward=normalized_reward,
            )
            self.store.refresh_cell_ucb_cache(resp["attribution_bandit_pk"])

        return {
            "status":             "applied" if format_relevant else "applied_no_format_update",
            "response_id":        response_id,
            "winner":             winner,
            "winner_source":      winner_source,
            "n_signals_pooled":   len(pending),
            "reward_category":    format_category if format_relevant else None,
            "normalized_reward":  normalized_reward,
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
