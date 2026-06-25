# 03 · Backend Core (build in this order)

## 3.1 Config Layer

All tunable behavior is data in the `config` collection, edited via the Admin UI
or `/config/*` endpoints and managed by `ConfigManager` / seeded by `seed_all`.

Entity types: `intent`, `strategy`, `policy`, `signal-rule`, `reward-scale`,
`instruction`, `offer`. Each doc has `entity_type`, `entity_id`, `status`
(`ACTIVE`/`DRAFT`/`INACTIVE`), and a version where relevant. Only `ACTIVE` docs
serve. Lookups are exact-match (`get_active_config(type, id)`).

## 3.2 Strategy Catalog & Instructions

- `ape/strategies/catalog.py` — `INTENT_STRATEGIES`: candidate formats per intent.
  `standard_llm` is first for every intent (the safe, no-constraint baseline).
- `ape/strategies/instructions.py` — `STRATEGY_INSTRUCTIONS`: one **format-only**
  sentence per strategy (e.g. `comparison_table` → "Format as a markdown table…").
  These are domain-neutral by design, so they work across all domains.
- Strategy config in Mongo owns format compliance: `format_type` is the primary
  target and `accepted_rendered_formats` lists acceptable rendered labels.
  Runtime compliance reads the active strategy row, not a hardcoded format map.

## 3.3 Signals & Reward Scale

- **Catalog** (`ape/signals/routing.py`): ~25 signals across sources — UI
  (thumbs/copy/regenerate), LLM-detected (format_change_request, deeper_question,
  …), derived (format_compliance_pass/fail, session_continue/abandon), and
  composites.
- **Reward scale** (`ape/signals/reward_scale.py`): `strong ±1.0`, `weak ±0.5`,
  `None` = no update.
- **Buffered resolver** (`ape/signals/resolver.py`, `composites.py`): signals
  pool in `pending_signals[]`; at finalize, detect a composite → resolve a label
  → reward = the **max-magnitude format signal** (never summed, bounded `[-1,1]`).
- Decoupling: the resolver's *label* and the bandit *reward* are separate, so a
  thumbs-up doesn't erase the format-compliance evidence.

## 3.4 Bandit (UCB)

- Formula: `cached_ucb = avg_reward + c·√(2·ln N / count)` (`ape/bandit`).
- **Cold start:** an untried arm gets `cached_ucb = 999.0` so every format is
  sampled once before exploitation.
- **Selection:** `select_strategy_from_rows` = argmax(cached_ucb), deterministic
  tie-break by strategy name.
- **Merge:** two cells combine losslessly — sum `count` and `total_reward`,
  recompute `avg`. (Used by clustering housekeeping — see `05`.)

## 3.5 The Classifier

One Claude call (`ape/llm/classifier.py`, prompt in `prompts.py`) returns
`intent`, `intent_confidence`, `unmapped_name`, **`domain`**, `topic`, `signal`.
Output is normalized to closed vocabularies (alias maps + heuristic rescue for
"what is X" / "X vs Y"). Unknown intent → `unmapped`; unknown domain → `general`.
Topic is canonicalized **domain-aware** (finance whitelist vs slugify).

## 3.6 The Synthesizer

`ape/llm/synthesizer.py` builds a system prompt from the strategy instruction +
optional retrieved context, calls Claude (streaming or not), and parses a JSON
wrapper `{"rendered_format","response"}`. Falls back to a per-strategy default
format if the wrapper is malformed.

## 3.7 Orchestrator

`ape/orchestrator.py` is the spine.

**Path A — `handle_turn` / `handle_turn_streaming`:**
A0 flush previous pending response · A1 check DB intent and fall back to
`unmapped` when missing/inactive · A2 resolve active policy strategies
(`topic` → `_default`) · A3 verify strategy
rows are ACTIVE and load strategy-owned formats · A4 load/lazy-create bandit cell ·
A5 round-robin/UCB select and bump count · A5b RAG retrieve · A6 append accepted
user message · A7 synthesize with active instruction · A8 compute compliance
from `accepted_rendered_formats` · A9 write PENDING turn.

**Path B — `apply_feedback` + `_finalize_response`:** append signal to the
turn's pool, eager-finalize when an explicit/strong signal arrives → composite
detection → resolver label → max-magnitude reward → update the bandit cell.
