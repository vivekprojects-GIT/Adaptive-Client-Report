"""
Smoke tests — verify the core modules import cleanly and the bandit math
works end-to-end without an LLM.

Run: pytest tests/test_smoke.py -v
"""

from __future__ import annotations

import os
import tempfile

from ape.bandit import compute_rewards, select_strategy
from ape.signals import (
    REWARD_SCALE,
    SIGNAL_ROUTING,
    canonicalize_topic,
    resolve_signal,
)
from ape.store import SqliteStore, new_session_id, new_turn_id, utcnow_iso
from ape.strategies import INTENT_STRATEGIES, compute_format_compliance


def test_canonicalize_topic():
    assert canonicalize_topic("Roth IRA") == "roth_ira"
    assert canonicalize_topic("roth-ira") == "roth_ira"
    assert canonicalize_topic("ROTH IRA") == "roth_ira"
    assert canonicalize_topic("  ") == "general"
    assert canonicalize_topic(None) == "general"
    assert canonicalize_topic("cryptocurrency") == "general"  # not in whitelist


def test_signal_routing_completeness():
    """Every signal in routing must have a corresponding reward_scale entry."""
    for signal, (fmt_str, ctn_str) in SIGNAL_ROUTING.items():
        assert fmt_str in REWARD_SCALE, f"{signal!r} format_strength={fmt_str!r}"
        assert ctn_str in REWARD_SCALE, f"{signal!r} content_strength={ctn_str!r}"


def test_compute_rewards_thumbs_up():
    c_rel, f_rel, c_rew, f_rew = compute_rewards("thumbs_up")
    assert c_rel and f_rel
    assert c_rew == 2 and f_rew == 2


def test_compute_rewards_format_change_request():
    c_rel, f_rel, c_rew, f_rew = compute_rewards("format_change_request")
    assert f_rel and not c_rel
    assert f_rew == -2
    assert c_rew is None  # NOT_RECORDED


def test_compute_rewards_no_signal():
    c_rel, f_rel, c_rew, f_rew = compute_rewards("no_signal")
    assert not c_rel and not f_rel
    assert c_rew is None and f_rew is None


def test_resolve_signal_ui_wins():
    # Both UI and LLM signals fire — UI must win
    assert resolve_signal({"thumbs_up": 1}, "deeper_question") == "thumbs_up"
    assert resolve_signal({"thumbs_down": 1}, "it_worked_statement") == "thumbs_down"


def test_resolve_signal_priority_ladder():
    # Multiple UI signals — highest priority wins
    assert resolve_signal({"thumbs_up": 1, "copy_save": 1}, None) == "thumbs_up"
    assert resolve_signal({"thumbs_down": 1, "copy_save": 1}, None) == "thumbs_down"
    assert resolve_signal({"regenerate_click": 1, "thumbs_up": 1}, None) == "regenerate_click"


def test_resolve_signal_falls_through():
    # No UI, fall to LLM signal
    assert resolve_signal(None, "deeper_question") == "deeper_question"
    # No UI and no LLM
    assert resolve_signal(None, None) == "no_signal"
    assert resolve_signal({}, None) == "no_signal"


def test_format_compliance_standard_llm_always_compliant():
    assert compute_format_compliance("standard_llm", "paragraph") is True
    assert compute_format_compliance("standard_llm", "hybrid") is True


def test_format_compliance_strict_match():
    assert compute_format_compliance("decision_card", "decision_recommendation") is True
    assert compute_format_compliance("decision_card", "paragraph") is False


def test_select_strategy_unpulled_first():
    """All counts=0 → first strategy in catalog wins (catalog-order tiebreak)."""
    intent = "Definitional"
    strategies = INTENT_STRATEGIES[intent]
    cell = {
        "strategies": {s: {"format_count": 0, "format_avg_reward": 0.0} for s in strategies}
    }
    result = select_strategy(cell, intent)
    assert result["selected_strategy"] == strategies[0]
    assert result["selection_method"] == "ucb"


