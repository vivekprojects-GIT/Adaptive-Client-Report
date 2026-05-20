# 09 - API Reference

> Base URL in local dev: `http://127.0.0.1:7860`. The Vite dev server at
> `http://127.0.0.1:5173` proxies the same paths.

---

## Authentication

Public app endpoints:

```text
GET  /health
POST /turn
POST /turn/stream
POST /feedback
GET  /sessions/*
GET  /users/*
DELETE /sessions/*
```

Protected operational endpoints:

```text
/config*
/admin/*
/analytics/*
```

Protected endpoints require one of:

```http
X-APE-Admin-Token: <APE_ADMIN_TOKEN>
Authorization: Bearer <APE_ADMIN_TOKEN>
```

If `APE_ADMIN_TOKEN` is not configured on the server, protected endpoints return
`503`. If the header is missing or wrong, they return `401`.

---

## Core Flow

### `GET /health`

```json
{ "status": "ok" }
```

### `POST /turn`

Generate one assistant response using the non-streaming path.

Request:

```json
{
  "user_id": "alex_retiree",
  "session_id": "optional-session-id",
  "query": "Compare Roth IRA vs Traditional IRA",
  "generate_response": true
}
```

Response:

```json
{
  "response_id": "resp_...",
  "session_id": "sess_...",
  "assistant_message_id": "msg_...",
  "classification": {
    "intent": "Comparison",
    "topic": "roth_vs_traditional_ira",
    "signal": "no_signal"
  },
  "selection": {
    "selected_strategy": "comparison_table",
    "strategies_available": [
      "standard_llm",
      "comparison_table",
      "pros_cons_table",
      "bullet_contrast"
    ],
    "ucb_at_selection": 1.522,
    "policy_version": "v1"
  },
  "answer": "| Feature | Roth IRA | Traditional IRA | ...",
  "rendered_format": "comparison_table",
  "timings_ms": {
    "total": 2100.4
  }
}
```

### `POST /turn/stream`

Same request body as `/turn`, but returns Server-Sent Events with
`Content-Type: text/event-stream`.

Event payloads are JSON objects sent as SSE `data:` lines.

`metadata` event:

```json
{
  "event": "metadata",
  "response_id": "resp_...",
  "session_id": "sess_...",
  "intent": "Comparison",
  "topic": "roth_vs_traditional_ira",
  "selected_strategy": "comparison_table",
  "candidate_strategies": ["standard_llm", "comparison_table"],
  "select_timings_ms": {}
}
```

`delta` event:

```json
{ "event": "delta", "text": "partial raw model text" }
```

`done` event:

```json
{
  "event": "done",
  "response_id": "resp_...",
  "session_id": "sess_...",
  "assistant_message_id": "msg_...",
  "answer": "final parsed answer",
  "rendered_format": "comparison_table",
  "format_compliance": 1,
  "selection": {},
  "classification": {},
  "timings_ms": {}
}
```

`error` event:

```json
{ "event": "error", "message": "..." }
```

Streaming and non-streaming paths both write `ape_messages`, `ape_turn_record`,
and pending format compliance signals.

### `POST /feedback`

Append a UI signal to one response. The response may finalize immediately or
queue the signal for later finalization.

Request:

```json
{
  "response_id": "resp_...",
  "user_id": "alex_retiree",
  "signal": "copy_save"
}
```

Possible response when queued:

```json
{
  "status": "queued",
  "response_id": "resp_..."
}
```

Possible response when applied:

```json
{
  "status": "applied",
  "response_id": "resp_...",
  "signal": "pattern_engaged_positive",
  "reward_category": "weak_positive",
  "normalized_reward": 0.5,
  "strategy_row_after": {
    "strategy": "comparison_table",
    "count": 4,
    "avg_reward": 0.625,
    "cached_ucb": 1.457
  }
}
```

Possible response with no bandit update:

```json
{
  "status": "applied_no_bandit_update",
  "response_id": "resp_...",
  "signal": "thumbs_up",
  "reward_category": null,
  "normalized_reward": null
}
```

Possible rejected response:

```json
{
  "status": "rejected",
  "response_id": "resp_...",
  "reason": "already_finalized",
  "current_status": "APPLIED"
}
```

