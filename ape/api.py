"""
FastAPI HTTP wrapper around the orchestrator (production design).

API endpoints:
  GET    /health                          — liveness probe
  POST   /turn                            — Path A: select strategy, write PENDING response
  POST   /feedback                        — Path B: apply reward to exact response_id

  GET    /sessions/{session_id}/turns     — load a session's response history
  GET    /users/{user_id}/responses       — load a user's recent responses

  Config (admin):
  GET    /config/intents                  — list active intents
  GET    /config/strategies               — list active strategies
  GET    /config/policies                 — list active policies
  GET    /config/signal-rules             — list active signal rules
  GET    /config/reward-scale             — list active reward values
  POST   /config/signal-rules             — upsert signal rule
  POST   /config/reward-scale             — upsert reward value
  POST   /config/policies                 — upsert policy
  POST   /config/instructions             — publish instruction version
  POST   /config/instructions/activate    — activate an instruction version

  Ops:
  DELETE /admin/clear-user/{user_id}      — delete a user's runtime data
  DELETE /admin/clear-all                 — clear runtime (preserves config + audit)
  POST   /admin/seed                      — seed default config into MongoDB
  GET    /admin/db-snapshot               — sidebar aggregated stats
  GET    /admin/audit                     — list admin audit entries

Frontend serving:
  /assets/...                             — Vite hashed asset bundles
  /                                       — SPA shell (index.html)
  /<any-path>                             — SPA shell (React Router)
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .analytics import (
    active_users_in_window,
    compute_cognitive_facets,
    compute_customer_health,
    compute_instruction_quality,
    compute_platform_overview,
    compute_rag_quality,
    compute_strategy_performance,
    compute_topic_trends,
    compute_unmapped_intents,
    compute_user_cognitive_profile,
    compute_user_topic_interest,
    eligible_offers_for_user,
    recompute_all,
)
from .config import ConfigManager, cleanup_non_canonical_intents, cleanup_strategy_format_metadata, seed_all
from .models import (
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    InstructionPublish,
    IntentUpsert,
    PolicyUpsert,
    RewardScaleUpdate,
    SignalRuleUpdate,
    StrategyUpsert,
    TurnRequest,
    TurnResponse,
    UcbConfigUpdate,
)
from .bandit.selection import set_ucb_params, get_ucb_params
from .orchestrator import ApeOrchestrator, NoActiveStrategiesError, UnknownIntentError, hash_user_id
from .rag import RAG_DOMAINS, RagStore
from .store import MongoStore
from .store.mongo_schema import (
    ENTITY_INSTRUCTION,
    ENTITY_INTENT,
    ENTITY_OFFER_POLICY,
    ENTITY_POLICY,
    ENTITY_REWARD_RULE,
    ENTITY_SIGNAL_RULE,
    ENTITY_STRATEGY,
    STATUS_ACTIVE,
)


app = FastAPI(title="APE Modular — Production (MongoDB)", version="2.0.0")

ORCHESTRATOR: Optional[ApeOrchestrator] = None
STORE: Optional[MongoStore] = None
CONFIG_MGR: Optional[ConfigManager] = None
RAG: Optional[RagStore] = None


# Admin-token gating was removed — admin/config/analytics surfaces are open
# again (no X-APE-Admin-Token required) per product decision. The chat UI
# and these operational surfaces all share the same origin with no auth wall.


# ============================================================================
# App bootstrap
# ============================================================================

def _build() -> ApeOrchestrator:
    load_dotenv(override=True)
    # LLM backend: Anthropic Claude (Haiku).
    model   = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required")

    domain = os.getenv("APE_DOMAIN", "finance")

    client = anthropic.Anthropic(api_key=api_key)
    store = MongoStore()

    # Seed default config if collections are empty
    if store.config.estimated_document_count() == 0:
        seed_all(store, domain=domain)
    else:
        cleanup_strategy_format_metadata(store)
        cleanup_non_canonical_intents(store)

    global STORE, CONFIG_MGR, RAG
    STORE = store
    CONFIG_MGR = ConfigManager(store)

    # Load the admin-tunable UCB params (bandit_config/ucb) into the live
    # selection module. Seed defaults if the doc doesn't exist yet.
    ucb_doc = store.get_active_config("bandit_config", "ucb")
    if not ucb_doc:
        defaults = get_ucb_params()
        store.upsert_config("bandit_config", "ucb", {
            "exploration_c":      defaults["c"],
            "reward_range_width": defaults["width"],
        })
        ucb_doc = store.get_active_config("bandit_config", "ucb")
    set_ucb_params(c=ucb_doc.get("exploration_c"), width=ucb_doc.get("reward_range_width"))
    print(f"[startup] UCB params: c={ucb_doc.get('exploration_c')} "
          f"width={ucb_doc.get('reward_range_width')}", flush=True)

    # RAG disabled — initialization commented out. RAG stays None, the
    # orchestrator skips retrieval, and /rag/* endpoints return
    # "RAG not initialized". Uncomment the block below to re-enable.
    # Multi-domain RAG knowledge base (Chroma). Idempotent ingest of the seed
    # corpora on boot so retrieval works immediately.
    # RAG = RagStore()
    # try:
    #     counts = RAG.ingest()
    #     print(f"[startup] RAG ingest counts: {counts}", flush=True)
    # except Exception as e:
    #     print(f"[startup] RAG ingest failed (continuing without RAG): {e}", flush=True)
    print("[startup] RAG disabled (initialization commented out)", flush=True)

    return ApeOrchestrator(client=client, model=model, store=store, domain=domain, rag=RAG)


@app.on_event("startup")
def startup() -> None:
    global ORCHESTRATOR
    ORCHESTRATOR = _build()


def _resolve_user_hash(user_id: str) -> str:
    """Accept either a raw user_id or an already-hashed `u_<16hex>` identifier.

    The analytics "active customers" list returns user_id_hash values (we
    intentionally don't store raw user_ids in the analytics layer). The admin
    can paste / click those hashes into any /analytics endpoint and they'll
    pass through unchanged instead of being double-hashed.

    Format check: hashes start with `u_` and the remainder is hex of length
    16 (or more, future-proof). Anything else gets the SHA-256 treatment.
    """
    if (
        isinstance(user_id, str)
        and user_id.startswith("u_")
        and len(user_id) >= 12
        and all(c in "0123456789abcdef" for c in user_id[2:].lower())
    ):
        return user_id
    return hash_user_id(user_id)


# ============================================================================
# Public endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


# ── RAG knowledge base — inspect + (re)load ──────────────────────────────────
@app.get("/rag/search")
def rag_search(q: str, domain: str, k: int = 4):
    """Inspect retrieval live: top-k passages for a query within a domain.

    Lets you verify domain isolation (e.g. q='who directed inception',
    domain='cricket' returns far/irrelevant hits).
    """
    if RAG is None:
        raise HTTPException(500, "RAG not initialized")
    if domain not in RAG_DOMAINS:
        raise HTTPException(400, f"Unknown domain '{domain}'. Valid: {RAG_DOMAINS}")
    hits = RAG.retrieve(q, domain, k=k)
    return {"query": q, "domain": domain, "k": k, "hits": hits}


@app.get("/rag/status")
def rag_status():
    """Per-domain document counts in the knowledge base."""
    if RAG is None:
        raise HTTPException(500, "RAG not initialized")
    return {"domains": RAG_DOMAINS, "counts": RAG._domain_counts()}


@app.post("/admin/rag-ingest")
def rag_ingest(force: bool = False):
    """(Re)load the seed corpora. force=true wipes and reloads the collection."""
    if RAG is None:
        raise HTTPException(500, "RAG not initialized")
    counts = RAG.ingest(force=force)
    return {"status": "ok", "force": force, "counts": counts}


@app.post("/turn", response_model=TurnResponse)
async def post_turn(req: TurnRequest) -> TurnResponse:
    """PATH A — process a user message, write a PENDING response record.

    Conversation history is read from MongoDB by session_id — the client no
    longer needs to send it.
    """
    if ORCHESTRATOR is None:
        raise HTTPException(500, "Orchestrator not initialized")

    try:
        result = await asyncio.to_thread(
            ORCHESTRATOR.handle_turn,
            user_id=req.user_id,
            query=req.query,
            session_id=req.session_id,
            generate=req.generate_response,
        )
    except (UnknownIntentError, NoActiveStrategiesError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return TurnResponse(**result)


@app.post("/turn/stream")
async def post_turn_stream(req: TurnRequest):
    """PATH A (streaming) — same as /turn but streams synthesizer tokens via SSE.

    Event sequence:
      metadata  — once, with the picked strategy + response_id (after selection)
      snapshot  — many; CUMULATIVE — each carries the full text so far, so the
                  client REPLACES its buffer instead of appending
      done      — once, with final answer + rendered_format + timings
      error     — if anything blew up mid-stream

    The frontend should:
      1. Parse the metadata event → store response_id + selected_strategy
      2. On each snapshot, replace the live bubble's text with snapshot.text
      3. On done, replace the bubble with the authoritative `answer`.
    """
    if ORCHESTRATOR is None:
        raise HTTPException(500, "Orchestrator not initialized")

    try:
        gen = await asyncio.to_thread(
            ORCHESTRATOR.handle_turn_streaming,
            user_id=req.user_id,
            query=req.query,
            session_id=req.session_id,
        )
    except (UnknownIntentError, NoActiveStrategiesError) as exc:
        raise HTTPException(422, str(exc)) from exc

    def _sse_format(event: Dict[str, Any]) -> str:
        """Convert one event dict to the SSE wire format."""
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    # The orchestrator's streaming method is a blocking generator (Anthropic SDK
    # is sync). Wrap it so each `next()` runs in a thread and yields back to
    # the event loop — keeps FastAPI's async event loop free to handle other
    # requests while one is streaming.
    async def event_gen():
        # Yield SSE-formatted events one at a time
        sentinel = object()
        try:
            while True:
                evt = await asyncio.to_thread(next, gen, sentinel)
                if evt is sentinel:
                    break
                yield _sse_format(evt)
        finally:
            # On client disconnect Starlette closes this async generator.
            # Explicitly close the inner blocking generator so its
            # `with client.messages.stream(...)` context exits and the
            # Anthropic HTTP connection is released immediately, rather
            # than waiting for garbage collection.
            try:
                await asyncio.to_thread(gen.close)
            except Exception:
                pass

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            # Disable proxy buffering so chunks actually arrive in real time
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",     # for nginx if present
            "Connection":        "keep-alive",
        },
    )


@app.post("/feedback", response_model=FeedbackResponse)
async def post_feedback(req: FeedbackRequest) -> FeedbackResponse:
    """PATH B — apply an explicit UI signal to a specific response_id."""
    if ORCHESTRATOR is None:
        raise HTTPException(500, "Orchestrator not initialized")
    result = await asyncio.to_thread(
        ORCHESTRATOR.apply_feedback,
        user_id=req.user_id,
        response_id=req.response_id,
        signal_name=req.signal,
    )
    return FeedbackResponse(**result)


# ============================================================================
# Conversation history (Mongo-backed)
# ============================================================================

@app.get("/sessions/{session_id}/messages")
def list_session_messages(session_id: str, user_id: str, limit: int = 200):
    """Load the full conversation history for a session — used by the chat UI
    on session open or page refresh.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_id_hash = hash_user_id(user_id)
    rows = STORE.list_session_messages(session_id, limit=limit, user_id_hash=user_id_hash)

    # Join each assistant message's applied reward from ape_turn_record so
    # the UI can show what every previous answer earned (signal + value), plus
    # the LIVE selection score of the strategy that was chosen for that answer.
    resp_ids = [r.get("response_id") for r in rows if r.get("response_id")]
    if resp_ids:
        from .bandit.selection import display_selection_score
        tr = {
            t["response_id"]: t
            for t in STORE.turn_record.find(
                {"response_id": {"$in": resp_ids}},
                {"response_id": 1, "reward_status": 1, "signal": 1,
                 "reward_category": 1, "normalized_reward": 1,
                 "content_category": 1, "content_reward": 1,
                 "attribution_bandit_pk": 1, "attribution_bandit_sk": 1,
                 "selection_method": 1},
            )
        }

        # Compute the selected strategy's selection score LIVE (no snapshot):
        # batch-load the current bandit-cell state for every referenced cell,
        # then score each cell's arms with the current c/width params.
        cells: Dict[tuple, Dict[str, Any]] = {}
        for t in tr.values():
            pk = t.get("attribution_bandit_pk")
            if pk:
                key = (pk.get("user_id_hash"), pk.get("domain"),
                       pk.get("intent"), pk.get("topic"))
                cells.setdefault(key, pk)
        live_scores: Dict[tuple, float] = {}   # (cell_key, strategy) -> score
        for key, pk in cells.items():
            cell_rows = list(STORE.bandit_state.find(
                pk, {"strategy": 1, "count": 1, "total_reward": 1}))
            n = sum(int(x.get("count", 0)) for x in cell_rows)
            for x in cell_rows:
                live_scores[(key, x["strategy"])] = display_selection_score(
                    x.get("count", 0), x.get("total_reward", 0.0), n)

        for r in rows:
            t = tr.get(r.get("response_id"))
            if t:
                r["reward_status"]     = t.get("reward_status")
                r["applied_signal"]    = t.get("signal")
                # FORMAT axis (bandit) + CONTENT axis (display)
                r["reward_category"]   = t.get("reward_category")
                r["normalized_reward"] = t.get("normalized_reward")
                r["content_category"]  = t.get("content_category")
                r["content_reward"]    = t.get("content_reward")
                # Historical fact: how the pick was made (round-robin vs ucb).
                r["selection_method"]  = t.get("selection_method")
                # Live score of the chosen strategy in its current cell state.
                pk = t.get("attribution_bandit_pk")
                sk = t.get("attribution_bandit_sk")
                if pk and sk:
                    key = (pk.get("user_id_hash"), pk.get("domain"),
                           pk.get("intent"), pk.get("topic"))
                    r["live_selection_score"] = live_scores.get((key, sk))

    return [_clean(r) for r in rows]


@app.get("/users/{user_id}/sessions")
def list_user_sessions(user_id: str, limit: int = 20):
    """List a user's recent sessions with a preview of the first user message.
    Used by the chat UI's session picker.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_id_hash = hash_user_id(user_id)
    return STORE.list_user_sessions(user_id_hash, limit=limit)


@app.get("/users/{user_id}/latest-session")
def get_latest_session(user_id: str):
    """Convenience endpoint for the UI to auto-resume the user's most recent
    conversation. Returns {session_id} or {session_id: null} if the user has
    no history yet.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_id_hash = hash_user_id(user_id)
    return {"session_id": STORE.latest_session_for_user(user_id_hash)}


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str, user_id: str):
    """Delete a single session's messages + response records. Bandit state is
    preserved (the user keeps their learned preferences across sessions).
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_id_hash = hash_user_id(user_id)
    return STORE.clear_user_session(user_id_hash, session_id)


# ----- Legacy turn-record view (kept for the analytics page) ----------------

@app.get("/sessions/{session_id}/turns")
def list_session_turns(session_id: str, user_id: str, limit: int = 100):
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_id_hash = hash_user_id(user_id)
    rows = STORE.list_session_responses(session_id, limit=limit, user_id_hash=user_id_hash)
    return [_clean(r) for r in rows]


@app.get("/users/{user_id}/responses")
def list_user_responses(user_id: str, limit: int = 50):
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_id_hash = hash_user_id(user_id)
    rows = STORE.list_user_responses(user_id_hash, limit=limit)
    return [_clean(r) for r in rows]


# ============================================================================
# Config endpoints
# ============================================================================

@app.get("/config/intents")
def list_intents():
    return _guard_cfg().list_intents()


@app.get("/config/strategies")
def list_strategies():
    return _guard_cfg().list_strategies()


@app.get("/config/policies")
def list_policies():
    return _guard_cfg().list_policies()


@app.get("/config/signal-rules")
def list_signal_rules():
    return _guard_cfg().list_signal_rules()


@app.get("/config/reward-scale")
def list_reward_scale():
    return _guard_cfg().list_reward_scale()


@app.post("/config/intents")
def upsert_intent(req: IntentUpsert):
    _guard_cfg().upsert_intent(
        intent_id=req.intent_id,
        description=req.description,
        changed_by=req.changed_by,
    )
    return {"status": "ok", "intent_id": req.intent_id}


@app.post("/config/strategies")
def upsert_strategy(req: StrategyUpsert):
    _guard_cfg().upsert_strategy(
        strategy_id=req.strategy_id,
        format_type=req.format_type,
        changed_by=req.changed_by,
    )
    return {"status": "ok", "strategy_id": req.strategy_id}


@app.post("/config/signal-rules")
def upsert_signal_rule(req: SignalRuleUpdate):
    _guard_cfg().update_signal_rule(
        signal_name=req.signal_name,
        format_relevant=req.format_relevant,
        content_relevant=req.content_relevant,
        format_category=req.format_category,
        content_category=req.content_category,
        source=req.source,
        feature_id=req.feature_id,
        expected_frequency=req.expected_frequency,
        evidence_quality=req.evidence_quality,
        consumers=req.consumers,
        trigger_pattern=req.trigger_pattern,
        time_window_sec=req.time_window_sec,
        changed_by=req.changed_by,
    )
    return {"status": "ok", "signal_name": req.signal_name}


@app.post("/config/reward-scale")
def upsert_reward_value(req: RewardScaleUpdate):
    _guard_cfg().update_reward_value(
        category=req.category,
        normalized_reward=req.normalized_reward,
        changed_by=req.changed_by,
    )
    return {"status": "ok", "category": req.category}


@app.get("/config/ucb")
def get_ucb_config():
    """Current global UCB params: exploration_c + reward_range_width."""
    return _guard_cfg().get_ucb_config()


@app.post("/config/ucb")
def update_ucb_config(req: UcbConfigUpdate):
    """Update the UCB formula knobs and apply them live (no redeploy)."""
    result = _guard_cfg().update_ucb_config(
        exploration_c=req.exploration_c,
        reward_range_width=req.reward_range_width,
        changed_by=req.changed_by,
    )
    # Apply to the running selection module immediately (single worker).
    set_ucb_params(c=result["exploration_c"], width=result["reward_range_width"])
    return {"status": "ok", **result}


@app.post("/config/policies")
def upsert_policy(req: PolicyUpsert):
    _guard_cfg().upsert_policy(
        domain=req.domain,
        intent=req.intent,
        topic=req.topic,
        strategy_id=req.strategy_id,
        policy_version=req.policy_version,
        exploration_constant=req.exploration_constant,
        changed_by=req.changed_by,
    )
    return {"status": "ok", "policy": f"{req.intent}#{req.topic}#{req.strategy_id}"}


@app.get("/config/instructions")
def list_instructions(strategy_id: Optional[str] = None, status: Optional[str] = None):
    """List instruction documents.

    Filters:
      - strategy_id: restrict to versions for one strategy
      - status:       e.g. ACTIVE / DRAFT / INACTIVE
    Sorted by strategy_id, then version descending.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    q: Dict[str, Any] = {"entity_type": ENTITY_INSTRUCTION}
    if strategy_id:
        q["entity_id"] = strategy_id
    if status:
        q["status"] = status
    rows = list(STORE.config.find(q).sort([("entity_id", 1), ("version", -1)]))
    return [_clean(r) for r in rows]


