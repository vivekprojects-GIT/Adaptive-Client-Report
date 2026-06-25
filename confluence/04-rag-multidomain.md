# 04 · RAG (Multi-Domain)

## 4.1 Knowledge Base & Corpus

- `ape/rag/corpus.py` — `KNOWLEDGE`: a small hand-written corpus for four
  domains (**cricket, it, movies, travel**), ~8 passages each. `RAG_DOMAINS`
  exposes the domain list.
- `ape/rag/store.py` — `RagStore`: a persistent ChromaDB collection (`ape_kb`)
  holding all domains, each doc tagged with a `domain` metadata field.
  Embeddings use Chroma's **default local model** (all-MiniLM-L6-v2 via ONNX) —
  no external API call, so synthesis isn't blocked on embedding latency.
- `ingest(force=False)` is idempotent; `retrieve(query, domain, k)` filters by
  domain; `format_context(hits)` renders passages for the prompt.

## 4.2 Domain Auto-Detection

Domain is detected by the **existing classifier call** — no extra LLM hop. The
prompt lists the domains; the output adds a `domain` field validated against
`RAG_DOMAINS + {"general"}` with an alias map (tech→it, film→movies, …).

Because intents are generic question *shapes*, the same intent catalog works
across all domains. Topics are canonicalized **domain-aware**
(`canonicalize_topic_for_domain`): the finance whitelist only applies to
`finance`; other domains slugify so e.g. `lbw_rule`, `tcp_handshake`,
`inception_plot` survive as their own bandit cells instead of collapsing.

## 4.3 Retrieval → Synthesis Wiring

In the orchestrator, the per-turn detected `domain` drives the bandit cell,
policy lookup, attribution, **and** retrieval. `_retrieve_context(query, domain)`
returns `[]` for `general` / when RAG is off / on error (safe no-op), otherwise
the top-k passages. The context is injected into the synthesizer system prompt as
authoritative grounding, and `rag_doc_ids` + `rag_hit_count` are recorded on the
turn record (so RAG-quality analytics are meaningful).

## 4.4 Endpoints & Ops

| Endpoint | Purpose |
|---|---|
| `GET /rag/search?q=&domain=&k=` | Inspect retrieval live (verify domain isolation) |
| `GET /rag/status` | Per-domain document counts |
| `POST /admin/rag-ingest?force=` | (Re)load the seed corpora |

Startup ingests the corpora idempotently. On Hugging Face the store is
re-seeded on each boot (ephemeral FS) — see `10 · Deployment`.
