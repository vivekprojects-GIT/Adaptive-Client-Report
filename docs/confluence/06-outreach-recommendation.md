# 06 · Outreach Recommendation

> The math behind recommended outreach — per-action scoring weights, threshold gate, and compliance gates. *(The DB-level entity_type is still `offer_policy` for backward compatibility; in the UI and docs we call these "outreach actions".)*

---

## What an outreach action is

A pre-defined next-best-action tied to a topic. Examples:

| Topic | Outreach type | Description |
|---|---|---|
| `retirement_accounts` | `retirement_planning_consultation` | Schedule a 30-min planning call |
| `mortgage` | `mortgage_rate_check` | Send current rate options |
| `credit_score` | `credit_education_email` | Free educational follow-up |
| `tax_implications` | `advisor_referral` | Hand off to a CPA |

The recommender decides whether a given user is **eligible** for each outreach based on their interest and compliance status. It never sends anything — it just surfaces candidates for the operations layer.

---

## The big picture

```
User's per-topic sub-scores (precomputed)         Outreach policy (admin-set)
┌─────────────────────────┐                       ┌─────────────────────────┐
│ frequency_score      F  │                       │ topic              T    │
│ recency_score        R  │ ─── join on topic ──▶ │ min_interest_score      │
│ engagement_score     E  │                       │ weight_frequency        │
│ followup_depth       U  │                       │ weight_recency          │
│                         │                       │ weight_engagement       │
└─────────────────────────┘                       │ weight_followup         │
                                                  └─────────────────────────┘
            │                                                  │
            └──────────────────┬───────────────────────────────┘
                               ▼
                    score = w_f·F + w_r·R + w_e·E + w_u·U
                    (weights normalized so they sum to 1)
                               │
                               ▼
        ┌──────────────────────┴──────────────────────┐
        │                                              │
        ▼                                              ▼
   score >= min_interest_score?            compliance + DNC ok?
        │                                              │
        └──────────────────────┬──────────────────────┘
                               ▼
                          eligible = both
```

---

## Step 1 · Sub-scores (in `ape_user_topic_interest`)

For each `(user_id_hash, topic)` row, we precompute four components from the last 30 days of `ape_turn_record`:

| Component | Formula | Range |
|---|---|---|
| **frequency_score** | `count_30d / max(count_30d across this user's topics)` | 0..1 |
| **recency_score** | `exp(-days_since_last_seen / 7)` | 0..1 |
| **engagement_score** | average normalized_reward across rewarded turns | 0..1 |
| **followup_depth_score** | `count_7d / count_30d` | 0..1 |

> ℹ These are stored in `ape_user_topic_interest` — recomputed on `POST /analytics/recompute` or via the cron. They are computed ONCE per user-topic, then reused by every outreach action.

---

## Step 2 · Composite interest score

**Default global weights** (from `ape/analytics/compute.py`):

```python
W_FREQ      = 0.40
W_RECENCY   = 0.25
W_ENGAGE    = 0.25
W_FOLLOWUP  = 0.10
```

The composite stored in `ape_user_topic_interest.interest_score`:

```
interest_score = 0.40·F + 0.25·R + 0.25·E + 0.10·U
```

---

## Step 3 · Per-action weight overrides

Each outreach row can override the global weights:

```yaml
entity_type: offer_policy             # legacy field name; UI says "outreach"
entity_id:   "retirement_accounts"
offer_type:  "retirement_planning_consultation"
min_interest_score: 0.80
# Optional overrides — null/missing means "use globals"
weight_frequency:  0.10
weight_recency:    0.10
weight_engagement: 0.70    # this outreach cares mostly about engagement
weight_followup:   0.10
```

The recommender resolves weights at request time:

```python
def _resolve_weights(policy):
    raw = {
        "frequency":  policy.get("weight_frequency",  W_FREQ),
        "recency":    policy.get("weight_recency",    W_RECENCY),
        "engagement": policy.get("weight_engagement", W_ENGAGE),
        "followup":   policy.get("weight_followup",   W_FOLLOWUP),
    }
    total = sum(raw.values())
    return {k: v / total for k, v in raw.items()}   # normalize to sum=1
```

