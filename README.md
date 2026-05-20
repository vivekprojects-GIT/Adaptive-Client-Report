---
title: APE Modulor
emoji: 🦧
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
pinned: false
short_description: Per-user UCB bandit picks the best response format
---

<!--
  ↑ The YAML block above is the Hugging Face Spaces manifest. Required keys
    for a Docker Space:
      sdk: docker          tells HF to build from the Dockerfile in this repo
      app_port: 7860       must match the port FastAPI listens on (see Dockerfile)
    Set these secrets in Space Settings → Variables and Secrets:
      ANTHROPIC_API_KEY    sk-ant-...           (required)
      APE_MONGO_URI        mongodb+srv://...    (required)
      APE_ADMIN_TOKEN      long random secret   (required for admin/config/analytics APIs)
      ANTHROPIC_MODEL      claude-haiku-4-5     (optional, has default)
      APE_MONGO_DB         ape                  (optional, has default)
-->

# APE Modular — Production (MongoDB)

Adaptive Prompt Engine that learns which response format works best per
`(user_id_hash, domain, intent, topic)` using UCB. Implements the design
described in *APE_Final_DynamoDB_Production_Design_UCB_Corrected.docx*,
translated from DynamoDB to **MongoDB** for the data layer.

## Key design points

1. **Personalized bandit.** Cell key = `(user_id_hash, domain, intent, topic, strategy)`. Each user learns their own preferences.
2. **Response-id reward attribution.** Every Path A write produces a `response_id`. Path B applies rewards to that exact `response_id` — never to "the user's last response" globally.
3. **Optional session context.** `session_id` is metadata only — useful for UI chat history. It is NOT part of the bandit key and cannot be used to identify which response gets the reward.
4. **Cached UCB.** `cached_ucb` is the serving cache (read by Path A on every selection). `count`, `total_reward`, `avg_reward` are the source of truth. Path B refreshes `cached_ucb` for every strategy in the cell after each reward (because the explore bonus depends on N).
5. **No raw query storage.** Only classification + attribution metadata is persisted.
6. **Admin-managed config.** Intents, strategies, instructions, policies, signal routing, and reward scale all live in MongoDB and can be mutated via the Config API. Every change is logged in `ape_admin_audit`.

## Five MongoDB collections

| Collection | Purpose | Key fields |
|---|---|---|
| `ape_config` | Admin-managed configuration | `entity_type, entity_id, version, status` |
| `ape_user_bandit_state` | Per-user bandit cells | `user_id_hash, domain, intent, topic, strategy` |
| `ape_turn_record` | Response-level journal (attribution + bandit only) | `response_id` (unique), `attribution_bandit_pk/sk`, `reward_status` |
| `ape_messages` | Conversation history (raw user + assistant text) | `message_id` (unique), `session_id`, `user_id_hash`, `role`, `content`, `response_id` |
| `ape_admin_audit` | Config change log | `date, action_id, action_type, entity_type, entity_id, before, after` |

**Conversation history note:** `ape_messages` stores raw chat content (queries + responses) so the UI can load full threads. The bandit-attribution table (`ape_turn_record`) stays clean — only classification + attribution metadata, no raw text. The two tables join via `response_id` when needed.

## Folder layout

```
ape_modulor_production/
├── ape/
│   ├── signals/             signal routing constants + topic canonicalization
│   ├── strategies/          arm catalog + per-strategy instructions
│   ├── bandit/
│   │   ├── selection.py        select highest cached_ucb + breakdown
│   │   └── reward.py           legacy in-memory reward computation
│   ├── llm/                 classifier + synthesizer (Anthropic Claude)
│   ├── store/
│   │   ├── mongo_schema.py     collections, indexes, status enums
│   │   ├── mongo_store.py      MongoStore class (primary)
│   │   └── store.py            legacy SQLiteStore (kept for reference)
│   ├── config/
│   │   ├── seed.py             seed default config into MongoDB
│   │   └── manager.py          CRUD + admin audit logging
│   ├── models/              Pydantic schemas
│   ├── orchestrator.py      Path A + Path B implementations
│   └── api.py               FastAPI app + SPA static serving
│
├── frontend/                React + Vite SPA
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── pages/              ChatPage, AnalyticsPage
│       ├── components/         Sidebar, MessageList, Composer, ...
│       ├── hooks/              useApe, usePersistedState
│       └── styles/             chat.css, analytics.css
│
├── tests/
│   ├── test_smoke.py           SQLite store (legacy)
│   └── test_mongo.py           MongoDB store + Path A/B
│
├── requirements.txt
├── .env.example
└── README.md
```

