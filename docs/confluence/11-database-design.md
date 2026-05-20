# 11 - Database Design

> Dedicated MongoDB design page for APE. This page is the Confluence-friendly
> version of the canonical schema in `ape/store/mongo_schema.py`.

---

## Design Goals

APE separates four concerns that should not blur together:

| Concern | Design choice |
|---|---|
| Personalization | Key bandit learning by `user_id_hash` |
| Reward attribution | Key feedback by exact `response_id` |
| Conversation resume | Use `session_id` only for UI grouping |
| Privacy | Store raw text only in `ape_messages` |

There are eight MongoDB collections:

| Layer | Collections |
|---|---|
| Chat history | `ape_messages` |
| Runtime learning | `ape_user_bandit_state`, `ape_turn_record` |
| Admin config | `ape_config`, `ape_admin_audit` |
| Analytics aggregates | `ape_user_topic_interest`, `ape_topic_trend_daily` |
| Optional display join | `ape_user_directory` |

---

## Key Rules

| Key | Meaning | Must not be used for |
|---|---|---|
| `user_id_hash` | Personalization and ownership key | Exact response attribution |
| `response_id` | One assistant response and its reward target | User personalization |
| `session_id` | Conversation grouping for UI resume | Bandit learning or reward attribution |

Load-bearing rules:

- `/feedback` targets `response_id`, not `session_id`.
- Bandit cells are per user, not per session.
- Analytics recompute reads `ape_turn_record`, not `ape_messages`.
- Runtime config reads use `status=ACTIVE`.
- Raw messages are scoped by `session_id + user_id_hash` when read back.

---

## Logical Relationship Map

```text
ape_messages
  assistant rows carry response_id
        |
        v
ape_turn_record
  response_id is unique
  attribution_bandit_pk/sk points to exact bandit row
        |
        v
ape_user_bandit_state
  one row per user + domain + intent + topic + strategy

ape_config
  controls intent, strategy, instruction, policy, signal routing,
  reward scale, and outreach policy
        |
        v
ape_admin_audit
  records every admin/config change

ape_turn_record
        |
        v
analytics recompute
        |
        v
ape_user_topic_interest
ape_topic_trend_daily

ape_user_directory
  optional display and compliance join by user_id_hash
```

---

## Collection: `ape_messages`

Purpose: raw chat history for UI resume and debugging.

Raw text lives here and only here.

Fields:

```yaml
message_id: UUID
session_id: UUID
user_id_hash: u_<hex>
ts: ISO-8601
role: user | assistant
content: raw text
response_id: UUID | null
rendered_format: string | null
meta: object
```

Indexes:

| Name | Keys | Why |
|---|---|---|
| `uniq_message_id` | `message_id` | Unique message lookup |
| `by_session_time` | `session_id`, `ts asc` | Load a chat thread in order |
| `by_user_time` | `user_id_hash`, `ts desc` | List user activity/sessions |
| `by_response_id` | `response_id` sparse | Join assistant message to turn record |

Retention recommendation: TTL 30 to 90 days, encryption at rest, and restricted
DB access because this collection contains raw text.

---

## Collection: `ape_user_bandit_state`

Purpose: personalized UCB learning state.

One row exists for each strategy arm in one user's cell:

```text
user_id_hash + domain + intent + topic + strategy
```

Fields:

```yaml
user_id_hash: u_<hex>
domain: finance
intent: Comparison
topic: retirement_accounts
strategy: comparison_table
count: int
total_reward: float
avg_reward: float
cached_ucb: float
policy_version: string
ucb_algorithm: UCB
last_updated_at: ISO-8601
```

Indexes:

| Name | Keys | Why |
|---|---|---|
| `uniq_bandit_cell_strategy` | `user_id_hash`, `domain`, `intent`, `topic`, `strategy` | One row per arm |
| `by_cell_for_query` | `user_id_hash`, `domain`, `intent`, `topic` | Load candidate arms for selection |

Cold start: unpulled arms get `cached_ucb = 999.0`, so UCB naturally explores
new arms first.

