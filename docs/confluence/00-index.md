# APE Modulor — Engineering Space

> **Adaptive Prompt Engine** · MongoDB · FastAPI · React/Vite · Anthropic Claude Haiku 4.5

Welcome to the APE Modulor engineering space. APE learns the best **response format** per user from real interactions: a UCB multi-armed bandit picks a strategy (comparison table, decision card, analogy, numbered steps, …) and updates from explicit feedback (👍 👎 copy regenerate …).

This space documents both **how the system works** and **how to operate it**.

---

## Space contents

| # | Page | What's inside |
|---|---|---|
| 01 | [Architecture overview](./01-architecture-overview.md) | 8-collection schema · data flow · privacy boundary |
| 02 | [Runtime paths](./02-runtime-paths.md) | Path A (selection + render) · Path B (reward attribution) |
| 03 | [Admin config](./03-admin-config.md) | Intents · strategies · instructions · policies · offers · signals · reward scale · audit log |
| 04 | [Analytics layer](./04-analytics-layer.md) | Platform overview · trends · active customers · user profile · cognitive facets |
| 05 | [Cognitive facets (the 12)](./05-cognitive-facets.md) | Per-user behavioral profile with formulas |
| 06 | [Outreach recommendation](./06-outreach-recommendation.md) | Scoring formula · per-action weights · eligibility gates |
| 07 | [Operations](./07-operations.md) | Recompute (manual + scheduled) · seeding · deploy |
| 08 | [Privacy & compliance](./08-privacy-and-compliance.md) | What's stored where · gates · audit trail |
| 09 | [API reference](./09-api-reference.md) | Every HTTP endpoint with payload shape |
| 10 | [Architecture comparison](./10-architecture-comparison.md) | Reference design review · side-by-side vs ours · equivalent diagram · DB tables · query flow · suggested-vs-rendered |

---

## The 30-second pitch

```
User asks "Compare Roth IRA vs Traditional IRA"
        │
        ▼
   classifier  →  intent=Comparison, topic=roth_vs_traditional_ira
        │
        ▼
   policy lookup  →  [standard_llm, comparison_table, pros_cons_table, bullet_contrast]
        │
        ▼
   bandit (per-user UCB)  →  picks comparison_table  (cached_ucb = 1.522)
        │
        ▼
   synthesizer LLM (with instruction text)  →  renders the answer as a markdown table
        │
        ▼
   write turn_record with reward_status=PENDING
        │
        ▼
   user clicks 👍  →  POST /feedback with response_id
        │
        ▼
   Path B  →  signal=thumbs_up → reward=+1.0 → update bandit row → recache UCB
        │
        ▼
   Next time this user asks a similar comparison → table wins faster.
```

---

## Three keys, three jobs

| Key | Job | Used by |
|---|---|---|
| `user_id_hash` | Personalization | Bandit cells, analytics scope |
| `response_id` | Reward attribution | Path B targets ONE exact response |
| `session_id` | Conversation grouping (UI) | Chat resume only — **never** a learning key |

---

## Quick links

- **Repo root**: `/ape_modulor_production`
- **Backend**: `ape/` — FastAPI app at `ape.api:app`
- **Frontend**: `frontend/` — Vite + React, served at `:5173` in dev, `:7860` (FastAPI static) in prod
- **Schema docstring** (canonical): `ape/store/mongo_schema.py`
- **Seed scripts**: `scripts/seed_demo_users.py`, `scripts/seed_demo_facets.py`
- **Scheduled recompute**: `scripts/cron_recompute.py`

---

## Local dev quick-start

```bash
# Backend (port 7860)
python -m uvicorn ape.api:app --host 127.0.0.1 --port 7860

# Frontend (port 5173, proxies /turn /feedback /config /admin/* /analytics/* to :7860)
cd frontend && npm run dev

# Seed demo data
python scripts/seed_demo_users.py
python scripts/seed_demo_facets.py
```

---

*Last revised: 2026-05-17*