## Quick start

### 1. Run MongoDB locally

Either run a real MongoDB:

```bash
docker run -d -p 27017:27017 --name mongo mongo:7
```

Or use **mongomock** for local development/tests without a live DB (already wired into `tests/test_mongo.py`).

### 2. Backend

```bash
pip install -r requirements.txt
cp .env.example .env   # set ANTHROPIC_API_KEY + APE_MONGO_URI + APE_ADMIN_TOKEN
uvicorn ape.api:app --port 7860 --reload
```

On startup, if `ape_config` is empty, the app seeds default intents,
strategies, instructions, policies, signal routing, and reward scale.
Admin/config/analytics API routes require `APE_ADMIN_TOKEN`; enter that same
token in the Admin or Analytics page prompt.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173 (proxies API to :7860)
```

## Per-turn flow

### Path A — strategy selection (current response)

```
POST /turn
{ user_id, query, history, session_id (optional) }
   │
   ▼
A1. Validate intent          GetItem ape_config (entity_type=intent)
A2. Resolve candidate        Query ape_config (entity_type=policy)
A3. Read instructions        Query ape_config (entity_type=instruction, ACTIVE)
A4. Read bandit cell         Query ape_user_bandit_state by (user, domain, intent, topic)
A5. Select highest cached_ucb
A6. Synthesizer LLM call     → answer, rendered_format
A7. Write PENDING response   Insert ape_turn_record with attribution_bandit_pk/sk
   │
   ▼
Response: { response_id, session_id, classification, selection, answer }
```

The client MUST remember `response_id` and send it back on `/feedback`.

### Path B — reward update (exact response_id)

```
POST /feedback
{ user_id, response_id, signal }
   │
   ▼
B1. Read response_id          ape_turn_record.find({response_id})
B2. Validate user + PENDING   reject if user mismatch or already APPLIED
B3. Read signal routing       ape_config (entity_type=signal_routing)
B4. Read reward scale         ape_config (entity_type=reward_scale)
B5. Mark response APPLIED     atomic conditional update
B6. Update bandit strategy    ape_user_bandit_state by attribution_pk/sk
B7. Refresh cached_ucb        recompute for ALL strategies in cell
   │
   ▼
Response: { status: "applied", reward_category, normalized_reward, strategy_row_after }
```

## API endpoints

```
Public:
  GET    /health
  POST   /turn                                    ← Path A (no history field; server reads from DB)
  POST   /feedback                                ← Path B (response_id-targeted)

Conversation history (Mongo-backed):
  GET    /sessions/{session_id}/messages?user_id=... ← load a user's thread
  GET    /users/{user_id}/sessions                ← list a user's recent chat threads
  GET    /users/{user_id}/latest-session          ← auto-resume the most recent one
  DELETE /sessions/{session_id}?user_id=...       ← delete one chat (bandit preserved)

Legacy turn-record views (analytics):
  GET    /sessions/{id}/turns?user_id=...
  GET    /users/{user_id}/responses

Config:
  GET    /config/intents | strategies | policies | signal-rules | reward-scale
  POST   /config/signal-rules | reward-scale | policies | instructions
  POST   /config/instructions/activate

Ops:
  DELETE /admin/clear-user/{user_id}
  DELETE /admin/clear-all
  POST   /admin/seed
  GET    /admin/db-snapshot
  GET    /admin/audit
```

## How conversation history works

```
First message from a user
   │
   ▼
POST /turn {user_id, query}    ← no session_id, no history[]
   │
   ▼
Server: lazy-creates session_id, reads history from ape_messages
   │   (empty on the very first message), runs Path A, writes:
   │       - user message  → ape_messages
   │       - assistant msg → ape_messages (with response_id)
   │       - PENDING record→ ape_turn_record
   │
   ▼
Response: {response_id, session_id, answer, assistant_message_id, ...}

Subsequent messages
   │
   ▼
POST /turn {user_id, session_id, query}
   │
   ▼
Server reads history from MongoDB via session_id, no client data needed.

Reload / open analytics page / come back later
   │
   ▼
