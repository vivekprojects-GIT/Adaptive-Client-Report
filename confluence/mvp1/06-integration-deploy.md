# MVP 1 · Integration, Testing, Deploy

MVP 1 ships **no frontend**. A consumer integrates by calling the API and
rendering the answer itself.

## How a consumer integrates

The caller does its own classification and synthesis. It uses APE for the format
decision + learning, through **one endpoint** that carries both the new
classification and the previous answer's signals.

1. **Call `POST /turn`** with the new `classification` and (after the first turn)
   a `feedback` block `{previous_turn_id, signals}`.
2. APE **rewards** the previous turn (Process 1) and **selects** for the new one
   (Process 2) in the same call.
3. **Use the response** → `{turn_id, selected_strategy, format_instruction}`.
   Feed `format_instruction` into your own LLM to render the answer; keep
   `turn_id` to pass as `previous_turn_id` on the next call.

That's the whole contract: **one call per turn — it teaches and decides.**

### Call sequence
```
# first turn (no feedback yet)
POST /turn {user_id, session_id, classification:{intent:"Comparison"}}
           → {turn_id:"t_1", selected_strategy, format_instruction, ...}

# next turn — feedback on t_1 + classification for the new message
POST /turn {user_id, session_id,
            classification:{intent:"Definitional"},
            feedback:{previous_turn_id:"t_1", signals:["thumbs_up"]}}
           → {turn_id:"t_2", selected_strategy, format_instruction, ...}
```

## Endpoints recap

| Group | Endpoint |
|---|---|
| Core (reward + select) | `POST /turn` |
| Admin | `GET/POST /config/intents`, `GET/POST /config/strategies`, `POST /admin/seed`, `GET /admin/bandit-state`, `DELETE /admin/clear-user/{id}` |
| Analytics | `GET /analytics/strategy-performance`, `/analytics/intent-mix`, `/analytics/signal-mix` |
| Ops | `GET /health` |

## Testing

- **Bandit math:** round-robin cold start (every arm shown once before UCB),
  UCB argmax selection, reward update (`count`, `avg_reward`, `cached_ucb`).
- **Loop test (offline):** with a local DynamoDB (DynamoDB Local / `moto`):
  seed → `POST /turn` (turn 1, no feedback) → `POST /turn` (turn 2 with
  `feedback.previous_turn_id` = turn 1) → assert the previous arm's `count` /
  `avg_reward` moved and turn 1 went `PENDING` → `APPLIED`.
- **Split test:** a request with both `classification` and `feedback` runs both
  processes; a request with only `classification` runs Select only.
- No LLM mocking needed — APE makes no LLM calls.

## Deploy (serverless)

- **AWS Lambda + API Gateway** run the FastAPI app via an ASGI adapter
  (e.g. Mangum: `handler = Mangum(app)`). API only — no static frontend.
- **Amazon DynamoDB** holds `ApeConfig`, `ApeBanditState`, `ApeTurnState`
  (on-demand capacity is fine for MVP 1).
- IAM: the Lambda role needs `dynamodb:GetItem/Query/UpdateItem/PutItem/Scan`
  on the three tables.
- Env vars: `APE_UCB_C`, `AWS_REGION`, and the three table names
  (`APE_CONFIG_TABLE`, `APE_BANDIT_TABLE`, `APE_TURN_TABLE`).
  (No `ANTHROPIC_API_KEY` — APE makes no LLM calls; the caller owns that.)
- Light package — no RAG / embedding dependencies in MVP 1.
- **Lambda cold start note:** this is infra (container spin-up) and is unrelated
  to the bandit's "cold start" (round-robin exploration). Keep the package small
  and use provisioned concurrency if p99 latency matters.

## Definition of Done (MVP 1)

1. `POST /turn` splits each request into **Reward** (previous turn) and
   **Select** (current turn) and runs both.
2. **Select** returns a bandit-chosen `selected_strategy` + `format_instruction`
   + a new `turn_id` for the caller-provided `(user, intent)` classification.
3. **Reward** updates the matching `(user, intent, strategy)` arm using
   **signals + the stored previous turn's classification + previous strategy**,
   and marks that turn `APPLIED`.
4. Round-robin cold start shows every format once before UCB takes over.
5. **Admin API** can manage intents/strategies and view/reset bandit state.
6. **Analytics API** returns, per (user, intent), which format is winning — and
   it visibly shifts with use.
7. No UI and no LLM calls inside APE.
