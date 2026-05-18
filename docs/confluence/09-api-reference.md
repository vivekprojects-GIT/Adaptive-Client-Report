# 09 · API Reference

> Every HTTP endpoint, grouped by purpose. All endpoints are JSON in / JSON out. The base URL in dev is `http://localhost:7860` (Vite proxy at `:5173` forwards transparently).

---

## Core flow

### `GET /health`
```json
{ "status": "ok" }
```

### `POST /turn`
Send a user message; get back the LLM's response and the bandit-selected strategy.

**Request:**
```json
{
  "user_id":    "alex_retiree",
  "session_id": "sess_optional_uuid",
  "query":      "Compare Roth IRA vs Traditional IRA"
}
```

**Response:**
```json
{
  "response_id":         "resp_4f1a92e8...",
  "session_id":          "sess_e2d1...",
  "answer":              "| Feature | Roth IRA | ...",
  "rendered_format":     "comparison_table",
  "selected_strategy":   "comparison_table",
  "strategies_available": ["standard_llm", "comparison_table", "pros_cons_table", "bullet_contrast"],
  "ucb_at_selection":    1.522,
  "intent":              "Comparison",
  "topic":               "roth_vs_traditional_ira"
}
```

### `POST /feedback`
Apply a reward to a specific response.

**Request:**
```json
{
  "response_id": "resp_4f1a92e8...",
  "user_id":     "alex_retiree",
  "signal":      "thumbs_up"
}
```

**Response:**
```json
{
  "status":     "applied",
  "reward":     1.0,
  "new_avg":    0.85
}
```

> Errors: `404` if no PENDING row matches the (response_id, user_id_hash) tuple. Returned cleanly — never crashes.

---

## Sessions / history

### `GET /sessions/{session_id}/messages?limit=200`
Returns the full message thread for a session.

### `GET /users/{user_id}/sessions?limit=20`
List a user's recent sessions with first-message previews.

### `GET /users/{user_id}/latest-session`
Returns `{ session_id }` or `{ session_id: null }`.

### `DELETE /sessions/{session_id}?user_id=X`
Delete one session.

### `GET /sessions/{session_id}/turns?limit=100`
Returns the audit-style `ape_turn_record` rows for a session.

### `GET /users/{user_id}/responses?limit=50`
Returns recent `ape_turn_record` rows for a user.

---

## Config — reads (admin UI)

| Endpoint | Returns |
|---|---|
| `GET /config/intents` | All intents (ACTIVE + PAUSED, per admin requirements) |
| `GET /config/strategies` | All strategies |
| `GET /config/policies` | All policies |
| `GET /config/signal-rules` | All signal routing rules |
| `GET /config/reward-scale` | All reward category values |
| `GET /config/instructions?strategy_id=X&status=Y` | Filter on strategy and/or status |
| `GET /config/offers?status=Y` | All offers (filter by status) |

---

## Config — writes

### `POST /config/intents`
```json
{ "intent_id": "Comparison", "description": "...", "changed_by": "admin_user" }
```

### `POST /config/strategies`
```json
{ "strategy_id": "comparison_table", "format_type": "comparison_table" }
```

### `POST /config/signal-rules`
```json
{
  "signal_name":     "thumbs_up",
  "format_relevant": true,
  "content_relevant": true,
  "format_category":  "strong_positive",
  "content_category": "strong_positive"
}
```

### `POST /config/reward-scale`
```json
{ "category": "strong_positive", "raw_reward": 2.0, "normalized_reward": 1.0 }
```

### `POST /config/policies`
```json
{
  "domain":  "finance",
  "intent":  "Comparison",
  "topic":   "_default",
  "strategy_id":          "comparison_table",
  "policy_version":       "v1",
  "exploration_constant": 1.0
}
```

### `POST /config/instructions`
```json
{
  "strategy_id":      "comparison_table",
  "version":          "v2",
  "instruction_text": "Format as a markdown table comparing the options...",
  "instruction_uri":  null,
  "activate":         true
}
```
`activate: true` deactivates the previous version and makes this one ACTIVE.

### `POST /config/instructions/activate?strategy_id=X&version=Y`
Promote an existing instruction version to ACTIVE.

