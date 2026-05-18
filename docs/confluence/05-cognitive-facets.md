# 05 · Cognitive Facets

> 12 **behavioral** observations per user. Never psychological labels.

```
We say:    User is in evaluation stage; prefers comparison tables.
We don't:  User is anxious; user is risk-averse.
```

---

## The 12 facets

| # | Facet | What it answers | Source |
|---|---|---|---|
| 1 | Topic interest | What topic the user keeps returning to | `ape_user_topic_interest` |
| 2 | Intent pattern | What kind of help they ask for | `ape_turn_record` (intent counter) |
| 3 | Decision stage | Where they are in the buying journey | recent intent sequence |
| 4 | Engagement depth | How deep they go on a topic | `ape_user_topic_interest.count_30d` |
| 5 | Format preference | Which format wins for them | `ape_user_bandit_state` |
| 6 | Structured-thinking | Tables/bullets vs paragraphs | bandit rewards over strategy groups |
| 7 | Clarity need | How often they need re-explanations | clarity signal counts |
| 8 | Friction signals | Where they struggle | negative signals + low rewards |
| 9 | Positive engagement | What they liked | positive signals + high rewards |
| 10 | Recency momentum | Are they hot right now? | last-3d-rate vs last-30d-rate |
| 11 | Offer readiness | Could we reach out? | composite × stage gate |
| 12 | Learning confidence | Is the personalization reliable? | total bandit pulls |

---

## Formulas

### 1 · Topic interest
Top topic from `ape_user_topic_interest`, sorted by `interest_score`.

### 2 · Intent pattern
```python
intent_counts = Counter(r["intent"] for r in turn_rows)
dominant_intent = intent_counts.most_common(1)[0][0]
intent_distribution = dict(intent_counts.most_common(6))
```
The dashboard shows percentages: *"Decision 31% · Explanation 26% · Instructional 17%"*

### 3 · Decision stage
Inferred from the most recent 10 intents. Precedence-ordered:

| Stage | Trigger | Score |
|---|---|---|
| Support-needed | ≥40% Troubleshooting | 0.30 |
| Action-ready | ≥40% Decision/Recommendation | 1.00 |
| Evaluation | ≥40% Comparison/Evaluation | 0.75 |
| Awareness | ≥50% Definitional | 0.20 |
| Exploration | otherwise (mixed) | 0.50 |

### 4 · Engagement depth
```
max_count_30d = max(count_30d across user's topics)
  ≥ 8 → High
  ≥ 3 → Medium
  else → Low
```

### 5 · Format preference
```python
best = argmax over pulled bandit rows of:
  avg_reward × min(count / 5.0, 1.0)
```
The count damping prevents a single high-reward pull from winning.

### 6 · Structured-thinking preference
Compare reward across two strategy groups:

```python
STRUCTURED  = {comparison_table, pros_cons_table, decision_card,
               numbered_steps, checklist, bullet_summary,
               phased_workflow, bullet_contrast, step_by_step_reasoning}
PARAGRAPH   = {standard_llm, short_paragraph, one_liner,
               analogy_explanation, definition_plus_example,
               definition_with_pointer}

s_avg = pull-count-weighted avg_reward across STRUCTURED group
p_avg = pull-count-weighted avg_reward across PARAGRAPH group

gap = s_avg - p_avg
  gap >  0.20  → "Structured"
  gap < -0.20  → "Paragraph"
  else          → "Mixed"
```
With fewer than 3 total pulls across both groups: `"Unknown"`.

### 7 · Clarity need
```python
CLARITY_SIGNALS = {"regenerate_click", "format_change_request", "reask_same_question"}
clarity_count = sum(1 for r in turn_rows if r.signal in CLARITY_SIGNALS)
  ≥ 5 → High
  ≥ 2 → Medium
  else → Low
```

### 8 · Friction signals
```python
FRICTION = {"thumbs_down", "regenerate_click", "session_abandon", "content_correction"}
friction = sum(1 for r in turn_rows
               if r.signal in FRICTION
               or (r.normalized_reward or 0) < -0.3)
```

### 9 · Positive engagement
```python
POSITIVE = {"thumbs_up", "copy_save", "it_worked_statement", "deeper_question"}
positive = sum(1 for r in turn_rows
               if r.signal in POSITIVE
               or (r.normalized_reward or 0) >= 0.5)
```

### 10 · Recency momentum
```python
rate_recent   = count_3d  / 3
rate_baseline = count_30d / 30
momentum_ratio = rate_recent / rate_baseline

  ≥ 1.5 → High
  ≥ 0.7 → Medium
  else  → Low
```

### 11 · Offer readiness — **stage-gated composite**
```python
raw = 0.35·interest + 0.30·recency + 0.20·pos_engagement + 0.15·stage_score
offer_readiness = raw × stage_score          # multiplicative gate

  ≥ 0.70 → "Ready"
  ≥ 0.50 → "Likely"
  ≥ 0.30 → "Nurture"
  else   → "Too early"
```
The multiplicative gate means a user in `Awareness` stage **cannot** be Ready no matter how engaged. This matches business intuition: outreach lands on users who've moved from learning to evaluating.

### 12 · Learning confidence
```python
total_pulls = sum(count) across all bandit cells for this user
  ≥ 20 → High
  ≥ 8  → Medium
  else → Low
```

---

## Example output

```json
{
  "user_id_hash": "u_61d48ed1c2e10e5e",
  "display_name": "Alex Chen",
  "top_topic": "retirement_accounts",
  "topic_interest_score": 0.89,
  "dominant_intent": "Decision",
  "intent_distribution": {"Decision": 22, "Comparison": 15, "Evaluation": 7},
  "decision_stage": "Action-ready",
  "decision_stage_score": 1.0,
  "engagement_depth": "High",
  "max_followups_30d": 19,
  "preferred_format": "decision_card",
  "preferred_format_avg_reward": 0.88,
  "structured_preference": "Structured",
  "structured_avg_reward": 0.85,
  "paragraph_avg_reward": 0.20,
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

## Card layout

```
╭─ COGNITIVE PROFILE · Alex Chen ────────────────────────────────────╮
│                                                                    │
│  ┌─ Offer readiness ──┐  ┌─ Decision stage ───┐  ┌─ Top topic ──┐  │
│  │ ████████ 0.97      │  │ Action-ready       │  │ retirement_  │  │
│  │ Ready              │  │ score 1.00         │  │ accounts     │  │
│  └────────────────────┘  └────────────────────┘  └──────────────┘  │
│                                                                    │
│  9-tile facet grid:                                                │
│  Intent pattern · Engagement · Format pref · Structured-thinking · │
│  Clarity need · Friction · Positive eng · Recency · Learning conf  │
│                                                                    │
│  "Behavioral facets only — no psychological labels, no raw queries"│
╰────────────────────────────────────────────────────────────────────╯
```

---

## See also

- [04 · Analytics layer](./04-analytics-layer.md) — where this card sits on the page
- [06 · Outreach recommendation](./06-outreach-recommendation.md) — how interest_score (facet #1) flows into eligibility