@app.post("/config/instructions")
def publish_instruction(req: InstructionPublish):
    mgr = _guard_cfg()
    mgr.publish_instruction(
        strategy_id=req.strategy_id,
        version=req.version,
        instruction_text=req.instruction_text,
        instruction_uri=req.instruction_uri,
        changed_by=req.changed_by,
    )
    if req.activate:
        mgr.activate_instruction(req.strategy_id, req.version, changed_by=req.changed_by)
    return {"status": "ok", "strategy_id": req.strategy_id, "version": req.version,
            "activated": req.activate}


@app.post("/config/instructions/activate")
def activate_instruction(strategy_id: str, version: str, changed_by: str = "admin_user"):
    _guard_cfg().activate_instruction(strategy_id, version, changed_by=changed_by)
    return {"status": "ok", "strategy_id": strategy_id, "version": version}


# ============================================================================
# DELETE endpoints — every config entity is removable from the admin UI.
# Each one is audited via STORE.log_admin_action so changes stay traceable.
# ============================================================================

def _audit_delete(entity_type: str, entity_id: str, changed_by: str, before: Optional[Dict[str, Any]]):
    """Helper: emit a DELETE audit entry."""
    if STORE is None:
        return
    STORE.log_admin_action(
        action_type="DELETE",
        entity_type=entity_type,
        entity_id=entity_id,
        changed_by=changed_by,
        before=before,
        after=None,
    )


