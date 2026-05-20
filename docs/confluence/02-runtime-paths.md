# 02 - Runtime Paths

> Path A generates a response and records attribution. Path B buffers feedback
> signals and finalizes learning. The shared ledger is `ape_turn_record`; the
> personalized learning table is `ape_user_bandit_state`.

---

## Path A - `/turn`

`POST /turn` handles one user message end to end.

```text
1. Ensure session_id
   If the request omits session_id, the orchestrator mints one.

2. Load history
   Read recent messages from ape_messages by session_id.

3. Append user message
   Write raw user text to ape_messages before generation.

4. Classify
   LLM returns:
     intent
     topic
     signal

5. Finalize previous pending response
   If this user/session has a recent PENDING response:
     - append classifier signal as source=llm if it is not no_signal
     - append session_continue as source=derived if previous response age < 5 min
     - run finalization:
         composite detection
         atomic resolver fallback
         strongest format-relevant reward selection
         CAS PENDING -> APPLIED
         bandit update if reward exists
         UCB cache refresh for the whole cell

6. Validate intent
   Intent must be ACTIVE in ape_config. Unknown or inactive intents become
   unmapped.

7. Resolve candidate strategies
   Lookup order:
     - exact policy: domain + intent + topic
     - default topic policy: domain + intent + _default
     - hardcoded fallback catalog

8. Load active instructions
   Each candidate strategy needs an ACTIVE instruction. Missing instructions
   fall back to safe defaults where available.

9. Load or create bandit cell
   The cell is keyed by user_id_hash + domain + intent + topic.
   One row exists per strategy.

10. Select strategy
    UCB selects argmax(cached_ucb).
    Unpulled arms have cached_ucb = 999.0 for natural exploration.

11. Generate answer
    The synthesizer receives the selected strategy instruction.

12. Measure format compliance
    format_compliance = 1 if rendered_format matches selected_strategy's
    expected format; otherwise 0.

13. Write PENDING turn record
    The row includes response_id, selected_strategy, rendered_format,
    attribution_bandit_pk/sk, and initial pending_signals:
      - format_compliance_pass, or
      - format_compliance_fail

14. Append assistant message
    Assistant message stores response_id so the UI can attach feedback to the
    exact response.
```

The response body returns `response_id`. The client must echo that id when it
posts feedback.

---

## Path A Streaming - `/turn/stream`

`POST /turn/stream` has the same learning semantics as `/turn`. The difference
is delivery: it returns Server-Sent Events while the synthesizer is producing
tokens.

Event sequence:

| Event | When | Payload highlights |
|---|---|---|
| `metadata` | After strategy selection, before token streaming | `response_id`, `session_id`, `intent`, `topic`, `selected_strategy`, `candidate_strategies` |
| `delta` | Many times during generation | Raw text chunk from the LLM |
| `done` | After generation and writes complete | Final `answer`, `rendered_format`, `format_compliance`, `selection`, `classification`, timings |
| `error` | If streaming fails | Error message |

The streaming path preallocates `response_id` before token streaming so the UI
can associate live feedback controls with the response as soon as metadata
arrives.

---

## Path B - `/feedback`

`POST /feedback` accepts an explicit UI signal for one `response_id`.

```text
1. Validate target
   - response_id must exist
   - user_id must hash to the response owner
   - reward_status must still be PENDING

2. Validate signal
   The signal must exist in ACTIVE signal_routing config.

3. Append to pending_signals
   UI feedback is appended as:
     { signal, source: "ui", ts }

4. Decide whether to finalize now
   Finalize immediately if:
     - response age >= 5 seconds, or
     - pending signal count >= 3, or
     - signal is explicit/strong:
         format_change_request
         format_keep_request
         content_correction
         regenerate_click
         thumbs_down

   Otherwise return status=queued. The response remains PENDING until another
   signal arrives or the next /turn finalizes it.

5. Finalize response
   - detect composite pattern first
   - otherwise resolve atomic signals:
       UI signals outrank LLM signals
       LLM signals outrank derived-only signals
   - record the winning label in ape_turn_record.signal
   - separately scan all buffered signals plus the winner
   - choose the highest absolute format-relevant normalized reward
   - CAS reward_status from PENDING to APPLIED
   - update the attributed bandit arm if a reward exists
   - refresh cached_ucb for every arm in the cell
```

This design protects bandit learning from noisy satisfaction clicks. For
example, `thumbs_up` can be the final analytics label, but because it has no
format category it does not by itself update the bandit. A co-fired
`format_compliance_pass` can still supply a +0.5 format reward.

---

## Feedback Statuses

| Status | Meaning |
|---|---|
| `queued` | Signal was buffered; finalization will happen later |
| `applied` | Response finalized and bandit row updated |
| `applied_no_bandit_update` | Response finalized, but no format-relevant reward existed |
| `rejected` | Response missing, wrong user, already finalized, or CAS race lost |
| `skipped` | Signal is unknown and was not buffered |

---

## Reward State Machine

```text
PENDING
  |
  | queued feedback appends pending_signals
  v
PENDING
  |
  | finalizer applies a label and optional reward
  v
APPLIED

PENDING
  |
  | explicit skip path for non-applicable responses
  v
SKIPPED
```

A PENDING response is safe. It means APE is waiting for more evidence or the
next user turn. It does not corrupt the bandit.

---

## Why UCB Cache Refresh Touches the Whole Cell

The UCB exploration term depends on total pulls in the cell:

```text
ucb = avg_reward + c * sqrt(2 * ln(total_cell_pulls) / arm_count)
```

When one arm receives a reward, the total pull count changes, so every arm's
`cached_ucb` can change. Path B refreshes the whole cell after a bandit update.

---

## See Also

- [03 - Admin config](./03-admin-config.md)
- [09 - API reference](./09-api-reference.md)
