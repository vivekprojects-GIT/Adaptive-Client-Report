# ─────────────────────────────────────────────────────────────────────────────
# APE Modulor — production container for Hugging Face Spaces (Docker SDK)
#
# Two-stage build:
#   Stage 1 (`frontend-build`)   compiles the React/Vite app → /app/frontend/dist
#   Stage 2 (`runtime`)          Python 3.12 + FastAPI; serves the API AND the
#                                built SPA from a single port (7860 — the HF
#                                Spaces default).
#
# Required HF Space secrets (Settings → Variables and Secrets):
#   ANTHROPIC_API_KEY        sk-ant-...          LLM writer + report chat
#   APE_MONGO_URI            mongodb+srv://...   config store (templates etc.)
#   APE_REPORT_TOKEN_SECRET  long random string  signs report links + sessions
#   ADVISOR_PASSWORD         choose one          gates advisor/admin surfaces
#   APP_BASE_URL             https://<space>.hf.space   absolute link base
#
# Email (optional — without these, sends write .eml files):
#   EMAIL_PROVIDER      gmail
#   EMAIL_FROM          the Gmail address that granted consent
#   GMAIL_TOKEN_JSON    contents of token.json (materialised at boot)
#
# Optional:
#   ANTHROPIC_MODEL     claude-haiku-4-5     (default)
#   APE_MONGO_DB        ape                  (default)
#   SEED_ON_EMPTY       1                    reseed synthetic book on empty DB
#   DATABASE_URL        postgres URL         durable learning state; SQLite
#                                            on ephemeral disk otherwise
#
# Build locally:
#   docker build -t ape-modulor .
#   docker run -p 7860:7860 \
#     -e ANTHROPIC_API_KEY=sk-ant-... -e APE_MONGO_URI=mongodb+srv://... \
#     ape-modulor
# ─────────────────────────────────────────────────────────────────────────────


# ─── Stage 1: build the frontend ──────────────────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# Install deps first (cached layer when package.json hasn't changed)
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund

# Build the SPA
COPY frontend/ ./
RUN npm run build
# Output lands at /app/frontend/dist
# (api.py mounts this at /assets and serves index.html for SPA routes)


# ─── Stage 2: Python runtime ──────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# HF Spaces requires a non-root user with UID 1000.
# Create it before installing anything so file ownership is consistent.
RUN useradd -m -u 1000 -s /bin/bash user

# System deps:
#   - tini   for clean signal handling (Ctrl-C / SIGTERM propagate properly)
#   - curl   for HEALTHCHECK probes
#   - libgomp1  OpenMP runtime required by onnxruntime (Chroma's default
#               embedding model). Without it RAG retrieval crashes at runtime.
RUN apt-get update \
 && apt-get install -y --no-install-recommends tini curl libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Sensible defaults (each can be overridden by Space env vars / docker -e)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    ANTHROPIC_MODEL=claude-haiku-4-5 \
    APE_MONGO_DB=ape \
    APE_DOMAIN=finance \
    APE_UCB_C=1.0 \
    PORT=7860 \
    HOME=/home/user \
    APE_RAG_DIR=/home/user/.chroma

# Install Python deps before copying source so they cache independently
COPY --chown=user:user requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY --chown=user:user ape/      ./ape/
COPY --chown=user:user scripts/  ./scripts/

# Copy built frontend from Stage 1
COPY --from=frontend-build --chown=user:user /app/frontend/dist ./frontend/dist

USER user

# Pre-download the Chroma embedding model (all-MiniLM-L6-v2 ONNX) at build
# time and warm the persistent store, so the first request isn't blocked on a
# model download and RAG works even if runtime egress is restricted.
# Skipped: retrieval is disabled in api.py, so downloading the embedding model
# would add minutes to every build and hundreds of MB to the image for a code
# path nothing calls. Re-enable together with the RAG init.
# RUN python -c "from ape.rag import RagStore; print('warm RAG:', RagStore().ingest())"

# The HOST decides the port: Render injects $PORT, HF Spaces expects 7860.
# Defaulting to 7860 keeps one image working on both.
ENV PORT=7860
EXPOSE 7860

# Probe whatever port the app is actually on, not a hardcoded one.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl --fail --silent "http://localhost:${PORT}/health" || exit 1

# tini handles signals cleanly so the host can stop/restart the container.
ENTRYPOINT ["/usr/bin/tini", "--"]

# Shell form deliberately: $PORT must be expanded at RUNTIME from the host's
# value. Exec form would hand uvicorn the literal string "$PORT".
# Bind 0.0.0.0 (not localhost) so the port is reachable from outside.
# Single worker — orchestrator and bandit state are process-local; more workers
# would split that state and multiply LLM connections.
CMD python -m uvicorn ape.api:app --host 0.0.0.0 --port ${PORT} --log-level info
