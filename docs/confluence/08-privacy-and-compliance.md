# 08 - Privacy and Compliance

> Raw text, access control, and outreach eligibility are deliberately separated.

---

## Privacy Boundary

Only `ape_messages` stores raw user and assistant text.

```text
ape_messages
  raw user text
  raw assistant text
  UI resume only

All other collections
  user hashes
  intent ids
  topic ids
  strategy ids
  counters
  rewards
  aggregate scores
  config rows
```

Analytics recompute reads `ape_turn_record` only. It does not read
`ape_messages`.

---

## Collection Sensitivity

| Collection | Raw text | PII | Recommended handling |
|---|---|---|---|
| `ape_messages` | Yes | Chat content can contain PII | TTL, encryption, strict access |
| `ape_user_bandit_state` | No | `user_id_hash` only | Long retention acceptable |
| `ape_turn_record` | No | `user_id_hash` only | Retain long enough for learning/analytics |
| `ape_config` | No | Operator-entered config | Indefinite |
| `ape_admin_audit` | No | `changed_by` operator id | Indefinite compliance log |
| `ape_user_topic_interest` | No | `user_id_hash` only | Recomputed aggregate |
| `ape_topic_trend_daily` | No | None | Aggregate trend retention |
| `ape_user_directory` | No chat text | Names/emails in demo/CRM form | Treat as CRM data |

---

## User Identifiers

```text
raw user_id
   |
   | SHA-256, truncated
   v
user_id_hash = u_<16 hex chars>
```

Properties:

- Deterministic: same user gets the same hash.
- One-way: APE cannot recover raw id from the hash.
- Stable: bandit learning survives session changes.

The analytics API accepts either raw ids or already-hashed `u_<hex>` ids. Hash
values pass through without being double-hashed.

---

## Access Control Now Enforced

Protected operational API families:

```text
/config*
/admin/*
/analytics/*
```

Accepted credentials:

```http
X-APE-Admin-Token: <APE_ADMIN_TOKEN>
Authorization: Bearer <APE_ADMIN_TOKEN>
```

Failure behavior:

| Condition | Response |
|---|---|
| Server has no `APE_ADMIN_TOKEN` | `503` |
| Header missing or wrong | `401` |
| Header correct | Request continues |

The SPA routes `/admin` and `/analytics` are not blocked, because the browser
must load the React app before it can ask for the token.

---

## Transcript Read Scope

Raw session reads require both:

- `session_id`
- `user_id`

The server hashes `user_id` and filters by:

```text
session_id + user_id_hash
```

This prevents reading raw messages with a session id alone.

---

## Outreach Compliance Gates

A user appears as contact-ready only when all gates pass:

```text
interest_score >= offer_policy.min_interest_score
AND compliance_eligible
AND NOT do_not_contact
```

| Gate | Source | Meaning |
|---|---|---|
| `interest_score` | `ape_user_topic_interest` | Behavioral readiness |
| `compliance_eligible` | `ape_user_directory` or CRM | Jurisdiction/regulatory eligibility |
| `do_not_contact` | `ape_user_directory` or CRM | Hard opt-out |

The dashboard is a candidate filter. Downstream outreach still needs full
business compliance checks such as channel preferences, cooldowns, time of day,
and jurisdictional rules.

---

## Audit Trail

Every admin write logs to `ape_admin_audit`:

```yaml
action_id: UUID
date: YYYY-MM-DD
ts: ISO-8601
action_type: string
entity_type: string
entity_id: string
before: object | null
after: object | null
changed_by: string
```

Audit rows are append-only.

---

## Production Hardening Checklist

| Item | Status | Notes |
|---|---|---|
| Token on `/config*`, `/admin/*`, `/analytics/*` | Baseline | Implemented with `APE_ADMIN_TOKEN` |
| User-scoped transcript reads | Baseline | `user_id` required on session message/turn reads |
| TTL on `ape_messages` | Recommended | Limit raw text exposure window |
| Encryption at rest | Recommended | Use Atlas or platform encryption |
| Separate analytics role | Recommended | Analytics readers should not access `ape_messages` |
| SSO for admin | Future hardening | Replace shared token with identity provider |
| Rate limit `/feedback` | Future hardening | Prevent reward gaming |
| CRM-backed directory | Future hardening | Move names/emails out of APE DB |
| Atlas IP allowlist | Recommended | Defense in depth |

---

## Anti-Patterns Avoided

| Anti-pattern | Why it is avoided |
|---|---|
| Store raw query text in `ape_turn_record` | Would leak PII into analytics |
| Use `session_id` as learning key | Learning would reset on every session |
| Use `user_id_hash` alone for reward attribution | Multiple responses per user would collide |
| Let `thumbs_up` directly train format bandit | Generic satisfaction is noisy format evidence |
| Read a transcript by `session_id` alone | Session ids can leak; user scope is required |
| Auto-delete config rows on pause | Pause should be reversible and auditable |

---

## See Also

- [01 - Architecture overview](./01-architecture-overview.md)
- [07 - Operations](./07-operations.md)
- [09 - API reference](./09-api-reference.md)
