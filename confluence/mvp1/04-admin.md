# MVP 1 · Admin API

A set of **JSON endpoints** (no UI) to manage config and inspect what the bandit
has learned. A consumer or an internal tool calls these directly. No auth in MVP 1.

## What the admin endpoints cover

### 1. Manage Intents
The closed set of question types. Each is an ACTIVE item in `ApeConfig`
(`pk = "INTENT"`, `sk = intent_id`).
- **List / add / edit / disable** intents (`Decision`, `Explanation`,
  `Comparison`, `Instructional`, `Definitional`, `Evaluation`).
- Disabling an intent means new turns that classify to it fall back to
  `unmapped` (single arm: `standard_llm`).

| Endpoint | Use |
|---|---|
| `GET /config/intents` | list |
| `POST /config/intents` | add / update `{intent_id, description}` |
| `POST /config/status` | flip ACTIVE / INACTIVE |
| `DELETE /config/intents/{id}` | remove |

### 2. Manage Strategies (formats)
The bandit arms. Each is an ACTIVE item in `ApeConfig` (`pk = "STRATEGY"`) with a
one-line format instruction, listed under one or more intents.
- **List / add / edit / disable** strategies (e.g. `comparison_table`,
  `one_liner`, `numbered_steps`, `standard_llm`).
- Each intent has a candidate list; `standard_llm` is always included as the
  no-constraint baseline.

| Endpoint | Use |
|---|---|
| `GET /config/strategies` | list |
| `POST /config/strategies` | add / update |
| `DELETE /config/strategies/{id}` | remove |

### 3. Inspect & reset bandit state
- **View** the learned cells from `ApeBanditState`: for a user + intent, the
  per-strategy `count`, `avg_reward`, `cached_ucb` (a single `Query` on
  `pk = "USER#…#INTENT#…"`).
- **Reset** a user (delete their cell items) or rebuild scores.

| Endpoint | Use |
|---|---|
| `GET /admin/bandit-state?user_id=` | view cells |
| `DELETE /admin/clear-user/{id}` | reset one user's learning |
| `POST /admin/seed` | seed default intents + strategies |
| `POST /admin/rebuild-bandit` | recompute cached_ucb from counts/rewards |

## Notes

- All responses are JSON; there is no admin screen in MVP 1.
- Seeding (`POST /admin/seed`) is the first call you make on a fresh deploy.
- These endpoints are how you (or an internal script) curate the intent list and
  the format catalog the bandit chooses from.