GET /sessions/{session_id}/messages?user_id=...
   → full thread back as a list of messages
```

The client persists ONLY `user_id` and the current `session_id` to localStorage. Everything else is server-authoritative.

## Frontend session UX

The sidebar now shows a list of the user's recent chats (first user message + last activity time). Click to switch between sessions; click × to delete one. Bandit state is preserved across session deletes — only the chat thread is removed.

```
useApe() hook    →  fetches from /users/{id}/sessions and /sessions/{id}/messages?user_id=...
ChatPage         →  renders sidebar (session list) + chat (loaded messages) + composer
Message.jsx      →  thumbs_up/down click → POST /feedback with response_id
```

## Reward attribution safety guarantees

Three invariants the design enforces, all verified by `tests/test_mongo.py`:

1. **Response-id targeting** — feedback always targets a specific `response_id`. The bandit row to update is denormalized into `attribution_bandit_pk/sk` on the response record, so Path B does an exact O(1) lookup. No timeline-walking, no guessing.

2. **Double-reward prevention** — Path B uses a conditional update that requires `reward_status = PENDING`. The second call from any source (UI retry, race condition) fails atomically.

3. **Cross-user injection prevention** — Path B requires `user_id_hash` to match the response record. A request claiming to feedback for another user's response is rejected.

## Smoke tests

```bash
PYTHONIOENCODING=utf-8 PYTHONPATH=. python tests/test_mongo.py
```

Uses `mongomock` — no live MongoDB required. Verifies:
- Default config seeding (7 intents, 18 strategies, 11 signals, 4 reward levels)
- Signal routing + reward scale lookups
- Bandit cell lazy-creation with cold-start UCB
- PENDING → APPLIED transition
- UCB cache refresh across the whole cell
- Double-reward + cross-user rejection
- Admin audit logging

## Production deployment

```bash
# Build the React app
cd frontend && npm install && npm run build && cd ..

# Run the unified server
uvicorn ape.api:app --host 0.0.0.0 --port 7860
```

FastAPI serves both the API and the React SPA from `:7860`. No CORS needed.

For a managed MongoDB (Atlas, etc.), set `APE_MONGO_URI` accordingly. Use TLS
and authentication for any non-local deployment.

### Docker / Hugging Face Spaces

The `Dockerfile` at the repo root is a 2-stage build:

1. `node:20-alpine` compiles the Vite SPA → `frontend/dist`
2. `python:3.12-slim` installs the Python deps + serves both the API and the
   built SPA on **port 7860** (HF Spaces default).

Build & run locally:

```bash
docker build -t ape-modulor .
docker run -p 7860:7860 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e APE_MONGO_URI=mongodb+srv://... \
  ape-modulor
```

Open `http://localhost:7860/`.

**Deploy to Hugging Face Spaces:**

1. Create a new Space → SDK: **Docker**, hardware: CPU basic.
2. Push this repo to the Space (or connect a GitHub repo).
3. Go to Space Settings → **Variables and secrets** and add:
   - `ANTHROPIC_API_KEY` (secret) — your Anthropic key
   - `APE_MONGO_URI` (secret) — Atlas/Mongo connection string
   - `APE_ADMIN_TOKEN` (secret) - long random token for admin/config/analytics
   - `ANTHROPIC_MODEL` (variable, optional) — defaults to `claude-haiku-4-5`
4. HF builds the Dockerfile automatically. Logs appear under the "Logs" tab.
5. Once healthy (the `HEALTHCHECK` probes `/health`), the Space serves
   the chat UI at the root and the admin/analytics dashboards at `/admin`
   and `/analytics`.

The container runs as UID 1000 (HF requirement), uses `tini` for clean
signal handling, and binds to `0.0.0.0:7860`. The image is ~250 MB after
multi-stage build trimming.

## Migration from the legacy SQLite store

The legacy `ape/store/store.py` (SqliteStore) is retained but not used. To
migrate existing turn rows from SQLite into MongoDB, write a one-shot script
that reads from `SqliteStore.conn.execute("SELECT * FROM turn_record")` and
inserts into `MongoStore.turn_record`. The bandit state can then be rebuilt
from the audit log via the existing rebuild logic (not currently exposed in
the new API but trivial to add — group-by user/domain/intent/topic/strategy
and sum the rewards).
