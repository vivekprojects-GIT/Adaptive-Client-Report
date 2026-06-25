# 00 · Home

> Section parent page. Child pages are the `##` blocks below.

## APE Modulor — Overview

**What it is.** APE Modulor (Adaptive Prompt Engine) is a chat application that
*learns the best response **format** per user, per question type, per topic*.
The content of an answer comes from an LLM (Anthropic Claude); APE decides the
**shape** of that answer — one-liner, comparison table, numbered steps, decision
card, etc. — and learns which shape earns the best user reaction.

**How it learns.** A UCB multi-armed bandit treats each response format as an
"arm." For every interaction it observes signals (thumbs up/down, copy, a
follow-up question, a format-change request, silent acceptance, …), turns them
into a reward, and updates the arm's running average. Over time it converges on
the format that works best for each `(user, domain, intent, topic)` cell.

**Stack.**
- **Backend:** FastAPI (Python 3.12)
- **Datastore:** MongoDB Atlas
- **LLM:** Anthropic Claude (classifier + synthesizer calls)
- **RAG:** ChromaDB (local MiniLM embeddings), multi-domain
- **Frontend:** React + Vite (Claude-desktop visual theme)
- **Deploy:** Docker → Hugging Face Spaces

**The two paths (mental model).**
- **Path A — serve:** classify the message → pick a format (bandit) → retrieve
  domain context (RAG) → synthesize the answer → record a PENDING turn.
- **Path B — learn:** collect signals on that turn → resolve them into one
  reward → update the bandit cell.

**Read next:** `01 · Concept & Architecture`.

## Glossary

| Term | Meaning |
|---|---|
| **Domain** | Subject area (cricket, it, movies, travel, …). Part of the cell key. |
| **Intent** | Question *type*: Decision, Explanation, Comparison, Instructional, Definitional, Evaluation (or `unmapped`). |
| **Topic** | What the question is about (canonical snake_case, e.g. `tcp_handshake`). |
| **Strategy / format** | A response shape (`one_liner`, `comparison_table`, …). The bandit arm. |
| **Cell** | A `(user_id_hash, domain, intent, topic)` bucket; arms = candidate strategies. |
| **Signal** | An observed reaction (UI, LLM-detected, or derived). |
| **Reward** | A number in `[-1, +1]` derived from signals; updates the bandit. |
| **UCB** | Upper Confidence Bound selection: `avg_reward + c·√(2·ln N / count)`. |
| **`standard_llm`** | The "no format constraint" baseline arm; the LLM picks its own shape. |
| **Status** | Config lifecycle: `ACTIVE` / `DRAFT` / `INACTIVE`. |
