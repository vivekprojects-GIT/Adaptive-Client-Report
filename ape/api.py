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
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import (FileResponse, HTMLResponse,
                               RedirectResponse, StreamingResponse)
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


def _resolve_language(body: dict, snap) -> str:
    """Which language this report is written in. Most specific wins.

        explicit language on the request   advisor picked from the dropdown
        -> language implied by the country advisor picked a country only
        -> the client's stored language    their standing preference
        -> ENGLISH

    English is the floor, always. A report nobody asked to be translated
    stays in English rather than being guessed into a language the reader
    may not have — guessing wrong here hands someone a document they
    cannot read, which is worse than an unlocalised one.

    Resolved once, here, so prose, number formatting and the grounding
    check all see the same answer. Splitting this decision is how a report
    ends up written in one convention and validated in another.
    """
    from .reporting.locales import get as _get_locale, language_for_country
    lang = str(body.get("language") or "").strip()
    if not lang:
        country = str(body.get("country") or "").strip()
        if country:
            lang = language_for_country(country)
    if not lang:
        lang = getattr(snap, "language", "") or ""
    return _get_locale(lang).code if lang else ""


def templates_for(templates, report_type):
    """ACTIVE templates authored for this report type.

    Template lists are report-type specific by design — there is no
    universal list, because a template's blocks assume that type's facts.
    Lived in reporting/d1.py as `eligible_arms` until the bandit went; the
    filtering was never bandit logic, only its caller was.
    """
    return [t for t in templates
            if t.get("report_type") == report_type
            and t.get("status", "ACTIVE") == "ACTIVE"]


app = FastAPI(title="APE Modular — Production (MongoDB)", version="2.0.0")

# Public-host hardening: advisor gate, gmail token from secret, boot
# seeding. Every piece is env-driven and a no-op in local dev.
from .deploy import install as _install_deploy_gate
_install_deploy_gate(app)

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

    # Warm the voice models off the request path. Whisper-tiny costs ~9s on
    # its very first load (download + init) and piper ~1.5s per voice;
    # paying either inside a client's first spoken turn reads as the
    # feature being broken. A daemon thread, because a slow model download
    # must never hold the server's startup hostage.
    def _warm_voice():
        try:
            from .reporting.transcribe import warm as _stt_warm
            _stt_warm()
        except Exception:
            pass
        try:
            from .reporting.speak import warm as _tts_warm
            _tts_warm("en")
        except Exception:
            pass
    import threading as _threading
    _threading.Thread(target=_warm_voice, daemon=True).start()

    # Keep the podcast renderer awake. A free Render instance sleeps after
    # ~15 minutes idle and then 502s for the best part of a minute while it
    # wakes — which is what a stalled "generating..." actually was. A ping
    # every ten minutes keeps that timer from expiring. Costs ~730 of the
    # account's ~750 free instance-hours a month; APE_RENDERER_KEEPWARM=0
    # turns it off and leaves the reactive wake_renderer path in place.
    if os.getenv("APE_RENDERER_KEEPWARM", "1") != "0":
        def _keep_renderer_warm():
            try:
                from .reporting.podcast import keep_warm
                keep_warm(float(os.getenv("APE_RENDERER_KEEPWARM_SECONDS",
                                           "600")))
            except Exception:
                pass
        _threading.Thread(target=_keep_renderer_warm, daemon=True,
                          name="renderer-keepwarm").start()
        print("[startup] renderer keep-warm on", flush=True)

    return ApeOrchestrator(client=client, model=model, store=store, domain=domain, rag=RAG)


@app.on_event("startup")
def startup() -> None:
    from .deploy import run_boot_tasks
    run_boot_tasks()
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

# ---- Adaptive client reporting --------------------------------------------

@app.get("/registry/blocks")
def registry_blocks():
    """The widget palette, grouped by the fact CATEGORY each block covers.

    Category is the useful grouping rather than block name: coverage is
    enforced per category, so an author choosing between two blocks needs
    to know which one closes the same gap.
    """
    from .reporting.registry import CHART_KINDS, REGISTRY
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for name, meta in REGISTRY.items():
        by_cat.setdefault(meta["category"], []).append({
            "block": name, "shows": meta["shows"],
            "needs": meta["needs"], "kind": "block"})
    for kind, (cat, shows) in CHART_KINDS.items():
        by_cat.setdefault(cat, []).append({
            "block": f"chart:{kind}", "shows": shows,
            "needs": "allocations", "kind": "chart"})
    return {"categories": [
        {"category": c, "blocks": sorted(by_cat[c], key=lambda b: b["block"])}
        for c in sorted(by_cat)]}


@app.get("/registry/templates")
def registry_templates():
    """Every template, nested under the report type that owns it.

    The nesting is the point: a template belongs to exactly one report
    type because its blocks assume that type's facts, and a flat list
    hides the one relationship that matters.
    """
    cfg = _guard_cfg()
    types = {t["report_type"]: t for t in cfg.list_report_types()}
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for t in cfg.list_templates():
        by_type.setdefault(t.get("report_type", ""), []).append({
            "template_id": t.get("template_id"),
            "label": t.get("label") or t.get("strategy"),
            "description": t.get("description", ""),
            "blocks": t.get("required_blocks", []) or [],
        })
    out = []
    for rt in sorted(set(types) | set(by_type)):
        tpl = sorted(by_type.get(rt, []), key=lambda x: x["label"] or "")
        out.append({
            "report_type": rt,
            "label": (types.get(rt) or {}).get("label", rt.replace("_", " ")),
            "prescribed": (types.get(rt) or {}).get("personalisable", True) is False,
            "templates": tpl,
        })
    return {"report_types": out}


@app.get("/registry/preferences")
def registry_preferences():
    """What has been learned, nested client -> report type.

    Only scopes with evidence are listed. A row of neutral 0.5s for every
    client against every one of sixteen report types would be a tree of
    things nobody has observed, which reads as knowledge and is not.
    """
    from .db.session import init_db, session_scope
    from .db.models import Client, ClientPreference, ClientSkill
    from .reporting.rewards import profile_for
    from sqlalchemy import select as _s
    init_db()
    out = []
    with session_scope() as db:
        names = {c.client_id: c.name for c in db.scalars(_s(Client))}
        rows: Dict[str, List[Any]] = {}
        for r in db.scalars(_s(ClientPreference)):
            rows.setdefault(r.client_id, []).append(r)
        skills: Dict[tuple, Any] = {
            (sk.client_id, sk.report_type): sk
            for sk in db.scalars(_s(ClientSkill))}

        for cid, prefs in sorted(rows.items()):
            scopes = []
            for r in sorted(prefs, key=lambda x: x.report_type):
                sk = skills.get((cid, r.report_type))
                dims = profile_for(db, cid, r.report_type)
                moved = {k: v for k, v in dims.items() if abs(v - 0.5) > 0.02}
                # A scope with no signals, nothing moved off the prior and
                # nothing stated is a row asserting knowledge that does not
                # exist. The client-wide row is not exempt: a client who has
                # never interacted should be absent from this tree, not
                # present with a line of zeroes.
                if (r.meaningful_signal_count <= 0 and not moved
                        and not (sk and sk.stated_prefs)):
                    continue
                scopes.append({
                    "report_type": r.report_type,
                    "scope": r.report_type or "(all report types)",
                    "signals": r.meaningful_signal_count,
                    "moved": {k: round(v, 3) for k, v in moved.items()},
                    "stated": (sk.stated_prefs if sk else []) or [],
                    "brief_lines": [l for l in
                                    ((sk.brief if sk else "") or "").splitlines()
                                    if l.strip()],
                })
            if scopes:
                out.append({"client_id": cid,
                            "name": names.get(cid, cid), "scopes": scopes})
    return {"clients": out}


# What each signal class is FOR. Shown beside the raw event so an advisor
# reads consequence, not just occurrence — "they opened it" and "they said
# it was confusing" are both events and are not remotely the same thing.
_SIGNAL_MEANING = {
    "report_opened":     ("engagement", "Opened the report"),
    "dwell_60s":         ("engagement", "Stayed with it over a minute"),
    "pdf_downloaded":    ("engagement", "Downloaded a copy"),
    "block_highlighted": ("attention",  "Highlighted a section"),
    "section_viewed":    ("attention",  "Scrolled a section into view"),
    "question_asked":    ("ambiguous",  "Asked a question"),
    "visual_requested":  ("preference", "Asked to see a chart"),
    "answer_helpful":    ("quality",    "Marked an answer helpful"),
    "answer_unhelpful":  ("quality",    "Marked an answer unhelpful"),
    "report_helpful":    ("quality",    "Said the report helped"),
    "report_unhelpful":  ("quality",    "Said the report was not helpful"),
}


@app.get("/config/locales")
def list_locales():
    """Countries and languages for the advisor's dropdowns.

    Countries carry their default language so the UI can preselect one
    without a second round trip — but the language list is returned whole,
    because the advisor must be able to override. A Dutch client who wants
    English reporting is common, not an edge case.
    """
    from .reporting.locales import countries, supported
    return {"countries": countries(), "languages": supported()}