def _find_config_for_delete(entity_type: str, entity_id: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return an admin-visible config doc regardless of ACTIVE/INACTIVE state.

    Runtime lookups intentionally use get_active_config(), but delete buttons in
    admin tables must also work for paused rows because those rows stay visible.
    """
    if STORE is None:
        return None
    return STORE.get_config(entity_type, entity_id, version=version)


@app.delete("/config/intents/{intent_id}")
def delete_intent(intent_id: str, changed_by: str = "admin_user"):
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    before = _find_config_for_delete(ENTITY_INTENT, intent_id)
    if not before:
        raise HTTPException(404, f"intent {intent_id} not found")
    n = STORE.delete_config(ENTITY_INTENT, intent_id)
    policies_deleted = STORE.config.delete_many({
        "entity_type": ENTITY_POLICY,
        "intent": intent_id,
    }).deleted_count
    _audit_delete(ENTITY_INTENT, intent_id, changed_by, before)
    return {
        "status": "ok",
        "deleted": n,
        "policies_deleted": policies_deleted,
        "intent_id": intent_id,
    }


@app.delete("/config/strategies/{strategy_id}")
def delete_strategy(strategy_id: str, changed_by: str = "admin_user"):
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    before = _find_config_for_delete(ENTITY_STRATEGY, strategy_id)
    if not before:
        raise HTTPException(404, f"strategy {strategy_id} not found")
    n = STORE.delete_config(ENTITY_STRATEGY, strategy_id)
    # Also drop all instructions for this strategy
    STORE.config.delete_many({"entity_type": ENTITY_INSTRUCTION, "entity_id": strategy_id})
    _audit_delete(ENTITY_STRATEGY, strategy_id, changed_by, before)
    return {"status": "ok", "deleted": n, "strategy_id": strategy_id}


@app.delete("/config/signal-rules/{signal_name}")
def delete_signal_rule(signal_name: str, changed_by: str = "admin_user"):
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    before = _find_config_for_delete(ENTITY_SIGNAL_RULE, signal_name)
    if not before:
        raise HTTPException(404, f"signal_rule {signal_name} not found")
    n = STORE.delete_config(ENTITY_SIGNAL_RULE, signal_name)
    _audit_delete(ENTITY_SIGNAL_RULE, signal_name, changed_by, before)
    return {"status": "ok", "deleted": n, "signal_name": signal_name}


@app.delete("/config/reward-scale/{category}")
def delete_reward_value(category: str, changed_by: str = "admin_user"):
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    before = _find_config_for_delete(ENTITY_REWARD_RULE, category)
    if not before:
        raise HTTPException(404, f"reward_scale {category} not found")
    n = STORE.delete_config(ENTITY_REWARD_RULE, category)
    _audit_delete(ENTITY_REWARD_RULE, category, changed_by, before)
    return {"status": "ok", "deleted": n, "category": category}


@app.delete("/config/policies")
def delete_policy(
    intent: str,
    topic: str,
    strategy_id: str,
    changed_by: str = "admin_user",
):
    """Policy rows are keyed by `intent#topic#strategy_id` — pass each piece."""
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    entity_id = f"{intent}#{topic}#{strategy_id}"
    before = _find_config_for_delete(ENTITY_POLICY, entity_id)
    if not before:
        raise HTTPException(404, f"policy {entity_id} not found")
    n = STORE.delete_config(ENTITY_POLICY, entity_id)
    _audit_delete(ENTITY_POLICY, entity_id, changed_by, before)
    return {"status": "ok", "deleted": n, "policy": entity_id}


@app.delete("/config/instructions/{strategy_id}/{version}")
def delete_instruction(strategy_id: str, version: str, changed_by: str = "admin_user"):
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    before = STORE.config.find_one({
        "entity_type": ENTITY_INSTRUCTION,
        "entity_id":   strategy_id,
        "version":     version,
    })
    if not before:
        raise HTTPException(404, f"instruction {strategy_id}@{version} not found")
    n = STORE.delete_config(ENTITY_INSTRUCTION, strategy_id, version=version)
    _audit_delete(ENTITY_INSTRUCTION, f"{strategy_id}@{version}", changed_by, before)
    return {"status": "ok", "deleted": n, "strategy_id": strategy_id, "version": version}


# ============================================================================
# Offer policies — CRUD for the offer_policy entity_type in ape_config.
# Powers the analytics page's "Recommended offers" table.
# ============================================================================

@app.get("/config/offers")
def list_offers(status: Optional[str] = None):
    """Admin view returns ALL offers (active + paused) by default.
    Filter by ?status=ACTIVE to mimic the runtime view."""
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    q: Dict[str, Any] = {"entity_type": ENTITY_OFFER_POLICY}
    if status:
        q["status"] = status
    rows = list(STORE.config.find(q).sort("entity_id", 1))
    return [_clean(r) for r in rows]


# ============================================================================
# Status toggle — pause/resume any config entity without deleting it.
# Runtime reads (get_active_config, list_active_config, get_policy_strategies,
# eligible_offers_for_user, _resolve_candidate_strategies, _load_active_instructions)
# all filter on status=ACTIVE, so flipping a doc to INACTIVE removes it from the
# runtime path immediately. Admin tabs still show it so it can be re-activated.
# ============================================================================

@app.post("/config/status")
def set_config_status(payload: Dict[str, Any]):
    """Flip the status on a config doc.

    Payload:
      {
        entity_type: "intent" | "strategy" | "instruction" | "policy" |
                     "signal_routing" | "reward_scale" | "offer_policy",
        entity_id:   "<id>",
        version:     "<optional version filter; required for instructions>",
        status:      "ACTIVE" | "INACTIVE" | "DRAFT",
        changed_by:  "<optional, defaults to 'admin_user'>",
      }
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")

    entity_type = payload.get("entity_type")
    entity_id   = payload.get("entity_id")
    new_status  = payload.get("status")
    version     = payload.get("version")
    changed_by  = payload.get("changed_by", "admin_user")

    if not entity_type or not entity_id or not new_status:
        raise HTTPException(400, "entity_type, entity_id, and status are required")
    if new_status not in ("ACTIVE", "INACTIVE", "DRAFT"):
        raise HTTPException(400, f"invalid status: {new_status}")

    # Capture before snapshot for audit
    q: Dict[str, Any] = {"entity_type": entity_type, "entity_id": entity_id}
    if version:
        q["version"] = version
    before = STORE.config.find_one(q)
    if not before:
        raise HTTPException(404, f"{entity_type}/{entity_id} not found")
    old_status = before.get("status")

    n = STORE.set_config_status(entity_type, entity_id, new_status, version=version)

    STORE.log_admin_action(
        action_type=f"STATUS_{new_status}",
        entity_type=entity_type,
        entity_id=entity_id if not version else f"{entity_id}@{version}",
        changed_by=changed_by,
        before={"status": old_status},
        after={"status": new_status},
    )
    return {
        "status":      "ok",
        "modified":    n,
        "entity_type": entity_type,
        "entity_id":   entity_id,
        "old_status":  old_status,
        "new_status":  new_status,
    }


@app.post("/config/offers")
def upsert_offer(payload: Dict[str, Any]):
    """Create or update an offer policy.

    Required keys: topic (entity_id), offer_type
    Optional keys: domain, description, min_interest_score, status,
                   weight_frequency, weight_recency,
                   weight_engagement, weight_followup
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")

    topic = (payload.get("topic") or payload.get("entity_id") or "").strip()
    if not topic:
        raise HTTPException(400, "Field 'topic' is required")
    offer_type = (payload.get("offer_type") or "").strip()
    if not offer_type:
        raise HTTPException(400, "Field 'offer_type' is required")

    def _opt_float(key: str) -> Optional[float]:
        v = payload.get(key)
        if v is None or v == "":
            return None
        try:
            f = float(v)
            return max(0.0, f)
        except (TypeError, ValueError):
            return None

    fields = {
        "domain":                   payload.get("domain", "finance"),
        "offer_type":               offer_type,
        "description":              payload.get("description", ""),
        "min_interest_score":       float(payload.get("min_interest_score", 0.7)),
        # Optional per-offer weight overrides. The recommender normalizes
        # whatever the admin enters so they can use either fractions (0.4 / 0.25)
        # or relative importance (4 / 2.5). Leaving them blank uses globals.
        "weight_frequency":         _opt_float("weight_frequency"),
        "weight_recency":           _opt_float("weight_recency"),
        "weight_engagement":        _opt_float("weight_engagement"),
        "weight_followup":          _opt_float("weight_followup"),
    }
    changed_by = payload.get("changed_by", "admin_user")
    before = STORE.get_config(ENTITY_OFFER_POLICY, topic)
    status = payload.get("status") or (before or {}).get("status") or STATUS_ACTIVE

    STORE.upsert_config(
        entity_type=ENTITY_OFFER_POLICY,
        entity_id=topic,
        fields=fields,
        status=status,
    )
    STORE.log_admin_action(
        action_type="UPSERT" if before is None else "UPDATE",
        entity_type=ENTITY_OFFER_POLICY,
        entity_id=topic,
        changed_by=changed_by,
        before=before,
        after={**fields, "status": status},
    )
    return {"status": "ok", "topic": topic, "offer_type": offer_type}


@app.delete("/config/offers/{topic}")
def delete_offer(topic: str, changed_by: str = "admin_user"):
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    before = _find_config_for_delete(ENTITY_OFFER_POLICY, topic)
    if not before:
        raise HTTPException(404, f"offer for topic {topic} not found")
    n = STORE.delete_config(ENTITY_OFFER_POLICY, topic)
    _audit_delete(ENTITY_OFFER_POLICY, topic, changed_by, before)
    return {"status": "ok", "deleted": n, "topic": topic}


# ============================================================================
# Ops endpoints
# ============================================================================

@app.delete("/admin/clear-user/{user_id}")
def admin_clear_user(user_id: str):
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_id_hash = hash_user_id(user_id)
    deleted = STORE.clear_user(user_id_hash)
    return {"status": "cleared", "user_id_hash": user_id_hash, **deleted}


@app.delete("/admin/clear-all")
def admin_clear_all():
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    return {"status": "cleared", **STORE.clear_all_runtime()}


@app.post("/admin/seed")
def admin_seed():
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    counts = seed_all(STORE)
    return {"status": "seeded", **counts}


@app.get("/admin/db-snapshot")
def admin_db_snapshot(user_id: Optional[str] = None, limit: int = 30):
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_id_hash = hash_user_id(user_id) if user_id else None
    return STORE.db_snapshot(user_id_hash=user_id_hash, limit=limit)


# ============================================================================
# Bandit state inspection (admin debug surface)
# ============================================================================

@app.get("/admin/bandit-state")
def admin_bandit_state(user_id: Optional[str] = None, only_pulled: bool = True):
    """List bandit_state rows. With `user_id` → only that user's cells.

    Use case: debugging "why did the bandit pick X for this user?" Shows every
    arm's count, avg_reward, cached_ucb. Rows are grouped by (domain, intent,
    topic) on the frontend so the admin sees each cell as a unit.

    `only_pulled=true` (default) filters out rows where count=0 (cold-start
    placeholders). Set false to see every lazy-created row.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    q: Dict[str, Any] = {}
    if user_id:
        q["user_id_hash"] = _resolve_user_hash(user_id)
    if only_pulled:
        q["count"] = {"$gt": 0}
    rows = list(STORE.bandit_state.find(q).sort([
        ("user_id_hash", 1),
        ("intent", 1),
        ("topic", 1),
        ("avg_reward", -1),
    ]).limit(2000))

    # Join display names from the directory for any user that has one
    user_hashes = {r.get("user_id_hash") for r in rows if r.get("user_id_hash")}
    name_map = STORE.get_display_names(user_hashes) if user_hashes else {}

    # Selection score is computed LIVE (no cache) — per cell, N = sum of counts,
    # then compute_ucb with the current c/width. Always reflects the live config.
    from .bandit.selection import display_selection_score
    cell_n: Dict[tuple, int] = {}
    for r in rows:
        key = (r.get("user_id_hash"), r.get("domain"), r.get("intent"), r.get("topic"))
        cell_n[key] = cell_n.get(key, 0) + int(r.get("count", 0))

    return [
        {
            "user_id_hash":    r.get("user_id_hash"),
            "display_name":    name_map.get(r.get("user_id_hash")),
            "domain":          r.get("domain"),
            "intent":          r.get("intent"),
            "topic":           r.get("topic"),
            "strategy":        r.get("strategy"),
            "count":           int(r.get("count", 0)),
            "total_reward":    round(float(r.get("total_reward", 0.0)), 4),
            "avg_reward":      round(float(r.get("avg_reward", 0.0)), 4),
            "cached_ucb":      display_selection_score(
                                   r.get("count", 0),
                                   r.get("total_reward", 0.0),
                                   cell_n[(r.get("user_id_hash"), r.get("domain"),
                                           r.get("intent"), r.get("topic"))],
                               ),
            "policy_version":  r.get("policy_version"),
            "ucb_algorithm":   r.get("ucb_algorithm"),
            "last_updated_at": r.get("last_updated_at"),
        }
        for r in rows
    ]