---

## Collection: `ape_turn_record`

Purpose: response attribution, reward ledger, and analytics source of truth.

Fields:

```yaml
response_id: UUID
user_id_hash: u_<hex>
session_id_optional: UUID
ts: ISO-8601
domain: finance
intent: Comparison
intent_confidence: float
topic: retirement_accounts
selected_strategy: comparison_table
selection_method: ucb
suggested_format: comparison_table
rendered_format: comparison_table
format_compliance: 0 | 1
ucb_at_selection: float
policy_version: string
instruction_version: string
attribution_bandit_pk:
  user_id_hash: u_<hex>
  domain: finance
  intent: Comparison
  topic: retirement_accounts
attribution_bandit_sk: comparison_table
pending_signals:
  - signal: format_compliance_pass
    source: derived
    ts: ISO-8601
reward_status: PENDING | APPLIED | SKIPPED
signal: final resolved label | null
reward_category: reward category | null
normalized_reward: float | null
rewarded_at: ISO-8601 | null
```

Indexes:

| Name | Keys | Why |
|---|---|---|
| `uniq_response_id` | `response_id` | Exact feedback target |
| `by_user_time` | `user_id_hash`, `ts desc` | User history and analytics |
| `by_session_time` | `session_id_optional`, `ts desc` sparse | Session turn history |
| `by_reward_status` | `reward_status` | Find pending/applied rows |

Reward state:

```text
PENDING -> APPLIED
PENDING -> SKIPPED
```

The final `signal` is the resolved label for audit and analytics. The bandit
reward is selected separately by scanning all buffered signals and choosing the
strongest format-relevant normalized reward.

---

## Collection: `ape_config`

Purpose: all admin-managed runtime configuration.

Generic fields:

```yaml
entity_type: intent | strategy | instruction | policy | signal_routing | reward_scale | offer_policy
entity_id: string
version: string
status: ACTIVE | INACTIVE | DRAFT
created_at: ISO-8601
updated_at: ISO-8601
```

Entity-specific examples:

```yaml
# intent
entity_type: intent
entity_id: Comparison
description: User wants two or more options compared side by side.
status: ACTIVE

# strategy
entity_type: strategy
entity_id: comparison_table
format_type: comparison_table
status: ACTIVE

# instruction
entity_type: instruction
entity_id: comparison_table
version: v2
instruction_text: Format as a markdown table...
status: ACTIVE

# policy
entity_type: policy
entity_id: Comparison#_default#comparison_table
domain: finance
intent: Comparison
topic: _default
strategy_id: comparison_table
exploration_constant: 1.0
status: ACTIVE

# signal routing
entity_type: signal_routing
entity_id: format_change_request
signal_name: format_change_request
source: llm
format_relevant: true
content_relevant: false
format_category: strong_negative
content_category: null
status: ACTIVE

# reward scale
entity_type: reward_scale
entity_id: strong_positive
reward_category: strong_positive
normalized_reward: 1.0
status: ACTIVE

# outreach policy
entity_type: offer_policy
entity_id: retirement_accounts
domain: finance
offer_type: retirement_planning_consultation
min_interest_score: 0.8
status: ACTIVE
```

Indexes:

| Name | Keys | Why |
|---|---|---|
| `uniq_config_entity` | `entity_type`, `entity_id`, `version` | Versioned config uniqueness |
| `by_entity_status` | `entity_type`, `status` | Runtime ACTIVE lookups |
| `by_policy_cell` | `entity_type`, `domain`, `intent`, `topic` sparse | Policy lookup |

---

## Collection: `ape_admin_audit`

Purpose: append-only audit trail for admin and config changes.

Fields:

```yaml
action_id: UUID
date: YYYY-MM-DD
ts: ISO-8601
action_type: UPSERT | DELETE | STATUS_ACTIVE | STATUS_INACTIVE | BANDIT_RESET | ...
entity_type: string
entity_id: string
before: object | null
after: object | null
changed_by: string
```

