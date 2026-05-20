# 10 - Architecture Comparison

> Review of the reference "APE Core Data Query and Learning Flow" architecture
> and how this implementation maps to it after the buffered-learning update.

---

## Reference Design Summary

The reference design has four main tables:

| Reference table | Role |
|---|---|
| Turn Record | Per-response attribution and audit trail |
| Beta Distribution Table | Learning state per topic/intent/strategy |
| Signal Routing Table | Maps signals to format/content relevance |
| Reward Scale | Maps reward categories to values |

The core flow is:

1. Classify topic and intent.
2. Pick a format strategy with UCB.
3. Write a turn record.
4. Generate the answer.
5. Capture signals.
6. Route signals to a reward category.
7. Update learning state.

The strongest parts of the reference are attribution, signal routing, and the
distinction between suggested format and rendered format.

---

## Main Differences

| Concern | Reference | This implementation |
|---|---|---|
| Learning scope | Global per topic/intent | Per user via `user_id_hash` |
| Algorithm storage | Named "Beta" table | UCB state with `count`, `avg_reward`, `total_reward`, `cached_ucb` |
| Cold start | Round-robin or random | Unpulled arms get `cached_ucb = 999.0` |
| Reward update | Async batch writer | Synchronous finalization when evidence is ready |
| Feedback handling | Usually one signal -> one reward | Buffered `pending_signals[]` -> composite/atomic resolver -> one final reward |
| Raw text boundary | Not specified | Raw text only in `ape_messages` |
| Admin surface | Not shown | `/admin` config UI with audit |
| Analytics | Implicit queries | Derived collections plus protected `/analytics/*` APIs |
| Operational auth | Not specified | `/config*`, `/admin/*`, `/analytics/*` require `APE_ADMIN_TOKEN` |

---

## Why Per-User Bandits Matter

If the learning key is only `topic + intent`, every user trains the same arm.
That is fine for a global product preference, but not for a personalized
assistant. A user who likes tables and a user who likes analogies would fight
over the same strategy scores.

This implementation keys bandit rows by:

```text
user_id_hash + domain + intent + topic + strategy
```

That keeps each user's format preferences independent while still allowing
global analytics to aggregate across users.

---

## Why Buffered Signals Matter

The initial implementation path treated explicit feedback too directly. That is
dangerous because broad satisfaction signals are not always format evidence.

Current behavior:

```text
response is written as PENDING
  |
  v
format_compliance_pass/fail is pre-seeded as derived evidence
  |
  v
UI, LLM, and lifecycle signals are appended to pending_signals[]
  |
  v
finalizer resolves one label for audit/analytics
  |
  v
finalizer separately chooses strongest format-relevant reward
  |
  v
bandit updates only if a format reward exists
```

Example: `thumbs_up` is useful for NPS and retention analytics, but it has no
format category. It cannot directly train the format bandit. If
`format_compliance_pass` is also present, that derived signal can still provide
the format reward.

---

## Database Mapping

| Reference table | Our collection | Notes |
|---|---|---|
| Turn Record | `ape_turn_record` | Adds `pending_signals[]`, `reward_status`, `format_compliance`, attribution pk/sk |
| Beta Distribution Table | `ape_user_bandit_state` | UCB state, per-user key, cached UCB |
| Signal Routing Table | `ape_config` rows with `entity_type=signal_routing` | Admin-editable and status-gated |
| Reward Scale | `ape_config` rows with `entity_type=reward_scale` | Uses `normalized_reward` only |
| Chat history | `ape_messages` | Explicit raw-text boundary |
| Admin audit | `ape_admin_audit` | Before/after log for config changes |
| Analytics aggregates | `ape_user_topic_interest`, `ape_topic_trend_daily` | Recomputed from turn metadata |
| User directory | `ape_user_directory` | Optional CRM/demo display join |

---

## Current Query and Learning Flow

```text
Client
  |
  | POST /turn or /turn/stream
  v
FastAPI
  |
  | append user message
  v
ape_messages
  |
  | classify intent/topic/signal
  v
Previous pending response finalizer
  |
  | append LLM/session signals
  | detect composites
  | resolve label
  | choose strongest format reward
  | CAS PENDING -> APPLIED
  | update bandit row
  | refresh UCB cache
  v
ape_turn_record + ape_user_bandit_state
  |
  | policy lookup + active instruction lookup
  v
ape_config
  |
  | load personalized bandit cell
  | select argmax(cached_ucb)
  v
Synthesizer
  |
  | answer + rendered_format
  v
ape_turn_record PENDING
  |
  | pending_signals = [format_compliance_pass/fail]
  v
ape_messages assistant row
  |
  v
Client receives response_id
```

Later:

```text
Client
  |
  | POST /feedback { response_id, user_id, signal }
  v
Path B
  |
  | validate response owner and PENDING status
  | validate signal routing
  | append source=ui signal
  | queue or finalize
  v
ape_turn_record + ape_user_bandit_state
```

---

## Suggested vs Rendered Strategy

Every turn records:

| Field | Meaning |
|---|---|
| `selected_strategy` | The UCB arm APE chose |
| `suggested_format` | The format requested from the synthesizer |
| `rendered_format` | The format the synthesizer actually produced |
| `format_compliance` | `1` if rendered format matched the suggestion |

This matters because the reward belongs to the arm APE pulled, but compliance
tells operators whether the instruction is being followed.

Example rows:

| selected_strategy | rendered_format | format_compliance | Buffered evidence | Bandit reward |
|---|---|---:|---|---:|
| `comparison_table` | `comparison_table` | 1 | `format_compliance_pass` | `+0.5` |
| `comparison_table` | `paragraph` | 0 | `format_compliance_fail` | `-0.5` |
| `comparison_table` | `paragraph` | 0 | `thumbs_up` + `format_compliance_fail` | `-0.5` |
| `pros_cons_table` | `pros_cons_table` | 1 | `copy_save` + `format_compliance_pass` | `+0.5` |
| `decision_card` | `decision_card` | 1 | `format_change_request` | `-1.0` |

The third row is the key behavior: a broad `thumbs_up` does not erase objective
format failure.

---

## Admin and Analytics Layer

Protected API surfaces:

```text
/config*
/admin/*
/analytics/*
```

These require `APE_ADMIN_TOKEN`. The SPA routes load first, then ask for the
token before calling protected APIs.

Analytics reads structured metadata:

```text
ape_turn_record
ape_user_bandit_state
ape_user_topic_interest
ape_topic_trend_daily
ape_user_directory
```

It does not read raw chat messages.

---

## Assessment

The reference design is a solid single-user UCB architecture. The production
changes here make it safer for a personalized, multi-user assistant:

1. Add `user_id_hash` to learning keys.
2. Keep raw text out of learning and analytics tables.
3. Use buffered signal resolution instead of direct click-to-reward mapping.
4. Keep broad satisfaction signals out of the format bandit unless a
   format-relevant signal also exists.
5. Make config versioned, status-gated, and audited.
6. Protect operational APIs with an admin token.
7. Precompute analytics aggregates instead of scanning raw runtime data on every
   dashboard load.

---

## See Also

- [01 - Architecture overview](./01-architecture-overview.md)
- [02 - Runtime paths](./02-runtime-paths.md)
- [03 - Admin config](./03-admin-config.md)
- [09 - API reference](./09-api-reference.md)
- [11 - Database design](./11-database-design.md)
