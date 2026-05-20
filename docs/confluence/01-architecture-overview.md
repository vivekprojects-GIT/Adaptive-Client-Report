# 01 - Architecture Overview

> APE uses MongoDB collections in five layers. Raw chat text is isolated in
> `ape_messages`. Bandit learning is keyed by `user_id_hash`. Reward
> attribution is keyed by `response_id`. Analytics is derived from structured
> turn metadata, not raw messages.

---

## Layers

```text
Layer 1: Chat history
  ape_messages

Layer 2: Runtime learning
  ape_user_bandit_state
  ape_turn_record

Layer 3: Admin configuration
  ape_config
  ape_admin_audit

Layer 4: Analytics aggregates
  ape_user_topic_interest
  ape_topic_trend_daily

Layer 5: Optional display join
  ape_user_directory
```

The optional directory is demo/CRM-style display data. The learning system does
not need names or emails to operate.

---

## Key Roles

| Key | Role | Important rule |
|---|---|---|
| `user_id_hash` | Personalization and user scoping | Same user keeps learning across sessions |
| `response_id` | Exact response attribution | Feedback must target one response |
| `session_id` | Conversation grouping | Never use as a bandit key |

The server hashes raw `user_id` into `user_id_hash` before storage. Analytics
and bandit collections store hashes, not raw user ids.

---

## Collection Summary

### `ape_messages`

Raw chat transcript for UI resume.

```yaml
message_id: UUID
session_id: UUID
user_id_hash: u_<hex>
role: user | assistant
content: raw text
ts: ISO-8601
response_id: UUID | null
rendered_format: string | null
meta: object
```

Transcript reads are user-scoped. The API requires `user_id`, then filters by
`session_id + user_id_hash`.

### `ape_user_bandit_state`

One row per personalized strategy arm.

```yaml
key: user_id_hash + domain + intent + topic + strategy
count: int
total_reward: float
avg_reward: float
cached_ucb: float
policy_version: string
ucb_algorithm: UCB
last_updated_at: ISO-8601
```

Cold-start arms use `cached_ucb = 999.0`, so each candidate strategy is explored
before the bandit starts exploiting winners.

### `ape_turn_record`

The response ledger and reward attribution source.

```yaml
response_id: UUID
user_id_hash: u_<hex>
session_id_optional: UUID
ts: ISO-8601
domain: string
intent: string
topic: string
selected_strategy: string
suggested_format: string
rendered_format: string
format_compliance: 0 | 1
ucb_at_selection: float
policy_version: string
instruction_version: string
attribution_bandit_pk:
  user_id_hash: u_<hex>
  domain: string
  intent: string
  topic: string
attribution_bandit_sk: strategy
pending_signals:
  - signal: string
    source: ui | llm | derived | composite
    ts: ISO-8601
reward_status: PENDING | APPLIED | SKIPPED
signal: final resolved label | null
reward_category: strong_positive | weak_positive | weak_negative | strong_negative | null
normalized_reward: float in [-1, +1] | null
rewarded_at: ISO-8601 | null
```

`pending_signals` is intentionally separate from the final `signal`. The final
label is useful for analytics and audit; the actual bandit reward is chosen by
scanning all buffered signals and taking the strongest format-relevant reward.
This prevents an analytics-only label such as `thumbs_up` from suppressing a
valid format signal such as `format_compliance_pass`.

### `ape_config`

Versioned, status-gated configuration.

```yaml
key: entity_type + entity_id + version
status: ACTIVE | INACTIVE | DRAFT
entity_type:
  intent
  strategy
  instruction
  policy
  signal_routing
  reward_scale
  offer_policy
```

Runtime reads use ACTIVE rows only. Admin pages can list ACTIVE and inactive
rows so operators can pause and resume without deleting history.

### `ape_admin_audit`

Append-only before/after log for config and admin changes.

```yaml
action_id: UUID
date: YYYY-MM-DD
ts: ISO-8601
action_type: UPSERT | DELETE | STATUS_ACTIVE | STATUS_INACTIVE | ...
entity_type: string
entity_id: string
before: object | null
after: object | null
changed_by: string
```

### `ape_user_topic_interest`

Per-user, per-topic interest scores derived from `ape_turn_record`.

```yaml
key: user_id_hash + domain + topic
count_7d: int
count_30d: int
last_seen_at: ISO-8601
avg_reward: float
frequency_score: 0..1
recency_score: 0..1
engagement_score: 0..1
followup_depth_score: 0..1
interest_score: 0..1
```

### `ape_topic_trend_daily`

Daily cross-user topic trend aggregates.

```yaml
key: date + domain + topic
total_turns: int
unique_users: int
avg_reward: float
growth_ratio: float
trend_score: float
```

### `ape_user_directory`

Optional display and outreach gates.

```yaml
user_id_hash: u_<hex>
display_name: string
email: string
do_not_contact: bool
compliance_eligible: bool
last_contacted_at: ISO-8601 | null
source: string
```

In production this should come from CRM or identity infrastructure.

---

## Runtime Contract

`/turn` and `/turn/stream` both do the same learning work:

1. Append the user message.
2. Classify intent/topic/signal.
3. Finalize the previous pending response for that user/session if one exists.
4. Resolve candidate strategies from policy rows.
5. Load active instructions.
6. Load or create the personalized bandit cell.
7. Select the highest `cached_ucb` arm.
8. Generate the answer.
9. Write a PENDING `ape_turn_record` with initial format compliance signal.
10. Append the assistant message.

`/feedback` appends UI signals to the pending response, then either queues or
finalizes the response depending on signal strength, age, and signal count.

---

## Security Boundary

Sensitive API families require `APE_ADMIN_TOKEN`:

```text
/config*
/admin/*
/analytics/*
```

Core chat endpoints remain public to the app:

```text
/health
/turn
/turn/stream
/feedback
/sessions/*
/users/*
```

Public does not mean unscoped. Session transcript endpoints require `user_id`
and filter by `user_id_hash`.

---

## Privacy Boundary

`ape_messages` is the only raw-text collection. The analytics recompute reads
`ape_turn_record`, not messages. Bandit state stores only counters, averages,
strategy ids, intent ids, topic ids, and hashed user ids.

Production controls should treat `ape_messages` as the highest sensitivity
collection:

- TTL or retention policy
- Encryption at rest
- Separate database role for analytics readers with no `ape_messages` access
- Exclusion from ETL jobs

---

## See Also

- [02 - Runtime paths](./02-runtime-paths.md)
- [03 - Admin config](./03-admin-config.md)
- [08 - Privacy and compliance](./08-privacy-and-compliance.md)
- [11 - Database design](./11-database-design.md)
