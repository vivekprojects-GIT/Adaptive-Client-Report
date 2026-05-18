# 10 · Architecture Comparison & Equivalent Diagram

> Reviews the reference "APE Core Data Query & Learning Flow" architecture, contrasts it with what we built in `ape_modulor_production`, and presents the equivalent diagram + DB tables + query-flow for our system. Three sections, as requested: **database design**, **flow diagram with query flow**, and **suggested vs rendered strategy**.

---

## Part 1 · Review of the reference architecture

The reference design has four runtime tables:

| Reference table | Role |
|---|---|
| **1. Turn Record** | Per-turn audit trail (suggested_format, rendered_format, signal, reward, attribution_arm_id) |
| **2. Beta Distribution Table** | Learning state: per `topic#intent#strategy`, tracks alpha / beta / format_count / format_avg_reward / format_total_reward |
| **3. Signal Routing Table** | Static gate: per signal, `format_relevant` + `content_relevant` + strength |
| **4. Reward Scale** | Static value key: signal category → reward value (+2 / +1 / -1 / -2 / NOT_RECORDED) |

The flow is 7 steps: pre-load static rulebooks → topic/intent → UCB pick → initial write → LLM generate → compliance check → signal capture → valuation → batch-writer learning update.

### What's strong

- **Clear separation of static rulebooks (Tables 3, 4) from learning state (Table 2).** They're read once at Lambda cold-start and never touched after — fast and consistent.
- **`attribution_arm_id` on Turn Record** correctly links N → N−1, so the reward goes to the right arm even with delayed feedback.
- **Compliance distinction** (`suggested_format` vs `rendered_format`) is exactly right — without it, you can't tell whether the LLM honored the format hint.
- **`format_relevant` gate before recording reward** prevents content-only feedback (e.g., factual correction) from corrupting format scores. This is the most important guardrail in the design.
- **"NOT_RECORDED" vs "zero reward"** — keeping the strategy *frozen* (no update) on an irrelevant signal is correct. A zero update would still nudge the average toward 0.
- **Asymmetric weighting** (+2 strong vs +1 weak) lets explicit thumbs-down hurt more than an inferred "regenerate" — also correct.

### Gaps / things to be careful about

| Gap | Why it matters | Our take |
|---|---|---|
| **Personalization is not in the cell key.** The Beta Distribution Table's composite key is `topic#intent`, so all users share the same arm. A user who hates tables and a user who loves them pull the same arm and corrupt each other's signal. | If APE is a product feature for a financial advisor's clients (or a multi-tenant assistant), per-user learning is essential. Without it, you get the *average* user's preference. | We added `user_id_hash` to the key. Each user has their own bandit cells. |
| **Naming "Beta Distribution Table" is misleading when the algorithm is UCB.** UCB is frequentist — it uses count + avg_reward + an exploration term. It doesn't need α / β. Calling the table that name implies Thompson Sampling. | If reviewers / auditors see "Beta Distribution" and read about UCB selection, they'll wonder which one is actually running. | We named ours `ape_user_bandit_state` and store `count / total_reward / avg_reward / cached_ucb`. We treat Beta(α, β) as a *visualization* device only (post-hoc projection from count + avg_reward) and label the curves "shape ≈ Beta(α, β)" so it's honest. |
| **Cold-start says "round-robin or random".** | That works, but UCB already handles cold-start naturally — give unpulled arms a very high cached_ucb (e.g., 999) and they win first by construction. No separate cold-start branch needed. | We use the natural UCB cold-start: `cached_ucb = 999.0` for `count == 0`. The selection code is one line: `argmax(cached_ucb)`. |
| **Batch-writer Lambda is asynchronous.** | If the batch-writer falls behind, the next selection reads stale state. Worse, if it fails silently, learning stops without anyone noticing. | We do the update synchronously inside `/feedback`: mark response APPLIED → update bandit row → recache UCB for the whole cell. Atomic, observable, no queue. |
| **No mention of audit / privacy boundary for raw text.** | The Turn Record stores `signal` and the rendered_format, but where does the raw query go? Without explicit separation, raw text leaks into analytics. | We put raw text only in `ape_messages` (UI resume) and never copy it into Turn Record / Bandit State / analytics aggregates. |
| **No admin tuning surface.** | Strategies, instructions, policies, signal mappings, reward values are all in tables but the diagram doesn't show admin write paths. | We have `ape_config` (versioned, status-gated) + `ape_admin_audit` (before/after) so every admin change is reversible and auditable. |