Feedback statuses:

| Status | Meaning |
|---|---|
| `queued` | Signal buffered; turn remains PENDING |
| `applied` | Turn finalized and bandit updated |
| `applied_no_bandit_update` | Turn finalized but no format-relevant reward existed |
| `rejected` | Missing response, wrong user, already finalized, or race |
| `skipped` | Unknown signal |

---

## Sessions and History

### `GET /sessions/{session_id}/messages?user_id=X&limit=200`

Returns raw chat messages for one session, scoped to the requesting user.
`user_id` is required.

### `GET /sessions/{session_id}/turns?user_id=X&limit=100`

Returns `ape_turn_record` rows for one session, scoped to the requesting user.
`user_id` is required.

### `GET /users/{user_id}/sessions?limit=20`

Returns recent session summaries for a user.

### `GET /users/{user_id}/latest-session`

Returns:

```json
{ "session_id": "sess_..." }
```

or:

```json
{ "session_id": null }
```

### `GET /users/{user_id}/responses?limit=50`

Returns recent turn records for one user.

### `DELETE /sessions/{session_id}?user_id=X`

Deletes one user's messages and response records for that session. Bandit state
is preserved.

---

## Config Reads

All config endpoints require admin token.

| Endpoint | Purpose |
|---|---|
| `GET /config/intents` | List intents |
| `GET /config/strategies` | List strategies |
| `GET /config/policies` | List policies |
| `GET /config/signal-rules` | List signal routing rules |
| `GET /config/reward-scale` | List reward categories |
| `GET /config/instructions?strategy_id=X&status=Y` | List instruction versions |
| `GET /config/offers?status=Y` | List outreach policies |

---

## Config Writes

### `POST /config/intents`

```json
{
  "intent_id": "Comparison",
  "description": "User wants two or more options compared side by side.",
  "changed_by": "admin_user"
}
```

### `POST /config/strategies`

```json
{
  "strategy_id": "comparison_table",
  "format_type": "comparison_table",
  "changed_by": "admin_user"
}
```

### `POST /config/signal-rules`

```json
{
  "signal_name": "format_change_request",
  "format_relevant": true,
  "content_relevant": false,
  "format_category": "strong_negative",
  "content_category": null,
  "source": "llm",
  "feature_id": 1,
  "expected_frequency": "rare",
  "evidence_quality": "high",
  "consumers": ["bandit", "instruction_quality"],
  "changed_by": "admin_user"
}
```

### `POST /config/reward-scale`

```json
{
  "category": "strong_positive",
  "normalized_reward": 1.0,
  "changed_by": "admin_user"
}
```

`raw_reward` is not part of the current request model.

### `POST /config/policies`

```json
{
  "domain": "finance",
  "intent": "Comparison",
  "topic": "_default",
  "strategy_id": "comparison_table",
  "policy_version": "v1",
  "exploration_constant": 1.0,
  "changed_by": "admin_user"
}
```

### `POST /config/instructions`

```json
{
  "strategy_id": "comparison_table",
  "version": "v2",
  "instruction_text": "Format as a markdown table comparing the options.",
  "instruction_uri": null,
  "activate": true,
  "changed_by": "admin_user"
}
```

### `POST /config/instructions/activate?strategy_id=X&version=Y&changed_by=admin_user`

Activates an existing instruction version.

### `POST /config/status`

```json
{
  "entity_type": "strategy",
  "entity_id": "comparison_table",
  "version": "v1",
  "status": "INACTIVE",
  "changed_by": "admin_user"
}
```

`version` is required for instruction rows and optional for most other entity
types.

### `POST /config/offers`

```json
{
  "topic": "retirement_accounts",
  "offer_type": "retirement_planning_consultation",
  "description": "Schedule a 30-minute planning call",
  "min_interest_score": 0.8,
  "weight_frequency": 0.4,
  "weight_recency": 0.25,
  "weight_engagement": 0.25,
  "weight_followup": 0.1,
  "changed_by": "admin_user"
}
```

---

## Config Deletes

