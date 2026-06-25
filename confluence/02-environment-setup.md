# 02 · Environment & Setup

## 2.1 Prerequisites & Accounts

- **Python** 3.12, **Node** 20+
- **Anthropic API key** (Claude)
- **MongoDB Atlas** cluster + connection string
- (Local) ability to download the Chroma MiniLM ONNX model on first run

## 2.2 Local Dev Setup

1. **Backend deps:** `pip install -r requirements.txt`
   (includes `fastapi`, `anthropic`, `pymongo`, `chromadb`, `pytest`, `mongomock`).
2. **`.env`** at the repo root:

   | Var | Purpose |
   |---|---|
   | `ANTHROPIC_API_KEY` | Claude access (required) |
   | `ANTHROPIC_MODEL` | e.g. `claude-haiku-4-5` |
   | `APE_MONGO_URI` | Atlas connection string |
   | `APE_MONGO_DB` | DB name (default `ape`) |
   | `APE_DOMAIN` | default/fallback domain |
   | `APE_UCB_C` | UCB exploration constant (default `1.0`) |
   | `APE_RAG_DIR` | Chroma persist dir (default `./.chroma`) |

3. **Run backend:** `python -m uvicorn ape.api:app --port 7860 --reload`
4. **Run frontend:** `cd frontend && npm install && npm run dev`
   (Vite proxies API calls to `:7860`.)
5. First boot ingests the RAG corpora and downloads the embedding model.

> Secrets live in `.env` (gitignored). Never commit credentials. `.chroma/` is gitignored.

## 2.3 Repo Layout

```
ape/
  api.py              FastAPI app + all endpoints
  orchestrator.py     Path A + Path B
  llm/                classifier.py, synthesizer.py, prompts.py
  bandit/             UCB selection
  signals/            routing, reward_scale, resolver, composites, topic
  rag/                corpus.py, store.py  (Chroma)
  analytics/          platform, strategy_performance, *_quality, unmapped_intents, compute
  store/              mongo_store.py, mongo_schema.py
  config/             seed.py, ConfigManager
frontend/src/         pages/, components/, styles/, api.js, hooks/
scripts/              demo/seed helpers
tests/                pytest suite
Dockerfile            two-stage build (Vite → Python runtime)
```
