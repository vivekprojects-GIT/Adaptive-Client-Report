# 07 - Operations

> How to run, seed, verify, recompute, and deploy APE.

---

## Required Environment

Create `.env` from `.env.example` and set:

```bash
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5
APE_MONGO_URI=mongodb+srv://...
APE_MONGO_DB=ape
APE_DOMAIN=finance
APE_UCB_C=1.0
APE_ADMIN_TOKEN=<long random secret>
```

`APE_ADMIN_TOKEN` is required for `/config*`, `/admin/*`, and `/analytics/*`.
Without it, protected routes return `503`.

---

## Local Development

### Backend

```bash
cd ape_modulor_production
pip install -r requirements.txt
python -m uvicorn ape.api:app --host 127.0.0.1 --port 7860 --log-level warning
```

### Frontend

```bash
cd ape_modulor_production/frontend
npm install
npm run dev
```

Vite serves the app at `http://127.0.0.1:5173` and proxies API calls to
`http://127.0.0.1:7860`.

Proxy families:

```text
/turn
/turn/stream
/feedback
/health
/sessions/*
/users/*
/config/*
/admin/*
/analytics/*
```

The bare SPA routes `/`, `/admin`, and `/analytics` are not API routes.

---

## Admin Token in the UI

1. Set `APE_ADMIN_TOKEN` in the backend environment.
2. Open `/admin` or `/analytics`.
3. Enter the same token in the prompt.
4. The frontend stores it in `localStorage["ape.admin_token"]`.

To rotate the token:

1. Change the server secret.
2. Restart the backend.
3. Clear the browser token or enter the new one when prompted.

---

## Verification Commands

Run these after code changes:

```bash
python -m pytest -q
python tests/test_mongo.py
python -m compileall -q ape tests scripts
```

Run these after frontend changes:

```bash
cd frontend
npm run build
npm audit --omit=dev --audit-level=moderate
```

Useful security smoke checks:

```bash
# Health stays public
curl http://127.0.0.1:7860/health

# Protected API should reject missing token
curl -i http://127.0.0.1:7860/admin/audit

# Protected API should accept correct token
curl -H "X-APE-Admin-Token: $APE_ADMIN_TOKEN" \
  http://127.0.0.1:7860/admin/audit
```

---

## Seeding Demo Data

```bash
python scripts/seed_demo_users.py
python scripts/seed_demo_facets.py
```

`seed_demo_users.py` creates named demo personas, directory rows, turn records,
and bandit state. `seed_demo_facets.py` creates a richer per-user dataset for
the cognitive facets view.

The scripts are intended to be repeatable for demo data. They clear and replace
their target demo rows before reseeding.

---

## Recomputing Analytics

### CLI

```bash
python scripts/cron_recompute.py
python scripts/cron_recompute.py --days 30
python scripts/cron_recompute.py --days 1 --quiet
```

The cron script reads the database directly, so it does not need
`APE_ADMIN_TOKEN`. It does need MongoDB environment variables.

### Admin UI

Click **Recompute now** on `/analytics`. This calls:

```text
POST /analytics/recompute?days=N
```

Because it is an API call, it requires `APE_ADMIN_TOKEN`.

### Linux/macOS cron

```cron
0 * * * * cd /path/to/ape_modulor_production && /usr/bin/python scripts/cron_recompute.py --days 1 --quiet >> /var/log/ape_recompute.log
30 2 * * * cd /path/to/ape_modulor_production && /usr/bin/python scripts/cron_recompute.py --days 30 --quiet >> /var/log/ape_recompute.log
```

### Windows Task Scheduler

```cmd
schtasks /create /tn "APE hourly recompute" ^
  /tr "python C:\path\to\ape_modulor_production\scripts\cron_recompute.py --days 1 --quiet" ^
  /sc HOURLY
```

### GitHub Actions

```yaml
on:
  schedule:
    - cron: "0 * * * *"
jobs:
  recompute:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: python scripts/cron_recompute.py --days 1 --quiet
        env:
          APE_MONGO_URI: ${{ secrets.APE_MONGO_URI }}
          APE_MONGO_DB: ape
```

---

## Production Deploy

Single-process deployment serves both the API and built React assets:

```bash
cd frontend
npm run build

cd ..
python -m uvicorn ape.api:app --host 0.0.0.0 --port 7860
```

FastAPI serves:

| Route | Purpose |
|---|---|
| `/assets/*` | Vite build assets |
| `/` | React SPA |
| `/admin` | React SPA admin route |
| `/analytics` | React SPA analytics route |
| `/turn`, `/turn/stream`, `/feedback` | Chat APIs |
| `/config*`, `/admin/*`, `/analytics/*` | Protected operational APIs |

Deployment checklist:

- Set `ANTHROPIC_API_KEY`.
- Set `APE_MONGO_URI`.
- Set `APE_ADMIN_TOKEN`.
- Build frontend assets.
- Confirm Mongo indexes are created at startup.
- Run the verification commands.
- Configure scheduled analytics recompute.

---

## Scaling Notes

- `/turn` latency is dominated by classifier and synthesizer LLM calls.
- Bandit selection is cheap: load a small cell and choose `argmax(cached_ucb)`.
- `/feedback` finalization updates one turn record, one bandit row, and then
  refreshes cached UCB values for the whole cell.
- Analytics recompute is linear in `ape_turn_record` rows for the chosen window.
  Move it to cron or a worker before large production volumes.

---

## Troubleshooting

| Symptom | Check |
|---|---|
| `/admin/*`, `/config*`, or `/analytics/*` returns `503` | `APE_ADMIN_TOKEN` is missing in backend environment |
| Protected route returns `401` | UI/header token is missing or does not match |
| `/admin` or `/analytics` page loads but data fails | Enter admin token in the UI prompt |
| Session messages request returns `422` | Include `user_id` query param |
| Session messages look empty | `user_id` does not match the session owner hash |
| Cognitive facets empty for a user | User has no bandit rows yet or the id hashes differently than expected |
| Recompute is slow | Check `ape_turn_record` indexes and reduce `days` for interactive runs |
| Admin pause has no effect | Confirm runtime reads use ACTIVE-filtered config helpers |
| Frontend 404 for API path | Check Vite proxy entries |

---

## See Also

- [08 - Privacy and compliance](./08-privacy-and-compliance.md)
- [09 - API reference](./09-api-reference.md)