@app.delete("/admin/bandit-state/cell")
def admin_delete_bandit_cell(
    user_id: str,
    domain: str,
    intent: str,
    topic: str,
    strategy: Optional[str] = None,
):
    """Delete bandit state for a user.

    - With `strategy`  → delete one arm (one row).
    - Without          → delete the whole (intent, topic) cell for this user.

    The next /turn for this user re-lazy-creates the cell with cold-start
    values, so this is a safe "reset" operation when a cell got corrupted
    or an instruction was rewritten and you want fresh learning.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_id_hash = _resolve_user_hash(user_id)
    q: Dict[str, Any] = {
        "user_id_hash": user_id_hash,
        "domain":       domain,
        "intent":       intent,
        "topic":        topic,
    }
    scope = f"{intent}#{topic}"
    if strategy:
        q["strategy"] = strategy
        scope = f"{intent}#{topic}#{strategy}"
    n = STORE.bandit_state.delete_many(q).deleted_count

    STORE.log_admin_action(
        action_type="BANDIT_RESET",
        entity_type="bandit_state",
        entity_id=f"{user_id_hash}/{scope}",
        changed_by="admin_user",
        before={"deleted_count": n},
        after=None,
    )
    return {"status": "ok", "deleted": n, "scope": scope}


@app.get("/admin/audit")
def admin_audit(date: Optional[str] = None, limit: int = 100):
    return _guard_cfg().list_audit(date=date, limit=limit)


# ============================================================================
# Helpers
# ============================================================================

def _guard_cfg() -> ConfigManager:
    if CONFIG_MGR is None:
        raise HTTPException(500, "ConfigManager not initialized")
    return CONFIG_MGR


def _clean(doc):
    if doc is None:
        return None
    out = dict(doc)
    out.pop("_id", None)
    return out


# ============================================================================
# ANALYTICS (derived business stores)
# ============================================================================

@app.post("/analytics/recompute")
def analytics_recompute(days: int = 14):
    """Recompute both analytics collections from ape_turn_record.

    Cheap on a small corpus; on production data you'd want this on a cron
    rather than per-request.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    return recompute_all(STORE, days=days)


