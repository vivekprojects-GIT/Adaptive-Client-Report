# APE Modulor — Confluence Documentation Set

This folder contains the documentation for building **APE Modulor** (Adaptive
Prompt Engine), organized as a Confluence page tree. Each numbered file is one
Confluence **section** (parent page); the `## ` headings inside it are the
**child pages**. Build/read top-to-bottom — later sections reference earlier ones.

## How to get this into Confluence
- **Import:** Confluence Cloud → Space → ••• → *Import* → Markdown (or use the
  "Markdown" macro per page). Create one parent page per file, then split each
  `## ` block into a child page.
- **Or paste:** copy each `## ` block into a new Confluence page under the
  matching parent.

## Page tree

| # | Section (parent page) | Child pages |
|---|---|---|
| 00 | Home | overview, glossary |
| 01 | Concept & Architecture | problem, architecture, data model, conventions |
| 02 | Environment & Setup | prerequisites, local dev, repo layout |
| 03 | Backend Core | config, strategies, signals, bandit, classifier, synthesizer, orchestrator |
| 04 | RAG (Multi-Domain) | corpus, domain detection, wiring, endpoints |
| 05 | Taxonomy Growth | unmapped backlog, clustering roadmap |
| 06 | API Reference | turn/feedback, config/admin, analytics |
| 07 | Frontend | app shell, chat, admin, analytics dashboard |
| 08 | Analytics Deep-Dive | pipeline, metrics catalog, per-domain adaptation |
| 09 | Testing & Quality | test suite, mock/demo data |
| 10 | Deployment & Ops | docker, hugging face, runbook, decisions (ADR) |
| 11 | Database Design | Mongo collections, DB-first turn flow, reward flow |

`mvp1/` is retained as historical DynamoDB reference material. The current app
uses the MongoDB flow documented in `11-database-design.md`.

## Conventions used in these docs
- File/identifier references point at the real code (`ape/...`, `frontend/src/...`).
- Each page should carry a Confluence **status label**: `Draft` / `Reviewed`.
- Significant decisions live in **10 → Decisions (ADR log)** — append, don't rewrite.
