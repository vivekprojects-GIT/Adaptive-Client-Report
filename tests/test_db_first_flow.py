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
