# APE Modulor — Project Standup

Running log of session outcomes, newest first. For standup reference.

---

## 2026-07-22 — Claude-style streaming, raw-markdown fix, regression tests

**Deployed to HF Space** (`saivivek6/updated_mongodb_p`, latest: `ef99e21`).

### What shipped
- **Claude-style progressive streaming.** Dropped the JSON envelope — the
  synthesizer now streams plain markdown directly (SSE deltas), the UI
  accumulates and repaints at most once per frame (`requestAnimationFrame`
  batching). `rendered_format` is now inferred server-side from the markdown's
  shape instead of self-declared by the model.
- **Fixed raw markdown visible during streaming** (`**`, `|---|` on screen).
  Root cause: the streaming renderer committed blank-line-delimited blocks,
  but a markdown table contains no blank lines — so the whole table stayed
  raw plain text until the stream ended. Now the renderer commits **complete
  lines** and buffers/sanitizes incomplete structures:
  - tables held until their `|---|` separator arrives, then grow row by row;
  - open ``` code fences held until closed, then render whole;
  - the in-progress line has `**`, backticks, `#` stripped.
- **Streaming logic extracted to a pure module** —
  `frontend/src/utils/streamRender.js` (no React) — with **16 regression
  tests** (`npm test`, node built-in runner, zero new deps). Invariant tested:
  no prefix of the stream may show raw `|---|`, `**`, `#`, or fences, and the
  final frame matches the completed-message render. Covers tables, code
  fences, lists, headings, inline code, links.

### Notable incident
- Local project directory was wiped mid-session (including `.git`). Recovered
  by cloning back from the HF Space remote; `.env` recreated. This standup doc
  was a casualty — recreated today.

- **Migrated to react-markdown + remark-gfm** (later same day). The static
  regex renderer was whack-a-mole: links, blockquotes, dividers, strikethrough,
  and task lists all showed as raw text. Now full CommonMark + GFM renders
  correctly — links are clickable (new tab), verified live in the browser
  against the Roth-vs-Traditional + IRS-link query. Streaming guards survived
  unchanged (they're text-level, renderer-agnostic). Also fixed end-of-stream
  flash (answer vanished during the Mongo history refetch) and a latent bug
  where the old renderer bolded text inside code blocks. 21 tests, all through
  the real parser. Bundle 121 → 168 kB gzip.

### Known gaps / honest caveats
- Code blocks appear whole when the fence closes (safe pause-then-pop), not
  character by character — deliberate holdback.
- Math/LaTeX would need `remark-math` (not added; models rarely emit it here).

### Earlier in this workstream (recent sessions)
- Reward model ported from vg_mvp_v1.0: two-axis (content/format), explicit ±2
  / inferred ±1, 9-signal catalog; thumbs bug fixed (user evidence now ranks
  above derived signals).
- Round-robin cold start confirmed before UCB; domain pinned to stop cell
  fragmentation from unstable LLM domain classification.
- Topic removed from the bandit key (now user + domain + intent).
- UCB runs live in-memory — no cached scores; UI shows the exact selection
  score, tunable formula (c, reward range) in Admin → Config.
- Riya synthetic persona seeded; demo_user cleared.
- Research tab: validated papers, RL taxonomy, bandit-family comparison,
  industry usage map, agentic roadmap.

### Next candidates
- Verify streaming UX on the rebuilt Space (tables/code across formats).
- Consider react-markdown if link rendering or richer CommonMark is needed.
- Visualization components for the synthesizer (Figma component menu idea).
