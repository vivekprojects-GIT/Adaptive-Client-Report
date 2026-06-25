# MVP 1 · Analytics API

A set of **read-only JSON endpoints** (no dashboard) that answer one question:
**is the bandit learning a better format for each (user, intent)?** Everything is
computed on the fly from `ApeTurnRecord` and `ApeBanditState` (DynamoDB `Scan`,
or a GSI on `intent`) — no extra pipeline and no UI in MVP 1. A consumer can
visualize the JSON if it wants.

## What the endpoints return

### 1. Strategy performance (the headline)
For a chosen scope (all users, or one user) and each intent, show every format
with its score:

| Intent | Strategy (format) | Pulls | Avg reward | Tier |
|---|---|---|---|---|
| Comparison | comparison_table | 14 | +0.78 | HIGH |
| Comparison | standard_llm (baseline) | 9 | +0.20 | MEDIUM |
| Comparison | bullet_contrast | 5 | −0.15 | LOW |

- **Tier:** HIGH ≥ 0.60 · MEDIUM ≥ 0.0 · LOW < 0.0 · EXPLORING (too few pulls).
- **Baseline:** `standard_llm` is marked so you can see whether structured
  formats beat "let the LLM decide".

### 2. Intent mix
How many turns landed in each intent over the window — shows what users actually
ask, and where there's enough data to trust the scores.

### 3. Signal mix
Counts of the signals collected (thumbs_up/down, format_change_request,
deeper_question, format_compliance_pass/fail, …) — the raw material of rewards.

### 4. Per-user lookup
Enter a `user_id` → see that user's intents and which format is winning for each.

## Endpoints

| Endpoint | Returns |
|---|---|
| `GET /analytics/strategy-performance?user_id=` | per-(intent, strategy) pulls + avg_reward + tier |
| `GET /analytics/intent-mix?days=` | turn counts per intent |
| `GET /analytics/signal-mix?days=` | counts per signal |

## How to read "is it adapting?"
- A structured format consistently above `standard_llm` for an intent = the
  bandit is earning its keep.
- Different users preferring different formats for the same intent = real
  per-user personalization.
- Rows still in **EXPLORING** just need more turns/feedback.

## Notes

- All responses are JSON; there is no analytics dashboard in MVP 1.
- The tables above describe the **shape of the JSON**, not a screen.
- Scope/window are query params (`?user_id=`, `?days=`); the consumer decides
  how (or whether) to visualize the result.