| Endpoint | Purpose |
|---|---|
| `DELETE /config/intents/{intent_id}` | Delete an intent |
| `DELETE /config/strategies/{strategy_id}` | Delete a strategy and its instructions |
| `DELETE /config/signal-rules/{signal_name}` | Delete a signal rule |
| `DELETE /config/reward-scale/{category}` | Delete a reward value |
| `DELETE /config/policies?intent=Y&topic=Z&strategy_id=S` | Delete a policy |
| `DELETE /config/instructions/{strategy_id}/{version}` | Delete an instruction version |
| `DELETE /config/offers/{topic}` | Delete an outreach policy |

All deletes are audited.

---

## Admin and Ops

All admin endpoints require admin token.

| Endpoint | Purpose |
|---|---|
| `DELETE /admin/clear-user/{user_id}` | Remove one user's runtime data |
| `DELETE /admin/clear-all` | Clear runtime collections while preserving config/audit |
| `POST /admin/seed` | Seed default config |
| `GET /admin/db-snapshot?user_id=X&limit=N` | Diagnostic snapshot |
| `GET /admin/bandit-state?user_id=X&only_pulled=true` | Inspect bandit rows |
| `DELETE /admin/bandit-state/cell?user_id=X&domain=D&intent=I&topic=T&strategy=S` | Delete one bandit cell or one arm when `strategy` is supplied |
| `GET /admin/audit?date=YYYY-MM-DD&limit=N` | Audit log |

There is no `/admin/rebuild-bandit` endpoint. UCB cache refresh happens during
feedback finalization, and bulk repair should be done with a script if needed.

---

## Analytics

All analytics endpoints require admin token.

| Endpoint | Purpose |
|---|---|
| `POST /analytics/recompute?days=N` | Rebuild derived collections from `ape_turn_record` |
| `GET /analytics/user-interests?user_id=X&limit=K&refresh=bool` | User topic interest |
| `GET /analytics/topic-users?topic=X&limit=K&min_score=Y` | Users interested in topic |
| `GET /analytics/trends?days=N&limit=K&refresh=bool` | Trending topics |
| `GET /analytics/topic-timeseries?topic=X&days=N` | Daily trend for one topic |
| `GET /analytics/platform-timeseries?days=N` | Daily platform activity |
| `GET /analytics/topics-timeseries?days=N&top_n=K` | Daily series for top topics |
| `GET /analytics/signal-correlations?min_users=N` | Signal co-occurrence |
| `GET /analytics/user-timeseries?user_id=X&days=N` | Daily user activity |
| `GET /analytics/offers/{user_id}?domain=Y` | Outreach recommendations |
| `GET /analytics/customer-health?days=N&cohort_weeks=K` | Retention/satisfaction health |
| `GET /analytics/rag-quality?days=N&min_turns=K&sample_limit=S` | Content-quality indicators |
| `GET /analytics/instruction-quality?days=N&min_turns=K&sample_limit=S` | Format/instruction quality |
| `GET /analytics/strategy-performance?user_id=X&min_pulls=N` | Strategy performance tiers |
| `GET /analytics/platform-overview?days=N&top_n=K` | Dashboard overview |
| `GET /analytics/active-users?days=N&min_interest=X&limit=K` | Outreach roster |
| `GET /analytics/user-profile?user_id=X&domain=Y` | 12-facet user profile |
| `GET /analytics/cognitive-facets?user_id=X&min_interactions=N` | Facets; omit user_id for global |

---

## Status Codes

| Code | Meaning |
|---|---|
| `200` | Success |
| `204` | Successful delete with no body |
| `400` | Invalid request value |
| `401` | Protected endpoint missing valid admin token |
| `404` | Resource not found |
| `422` | FastAPI validation error, such as missing required query param |
| `500` | Store/orchestrator not initialized or unexpected server error |
| `503` | Protected endpoint called while `APE_ADMIN_TOKEN` is not configured |

Feedback errors are usually returned as `200` with `status: "rejected"` or
`status: "skipped"` so the UI can show clean inline state without treating user
feedback races as transport failures.

---

## See Also

- [02 - Runtime paths](./02-runtime-paths.md)
- [03 - Admin config](./03-admin-config.md)
- [04 - Analytics layer](./04-analytics-layer.md)