Indexes:

| Name | Keys | Why |
|---|---|---|
| `by_date_ts` | `date desc`, `ts desc` | Recent audit view |
| `by_entity` | `entity_type`, `entity_id` | Entity change history |

Retention recommendation: keep indefinitely unless compliance policy says
otherwise.

---

## Collection: `ape_user_topic_interest`

Purpose: derived per-user topic scoring for analytics and outreach.

Fields:

```yaml
user_id_hash: u_<hex>
domain: finance
topic: retirement_accounts
count_7d: int
count_30d: int
last_seen_at: ISO-8601
avg_reward: float
frequency_score: 0..1
recency_score: 0..1
engagement_score: 0..1
followup_depth_score: 0..1
interest_score: 0..1
computed_at: ISO-8601
```

Indexes:

| Name | Keys | Why |
|---|---|---|
| `uniq_user_topic` | `user_id_hash`, `domain`, `topic` | One aggregate row per user-topic |
| `user_top_topics` | `user_id_hash`, `interest_score desc` | User topic table |
| `topic_top_users` | `topic`, `interest_score desc` | Users interested in a topic |

Recomputed from `ape_turn_record`.

---

## Collection: `ape_topic_trend_daily`

Purpose: derived daily topic trend aggregate.

Fields:

```yaml
date: YYYY-MM-DD
domain: finance
topic: retirement_accounts
total_turns: int
unique_users: int
avg_reward: float
growth_ratio: float
trend_score: float
computed_at: ISO-8601
```

Indexes:

| Name | Keys | Why |
|---|---|---|
| `uniq_date_topic` | `date desc`, `domain`, `topic` | One row per topic/day |
| `by_date_trend` | `date desc`, `trend_score desc` | Trending topics |

Recomputed from `ape_turn_record`.

---

## Collection: `ape_user_directory`

Purpose: optional display and compliance join.

Fields:

```yaml
user_id_hash: u_<hex>
display_name: string
email: string
do_not_contact: bool
compliance_eligible: bool
last_contacted_at: ISO-8601 | null
source: demo_seed | crm_sync | ...
```

Indexes:

| Name | Keys | Why |
|---|---|---|
| `uniq_user_directory_hash` | `user_id_hash` | Display/compliance lookup |

Production note: names and emails should usually live in CRM or identity
systems. APE should be able to operate with hashes only.

---

## Runtime Write Paths

### `/turn` and `/turn/stream`

Writes:

```text
ape_messages            user message
ape_user_bandit_state   lazy-created cell rows when needed
ape_turn_record         PENDING response row
ape_messages            assistant message
```

May also finalize a previous pending response before selecting the new one.

### `/feedback`

Writes:

```text
ape_turn_record         append pending signal
ape_turn_record         PENDING -> APPLIED when finalizing
ape_user_bandit_state   update count/reward if format reward exists
ape_user_bandit_state   refresh cached_ucb for the whole cell
```

### `/analytics/recompute`

Reads:

```text
ape_turn_record
```

Writes:

```text
ape_user_topic_interest
ape_topic_trend_daily
```

### Admin Config

Writes:

```text
ape_config
ape_admin_audit
```

---

## Data Retention Guidance

| Collection | Suggested retention |
|---|---|
| `ape_messages` | Short, usually 30 to 90 days |
| `ape_turn_record` | Medium, usually 90 to 180 days |
| `ape_user_bandit_state` | Long, small and useful for personalization |
| `ape_config` | Indefinite |
| `ape_admin_audit` | Indefinite |
| `ape_user_topic_interest` | Recomputed; can be short-lived |
| `ape_topic_trend_daily` | Medium, usually 90 days or business need |
| `ape_user_directory` | CRM policy |

---

## See Also

- [01 - Architecture overview](./01-architecture-overview.md)
- [02 - Runtime paths](./02-runtime-paths.md)
- [08 - Privacy and compliance](./08-privacy-and-compliance.md)
- [09 - API reference](./09-api-reference.md)
