# MVP 1 · Data Model (DynamoDB) — the 3 tables

APE is a **decision + learning service**. The caller does its own LLM
classification and answer synthesis. APE only:
1. **selects** a format (strategy) for a given classification, and
2. **learns** from the signals the caller sends back.

Three DynamoDB tables make that work. Keys are designed so the serve path is a
single `Query`/`GetItem` and updates are a single `UpdateItem`.

---

## Table 1 — `ApeConfig`  (intents + strategies + format instructions)

**Purpose:** the catalog the bandit chooses from. Tells APE which strategies
(formats) are valid for an intent, and the **format instruction** text to return
to the caller.

| Attribute | Type | Meaning |
|---|---|---|
| `pk` | S (partition key) | `"INTENT"` or `"STRATEGY"` |
| `sk` | S (sort key) | the id — intent name or strategy name |
| `status` | S | `"ACTIVE"` / `"INACTIVE"` (only ACTIVE is used) |
| `description` | S | (intents) human description |
| `format_instruction` | S | (strategies) the directive returned to the caller, e.g. "Format as a markdown table…" |
| `intents` | SS (string set) | (strategies) which intents this strategy is a candidate for |

**Example items**
```jsonc
// an intent
{ "pk": "INTENT", "sk": "Comparison", "status": "ACTIVE",
  "description": "side-by-side comparison questions" }

// a strategy (format) + the instruction APE returns
{ "pk": "STRATEGY", "sk": "comparison_table", "status": "ACTIVE",
  "format_instruction": "Format as a markdown table comparing the options across relevant dimensions.",
  "intents": ["Comparison"] }
```

**Access patterns**
- Candidate strategies for an intent → `Query pk="STRATEGY"`, filter `intents`
  contains the intent (or keep a small per-intent list item).
- A strategy's instruction → `GetItem pk="STRATEGY", sk=<strategy>`.

---

## Table 2 — `ApeBanditState`  (the learned scores — one item per arm)

**Purpose:** the bandit memory. One item = one strategy's score inside one
`(user, intent)` cell.

| Attribute | Type | Meaning |
|---|---|---|
| `pk` | S (partition key) | the **cell**: `"USER#<user_id>#INTENT#<intent>"` |
| `sk` | S (sort key) | `strategy` (the arm) |
| `count` | N | times this strategy was rewarded in this cell |
| `total_reward` | N | sum of rewards |
| `avg_reward` | N | `total_reward / count` (app-computed) |
| `cached_ucb` | N | `avg_reward + c·√(2·ln N / count)` (app-computed) |
| `last_updated_at` | S | ISO timestamp |

**Example item**
```jsonc
{ "pk": "USER#u_ab12#INTENT#Comparison", "sk": "comparison_table",
  "count": 14, "total_reward": 9.5, "avg_reward": 0.679,
  "cached_ucb": 0.95, "last_updated_at": "2026-05-22T10:00:00Z" }
```

**Access patterns**
- Read a whole cell (all arms) for selection → **`Query pk="USER#…#INTENT#…"`**
  (one call). `N` = sum of `count` over the returned arms.
- Reward one arm → **`UpdateItem`** on that exact `(pk, sk)`:
  `ADD count 1, ADD total_reward :r` (returns new values; app recomputes
  `avg_reward` + `cached_ucb`).
- A missing arm = never tried (count 0) → eligible for round-robin cold start.

---

## Table 3 — `ApeTurnState`  (the PENDING turn — the "pending id")

**Purpose:** when APE selects a strategy it writes a **pending** turn keyed by a
`turn_id`. That's the record the caller refers back to when it sends signals, so
APE knows exactly which arm to reward.

| Attribute | Type | Meaning |
|---|---|---|
| `pk` | S (partition key) | `turn_id` (the pending id APE returns) |
| `user_id` | S | who |
| `session_id` | S | conversation id (caller-supplied or minted) |
| `intent` | S | the classification used (which cell) |
| `selected_strategy` | S | the format chosen (**the "previous strategy"** on reward) |
| `format_instruction` | S | the instruction returned to the caller |
| `status` | S | `"PENDING"` → `"APPLIED"` |
| `created_at` | S | ISO timestamp |
| `signals` | L | (set on update) the reactions the caller sent |
| `reward` | N | (set on update) the applied reward |
| `applied_at` | S | (set on update) ISO timestamp |
| `ttl` | N | optional: auto-expire stale PENDING turns |

**Example item (after select, before reward)**
```jsonc
{ "pk": "t_789", "user_id": "u_ab12", "session_id": "s_123",
  "intent": "Comparison", "selected_strategy": "comparison_table",
  "format_instruction": "Format as a markdown table…",
  "status": "PENDING", "created_at": "2026-05-22T10:00:00Z" }
```

**Access patterns**
- Write on select → `PutItem` (status PENDING).
- On reward → `GetItem pk=turn_id` to recover `user_id`, `intent`,
  `selected_strategy`; then `UpdateItem` to set `status="APPLIED"`, `signals`,
  `reward`, `applied_at`.

> The caller may also send `intent` + `previous_strategy` directly with the
> signals; the pending turn is the durable source of truth and lets APE verify
> them. Either way, the reward update needs **(user, intent, previous strategy)**
> — all of which live on the `ApeTurnState` item.
