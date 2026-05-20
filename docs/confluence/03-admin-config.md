# 03 - Admin Config

> All runtime tunables live in `ape_config`. The `/admin` UI edits them and
> every write is recorded in `ape_admin_audit`.

---

## Access

The admin SPA route `/admin` is public so React can load. The API calls behind
it are protected:

```text
APE_ADMIN_TOKEN=<long random secret>
X-APE-Admin-Token: <same secret>
```

The frontend stores the token in `localStorage["ape.admin_token"]` and sends it
on admin, config, and analytics API requests. If the server has no
`APE_ADMIN_TOKEN`, protected routes return `503`. If the token is missing or
wrong, protected routes return `401`.

---

## Tabs

| Tab | Config entity | Purpose |
|---|---|---|
| Intents | `intent` | Classifier output vocabulary |
| Strategies | `strategy` | Bandit arms / answer formats |
| Instructions | `instruction` | Versioned synthesizer prompts per strategy |
| Policies | `policy` | Strategy whitelist per `(domain, intent, topic)` |
| Outreach | `offer_policy` | Recommended outreach actions and thresholds |
| Signal Routing | `signal_routing` | Signal metadata and reward categories |
| Reward Scale | `reward_scale` | Normalized reward values consumed by UCB |
| Audit Log | `ape_admin_audit` | Recent config/admin changes |

Runtime reads filter to `status=ACTIVE`. Admin reads show all statuses so
operators can pause and resume rows without deleting them.

---

## Universal Patterns

### Status

Rows can be switched between `ACTIVE`, `INACTIVE`, and for some entity types
`DRAFT`.

- `ACTIVE`: runtime can use the row.
- `INACTIVE`: row is preserved but ignored by runtime.
- `DRAFT`: row exists for editing, not live.

### Audit

Every write stores:

```yaml
action_type: UPSERT | DELETE | STATUS_ACTIVE | STATUS_INACTIVE | ...
entity_type: string
entity_id: string
before: object | null
after: object | null
changed_by: string
```

The audit collection is append-only.

---

## Entity Details

### `intent`

```yaml
entity_id: Comparison
description: User wants two or more options compared side by side.
status: ACTIVE
```

The classifier must emit an ACTIVE intent. Unknown or inactive values are
coerced to `unmapped`.

### `strategy`

```yaml
entity_id: comparison_table
format_type: comparison_table
status: ACTIVE
```

A strategy is a bandit arm. To be useful it also needs:

1. An ACTIVE `instruction`.
2. At least one ACTIVE `policy` row that allows it for an intent/topic.

### `instruction`

```yaml
entity_id: comparison_table
version: v2
instruction_text: Format as a concise markdown comparison table...
instruction_uri: null
status: ACTIVE
```

Only one instruction version should be ACTIVE per strategy. Activating a new
version deactivates the previous one.

### `policy`

```yaml
entity_id: Comparison#_default#comparison_table
domain: finance
intent: Comparison
topic: _default
strategy_id: comparison_table
policy_version: v1
exploration_constant: 1.0
status: ACTIVE
```

Runtime lookup order:

1. Exact `(domain, intent, topic)`.
2. Default topic `(domain, intent, _default)`.
3. Hardcoded fallback catalog.

### `offer_policy`

```yaml
entity_id: retirement_accounts
domain: finance
offer_type: retirement_planning_consultation
description: Schedule a 30-minute planning call
min_interest_score: 0.80
weight_frequency: 0.40
weight_recency: 0.25
weight_engagement: 0.25
weight_followup: 0.10
status: ACTIVE
```

The UI calls these "Outreach" actions. The DB entity name remains
`offer_policy` for compatibility.

Weights can be fractions or raw importance values; the recommender normalizes
them before scoring.

### `signal_routing`

Signals describe evidence. The bandit uses only the format axis today; content
and satisfaction signals remain valuable for analytics and quality dashboards.

Example format-negative rule:

```yaml
entity_id: format_change_request
signal_name: format_change_request
source: llm
format_relevant: true
content_relevant: false
format_category: strong_negative
content_category: null
feature_id: 1
expected_frequency: rare
evidence_quality: high
consumers:
  - bandit
  - instruction_quality
status: ACTIVE
```

Example satisfaction-only rule:

```yaml
entity_id: thumbs_up
signal_name: thumbs_up
source: ui
format_relevant: false
content_relevant: false
format_category: null
content_category: null
feature_id: 13
expected_frequency: moderate
evidence_quality: low
consumers:
  - analytics
  - retention
  - nps
status: ACTIVE
```

This is intentional. `thumbs_up` should not directly train the format bandit;
otherwise generic satisfaction would bias format selection.

### `reward_scale`

```yaml
entity_id: strong_positive
reward_category: strong_positive
normalized_reward: 1.0
status: ACTIVE
```

There is no `raw_reward` field in the current schema. The bandit consumes
`normalized_reward` directly.

Default values:

| Category | Normalized reward |
|---|---:|
| `strong_positive` | `1.0` |
| `weak_positive` | `0.5` |
| `weak_negative` | `-0.5` |
| `strong_negative` | `-1.0` |

---

## Strategy Performance

The Policies tab surfaces strategy diagnostics from bandit state:

| Tier | Score range | Meaning |
|---|---|---|
| HIGH | `>= 80` | Strong performer |
| MEDIUM | `50..80` | Acceptable, worth tuning |
| LOW | `< 50` | Underperforming |
| EXPLORING | Too few pulls | Wait for more data |

The score is derived from average reward:

```text
performance_pct = (avg_reward + 1) / 2 * 100
```

---

## Operational Notes

- Pausing a strategy does not delete its historical bandit rows.
- Pausing a policy removes that strategy from future candidate sets.
- Changing reward scale affects future finalizations; historical rows keep the
  reward value that was applied at finalization time.
- Signal routing can make a signal analytics-only by setting both relevance
  booleans to false.

---

## See Also

- [02 - Runtime paths](./02-runtime-paths.md)
- [09 - API reference](./09-api-reference.md)
