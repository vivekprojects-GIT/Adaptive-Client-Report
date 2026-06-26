from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException


def _store(monkeypatch, db_name="ape_db_first_test"):
    import mongomock
    import pymongo

    monkeypatch.setattr(pymongo, "MongoClient", mongomock.MongoClient)

    import ape.store.mongo_store as mongo_store_mod
    from ape.config import seed_all
    from ape.store import MongoStore

    monkeypatch.setattr(mongo_store_mod, "MongoClient", mongomock.MongoClient)
    store = MongoStore(uri="mongodb://localhost:27017", db_name=db_name)
    seed_all(store, domain="finance")
    return store


def test_unknown_intent_falls_back_to_unmapped_and_writes_turn(monkeypatch):
    import ape.orchestrator as orch_mod
    from ape.orchestrator import ApeOrchestrator

    store = _store(monkeypatch)

    def fake_classify(client, model, query, history, prev_format=None):
        return {
            "intent": "MysteryIntent",
            "intent_confidence": 0.91,
            "domain": "finance",
            "topic": "_all",
            "signal": "no_signal",
        }

    def fake_generate(
        client,
        model,
        query,
        strategy,
        history,
        max_tokens=1500,
        context="",
        instruction_text=None,
        fallback_format=None,
    ):
        return fallback_format or "paragraph", "answer"

    monkeypatch.setattr(orch_mod, "classify_and_detect", fake_classify)
    monkeypatch.setattr(orch_mod, "generate_response", fake_generate)
    orch = ApeOrchestrator(client=object(), model="fake", store=store, domain="finance")

    result = orch.handle_turn("alice", "surprise me")
    record = store.turn_record.find_one({"response_id": result["response_id"]})

    assert result["classification"]["intent"] == "MysteryIntent"
    assert result["selection"]["selected_strategy"] == "standard_llm"
    assert record["intent"] == "unmapped"
    assert record["suggested_intent"] == "MysteryIntent"
    assert store.messages.count_documents({}) == 2
    assert store.turn_record.count_documents({}) == 1


def test_inactive_policy_strategy_is_not_a_bandit_candidate(monkeypatch):
    import ape.orchestrator as orch_mod
    from ape.orchestrator import ApeOrchestrator, hash_user_id

    store = _store(monkeypatch)
    store.set_config_status("strategy", "standard_llm", "INACTIVE")

    def fake_classify(client, model, query, history, prev_format=None):
        return {
            "intent": "Definitional",
            "intent_confidence": 0.99,
            "domain": "finance",
            "topic": "_all",
            "signal": "no_signal",
        }

    def fake_generate(
        client,
        model,
        query,
        strategy,
        history,
        max_tokens=1500,
        context="",
        instruction_text=None,
        fallback_format=None,
    ):
        return fallback_format or "paragraph", "answer"

    monkeypatch.setattr(orch_mod, "classify_and_detect", fake_classify)
    monkeypatch.setattr(orch_mod, "generate_response", fake_generate)

    orch = ApeOrchestrator(client=object(), model="fake", store=store, domain="finance")
    result = orch.handle_turn("alice", "what is duration?")

    assert result["selection"]["selected_strategy"] != "standard_llm"
    assert "standard_llm" not in result["selection"]["strategies_available"]

    user_hash = hash_user_id("alice")
    bandit_rows = list(store.bandit_state.find({"user_id_hash": user_hash, "intent": "Definitional"}))
    assert bandit_rows
    assert {r["strategy"] for r in bandit_rows}.isdisjoint({"standard_llm"})


def test_no_active_policy_strategies_rejects_without_bandit_rows(monkeypatch):
    import ape.orchestrator as orch_mod
    from ape.orchestrator import ApeOrchestrator, NoActiveStrategiesError, hash_user_id
    from ape.strategies.catalog import INTENT_STRATEGIES

    store = _store(monkeypatch)
    for strategy in INTENT_STRATEGIES["Definitional"]:
        store.set_config_status("strategy", strategy, "INACTIVE")

    def fake_classify(client, model, query, history, prev_format=None):
        return {
            "intent": "Definitional",
            "intent_confidence": 0.99,
            "domain": "finance",
            "topic": "_all",
            "signal": "no_signal",
        }

    monkeypatch.setattr(orch_mod, "classify_and_detect", fake_classify)
    orch = ApeOrchestrator(client=object(), model="fake", store=store, domain="finance")

    with pytest.raises(NoActiveStrategiesError, match="No active strategies"):
        orch.handle_turn("alice", "what is duration?")

    assert store.bandit_state.count_documents({"user_id_hash": hash_user_id("alice")}) == 0
    assert store.turn_record.count_documents({}) == 0


