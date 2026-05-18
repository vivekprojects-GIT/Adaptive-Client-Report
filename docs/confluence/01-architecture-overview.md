# 01 · Architecture Overview

> **TL;DR** · APE uses 8 MongoDB collections in 5 layers. Raw chat content lives only in `ape_messages`. Bandit learning is keyed by `user_id_hash`. Reward attribution is keyed by `response_id`. Analytics is derived from `ape_turn_record` (structured metadata) — never from raw text.

---

## The 5 layers

```
┌───────────────────────────────────────────────────────────────────┐
│ LAYER 1 — CHAT HISTORY                                            │
│   ape_messages                  raw text (UI resume only)          │
├───────────────────────────────────────────────────────────────────┤
│ LAYER 2 — RUNTIME LEARNING                                        │
│   ape_user_bandit_state         per-user, per-cell, per-strategy   │
│   ape_turn_record               response attribution + reward log  │
├───────────────────────────────────────────────────────────────────┤
│ LAYER 3 — ADMIN CONFIG                                            │
│   ape_config                    intents, strategies, instructions, │
│                                 policies, signals, rewards, offers │
│   ape_admin_audit               before/after on every change       │
├───────────────────────────────────────────────────────────────────┤
│ LAYER 4 — ANALYTICS AGGREGATES                                    │
│   ape_user_topic_interest       per (user, topic) interest scoring │
│   ape_topic_trend_daily         per (date, topic) trending         │
├───────────────────────────────────────────────────────────────────┤
│ LAYER 5 — DISPLAY JOIN (optional)                                 │
│   ape_user_directory            hash → display_name + compliance   │
└───────────────────────────────────────────────────────────────────┘
```

**Total: 8 collections.** 7 APE-owned + 1 optional directory.

---

## Why this split?

| Concern | Where it goes | Why |
|---|---|---|
| Personalization | `ape_user_bandit_state` | Per `user_id_hash` — survives session changes |
| Reward attribution | `ape_turn_record` | Per `response_id` — exact target, prevents double-rewards |
| Audit / history | `ape_messages` (raw) + `ape_admin_audit` (config) | Different lifecycles — chat retention vs config audit |
| Dashboard reads | `ape_user_topic_interest` + `ape_topic_trend_daily` | Precomputed — keep dashboard fast, decouple from runtime |
| Display names | `ape_user_directory` | In production this lives in CRM; the analytics DB tolerates its absence |

---

## Key roles (load-bearing)

> ⚠ **These three keys do non-overlapping jobs.** Mixing them up breaks personalization or causes double-rewards.

| Key | Type | Job | Used by |
|---|---|---|---|
| `user_id_hash` | `u_<16hex>` | **Personalization** | Bandit cells, analytics scope, directory lookup |
| `response_id` | UUID | **Reward attribution** | Path B does an exact lookup by this |
| `session_id` | UUID | **Conversation grouping** | Chat history threads (UI only — **never** a learning or reward key) |

A user moving between sessions keeps the same `user_id_hash`, so their bandit cells continue learning. A reward submitted with the wrong `response_id` gets rejected (no PENDING row matches).

---

## Collection details

### ape_messages
```yaml
PK:        message_id (UUID)
indexes:   (session_id, ts)  ·  (user_id_hash, ts)  ·  response_id (sparse)
fields:
  session_id:   UUID                # conversation grouping (UI)
  user_id_hash: u_<hex>             # owner
  role:         "user" | "assistant"
  content:      RAW text            # ⚠ raw content lives ONLY here
  ts:           ISO-8601
  response_id:  UUID                # assistant rows only — FK to turn_record
```

### ape_user_bandit_state
```yaml
PK:        (user_id_hash, domain, intent, topic, strategy)  # composite unique
indexes:   by cell (user_id_hash, domain, intent, topic) for cell loads
fields:
  count:           int
  total_reward:    float
  avg_reward:      float in [-1, +1]
  cached_ucb:      float (999.0 for cold-start arms)
  policy_version:  string
  ucb_algorithm:   "UCB"
  last_updated_at: ISO-8601
```
One row per (user × cell × strategy arm). Lazy-created on first selection.