def test_select_strategy_ucb_picks_winner():
    """With pulls accumulated, UCB picks the highest score."""
    intent = "Definitional"
    strategies = INTENT_STRATEGIES[intent]
    cell = {
        "strategies": {
            "standard_llm":             {"format_count": 2, "format_avg_reward": 2.0,
                                         "content_count": 2, "content_avg_reward": 2.0},
            "one_liner":                {"format_count": 1, "format_avg_reward": -2.0,
                                         "content_count": 1, "content_avg_reward": -1.0},
            "definition_plus_example":  {"format_count": 2, "format_avg_reward": 1.5,
                                         "content_count": 2, "content_avg_reward": 1.5},
            "definition_with_pointer":  {"format_count": 1, "format_avg_reward": 0.0,
                                         "content_count": 1, "content_avg_reward": 1.0},
        }
    }
    result = select_strategy(cell, intent)
    # standard_llm has highest avg (2.0); should win UCB even with smaller explore bonus
    assert result["selected_strategy"] == "standard_llm"


def test_store_lifecycle():
    """End-to-end: create session, finalize a turn, verify bandit state."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    os.unlink(db_path)  # let SqliteStore create it

    try:
        store = SqliteStore(path=db_path)
        ts = utcnow_iso()
        session_id = new_session_id("alice")
        turn_id = new_turn_id()

        # Create session
        store.upsert_session(session_id, "alice", ts)

        # Lazy-create a cell
        cell = store.get_or_create_cell(
            "alice", "roth_ira", "Definitional",
            INTENT_STRATEGIES["Definitional"],
        )
        assert len(cell["strategies"]) == 4
        assert all(s["format_count"] == 0 for s in cell["strategies"].values())

        # Record a finalized turn with thumbs_up on a Definitional strategy
        store.record_turn({
            "turn_id":             turn_id,
            "session_id":          session_id,
            "user_id":             "alice",
            "ts":                  ts,
            "topic":               "roth_ira",
            "intent":              "Definitional",
            "intent_confidence":   0.95,
            "low_confidence_flag": 0,
            "unmapped_name":       None,
            "selected_strategy":   "definition_plus_example",
            "selection_method":    "ucb",
            "suggested_format":    "definition_plus_example",
            "rendered_format":     "paragraph",
            "format_compliance":   1,
            "ui_signal":           "thumbs_up",
            "llm_signal":          None,
            "signal":              "thumbs_up",
            "raw_ui_signals":      ["thumbs_up"],
            "content_relevant":    1,
            "format_relevant":     1,
            "content_reward":      2,
            "format_reward":       2,
            "query_text":          "What is a Roth IRA?",
            "response_text":       "...",
        })

        # Bandit state should reflect the +2/+2 update
        cell2 = store.get_or_create_cell(
            "alice", "roth_ira", "Definitional",
            INTENT_STRATEGIES["Definitional"],
        )
        dpe = cell2["strategies"]["definition_plus_example"]
        assert dpe["format_count"] == 1, f"expected 1, got {dpe['format_count']}"
        assert dpe["format_total_reward"] == 2
        assert dpe["format_avg_reward"] == 2.0
        assert dpe["content_count"] == 1
        assert dpe["content_avg_reward"] == 2.0

        # Rebuild from turn_record should be idempotent
        rebuilt = store.rebuild_bandit_state_from_turns()
        assert rebuilt >= 1

        # Close the connection before unlinking on Windows
        store.conn.close()
    finally:
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass    # leave for OS cleanup; not a test failure


if __name__ == "__main__":
    test_canonicalize_topic()
    test_signal_routing_completeness()
    test_compute_rewards_thumbs_up()
    test_compute_rewards_format_change_request()
    test_compute_rewards_no_signal()
    test_resolve_signal_ui_wins()
    test_resolve_signal_priority_ladder()
    test_resolve_signal_falls_through()
    test_format_compliance_standard_llm_always_compliant()
    test_format_compliance_strict_match()
    test_select_strategy_unpulled_first()
    test_select_strategy_ucb_picks_winner()
    test_store_lifecycle()
    print("All smoke tests passed.")
