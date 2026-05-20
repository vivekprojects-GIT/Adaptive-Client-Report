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
#   ANTHROPIC_API_KEY   sk-ant-...           — required for /turn LLM calls
#   APE_MONGO_URI       mongodb+srv://...    — required for state + history
#   APE_ADMIN_TOKEN     long random secret   — required for admin/config/analytics
#
# Optional secrets / env:
#   ANTHROPIC_MODEL     claude-haiku-4-5     (default in env_default below)
#   APE_MONGO_DB        ape                  (default)
#   APE_DOMAIN          finance              (default)
#   APE_UCB_C           1.0                  (default)
#
# Build locally:
#   docker build -t ape-modulor .
#   docker run -p 7860:7860 \
#     -e ANTHROPIC_API_KEY=sk-... -e APE_MONGO_URI=mongodb+srv://... \
#     -e APE_ADMIN_TOKEN=replace-with-a-long-random-secret \
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
RUN python -c "from ape.rag import RagStore; print('warm RAG:', RagStore().ingest())"

EXPOSE 7860

# Lightweight liveness probe — HF Spaces uses this to mark the Space healthy
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl --fail --silent http://localhost:7860/health || exit 1

# tini handles signals cleanly so Spaces can stop/restart the container.
ENTRYPOINT ["/usr/bin/tini", "--"]

# Bind to 0.0.0.0 (NOT localhost) so the port is reachable from outside the container.
# Single worker — the orchestrator + bandit state are process-local; multi-worker
# would multiply LLM connections and split cache. Scale horizontally instead.
CMD ["python", "-m", "uvicorn", "ape.api:app", "--host", "0.0.0.0", "--port", "7860", "--log-level", "info"]
