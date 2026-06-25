# MVP 1 · Scope & Architecture

## The idea, in plain words

For every **user** and every **intent** (the *type* of question they asked),
learn which **answer format** they respond to best. The LLM writes the content;
the bandit picks the shape (one-liner, table, numbered steps, …).

## The "cell" — the thing that learns

```
cell key = (user_id_hash, intent)
arms     = the candidate formats allowed for that intent
```

Example: `(alice, Comparison)` has arms `comparison_table`, `bullet_contrast`,
`standard_llm`. The bandit keeps a score per arm and learns which one Alice
likes for comparison questions. No topic, no domain in MVP 1.

## Architecture — a decision + learning service

APE is **not** the chatbot. The caller runs its own intent classification and
its own answer synthesis. APE just **picks the format** and **learns**. The
caller sends the classification in; APE returns the chosen strategy + format
instruction; later the caller sends signals back to teach it.

```
        API consumer (does its own classify + synthesize)
                      │  JSON: classification + signals (one request)
                      ▼
              API Gateway  →  AWS Lambda
            ┌──────────────────────────┐
            │   FastAPI /turn handler   │   splits JSON → Reward + Select
            └──────────────────────────┘
                      │
                      ▼
                  DynamoDB
        (ApeConfig · ApeBanditState · ApeTurnState)
                      │
                      ▼
        JSON: selected_strategy + format_instruction + turn_id + session_id + user_id
```

No orchestrator class, no frontend, no LLM calls inside APE. Admin and Analytics
are additional JSON endpoints on the same API — not screens.

## One endpoint, two processes

There is a single endpoint, `POST /turn`. Every request carries **both** the new
`classification` and the `signals` for the previous answer. The handler splits
the JSON and runs two independent processes:

**Process 1 — Reward** (only if `feedback` is present)
Uses `signals` + the previous turn's stored details. The three reward inputs:
- **signals** — in the request,
- **classification** (which `(user, intent)` cell) — on the stored previous turn,
- **previous strategy** (which format to reward) — on the stored previous turn.

APE reads the previous turn by `previous_turn_id`, computes the reward, updates
that arm, and marks the turn `APPLIED`.

**Process 2 — Select** (always)
Uses the new `classification`: read the `(user, intent)` cell, pick a format
(round-robin while cold, UCB once warm), write a fresh **PENDING turn**
(`turn_id`), and return `{turn_id, selected_strategy, format_instruction, …}`.

The two processes share nothing but the request envelope. The `turn_id` returned
now becomes the next request's `feedback.previous_turn_id`. See `03` for the full
query flow.

## Why start here

Fewest moving parts, no orchestrator to build, and the cell key is tiny so you
see learning quickly. Topic, domain, and RAG are **additive** later — you widen
the key and add a retrieval step; nothing here gets rewritten.
