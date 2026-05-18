# 07 · Operations

> Run, recompute, seed, deploy.

---

## Local dev

### Backend
```bash
cd ape_modulor_production
python -m uvicorn ape.api:app --host 127.0.0.1 --port 7860 --log-level warning
```

Environment (from `.env`):
```
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5
APE_MONGO_URI=mongodb+srv://...
APE_MONGO_DB=ape
APE_DOMAIN=finance
APE_UCB_C=1.0
```

### Frontend
```bash
cd ape_modulor_production/frontend
npm run dev    # serves at :5173, proxies API calls to :7860
```

The Vite proxy in `vite.config.js` forwards: `/turn`, `/feedback`, `/health`, `/sessions/*`, `/users/*`, `/config/*`, `/admin/*` (regex `^/admin/` so the bare `/admin` SPA route is not eaten), `/analytics/*`.

---

## Seeding demo data

### Five named personas with distinct cognitive signatures
```bash
python scripts/seed_demo_users.py
```
Creates:
- Alex Chen — Action-ready · retirement planner · decision_card lover
- Maya Patel — Awareness · analogy / definition prefer
- Dan Mueller — Evaluation · comparison-table loyalist
- Riya Singh — `compliance_eligible=false` · friction on tax topics
- Sam Rodriguez — `do_not_contact=true` · broad explorer, low pulls

Each persona writes `ape_user_bandit_state` rows + matching `ape_turn_record` events + a `ape_user_directory` entry. The script then recomputes `ape_user_topic_interest` and `ape_topic_trend_daily`.

### The "demo_user" deep cell set
```bash
python scripts/seed_demo_facets.py
```
Heavier per-user activity (~70 turns over 6 cells) so the user-scoped facet view has rich data to render.

Both scripts are **idempotent** — they `delete_many` the user's prior bandit + turn rows before re-seeding.

---

## Recompute aggregates

### What recompute does
Reads `ape_turn_record` (last N days), upserts into:
- `ape_user_topic_interest` — per `(user, topic)` interest score + sub-scores
- `ape_topic_trend_daily` — per `(date, topic)` trend score

### Manual — admin UI
Click **"Recompute now"** in the Analytics page header. Takes ~13 s on the current dataset. The next reload shows fresh aggregates.

### Manual — CLI
```bash
python scripts/cron_recompute.py             # default 14-day window
python scripts/cron_recompute.py --days 30   # full 30-day backfill
python scripts/cron_recompute.py --quiet     # one-line log-scrapeable output
```

### Scheduled

#### Linux/macOS cron
```cron
# Hourly recompute of the last 24h (keeps dashboard near-real-time)
0 * * * * cd /path/to/ape_modulor_production && /usr/bin/python scripts/cron_recompute.py --days 1 --quiet >> /var/log/ape_recompute.log

# Nightly full rebuild over 30 days
30 2 * * * cd /path/to/ape_modulor_production && /usr/bin/python scripts/cron_recompute.py --days 30 --quiet >> /var/log/ape_recompute.log
```

#### Windows Task Scheduler
```cmd
schtasks /create /tn "APE hourly recompute" ^
  /tr "python C:\path\to\scripts\cron_recompute.py --days 1 --quiet" ^
  /sc HOURLY
```

#### GitHub Actions / GitLab CI (recommended)
```yaml
on:
  schedule:
    - cron: "0 * * * *"      # every hour
jobs:
  recompute:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: python scripts/cron_recompute.py --days 1 --quiet
        env:
          APE_MONGO_URI: ${{ secrets.APE_MONGO_URI }}
          APE_MONGO_DB:  ape
```

---

## Reload vs Recompute (the two-button design)

| Button | Latency | When | Cache impact |
|---|---|---|---|
| **Reload** | ~2 s | Re-fetch existing aggregates | Read-only |
| **Recompute now** | ~13 s | After lots of new chat activity | Rebuilds analytics collections |

> ⚠ **Page load does NOT auto-recompute.** It used to; we changed it so the page is fast by default. Admin opts into recompute when they need fresh aggregates.

The header shows:
```
Reloaded 4:45 AM · Recomputed 4:32 AM
```
in muted gray + green respectively, so the data freshness is always visible.

---

## Production deploy notes

### Single-process deploy
The FastAPI app at `ape.api:app` serves both the API and the built React SPA:

```bash
# 1. Build the frontend
cd frontend && npm run build      # produces frontend/dist/

# 2. Serve everything from FastAPI
python -m uvicorn ape.api:app --host 0.0.0.0 --port 7860
```

The SPA is mounted at `/assets`, and bare paths `/`, `/analytics`, `/admin` fall through to `index.html`. Unknown paths return 404 (no SPA fallback for arbitrary URLs).

### Mongo connection
- Atlas URIs (`mongodb+srv://...`) auto-enable `ServerApi("1")` for forward compatibility.
- The store creates all required indexes on startup via `apply_indexes(db)`.
- The DB driver is connection-pooled — long-lived `MongoStore` per process is fine.

### LLM client
- Uses the Anthropic Python SDK. Model from `ANTHROPIC_MODEL` env var (currently `claude-haiku-4-5`).
- Two LLM calls per `/turn`: classifier + synthesizer.

### Scaling considerations
- **Reads**: classifier + synthesizer LLM calls dominate latency. Bandit selection is sub-millisecond.
- **Writes**: every `/turn` writes 3 docs (`messages` + `bandit_state` upsert + `turn_record`). Every `/feedback` writes 1 update + cell-wide UCB recache.
- **Recompute cost**: scales linearly with active `ape_turn_record` rows in the window. The 13 s on the current dataset (~260 turns) → roughly 1 s per 20 turns. Move to background workers (Celery / RQ / GitHub Actions cron) before the dataset crosses ~10k turns.

---

## Troubleshooting

| Symptom | Check |
|---|---|
| `/analytics/cognitive-facets` returns empty for a user | They have no bandit_state rows. Either no turns yet, or the user_id you passed doesn't hash to a stored hash. |
| "Failed to load: 404 Not Found" inside dashboard | Vite proxy missing for that path. Check `vite.config.js` — `/analytics/*` and `^/admin/` should both be there. |
| Recompute is slow | Indexes missing on `ape_turn_record`. Verify via `db.ape_turn_record.getIndexes()` — should have `by_user_time` and `by_session_time`. |
| ObjectId serialization error in audit | Fixed (`_strip_mongo_id` in `log_admin_action`). If you see this again on a brand-new install, run a one-off `db.ape_admin_audit.updateMany({}, {$unset: {"before._id": ""}})`. |
| Admin pause doesn't take effect | Verify the runtime read goes through `get_active_config` / `list_active_config` / `get_policy_strategies` — those filter on `status=ACTIVE`. Direct `config.find()` calls would bypass the gate. |

---

## See also

- [09 · API reference](./09-api-reference.md) — every admin/ops endpoint
- [08 · Privacy & compliance](./08-privacy-and-compliance.md) — what to enforce in production
