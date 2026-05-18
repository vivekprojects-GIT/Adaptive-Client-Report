# 08 · Privacy & Compliance

> What's stored where, who can read it, and how outreach is gated.

---

## The privacy boundary

The **only** collection that contains raw user text is `ape_messages`. Every other collection stores structured metadata: topic IDs, intent IDs, strategy IDs, counters, scores.

```
ape_messages          ⟵ RAW user + assistant text (UI resume only)
                        │
                        │  NOT copied to:
                        ▼
ape_turn_record           normalized metadata + reward attribution
ape_user_bandit_state     counters + averages
ape_user_topic_interest   derived 0..1 scores
ape_topic_trend_daily     derived 0..1 scores
ape_config                config rows
ape_admin_audit           before/after on config changes
ape_user_directory        hash → display name (production: from CRM)
```

The analytics recompute reads `ape_turn_record` exclusively. It never touches `ape_messages`.

---

## What's persisted by collection

| Collection | Raw text? | PII fields? | Retention recommendation |
|---|---|---|---|
| `ape_messages` | ✅ yes | content (user query + assistant answer) | TTL 30–90 days; encrypt at rest |
| `ape_user_bandit_state` | ❌ no | none (`user_id_hash` only) | Indefinite (small footprint) |
| `ape_turn_record` | ❌ no | none (`user_id_hash` only) | TTL 90–180 days |
| `ape_config` | ❌ no | none (just config) | Indefinite |
| `ape_admin_audit` | ❌ no | `changed_by` (operator identity) | Indefinite (compliance) |
| `ape_user_topic_interest` | ❌ no | none (`user_id_hash` only) | Recomputed nightly — TTL 7 days |
| `ape_topic_trend_daily` | ❌ no | none (aggregate) | TTL 90 days |
| `ape_user_directory` | ❌ no but **display_name + email** | yes — names, emails | Treat as CRM data; move to CRM in production |

---

## User identifiers

```
user_id            ←  raw, supplied by upstream auth/system
    │
    ▼  SHA-256, truncate to 16 hex chars
user_id_hash       ←  "u_d74738e262dc4ca9"  — what APE actually stores
```

- The hash is **deterministic** — same `user_id` always maps to the same hash, so personalization works across sessions.
- The hash is **one-way** — APE can't recover the raw `user_id` from `user_id_hash` alone.
- The mapping back to a human name lives in `ape_user_directory` (or the CRM in production).

> ℹ The admin Active customers list surfaces `user_id_hash` so operators can match against their CRM. The Inspect button accepts either form — the `_resolve_user_hash` helper detects `u_<hex>` and passes it through, otherwise it hashes.

---

## Compliance gates (outreach side)

Three independent boolean checks decide whether a user appears as "contact-ready":

```python
eligible_for_outreach =
    score_ok                                    # interest_score >= threshold
  AND compliance_eligible                       # jurisdictional / regulatory
  AND NOT do_not_contact                        # hard user opt-out
```

| Flag | Source | Meaning |
|---|---|---|
| `score_ok` | computed at request time | Per-offer threshold passed |
| `compliance_eligible` | `ape_user_directory.compliance_eligible` (default `true`) | Set by your compliance pipeline; flips to `false` when a user fails a jurisdictional check |
| `do_not_contact` | `ape_user_directory.do_not_contact` (default `false`) | Hard opt-out; admin sets this, runtime respects it |

The narrative reason on each row explains which check failed:

```
"Sam Rodriguez has do_not_contact set — never surface for outreach."
"Riya Singh failed compliance check — not eligible for outreach."
"Maya Patel: top interest_score = 0.86 — ready for outreach."
```

> ⚠ **The dashboard is a candidate filter, not a decision system.** Downstream outreach must still pass your full compliance pipeline (jurisdictional rules, time-of-day, cooldowns, channel preferences). The dashboard surfaces *who could be contacted*; the operations layer decides *whether and how*.

---

## Audit trail

Every admin write logs to `ape_admin_audit`:

```yaml
action_id:   UUID
date:        YYYY-MM-DD
ts:          ISO-8601
action_type: UPSERT | DELETE | STATUS_INACTIVE | STATUS_ACTIVE | UPSERT_INTENT | ...
entity_type: intent | strategy | instruction | policy | offer_policy | ...
entity_id:   (and version for instructions)
before:      pre-change snapshot (Mongo _id stripped)
after:       post-change snapshot
changed_by:  string (currently a free-form string; integrate with SSO in prod)
```

This is append-only — there's no `delete` or `update` path on audit rows.

The **Audit Log** tab in `/admin` shows the most recent 100 rows by default, filterable by date.

---

## Production hardening checklist

| Item | Why | How |
|---|---|---|
| TTL on `ape_messages` | Limit raw-text exposure window | Mongo TTL index on `ts` |
| Encryption at rest | Per industry baseline | Atlas: enable encryption; on-prem: filesystem-level |
| Separate read access | Analytics readers should not need raw-text access | Two roles: `ape_runtime` (full) and `ape_analytics` (no `ape_messages`) |
| ETL exclusion | Analytics pipelines should not scan raw text | Explicit collection allowlist in any ETL job |
| `changed_by` from SSO | Currently free-form | Integrate with your IdP; require auth header on `/admin/*` |
| `ape_user_directory` → CRM | Display data is sensitive | Replace with a live CRM join; dashboard tolerates absence |
| Outbound IP allowlist on Atlas | Defense in depth | Atlas IP access list |
| Rate limit on `/feedback` | Prevent reward gaming | Per-`response_id` and per-`user_id_hash` rate limits |

---

## What we explicitly DON'T do

| Anti-pattern | Why we avoid it |
|---|---|
| Store raw queries in `ape_turn_record` | Would defeat the privacy boundary; the analytics layer would carry PII |
| Use `session_id` as a learning key | Personalization would reset every new session; cross-session learning is the whole point |
| Use `user_id_hash` as a reward attribution key | Multiple in-flight responses per user would collide; we'd reward the wrong arm |
| Allow `session_id` to write `ape_user_bandit_state` | Cross-contamination across sessions in the same user; user_id_hash is the right key |
| Auto-delete config rows on pause | Pause should be reversible; deletes go through DELETE actions which audit clearly |
| Hard-fail when `ape_user_directory` is empty | Dashboard must work with hashes alone for graceful degradation |

---

## See also

- [01 · Architecture overview](./01-architecture-overview.md) — full schema with privacy callouts
- [07 · Operations](./07-operations.md) — what to enforce on deploy
