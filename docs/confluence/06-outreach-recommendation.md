# 06 - Outreach Recommendation

> Outreach recommendation is a candidate filter. It surfaces users who may be
> worth contacting; it does not send messages or replace compliance workflows.

The database entity remains `offer_policy` for compatibility. The UI and docs
use the clearer label "Outreach".

---

## What an Outreach Action Is

An outreach action is a topic-specific next-best-action configured by an admin.

| Topic | Outreach type | Description |
|---|---|---|
| `retirement_accounts` | `retirement_planning_consultation` | Schedule a planning call |
| `mortgage` | `mortgage_rate_check` | Send current rate options |
| `credit_score` | `credit_education_email` | Send educational follow-up |
| `tax_implications` | `advisor_referral` | Refer to a tax professional |

The recommender scores whether a user qualifies for each action based on
precomputed topic interest and compliance flags.

---

## Inputs

| Source | Used for |
|---|---|
| `ape_user_topic_interest` | `frequency_score`, `recency_score`, `engagement_score`, `followup_depth_score` |
| `ape_config` with `entity_type=offer_policy` | Topic, action type, threshold, optional weights |
| `ape_user_directory` | `do_not_contact`, `compliance_eligible` |

The recommender does not read raw chat messages.

---

## Base Interest Score

The analytics recompute stores four sub-scores per user/topic:

| Component | Meaning | Range |
|---|---|---|
| `frequency_score` | How often this topic appears for the user | `0..1` |
| `recency_score` | How recently the topic appeared | `0..1` |
| `engagement_score` | Average normalized reward | `0..1` |
| `followup_depth_score` | Recent follow-up depth | `0..1` |

Default global weights:

```python
W_FREQ = 0.40
W_RECENCY = 0.25
W_ENGAGE = 0.25
W_FOLLOWUP = 0.10
```

Default composite:

```text
interest_score =
  0.40 * frequency_score
+ 0.25 * recency_score
+ 0.25 * engagement_score
+ 0.10 * followup_depth_score
```

---

## Per-Action Weight Overrides

Each outreach policy can override the weights:

```yaml
entity_type: offer_policy
entity_id: retirement_accounts
domain: finance
offer_type: retirement_planning_consultation
description: Schedule a 30-minute planning call
min_interest_score: 0.80
weight_frequency: 0.10
weight_recency: 0.10
weight_engagement: 0.70
weight_followup: 0.10
status: ACTIVE
```

Weights may be fractions or raw importance values. The recommender normalizes
them to sum to 1 before scoring.

Example:

```text
0.40 / 0.25 / 0.25 / 0.10
```

and:

```text
4 / 2.5 / 2.5 / 1
```

produce the same effective ratio.

---

## Per-Action Score

```python
score = (
    weights["frequency"]  * interest_row.frequency_score
  + weights["recency"]    * interest_row.recency_score
  + weights["engagement"] * interest_row.engagement_score
  + weights["followup"]   * interest_row.followup_depth_score
)
```

The endpoint returns both the score and the contribution breakdown so the UI can
show why a recommendation passed or failed.

---

## Eligibility Gate

Three checks must pass:

```text
score >= min_interest_score
AND compliance_eligible
AND NOT do_not_contact
```

Failure reasons are intentionally plain:

| Failure | Reason |
|---|---|
| `do_not_contact` | User has `do_not_contact` set; outreach blocked |
| `compliance_eligible = false` | User failed compliance check |
| Score below threshold | Interest is below the action threshold |
| All pass | Score is above threshold and compliance/consent gates pass |

---

## Example

User topic sub-scores for `roth_ira`:

```text
frequency_score = 0.82
recency_score = 0.89
engagement_score = 0.67
followup_depth_score = 0.67
```

Default action weights:

```text
score =
  0.40 * 0.82
+ 0.25 * 0.89
+ 0.25 * 0.67
+ 0.10 * 0.67
= 0.786
```

If the threshold is `0.80`, the user is not eligible yet.

Engagement-weighted action:

```text
score =
  0.10 * 0.82
+ 0.10 * 0.89
+ 0.70 * 0.67
+ 0.10 * 0.67
= 0.707
```

If that action's threshold is `0.60`, the same user becomes eligible. Same user,
same data, different outreach goal.

---

## API Output Shape

`GET /analytics/offers/{user_id}` returns rows shaped like:

```json
{
  "offer_type": "retirement_planning_consultation",
  "description": "Schedule a 30-minute planning call",
  "topic": "retirement_accounts",
  "domain": "finance",
  "min_interest_score": 0.8,
  "interest_score": 0.786,
  "eligible": false,
  "reason": "interest_score 0.79 below threshold 0.80 - nurture before offering",
  "score_ok": false,
  "compliance_ok": true,
  "do_not_contact": false,
  "weights": {
    "frequency": 0.4,
    "recency": 0.25,
    "engagement": 0.25,
    "followup": 0.1
  },
  "score_breakdown": {
    "frequency": 0.328,
    "recency": 0.2225,
    "engagement": 0.1675,
    "followup": 0.067
  }
}
```

---

## Tuning Hints

| Symptom | Likely action |
|---|---|
| Too many users qualify | Raise `min_interest_score` |
| One action never qualifies | Lower its threshold or shift weights |
| New users qualify too early | Increase engagement weight or threshold |
| Dormant users still qualify | Increase recency weight |
| Compliance-blocked users never show eligible | Expected; compliance gate is multiplicative |

---

## Boundary

This dashboard is not a decision system. It should feed downstream outreach
operations that enforce jurisdictional rules, consent, channel preferences,
cooldowns, and business approvals.

---

## See Also

- [03 - Admin config](./03-admin-config.md)
- [04 - Analytics layer](./04-analytics-layer.md)
- [08 - Privacy and compliance](./08-privacy-and-compliance.md)
