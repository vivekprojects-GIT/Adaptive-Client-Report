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
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
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
    ReportTypeUpsert,
    StrategyUpsert,
    TemplateUpsert,
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
    ENTITY_TEMPLATE,
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


# ----- Legacy turn-record view (kept for the analytics page) ----------------

@app.get("/config/intents")
def list_intents():
    return _guard_cfg().list_intents()


@app.get("/config/strategies")
def list_strategies():
    return _guard_cfg().list_strategies()


@app.get("/config/policies")
def list_policies():
    return _guard_cfg().list_policies()


# ---- Adaptive client reporting (D1) ---------------------------------------

@app.get("/config/report-types")
def list_report_types():
    return _guard_cfg().list_report_types()


@app.post("/config/report-types")
def upsert_report_type(req: ReportTypeUpsert):
    _guard_cfg().upsert_report_type(
        report_type=req.report_type,
        label=req.label,
        personalisable=req.personalisable,
        cadence=req.cadence,
        notes=req.notes,
        changed_by=req.changed_by,
    )
    return {"status": "ok", "report_type": req.report_type}


@app.get("/config/templates")
def list_templates(report_type: Optional[str] = None):
    return _guard_cfg().list_templates(report_type=report_type)


@app.post("/config/templates")
def upsert_template(req: TemplateUpsert):
    _guard_cfg().upsert_template(
        template_id=req.template_id,
        strategy=req.strategy,
        report_type=req.report_type,
        label=req.label,
        description=req.description,
        brief=req.brief,
        required_blocks=req.required_blocks,
        optional_blocks=req.optional_blocks,
        style_profile=req.style_profile,
        changed_by=req.changed_by,
    )
    return {"status": "ok", "template_id": req.template_id}


@app.delete("/config/templates/{template_id}")
def delete_template(template_id: str, changed_by: str = "admin_user"):
    before = _find_config_for_delete(ENTITY_TEMPLATE, template_id)
    if before is None:
        raise HTTPException(404, f"template '{template_id}' not found")
    _guard_store().config.delete_many(
        {"entity_type": ENTITY_TEMPLATE, "entity_id": template_id}
    )
    _audit_delete(ENTITY_TEMPLATE, template_id, changed_by, before)
    return {"status": "ok", "deleted": template_id}


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


@app.get("/config/thompson")
def get_thompson_config():
    """Live Thompson parameters for both decisions."""
    from .reporting.policy_config import thompson_params
    return thompson_params(force=True)


@app.post("/config/thompson")
async def update_thompson_config(request: Request):
    """Edit the prior strengths and apply them on the next selection."""
    body = await request.json()
    store = _guard_store()
    updates = {}
    for k in ("prior_strength_d1", "prior_strength_d2"):
        v = body.get(k)
        if v is not None:
            v = float(v)
            if not (0.0 < v <= 100.0):
                raise HTTPException(400, f"{k} must be in (0, 100]")
            updates[k] = v
    if not updates:
        raise HTTPException(400, "nothing to update")
    store.db["ape_config"].update_one(
        {"entity_type": "bandit_config", "entity_id": "thompson"},
        {"$set": {**updates, "policy": "thompson_sampling",
                  "status": "ACTIVE", "version": "_"}},
        upsert=True)
    from .reporting.policy_config import invalidate, thompson_params
    invalidate()
    return {"status": "ok", **thompson_params(force=True)}


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

@app.get("/admin/audit")
def admin_audit(date: Optional[str] = None, limit: int = 100):
    return _guard_cfg().list_audit(date=date, limit=limit)


# ============================================================================
# Helpers
# ============================================================================

def _guard_store() -> MongoStore:
    if STORE is None:
        raise HTTPException(503, "Store not ready")
    return STORE


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

# ---- Report preview (Phase 1) ---------------------------------------------
# Serves generated report artifacts. In production these live in S3 behind a
# signed URL; locally they are files on disk. The interface is the same:
# the client never gets a raw storage path, only an app URL.

# ---- Advisor back-office: clients + D1 decision detail ---------------------

