# 07 · Frontend

React + Vite SPA in `frontend/src`. API client is `api.js`; shared hooks in
`hooks/` (`useApe.js`, `usePersistedState.js`).

## 7.1 App Shell & Theme

- **Theme:** Claude-desktop palette in `styles/global.css` (`--primary #c87a4c`
  orange, `--bg #fafaf7`, warm near-black text). Shared chrome in
  `styles/app-shell.css` (`.app-page/.app-header/.app-brand/.app-tabs/.btn-text`).
- **Routing:** Chat (`/`), Admin (`/admin`), Analytics (`/analytics`); each page
  reuses the same header/tabs/buttons.

## 7.2 Chat Page

- Streaming answers via `/turn/stream` (SSE), with mount-guarded state +
  AbortController for leak-free teardown.
- **Regenerate** button (emits `regenerate_click`), copy button, thumbs signals.
- Session continuity: a follow-up message finalizes the previous turn's reward;
  `beforeunload` sends a `session_abandon` beacon.

## 7.3 Admin Pages

- Config tabs (Intents, Strategies, Policies, Reward scale, Signals, Offers),
  each using `AdminTable` + `StatusPill` for CRUD and status flips.
- **Intents tab** also shows the **Suggested intents — unmapped backlog** table
  with "Use as new intent" prefill (see `05 · Taxonomy Growth`).
- No admin-token prompt (auth removed by design).

## 7.4 Analytics Dashboard

- Tabs: **Overview / Customers / Cognition / Content / Health**.
- Toolbar: **Date filter** + **Domain selector** (All / Cricket / IT / Movies /
  Travel) + user search. The domain selector threads `&domain=` into every
  domain-aware panel and the trend charts, and reloads them on change.
- **Strategy Performance** panel (Overview): per-format avg reward, tier, pulls,
  best/worst cell, `standard_llm` flagged as baseline — the most direct
  per-domain "is the bandit adapting?" view.
- Charts via `MiniLineChart`; cards via `PlatformOverviewCard`,
  `CognitiveFacetCard`, `CustomerHealthSection`, quality panels.