### `POST /config/offers`
```json
{
  "topic":              "retirement_accounts",
  "offer_type":         "retirement_planning_consultation",
  "description":        "Schedule a 30-min planning call",
  "min_interest_score": 0.80,
  "weight_frequency":   0.40,
  "weight_recency":     0.25,
  "weight_engagement":  0.25,
  "weight_followup":    0.10
}
```
Weights are optional; missing values fall back to global defaults.

### `POST /config/status`  *(universal toggle)*
```json
{
  "entity_type": "intent",
  "entity_id":   "Evaluation",
  "version":     "v1",          // required for instructions only
  "status":      "INACTIVE"     // ACTIVE | INACTIVE | DRAFT
}
```
Flips the status field. Runtime reads pick it up immediately.

---

## Config — deletes

| Endpoint | Payload |
|---|---|
| `DELETE /config/intents/{intent_id}` | path |
| `DELETE /config/strategies/{strategy_id}` | path (also removes instructions for that strategy) |
| `DELETE /config/signal-rules/{signal_name}` | path |
| `DELETE /config/reward-scale/{category}` | path |
| `DELETE /config/policies?intent=X&topic=Y&strategy_id=Z` | query |
| `DELETE /config/instructions/{strategy_id}/{version}` | path |
| `DELETE /config/offers/{topic}` | path |

All deletes log to `ape_admin_audit`.

---

## Analytics

### `POST /analytics/recompute?days=N`
Rebuilds `ape_user_topic_interest` + `ape_topic_trend_daily` from raw `ape_turn_record`. Takes ~13 s on a 260-turn dataset.

### `GET /analytics/platform-overview?days=N&top_n=K`
Cross-user macro view.

### `GET /analytics/active-users?days=N&min_interest=X&limit=K`
Outreach roster.

### `GET /analytics/trends?days=N&limit=K&refresh=bool`
Trending topics.

### `GET /analytics/topic-users?topic=X&limit=K&min_score=Y`
Users interested in a topic.

### `GET /analytics/topic-timeseries?topic=X&days=N`
Daily counts for one topic.

### `GET /analytics/user-profile?user_id=X`
12-facet profile (per-user only — `user_id` required).

### `GET /analytics/cognitive-facets?user_id=X&min_interactions=N`
Per-cell facets. **Omit `user_id` for the global aggregated view.**

### `GET /analytics/user-interests?user_id=X&limit=K&refresh=bool`
Topic interest table for one user.

### `GET /analytics/offers/{user_id}?domain=Y`
Recommended outreach actions for one user. *(Endpoint path keeps `offers` for backward compatibility.)*

### `GET /analytics/strategy-performance?user_id=X&min_pulls=N`
Strategy ranking with tiers. Omit `user_id` for global only; pass `user_id` for global + per-user.

---

## Admin / ops

| Endpoint | Purpose |
|---|---|
| `DELETE /admin/clear-user/{user_id}` | Remove all data for one user (bandit + turns + messages) |
| `DELETE /admin/clear-all` | Reset the runtime collections (config preserved) |
| `POST /admin/rebuild-bandit` | Recompute UCB cache for every cell |
| `GET /admin/db-snapshot?user_id=X&limit=N` | Diagnostic dump for one user |
| `GET /admin/audit?date=Y&limit=N` | Audit log entries |
| `POST /admin/seed` | Seed default intents/strategies/instructions/policies/signal-rules/reward-scale |

---

## Status code conventions

| Code | When |
|---|---|
| `200` | Success |
| `204` | Success, no content (e.g. delete) |
| `400` | Bad request (missing required field, invalid status value) |
| `404` | Resource not found OR no PENDING row matches feedback |
| `500` | Store not initialized (startup failure) — should never happen in steady state |

The frontend `request()` helper unwraps FastAPI's `{"detail": "..."}` error body and throws an Error with that message, so the UI surfaces clean error text on the failing section.

---

## See also

- [02 · Runtime paths](./02-runtime-paths.md) — what `/turn` and `/feedback` do internally
- [03 · Admin config](./03-admin-config.md) — UI for the config endpoints
- [04 · Analytics layer](./04-analytics-layer.md) — UI for the analytics endpoints