@app.post("/clients/import")
async def import_clients(request: Request):
    """Persist clients from an uploaded CSV so the advisor has a real book to
    work from. Idempotent on client_id — re-importing updates in place."""
    from .reporting.csv_source import parse_csv
    body = await request.json()
    snaps, errors = parse_csv(body.get("csv_text", ""))

    # SQL is the data home reports are generated FROM; Mongo keeps a copy
    # for the transition but nothing reads it any more.
    from .db.session import init_db, session_scope
    from .db.repository import ingest_snapshot
    init_db()
    with session_scope() as db:
        for s in snaps:
            ingest_snapshot(db, s)

    store = _guard_store()
    for s in snaps:
        store.db["ape_clients"].update_one(
            {"client_id": s.client_id},
            {"$set": {
                "client_id": s.client_id, "display_name": s.display_name,
                "email": s.email, "segment_id": s.segment_id,
                "last_period": s.period, "portfolio_value": s.portfolio_value,
                # The FULL snapshot, so a report can be regenerated later
                # without re-uploading the CSV. Summary fields alone are not
                # enough to build blocks from.
                "snapshot": {
                    "client_id": s.client_id, "display_name": s.display_name,
                    "email": s.email, "segment_id": s.segment_id,
                    "period": s.period, "as_of": s.as_of,
                    "portfolio_value": s.portfolio_value,
                    "quarter_return_pct": s.quarter_return_pct,
                    "benchmark_return_pct": s.benchmark_return_pct,
                    "risk_level": s.risk_level,
                    "allocations": s.allocations,
                    "attribution": s.attribution,
                    "fees": s.fees, "cash_flows": s.cash_flows,
                },
            }},
            upsert=True,
        )
    return {"imported": len(snaps),
            "rejected": [{"row": e.row_number, "client_id": e.client_id,
                          "problems": e.problems} for e in errors]}


@app.get("/clients")
def list_clients(q: Optional[str] = None, limit: int = 200):
    """The advisor's book, from SQL — the same tables generation reads."""
    from .db.session import init_db, session_scope
    from .db.repository import list_clients as _sql_clients, list_periods
    init_db()
    rows = []
    with session_scope() as db:
        for c in _sql_clients(db):
            if q and q.lower() not in (c.client_id + c.name + c.email).lower():
                continue
            periods = list_periods(db, c.client_id)
            from .db.models import ReportSnapshot as _RS
            from sqlalchemy import select as _sel
            latest_snap = db.scalars(
                _sel(_RS).where(_RS.client_id == c.client_id)
                .order_by(_RS.period.desc())).first()
            rows.append({
                "client_id": c.client_id, "display_name": c.name,
                "email": c.email, "segment_id": c.segment_id,
                "risk_profile": c.risk_profile,
                "periods": periods,
                "last_period": periods[-1] if periods else None,
                "portfolio_value": latest_snap.portfolio_value if latest_snap else 0.0,
            })
            if len(rows) >= limit:
                break
    # Latest report per client, for the "Last report / Status" columns.
    gen = Path(__file__).resolve().parents[1] / "data" / "generated"
    latest: Dict[str, Dict[str, Any]] = {}
    if gen.is_dir():
        for f in sorted(gen.glob("*.json"), key=lambda x: x.stat().st_mtime):
            try:
                r = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            latest[r.get("client_id")] = r
    out = []
    for r in rows:
        rep = latest.get(r.get("client_id"))
        out.append({**r,
                    "last_report_period": (rep or {}).get("period"),
                    "last_report_id": (rep or {}).get("report_id"),
                    "last_strategy": (rep or {}).get("template_strategy"),
                    "status": "Complete" if rep else "No report"})
    return out


