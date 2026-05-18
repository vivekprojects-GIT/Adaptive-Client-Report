"""
Smoke test against the live MongoDB Atlas cluster from .env.

Covers Path A / Path B / admin audit / conversation history.

Run:
    cd ape_modulor_production
    PYTHONIOENCODING=utf-8 PYTHONPATH=. python tests/test_atlas.py
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    if not os.getenv("APE_MONGO_URI"):
        print("ERROR: APE_MONGO_URI not set in .env", file=sys.stderr)
        return 1

    from ape.store import MongoStore, new_message_id, utcnow_iso
    from ape.config import seed_all
    from ape.config.manager import ConfigManager

    store = MongoStore(db_name="ape_test_smoke")
    cfg = ConfigManager(store)

    # Reset test DB
    for col in ("ape_config", "ape_user_bandit_state", "ape_turn_record",
                "ape_messages", "ape_admin_audit"):
        store.db[col].drop()
    print("[01/16] Cleared test DB 'ape_test_smoke'")

    try:
        # 1. Seed config
        counts = seed_all(store, domain="finance")
        assert counts["intents"] > 0
        print(f"[02/16] Seed: {counts}")

        # 2. Signal routing + reward scale
        assert store.get_signal_routing("thumbs_up")["format_category"] == "strong_positive"
        assert store.get_reward_scale("strong_positive")["normalized_reward"] == 1.0
        print("[03/16] Signal routing + reward scale resolve correctly")

        # 3. Bandit cell lazy creation
        rows = store.get_or_create_bandit_cell(
            user_id_hash="u_alice_test",
            domain="finance",
            intent="Definitional",
            topic="roth_ira",
            strategies=["standard_llm", "one_liner",
                        "definition_plus_example", "definition_with_pointer"],
        )
        assert len(rows) == 4
        print(f"[04/16] Bandit cell lazy-created with {len(rows)} rows")

        # 4. Conversation history — user message
        ts1 = utcnow_iso()
        store.append_message(
            message_id=new_message_id(),
            user_id_hash="u_alice_test",
            session_id="sess_smoke_A",
            role="user",
            content="What is a Roth IRA?",
            ts=ts1,
        )
        print("[05/16] Wrote user message")

        # 5. Conversation history — assistant message
        ts2 = utcnow_iso()
        assistant_msg_id = new_message_id()
        store.append_message(
            message_id=assistant_msg_id,
            user_id_hash="u_alice_test",
            session_id="sess_smoke_A",
            role="assistant",
            content="A Roth IRA is...",
            ts=ts2,
            response_id="resp_atlas_smoke_001",
            rendered_format="paragraph",
            meta={"intent": "Definitional", "topic": "roth_ira",
                  "selected_strategy": "definition_plus_example"},
        )
        print("[06/16] Wrote assistant message")

        # 6. List session messages — in order
        msgs = store.list_session_messages("sess_smoke_A")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["response_id"] == "resp_atlas_smoke_001"
        print(f"[07/16] list_session_messages returns {len(msgs)} messages in order")

        # 7. history_for_llm — only role+content, chronological
        h = store.history_for_llm("sess_smoke_A")
        assert h == [
            {"role": "user", "content": "What is a Roth IRA?"},
            {"role": "assistant", "content": "A Roth IRA is..."},
        ]
        print("[08/16] history_for_llm returns chronological role/content list")

        # 8. List user sessions — aggregation
        sessions = store.list_user_sessions("u_alice_test")
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "sess_smoke_A"
        assert sessions[0]["first_user_message"] == "What is a Roth IRA?"
        assert sessions[0]["message_count"] == 2
        print(f"[09/16] list_user_sessions returned {len(sessions)} sessions with previews")

        # 9. Latest session
        latest = store.latest_session_for_user("u_alice_test")
        assert latest == "sess_smoke_A"
        print(f"[10/16] latest_session_for_user: {latest}")

        # 10. Path A — PENDING response with attribution
        attribution_pk = {
            "user_id_hash": "u_alice_test",
            "domain":       "finance",
            "intent":       "Definitional",
            "topic":        "roth_ira",
        }
        store.write_pending_response({
            "response_id":           "resp_atlas_smoke_001",
            "user_id_hash":          "u_alice_test",
            "session_id_optional":   "sess_smoke_A",
            "ts":                    ts2,
            "domain":                "finance",
            "intent":                "Definitional",
            "intent_confidence":     0.95,
            "topic":                 "roth_ira",
            "selected_strategy":     "definition_plus_example",
            "selection_method":      "ucb",
            "suggested_format":      "definition_plus_example",
            "rendered_format":       "paragraph",
            "format_compliance":     1,
            "ucb_at_selection":      999.0,
            "policy_version":        "v1",
            "instruction_version":   "v1",
            "attribution_bandit_pk": attribution_pk,
            "attribution_bandit_sk": "definition_plus_example",
        })
        print("[11/16] Wrote PENDING response with attribution")

        # 11. Path B — thumbs_up reward
        rewarded = store.mark_response_rewarded(
            response_id="resp_atlas_smoke_001",
            user_id_hash="u_alice_test",
            signal="thumbs_up",
            reward_category="strong_positive",
            normalized_reward=1.0,
        )
        assert rewarded is not None and rewarded["reward_status"] == "APPLIED"
        updated = store.update_strategy_reward(attribution_pk, "definition_plus_example", 1.0)
        assert updated["count"] == 1 and updated["avg_reward"] == 1.0
        store.refresh_cell_ucb_cache(attribution_pk)
        print("[12/16] Path B applied reward and refreshed UCB cache")

        # 12. Double-reward prevention
        assert store.mark_response_rewarded(
            response_id="resp_atlas_smoke_001",
            user_id_hash="u_alice_test",
            signal="thumbs_up",
            reward_category="strong_positive",
            normalized_reward=1.0,
        ) is None
        print("[13/16] Double-reward rejected")

        # 13. Cross-user injection prevention
        assert store.mark_response_rewarded(
            response_id="resp_atlas_smoke_001",
            user_id_hash="u_eve_attacker",
            signal="thumbs_up",
            reward_category="strong_positive",
            normalized_reward=1.0,
        ) is None
        print("[14/16] Cross-user injection rejected")

        # 14. Admin audit
        cfg.update_signal_rule(
            signal_name="thumbs_up",
            format_relevant=True,
            content_relevant=True,
            format_category="strong_positive",
            content_category="strong_positive",
            changed_by="atlas_test",
        )
        audit = cfg.list_audit(limit=10)
        assert any(r["changed_by"] == "atlas_test" for r in audit)
        print("[15/16] Admin audit logged signal-rule update")

        # 15. Session deletion (messages + turns, preserving bandit_state)
        before_bandit = store.bandit_state.count_documents({"user_id_hash": "u_alice_test"})
        deleted = store.clear_user_session("u_alice_test", "sess_smoke_A")
        after_bandit = store.bandit_state.count_documents({"user_id_hash": "u_alice_test"})
        assert deleted["messages_deleted"] == 2
        assert deleted["turn_record_deleted"] == 1
        assert before_bandit == after_bandit, "Deleting a session must NOT reset the bandit"
        print(f"[16/16] Session delete: {deleted}, bandit preserved ({after_bandit} rows)")

        print()
        print("=" * 60)
        print("ALL ATLAS SMOKE TESTS PASSED (with conversation history)")
        print("=" * 60)
        return 0

    finally:
        for col in ("ape_config", "ape_user_bandit_state", "ape_turn_record",
                    "ape_messages", "ape_admin_audit"):
            store.db[col].drop()
        store.client.close()
        print("\n(cleaned up test collections in 'ape_test_smoke')")


if __name__ == "__main__":
    sys.exit(main())