@app.get("/alerts")
def list_alerts(limit: int = 50, unread_only: bool = False):
    """Adviser notifications — newest first, with an unread count.

    Behind the same advisor gate as every other admin surface: these name
    clients who are struggling, which is not public information.
    """
    from .db.session import init_db, session_scope
    from .db.models import AdviserAlert, Client
    from sqlalchemy import select as _s, func as _f
    init_db()
    out, unread = [], 0
    with session_scope() as db:
        unread = db.scalar(
            _s(_f.count()).select_from(AdviserAlert)
            .where(AdviserAlert.acknowledged_at.is_(None))) or 0
        q = _s(AdviserAlert).order_by(AdviserAlert.created_at.desc())
        if unread_only:
            q = q.where(AdviserAlert.acknowledged_at.is_(None))
        for a in db.scalars(q.limit(max(1, min(limit, 200)))):
            client = db.get(Client, a.client_id)
            out.append({
                "alert_id": a.alert_id,
                "client_id": a.client_id,
                "client_name": (client.name if client else a.client_id),
                "report_id": a.report_id,
                "trigger": a.trigger,
                "detail": a.detail,
                "delivery_status": a.delivery_status,
                "acknowledged": a.acknowledged_at is not None,
                "created_at": a.created_at.isoformat() if a.created_at else "",
            })
    return {"alerts": out, "unread": unread}


@app.post("/alerts/{alert_id}/ack")
def acknowledge_alert(alert_id: str):
    """Mark one alert as dealt with.

    Acknowledgement is explicit, not inferred from opening the panel — an
    adviser scanning a list has not necessarily actioned anything in it,
    and auto-clearing would quietly lose the one that mattered.
    """
    from datetime import datetime as _dt
    from .db.session import init_db, session_scope
    from .db.models import AdviserAlert
    init_db()
    with session_scope() as db:
        row = db.get(AdviserAlert, alert_id)
        if row is None:
            raise HTTPException(404, "no such alert")
        if row.acknowledged_at is None:
            row.acknowledged_at = _dt.utcnow()
    return {"status": "ok", "alert_id": alert_id}


@app.get("/registry/signals")
def registry_signals(limit: int = 400):
    """The raw signals, nested client -> report type -> event.

    The preference tree shows what was CONCLUDED. This shows what was
    observed, which is the only way to check a conclusion — an advisor
    surprised by a profile needs to see the clicks behind it, not a
    better summary of them.

    Every event is stored verbatim and nothing here is derived; the only
    additions are the signal's class and a plain-English label, so the
    difference between "opened it" and "said it was confusing" is legible
    without knowing the event vocabulary.
    """
    from .db.session import init_db, session_scope
    from .db.models import Client, Event, Report
    from sqlalchemy import select as _s
    init_db()
    out: List[Dict[str, Any]] = []
    with session_scope() as db:
        names = {c.client_id: c.name for c in db.scalars(_s(Client))}
        rtype = {r.report_id: r.report_type
                 for r in db.scalars(_s(Report))}

        rows = list(db.scalars(_s(Event)
                               .order_by(Event.created_at.desc())
                               .limit(max(1, min(limit, 2000)))))
        by_client: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for e in rows:
            scope = rtype.get(e.report_id, "") or "(no report)"
            meta = e.metadata_json or {}
            detail = ""
            if e.event_type == "question_asked":
                detail = str(meta.get("question", ""))[:150]
            elif e.event_type == "visual_requested":
                detail = (f"{meta.get('binding')} as {meta.get('kind')}"
                          if meta.get("drawn")
                          else f"could not draw — {str(meta.get('reason',''))[:90]}")
            cls, label = _SIGNAL_MEANING.get(e.event_type,
                                             ("other", e.event_type))
            by_client.setdefault(e.client_id, {}).setdefault(scope, []).append({
                "event_type": e.event_type, "label": label, "class": cls,
                "block_id": e.block_id or "", "detail": detail,
                "applies_to": e.applies_to or "",
                "at": e.created_at.isoformat(timespec="seconds"),
            })

        for cid, scopes in by_client.items():
            total = sum(len(v) for v in scopes.values())
            out.append({
                "client_id": cid, "name": names.get(cid, cid), "total": total,
                "scopes": [{"scope": sc.replace("_", " "), "events": ev}
                           for sc, ev in sorted(scopes.items())],
            })
    out.sort(key=lambda c: -c["total"])
    return {"clients": out, "shown": sum(c["total"] for c in out),
            "limit": limit}


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
        language=req.language,
        country=req.country,
        changed_by=req.changed_by,
    )
    return {"status": "ok", "template_id": req.template_id}


@app.post("/config/templates/preview")
async def preview_template(request: Request):
    """Render a DRAFT template — unsaved — through the real pipeline.

    This deliberately calls the same build_report / enforce_mandatory /
    validate_report / render_html path that generation uses, against a real
    client snapshot. A preview built any other way would be a second
    renderer that drifts from the first, and the whole point is that what
    the admin sees is what the client gets.

    Returns the document HTML plus what the coverage gate had to add — so
    an author who forgets the fees table sees it appear and learns why.
    """
    body = await request.json()
    report_type = body.get("report_type") or "quarterly_portfolio_review"
    blocks = body.get("required_blocks") or []
    if not blocks:
        raise HTTPException(400, "no blocks to preview")

    from .db.session import init_db, session_scope
    from .db.repository import list_clients as _sql_clients, load_snapshot
    from .reporting.generate import (build_report, enforce_mandatory,
                                     render_html)
    from .reporting.grounding import validate_report
    init_db()

    with session_scope() as db:
        client_id = body.get("client_id")
        if not client_id:
            people = _sql_clients(db)
            if not people:
                raise HTTPException(400, "no clients on file to preview with")
            client_id = people[0].client_id
        try:
            snap = load_snapshot(db, client_id, body.get("period"))
        except LookupError as exc:
            raise HTTPException(404, str(exc))

    template = {
        "template_id": body.get("template_id") or "__preview__",
        "strategy": body.get("strategy") or "preview",
        "label": body.get("label") or "Preview",
        "brief": body.get("brief") or "",
        "required_blocks": blocks,
    }
    report = build_report(snap, template, report_type)
    # Stamped HERE, before prose is written and before validation runs.
    # Both of those read it: the writer to choose the language, the
    # validator to choose the number convention. Setting it later meant the
    # gate checked a Dutch callout with English rules and dropped it, and
    # the only trace was "1 rejected".
    report["language"] = getattr(snap, "language", "") or ""
    enforced = enforce_mandatory(report, snap)
    verdict = validate_report(report, snap.numeric_facts(), snap.label_terms())
    if verdict.rejected:
        report["blocks"] = verdict.accepted

    # Blocks the source cannot support return None and simply do not appear;
    # naming them is how the author learns this client has no holdings
    # detail rather than wondering where the block went.
    built = {b["type"] for b in report["blocks"]}
    unsupported = [b for b in blocks
                   if b.split(":")[0] not in built
                   and b.split(":")[0] != "chart"]

    return {
        "html": render_html(report, internal=False),
        "client_id": client_id, "client_name": snap.display_name,
        "period": snap.period,
        "blocks_rendered": [b["type"] for b in report["blocks"]],
        "enforced_blocks": enforced,
        "unsupported_blocks": unsupported,
        "validation_summary": verdict.summary(),
    }


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


@app.get("/config/selection")
def get_selection_config():
    """Live UCB parameters for both decisions."""
    from .reporting.policy_config import selection_params
    return selection_params(force=True)


@app.post("/config/selection")
async def update_selection_config(request: Request):
    """Edit prior strengths / exploration constant; applies on the next
    selection."""
    body = await request.json()
    store = _guard_store()
    updates = {}
    for k in ("prior_strength_d1", "prior_strength_d2", "exploration_c"):
        v = body.get(k)
        if v is not None:
            v = float(v)
            if not (0.0 < v <= 100.0):
                raise HTTPException(400, f"{k} must be in (0, 100]")
            updates[k] = v
    if not updates:
        raise HTTPException(400, "nothing to update")
    store.db["ape_config"].update_one(
        {"entity_type": "bandit_config", "entity_id": "selection"},
        {"$set": {**updates, "policy": "ucb_contextual",
                  "status": "ACTIVE", "version": "_"}},
        upsert=True)
    from .reporting.policy_config import invalidate, selection_params
    invalidate()
    return {"status": "ok", **selection_params(force=True)}


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

# ---- Advisor back-office: clients ------------------------------------------

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


# ============================================================================
# SPA static serving (production build)
# ============================================================================

_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
_ASSETS_DIR    = _FRONTEND_DIST / "assets"
_INDEX_HTML    = _FRONTEND_DIST / "index.html"

_STATIC_DIR = Path(__file__).resolve().parent / "static"

