# 06 · API Reference

All paths are relative; the React client (`frontend/src/api.js`) calls them.
There is **no admin-token auth** (removed by design — the UI never prompts).

## 6.1 Turn & Feedback

| Method | Path | Body / params | Notes |
|---|---|---|---|
| POST | `/turn` | `{user_id, query, session_id?, generate_response?}` | Path A; returns answer + classification + selection + timings |
| POST | `/turn/stream` | same | SSE: `metadata` → `delta…` → `done` |
| POST | `/feedback` | `{response_id, user_id, signal, …}` | Path B; appends a signal, may finalize reward |
| GET | `/health` | — | liveness |

History is read server-side by `session_id`; clients don't send it.
DB validation runs before writes, but unknown classifier intents do not stop the
chat. Missing or inactive labels fall back to active `unmapped` and are stored as
`suggested_intent` for admin review. `/turn` and `/turn/stream` return `422`
only when the served intent has no active strategy candidates.

## 6.2 Config & Admin

- **Read:** `/config/intents|strategies|policies|signal-rules|reward-scale|instructions|offers`
- **Write:** `POST /config/<entity>`, `POST /config/instructions/activate`,
  `POST /config/status` (flip ACTIVE/INACTIVE/DRAFT)
- **Delete:** `DELETE /config/<entity>/...`
- **Ops:** `/admin/seed`, `/admin/clear-user/{id}`, `/admin/clear-all`,
  `/admin/rebuild-bandit`, `/admin/db-snapshot`, `/admin/bandit-state`,
  `/admin/audit`, `/admin/rag-ingest`

Strategy writes include `format_type` and optional `accepted_rendered_formats`.
The strategy remains the bandit arm; aliases only decide format compliance.

## 6.3 Analytics (all support `?days=`; many support `?domain=`)

| Path | Returns |
|---|---|
| `/analytics/recompute` | rebuild interest + trend_daily aggregates |
| `/analytics/platform-overview` | top topics, intent/signal mix, volume (domain-filterable) |
| `/analytics/strategy-performance` | per-format avg reward, tier, best/worst cell (domain-filterable) |
| `/analytics/cognitive-facets` | per-(intent,topic) cells (domain-filterable) |
| `/analytics/active-users`, `/user-profile` | per-user views (domain-filterable) |
| `/analytics/trends`, `/topic(s)-timeseries`, `/platform-timeseries`, `/user-timeseries` | trend charts (domain-filterable) |
| `/analytics/customer-health` | retention cohorts + satisfaction + segments |
| `/analytics/rag-quality`, `/instruction-quality` | failure hotspots by topic / instruction |
| `/analytics/unmapped-intents` | taxonomy backlog (domain-filterable) |