def test_strategy_config_uses_format_type_metadata_only(monkeypatch):
    from ape.config.manager import ConfigManager
    from ape.config.seed import cleanup_strategy_format_metadata

    store = _store(monkeypatch)
    cfg = ConfigManager(store)

    cfg.upsert_strategy("pros_cons_table", "comparison_table")
    doc = store.get_active_config("strategy", "pros_cons_table")
    assert doc["format_type"] == "comparison_table"
    assert "accepted_rendered_formats" not in doc
    assert "expected_format" not in doc

    store.config.update_one(
        {"entity_type": "strategy", "entity_id": "bullet_contrast"},
        {"$set": {
            "format_type": "*",
            "expected_format": "*",
            "accepted_rendered_formats": ["*"],
        }},
    )
    cleanup_strategy_format_metadata(store)
    cleaned_doc = store.get_active_config("strategy", "bullet_contrast")
    assert cleaned_doc["format_type"] == "*"
    assert "accepted_rendered_formats" not in cleaned_doc
    assert "expected_format" not in cleaned_doc


def test_delete_intent_removes_policy_rows(monkeypatch):
    import ape.api as api_mod

    store = _store(monkeypatch)
    monkeypatch.setattr(api_mod, "STORE", store)

    assert store.config.count_documents({"entity_type": "policy", "intent": "Decision"}) > 0

    result = api_mod.delete_intent("Decision")

    assert result["status"] == "ok"
    assert result["policies_deleted"] > 0
    assert store.get_active_config("intent", "Decision") is None
    assert store.config.count_documents({"entity_type": "policy", "intent": "Decision"}) == 0


def test_delete_paused_config_rows(monkeypatch):
    import ape.api as api_mod

    store = _store(monkeypatch)
    monkeypatch.setattr(api_mod, "STORE", store)

    store.upsert_config(
        "intent",
        "PausedIntent",
        {"intent_id": "PausedIntent", "description": "paused"},
        status="INACTIVE",
    )
    assert api_mod.delete_intent("PausedIntent")["deleted"] == 1

    store.upsert_config(
        "strategy",
        "paused_strategy",
        {"strategy_id": "paused_strategy", "format_type": "paragraph"},
        status="INACTIVE",
    )
    assert api_mod.delete_strategy("paused_strategy")["deleted"] == 1

    store.upsert_config(
        "signal_routing",
        "paused_signal",
        {
            "signal_name": "paused_signal",
            "format_relevant": False,
            "content_relevant": True,
            "format_category": None,
            "content_category": "inferred_negative",
        },
        status="INACTIVE",
    )
    assert api_mod.delete_signal_rule("paused_signal")["deleted"] == 1

    store.upsert_config(
        "reward_scale",
        "paused_reward",
        {"reward_category": "paused_reward", "normalized_reward": -1.0},
        status="INACTIVE",
    )
    assert api_mod.delete_reward_value("paused_reward")["deleted"] == 1

    store.upsert_config(
        "policy",
        "PausedIntent#_default#paused_strategy",
        {
            "domain": "finance",
            "intent": "PausedIntent",
            "topic": "_default",
            "strategy_id": "paused_strategy",
            "policy_version": "v1",
            "exploration_constant": 1.0,
        },
        status="INACTIVE",
    )
    assert api_mod.delete_policy("PausedIntent", "_default", "paused_strategy")["deleted"] == 1

    store.upsert_config(
        "offer_policy",
        "paused_topic",
        {"domain": "finance", "offer_type": "paused", "description": "paused"},
        status="INACTIVE",
    )
    assert api_mod.delete_offer("paused_topic")["deleted"] == 1


def test_edit_paused_config_rows_preserves_status(monkeypatch):
    import ape.api as api_mod
    from ape.config.manager import ConfigManager

    store = _store(monkeypatch)
    monkeypatch.setattr(api_mod, "STORE", store)
    cfg = ConfigManager(store)

    store.upsert_config(
        "intent",
        "PausedIntent",
        {"intent_id": "PausedIntent", "description": "old"},
        status="INACTIVE",
    )
    cfg.upsert_intent("PausedIntent", "new")
    intent = store.get_config("intent", "PausedIntent")
    assert intent["status"] == "INACTIVE"
    assert intent["description"] == "new"

    store.upsert_config(
        "strategy",
        "paused_strategy",
        {"strategy_id": "paused_strategy", "format_type": "paragraph"},
        status="INACTIVE",
    )
    cfg.upsert_strategy("paused_strategy", "comparison_table")
    strategy = store.get_config("strategy", "paused_strategy")
    assert strategy["status"] == "INACTIVE"
    assert strategy["format_type"] == "comparison_table"

    store.upsert_config(
        "policy",
        "PausedIntent#_default#paused_strategy",
        {
            "domain": "finance",
            "intent": "PausedIntent",
            "topic": "_default",
            "strategy_id": "paused_strategy",
            "policy_version": "v1",
            "exploration_constant": 1.0,
        },
        status="INACTIVE",
    )
    cfg.upsert_policy("finance", "PausedIntent", "_default", "paused_strategy", exploration_constant=2.0)
    policy = store.get_config("policy", "PausedIntent#_default#paused_strategy")
    assert policy["status"] == "INACTIVE"
    assert policy["exploration_constant"] == 2.0

    store.upsert_config(
        "offer_policy",
        "paused_topic",
        {"domain": "finance", "offer_type": "old", "description": "old"},
        status="INACTIVE",
    )
    api_mod.upsert_offer({
        "topic": "paused_topic",
        "offer_type": "new",
        "description": "new",
    })
    offer = store.get_config("offer_policy", "paused_topic")
    assert offer["status"] == "INACTIVE"
    assert offer["offer_type"] == "new"


