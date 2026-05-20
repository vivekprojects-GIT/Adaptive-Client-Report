# 05 - Cognitive Facets

> The cognitive profile is a set of behavioral product observations. It should
> never claim psychological traits.

Good language:

```text
User is in evaluation stage.
User prefers comparison tables.
User has high follow-up depth on retirement accounts.
```

Avoid:

```text
User is anxious.
User is risk-averse.
User is impulsive.
```

---

## Inputs

The profile uses structured metadata only:

| Source | Used for |
|---|---|
| `ape_turn_record` | intent, topic, final signal label, normalized reward, timestamps |
| `ape_user_bandit_state` | strategy pulls and average rewards |
| `ape_user_topic_interest` | topic interest scores and sub-scores |
| `ape_user_directory` | optional display name |

It does not read raw text from `ape_messages`.

---

## The 12 Facets

| # | Facet | Answers | Main source |
|---|---|---|---|
| 1 | Topic interest | Which topic the user keeps returning to | `ape_user_topic_interest` |
| 2 | Intent pattern | What kind of help they ask for | `ape_turn_record.intent` |
| 3 | Decision stage | Where they are in the journey | Recent intent sequence |
| 4 | Engagement depth | How deep they go on topics | `count_30d` |
| 5 | Format preference | Which format wins for this user | `ape_user_bandit_state` |
| 6 | Structured-thinking preference | Structured formats vs paragraph formats | Strategy group rewards |
| 7 | Clarity need | How often they ask for re-explanation | Clarity signals |
| 8 | Friction signals | Where the interaction struggles | Negative signals and rewards |
| 9 | Positive engagement | What they react well to | Positive signals and rewards |
| 10 | Recency momentum | Whether activity is rising now | 3-day vs 30-day activity rate |
| 11 | Offer readiness | Whether outreach is worth considering | Interest + stage-gated score |
| 12 | Learning confidence | Whether personalization is reliable | Total bandit pulls |

---

## Facet Formulas

### 1. Topic Interest

Top row from `ape_user_topic_interest`, sorted by `interest_score`.

### 2. Intent Pattern

```python
intent_counts = Counter(r["intent"] for r in turn_rows)
dominant_intent = intent_counts.most_common(1)[0][0]
intent_distribution = dict(intent_counts.most_common(6))
```

If turn records are sparse, the implementation can fall back to bandit cells so
the dashboard still shows something useful for seeded data.

### 3. Decision Stage

Uses the most recent 10 intents with precedence:

| Stage | Trigger | Score |
|---|---|---:|
| Support-needed | 40% or more `Troubleshooting` | `0.30` |
| Action-ready | 40% or more `Decision` or `Recommendation` | `1.00` |
| Evaluation | 40% or more `Comparison` or `Evaluation` | `0.75` |
| Awareness | 50% or more `Definitional` | `0.20` |
| Exploration | Otherwise mixed | `0.50` |

### 4. Engagement Depth

```text
max_count_30d >= 8  => High
max_count_30d >= 3  => Medium
otherwise           => Low
```

### 5. Format Preference

Uses pulled bandit rows only:

```python
score = avg_reward * min(count / 5.0, 1.0)
preferred_format = argmax(score)
```

The count damping prevents one lucky high-reward pull from dominating.

### 6. Structured-Thinking Preference

Compare pull-weighted average rewards across strategy groups.

Structured group examples:

```text
comparison_table
pros_cons_table
decision_card
numbered_steps
checklist
bullet_summary
phased_workflow
bullet_contrast
step_by_step_reasoning
```

Paragraph group examples:

```text
standard_llm
short_paragraph
one_liner
analogy_explanation
definition_plus_example
definition_with_pointer
```

Classification:

```text
total pulls < 3       => Unknown
structured - paragraph >  0.20 => Structured
structured - paragraph < -0.20 => Paragraph
otherwise                     => Mixed
```

### 7. Clarity Need

```python
CLARITY_SIGNALS = {
    "regenerate_click",
    "format_change_request",
    "reask_same_question",
}
```

```text
count >= 5 => High
count >= 2 => Medium
otherwise  => Low
```

### 8. Friction Signals

```python
FRICTION_SIGNALS = {
    "thumbs_down",
    "regenerate_click",
    "session_abandon",
    "content_correction",
}
```

A turn also counts as friction when `normalized_reward < -0.3`.

### 9. Positive Engagement

```python
POSITIVE_SIGNALS = {
    "thumbs_up",
    "copy_save",
    "it_worked_statement",
    "deeper_question",
}
```

A turn also counts as positive when `normalized_reward >= 0.5`.

Important distinction: `thumbs_up` is positive engagement for analytics, but it
is not direct format-bandit evidence unless another format-relevant signal is
also present.

### 10. Recency Momentum

```text
rate_recent = turns_last_3d / 3
rate_baseline = turns_last_30d / 30
momentum_ratio = rate_recent / rate_baseline

ratio >= 1.5 => High
ratio >= 0.7 => Medium
otherwise    => Low
```

### 11. Offer Readiness

Offer readiness is stage-gated:

```text
raw_strength =
  0.35 * topic_interest_score
+ 0.30 * recency_score
+ 0.20 * positive_engagement_norm
+ 0.15 * decision_stage_score

offer_readiness = raw_strength * decision_stage_score
```

Labels:

```text
>= 0.70 => Ready
>= 0.50 => Likely
>= 0.30 => Nurture
otherwise => Too early
```

The multiplicative stage gate is deliberate. A user in awareness should not be
marked "Ready" only because they are active.

### 12. Learning Confidence

```text
total_bandit_pulls >= 20 => High
total_bandit_pulls >= 8  => Medium
otherwise                => Low
```

---

## Example Output

```json
{
  "user_id_hash": "u_61d48ed1c2e10e5e",
  "display_name": "Alex Chen",
  "top_topic": "retirement_accounts",
  "topic_interest_score": 0.89,
  "dominant_intent": "Decision",
  "intent_distribution": {
    "Decision": 22,
    "Comparison": 15,
    "Evaluation": 7
  },
  "decision_stage": "Action-ready",
  "decision_stage_score": 1.0,
  "engagement_depth": "High",
  "max_followups_30d": 19,
  "preferred_format": "decision_card",
  "preferred_format_avg_reward": 0.88,
  "structured_preference": "Structured",
  "structured_avg_reward": 0.85,
  "paragraph_avg_reward": 0.2,
  "clarity_need": "Low",
  "clarity_signal_count": 0,
  "friction_signal_count": 0,
  "positive_signal_count": 53,
  "recency_momentum": "High",
  "turns_last_3d": 32,
  "turns_last_30d": 54,
  "offer_readiness_score": 0.97,
  "offer_readiness_label": "Ready",
  "learning_confidence": "High",
  "total_bandit_pulls": 54
}
```

---

## UI Guidance

The card should clearly label these as behavioral facets. The footer copy should
reinforce the boundary:

```text
Behavioral facets only. No psychological labels. No raw queries.
```

---

## See Also

- [04 - Analytics layer](./04-analytics-layer.md)
- [06 - Outreach recommendation](./06-outreach-recommendation.md)
