# Deploying to a Hugging Face Space

The repo already builds as a Docker Space: one container compiles the React
app and serves it alongside the API on port 7860.

## 1. Create the Space

New Space → **Docker** SDK → blank template. Push this repo to it.

## 2. Secrets (Settings → Variables and secrets)

**Required**

| Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-…` — the LLM writes reports and answers |
| `APE_MONGO_URI` | your Atlas URI — templates, report types, audit |
| `APE_REPORT_TOKEN_SECRET` | a long random string — signs report links **and** advisor sessions |
| `ADVISOR_PASSWORD` | any password — gates the advisor/admin surfaces |
| `APP_BASE_URL` | `https://<user>-<space>.hf.space` — the base for emailed links |

**Email** (omit and sends write `.eml` files instead)

| Name | Value |
|---|---|
| `EMAIL_PROVIDER` | `gmail` |
| `EMAIL_FROM` | the Gmail address that granted consent |
| `GMAIL_TOKEN_JSON` | the **contents** of your local `token.json` |

**Optional**

| Name | Default | Notes |
|---|---|---|
| `DATABASE_URL` | SQLite on local disk | Point at hosted Postgres to make learning survive restarts |
| `SEED_ON_EMPTY` | `1` | Seed the synthetic book when the clients table is empty |
| `ANTHROPIC_MODEL` | `claude-haiku-4-5` | |

`APP_BASE_URL` is what fixes the problem you hit: without it links are minted
against the local host and only open on the machine that generated them.

## 3. What is public and what is not

| Path | Access |
|---|---|
| `/r/{report_id}?token=…` | **Open by design** — each link is HMAC-signed for one report and expires (14 days). This is what clients receive. |
| `/health` | Open — liveness probe |
| `/login` | Open — the gate's own door |
| everything else (`/`, `/admin`, all APIs) | **Advisor session required** |

Deny-by-default: a new endpoint is protected unless it is explicitly added to
`PUBLIC_PREFIXES` in `ape/deploy.py`. Without the gate, anyone finding the URL
could rewrite templates, spend your Anthropic credits and send email from your
Gmail account.

Locally, leaving `ADVISOR_PASSWORD` unset disables the gate entirely, so
development is unchanged.

## 4. Storage — read before demoing

Space disks are **ephemeral**: a rebuild or restart wipes SQLite, taking the
client book, generated reports **and everything the bandits have learned**
with it. Mongo config survives.

- Demo only → leave defaults. Each boot reseeds a fresh synthetic book;
  learning starts from zero.
- Learning must persist → create a free Postgres (Neon, Supabase) and set
  `DATABASE_URL`. No code change: the schema was written for exactly this
  swap.

## 5. Known gaps before real clients

- **No approval enforcement.** `DRAFT` status exists but nothing blocks
  sending an unapproved report. With real email live, this is the gap to
  close first.
- Reports are printed to PDF client-side; there is no server-rendered PDF
  artifact to file or attach.
- Only the account that granted Gmail consent can send, and Google keeps the
  app in Testing mode until verified — fine for demos, not for volume.
