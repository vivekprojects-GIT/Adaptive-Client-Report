# APE Modulor - Engineering Space

> Adaptive Prompt Engine - MongoDB - FastAPI - React/Vite - Anthropic Claude

APE learns the best response format per user. A UCB bandit picks a strategy
such as `comparison_table`, `decision_card`, or `numbered_steps`; the runtime
then records objective and user-facing signals, resolves them once, and updates
the exact bandit arm that produced the response.

The important current behavior: feedback is buffered. A `thumbs_up` alone is
tracked for analytics and satisfaction, but it is not a direct bandit reward.
Bandit learning comes from format-relevant signals such as
`format_compliance_pass`, `format_change_request`, `copy_save`, composite
patterns, and other configured format evidence.

---

## Space Contents

| # | Page | What is inside |
|---|---|---|
| 01 | [Architecture overview](./01-architecture-overview.md) | Collections, keys, privacy boundary, auth boundary |
| 02 | [Runtime paths](./02-runtime-paths.md) | `/turn`, `/turn/stream`, `/feedback`, pending signal finalization |
| 03 | [Admin config](./03-admin-config.md) | Intents, strategies, instructions, policies, signals, reward scale, audit log |
| 04 | [Analytics layer](./04-analytics-layer.md) | Dashboard scope, derived collections, recompute, protected endpoints |
| 05 | [Cognitive facets](./05-cognitive-facets.md) | The 12 behavioral profile facets |
| 06 | [Outreach recommendation](./06-outreach-recommendation.md) | Interest scoring and outreach eligibility gates |
| 07 | [Operations](./07-operations.md) | Local run, secrets, tests, recompute, deploy, troubleshooting |
| 08 | [Privacy and compliance](./08-privacy-and-compliance.md) | Raw text boundary, access control, outreach gates |
| 09 | [API reference](./09-api-reference.md) | Endpoint payloads, auth, streaming events, feedback statuses |
| 10 | [Architecture comparison](./10-architecture-comparison.md) | Reference design review and how this implementation maps to it |
| 11 | [Database design](./11-database-design.md) | MongoDB collections, keys, indexes, retention, ownership rules |

---

## The Current Learning Loop

```text
User sends a message
        |
        v
Server appends the user message to ape_messages
        |
        v
Classifier returns intent, topic, and any next-turn reaction signal
        |
        v
Previous pending response is finalized, if one exists:
  - append LLM signal if present
  - append session_continue if the user came back quickly
  - resolve composite/atomic signal label
  - choose the strongest format-relevant reward from all buffered signals
  - mark the turn APPLIED and update the bandit cell if reward exists
        |
        v
Policy and instruction lookup choose candidate strategies
        |
        v
Per-user UCB bandit picks the highest cached_ucb arm
        |
        v
Synthesizer renders the answer
        |
        v
Runtime records a PENDING turn with pending_signals:
  - format_compliance_pass if rendered format matched
  - format_compliance_fail if it did not
        |
        v
User feedback may queue more signals or finalize immediately
```

`/turn` and `/turn/stream` now share the same learning semantics. Streaming only
changes how tokens are delivered to the browser; it does not bypass bandit
attribution or reward finalization.

---

## Three Keys, Three Jobs

| Key | Job | Used by |
|---|---|---|
| `user_id_hash` | Personalization and ownership | Bandit cells, analytics scope, transcript filters |
| `response_id` | Exact reward attribution | `/feedback`, `ape_turn_record`, assistant message join |
| `session_id` | Conversation grouping | Chat resume and UI history only |

Do not use `session_id` as a learning key. Users learn across sessions through
`user_id_hash`.

---

## Security Defaults

Sensitive operational APIs require a shared admin token:

```text
APE_ADMIN_TOKEN=<long random secret>
X-APE-Admin-Token: <same secret>
```

The protected surfaces are `/config*`, `/admin/*`, and `/analytics/*`. The SPA
routes `/admin` and `/analytics` still load normally, then the UI prompts for
the token and stores it in browser local storage.

Session transcript reads also require `user_id`; the server filters by
`session_id + user_id_hash` so a session id alone is not enough to read raw
messages.

---

## Quick Links

- Repo root: `ape_modulor_production`
- Backend: `ape/` with FastAPI app `ape.api:app`
- Frontend: `frontend/` with Vite + React
- Canonical schema notes: `ape/store/mongo_schema.py`
- Runtime store implementation: `ape/store/mongo_store.py`
- Signal catalog: `ape/signals/routing.py`
- Reward scale: `ape/signals/reward_scale.py`
- Seed scripts: `scripts/seed_demo_users.py`, `scripts/seed_demo_facets.py`
- Analytics cron: `scripts/cron_recompute.py`

---

## Local Dev Quick Start

```bash
cp .env.example .env
# Edit .env:
#   ANTHROPIC_API_KEY=...
#   APE_MONGO_URI=...
#   APE_ADMIN_TOKEN=<long random secret>

pip install -r requirements.txt

# Backend on 127.0.0.1:7860
python -m uvicorn ape.api:app --host 127.0.0.1 --port 7860

# Frontend on 127.0.0.1:5173
cd frontend
npm install
npm run dev
```

Useful verification commands:

```bash
python -m pytest -q
python tests/test_mongo.py
python -m compileall -q ape tests scripts
cd frontend && npm run build
```

---

*Last revised: 2026-05-20*
