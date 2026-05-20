# 04 - Analytics Layer

> Analytics is derived from structured runtime metadata. It does not read raw
> chat text from `ape_messages`.

---

## Access

The `/analytics` SPA route can load without a token. All `/analytics/*` API
routes require the admin token:

```text
X-APE-Admin-Token: <APE_ADMIN_TOKEN>
```

The frontend prompts for the token when it is missing and sends it through the
shared `request()` helper.

---

## Source Collections

| Collection | Used for |
|---|---|
| `ape_turn_record` | Turns, rewards, signals, selected/rendered formats, topics |
| `ape_user_bandit_state` | Strategy performance and cognitive facets |
| `ape_user_topic_interest` | Precomputed user-topic interest |
| `ape_topic_trend_daily` | Precomputed daily topic trends |
| `ape_user_directory` | Optional display names and outreach gates |

`ape_messages` is intentionally excluded.

---

## Page Scope

The dashboard has one search input:

| Input | Mode | Behavior |
|---|---|---|
| Empty | Global | Platform overview, trends, active customers, global facets |
| Raw user id | Single user | Server hashes it and returns that user's profile |
| `u_<hex>` hash | Single user | Server passes it through without double-hashing |

Clicking an active-customer row fills the search input with that user's hash.

---

## Main Sections

### Platform Overview

Cross-user macro view:

- top topics
- top strategies
- stage funnel
- readiness funnel
- intent mix
- signal mix
- platform time series
- customer health
- RAG and instruction quality summaries

### Active Customers

Outreach roster, sorted by readiness. Each row includes:

- display name if available
- user hash
- strongest topic
- interest score
- recent turn counts
- positive/negative engagement
- compliance status
- narrative reason

The outreach gate is:

```text
interest_score >= threshold
AND compliance_eligible
AND NOT do_not_contact
```

### Cognitive Facets

Global mode aggregates by `(intent, topic, strategy)` across users. Single-user
mode shows one user's cells and strategy preferences.

### Topic Interest

Per-user topic scores:

```text
interest_score =
  weight_frequency  * frequency_score
+ weight_recency    * recency_score
+ weight_engagement * engagement_score
+ weight_followup   * followup_depth_score
```

### Recommended Outreach

Uses `offer_policy` rows plus user-topic interest scores. Endpoint path still
uses `/analytics/offers/{user_id}` for compatibility, but the UI label is
Outreach.

---

## Recompute

`POST /analytics/recompute?days=N` rebuilds:

- `ape_user_topic_interest`
- `ape_topic_trend_daily`

It reads `ape_turn_record` only. It does not scan raw messages.

Use cases:

- after demo seeding
- after heavy chat activity
- scheduled cron refresh
- before screenshots or stakeholder review

The UI separates:

| Button | Work |
|---|---|
| Reload | Re-fetch current aggregate collections |
| Recompute now | Rebuild aggregates, then reload |

---

## Endpoint Families

| Endpoint | Purpose |
|---|---|
| `POST /analytics/recompute?days=N` | Rebuild derived aggregate collections |
| `GET /analytics/platform-overview?days=N&top_n=K` | Cross-user dashboard summary |
| `GET /analytics/platform-timeseries?days=N` | Daily platform trend data |
| `GET /analytics/topics-timeseries?days=N&top_n=K` | Daily data for top topics |
| `GET /analytics/trends?days=N&limit=K&refresh=bool` | Trending topics |
| `GET /analytics/topic-timeseries?topic=X&days=N` | Daily counts for one topic |
| `GET /analytics/topic-users?topic=X&limit=K&min_score=Y` | Users interested in a topic |
| `GET /analytics/active-users?days=N&min_interest=X&limit=K` | Outreach roster |
| `GET /analytics/user-profile?user_id=X&domain=Y` | 12-facet profile |
| `GET /analytics/cognitive-facets?user_id=X&min_interactions=N` | Per-cell facets; omit user_id for global |
| `GET /analytics/user-interests?user_id=X&limit=K&refresh=bool` | Per-user topic interest |
| `GET /analytics/user-timeseries?user_id=X&days=N` | Per-user daily activity |
| `GET /analytics/offers/{user_id}?domain=Y` | Recommended outreach actions |
| `GET /analytics/strategy-performance?user_id=X&min_pulls=N` | Strategy ranking and tiers |
| `GET /analytics/customer-health?days=N&cohort_weeks=K` | Satisfaction and retention style health metrics |
| `GET /analytics/rag-quality?days=N&min_turns=K&sample_limit=S` | Content correction and answer quality signals |
| `GET /analytics/instruction-quality?days=N&min_turns=K&sample_limit=S` | Format compliance and instruction issues |

---

## Signal Interpretation

The signal mix should count both:

- entries in `pending_signals[]`
- the final resolved `signal` label, especially composite labels

That is why analytics can still show `thumbs_up` and `thumbs_down` even though
they do not directly update the format bandit.

---

## See Also

- [05 - Cognitive facets](./05-cognitive-facets.md)
- [06 - Outreach recommendation](./06-outreach-recommendation.md)
- [09 - API reference](./09-api-reference.md)