### Net assessment

The reference design is **correct as a single-user learning system**. The flow control, gate logic, attribution, and reward weighting are right. The two things that make it production-fragile rather than wrong:

1. **No per-user personalization** — fundamental product decision; if all users want the same thing, this is fine.
2. **Async batch-writer** — works at scale but introduces invisible failure modes.

Everything else in the reference is solid foundation.

---

## Part 2 · Side-by-side comparison

| Concern | Reference design | `ape_modulor_production` |
|---|---|---|
| **Algorithm** | UCB on Beta Distribution Table | UCB (`avg_reward + c·√(2·ln N / count)`) on Bandit State |
| **Bandit cell key** | `topic#intent` (1 cell per topic+intent globally) | `(user_id_hash, domain, intent, topic, strategy)` (1 cell per user × intent × topic, one row per strategy) |
| **Personalization** | ❌ Global | ✅ Per-user |
| **Storage** | DynamoDB | MongoDB |
| **Compute** | AWS Lambda (LangGraph) | FastAPI (Python) |
| **Bandit cells maintained** | Tracks α / β / count / avg_reward / total_reward | Tracks count / total_reward / avg_reward / **cached_ucb** |
| **Cold-start** | Round-robin or random | `cached_ucb = 999.0` for unpulled arms (UCB picks them first naturally) |
| **Reward write path** | Async batch-writer Lambda | Synchronous: mark response APPLIED → update row → recache cell UCB |
| **Reward attribution** | `attribution_arm_id` on Turn Record (links N → N−1) | `attribution_bandit_pk` + `attribution_bandit_sk` (exact bandit row to update; keyed by `response_id` for exact targeting) |
| **Compliance** | `suggested_format` vs `rendered_format` | Same, plus a `format_compliance` 0/1 flag computed via `compute_format_compliance(suggested, rendered)` |
| **Signal routing** | Boolean `format_relevant` + `content_relevant` + strength | Same shape; admin-editable in `ape_config` with `status` toggle |
| **Reward scale** | Category → +2/+1/-1/-2 | Same shape; admin-editable |
| **Static rulebooks** | Loaded at Lambda cold-start | Read on demand from `ape_config` with `status=ACTIVE` filter — cache via natural process-lifetime caching |
| **Number of collections** | 4 runtime tables | 8 collections (chat history, runtime bandit, turn record, config, admin audit, user-topic interest, topic trend daily, optional user directory) |
| **Analytics layer** | Implicit (would query Turn Record directly) | Explicit: `ape_user_topic_interest` + `ape_topic_trend_daily` recomputed from `ape_turn_record` |
| **Privacy boundary for raw text** | Not stated | Raw queries live ONLY in `ape_messages`; never copied into bandit / analytics |
| **Admin surface** | Not shown | `/admin` UI with versioned config + status pill + audit log |
| **Outreach gates** | Not shown | `do_not_contact` + `compliance_eligible` + `score ≥ threshold` (three-way gate in offer recommender) |

---

## Part 3 · Database design

Eight collections, grouped by purpose. See [01 · Architecture overview](./01-architecture-overview.md) for the full schema; the table below is the elevator pitch.

| Collection | Role | Primary key | Updated by |
|---|---|---|---|
| `ape_messages` | Chat transcript (raw text — UI resume only) | `message_id` | Path A on every turn |
| `ape_user_bandit_state` | Per-user bandit cells | `(user_id_hash, domain, intent, topic, strategy)` | Path A (lazy-create) + Path B (reward) |
| `ape_turn_record` | Response-level attribution + reward log | `response_id` | Path A (PENDING) → Path B (APPLIED) |
| `ape_config` | All admin config (intents, strategies, instructions, policies, signal_routing, reward_scale, offer_policy) | `(entity_type, entity_id, version)` | Admin tab writes |
| `ape_admin_audit` | Before/after on every config change | `action_id` | Admin tab writes (via `log_admin_action`) |
| `ape_user_topic_interest` | Per `(user, topic)` derived interest score | `(user_id_hash, domain, topic)` | `POST /analytics/recompute` (admin or cron) |
| `ape_topic_trend_daily` | Per `(date, topic)` daily trend score | `(date, domain, topic)` | `POST /analytics/recompute` |
| `ape_user_directory` *(optional)* | Hash → display_name + compliance gates | `user_id_hash` | Seed scripts (production: CRM-sourced) |

