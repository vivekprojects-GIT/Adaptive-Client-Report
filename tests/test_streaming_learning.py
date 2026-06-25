from __future__ import annotations


def test_streaming_turns_seed_and_flush_bandit_signals(monkeypatch):
    import mongomock
    import pymongo

    monkeypatch.setattr(pymongo, "MongoClient", mongomock.MongoClient)

    import ape.orchestrator as orch_mod
    import ape.store.mongo_store as mongo_store_mod
    from ape.config import seed_all
    from ape.orchestrator import ApeOrchestrator
    from ape.store import MongoStore

    monkeypatch.setattr(mongo_store_mod, "MongoClient", mongomock.MongoClient)

    store = MongoStore(uri="mongodb://localhost:27017", db_name="ape_streaming_test")
    seed_all(store, domain="finance")

    def fake_classify(client, model, query, history, prev_format=None):
        return {
            "intent": "Definitional",
            "intent_confidence": 0.99,
            "domain": "finance",
            "topic": "roth_ira",
            "signal": "deeper_question",
        }

    seen = {}

    def fake_stream(client, model, query, strategy, history, context="", instruction_text=None):
        seen["strategy"] = strategy
        seen["instruction_text"] = instruction_text
        yield {"type": "delta", "text": "hello"}
        yield {"type": "done", "rendered_format": "paragraph", "response": "hello"}

    monkeypatch.setattr(orch_mod, "classify_and_detect", fake_classify)
    monkeypatch.setattr(orch_mod, "generate_response_stream", fake_stream)

    orch = ApeOrchestrator(client=object(), model="fake", store=store, domain="finance")

    first_events = list(orch.handle_turn_streaming("alice", "What is a Roth IRA?"))
    first_response_id = first_events[-1]["response_id"]
    first_session_id = first_events[-1]["session_id"]

    first_row = store.get_response(first_response_id)
    assert first_row["reward_status"] == "PENDING"
    assert first_row["pending_signals"] == []
    assert seen["instruction_text"]

    list(orch.handle_turn_streaming("alice", "Can you explain more?", session_id=first_session_id))

    finalized = store.get_response(first_response_id)
    assert finalized["reward_status"] == "APPLIED"
    assert finalized["signal"] == "deeper_question"
    assert finalized["normalized_reward"] is None
    assert finalized["content_reward"] == 1.0
