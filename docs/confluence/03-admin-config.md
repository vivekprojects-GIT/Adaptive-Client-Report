# 03 · Admin Config

> Every config entity (intent, strategy, instruction, policy, signal rule, reward value, offer) lives in `ape_config`. The admin UI at `/admin` provides CRUD + status toggling on each. Every write is audited to `ape_admin_audit` with before/after snapshots.

---

## Tabs in `/admin`

| Tab | Entity type | What it controls |
|---|---|---|
| **Intents** | `intent` | The classifier's output vocabulary |
| **Strategies** | `strategy` | The bandit's arms (formats) |
| **Instructions** | `instruction` | Versioned synthesizer prompts per strategy |
| **Policies** | `policy` | Which strategies are allowed per `(intent, topic)` |
| **Outreach** | `offer_policy` | Outreach actions (consults, emails, calls…) with per-action scoring weights |
| **Signal Routing** | `signal_routing` | How user signals map to reward categories |
| **Reward Scale** | `reward_scale` | What each reward category is worth (-1 .. +1) |
| **Audit Log** | (read-only) | Every admin change with before/after |

---

## Universal patterns

### Status pill (every tab)
Every row has a clickable `ACTIVE` / `PAUSED` pill. Click → menu opens → Pause/Activate.

```
ACTIVE  ▾                  PAUSED  ▾
  ┌────────┐                ┌──────────┐
  │ Pause  │                │ Activate │
  │ Cancel │                │ Cancel   │
  └────────┘                └──────────┘
```

Runtime reads filter on `status=ACTIVE`. Pausing is **immediate** and **non-destructive** — the row stays in the table, the runtime just stops using it.

### Edit (loads into form)
Each row has an "Edit" action that loads the row into the form. Saving issues an upsert against the same `(entity_type, entity_id, version)` key.

### Delete (with confirmation)
Each row has a "Delete" action with an explicit confirmation. Logs to `ape_admin_audit` as `DELETE`.

---

## Entity types — detail

### intent
```yaml
entity_id: "Comparison"
description: "User wants two or more options compared side by side."
status: ACTIVE
```
Used by the classifier as the closed vocabulary it must emit. If the classifier returns something not in this list (or marked INACTIVE), the orchestrator coerces to `unmapped`.

### strategy
```yaml
entity_id: "comparison_table"
format_type: "comparison_table"
status: ACTIVE
```
A bandit arm. Each strategy needs:
1. A row in `ape_config` (this entity).
2. An ACTIVE `instruction` for the synthesizer to know how to render it.
3. Inclusion in one or more `policy` rows so the bandit can pick it.

### instruction
```yaml
entity_id: "comparison_table"          # strategy_id
version:   "v1"                         # multiple versions allowed
status:    ACTIVE                       # exactly one ACTIVE per strategy
instruction_text: "Format as a markdown table comparing the options …"
instruction_uri:  null                  # could point to S3 in production
```

> ℹ The Instructions tab shows a coverage banner — *"18 of 19 strategies have an active instruction"* — and lists missing strategies as clickable chips so admin can quickly publish the gap.

### policy
```yaml
entity_id: "Comparison#_default#comparison_table"   # synthesized key
domain:    "finance"
intent:    "Comparison"
topic:     "_default"                                # or a specific topic
strategy_id: "comparison_table"
policy_version: "v1"
exploration_constant: 1.0                            # UCB's c
status: ACTIVE
```

**Lookup order at runtime:**
1. `(domain, intent, topic, status=ACTIVE)` — exact topic match
2. `(domain, intent, "_default", status=ACTIVE)` — fallback
3. Hardcoded `INTENT_STRATEGIES` catalog — last resort

The **Intent → Candidate strategies** view groups these as chips:

```
Comparison · _default · 4 strategies
[standard_llm 47 ×] [comparison_table 87 ×] [pros_cons_table 70 ×] [bullet_contrast 65 ×]
   🔴 LOW         🟢 HIGH                    🟠 MEDIUM            🟠 MEDIUM
                                                              + add strategy… ▾
```