def test_cleanup_non_canonical_intents_removes_stale_policy_rows(monkeypatch):
    from ape.config.seed import cleanup_non_canonical_intents

    store = _store(monkeypatch)
    store.upsert_config(
        "intent",
        "Advisory",
        {"intent_id": "Advisory", "description": "stale custom intent"},
    )
    store.upsert_config(
        "policy",
        "Advisory#_default#standard_llm",
        {
            "domain": "finance",
            "intent": "Advisory",
            "topic": "_default",
            "strategy_id": "standard_llm",
            "policy_version": "v1",
            "exploration_constant": 1.0,
        },
    )

    result = cleanup_non_canonical_intents(store)

    assert result == {"intents_deleted": 1, "policies_deleted": 1}
    assert store.get_active_config("intent", "Advisory") is None
    assert store.config.count_documents({"entity_type": "policy", "intent": "Advisory"}) == 0


def test_reask_same_question_is_analytics_only_for_bandit(monkeypatch):
    import ape.orchestrator as orch_mod
    from ape.orchestrator import ApeOrchestrator

    store = _store(monkeypatch)
    # Simulate a stale/misconfigured DB row: even if the signal accidentally has
    # a format category, consumers=["analytics"] must keep it out of bandit UCB.
    store.config.update_one(
        {"entity_type": "signal_routing", "entity_id": "reask_same_question"},
        {"$set": {
            "format_relevant": True,
            "format_category": "inferred_negative",
            "consumers": ["analytics"],
        }},
    )

    signals = ["no_signal", "reask_same_question"]

    def fake_classify(client, model, query, history, prev_format=None):
        return {
            "intent": "Definitional",
            "intent_confidence": 0.99,
            "domain": "finance",
            "topic": "_all",
            "signal": signals.pop(0),
        }

    monkeypatch.setattr(orch_mod, "classify_and_detect", fake_classify)

    orch = ApeOrchestrator(client=object(), model="fake", store=store, domain="finance")
    first = orch.handle_turn("alice", "what is duration?", generate=False)
    first_record = store.get_response(first["response_id"])

    orch.handle_turn("alice", "what is duration?", session_id=first["session_id"], generate=False)

    finalized = store.get_response(first["response_id"])
    row = store.bandit_state.find_one({
        "user_id_hash": first_record["user_id_hash"],
        "domain": "finance",
        "intent": "Definitional",
        "topic": "_all",
        "strategy": first_record["selected_strategy"],
    })

    assert finalized["signal"] == "reask_same_question"
    assert finalized["reward_status"] == "APPLIED"
    assert finalized.get("normalized_reward") is None
    assert finalized["content_reward"] == -1.0
    assert row["total_reward"] == 0.0
    assert row["avg_reward"] == 0.0


def test_turn_routes_raise_422_before_streaming_for_missing_strategy_config(monkeypatch):
    import ape.api as api_mod
    from ape.models import TurnRequest
    from ape.orchestrator import NoActiveStrategiesError

    class FakeOrchestrator:
        def handle_turn(self, **kwargs):
            raise NoActiveStrategiesError("unmapped", "_all")

        def handle_turn_streaming(self, **kwargs):
            raise NoActiveStrategiesError("unmapped", "_all")

    monkeypatch.setattr(api_mod, "ORCHESTRATOR", FakeOrchestrator())

    req = TurnRequest(user_id="alice", query="hello")

    with pytest.raises(HTTPException) as normal_exc:
        asyncio.run(api_mod.post_turn(req))
    assert normal_exc.value.status_code == 422
    assert normal_exc.value.detail == "No active strategies for intent: unmapped topic: _all"

    with pytest.raises(HTTPException) as stream_exc:
        asyncio.run(api_mod.post_turn_stream(req))
    assert stream_exc.value.status_code == 422
    assert stream_exc.value.detail == "No active strategies for intent: unmapped topic: _all"
