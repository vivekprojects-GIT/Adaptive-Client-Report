# MVP 1 · API & Query Flow (one endpoint, two processes)

APE exposes **one** endpoint. Each request carries **both**:
- the **classification** of the new message (for selection), and
- the **signals** reacting to the **previous** answer (for reward).

The handler **splits the JSON** and runs **two independent processes**:
**(1) Reward** the previous turn, then **(2) Select** for the current turn.
No orchestrator class; it all runs in the FastAPI handler on AWS Lambda.

---

## The single endpoint — `POST /turn`

**Request**
```json
{
  "user_id": "u_ab12",
  "session_id": "s_123",

  "classification": { "intent": "Comparison" },     // → Process 2 (Select)

  "feedback": {                                       // → Process 1 (Reward)
    "previous_turn_id": "t_788",
    "signals": ["thumbs_up", "session_continue"]
  }
}
```
- On the **first** message of a session there is no `feedback` block — only
  Process 2 runs.
- `classification` drives selection; `feedback` drives the reward for the prior
  turn. They are handled separately.

**Response**
```json
{
  "turn_id": "t_789",
  "session_id": "s_123",
  "user_id": "u_ab12",
  "selected_strategy": "comparison_table",
  "format_instruction": "Format as a markdown table comparing the options across relevant dimensions."
}
```

---

## Process 1 — Reward (runs first, only if `feedback` is present)

Uses **signals + the previous turn's details**. The previous strategy and
classification are recovered from the stored PENDING turn.

```
1. GetItem ApeTurnState pk = feedback.previous_turn_id
      → user_id, intent, selected_strategy   (the arm to reward)
2. reward = signals → max-magnitude value in [-1, +1]   (strong ±1.0, weak ±0.5, none → skip)
3. UpdateItem ApeBanditState
      pk = "USER#<user_id>#INTENT#<intent>", sk = selected_strategy
      ADD count 1, ADD total_reward :reward
   (app-side: recompute avg_reward, refresh cached_ucb for the cell)
4. UpdateItem ApeTurnState pk = previous_turn_id
      SET status="APPLIED", signals=…, reward=…, applied_at=now
```

> The caller MAY also include `intent` + `previous_strategy` in `feedback`; APE
> verifies them against the stored turn. The stored turn is the source of truth.

## Process 2 — Select (always runs)

Uses the **new classification** to pick a format and open a fresh PENDING turn.

```
1. ApeConfig  → candidate strategies for classification.intent (+ format_instruction)
2. ApeBanditState → Query pk = "USER#<user_id>#INTENT#<intent>"  (all arms)
3. PICK:
     if any arm count == 0 → next untried arm in catalog order   (round-robin cold start)
     else                  → argmax(avg_reward + c·√(2·ln N / count))   (UCB)
4. turn_id = new id
   PutItem ApeTurnState { pk: turn_id, user_id, session_id, intent,
                          selected_strategy, format_instruction, status:"PENDING", created_at }
5. return { turn_id, session_id, user_id, selected_strategy, format_instruction }
```

---

## Why one endpoint with two processes

- The caller naturally has both pieces at request time: it just observed the
  user's reaction to the last answer (**signals**) and classified the new
  message (**classification**). Sending them together = one round trip.
- APE keeps them **cleanly separated internally**: reward touches the *previous*
  `(user, intent, strategy)` arm; select reads/writes the *current* cell + a new
  turn. They share nothing except the request envelope.
- The `turn_id` chain links them across calls: this call's `turn_id` becomes the
  next call's `feedback.previous_turn_id`.

## The three reward inputs (recap)

| Input | Source |
|---|---|
| **signals** | `feedback.signals` in the request |
| **classification** (which cell) | the previous turn's `intent` (stored) |
| **previous strategy** (which arm) | the previous turn's `selected_strategy` (stored) |