### ape_turn_record
```yaml
PK:        response_id (UUID)
indexes:   (user_id_hash, ts)  ·  (session_id, ts)  ·  reward_status
fields:
  user_id_hash:           u_<hex>
  session_id:             UUID         # grouping only — NOT a learning key
  ts:                     ISO-8601
  domain, intent, topic:  strings
  selected_strategy:      string       # what APE picked
  rendered_format:        string       # what the synthesizer actually produced
  format_compliance:      0 | 1        # did rendered match selected's expected format
  attribution_bandit_pk:  { user_id_hash, domain, intent, topic }
  attribution_bandit_sk:  strategy     # exact row to update on feedback
  ucb_at_selection:       float
  instruction_version:    string
  reward_status:          "PENDING" | "APPLIED" | "SKIPPED"
  signal:                 "thumbs_up" | "thumbs_down" | "copy_save" | …
  reward_category:        "strong_positive" | "weak_negative" | …
  normalized_reward:      float in [-1, +1]
```
**Source of truth for analytics recompute.**

### ape_config
```yaml
PK:        (entity_type, entity_id, version)
indexes:   by (entity_type, status) for runtime ACTIVE filter
status:    ACTIVE | INACTIVE | DRAFT
entity_type ∈ {
  intent          # classifier output vocabulary
  strategy        # bandit arm
  instruction     # versioned synthesizer prompt per strategy
  policy          # whitelist of strategies per (domain, intent, topic)
  signal_routing  # signal → reward category mapping
  reward_scale    # reward category → raw + normalized reward
  offer_policy    # topic → outreach action + threshold + weights (UI label: "Outreach")
}
```

### ape_admin_audit
```yaml
PK:        action_id (UUID)
indexes:   (date, ts)  ·  (entity_type, entity_id)
fields:
  date:        YYYY-MM-DD
  ts:          ISO-8601
  action_type: UPSERT | DELETE | STATUS_INACTIVE | STATUS_ACTIVE | UPSERT_INTENT | …
  entity_type, entity_id
  before:      dict (Mongo _id stripped)
  after:       dict (Mongo _id stripped)
  changed_by:  string
```
Append-only. Every admin write goes through `log_admin_action`.

### ape_user_topic_interest
```yaml
PK:        (user_id_hash, domain, topic)
fields:
  count_7d, count_30d:       int
  last_seen_at:              ISO-8601
  avg_reward:                float
  frequency_score:           [0, 1]
  recency_score:             [0, 1]   # exp(-days_since_last / 7)
  engagement_score:          [0, 1]   # avg_reward
  followup_depth_score:      [0, 1]   # count_7d / count_30d
  interest_score:            [0, 1]   # composite (see Outreach recommendation page)
```
Recomputed from `ape_turn_record` — admin trigger or scheduled cron.

### ape_topic_trend_daily
```yaml
PK:        (date, domain, topic)
fields:
  total_turns:       int
  unique_users:      int
  avg_reward:        float
  growth_ratio:      float
  trend_score:       float    # 0.4·norm_count + 0.3·growth/3 + 0.2·density + 0.1·avg_reward
```

### ape_user_directory  *(optional, would be CRM in prod)*
```yaml
PK:        user_id_hash
fields:
  display_name:        "Alex Chen"
  email:               "alex.chen@example.com"
  do_not_contact:      bool          # hard opt-out
  compliance_eligible: bool          # jurisdictional gate
  last_contacted_at:   ISO-8601
  source:              "demo_seed" | "crm_sync" | …
```

> ℹ **In production** this collection should be replaced by a live join to the CRM / identity service. The dashboard must work with hashes alone if the directory is unavailable.

---

## Privacy boundary

The **only** place raw user text exists is `ape_messages`. Production controls for this collection:

- TTL / retention policy
- At-rest encryption
- Access control distinct from analytics readers
- Exclude from analytics ETL jobs

Every other collection stores **structured metadata only** — topic IDs, intent IDs, strategy IDs, scores. This is what makes analytics recompute fast and privacy-safe.

```
ape_messages   ⟵  raw text (UI only)
       │
       │  NOT copied to:
       ▼
ape_turn_record           ← metadata only
ape_user_bandit_state     ← counters + averages
ape_user_topic_interest   ← derived scores
ape_topic_trend_daily     ← derived scores
```

The analytics recompute reads `ape_turn_record` exclusively.

---

## See also

- [02 · Runtime paths](./02-runtime-paths.md) — how Path A and Path B write the runtime collections
- [04 · Analytics layer](./04-analytics-layer.md) — how derived collections are built
- [08 · Privacy & compliance](./08-privacy-and-compliance.md) — the full privacy story
