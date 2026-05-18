# 02 · Runtime Paths

> Path A handles **selection + render** on every `/turn`. Path B handles **reward attribution** on every `/feedback`. They share state through `ape_turn_record` (the response ledger) and `ape_user_bandit_state` (the personalized arms).

---

## Path A — `/turn` (generate + select)

```
USER sends query
    │
    ▼
1. append user message to ape_messages
       (so audit happens even if generation fails)
    │
    ▼
2. classifier LLM call
       input:  query + recent history
       output: { intent, topic, signal }
    │
    ▼
3. validate intent
       get_active_config("intent", intent) — must be ACTIVE
       if missing → coerce to "unmapped"
    │
    ▼
4. resolve candidate strategies
       _resolve_candidate_strategies(intent, topic):
         a. policy lookup for (domain, intent, topic) AND status=ACTIVE
         b. fallback to (domain, intent, "_default")
         c. fallback to INTENT_STRATEGIES[intent]  (hardcoded catalog)
    │
    ▼
5. load active instructions
       for each candidate strategy:
         get_active_config("instruction", strategy_id) → version + text
    │
    ▼
6. load/create bandit cell
       get_or_create_bandit_cell(user_hash, domain, intent, topic, strategies)
         lazy-creates rows with cold-start values:
           count=0, avg_reward=0.5, cached_ucb=999.0
    │
    ▼
7. UCB selection
       select_strategy_from_rows(rows) — argmax(cached_ucb)
       Cold-start arms (cached_ucb=999.0) get picked first → exploration.
    │
    ▼
8. synthesizer LLM call
       input:  query + history + instruction_text for selected strategy
       output: { rendered_format, answer }
    │
    ▼
9. compute format_compliance
       compute_format_compliance(selected_strategy, rendered_format)
       → 0 or 1
    │
    ▼
10. write PENDING turn_record
        response_id (UUID), user_id_hash, session_id, ts,
        intent, topic, selected_strategy, rendered_format, format_compliance,
        attribution_bandit_pk = { user_hash, domain, intent, topic }
        attribution_bandit_sk = strategy
        ucb_at_selection, instruction_version,
        reward_status = PENDING
    │
    ▼
11. append assistant message to ape_messages
        (with response_id for join)
    │
    ▼
RETURN { response_id, answer, rendered_format, selected_strategy }
```

### What the client receives

```json
{
  "response_id": "resp_4f1a92e8...",
  "session_id":  "sess_e2d1...",
  "answer":      "| Feature | Roth IRA | Traditional IRA |\n|...",
  "rendered_format": "comparison_table",
  "selected_strategy": "comparison_table",
  "strategies_available": ["standard_llm", "comparison_table", "pros_cons_table", "bullet_contrast"],
  "ucb_at_selection": 1.522,
  "intent": "Comparison",
  "topic":  "roth_vs_traditional_ira"
}
```

The `response_id` is **the** key the client must echo back when sending feedback.

---

## Path B — `/feedback` (apply reward)

```
USER clicks 👍 (or 👎, copy, regenerate, …)
    │
    ▼
1. classify signal
       signal_routing config maps the raw signal to:
         format_category   ∈ {strong_positive, weak_positive, ...}
         content_category  ∈ {...}
       Each axis is independent — a signal can affect format only,
       content only, both, or neither.
    │
    ▼
2. compute normalized_reward
       reward_scale config maps each category to a value in [-1, +1].
       For format-axis updates we use format_category's normalized reward.
    │
    ▼
3. atomic mark APPLIED
       store.mark_response_rewarded(response_id, user_id_hash, signal,
                                    reward_category, normalized_reward)
       Conditional update on:
         response_id matches AND
         user_id_hash matches AND
         reward_status == PENDING
       This rejects:
         • Wrong response_id (nothing matches)
         • Cross-user reward injection (user_hash mismatch)
         • Double rewards (status already APPLIED)
    │
    ▼
4. read attribution
       From the just-updated turn_record:
         attribution_bandit_pk → (user_hash, domain, intent, topic)
         attribution_bandit_sk → strategy
    │
    ▼
5. update bandit row
       update_strategy_reward(pk, sk, reward):
         count       += 1
         total_reward += reward
         avg_reward   = total_reward / count
       (atomic increment + recompute)
    │
    ▼
6. recache UCB for the WHOLE cell
       refresh_cell_ucb_cache(pk):
         N = sum of count across all strategies in the cell
         for each strategy s in cell:
           if s.count == 0:
             s.cached_ucb = 999.0
           else:
             s.cached_ucb = s.avg_reward + c * sqrt(2 * ln(N) / s.count)
         (c is the exploration constant from the policy row)
    │
    ▼
RETURN { status: "applied", reward, new_avg }
```

### Why we recache the whole cell

UCB's exploration bonus depends on `N` (total pulls across all arms in the cell). When ANY arm's count changes, EVERY other arm's UCB changes. Caching the result lets selection (Path A) stay O(1) — just `argmax(cached_ucb)`.

---

## Idempotency & safety

| Concern | How it's handled |
|---|---|
| Same response_id rewarded twice | Atomic `update_one` with `reward_status: PENDING` filter — second update modifies 0 rows |
| User A submits feedback for User B's response | `user_id_hash` is part of the filter — mismatch → 0 rows updated |
| User submits feedback for a fabricated response_id | No row matches → 0 rows updated → return clean error |
| Generation fails after writing user message | User message persists; no `turn_record` is written; nothing to reward |
| Synthesizer returns wrong format | `format_compliance=0` — bandit still gets the reward but compliance is auditable |

---

## State machine

```
turn_record.reward_status

    PENDING ─────► APPLIED       (Path B success)
       │
       ├──────────► SKIPPED      (signal known but not format-relevant —
       │                          e.g. session_abandon)
       │
       └──────────► PENDING       (Path B failed — never modified)
```

A response stuck in PENDING is harmless; it just means the bandit didn't learn from that turn.

---

## See also

- [03 · Admin config](./03-admin-config.md) — what `signal_routing` and `reward_scale` look like
- [09 · API reference](./09-api-reference.md) — `/turn` and `/feedback` request/response shapes
