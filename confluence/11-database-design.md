# 11 - Database Design

This is the current MongoDB production flow, aligned to the `vg_mvp_v1.0`
strategy-level behavior. The `mvp1/` folder remains the DynamoDB reference for
the original MVP1 shape.

## Tables Used

- `ape_config`: active intents, strategies, policies, instructions, signal rules, reward scale, UCB config, offers
- `ape_user_bandit_state`: per-user/per-intent strategy arms
- `ape_turn_record`: one receipt per served response
- `ape_messages`: raw chat transcript for UI resume only
- `ape_admin_audit`: config change audit trail

## Step By Step `/turn`

1. `/turn` starts in `ape/api.py`, then calls `ApeOrchestrator.handle_turn`.
2. User id is normalized into `user_id_hash`.
3. Conversation history is loaded from `ape_messages`; the new message is not written yet.
4. Classifier detects `intent`, `domain`, `topic`, and a reaction signal for the previous answer.
5. Previous pending response is looked up in `ape_turn_record` by `user_id_hash + session_id + reward_status=PENDING`, newest first.
6. If no pending response exists, reward is skipped. If previous intent is `unmapped`, the pending response is marked skipped. Otherwise the classifier signal is appended and the response is finalized.
7. Current intent is checked against `ape_config` where `entity_type="intent"` and `status=ACTIVE`. If the classifier label is missing or inactive, the flow preserves that label as `suggested_intent`, switches the served intent to active `unmapped`, and continues.
8. Policy lookup reads active policy rows for `(domain, served_intent, topic="_all")`, then falls back to `topic="_default"`.
9. Every policy strategy is verified against an active `strategy` config row. Inactive strategy rows are ignored. If no active strategies remain, API returns 422.
10. Strategy config supplies instruction metadata: `format_type` is a hint returned with the selected instruction. There is no nested format selection and no active `accepted_rendered_formats` alias system.
    Startup cleanup removes old alias fields from strategy rows without changing the configured `format_type`.
11. The user's bandit cell is loaded or created in `ape_user_bandit_state` for `user_id_hash + domain + served_intent + topic`, one row per active candidate strategy.
12. Missing strategy arms are created with `count=0`, `total_reward=0`, `avg_reward=0.5`, and `cached_ucb=999.0`.
13. Selection happens in memory: first any `count == 0` arm by policy order, else highest UCB:
    `avg_reward + c * width * sqrt(2 * ln(N) / count)`.
14. After selection, DB is updated immediately: selected arm `count` is bumped and the cell UCB display cache is refreshed.
15. Active instruction/config is fetched for the selected strategy.
16. Only now is the user message written to `ape_messages`.
17. The synthesizer uses selected strategy, active instruction text, and strategy `format_type` as parser fallback metadata.
18. Optional format-compliance analytics are strategy-level only and are not used as the bandit reward.
19. A new pending receipt is written to `ape_turn_record` with `response_id`, `user_id_hash`, `selected_strategy`, `suggested_format`, `rendered_format`, `format_compliance`, `reward_status=PENDING`, and bandit attribution pk/sk.
20. Assistant message is written to `ape_messages` with the same response id and metadata chips.

## Reward DB Flow

1. `/feedback` receives `{user_id, response_id, signal}`.
2. User id is normalized and `ape_turn_record` is read by `response_id`.
3. User hash and `reward_status=PENDING` are verified.
4. The signal is appended to `pending_signals`.
5. On eager finalize or next-turn flush, resolver chooses a display label and a separate bandit reward.
6. `ape_turn_record` conditionally flips `PENDING -> APPLIED`.
7. If reward evidence is clear, `ape_user_bandit_state` is updated:
   - `total_reward += reward`
   - `positive_count += 1` when reward > 0
   - `negative_count += 1` when reward < 0
   - `avg_reward = total_reward / count`
8. The cell UCB display cache is refreshed.
