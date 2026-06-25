from ape.llm.prompts import build_synthesizer_system_prompt
from ape.strategies.instructions import STRATEGY_INSTRUCTIONS


def test_synthesizer_uses_active_instruction_override():
    active = "ACTIVE DB INSTRUCTION: use exactly two labelled bullet blocks."

    prompt = build_synthesizer_system_prompt(
        "bullet_contrast",
        instruction_text=active,
    )

    assert active in prompt
    assert STRATEGY_INSTRUCTIONS["bullet_contrast"] not in prompt


def test_bullet_contrast_fallback_explicitly_forbids_tables():
    prompt = build_synthesizer_system_prompt("bullet_contrast")

    assert "Do not use markdown tables" in prompt
    assert "pipe characters" in prompt
    assert "selected response-format instruction below is mandatory" in prompt
