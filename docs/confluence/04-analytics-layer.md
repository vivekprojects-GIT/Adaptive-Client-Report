# 04 · Analytics Layer

> Derived collections + dashboard endpoints. Driven by a single search input: empty → global, non-empty → that user.

---

## Page anatomy (`/analytics`)

```
┌────────────────────────────────────────────────────────────────────────┐
│ HEADER                                                                 │
│   H1: Cognitive Analytics                                              │
│   Nav: Chat · Admin/Config · [Reload] [Recompute now]                  │
│   Date window: Today · 7d · 30d · 90d · All                            │
│   🔍 User search    (empty = ALL USERS · type = SINGLE USER)            │
│                                                Reloaded · Recomputed   │
├────────────────────────────────────────────────────────────────────────┤
│ SUMMARY TILES                                                          │
│   Cognitive facets · Trending topics · Active customers · Eligible …   │
├────────────────────────────────────────────────────────────────────────┤
│ PLATFORM OVERVIEW (always, global)                                     │
│   Top topics · Top strategies · Stage funnel · Readiness funnel ·      │
│   Intent mix · Signal mix                                              │
├────────────────────────────────────────────────────────────────────────┤
│ ACTIVE CUSTOMERS (always, global)                                      │
│   Outreach roster with display names, narrative reasons, compliance    │
│   gates. Click [Inspect →] on any row to drill into that user.         │
├────────────────────────────────────────────────────────────────────────┤
│ USER COGNITIVE PROFILE (per-user, shows empty state when no user)      │
│   12-facet hero card                                                   │
├────────────────────────────────────────────────────────────────────────┤
│ COGNITIVE FACETS  (scope follows search input)                          │
│   Per-(intent, topic) cards · Beta(α,β) curves · Insight callout       │
│   In global mode: each card shows "N users contributed"                │
├────────────────────────────────────────────────────────────────────────┤
│ TRENDING TOPICS (always, global, windowed)                             │
│ TOPIC INTEREST  (per-user only)                                        │
│ RECOMMENDED OFFERS  (per-user only)                                    │
│ PRIVACY                                                                │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Search input drives scope

The single search bar is the source of truth for "who am I looking at?":

| Input | Mode | What renders |
|---|---|---|
| **(empty)** | **All users** (global) | Platform Overview, Active customers, Cognitive facets (aggregated, with `unique_users` pill), Trending topics. User-specific sections show a friendly "Select a user" panel. |
| **`alex_retiree`** (raw id) | Single user | Hash internally, load that user's profile + facets + interests + offers. |
| **`u_61d48ed1c2e10e5e`** (already hashed) | Single user | Pass through as-is. |

Clicking **Inspect →** on a row in the Active customers table populates the search input with the user's hash.

---

## Sections

### Summary tiles (4-card strip)
```
Cognitive facets      Trending topics (30d)   Active customers (30d)   Eligible offers
22                    2                       7                        1
2 high · 4 moderate   261 turns in window     3 contact-ready          of 3 policies
```
Numbers reflect the current window + user state.

### Platform Overview
Always-on macro view. Source: `ape_user_topic_interest`, `ape_user_bandit_state`, `ape_turn_record` (aggregated).

Includes:
- **Top topics by user reach** — sorted by unique users, then sum of interest_score
- **Top strategies** — popularity × reward weighted
- **Stage funnel** — Awareness / Exploration / Evaluation / Action-ready / Support-needed
- **Offer-readiness distribution** — Ready / Likely / Nurture / Too early
- **Intent mix** — % of turns by intent across the window
- **Signal mix** — % of rewarded turns by signal (positive in green, negative in red)

### Active customers
The outreach roster. One row per user active in the window. Sorted by contact-readiness, then interest.

Columns:
- **User** — display name + truncated hash + intent mini-pills
- **Top topic** — chip + "+N more" badge
- **Interest** — best score with HIGH/MEDIUM/LOW color
- **Turns / Topics / Pos / total** — counters
- **Last seen** — relative time
- **Status** — `● Contact ready` / `○ Below threshold` / `⊘ Do not contact` / `⊘ Compliance block`
- **Reason** — narrative explanation (see below)
- **Inspect →** — sets the search input to this user's hash, scrolls to cognitive facets

#### Narrative reason
Every row carries a human-readable rationale:

> *"Alex Chen: asked about retirement_accounts across 54 turns; spanning 3 topics; mostly Comparison / Decision / Evaluation intent; 53/54 positive rewards (98% positive engagement); top interest_score = 0.89 — ready for outreach."*

Or for a blocked user:

> *"Sam Rodriguez has do_not_contact set — never surface for outreach."*

### User Cognitive Profile  *(per-user only)*
Hero card with all 12 facets. See [05 · Cognitive facets](./05-cognitive-facets.md).

### Cognitive Facets — scope follows search input

**In single-user mode**: per-(intent, topic) cells for that user. Each card shows leading strategy μ-reward, runner-up, Beta(α,β) curves, confidence tier (HIGH/MODERATE/LOW), and a "Cognitive Insight" callout.

**In global mode**: same cards, but the per-strategy values are aggregated across all users via:
```
total_count   = sum of counts across users
total_reward  = sum of total_reward across users
avg_reward    = total_reward / total_count
unique_users  = |{ user_id_hash for that (intent, topic, strategy) }|
```
Each card displays a green **"N users"** pill so the admin sees how broad the evidence is.

### Trending Topics
Windowed by date filter. Source: `ape_topic_trend_daily`.
```
trend_score = 0.4·normalized_volume + 0.3·growth/3 + 0.2·density + 0.1·avg_reward
```

### Topic Interest  *(per-user only)*
Table showing the 4 sub-scores per topic for the inspected user. See [06 · Outreach recommendation](./06-outreach-recommendation.md) for what the scores mean.

### Recommended Offers  *(per-user only)*
Each offer row shows:
- offer_type + description
- user's interest_score for that topic + breakdown (`freq 0.33  rec 0.22  eng 0.17  foll 0.07`)
- threshold (`min_interest_score`)
- Eligibility — `● Eligible` / `○ Not eligible`
- Narrative reason: *"score 0.90 ≥ 0.80 threshold; engagement contributes 0.22, frequency contributes 0.32; compliance + consent gates pass"*

---

## Endpoints

| Endpoint | Purpose | Scope |
|---|---|---|
| `POST /analytics/recompute?days=N` | Rebuild `ape_user_topic_interest` + `ape_topic_trend_daily` from raw `ape_turn_record` | Admin trigger only |
| `GET /analytics/platform-overview?days=N&top_n=K` | Cross-user macro view | All users |
| `GET /analytics/active-users?days=N` | Outreach roster | All users (per-row) |
| `GET /analytics/trends?days=N&limit=K` | Trending topics | All users |
| `GET /analytics/topic-users?topic=X` | Users interested in a topic | All users, scoped to topic |
| `GET /analytics/topic-timeseries?topic=X&days=N` | Daily counts for one topic | All users, scoped to topic |
| `GET /analytics/user-profile?user_id=X` | 12-facet profile | One user |
| `GET /analytics/cognitive-facets[?user_id=X]` | Per-cell facets — **omit user_id for global** | Both |
| `GET /analytics/user-interests?user_id=X` | Topic interest table | One user |
| `GET /analytics/offers/{user_id}` | Recommended outreach actions | One user |
| `GET /analytics/strategy-performance[?user_id=X]` | Strategy ranking + tier | Both |

See [09 · API reference](./09-api-reference.md) for payload shapes.

---

## Reload vs Recompute

> ⚠ These two buttons do **different things** — read them carefully.

| Button | Latency | What it does | When |
|---|---|---|---|
| **Reload** | ~2 s | Re-fetch the precomputed aggregates from Mongo | Whenever — cheap |
| **Recompute now** | ~13 s | Rebuild `ape_user_topic_interest` + `ape_topic_trend_daily` from raw `ape_turn_record`, then reload | When admin wants fresh aggregates after new chat activity |

Production should also run `scripts/cron_recompute.py` on a schedule. See [07 · Operations](./07-operations.md).

---

## See also

- [05 · Cognitive facets](./05-cognitive-facets.md) — the 12-facet profile in detail
- [06 · Outreach recommendation](./06-outreach-recommendation.md) — the scoring formula behind eligible outreach