@app.get("/ape/d1-decision")
def d1_decision(client_id: str, report_type: str):
    """Full explainable D1 decision for ONE client + report type.

    Returns the arm scores, the preference inputs behind them, and how much
    weight the client's own evidence currently carries. This is what the
    advisor sees when they ask 'why this template?'.
    """
    from .reporting.d1 import (cell_key, eligible_arms, evidence_weight,
                               score_arms, select, DIMENSIONS)
    cfg = _guard_cfg(); store = _guard_store()

    rt = next((r for r in cfg.list_report_types()
               if r.get("report_type") == report_type), None)
    if rt is None:
        raise HTTPException(404, f"unknown report type '{report_type}'")

    # Client identity and learned profile come from SQL — the same store
    # the viewer writes and generation reads. The old Mongo ape_clients rows
    # are import-era leftovers and can name people who no longer exist.
    from .db.session import init_db, session_scope
    from .db.models import Client as _Client, ClientPreference as _Pref
    init_db()
    with session_scope() as _db:
        _c = _db.get(_Client, client_id)
        client_name = _c.name if _c else client_id
        segment_id = _c.segment_id if _c else "unsegmented"
        _p = _db.get(_Pref, client_id)
        sql_profile = _p.as_dimensions() if _p else None
        sql_signals = _p.meaningful_signal_count if _p else 0

    templates = cfg.list_templates()
    arms = eligible_arms(templates, report_type)
    key = cell_key(report_type)
    from .db.models import ApeState as _AS
    from sqlalchemy import select as _sel
    with session_scope() as _db:
        state = {r.arm_id: {"count": int(r.selection_count),
                            "total_reward": float(r.total_reward)}
                 for r in _db.scalars(_sel(_AS).where(
                     _AS.decision == "D1", _AS.scope_type == "GLOBAL",
                     _AS.context == report_type))}
    arm_state = {a["strategy"]: state.get(a["strategy"],
                                          {"count": 0, "total_reward": 0.0})
                 for a in arms}

    # The learned profile. Zero signals means it is reported as absent —
    # a profile nobody has learned must not pretend to be knowledge.
    client_profile = sql_profile if sql_signals > 0 else None
    n_signals = sql_signals

    seg_doc = store.db["ape_preference_profile"].find_one(
        {"scope": "SEGMENT", "key": segment_id})
    segment_profile = (seg_doc or {}).get("dimensions")

    personalisable = bool(rt.get("personalisable", True))
    if personalisable:
        strategy, rows, method = select(
            templates, arm_state, report_type, True,
            client_profile=client_profile, n_signals=n_signals,
            segment_profile=segment_profile)
    else:
        strategy, rows, method = select(templates, arm_state, report_type, False)

    return {
        "client_id": client_id,
        "client_name": client_name,
        "segment_id": segment_id,
        "report_type": report_type,
        "report_type_label": rt.get("label"),
        "personalisable": personalisable,
        "cell_key": key,
        "selected": strategy,
        "method": method,
        "user_weight": evidence_weight(n_signals),
        "meaningful_signal_count": n_signals,
        "has_client_profile": client_profile is not None,
        "has_segment_profile": segment_profile is not None,
        "dimensions": list(DIMENSIONS),
        "client_profile": client_profile or {},
        "arms": rows,
    }


# ============================================================================
# SPA static serving (production build)
# ============================================================================

_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
_ASSETS_DIR    = _FRONTEND_DIST / "assets"
_INDEX_HTML    = _FRONTEND_DIST / "index.html"

if _ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_ASSETS_DIR)),
              name="frontend-assets")

# Known client-side routes the React app handles. Any other unmatched path
# falls through to a 404 instead of silently serving the SPA shell.
# "analytics" is gone — that page was the chat product's.
_SPA_ROUTES = {"", "admin"}