Admin can enter weights as **fractions** (`0.4`, `0.25`) **or** as **raw importance** (`4`, `2.5`) — both produce the same effective ratio after normalization. The form shows a live preview:

```
EFFECTIVE: [Frequency 10%] [Recency 10%] [Engagement 70%] [Followup 10%]
```

---

## Step 4 · Per-action score

Apply the resolved weights to the user's stored sub-scores:

```python
score = (
    weights["frequency"]  * interest_row.frequency_score
  + weights["recency"]    * interest_row.recency_score
  + weights["engagement"] * interest_row.engagement_score
  + weights["followup"]   * interest_row.followup_depth_score
)
```

This is **cheap** — no aggregation, just 4 multiplications using already-stored sub-scores. The recommender returns both the score and a per-component breakdown so the UI can show *why* a number came out the way it did.

---

## Step 5 · Three-way eligibility gate

```python
score_ok       = score >= threshold
compliance_ok  = directory.compliance_eligible        # default True
do_not_contact = directory.do_not_contact             # default False

eligible = score_ok AND compliance_ok AND NOT do_not_contact
```

Most-specific failure reason wins:

| Failure | Reason text |
|---|---|
| `do_not_contact` is set | "user has do_not_contact set — outreach blocked" |
| `compliance_eligible = false` | "user failed compliance check — not eligible for outreach" |
| `score < threshold` | "interest_score 0.78 below threshold 0.80 — nurture before reaching out" |
| All pass | "score 0.90 ≥ 0.80 threshold; engagement contributes 0.22, frequency contributes 0.32; compliance + consent gates pass" |

---

## Example — same user, two weighting profiles

**User:** maya_learner. Her sub-scores on `roth_ira`:
```
frequency_score      = 0.82
recency_score        = 0.89
engagement_score     = 0.67
followup_depth_score = 0.67
```

**Outreach A — default weights (40/25/25/10):**
```
score = 0.40·0.82 + 0.25·0.89 + 0.25·0.67 + 0.10·0.67
      = 0.328 + 0.223 + 0.168 + 0.067
      = 0.786
threshold = 0.80 → NOT ELIGIBLE
```

**Outreach B — engagement-weighted (10/10/70/10):**
```
score = 0.10·0.82 + 0.10·0.89 + 0.70·0.67 + 0.10·0.67
      = 0.082 + 0.089 + 0.469 + 0.067
      = 0.707
threshold = 0.60 → ELIGIBLE
```

Same user. Same data. Different outreach goals → different verdicts. Admin sets this profile via the form on the Outreach tab.

---

## How the breakdown appears in the UI

Each row in the Recommended Outreach table:

```
Outreach                    User score    Threshold   Status        Reason
─────────────────────────────────────────────────────────────────────────────
retirement_planning_consult  0.78         0.80        ○ Not eligible
                             freq 0.33  rec 0.22  eng 0.17  foll 0.07
                                                                    "interest_score 0.78 below
                                                                     threshold 0.80 — nurture
                                                                     before reaching out"
```

Hover the breakdown for per-component weights tooltip.

---

## Tuning hints

| Symptom | Likely fix |
|---|---|
| Too many users get "Eligible" everywhere | Raise `min_interest_score` |
| One outreach action never fires even when users seem qualified | Lower its threshold, or shift weights to a component the users score well on |
| New users get outreach prematurely | Tighten weights toward `engagement` (which falls back to 0.5 when no rewards yet) |
| Old users keep getting outreach after going dormant | Raise `weight_recency` |
| Compliance-blocked users vanish from list | Expected — gate is multiplicative; check `ape_user_directory.compliance_eligible` |

---

## Important boundary

> ⚠ **The dashboard is a candidate filter, not a decision system.** It surfaces *who could be reached out to*. Downstream outreach orchestration must still pass your full compliance pipeline (jurisdictional rules, channel preferences, time-of-day, cooldown windows). Treat the Recommended Outreach table as input, not output.

---

## See also

- [03 · Admin config](./03-admin-config.md) — the Outreach tab UI + entity schema
- [04 · Analytics layer](./04-analytics-layer.md) — where the recommended outreach appears
- [08 · Privacy & compliance](./08-privacy-and-compliance.md) — what the compliance gate actually checks
