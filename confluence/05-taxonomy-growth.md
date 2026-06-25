# 05 · Taxonomy Growth

## 5.1 Unmapped-Intent Backlog

When a turn resolves to `unmapped`, the classifier still produced a best guess.
APE captures it as `suggested_intent` on the turn record (see
`orchestrator._suggested_intent_for`):

- classifier returned `unmapped` → its `unmapped_name` (canonicalized via
  `normalize_suggested_label`: slugify + synonym alias map);
- classifier named a real intent that isn't an **active** config entity → that
  intent name (a "you should enable this" signal).

`compute_unmapped_intents` (`ape/analytics/unmapped_intents.py`) groups these by
`suggested_intent` → count, unique users, avg confidence, top topics, last seen.
Surfaced at `GET /analytics/unmapped-intents` and in the **Admin → Intents**
tab as a "Suggested intents — unmapped backlog" table with a **"Use as new
intent"** button that prefills the create form. Promoting an intent makes future
matching turns map, and they drop out of the backlog.

## 5.2 Topic / Intent Clustering Roadmap (design)

Hardcoded whitelists don't scale and you can't list all topics in a prompt.
Target design:

- **The cluster *is* the canonical key.** For a label: embed → nearest cluster
  centroid; ≥ threshold → assign, else create a new cluster.
- **Clustering is the dedup engine** (not nearest-neighbor alone): an offline
  housekeeping pass re-centers centroids and merges drifted duplicates;
  bandit cells merge losslessly (`count` and `total_reward` add).
- **Latency rule:** no LLM/network on the selection hot path. Hot path = O(1)
  cache hit or a local-model embedding + in-memory ANN. Heavy work (re-embed,
  community detection / merge) runs at recompute only.
- **Domain-scoped:** clusters partition by domain (same label means different
  things across domains).
- **Datastore options considered:** Atlas (native `$vectorSearch` + aggregation —
  current best fit); Neptune (use Neptune **Analytics** for vector + community
  detection; keep an in-memory cache on the hot path); DynamoDB (no native vector
  or aggregation — not recommended for this).
- **Graduate to embeddings + vector index** only when distinct topics grow large;
  until then `slug + alias` + LLM batch-canonicalization at recompute suffices.

Status: backlog capture is **shipped**; clustering is **designed, not built**.