@app.get("/analytics/user-interests")
def analytics_user_interests(user_id: str, limit: int = 10, refresh: bool = False):
    """Top topics for one user, sorted by interest_score.

    `user_id` accepts either a raw user_id (we hash it) or an already-hashed
    `u_<hex>` identifier (used by the admin click-through from the active-users list).
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_id_hash = _resolve_user_hash(user_id)
    if refresh:
        compute_user_topic_interest(STORE, user_id_hash=user_id_hash)
    rows = list(
        STORE.db["ape_user_topic_interest"].find({"user_id_hash": user_id_hash})
                                            .sort("interest_score", -1)
                                            .limit(limit)
    )
    return [_clean(r) for r in rows]


@app.get("/analytics/topic-users")
def analytics_topic_users(topic: str, limit: int = 20, min_score: float = 0.5):
    """Users most interested in a given topic (privacy: only user_id_hash exposed)."""
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    rows = list(
        STORE.db["ape_user_topic_interest"].find({
            "topic": topic,
            "interest_score": {"$gte": float(min_score)},
        }).sort("interest_score", -1).limit(limit)
    )
    return [_clean(r) for r in rows]


@app.get("/analytics/trends")
def analytics_trends(days: int = 7, limit: int = 30, refresh: bool = False,
                     domain: Optional[str] = None):
    """Trending topics on the most recent day, sorted by trend_score."""
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    if refresh:
        compute_topic_trends(STORE, days=days)
    latest = STORE.db["ape_topic_trend_daily"].find_one(sort=[("date", -1)])
    if not latest:
        return []
    q: Dict[str, Any] = {"date": latest["date"]}
    if domain:
        q["domain"] = domain
    rows = list(
        STORE.db["ape_topic_trend_daily"].find(q)
                                          .sort("trend_score", -1)
                                          .limit(limit)
    )
    return [_clean(r) for r in rows]


@app.get("/analytics/topic-timeseries")
def analytics_topic_timeseries(topic: str, days: int = 30, domain: Optional[str] = None):
    """Daily counts for one topic — for sparkline charts."""
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    q: Dict[str, Any] = {"topic": topic}
    if domain:
        q["domain"] = domain
    rows = list(
        STORE.db["ape_topic_trend_daily"].find(q)
                                          .sort("date", -1)
                                          .limit(days)
    )
    rows.reverse()
    return [_clean(r) for r in rows]


@app.get("/analytics/platform-timeseries")
def analytics_platform_timeseries(days: int = 30, domain: Optional[str] = None):
    """Daily platform activity — aggregates ape_topic_trend_daily by date.

    Returns one row per day with total turns and unique-user count across
    all topics. Front-end uses this to draw the platform-overview sparkline.
    Output shape:
      [{"date": "2026-05-12", "total_turns": 84, "unique_users": 12}, ...]
    sorted ascending by date.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    pipeline: List[Dict[str, Any]] = []
    if domain:
        pipeline.append({"$match": {"domain": domain}})
    pipeline += [
        {"$sort": {"date": -1}},
        {"$group": {
            "_id":          "$date",
            "total_turns":  {"$sum": "$total_turns"},
            # Across topics on the same day, the SAME user can appear in
            # multiple topic rows, so summing unique_users over-counts. The
            # daily roll-up doesn't store the user set per day, so we
            # approximate with $max — the largest single-topic user count
            # for that day. This is a conservative lower bound and good
            # enough for a trend line; for exact unique users use the per-
            # turn aggregation below if you ever need precise numbers.
            "unique_users": {"$max": "$unique_users"},
        }},
        {"$sort": {"_id": 1}},
        {"$limit": int(days)},
    ]
    rows = list(STORE.db["ape_topic_trend_daily"].aggregate(pipeline))
    return [
        {"date": r["_id"], "total_turns": int(r["total_turns"]), "unique_users": int(r["unique_users"])}
        for r in rows
    ]