---

## Part 4 · Flow diagram (in the style of the reference)

```
═══════════════════════════════════════════════════════════════════════════════════════════════
                    APE MODULAR — DATA QUERY & LEARNING FLOW
                         FastAPI · MongoDB · UCB · Per-user
═══════════════════════════════════════════════════════════════════════════════════════════════

         ┌─────────────────────────────────────────────────────────────────────────────┐
         │                          APE RUNTIME (FastAPI)                              │
         │                                                                             │
         │   ┌──────────────────────────┐                                              │
         │   │ 1. USER INTERACTION       │       ┌──────────────────────────────────┐  │
         │   │    & CLASSIFICATION        │       │ 2. BANDIT STATE                  │  │
         │   │    (Turn N)                │       │    (ape_user_bandit_state)       │  │
         │   │ ── classifier LLM call ──  │       │    PK = (user_hash, domain,      │  │
         │   │   intent, topic, signal    │──────▶│         intent, topic, strategy) │  │
         │   └──────────────┬────────────┘  ────  │    count · avg_reward ·          │  │
         │                  │  user_hash + topic  │    total_reward · cached_ucb     │  │
         │                  │  + intent           │                                  │  │
         │                  ▼                     └────────────────────┬─────────────┘  │
         │   ┌──────────────────────────┐                              │                │
         │   │ 3. POLICY LOOKUP &        │                              │                │
         │   │    CANDIDATE STRATEGIES   │                              │                │
         │   │  ape_config(policy,ACTIVE)│                              │                │
         │   └──────────────┬────────────┘                              │                │
         │                  │                                            │                │
         │                  │   candidates                               │                │
         │                  ▼                                            │                │
         │   ┌──────────────────────────┐         ┌──────────────────────┘                │
         │   │ 4. UCB SELECTION          │  reads │                                       │
         │   │  argmax(cached_ucb)       │◀───────┤  picks the winner                     │
         │   │  cold-start arms          │        │                                       │
         │   │  (count=0) → ucb=999      │        │                                       │
         │   └──────────────┬────────────┘        │                                       │
         │                  │ selected_strategy   │                                       │
         │                  ▼                     │                                       │
         │   ┌──────────────────────────┐         │                                       │
         │   │ 5. SYNTHESIZER LLM         │       │                                       │
         │   │   + instruction_text       │       │                                       │
         │   │  ape_config(instruction,   │       │                                       │
         │   │  ACTIVE) for selected      │       │                                       │
         │   │   strategy                 │       │                                       │
         │   └──────────────┬────────────┘       │                                       │
         │                  │ answer + rendered_format                                   │
         │                  ▼                                                             │
         │   ┌────────────────────────────────────────────────┐                          │
         │   │ 6. TURN RECORD WRITE (PENDING)                  │                          │
         │   │    ape_turn_record                              │                          │
         │   │    PK = response_id                             │                          │
         │   │    suggested_strategy · rendered_format         │                          │
         │   │    format_compliance · attribution_bandit_pk/sk │                          │
         │   │    reward_status = PENDING                      │                          │
         │   └────────────────────────────────────────────────┘                          │
         │                                                                                 │
         │   - - - - - - - - - - - - -  Async user feedback later  - - - - - - - - - - - │
         │                                                                                 │
         │   ┌──────────────────────────┐    reads     ┌─────────────────────────────┐   │
         │   │ 7. SIGNAL CAPTURE          │            │ SIGNAL ROUTING               │   │
         │   │    POST /feedback          │◀───────────│ ape_config(signal_routing,   │   │
         │   │    + response_id           │            │            ACTIVE)           │   │
         │   │    + signal (thumbs_up,    │            │ format_relevant · strength · │   │
         │   │       regenerate, ...)     │            │ content_relevant             │   │
         │   └──────────────┬────────────┘            └─────────────────────────────┘   │
         │                  │ format_relevant?                                            │
         │                  │   • true  → continue                                        │
         │                  │   • false → SKIPPED, freeze the strategy                    │
         │                  ▼                                                             │
         │   ┌──────────────────────────┐    reads     ┌─────────────────────────────┐   │
         │   │ 8. VALUATION               │            │ REWARD SCALE                 │   │
         │   │    look up reward          │◀───────────│ ape_config(reward_scale,     │   │
         │   │    category for signal     │            │            ACTIVE)           │   │
         │   │    → normalized [-1,+1]    │            │ strong_positive=+2 ...       │   │
         │   └──────────────┬────────────┘            └─────────────────────────────┘   │
         │                  │ reward                                                      │
         │                  ▼                                                             │
         │   ┌──────────────────────────────────────────────────────────────────────────┐ │
         │   │ 9. ATOMIC LEARNING UPDATE  (synchronous — no queue)                       │ │
         │   │    a. mark turn_record APPLIED  conditional on PENDING + user_hash match  │ │
         │   │    b. read attribution_bandit_pk + sk from the record                     │ │
         │   │    c. update bandit row: count += 1, total_reward += r, avg_reward = …    │ │
         │   │    d. recache UCB for every arm in the cell (N changed)                   │ │
         │   └──────────────────────────────────────────────────────────────────────────┘ │
         │                                                                                 │
         └─────────────────────────────────────────────────────────────────────────────────┘

       - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

         ┌─────────────────────────────────────────────────────────────────────────────────┐
         │                ADMIN / ANALYTICS LAYER  (decoupled from runtime)                 │
         │                                                                                  │
         │   /admin UI ─ writes ape_config + ape_admin_audit                                │
         │                                                                                  │
         │   POST /analytics/recompute  (admin button + cron)                               │
         │     reads:  ape_turn_record  (NEVER ape_messages — raw text stays put)            │
         │     writes: ape_user_topic_interest · ape_topic_trend_daily                       │
         │                                                                                  │
         │   Dashboard reads:                                                                │
         │     /analytics/platform-overview   /analytics/active-users                        │
         │     /analytics/user-profile        /analytics/cognitive-facets                    │
         │     /analytics/trends              /analytics/offers/{user_id}                    │
         │     /analytics/strategy-performance                                               │
         └─────────────────────────────────────────────────────────────────────────────────┘
```