@app.post("/reports/generate-one")
async def generate_one_report(request: Request):
    """Generate a single report for an already-imported client.

    The advisor screen works client-by-client, so it needs a path that does
    not require re-uploading a CSV. Reads the stored snapshot, runs D1, and
    writes the same artifacts as a batch run.
    """
    from .reporting.csv_source import ClientSnapshot
    from .reporting.d1 import cell_key, eligible_arms, select
    from .reporting.generate import build_report, render_html

    body = await request.json()
    client_id = body.get("client_id")
    report_type = body.get("report_type") or "quarterly_portfolio_review"

    store = _guard_store(); cfg = _guard_cfg()

    # Snapshot from SQL — the shared relational book. Mongo fallback covers
    # anything imported before the SQL layer existed.
    from .db.session import init_db, session_scope
    from .db.repository import load_snapshot as _sql_snapshot
    init_db()
    snap = None
    try:
        with session_scope() as db:
            snap = _sql_snapshot(db, client_id, body.get("period"))
    except LookupError:
        doc = store.db["ape_clients"].find_one({"client_id": client_id})
        if doc and doc.get("snapshot"):
            snap = ClientSnapshot(**doc["snapshot"])
    if snap is None:
        raise HTTPException(404, f"no stored snapshot for client '{client_id}'")

    rt = next((r for r in cfg.list_report_types()
               if r.get("report_type") == report_type), None)
    if rt is None:
        raise HTTPException(404, f"unknown report type '{report_type}'")
    templates = cfg.list_templates()
    arms = eligible_arms(templates, report_type)
    if not arms:
        raise HTTPException(400, f"no active templates for '{report_type}'")

    key = cell_key(report_type)

    # D1 state lives in SQL ape_state, same table as D2 — one store for
    # both decisions. (The old Mongo collection carried a chat-era unique
    # index without cell_key, which silently collapsed every report type
    # onto one row per strategy.)
    from .db.models import ApeState as _AS, ClientPreference as _Pref
    from sqlalchemy import select as _sel
    with session_scope() as _db:
        _rows = _db.scalars(_sel(_AS).where(
            _AS.decision == "D1", _AS.scope_type == "GLOBAL",
            _AS.context == report_type)).all()
        state = {r.arm_id: {"count": int(r.selection_count),
                            "total_reward": float(r.total_reward)}
                 for r in _rows}
        _p = _db.get(_Pref, client_id)
        _profile = (_p.as_dimensions()
                    if _p and _p.meaningful_signal_count > 0 else None)
        _nsig = _p.meaningful_signal_count if _p else 0
    arm_state = {a["strategy"]: state.get(a["strategy"],
                                          {"count": 0, "total_reward": 0.0})
                 for a in arms}

    strategy, rows, method = select(
        templates, arm_state, report_type,
        bool(rt.get("personalisable", True)),
        client_profile=_profile, n_signals=_nsig)

    # count rises at SELECTION so cold-start exploration advances even
    # before any reward lands.
    with session_scope() as _db:
        _row = _db.scalars(_sel(_AS).where(
            _AS.decision == "D1", _AS.scope_type == "GLOBAL",
            _AS.context == report_type, _AS.arm_id == strategy)).first()
        if _row is None:
            _row = _AS(scope_type="GLOBAL", scope_id="_global",
                       decision="D1", context=report_type, arm_id=strategy,
                       alpha=1.0, beta=1.0, selection_count=0,
                       reward_count=0, total_reward=0.0)
            _db.add(_row)
        _row.selection_count += 1

    template = next(t for t in arms if t["strategy"] == strategy)
    report = build_report(snap, template, report_type)

    # THE LLM WRITES THE PROSE. Style comes from the control plane: the
    # selected template's strategy plus this client's learned dimensions.
    # Every model sentence goes through the same grounding gate below; a
    # rejected draft falls back to the code-built block, so a bad model day
    # degrades style, never truth.
    from .reporting.writer import write_prose_blocks
    from .db.models import ClientPreference
    dims = None
    with session_scope() as db:
        prefs = db.get(ClientPreference, client_id)
        if prefs is not None:
            dims = prefs.as_dimensions()
    authors = write_prose_blocks(report, snap, strategy, dims)

    # GROUNDING GATE. Every number in every block must trace to the frozen
    # snapshot. Rejected blocks are DROPPED, not corrected and not rendered
    # with a warning — a plausible wrong figure is worse than a missing
    # section. Today all blocks are code-built so this should always pass;
    # it becomes load-bearing the moment the LLM writes one.
    from .reporting.grounding import validate_report
    verdict = validate_report(report, snap.numeric_facts(), snap.label_terms())
    if verdict.rejected:
        report["blocks"] = verdict.accepted
        report["rejected_blocks"] = [
            {"block_id": f.block_id, "kind": f.kind, "detail": f.detail}
            for f in verdict.findings
        ]

    out = Path(__file__).resolve().parents[1] / "data" / "generated"
    out.mkdir(parents=True, exist_ok=True)
    rid = report["report_id"]
    (out / f"{rid}.html").write_text(render_html(report), encoding="utf-8")
    (out / f"{rid}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    # SQL: the report row (arm, method — the reward address) and every
    # block (source_refs — the localisation for highlight-to-ask).
    from .db.repository import persist_report
    with session_scope() as db:
        persist_report(db, report, strategy, method,
                       template.get("template_id") or "",
                       "passed" if verdict.ok else "rejected_blocks",
                       authors)

    return {
        "report_id": rid, "client_id": client_id, "strategy": strategy,
        "method": method, "template_id": template.get("template_id"),
        "template_label": template.get("label"),
        "blocks": [b["type"] for b in report["blocks"]],
        "authors": authors,
        "validation": "passed" if verdict.ok else "rejected_blocks",
        "validation_summary": verdict.summary(),
        "validation_findings": [
            {"block_id": f.block_id, "kind": f.kind, "detail": f.detail}
            for f in verdict.findings
        ],
        "email_status": "sent (stub)",
        "arms": rows,
    }


@app.post("/reports/generate")
async def generate_reports(request: Request):
    """Upload a CSV and generate one report per row.

    Body: multipart with `file` (the CSV) and `report_type`, OR JSON with
    `csv_text` + `report_type` so it is scriptable without a browser.
    """
    from .reporting.batch import generate_batch

    csv_text = ""
    report_type = "quarterly_portfolio_review"

    ctype = request.headers.get("content-type", "")
    if ctype.startswith("multipart/form-data"):
        form = await request.form()
        report_type = str(form.get("report_type") or report_type)
        upload = form.get("file")
        if upload is None:
            raise HTTPException(400, "no file supplied")
        csv_text = (await upload.read()).decode("utf-8-sig", errors="replace")
    else:
        body = await request.json()
        csv_text = body.get("csv_text", "")
        report_type = body.get("report_type") or report_type

    if not csv_text.strip():
        raise HTTPException(400, "CSV is empty")

    cfg = _guard_cfg()
    rt = next((r for r in cfg.list_report_types()
               if r.get("report_type") == report_type), None)
    if rt is None:
        raise HTTPException(404, f"unknown report type '{report_type}'")

    return generate_batch(
        csv_text=csv_text,
        report_type=report_type,
        templates=cfg.list_templates(),
        personalisable=bool(rt.get("personalisable", True)),
        store=_guard_store(),
    )


# ---- Secure client report link + delivery ---------------------------------

@app.post("/reports/{report_id}/send")
async def send_report(report_id: str, request: Request):
    """Mint a signed link and deliver it. Provider chosen by EMAIL_PROVIDER."""
    from .reporting.email import get_provider
    from .reporting.tokens import report_url

    gen = Path(__file__).resolve().parents[1] / "data" / "generated"
    f = gen / f"{report_id}.json"
    if not f.is_file():
        raise HTTPException(404, f"no generated report '{report_id}'")
    rep = json.loads(f.read_text(encoding="utf-8"))

    try:
        body = await request.json()
    except Exception:
        body = {}
    base = body.get("base_url") or str(request.base_url).rstrip("/")

    url = report_url(report_id, rep["client_id"], base_url=base)
    try:
        result = get_provider(body.get("provider")).send_report_ready(
            to_email=rep.get("email", ""),
            client_name=rep.get("client_name", ""),
            report_url=url,
            period=rep.get("period", ""),
        )
    except Exception as exc:
        raise HTTPException(502, f"email failed: {exc}")

    _guard_store().db["ape_report_delivery"].update_one(
        {"report_id": report_id},
        {"$set": {"report_id": report_id, "client_id": rep["client_id"],
                  "to": rep.get("email"), "provider": result.get("provider"),
                  "status": result.get("status"), "sent_at": datetime.utcnow().isoformat()}},
        upsert=True,
    )
    return {**result, "report_id": report_id}


@app.get("/r/{report_id}", response_class=HTMLResponse)
def client_report_view(report_id: str, token: str = ""):
    """The client-facing surface. The TOKEN is the authorisation.

    Report ids are guessable, so knowing one must never be enough. A valid
    token for a different report fails here too — that is the cross-client
    case.
    """
    from .reporting.tokens import TokenError, verify
    try:
        verify(token, report_id=report_id)
    except TokenError as exc:
        return HTMLResponse(
            f'<!doctype html><meta charset="utf-8"><title>Link problem</title>'
            f'<div style="font-family:Segoe UI,system-ui,Arial;max-width:460px;'
            f'margin:14vh auto;text-align:center;color:#0f172a">'
            f'<h2 style="font-size:19px">This link cannot be opened</h2>'
            f'<p style="color:#64748b;font-size:14px;line-height:1.6">{_esc_html(str(exc))}.'
            f'<br>Report links are personal and expire. Please ask your adviser '
            f'to send a fresh one.</p></div>', status_code=403)

    gen = Path(__file__).resolve().parents[1] / "data" / "generated"
    f = gen / f"{report_id}.json"
    if not f.is_file():
        raise HTTPException(404, "report not found")
    report = json.loads(f.read_text(encoding="utf-8"))
    from .reporting.viewer import render_viewer
    return HTMLResponse(render_viewer(report, token))


def _viewer_auth(report_id: str, token: str) -> None:
    from .reporting.tokens import TokenError, verify as _verify
    try:
        _verify(token, report_id=report_id)
    except TokenError as exc:
        raise HTTPException(403, str(exc))


def _report_json(report_id: str) -> dict:
    f = (Path(__file__).resolve().parents[1] / "data" / "generated"
         / f"{report_id}.json")
    if not f.is_file():
        raise HTTPException(404, "report not found")
    return json.loads(f.read_text(encoding="utf-8"))


@app.get("/reports/{report_id}/link")
def report_client_link(report_id: str, request: Request):
    """A signed client-view URL WITHOUT sending anything. The advisor's
    review should look at exactly what the client will see — same page,
    same token gate — not the internal preview."""
    _report_json(report_id)          # 404 before minting
    from .reporting.tokens import mint
    report = _report_json(report_id)
    token = mint(report_id, report["client_id"])
    base = str(request.base_url).rstrip("/")
    return {"url": f"{base}/r/{report_id}?token={token}",
            "expires": "14 days"}


@app.get("/clients/{client_id}/insight")
def client_insight(client_id: str):
    """What the system has LEARNED about this client — the advisor's window
    into the adaptation. Empty profile is reported as exactly that, never
    dressed up as knowledge."""
    from .db.session import init_db, session_scope
    from .db.models import ClientPreference, Event, Message, Report
    from sqlalchemy import select as _sel, func as _fn
    init_db()
    with session_scope() as db:
        pref = db.get(ClientPreference, client_id)
        dims = pref.as_dimensions() if pref else {}
        n = pref.meaningful_signal_count if pref else 0

        reports = []
        for r in db.scalars(_sel(Report).where(Report.client_id == client_id)
                            .order_by(Report.created_at.desc()).limit(10)):
            nev = db.scalar(_sel(_fn.count()).select_from(Event)
                            .where(Event.report_id == r.report_id))
            nq = db.scalar(_sel(_fn.count()).select_from(Message)
                           .where(Message.report_id == r.report_id,
                                  Message.role == "client"))
            reports.append({
                "report_id": r.report_id, "period": r.period,
                "template_arm": r.template_arm, "status": r.status,
                "engagement": round(r.normalized_reward or 0.0, 2),
                "events": nev or 0, "questions": nq or 0,
            })
        recent = [{"event_type": e.event_type, "block_id": e.block_id,
                   "at": e.created_at.isoformat(timespec="seconds")}
                  for e in db.scalars(
                      _sel(Event).where(Event.client_id == client_id)
                      .order_by(Event.created_at.desc()).limit(12))]
    return {"client_id": client_id, "signals": n, "dimensions": dims,
            "reports": reports, "recent_events": recent}


@app.get("/ape/d1-state")
def d1_state():
    """Template-decision posteriors per report type — same shape as
    /ape/d2-state so the two admin tabs stay twins."""
    from .db.session import init_db, session_scope
    from .db.models import ApeState
    from sqlalchemy import select as _sel
    init_db()
    out: Dict[str, list] = {}
    with session_scope() as db:
        for r in db.scalars(_sel(ApeState).where(ApeState.decision == "D1")
                            .order_by(ApeState.context, ApeState.arm_id)):
            mean = ((1.0 + r.total_reward) /
                    (2.0 + r.reward_count)) if r.reward_count else 0.5
            out.setdefault(r.context, []).append({
                "arm": r.arm_id, "selected": r.selection_count,
                "rewarded": r.reward_count,
                "total_reward": round(r.total_reward, 2),
                "posterior_mean": round(mean, 3),
                "updated_at": r.updated_at.isoformat(timespec="seconds"),
            })
    return {"contexts": out}


@app.get("/ape/d2-state")
def d2_state():
    """The answer-format decision's posteriors, grouped by question intent.
    SQL ape_state is the live store D2 selects from — this is a read of the
    real thing, not a report about it."""
    from .db.session import init_db, session_scope
    from .db.models import ApeState
    from sqlalchemy import select as _sel
    init_db()
    out: Dict[str, list] = {}
    with session_scope() as db:
        for r in db.scalars(_sel(ApeState).where(ApeState.decision == "D2")
                            .order_by(ApeState.context, ApeState.arm_id)):
            mean = ((1.0 + r.total_reward) /
                    (2.0 + r.reward_count)) if r.reward_count else 0.5
            out.setdefault(r.context, []).append({
                "arm": r.arm_id, "selected": r.selection_count,
                "rewarded": r.reward_count,
                "total_reward": round(r.total_reward, 2),
                "posterior_mean": round(mean, 3),
                "updated_at": r.updated_at.isoformat(timespec="seconds"),
            })
    return {"contexts": out}


@app.post("/r/{report_id}/chat")
async def report_chat(report_id: str, request: Request):
    """The client talks to the report. Token-gated like the page itself;
    the highlighted block localises the answer to its own facts."""
    body = await request.json()
    _viewer_auth(report_id, str(body.get("token", "")))

    report = _report_json(report_id)
    question = str(body.get("question", "")).strip()
    if not question:
        raise HTTPException(400, "empty question")
    block_id = body.get("block_id") or None

    from .db.session import init_db, session_scope
    from .db.models import ReportBlock
    from .db.repository import load_snapshot as _sql_snapshot
    from .reporting.csv_source import ClientSnapshot as _CS
    from .reporting.d2 import answer_question
    from .reporting.rewards import record_event
    from sqlalchemy import select as _select
    init_db()

    with session_scope() as db:
        try:
            snap = _sql_snapshot(db, report["client_id"], report.get("period"))
        except LookupError:
            raise HTTPException(404, "client facts not on file")

        block = None
        if block_id:
            row = db.scalars(_select(ReportBlock).where(
                ReportBlock.report_id == report_id,
                ReportBlock.block_id == block_id)).first()
            if row is not None:
                block = {"block_id": row.block_id,
                         "block_type": row.block_type,
                         "content_json": row.content_json,
                         "source_refs": row.source_refs}
            else:
                # Report predates SQL persistence: fall back to the JSON.
                block = next((b for b in report["blocks"]
                              if b["block_id"] == block_id), None)

        result = answer_question(
            db, snap, report_id, question, block,
            selected_text=str(body.get("selected_text", "")),
            conversation_id=body.get("conversation_id"))

        # The question itself is a signal: engagement for D1, and its
        # wording may carry format preferences for the profile.
        record_event(db, report["client_id"], "question_asked",
                     report_id=report_id, block_id=block_id or "",
                     metadata={"question": question,
                               "intent": result["intent"]})
    return result


@app.post("/r/{report_id}/events")
async def report_events(report_id: str, request: Request):
    """Engagement signals from the viewer. Every event is stored raw, then
    routed: D2 reward, D1 reward, preference profile — or all three."""
    body = await request.json()
    _viewer_auth(report_id, str(body.get("token", "")))
    report = _report_json(report_id)

    from .db.session import init_db, session_scope
    from .reporting.rewards import record_event
    init_db()
    with session_scope() as db:
        out = record_event(
            db, report["client_id"],
            str(body.get("event_type", "")),
            report_id=report_id,
            block_id=str(body.get("block_id", "") or ""),
            message_id=str(body.get("message_id", "") or ""),
            metadata=body.get("metadata") or {})
    return out


def _esc_html(s: str) -> str:
    import html as _h
    return _h.escape(s)


@app.get("/reports/generated")
def list_generated_reports():
    """Everything generated so far, newest first."""
    d = Path(__file__).resolve().parents[1] / "data" / "generated"
    if not d.is_dir():
        return []
    out = []
    for f in sorted(d.glob("*.json"), key=lambda x: -x.stat().st_mtime):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        out.append({
            "report_id":   r.get("report_id"),
            "client_id":   r.get("client_id"),
            "client_name": r.get("client_name"),
            "email":       r.get("email"),
            "period":      r.get("period"),
            "report_type": r.get("report_type"),
            "strategy":    r.get("template_strategy"),
            "template_id": r.get("template_id"),
            "label":       r.get("template_label"),
            "blocks":      [b.get("type") for b in r.get("blocks", [])],
            "email_status": "sent (stub)",
        })
    return out


@app.get("/reports/{report_id}/html")
def get_report_html(report_id: str):
    d = Path(__file__).resolve().parents[1] / "data" / "generated"
    f = d / f"{report_id}.html"
    if not f.is_file():
        raise HTTPException(404, f"no generated report '{report_id}'")
    return HTMLResponse(f.read_text(encoding="utf-8"))


@app.get("/reports/{report_id}/json")
def get_report_json(report_id: str):
    d = Path(__file__).resolve().parents[1] / "data" / "generated"
    f = d / f"{report_id}.json"
    if not f.is_file():
        raise HTTPException(404, f"no generated report '{report_id}'")
    return json.loads(f.read_text(encoding="utf-8"))


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
