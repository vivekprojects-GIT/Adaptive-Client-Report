# 08 · Analytics Deep-Dive

## 8.1 Aggregation Pipeline

`recompute_all(store, days)` (`ape/analytics/compute.py`) rebuilds two derived
collections from `ape_turn_record`:

- `ape_user_topic_interest` — per `(user, domain, topic)` interest score
  (frequency + recency + engagement + follow-up depth).
- `ape_topic_trend_daily` — per `(date, domain, topic)` turns, unique users,
  trend score (vs trailing average).

Jobs are idempotent (upsert by key); safe on demand or on a schedule. Headline
aggregates (platform overview, strategy performance) read `ape_turn_record` /
`ape_user_bandit_state` directly and don't require recompute; trend charts do.

## 8.2 Metrics Catalog

| View | Source | Reads as |
|---|---|---|
| Platform Overview | turns + bandit + interest | top topics, intent/signal mix, volume, funnel |
| Strategy Performance | bandit_state | per-format avg reward → tier (HIGH ≥0.60 / MEDIUM ≥0.0 / LOW <0.0 / EXPLORING <min_pulls) |
| Cognitive Facets | bandit_state | one facet per (intent, topic) cell + confidence tier |
| Customer Health | turns | retention cohorts + satisfaction + engagement segments |
| RAG Quality | turns | topics with high content-correction / re-ask rates |
| Instruction Quality | turns | (strategy, instruction_version) failure rates |
| Unmapped Intents | turns | taxonomy backlog (see `05`) |

## 8.3 Per-Domain Adaptation (how to read it)

The honest "is the bandit working?" check is **per-arm `avg_reward`, scoped to a
domain**, with **`standard_llm` as the baseline**:

- Pick a domain in the selector → Strategy Performance shows that domain's arms.
- A structured format consistently above `standard_llm` = the bandit is earning
  its keep for that domain; if `standard_llm` wins, the bandit correctly learned
  to let the model choose.
- Different winners across domains (e.g. `comparison_table` for IT,
  `numbered_steps` for travel) = genuine per-domain adaptation.
- Arms below `min_pulls` show as **EXPLORING** — they need more turns/feedback.
