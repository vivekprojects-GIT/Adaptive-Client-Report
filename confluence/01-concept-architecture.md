# 01 · Concept & Architecture

## 1.1 Problem & Approach

Most assistants vary *what* they say. APE varies *how* they say it and learns
the shape that lands best for each kind of question and each user.

- **Why format, not content?** Content is the LLM's job. Format is a cheap,
  measurable lever with a small action space (a handful of shapes per intent),
  which makes online learning tractable and safe.
- **Why a bandit (not A/B testing)?** A bandit explores *and* exploits
  continuously per cell, adapts as preferences drift, and needs no fixed test
  windows. UCB gives principled exploration with one tunable constant `c`.
- **Unit of learning:** the cell `(user, domain, intent, topic)`. Each cell has
  its own arms and its own learned distribution.

## 1.2 System Architecture

```
        React SPA (Vite)
              │  /turn /turn/stream /feedback /config/* /analytics/*
              ▼
        FastAPI (ape/api.py)
   ┌──────────┼─────────────────────────────┐
   ▼          ▼              ▼                ▼
Orchestrator  MongoStore   Anthropic        RagStore (Chroma)
(ape/         (Atlas)      (classifier +    local MiniLM
 orchestrator)             synthesizer)     embeddings
```

- **Path A (serve):** `handle_turn` / `handle_turn_streaming` — classify → resolve
  candidate strategies → UCB select → RAG retrieve → synthesize → write PENDING turn.
- **Path B (learn):** `apply_feedback` + `_finalize_response` — pool signals →
  detect composite → resolve label → compute max-magnitude reward → update cell.
- **Analytics** read MongoDB aggregates (never the runtime path).

## 1.3 Data Model (MongoDB Atlas)

| Collection | Holds |
|---|---|
| `config` (`APE_Config`) | intents, strategies, policies, signal-rules, reward-scale, instructions, offers |
| `ape_user_bandit_state` | one doc per `(user, domain, intent, topic, strategy)`: `count`, `total_reward`, `avg_reward`, `cached_ucb` |
| `ape_turn_record` | one doc per response: intent/domain/topic, selected/rendered format, `pending_signals`, reward |
| `ape_messages` | conversation history (raw text lives here, deletable) |
| `ape_user_topic_interest` | derived per-user topic profile (recompute) |
| `ape_topic_trend_daily` | derived daily `(date, domain, topic)` activity (recompute) |

**Cell key:** `(user_id_hash, domain, intent, topic)` → arms = strategies.
Strategies carry instruction text plus `format_type` metadata; the bandit
learns the strategy, not a nested format. See `11-database-design.md` for the
DB-first `/turn` flow, including unknown-intent fallback to `unmapped`.
Privacy: raw queries are **never** aggregated; only normalized fields.

## 1.4 Glossary & Conventions

- Intents are a closed set (PascalCase). Topics are open vocabulary
  (snake_case, canonical).
- Reward scale: strong `±1.0`, weak `±0.5`, `None` = no bandit update.
- Config status: `ACTIVE` is what serves; `DRAFT`/`INACTIVE` don't.
- IDs: `response_id`, `message_id`, `user_id_hash` (`u_<16hex>`).