### How this maps to the reference's 7 steps

| Reference step | Our equivalent |
|---|---|
| Pre-load Tables 3, 4 | `ape_config` is read on demand; `status=ACTIVE` filter is the access gate. Reads can be cached by process — they're tiny. |
| Step 1 — Topic + Intent | Classifier LLM in `orchestrator.handle_turn`; intent validated against `ape_config(intent)` |
| Step 2 — UCB selection | `select_strategy_from_rows()` = `argmax(cached_ucb)`. Cold-start handled by 999.0 sentinel. |
| Step 2 — Initial write | `store.write_pending_response(doc)` writes Turn Record with `reward_status=PENDING` |
| Step 3 — Synthesizer + compliance | `generate_response()` returns `rendered_format`; `compute_format_compliance(suggested, rendered)` → 0/1 written to the same row |
| Step 4 — Signal filter | `signal_routing` lookup; if `format_relevant=false`, the Path B atomic update never fires (reward_status stays PENDING; we mark SKIPPED if desired) |
| Step 5 — Valuation | `reward_scale` lookup; normalized reward applied |
| Step 6 — Learning update | Synchronous atomic update + UCB cache refresh for the whole cell. No separate batch-writer. |

---

## Part 5 · Suggested vs Rendered strategy (compliance tracking)

Every Turn Record carries three related fields:

| Field | Type | What it means | Who writes it |
|---|---|---|---|
| `selected_strategy` | string | What APE *suggested* — output of UCB selection. e.g. `"comparison_table"` | Path A, before the synthesizer call |
| `rendered_format` | string | What the synthesizer *actually produced*. e.g. `"comparison_table"` or `"paragraph"` if it ignored the hint | Path A, after the synthesizer call |
| `format_compliance` | 0 \| 1 | `1` iff rendered matches the expected format for the strategy. `standard_llm` and `*`-format strategies are always compliant. | Path A, via `compute_format_compliance(selected, rendered)` |

### Why these are separate

