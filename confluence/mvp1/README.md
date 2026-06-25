# APE Modulor — MVP 1 Documentation

**One sentence:** MVP 1 is a **headless decision + learning API** that picks the
best **answer format** for each **(user, intent)** pair and learns from signals.
The caller does its own classification and synthesis; APE just selects the
format and learns. **No UI** — admin and analytics are JSON endpoints too.

## Tech stack (MVP 1)

| Layer | Choice |
|---|---|
| Language / framework | **Python + FastAPI** |
| Compute | **AWS Lambda** (FastAPI via an ASGI adapter) + API Gateway |
| Datastore | **Amazon DynamoDB** |
| Learning | **UCB** bandit, with **round-robin cold start** |
| Cell key | **(user_id_hash, intent)** only |

## How MVP 1 is wired

No orchestrator layer, no frontend, no LLM calls inside APE. **One** FastAPI
endpoint on **AWS Lambda**. Each request carries **both** the new
`classification` and the `signals` for the previous answer; the handler **splits
the JSON** and runs **two processes**:
- **Reward** — uses `signals` + the previous turn's stored details to update the
  previous `(user, intent, strategy)` arm.
- **Select** — uses the new `classification` to pick a format (round-robin while
  cold, UCB once warm), opens a **PENDING turn** (`turn_id`), and returns the
  **selected strategy + format instruction + turn_id**.

```
POST /turn  {user_id, session_id, classification, feedback:{previous_turn_id, signals}}
            │
            ├─ Process 1 (Reward): signals + previous turn → update previous arm
            └─ Process 2 (Select): classification → new strategy + new PENDING turn
            │
            ▼
            {turn_id, selected_strategy, format_instruction, session_id, user_id}
```

## What's IN (MVP 1)

- A UCB bandit keyed on **(user_id, intent)**, with **round-robin cold start**
- **One endpoint** that splits each request into a Reward process and a Select process
- Strategy selection from a **caller-provided classification**, returning the format instruction
- A **PENDING turn** record (`turn_id`) that ties the next request's signals back to the right arm
- **Admin API** (JSON) — manage intents & strategies, view/reset bandit state
- **Analytics API** (JSON) — per (user, intent) format performance + rewards

## What's OUT (MVP 1)

| Not in MVP 1 | Notes |
|---|---|
| Chat UI / any frontend | API-only; the consumer renders the answer |
| Dashboard / charts | Analytics is JSON; the consumer visualizes if it wants |
| Topic in the cell key | MVP 2 |
| Domain detection + RAG | MVP 3 |
| Orchestrator abstraction, policies, offers | later |

## Page tree

| File | Page |
|---|---|
| `01-scope-and-architecture.md` | The (user, intent) cell + the headless API flow |
| `02-data-model.md` | Collections + the bandit cell schema |
| `03-fastapi-flow.md` | The single `/turn` endpoint split into Reward + Select |
| `04-admin.md` | Admin **API** — manage intents/strategies, bandit state |
| `05-analytics.md` | Analytics **API** — format performance per (user, intent) |
| `06-integration-deploy.md` | How a consumer integrates, tests, deploy, done |

> Cell key in MVP 1 is `(user_id_hash, intent)`. Later versions only widen this
> key (add topic, then domain) — the flow itself stays the same.
# Historical Reference

These pages describe the earlier DynamoDB MVP1 design. The current production
app uses MongoDB and is documented in `../11-database-design.md`.