if _STATIC_DIR.is_dir():
    # The chart runtime and the vendored ECharts build. Same origin on
    # purpose: a client opening their report must not have to reach a CDN
    # for it to render.
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)),
              name="ape-static")

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
    not require re-uploading a CSV. Reads the stored snapshot, builds the
    report from the chosen or composed template, and
    writes the same artifacts as a batch run.
    """
    from .reporting.csv_source import ClientSnapshot
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

    snap.language = _resolve_language(body, snap)

    rt = next((r for r in cfg.list_report_types()
               if r.get("report_type") == report_type), None)
    if rt is None:
        raise HTTPException(404, f"unknown report type '{report_type}'")
    templates = cfg.list_templates()
    arms = templates_for(templates, report_type)
    if not arms:
        raise HTTPException(400, f"no active templates for '{report_type}'")

    from .db.models import ClientPreference as _Pref
    with session_scope() as _db:
        # The profile that shapes THIS report is the one for THIS report
        # type. profile_for blends in the client-wide row, so a type with
        # no history of its own still starts from what is known about the
        # client rather than from a neutral 0.5 across the board.
        from .reporting.rewards import profile_for
        _wide = _db.get(_Pref, (client_id, ""))
        _p = _db.get(_Pref, (client_id, report_type))
        _any = (_p.meaningful_signal_count if _p else 0) or                (_wide.meaningful_signal_count if _wide else 0)
        _profile = profile_for(_db, client_id, report_type) if _any else None
        _nsig = (_p.meaningful_signal_count if _p else 0)

    # Two ways to get a template, and neither is learned:
    #   the advisor names one they authored for this report type, or
    #   the composer designs a one-off from the block registry.
    # Nothing explores and nothing is rewarded for the CHOICE — what
    # improves the next report is the preference profile and the skill
    # brief, both of which reach the composer as inputs.
    compose = str(body.get("composer") or "").lower() in ("llm", "true", "1")

    chosen_id = str(body.get("template_id") or "").strip()
    chosen = None
    if chosen_id:
        chosen = next((t for t in templates
                       if t.get("template_id") == chosen_id), None)
        if chosen is None:
            raise HTTPException(404, f"no template '{chosen_id}'")
        if chosen.get("report_type") != report_type:
            # Templates bind to a report type because their blocks assume
            # that type's facts. Silently rendering one against another
            # would produce a document that looks authored and is not.
            raise HTTPException(
                400, f"template '{chosen_id}' belongs to "
                     f"'{chosen.get('report_type')}', not '{report_type}'")
        compose = False
    else:
        # Nothing selects a template any more, so with none named the
        # composer is the only route. Decided here rather than trusted to
        # the UI, because a direct API call has no UI to constrain it.
        compose = True

    compose_diag = None
    if chosen is not None:
        template = chosen
        strategy = chosen.get("strategy") or chosen_id
        method = "advisor_choice"
        rows = []
    elif compose:
        from .reporting.composer import compose_template
        from .reporting.skill import skill_text
        with session_scope() as _db:
            _skill = skill_text(_db, client_id, report_type)
        template, compose_diag = compose_template(snap, report_type, _profile,
                                                  skill=_skill)
        strategy = template["strategy"]
        method = "llm_composed"
        rows = []

    report = build_report(snap, template, report_type)
    # Same reason as the preview path: prose and validation both read this,
    # so it must exist before either runs.
    report["language"] = getattr(snap, "language", "") or ""

    # Structural coverage gate: mandatory categories (costs, disclosures)
    # are appended if the template omitted them. Personalisation may not
    # shrink what the client is told.
    from .reporting.generate import enforce_coverage, enforce_mandatory
    # Order matters: repair missing CATEGORIES first (a thin data source may
    # have voided the arm's preferred renderings), then guarantee the
    # mandatory blocks regardless.
    enforced = enforce_coverage(report, snap) + enforce_mandatory(report, snap)

    # THE LLM WRITES THE PROSE. Style comes from the control plane: the
    # selected template's strategy plus this client's learned dimensions.
    # Every model sentence goes through the same grounding gate below; a
    # rejected draft falls back to the code-built block, so a bad model day
    # degrades style, never truth.
    from .reporting.writer import write_prose_blocks
    from .db.models import ClientPreference
    dims = None
    with session_scope() as db:
        from .reporting.rewards import profile_for
        rt = str(report.get("report_type", "") or "")
        if db.get(ClientPreference, (client_id, "")) is not None:
            dims = profile_for(db, client_id, rt)
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

    # No media here. Both are built when the advisor SENDS, after they have
    # reviewed the draft — see _start_media_job.
    #
    # Generating on every draft renders audio and video for reports that
    # are still being edited, or discarded, and spends the one renderer we
    # have on work nobody asked for. Send is the point at which this report
    # is real.

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
        "enforced_blocks": enforced,
        "composer": compose_diag,
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
    snap.language = _resolve_language(body, snap)

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

    # Start the audio the moment the link goes out, not when the client
    # opens it.
    #
    # Generation already kicks one off, but send is the deadline that
    # matters: from here a client can click the link at any second, and
    # anything not started by now is something they wait for. This also
    # covers the report that was generated days ago, or whose first render
    # failed — by the time the email lands, a fresh attempt is running.
    #
    # Idempotent. The in-flight guard drops a duplicate, and a podcast that
    # already exists is found in the database and never re-rendered.
    try:
        from .db.session import init_db as _init, session_scope as _scope
        from .db.repository import load_snapshot as _load
        _init()
        with _scope() as _db:
            _snap = _load(_db, rep["client_id"], rep.get("period"))
        if _snap is not None:
            _start_media_job(report_id, rep, _snap)
    except Exception as exc:            # sending must never fail for media
        print(f"[podcast] could not start job on send for {report_id}: "
              f"{type(exc).__name__}: {str(exc)[:100]}", flush=True)

    url = report_url(report_id, rep["client_id"], base_url=base)
    try:
        result = get_provider(body.get("provider")).send_report_ready(
            to_email=rep.get("email", ""),
            client_name=rep.get("client_name", ""),
            report_url=url,
            period=rep.get("period", ""),
        )
    except Exception as exc:
        # A MAIL PROBLEM IS NOT A FAILED REPORT.
        #
        # This raised 502, which an advisor reads as "the system broke" —
        # and it threw away the two things that were actually fine: the
        # report is finished and its signed link is valid. Gmail simply
        # needing a one-time authorisation on this machine should not look
        # like a server crash, and it should not leave the advisor with
        # nothing to hand their client.
        #
        # So: report it as UNSENT, plainly, with the link and the remedy.
        # Nothing here pretends the email went — that would be far worse
        # than an error — but the advisor can still copy the link, and the
        # audio and video jobs started above are unaffected.
        detail = str(exc)
        low = detail.lower()
        if "invalid_grant" in low or "expired or revoked" in low:
            # The commonest Gmail failure here, and the least obvious.
            # Google expires refresh tokens after SEVEN DAYS while the
            # OAuth app sits in "Testing", so a setup that worked when it
            # was made stops silently a week later. Saying "check your
            # credentials" sends someone hunting for a problem that is not
            # there — the credentials are fine, the grant simply aged out.
            remedy = ("The Gmail token has expired. Re-run "
                      "scripts/connect_gmail.py to refresh it. Google expires "
                      "these after 7 days while the OAuth app is in Testing — "
                      "publish the app (Google Auth Platform > Audience) to "
                      "stop it recurring weekly.")
        elif "token.json" in low:
            remedy = ("Run scripts/connect_gmail.py once to authorise this "
                      "machine, or set EMAIL_PROVIDER=file to write the "
                      "message to disk instead.")
        else:
            remedy = "Check EMAIL_PROVIDER and the provider's credentials."
        print(f"[send] {report_id}: email not sent — {detail[:160]}", flush=True)
        return {"status": "not sent", "sent": False,
                "provider": (body.get("provider")
                             or _os_getenv_provider()),
                "to": rep.get("email", ""), "url": url,
                "error": detail[:300], "remedy": remedy,
                "report_id": report_id}

    _guard_store().db["ape_report_delivery"].update_one(
        {"report_id": report_id},
        {"$set": {"report_id": report_id, "client_id": rep["client_id"],
                  "to": rep.get("email"), "provider": result.get("provider"),
                  "status": result.get("status"), "sent_at": datetime.utcnow().isoformat()}},
        upsert=True,
    )
    return {**result, "report_id": report_id}


def _os_getenv_provider() -> str:
    import os as _os
    return _os.getenv("EMAIL_PROVIDER", "file")


def _first_name(client_id: str) -> str:
    """First name only, for the greeting on the identity page."""
    try:
        from .db.models import Client
        from .db.session import init_db, session_scope
        init_db()
        with session_scope() as db:
            row = db.get(Client, client_id)
            return (row.name or "").split()[0] if row and row.name else ""
    except Exception:
        return ""


@app.post("/r/{report_id}/verify", response_class=HTMLResponse)
async def client_report_verify(request: Request, report_id: str):
    """Check the answer; on success write the pass and open the report.

    The token is re-verified here rather than trusted from the form. The
    form field is client-controlled, so treating it as already-checked
    would let anyone mint access by posting a report id and any string.
    """
    from .reporting.identity import (IdentityError, challenge_html,
                                     cookie_name, cookie_path, mint_pass,
                                     verify_answer, PASS_TTL_SECONDS)
    from .reporting.tokens import TokenError, verify

    form = await request.form()
    token = str(form.get("token", ""))
    given = str(form.get("birth_year", ""))

    try:
        _rid, client_id, _scope = verify(token, report_id=report_id)
    except TokenError:
        raise HTTPException(403, "link cannot be verified")

    from .db.session import init_db, session_scope
    init_db()
    try:
        with session_scope() as db:
            verify_answer(db, report_id, client_id, given)
    except IdentityError as exc:
        # Wrong answers are logged: repeated failures on one report are
        # what an attempt to guess a link looks like from the server side.
        print(f"[SECURITY] identity check failed for {report_id} "
              f"({client_id}): {exc}", flush=True)
        return HTMLResponse(
            challenge_html(report_id, token, first_name=_first_name(client_id),
                           error=str(exc)),
            status_code=401)

    # 303 so the browser re-issues as GET; a refresh then reloads the
    # report rather than re-posting the form.
    resp = RedirectResponse(
        url=f"/r/{report_id}?token={quote(token, safe='')}", status_code=303)
    resp.set_cookie(
        key=cookie_name(report_id), value=mint_pass(report_id, client_id),
        # NO max_age — a SESSION cookie, gone when the browser closes.
        #
        # With max_age set this was written to disk and survived everything:
        # closing the tab, closing the browser, restarting the machine. A
        # client who answered once on a shared laptop left that report
        # unlocked there for a fortnight.
        #
        # Without it the cookie lives in memory for this browsing session
        # only, and the pass inside it expires on its own after
        # PASS_TTL_SECONDS regardless. Two independent limits: close the
        # browser, or wait out the clock.
        path=cookie_path(report_id),
        httponly=True,          # never readable by page script
        samesite="lax",         # not sent on cross-site POSTs
        secure=request.url.scheme == "https",
    )
    return resp


@app.get("/r/{report_id}", response_class=HTMLResponse)
def client_report_view(request: Request, report_id: str, token: str = ""):
    """The client-facing surface, behind two gates.

    The TOKEN proves the link is genuine — report ids are guessable, so
    knowing one must never be enough, and a valid token for a different
    report fails here too (the cross-client case).

    The IDENTITY PASS proves the holder is the client the link was issued
    to. The token cannot do that: it travels in a URL, and a URL can be
    forwarded, pasted into a chat, or left in a shared inbox. Without this
    second gate, whoever holds the link is the client.
    """
    from .reporting.tokens import TokenError, verify
    try:
        _rid, client_id, _scope = verify(token, report_id=report_id)
    except TokenError as exc:
        # A client may be told why THEIR link failed. They may not be told
        # that the server has no signing secret — that names the exact
        # misconfiguration to whoever is probing, and it is not their
        # problem to solve. Config faults are logged and shown as a
        # generic failure.
        detail = str(exc)
        if "APE_REPORT_TOKEN_SECRET" in detail:
            print(f"[SECURITY] report link refused — {detail}", flush=True)
            shown = "This link cannot be verified right now"
        else:
            shown = _esc_html(detail)
        return HTMLResponse(
            f'<!doctype html><meta charset="utf-8"><title>Link problem</title>'
            f'<div style="font-family:Segoe UI,system-ui,Arial;max-width:460px;'
            f'margin:14vh auto;text-align:center;color:#0f172a">'
            f'<h2 style="font-size:19px">This link cannot be opened</h2>'
            f'<p style="color:#64748b;font-size:14px;line-height:1.6">{shown}.'
            f'<br>Report links are personal and expire. Please ask your adviser '
            f'to send a fresh one.</p></div>', status_code=403)

    # Second gate. The pass is written only after the client answers, and
    # is scoped to this one report, so it cannot be carried across links.
    from .reporting.identity import (challenge_html, cookie_name,
                                     verify_pass)
    if not verify_pass(request.cookies.get(cookie_name(report_id), ""),
                       report_id, client_id):
        return HTMLResponse(
            challenge_html(report_id, token, first_name=_first_name(client_id)),
            status_code=401)

    gen = Path(__file__).resolve().parents[1] / "data" / "generated"
    f = gen / f"{report_id}.json"
    if not f.is_file():
        raise HTTPException(404, "report not found")
    report = json.loads(f.read_text(encoding="utf-8"))

    # The snapshot is loaded only so the opening chips know which charts
    # this client's data can fill. A failure here must not cost anyone
    # their report — the chips fall back to text-only questions.
    snap = None
    try:
        from .db.session import init_db, session_scope
        from .db.repository import load_snapshot as _sql_snapshot
        init_db()
        with session_scope() as _db:
            snap = _sql_snapshot(_db, report["client_id"],
                                 report.get("period"))
    except Exception:
        snap = None

    from .reporting.viewer import render_viewer
    return HTMLResponse(render_viewer(report, token, snapshot=snap))


def _viewer_auth(report_id: str, token: str,
                 request: Optional[Request] = None) -> str:
    """Both gates on the client surface. Returns the client_id.

    The token proves the URL is genuine; the identity pass proves the
    holder answered the verification question. Gating only the HTML page
    would be theatre — the page is a shell, and the report content, the
    conversation history and the chat all arrive through these endpoints.
    Anyone with the URL could read the lot with curl.
    """
    from .reporting.tokens import TokenError, verify as _verify
    try:
        _rid, client_id, _scope = _verify(token, report_id=report_id)
    except TokenError as exc:
        detail = str(exc)
        if "APE_REPORT_TOKEN_SECRET" in detail:
            print(f"[SECURITY] report request refused — {detail}", flush=True)
            raise HTTPException(403, "link cannot be verified")
        raise HTTPException(403, detail)

    if request is not None:
        from .reporting.identity import cookie_name, verify_pass
        held = request.cookies.get(cookie_name(report_id), "")
        if not verify_pass(held, report_id, client_id):
            # 401 rather than 403: the caller may still become authorised
            # by answering, which is exactly what the viewer does with it.
            raise HTTPException(401, "identity not confirmed for this report")
    return client_id


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
        from .reporting.rewards import profile_for
        from sqlalchemy import select as _s2
        pref = db.get(ClientPreference, (client_id, ""))
        dims = profile_for(db, client_id, "")
        n = pref.meaningful_signal_count if pref else 0
        # What has been learned PER REPORT TYPE, so an advisor can see that
        # a quarterly review and a tax summary are being shaped differently
        # rather than having to infer it from one blended number.
        by_type = [
            {"report_type": r.report_type, "signals": r.meaningful_signal_count,
             "dimensions": profile_for(db, client_id, r.report_type)}
            for r in db.scalars(_s2(ClientPreference).where(
                ClientPreference.client_id == client_id,
                ClientPreference.report_type != ""))
            if r.meaningful_signal_count > 0]

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
        # The composer's memory of this client, in words. Surfaced so an
        # advisor can see what the system believes and correct it.
        from .reporting.skill import refresh_skill
        skill_row = refresh_skill(db, client_id, "")
        from .reporting.stated_prefs import for_advisor
        skill = {"brief": skill_row.brief,
                 "advisor_note": skill_row.advisor_note,
                 "evidence_count": skill_row.evidence_count,
                 "top_blocks": skill_row.top_blocks,
                 "ignored_blocks": skill_row.ignored_blocks,
                 "stated": skill_row.stated_prefs or [],
                 # Requests no part of the generation pipeline can satisfy
                 # — a video walkthrough, a printed copy, a phone call.
                 # Shown to the advisor precisely because the system
                 # cannot act on them and somebody should.
                 "needs_a_human": for_advisor(skill_row.stated_prefs)}

    return {"client_id": client_id, "signals": n, "dimensions": dims,
            "reports": reports, "recent_events": recent, "skill": skill,
            "by_report_type": by_type}


@app.post("/clients/{client_id}/skill-note")
async def set_skill_note(client_id: str, request: Request):
    """An advisor's own note about how this client likes to be written to.

    It takes precedence over anything inferred: someone who has met the
    client knows more than their click history does.
    """
    body = await request.json()
    from .db.session import init_db, session_scope
    from .db.models import ClientSkill
    init_db()
    with session_scope() as db:
        rt = str(body.get("report_type", "") or "")
        row = db.get(ClientSkill, (rt, client_id))
        if row is None:
            row = ClientSkill(client_id=client_id, report_type=rt)
            db.add(row)
        row.advisor_note = str(body.get("note", ""))[:600]
        note = row.advisor_note
    return {"status": "ok", "advisor_note": note}


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


# rid -> unix time the job started. The VALUE matters: a client that
# refreshes mid-render must see the elapsed time keep climbing, not
# restart from zero as though nothing had happened yet.
_PODCAST_JOBS: Dict[str, float] = {}
_PODCAST_JOBS_LOCK = __import__("threading").Lock()


def _pregenerate_disabled(os_module) -> bool:
    """Whether to SKIP building media at report-generation time.

    OFF BY DEFAULT, AND THE DEFAULT IS THE POINT.
    ────────────────────────────────────────────────────────────────────
    Approving a report used to fire a podcast and a video for it whether
    or not anybody ever opened it. On a renderer that serialises every
    render behind one lock, a batch of approvals became a queue of renders
    nobody had asked for, each one competing with the clients who HAD
    asked - and each one more chance to push a 512MB instance over.

    The client's click is the honest signal that a medium is wanted. It
    costs them the wait, which is the trade being made deliberately: a
    slower first play for a renderer that is not busy making things no one
    will listen to.

    APE_PODCAST_PREGENERATE=1 restores the head start on a renderer with
    the capacity for it. A client click always renders either way - this
    governs the head start, never the feature.
    """
    return (os_module.getenv("APE_PODCAST_PREGENERATE", "0").strip().lower()
            not in ("1", "true", "yes", "on"))


def _start_podcast_job(rid: str, report: Dict[str, Any], snap,
                       minutes: int = 1, on_demand: bool = False) -> None:
    """Render this report's podcast in the background. One job per report.

    Started by a client clicking Listen, or at generation time when
    APE_PODCAST_PREGENERATE=1. Either way the client never waits on the
    renderer and never sees it fail — the page asks whether the audio is
    ready, and until it is, it says so.

    The de-duplication is not a nicety. Two clicks, or a click plus an
    impatient refresh, would otherwise start two renders of identical
    audio against a single-worker service — the second of which makes the
    first return 502.
    """
    import os as _os
    api_key = _os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return

    # ON by default: the audio is built alongside the report, so it is
    # already there when the client opens their link. Two minutes of
    # waiting moves from the client, who is standing in front of it, to a
    # background thread nobody is watching.
    #
    # "In parallel" means alongside the report, NOT many renders at once.
    # The renderer is a single worker: firing thirteen at it would make
    # twelve of them 502. _RENDER_LOCK queues them, so a batch of thirteen
    # is thirteen renders in a row, not a stampede.
    #
    # Set APE_PODCAST_PREGENERATE=0 to go back to building on the click —
    # worth it if most clients never listen, since this spends a render on
    # every report whether or not anyone plays it.
    # The switch governs the HEAD START only. A client who clicked Listen
    # asked for this directly and must always get it, whatever the default
    # is set to.
    if not on_demand and _pregenerate_disabled(_os):
        return

    with _PODCAST_JOBS_LOCK:
        if _PODCAST_JOBS.get(rid):
            return                      # already being made
        _PODCAST_JOBS[rid] = __import__("time").time()

    import threading

    def _run():
        try:
            _render_podcast(rid, report, snap, api_key, minutes=minutes)
        except Exception as exc:                    # never fail the report
            print(f"[podcast] {rid}: job error {type(exc).__name__}: "
                  f"{str(exc)[:120]}", flush=True)
        finally:
            with _PODCAST_JOBS_LOCK:
                _PODCAST_JOBS.pop(rid, None)

    threading.Thread(target=_run, name=f"podcast-{rid}", daemon=True).start()


def _render_podcast(rid: str, report: Dict[str, Any], snap, api_key: str,
                    minutes: int = 1) -> None:
    """Write, check, render and STORE the podcast. Blocking."""
    import os as _os, json as _json
    from pathlib import Path as _Path
    import anthropic
    from .reporting import podcast as _pod

    client = anthropic.Anthropic(api_key=api_key)
    model = _os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

    # Patient by design. The renderer sleeps and recovers, so the remedy is
    # to keep asking rather than give up and leave a client with nothing.
    result = _pod.generate_for_report(client, model, report, snap,
                                      minutes=minutes, attempts=6)

    if result.get("audio_url"):
        mp3 = (_Path(__file__).resolve().parents[1] / "data" / "generated"
               / f"{rid}.mp3")
        if _pod.fetch_audio(result["audio_url"], mp3):
            result["remote_url"] = result["audio_url"]
            result["audio_url"] = f"/r/{rid}/podcast.mp3"
        _podcast_to_db(rid, result)

    path = (_Path(__file__).resolve().parents[1] / "data" / "generated"
            / f"{rid}.json")
    try:
        current = _json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        current = report
    current["podcast"] = result
    path.write_text(_json.dumps(current, indent=2), encoding="utf-8")

    print(f"[podcast] {rid}: "
          + (result.get("audio_url") or f"failed — {result.get('error')}"),
          flush=True)


@app.get("/r/{report_id}/podcast")
async def report_podcast_status(report_id: str, token: str = "",
                                request: Request = None):
    """Is the pre-generated audio ready yet?

    The viewer polls this instead of asking for a render, so the common
    case costs nothing and returns instantly.
    """
    _viewer_auth(report_id, token, request)

    cached = _podcast_from_disk(report_id)
    if cached:
        return {"status": "ready", **cached}

    # Older reports cached it in the generated JSON before the column
    # existed. Still honoured, so nothing already rendered is re-rendered.
    pod = (_report_json(report_id).get("podcast") or {})
    if pod.get("audio_url"):
        return {"status": "ready", "audio_url": pod["audio_url"],
                "script": pod.get("script", ""), "note": pod.get("note", "")}

    with _PODCAST_JOBS_LOCK:
        started = _PODCAST_JOBS.get(report_id)
    if started:
        return {"status": "working", "started_at": started}

    # A job that finished without audio. The client is told it did not work
    # and can try again — never why, because "HTTPStatusError 502 from a
    # TaskGroup" is our problem to read, not theirs.
    if pod.get("error"):
        return {"status": "none"}
    return {"status": "none"}


_VIDEO_JOBS: Dict[str, float] = {}

# ── MEDIA LIVES IN A FOLDER ─────────────────────────────────────────────
#
# data/generated/{report_id}.mp3 and .mp4, beside the report's own HTML and
# JSON. The file's existence IS the record — there is no separate row to
# agree with it, so there is no way for the two to disagree.
#
# The database columns are still written as a convenience for anything that
# wants to query media without touching the filesystem, but nothing READS
# them on the client path. A row saying "ready" while the file is missing
# would show a client a dead player, and that is precisely the failure a
# second source of truth invites.
#
# The script and the slide sections live in the report's own JSON, which is
# in the same folder. Clearing a report's media is deleting two files.

def _media_dir() -> Path:
    d = Path(__file__).resolve().parents[1] / "data" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _media_on_disk(report_id: str, ext: str) -> Optional[Path]:
    """The rendered file, if it is actually there."""
    p = _media_dir() / f"{report_id}.{ext}"
    return p if (p.is_file() and p.stat().st_size > 0) else None


def _video_from_disk(report_id: str) -> Optional[Dict[str, Any]]:
    """The stored presentation, or None. The FILE decides."""
    if _media_on_disk(report_id, "mp4") is None:
        return None
    try:
        pres = (_report_json(report_id).get("presentation") or {})
    except Exception:
        pres = {}
    sections = pres.get("sections") or []
    if not sections:
        # Same as the podcast script: a regenerated report rewrites the
        # JSON and takes the slide text with it, while the .mp4 remains.
        sections = (_video_from_db(report_id) or {}).get("sections") or []
    return {"video_url": f"/r/{report_id}/presentation.mp4",
            "sections": sections,
            "note": pres.get("note", "")}


def _podcast_from_disk(report_id: str) -> Optional[Dict[str, Any]]:
    """The stored podcast, or None. The FILE decides that it exists.

    The SCRIPT, though, comes from the report JSON first and the database
    second — because regenerating a report rewrites {rid}.json and drops
    the podcast entry, while the .mp3 beside it survives. The result was a
    working player with an empty "Read the script": five of six podcasts
    here had lost their text that way.

    These are not two sources of truth for one question. The file answers
    "is there audio"; the row answers "what does it say". The row is only
    consulted when the file that used to hold the text has been overwritten.
    """
    if _media_on_disk(report_id, "mp3") is None:
        return None
    try:
        pod = (_report_json(report_id).get("podcast") or {})
    except Exception:
        pod = {}
    script = pod.get("script") or ""
    if not script:
        stored = _podcast_from_db(report_id) or {}
        script = stored.get("script") or ""
    return {"audio_url": f"/r/{report_id}/podcast.mp3",
            "script": script,
            "note": pod.get("note", "")}


def _video_from_db(report_id: str) -> Optional[Dict[str, Any]]:
    from .db.session import init_db, session_scope
    from .db.models import Report
    init_db()
    try:
        with session_scope() as db:
            row = db.get(Report, report_id)
            if row is not None and getattr(row, "video_url", None):
                return {"video_url": row.video_url,
                        "sections": json.loads(row.video_sections or "[]"),
                        "note": ""}
    except Exception as exc:
        print(f"[video] cache read failed for {report_id}: "
              f"{type(exc).__name__}: {str(exc)[:100]}", flush=True)
    return None


def _video_to_db(report_id: str, result: Dict[str, Any]) -> None:
    from datetime import datetime as _dt
    from .db.session import init_db, session_scope
    from .db.models import Report
    init_db()
    try:
        with session_scope() as db:
            row = db.get(Report, report_id)
            if row is None:
                return
            row.video_url = result.get("video_url")
            row.video_sections = json.dumps(result.get("sections") or [],
                                            ensure_ascii=False)
            row.video_at = _dt.utcnow()
    except Exception as exc:
        print(f"[video] cache write failed for {report_id}: "
              f"{type(exc).__name__}: {str(exc)[:100]}", flush=True)


def _start_video_job(rid: str, report: Dict[str, Any], snap,
                     on_demand: bool = False) -> None:
    """Render this report's presentation in the background.

    Same shape as the podcast job, and started at the same two moments —
    generation and send — so the client finds it already made.

    Kept as a SEPARATE job rather than one job producing both. Audio takes
    two minutes and video four; bundling them would make every client wait
    the longer of the two for whichever they wanted first, and one
    failing would take the other down with it.
    """
    import os as _os
    api_key = _os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return
    if not on_demand and _pregenerate_disabled(_os):
        return

    with _PODCAST_JOBS_LOCK:
        if _VIDEO_JOBS.get(rid):
            return
        _VIDEO_JOBS[rid] = __import__("time").time()

    import threading

    def _run():
        try:
            _render_video(rid, report, snap, api_key)
        except Exception as exc:
            print(f"[video] {rid}: job error {type(exc).__name__}: "
                  f"{str(exc)[:120]}", flush=True)
        finally:
            with _PODCAST_JOBS_LOCK:
                _VIDEO_JOBS.pop(rid, None)

    threading.Thread(target=_run, name=f"video-{rid}", daemon=True).start()


def _render_video(rid: str, report: Dict[str, Any], snap, api_key: str) -> None:
    """Write, check, render and STORE the presentation. Blocking."""
    import os as _os, json as _json
    from pathlib import Path as _Path
    import anthropic
    from .reporting import presentation as _pres
    from .reporting import podcast as _pod

    client = anthropic.Anthropic(api_key=api_key)
    model = _os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
    result = _pres.generate_for_report(client, model, report, snap)

    if result.get("video_url"):
        mp4 = (_Path(__file__).resolve().parents[1] / "data" / "generated"
               / f"{rid}.mp4")
        # The renderer's files expire fast — two rendered less than an hour
        # earlier were already 404 — so the copy happens before the link is
        # recorded, not after.
        if _pod.fetch_audio(result["video_url"], mp4):
            result["remote_url"] = result["video_url"]
            result["video_url"] = f"/r/{rid}/presentation.mp4"
        _video_to_db(rid, result)

    path = (_Path(__file__).resolve().parents[1] / "data" / "generated"
            / f"{rid}.json")
    try:
        current = _json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        current = report
    current["presentation"] = result
    path.write_text(_json.dumps(current, indent=2), encoding="utf-8")

    print(f"[video] {rid}: "
          + (result.get("video_url") or f"failed — {result.get('error')}"),
          flush=True)


def _start_media_job(rid: str, report: Dict[str, Any], snap) -> None:
    """Build the video, then the audio. One thread, strictly in order.

    Fired when the advisor SENDS, which is the moment the report becomes
    real and the client can open the link at any second.

    SEQUENTIAL, AND THAT IS THE POINT. The renderer is one CPU and 512MB.
    Two jobs racing for it — even correctly serialised by a lock — means a
    thread sitting on a held lock while the other runs, and any overlap at
    the boundaries is what pushes the box over its memory limit. Doing the
    video first and the audio only once it has finished keeps exactly one
    piece of work in flight, end to end.

    Video first because it is the longer of the two: if only one is going
    to be ready when the client arrives, it should be the one that took
    longer to make.
    """
    import os as _os
    api_key = _os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return
    if _pregenerate_disabled(_os):
        return

    with _PODCAST_JOBS_LOCK:
        if _VIDEO_JOBS.get(rid) or _PODCAST_JOBS.get(rid):
            return                       # already being made
        _now = __import__("time").time()
        _VIDEO_JOBS[rid] = _now
        _PODCAST_JOBS[rid] = _now

    import threading

    def _run():
        # AUDIO FIRST, AND THE ORDER IS THE WHOLE POINT.
        #
        # Measured against the live renderer, in one session: text_to_speech
        # succeeded in 27.6s, generate_video_from_sections then failed after
        # 21.3s, and the SAME text_to_speech call failed 0.4s later. A
        # sub-second 502 is a dead worker, not a slow one. The video tool
        # takes the renderer down with it - it survives long enough to
        # synthesise narration, then dies where ffmpeg is spawned, because a
        # 512MB box already holding piper cannot also hold a full narration
        # waveform, its concatenated copy and an libx264 subprocess.
        #
        # With video running first, that crash landed on the podcast too:
        # the audio step then met an instance that was restarting and got
        # nothing, which is why NEITHER medium appeared. Podcast first means
        # the cheap, reliable artefact is already on disk before the
        # expensive one is allowed to risk the renderer.
        #
        # This is a mitigation, not the fix. The fix belongs in the renderer
        # (Podcast_MCP): free the waveform before spawning ffmpeg, or give
        # the service enough memory to hold both.
        try:
            if not _podcast_from_disk(rid):
                _render_podcast(rid, report, snap, api_key)
        except Exception as exc:
            print(f"[media] {rid}: audio step failed "
                  f"{type(exc).__name__}: {str(exc)[:100]}", flush=True)
        finally:
            with _PODCAST_JOBS_LOCK:
                _PODCAST_JOBS.pop(rid, None)

        try:
            if not _video_from_disk(rid):
                _render_video(rid, report, snap, api_key)
        except Exception as exc:
            print(f"[media] {rid}: video step failed "
                  f"{type(exc).__name__}: {str(exc)[:100]}", flush=True)
        finally:
            with _PODCAST_JOBS_LOCK:
                _VIDEO_JOBS.pop(rid, None)

    threading.Thread(target=_run, name=f"media-{rid}", daemon=True).start()


@app.get("/r/{report_id}/video")
async def report_video_status(report_id: str, token: str = "",
                              request: Request = None):
    """Is the presentation ready yet?"""
    _viewer_auth(report_id, token, request)
    cached = _video_from_disk(report_id)
    if cached:
        return {"status": "ready", **cached}
    legacy = (_report_json(report_id).get("presentation") or {})
    if legacy.get("video_url"):
        return {"status": "ready", "video_url": legacy["video_url"],
                "sections": legacy.get("sections") or [],
                "note": legacy.get("note", "")}
    with _PODCAST_JOBS_LOCK:
        started = _VIDEO_JOBS.get(report_id)
    if started:
        return {"status": "working", "started_at": started}
    return {"status": "none"}


@app.post("/r/{report_id}/video")
async def report_video(report_id: str, request: Request):
    """Ask for the presentation. Enqueues; never waits, never errors at the
    client. Same contract as /podcast."""
    body = await request.json()
    _viewer_auth(report_id, str(body.get("token", "")), request)
    report = _report_json(report_id)

    stored = _video_from_disk(report_id)
    if stored:
        return {**stored, "cached": True}

    import os as _os
    if not _os.getenv("ANTHROPIC_API_KEY", ""):
        raise HTTPException(503, "presentation needs ANTHROPIC_API_KEY")

    from .db.session import init_db, session_scope
    from .db.repository import load_snapshot as _sql_snapshot
    init_db()
    with session_scope() as db:
        snap = _sql_snapshot(db, report["client_id"], report.get("period"))
    if snap is None:
        raise HTTPException(404, "no snapshot for this report")

    _start_video_job(report_id, report, snap, on_demand=True)
    return {"status": "working"}


@app.get("/r/{report_id}/presentation.mp4")
def report_video_file(report_id: str, token: str = "", request: Request = None):
    """Our own copy of the video, behind the same two gates as the report."""
    _viewer_auth(report_id, token, request)
    path = (Path(__file__).resolve().parents[1] / "data" / "generated"
            / f"{report_id}.mp4")
    if not path.is_file():
        raise HTTPException(404, "no presentation for this report")
    report = _report_json(report_id)
    name = f"{report.get('client_name', 'report')} {report.get('period', '')}".strip()
    safe = "".join(ch if (ch.isalnum() or ch in " -_") else "" for ch in name)
    from fastapi.responses import FileResponse
    return FileResponse(
        path, media_type="video/mp4",
        headers={"Content-Disposition":
                 f'inline; filename="{safe or report_id}.mp4"'})


@app.post("/r/{report_id}/transcribe")
async def report_transcribe(report_id: str, request: Request,
                            token: str = ""):
    """Turn a recorded question into text, in whatever language it was asked.

    Behind the same two gates as everything else on the client surface: a
    microphone endpoint that anyone could POST to is a free transcription
    service running on our CPU.

    The audio is decoded and transcribed in this process and then dropped.
    It is never written to disk and never forwarded, which is what lets the
    page say the recording does not leave the building.
    """
    _viewer_auth(report_id, token, request)

    audio = await request.body()
    if not audio:
        raise HTTPException(400, "no audio received")

    # The report's language is a prior, not an instruction: it is consulted
    # only when detection is unsure. See transcribe.py.
    try:
        report = _report_json(report_id)
        fallback = report.get("language") or "en"
    except Exception:
        fallback = "en"

    from .reporting.transcribe import transcribe, TranscriptionError
    try:
        # Whisper is CPU-bound and would block the event loop for the whole
        # decode, stalling every other client on this worker.
        text, language, confidence = await asyncio.to_thread(
            transcribe, audio, fallback)
    except TranscriptionError as exc:
        raise HTTPException(422, str(exc))

    return {"text": text, "language": language,
            "confidence": round(confidence, 3)}


@app.post("/r/{report_id}/speak")
async def report_speak(report_id: str, request: Request, token: str = ""):
    """Read a chat answer aloud, in the language it was written in.

    Piper, locally, rather than the browser's own voice: same engine as the
    client's podcast, so they hear one voice across the whole report instead
    of a warm narrator in one place and a robot in another. It also means
    the answer - figures included - is never handed to a speech vendor.

    Behind the same two gates as the rest of the client surface.
    """
    _viewer_auth(report_id, token, request)

    body = await request.json()
    text = (body or {}).get("text") or ""
    language = (body or {}).get("language") or ""
    if not language:
        try:
            language = _report_json(report_id).get("language") or "en"
        except Exception:
            language = "en"

    from .reporting.speak import synthesize, SpeechError
    try:
        # Synthesis is CPU-bound; on the event loop it would stall every
        # other client on this worker for its duration.
        audio, voice = await asyncio.to_thread(synthesize, text, language)
    except SpeechError as exc:
        raise HTTPException(422, str(exc))

    from fastapi.responses import Response
    return Response(audio, media_type="audio/wav",
                    headers={"X-Voice": voice, "Cache-Control": "no-store"})


@app.get("/r/{report_id}/podcast.mp3")
def report_podcast_audio(report_id: str, token: str = "",
                         request: Request = None):
    """Serve our own copy of the audio, behind the same two gates.

    The client's portfolio read aloud is exactly as private as the report
    it came from, so it goes through _viewer_auth like everything else. The
    third-party URL is never handed to the browser.

    A filename is set deliberately: the renderer names files by hash, and
    "marcus-whitfield-2026q2-2d895a5c.mp3" is not what anyone wants sitting
    in their downloads folder.
    """
    _viewer_auth(report_id, token, request)
    path = (Path(__file__).resolve().parents[1] / "data" / "generated"
            / f"{report_id}.mp3")
    if not path.is_file():
        raise HTTPException(404, "no audio for this report")

    report = _report_json(report_id)
    name = f"{report.get('client_name', 'report')} {report.get('period', '')}".strip()
    safe = "".join(ch if (ch.isalnum() or ch in " -_") else "" for ch in name)
    from fastapi.responses import FileResponse
    return FileResponse(
        path, media_type="audio/mpeg",
        headers={"Content-Disposition":
                 f'inline; filename="{safe or report_id}.mp3"'})


def _podcast_from_db(report_id: str) -> Optional[Dict[str, Any]]:
    """The stored podcast for this report, or None if nobody has made one."""
    from .db.session import init_db, session_scope
    from .db.models import Report
    init_db()
    try:
        with session_scope() as db:
            row = db.get(Report, report_id)
            if row is not None and getattr(row, "podcast_url", None):
                return {"audio_url": row.podcast_url,
                        "script": row.podcast_script or "",
                        "note": ""}
    except Exception as exc:                 # a cache miss, never a failure
        print(f"[podcast] cache read failed for {report_id}: "
              f"{type(exc).__name__}: {str(exc)[:100]}", flush=True)
    return None


def _podcast_to_db(report_id: str, result: Dict[str, Any]) -> None:
    """Store the rendered podcast against the report row."""
    from datetime import datetime as _dt
    from .db.session import init_db, session_scope
    from .db.models import Report
    init_db()
    try:
        with session_scope() as db:
            row = db.get(Report, report_id)
            if row is None:
                return
            row.podcast_url = result.get("audio_url")
            row.podcast_script = result.get("script", "")
            row.podcast_at = _dt.utcnow()
    except Exception as exc:                 # caching is not the product
        print(f"[podcast] cache write failed for {report_id}: "
              f"{type(exc).__name__}: {str(exc)[:100]}", flush=True)


@app.post("/r/{report_id}/podcast")
async def report_podcast(report_id: str, request: Request):
    """Turn this report into a two-voice podcast the client can play.

    Same two gates as every other client surface. The audio is derived from
    the client's own figures, so it is exactly as private as the report.

    The script is written by the model, checked by the grounding gate with
    its DIGITS INTACT, and only then converted to spoken words in code. That
    order is not incidental — see ape/reporting/podcast.py. A script that
    fails the gate is not narrated; it is refused, because nobody proofreads
    audio.
    """
    body = await request.json()
    _viewer_auth(report_id, str(body.get("token", "")), request)

    report = _report_json(report_id)

    # Rendered once, ever. A second click, a second device, a client coming
    # back next week — all of it is a row lookup, not another two minutes
    # and another render nobody should pay for twice.
    stored = _podcast_from_disk(report_id)
    if stored:
        return {**stored, "spoken": "", "grounding": "cached", "cached": True}
    legacy = report.get("podcast") or {}
    if legacy.get("audio_url"):
        return {"audio_url": legacy["audio_url"],
                "script": legacy.get("script", ""),
                "spoken": legacy.get("spoken", ""),
                "grounding": legacy.get("grounding", "cached"),
                "note": legacy.get("note", ""), "cached": True}

    import os as _os
    api_key = _os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(503, "podcast needs ANTHROPIC_API_KEY")

    from .db.session import init_db, session_scope
    from .db.repository import load_snapshot as _sql_snapshot
    from .reporting import podcast as _pod
    init_db()

    with session_scope() as db:
        snap = _sql_snapshot(db, report["client_id"], report.get("period"))
    if snap is None:
        raise HTTPException(404, "no snapshot for this report")

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    model = _os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

    minutes = max(1, min(5, int(body.get("minutes") or 2)))

    # The click ENQUEUES. It does not wait.
    #
    # The renderer is a free single-worker instance that returns 502
    # whenever it is busy or simply out of sorts, and a client should never
    # be shown the consequences of that — least of all an HTTP status and a
    # TaskGroup traceback, which is what a synchronous call surfaced.
    #
    # So the work moves to a background job that can retry patiently, and
    # the page just asks "ready yet?". The worst a client sees is that
    # their podcast is still being prepared.
    _start_podcast_job(report_id, report, snap, minutes=minutes,
                       on_demand=True)
    return {"status": "working"}


@app.post("/r/{report_id}/chat")
async def report_chat(report_id: str, request: Request):
    """The client talks to the report. Token-gated like the page itself;
    the highlighted block localises the answer to its own facts."""
    body = await request.json()
    _viewer_auth(report_id, str(body.get("token", "")), request)

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
    from .db.models import Message
    init_db()

    with session_scope() as db:
        try:
            snap = _sql_snapshot(db, report["client_id"], report.get("period"))
            # The REPORT decides the language, not the client row. They
            # are asking about THIS document: a client whose standing
            # preference later changed must still get answers in the
            # language the report in front of them is written in, or the
            # reply arrives in a different language from the page.
            snap.language = report.get("language") or getattr(snap, "language", "") or ""
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

        # Same door as the streaming path: a request to MAKE a medium is
        # not a question about the report, and must not be answered as one.
        from .reporting.d2 import media_request as _media_request
        _want = _media_request(question)
        if _want and not block_id and not body.get("selected_text"):
            _reply, _widget = _media_chat_turn(report_id, report, snap, _want)
            return {"answer": _reply, "intent": "media_request",
                    "strategy": "", "arms": [], "author": "media_request",
                    "sources": [], "followups": [], "widget": _widget or None,
                    "conversation_id": body.get("conversation_id") or ""}

        result = answer_question(
            db, snap, report_id, question, block,
            selected_text=str(body.get("selected_text", "")),
            conversation_id=body.get("conversation_id"),
            report_json=report)

        # Chips for the NEXT turn, drawn from the blocks this report actually
        # contains and what was just asked — so they stay relevant to this
        # document instead of offering the same four questions forever.
        from .reporting.d2 import suggest_followups
        asked = list(db.scalars(_select(Message.content).where(
            Message.report_id == report_id, Message.role == "client")))
        result["followups"] = suggest_followups(
            report, result.get("intent", ""), asked, snap=snap,
            block_type=(block or {}).get("block_type", ""),
            question=question, answer=result.get("answer", ""),
            sources=result.get("sources") or [],
            locale=getattr(snap, "language", "") or "")

        # The question itself is a signal: engagement on the report, and its
        # wording may carry format preferences for the profile.
        _rt = str(report.get("report_type", "") or "")
        record_event(db, report["client_id"], "question_asked",
                     report_id=report_id, block_id=block_id or "",
                     metadata={"question": question,
                               "intent": result["intent"]},
                     report_type=_rt)

        # A client asking to SEE something is the most direct statement of
        # presentation preference this system ever receives — far stronger
        # than inferring it from where they lingered. Recorded with what
        # they were asking ABOUT, so the composer learns the pairing
        # ("fees, as a bar chart") rather than a free-floating taste.
        w = result.get("widget")
        if w:
            record_event(db, report["client_id"], "visual_requested",
                         report_id=report_id, block_id=block_id or "",
                         metadata={"binding": w["binding"], "kind": w["kind"],
                                   "intent": result["intent"], "drawn": True},
                         report_type=_rt)
        elif result.get("widget_declined"):
            # A visual we could not fill is worth recording too, and for a
            # different reason: it is not a presentation preference to
            # learn from but a gap in what this client's data can support.
            # Left unrecorded, the only trace is a client being told no.
            record_event(db, report["client_id"], "visual_requested",
                         report_id=report_id, block_id=block_id or "",
                         metadata={"binding": "", "kind": "",
                                   "intent": result["intent"], "drawn": False,
                                   "reason": result["widget_declined"]},
                         report_type=_rt)

        # Every question is fresh evidence about how this client reads, so
        # the brief the composer sees next time is rebuilt now rather than
        # on a schedule — the whole point is that the next report reflects
        # what just happened.
        # Anything the client said about HOW they want to be shown things,
        # in their own words, kept against this report type. Best effort:
        # a failed extraction costs one signal, and must never cost the
        # client their answer.
        try:
            from .reporting.stated_prefs import extract, merge
            from .reporting.skill import _skill_row
            found = extract(question, result.get("answer", ""))
            if found:
                for scope in ("", _rt) if _rt else ("",):
                    row = _skill_row(db, report["client_id"], scope)
                    row.stated_prefs = merge(row.stated_prefs, found)
        except Exception:
            pass

        from .reporting.skill import refresh_skill
        refresh_skill(db, report["client_id"], _rt)
    return result



def _media_chat_turn(report_id: str, report: Dict[str, Any], snap,
                     kind: str) -> Tuple[str, Dict[str, Any]]:
    """Start the render a client asked for in chat, and say so.

    The chat and the buttons are two doors into the same job. This goes
    through _start_*_job exactly as a button press does - same lock, same
    de-duplication - so asking twice, or asking in chat while a button
    press is already running, cannot start a second render.

    on_demand=True because the client asked for this one directly. The
    pregenerate switch governs the head start nobody requested; it must
    never suppress a render somebody typed a sentence to get.

    Returns (reply, widget). THE WIDGET IS THE POINT: something asked for
    in the conversation should arrive in the conversation. Sending a client
    to hunt for a button when they asked here is the kind of small
    discourtesy that makes a feature feel unfinished.
    """
    from .reporting.labels import t as _t
    lang = (report.get("language") or getattr(snap, "language", "") or "en")

    is_pod = kind == "podcast"
    title = _t("Your podcast" if is_pod else "Your presentation", lang) or (
        "Your podcast" if is_pod else "Your presentation")
    widget = {
        "media": kind,
        "title": title,
        "url": None,
        "status": f"/r/{report_id}/{'podcast' if is_pod else 'video'}",
        "pending": _t("Preparing it now…", lang) or "Preparing it now…",
        "failed": _t("That did not work this time. Please try again.", lang)
                  or "That did not work this time. Please try again.",
    }

    ready = (_podcast_from_disk(report_id) if is_pod
             else _video_from_disk(report_id))
    if ready:
        widget["url"] = (f"/r/{report_id}/podcast.mp3" if is_pod
                         else f"/r/{report_id}/presentation.mp4")
        msg = ("Here is your podcast." if is_pod
               else "Here is your presentation.")
        return (_t(msg, lang) or msg), widget

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        msg = "I cannot make that right now. Please try the button above."
        return (_t(msg, lang) or msg), {}

    if is_pod:
        _start_podcast_job(report_id, report, snap, on_demand=True)
        msg = ("I am making your podcast now — it takes a minute or so, and "
               "it will play here as soon as it is ready.")
    else:
        _start_video_job(report_id, report, snap, on_demand=True)
        msg = ("I am making your presentation now — it takes a minute or so, "
               "and it will play here as soon as it is ready.")
    return (_t(msg, lang) or msg), widget


@app.post("/r/{report_id}/chat/stream")
async def report_chat_stream(report_id: str, request: Request):
    """The same turn as /chat, delivered as it forms.

    Server-Sent Events over POST rather than EventSource, because the
    question and the token belong in a body, not a query string — a token
    in a URL lands in access logs and browser history.

    Only text that has already passed the grounding check is sent. See
    d2_stream for why that is not negotiable.
    """
    body = await request.json()
    _viewer_auth(report_id, str(body.get("token", "")), request)

    report = _report_json(report_id)
    question = str(body.get("question", "")).strip()
    if not question:
        raise HTTPException(400, "empty question")
    block_id = body.get("block_id") or None

    def events():
        from .db.session import init_db, session_scope
        from .db.models import ReportBlock
        from .db.repository import load_snapshot as _sql_snapshot
        from .reporting.d2 import suggest_followups
        from .reporting.d2_stream import stream_answer
        from .reporting.rewards import record_event
        from .reporting.skill import refresh_skill
        from sqlalchemy import select as _select
        from .db.models import Message
        init_db()

        with session_scope() as db:
            try:
                snap = _sql_snapshot(db, report["client_id"],
                                     report.get("period"))
                # Same rule as the buffered path: the document in front of
                # them decides the language, not their stored preference.
                snap.language = (report.get("language")
                                 or getattr(snap, "language", "") or "")
            except LookupError:
                yield _sse("error", {"detail": "client facts not on file"})
                return

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
                    block = next((b for b in report["blocks"]
                                  if b["block_id"] == block_id), None)

            # "make me a podcast" is a request, not a question. It must
            # not reach the grounded writer, which would answer it with
            # prose about the report and never start anything.
            from .reporting.d2 import media_request as _media_request
            _want = _media_request(question)
            if _want and not block_id and not body.get("selected_text"):
                _reply, _widget = _media_chat_turn(report_id, report, snap,
                                                   _want)
                yield _sse("delta", {"text": _reply})
                yield _sse("final", {
                    "answer": _reply,
                    "intent": "media_request",
                    # Not a bandit answer, so it reports no strategy and no
                    # arms - crediting one for this would teach the learner
                    # from a turn it did not choose.
                    "strategy": "", "arms": [], "author": "media_request",
                    "sources": [], "followups": [], "widget": _widget or None,
                    "conversation_id": body.get("conversation_id") or "",
                })
                return

            result = None
            for kind, payload in stream_answer(
                    db, snap, report_id, question, block,
                    selected_text=str(body.get("selected_text", "")),
                    conversation_id=body.get("conversation_id"),
                    report_json=report):
                if kind == "final":
                    result = payload
                else:
                    yield _sse(kind, {"text": payload})

            if result is None:
                yield _sse("error", {"detail": "no answer produced"})
                return

            # Follow-up chips cost a model call and produce buttons. A
            # voice turn has no buttons, so the call is pure latency and
            # spend on the path where latency is felt most.
            if body.get("voice"):
                result["followups"] = []
            else:
                asked = list(db.scalars(_select(Message.content).where(
                    Message.report_id == report_id, Message.role == "client")))
                result["followups"] = suggest_followups(
                    report, result.get("intent", ""), asked, snap=snap,
                    block_type=(block or {}).get("block_type", ""),
                    question=question, answer=result.get("answer", ""),
                    sources=result.get("sources") or [],
                    locale=getattr(snap, "language", "") or "")

            _rt = str(report.get("report_type", "") or "")
            record_event(db, report["client_id"], "question_asked",
                         report_id=report_id, block_id=block_id or "",
                         metadata={"question": question,
                                   "intent": result["intent"]},
                         report_type=_rt)
            w = result.get("widget")
            if w:
                record_event(db, report["client_id"], "visual_requested",
                             report_id=report_id, block_id=block_id or "",
                             metadata={"binding": w["binding"],
                                       "kind": w["kind"],
                                       "intent": result["intent"],
                                       "drawn": True}, report_type=_rt)
            try:
                from .reporting.stated_prefs import extract, merge
                from .reporting.skill import _skill_row
                found = extract(question, result.get("answer", ""))
                if found:
                    for scope in ("", _rt) if _rt else ("",):
                        row = _skill_row(db, report["client_id"], scope)
                        row.stated_prefs = merge(row.stated_prefs, found)
            except Exception:
                pass
            refresh_skill(db, report["client_id"], _rt)

            yield _sse("final", result)

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/r/{report_id}/history")
def report_history(request: Request, report_id: str, token: str = "", limit: int = 40):
    """This client's earlier conversation about THIS report.

    Stored all along — every turn writes a Message row keyed by client_id
    — but the viewer never asked for it, so each visit began blank and a
    client who came back had lost the thread they built.

    Deliberately scoped to one report, not to everything the client has
    ever asked. The token authorises ONE report; returning conversations
    from others through it would widen what that token grants, which is
    the sort of quiet scope creep the cross-client check exists to stop.
    """
    _viewer_auth(report_id, token, request)
    from .db.session import init_db, session_scope
    from .db.models import Message
    from sqlalchemy import select as _s
    init_db()
    out = []
    with session_scope() as db:
        rows = list(db.scalars(
            _s(Message).where(Message.report_id == report_id)
            .order_by(Message.created_at.desc())
            .limit(max(2, min(limit, 200)))))
        for m in reversed(rows):
            out.append({"role": m.role, "content": m.content,
                        "message_id": m.message_id,
                        "conversation_id": m.conversation_id,
                        "block_ids": m.block_ids or [],
                        # The evidence and the chart, so a restored answer
                        # IS the answer. Follow-up chips are not stored:
                        # they suggest what to ask NEXT, and next has
                        # already happened by the time anyone re-reads it.
                        "sources": m.sources or [],
                        "widget": m.widget or None,
                        "at": m.created_at.isoformat(timespec="seconds")})
    return {"messages": out,
            "conversation_id": out[-1]["conversation_id"] if out else None}


@app.post("/r/{report_id}/events")
async def report_events(report_id: str, request: Request):
    """Engagement signals from the viewer. Every event is stored raw, then
    routed: D2 reward, report engagement, preference profile."""
    body = await request.json()
    _viewer_auth(report_id, str(body.get("token", "")), request)
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
            metadata=body.get("metadata") or {},
            report_type=str(report.get("report_type", "") or ""))
    return out


def _sse(event: str, data: Any) -> str:
    """One Server-Sent Event frame.

    json.dumps also protects the wire format: a newline inside the answer
    would otherwise terminate the frame early and truncate the message.
    """
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


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