@app.get("/analytics/topics-timeseries")
def analytics_topics_timeseries(days: int = 30, top_n: int = 5, domain: Optional[str] = None):
    """Multi-series time chart for the top-N most active topics in the window.

    Output shape:
      [
        {"topic": "retirement_accounts",
         "series": [{"date": "2026-05-12", "count": 5}, ...]},
        ...
      ]
    The top-N is determined by total turns across the window. Each series
    is sorted ascending by date and zero-fills missing dates so the front-
    end can plot evenly-spaced points without per-series x-axis math.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")

    # Step 1 — find the top-N topics by total turns over the window.
    top_pipeline: List[Dict[str, Any]] = []
    if domain:
        top_pipeline.append({"$match": {"domain": domain}})
    top_pipeline += [
        {"$sort": {"date": -1}},
        {"$limit": int(days) * 200},   # window cap; topics × days
        {"$group": {"_id": "$topic", "total_turns": {"$sum": "$total_turns"}}},
        {"$sort": {"total_turns": -1}},
        {"$limit": int(top_n)},
    ]
    top_topics = [r["_id"] for r in STORE.db["ape_topic_trend_daily"].aggregate(top_pipeline)]
    if not top_topics:
        return []

    # Step 2 — pull the date series for those topics.
    series_q: Dict[str, Any] = {"topic": {"$in": top_topics}}
    if domain:
        series_q["domain"] = domain
    rows = list(
        STORE.db["ape_topic_trend_daily"].find(series_q)
                                          .sort("date", 1)
    )

    # Build the union of dates so we zero-fill consistently.
    all_dates = sorted({r["date"] for r in rows})
    # Keep only the last `days` calendar dates seen.
    if len(all_dates) > days:
        all_dates = all_dates[-days:]
    date_set = set(all_dates)

    by_topic: Dict[str, Dict[str, int]] = {t: {} for t in top_topics}
    for r in rows:
        if r["date"] in date_set:
            by_topic[r["topic"]][r["date"]] = int(r.get("total_turns", 0))

    out = []
    for t in top_topics:
        series = [{"date": d, "count": by_topic[t].get(d, 0)} for d in all_dates]
        out.append({"topic": t, "series": series})
    return out


@app.get("/analytics/user-timeseries")
def analytics_user_timeseries(user_id: str, days: int = 30, domain: Optional[str] = None):
    """Per-user daily activity — bucket this user's turn_record by date.

    Output shape:
      [{"date": "2026-05-12", "count": 4}, ...]
    sorted ascending by date. Zero-fills are intentionally OMITTED here —
    the front-end fills gaps so it can render either gapped bars or a
    continuous line as it prefers.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_id_hash = _resolve_user_hash(user_id)

    # Cutoff = today - days. `ts` is utcnow_iso() in turn_record, so a
    # YYYY-MM-DD prefix on $substr gives the calendar date in UTC, and a
    # string compare against the iso cutoff works lexicographically.
    cutoff_dt = datetime.utcnow() - timedelta(days=int(days))
    cutoff_iso = cutoff_dt.strftime("%Y-%m-%dT00:00:00")

    match: Dict[str, Any] = {
        "user_id_hash": user_id_hash,
        "ts":           {"$gte": cutoff_iso},
    }
    if domain:
        match["domain"] = domain
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id":   {"$substr": ["$ts", 0, 10]},   # YYYY-MM-DD
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    rows = list(STORE.db["ape_turn_record"].aggregate(pipeline))
    return [{"date": r["_id"], "count": int(r["count"])} for r in rows]


