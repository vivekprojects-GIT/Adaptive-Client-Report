# 09 · Testing & Quality

## 9.1 Test Suite

- Run: `python -m pytest -q` (currently **14 tests**).
- Uses **mongomock** (monkeypatched `MongoClient`) so tests need no real Atlas.
- Coverage highlights:
  - signal routing / reward resolution (composite + atomic, max-magnitude reward)
  - bandit selection + cold-start `999`
  - streaming turn flow: seed cells, finalize previous response, apply reward
  - config seeding / status flips
- LLM calls are monkeypatched in tests (`classify_and_detect`,
  `generate_response_stream`); their fakes must match current signatures
  (e.g. accept the `context` kwarg, return a `domain`).

## 9.2 Mock / Demo Data

Two helper scripts (run with `PYTHONPATH=.`):

- `scripts/drive_demo_traffic.py` — sends real multi-turn questions across the
  four domains at the live Space, then recomputes and prints per-domain strategy
  performance. Good for an end-to-end smoke test.
- `scripts/seed_mock_analytics.py` — writes **differentiated** `bandit_state`
  cells + dated `turn_record` docs directly to Atlas (HIGH/MEDIUM/LOW spreads,
  multiple users, varied signals), then `recompute_all`. Makes the dashboard
  show realistic per-domain adaptation without waiting for organic traffic.

**Cleanup:** mock docs carry `{"mock": True}` — delete by that tag, or clear the
mock users via `DELETE /admin/clear-user/{id}`. The seeder wipes prior mock docs
on each run (idempotent).