Each chip is tier-colored by the strategy's **global** performance (see [Strategy performance](#strategy-performance-panel) below).

### offer_policy *(UI label: "Outreach")*
```yaml
entity_id: "retirement_accounts"          # topic
domain: "finance"
offer_type: "retirement_planning_consultation"   # UI label: "Outreach type"
description: "Schedule a 30-min planning call"
min_interest_score: 0.80                  # eligibility threshold
status: ACTIVE
# Optional per-action scoring weights (else fall back to globals)
weight_frequency:  0.40
weight_recency:    0.25
weight_engagement: 0.25
weight_followup:   0.10
```

> ℹ The DB-level entity_type is still `offer_policy` for backward compatibility. The UI calls these "outreach actions" — they cover consultations, follow-up emails, support calls, content recommendations, etc.

> ℹ Weights can be entered as fractions (`0.4`, `0.25`) **or** as raw importance (`4`, `2.5`) — the recommender normalizes to sum=1 before applying. See [06 · Outreach recommendation](./06-outreach-recommendation.md).

### signal_routing
```yaml
entity_id: "thumbs_up"
signal_name: "thumbs_up"
format_relevant:  true
content_relevant: true
format_category:  "strong_positive"
content_category: "strong_positive"
status: ACTIVE
```
Maps a user signal to reward categories on each axis. **Format** and **content** are independent — a signal can update one, both, or neither.

### reward_scale
```yaml
entity_id: "strong_positive"             # reward category
raw_reward: 2.0
normalized_reward: 1.0                   # the value the bandit sees
status: ACTIVE
```
The bandit math uses `normalized_reward`. Convention: normalized ∈ [-1, +1].

---

## Strategy performance panel

The Policies tab opens with a **diagnostic panel** that ranks every strategy by reward across the whole user base (and optionally for one user):

```
Strategy              Tier        Performance      Pulls  Users  Best cell
─────────────────────────────────────────────────────────────────────────────
decision_card         HIGH        ████████░ 91.6   40     2      Decision/retirement_accounts μ=0.88
comparison_table      HIGH        ████████░ 86.7   53     4      Comparison/retirement_accounts μ=0.85
analogy_explanation   HIGH        ████████░ 85.0   33     4      Definitional/roth_ira μ=0.82
definition+example    MEDIUM      ███████░░ 79.3   24     4      Definitional/credit_score μ=0.72
pros_cons_table       MEDIUM      ██████░░░ 70.0   26     3      Evaluation/annuity_options μ=0.65
standard_llm          LOW         ████░░░░░ 47.5   6      3      Definitional/expense_ratio μ=-0.10
phased_workflow       LOW         ████░░░░░ 40.0   5      2      Instructional/tax_implications μ=-0.20
bullet_summary        EXPLORING   ██████░░░ 52.5   2      1      —
```

**Tier mapping** (performance_pct = (avg_reward + 1) / 2 × 100):

| Tier | Score range | Meaning | Suggested action |
|---|---|---|---|
| **HIGH** | ≥ 80 | Reliably wins | Keep · maybe promote to more intents |
| **MEDIUM** | 50–80 | Acceptable | Refine the instruction |
| **LOW** | < 50 | Underperforming | Rewrite instruction or pause |
| **EXPLORING** | < min_pulls (default 3) | Too little data | Wait |

The panel also shows **best cell** (where the strategy shines) and **worst cell** (where it bombs) — those guide instruction refinement.

---

## Audit log

Every change writes a row:

```
2026-05-17T07:48:57  STATUS_INACTIVE  intent           Evaluation       admin_user
2026-05-17T07:48:44  DELETE           offer_policy     test_topic       admin_user
2026-05-17T07:48:44  UPDATE           offer_policy     test_topic       admin_user
2026-05-17T07:48:44  UPSERT           offer_policy     test_topic       admin_user
```

`before` and `after` snapshots are JSON-serializable (Mongo `_id` is stripped on both write and read).

---

## See also

- [02 · Runtime paths](./02-runtime-paths.md) — how runtime reads filter on `status=ACTIVE`
- [09 · API reference](./09-api-reference.md) — every config CRUD endpoint