@app.get("/analytics/offers/{user_id}")
def analytics_offers(user_id: str, domain: Optional[str] = None):
    """Recommend offers based on interest_score + active offer_policy entries.

    `user_id` accepts a raw id or a hash (see _resolve_user_hash).
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_id_hash = _resolve_user_hash(user_id)
    return eligible_offers_for_user(
        STORE,
        user_id_hash=user_id_hash,
        domain=domain,
    )


@app.get("/analytics/customer-health")
def analytics_customer_health(days: int = 30, cohort_weeks: int = 4):
    """Customer-health rollup: retention cohorts + NPS satisfaction +
    behavioral engagement segments.

    All three views come from one MongoDB scan. Use for product/retention
    dashboards and quarterly satisfaction reporting.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    return compute_customer_health(
        STORE,
        days=days,
        cohort_weeks=cohort_weeks,
    )


@app.get("/analytics/rag-quality")
def analytics_rag_quality(days: int = 14, min_turns: int = 5, sample_limit: int = 5):
    """Surface TOPICS where RAG / knowledge-base content is failing.

    Different lens on the same problem signals as instruction-quality:
    - instruction_quality groups by (strategy, instruction_version)
      → "which instruction needs rewriting?"
    - rag_quality groups by topic
      → "which topic's knowledge base needs enriching?"

    Uses content_correction (weight 1.0) and reask_same_question
    (weight 0.5) to compute a weighted RAG failure rate per topic.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    return compute_rag_quality(
        STORE,
        days=days,
        min_turns=min_turns,
        sample_limit=sample_limit,
    )


@app.get("/analytics/instruction-quality")
def analytics_instruction_quality(days: int = 14, min_turns: int = 5, sample_limit: int = 5):
    """Surface (strategy, instruction_version) pairs producing problem signals.

    Reads format_compliance_fail / content_correction / reask_same_question
    incidence from ape_turn_record in the window. Groups by strategy +
    instruction version, computes failure rate, assigns tier
    (CRITICAL/HIGH/MEDIUM/LOW/EXPLORING), and attaches up to N sample
    failing turns per pair for admin inspection.

    The admin uses this to know which instructions to rewrite — and which
    signal type is dominating each pair's failures, so they can target
    the fix (format clarity vs factual accuracy vs comprehension).
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    return compute_instruction_quality(
        STORE,
        days=days,
        min_turns=min_turns,
        sample_limit=sample_limit,
    )


