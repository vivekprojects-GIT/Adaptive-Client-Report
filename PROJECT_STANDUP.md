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

### Known gaps / honest caveats
- The minimal markdown renderer has **no link support** (`[text](url)` passes
  through as text) — pinned by a test so adding it is a conscious decision.
- Long code blocks appear whole when the fence closes (safe pause-then-pop),
  not character by character — full incremental code rendering would need a
  stateful parser (e.g. react-markdown).

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