The synthesizer LLM doesn't always honor the format hint. The reward still belongs to the *suggested* strategy (because that's the arm we pulled), but compliance lets us audit:

1. **Per-strategy compliance rate** — admin can ask: *"How often does the synthesizer honor `comparison_table`?"* Aggregate `format_compliance / count` over `ape_turn_record` grouped by `selected_strategy`.
2. **Instruction-text quality** — if a strategy has low compliance and low avg_reward, the synthesizer is probably ignoring the instruction. Time to refine the instruction text (Admin → Instructions).
3. **Honest reward attribution** — if compliance is 0 but reward is high, the synthesizer found something better on its own; the bandit still credits the suggested strategy, but admin knows to investigate.

### Example rows

| selected_strategy | rendered_format | format_compliance | normalized_reward |
|---|---|---|---|
| `comparison_table` | `comparison_table` | **1** | +1.0 (thumbs_up) |
| `comparison_table` | `paragraph` | **0** | +1.0 (thumbs_up — user liked the paragraph anyway) |
| `pros_cons_table` | `paragraph` | **0** | -1.0 (thumbs_down) |
| `standard_llm` | `paragraph` | **1** | +0.5 (copy_save — standard_llm is always compliant) |

Row 2 is interesting: high reward, low compliance. The bandit still credits `comparison_table` (correctly — that was the arm we pulled), but the admin should refine the instruction text or accept that paragraph mode is fine here.

---

## Part 6 · Where the reference's tables map onto ours

The reference has 4 tables. Ours has 8 collections. Here's the mapping:

| Reference table | Our equivalent | Notes |
|---|---|---|
| **1. Turn Record** | `ape_turn_record` | Same role. We add `format_compliance` field, `reward_status` enum (PENDING / APPLIED / SKIPPED), and `attribution_bandit_pk + sk` (their `attribution_arm_id` made more explicit). |
| **2. Beta Distribution Table** | `ape_user_bandit_state` | Same role. We add `user_id_hash` to the key (personalization). We track `cached_ucb` directly — not α / β. We treat Beta(α, β) as visualization only. |
| **3. Signal Routing Table** | `ape_config` with `entity_type=signal_routing` | Same shape. Admin-editable via `/admin` with versioned audit. |
| **4. Reward Scale** | `ape_config` with `entity_type=reward_scale` | Same shape. Admin-editable. |
| *(implicit chat history)* | `ape_messages` | We made it explicit because of the privacy boundary — raw text lives ONLY here. |
| *(not present)* | `ape_admin_audit` | Captures every admin write with before/after for compliance. |
| *(would be queries on Turn Record)* | `ape_user_topic_interest` + `ape_topic_trend_daily` | Pre-computed analytics aggregates so dashboard reads are fast. |
| *(not present)* | `ape_user_directory` | Optional hash → display name + compliance gates (production: CRM-sourced). |

---

## Final verdict

The reference design is a **solid single-user UCB engine**. The flow control, gate logic, attribution, and reward weighting are correct. To turn it into a production multi-tenant product, the changes are:

1. **Add `user_id_hash` to the Beta Distribution Table's key** so each user learns independently. *(We did this.)*
2. **Make the learning update synchronous** so failures are observable rather than silently queued. *(We did this.)*
3. **Move admin tunables (instructions, policies, signals, rewards) into a versioned config table with audit** so changes are reversible. *(We did this.)*
4. **Decouple raw chat text from learning state** so the analytics layer can't accidentally leak it. *(We did this.)*
5. **Pre-compute analytics aggregates** so dashboard reads don't scan Turn Record on every page load. *(We did this.)*
6. **Rename "Beta Distribution Table" to something UCB-honest** (we call ours `ape_user_bandit_state`). The α / β values are a visualization device; the actual algorithm reads count + avg_reward + cached_ucb.

The reference design is the **right starting point**; `ape_modulor_production` is what it looks like after those six changes are applied.

---

## See also

- [01 · Architecture overview](./01-architecture-overview.md) — full schema definition
- [02 · Runtime paths](./02-runtime-paths.md) — Path A and Path B in code-level detail
- [03 · Admin config](./03-admin-config.md) — the admin tunable surface
- [09 · API reference](./09-api-reference.md) — every HTTP endpoint
