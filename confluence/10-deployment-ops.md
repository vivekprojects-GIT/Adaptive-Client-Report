# 10 · Deployment & Ops

## 10.1 Docker Build

Two-stage `Dockerfile`:

1. **frontend-build** (`node:20-alpine`) → `npm ci` + `npm run build` → `dist/`.
2. **runtime** (`python:3.12-slim`) → install deps, copy `ape/` + built `dist/`,
   run as non-root `user` (uid 1000), `uvicorn ape.api:app` on `:7860`.

RAG-specific runtime requirements (lessons learned):
- `apt-get install libgomp1` — onnxruntime (Chroma's default embedder) needs it;
  without it every RAG call 500s.
- `APE_RAG_DIR=/home/user/.chroma` — `/app` is root-owned; the uid-1000 user
  can't write there.
- A build-time warm-up (`RagStore().ingest()`) pre-downloads the MiniLM model so
  the first request isn't blocked and RAG works even with restricted egress.

## 10.2 Hugging Face Space

- Space builds the image itself (so committing source is enough; `dist/` is
  gitignored and built in-image).
- Set secrets/env in the Space: `ANTHROPIC_API_KEY`, `APE_MONGO_URI`, etc.
- Build logs show `warm RAG: {...}` (build) and `[startup] RAG ingest counts`
  (boot).
- **Cache caveat:** after a deploy, hard-refresh (`Ctrl+Shift+R`) — a stale
  bundle in the browser will show old UI even though the server is current
  (compare the served `assets/index-*.js` hash to the build).
- FS is ephemeral → the Chroma store is re-seeded each boot (intentional).

## 10.3 Runbook / Troubleshooting

| Symptom | Check / fix |
|---|---|
| `/rag/*` returns 500 | onnxruntime/libgomp1 in image; `GET /rag/status` |
| Answers ignore the KB | domain detected as `general` (no RAG); confirm via `/rag/search` |
| UI looks old after deploy | browser cache → hard refresh; verify bundle hash |
| Empty analytics | run `POST /analytics/recompute`; ensure turns exist for the window |
| Reset a user / cell | `DELETE /admin/clear-user/{id}`, `DELETE /admin/bandit-state/cell` |

## 10.4 Decisions (ADR log)

Append one short entry per significant decision (context → decision → consequence):

- **No admin token in the UI** — auth gate removed; UI never prompts. The Space
  is a demo; protect via Space access if needed.
- **Drop `raw_reward`** — REWARD_SCALE stores normalized floats directly
  (`±1.0/±0.5/None`); seed `$unset`s the legacy field.
- **Multi-domain over finance** — detected domains are cricket/it/movies/travel;
  `finance` maps to `general` (no RAG). Topics are domain-aware canonicalized.
- **Local embeddings for RAG** — Chroma default MiniLM (no embedding API) to keep
  the synthesis path off external latency.
- **libgomp1 + writable RAG dir + model pre-bake** — required to run Chroma on
  the slim HF image.
- **Clustering deferred** — taxonomy backlog capture shipped; embedding/cluster
  canonicalization designed but not built (see `05`).