@app.get("/analytics/strategy-performance")
def analytics_strategy_performance(
    user_id: Optional[str] = None,
    domain: Optional[str] = None,
    min_pulls: int = 3,
):
    """Strategy diagnostics for the admin Policies tab.

    Returns:
      - global:    list of {strategy, total_pulls, avg_reward, performance_pct,
                            tier, unique_users, unique_cells, best_cell, worst_cell}
      - per_user:  same but filtered to one user (or null if user_id omitted)

    Tier mapping on the 0-100 performance scale:
      HIGH       ≥ 80    (avg_reward ≥ 0.60)
      MEDIUM     50-80
      LOW        < 50    (avg_reward < 0.00)
      EXPLORING  < min_pulls — not enough data to tier
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_hash = _resolve_user_hash(user_id) if user_id else None
    return compute_strategy_performance(
        STORE,
        user_id_hash=user_hash,
        domain=domain,
        min_pulls=min_pulls,
    )


@app.get("/analytics/platform-overview")
def analytics_platform_overview(
    days: int = 30,
    domain: Optional[str] = None,
    top_n: int = 8,
):
    """Cross-user macro view: top topics, top strategies, intent/signal mix,
    decision-stage funnel, and offer-readiness distribution — all aggregated
    over the selected window. No per-user identifiers in the response.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    return compute_platform_overview(
        STORE,
        days=days,
        domain=domain,
        top_n=top_n,
    )


@app.get("/analytics/unmapped-intents")
def analytics_unmapped_intents(
    days: int = 30,
    domain: Optional[str] = None,
    limit: int = 50,
):
    """Backlog of intents the classifier saw but the taxonomy doesn't cover.

    Groups turns that resolved to "unmapped" by the classifier's best-guess
    label (suggested_intent), so an admin can decide which to promote to a
    real intent. Aggregates only — no raw queries.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    return compute_unmapped_intents(
        STORE,
        days=days,
        domain=domain,
        limit=limit,
    )


@app.get("/analytics/active-users")
def analytics_active_users(
    days: int = 1,
    domain: Optional[str] = None,
    min_interest: float = 0.0,
    limit: int = 100,
):
    """Admin-facing slice: who was active in the last `days` days, what
    topics did they touch, and are they contact-ready (interest_score ≥ 0.7).

    Use this to drive outreach lists — the API surfaces candidates only;
    the contact decision must still pass downstream consent / compliance.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    return active_users_in_window(
        STORE,
        days=days,
        domain=domain,
        min_interest=min_interest,
        limit=limit,
    )


@app.get("/analytics/user-profile")
def analytics_user_profile(user_id: str, domain: Optional[str] = None):
    """Per-user Cognitive Profile — single dict with all 12 behavioral facets:
    topic interest, intent pattern, decision stage, engagement depth,
    format preference, structured-thinking, clarity need, friction, positive
    engagement, recency momentum, offer readiness, and learning confidence.

    `user_id` accepts a raw id or a hash (see _resolve_user_hash).
    Drives the "Cognitive Profile" hero card on the analytics page.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_id_hash = _resolve_user_hash(user_id)
    return compute_user_cognitive_profile(
        STORE,
        user_id_hash=user_id_hash,
        domain=domain,
    )


@app.get("/analytics/cognitive-facets")
def analytics_cognitive_facets(
    user_id: Optional[str] = None,
    domain: Optional[str] = None,
    min_interactions: int = 1,
):
    """Per-(intent, topic) facet view: leading strategy, runner-up, Beta(α,β),
    confidence score + tier, qualitative insight text.

    Scope is controlled by `user_id`:
      - omit user_id        → GLOBAL view, aggregates across all users.
                              Each facet includes `unique_users` so admin sees
                              how many people contributed to the cell.
      - pass user_id        → per-user view. Accepts raw id or u_<hash>.
    """
    if STORE is None:
        raise HTTPException(500, "Store not initialized")
    user_id_hash = _resolve_user_hash(user_id) if user_id else None
    return compute_cognitive_facets(
        STORE,
        user_id_hash=user_id_hash,
        domain=domain,
        min_interactions=min_interactions,
    )


# ============================================================================
# SPA static serving (production build)
# ============================================================================

_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
_ASSETS_DIR    = _FRONTEND_DIST / "assets"
_INDEX_HTML    = _FRONTEND_DIST / "index.html"


if _ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_ASSETS_DIR)), name="frontend-assets")


# Known client-side routes the React app handles. Any other unmatched path
# falls through to a 404 instead of silently serving the SPA shell.
_SPA_ROUTES = {"", "analytics", "admin"}


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    """Serve the SPA shell for known React routes; 404 everything else."""
    # Bare path or a known frontend route → serve the SPA
    if full_path in _SPA_ROUTES:
        if _INDEX_HTML.is_file():
            return FileResponse(_INDEX_HTML)
        raise HTTPException(404, "Frontend not built. Run `npm run build` inside frontend/.")

    # Anything else (typo API paths, unknown URLs) → 404
    raise HTTPException(404, "Not found")
