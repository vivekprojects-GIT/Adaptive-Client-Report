from ape.llm.prompts import build_synthesizer_system_prompt
from ape.llm.synthesizer import parse_generation_wrapper
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


def test_bullet_contrast_repairs_markdown_table_to_bullets():
    raw = """
    {
      "rendered_format": "comparison_table",
      "response": "| Feature | Roth IRA | Traditional IRA |\\n|---|---|---|\\n| Tax | After-tax | Pre-tax |\\n| RMDs | None | Required |"
    }
    """

    rendered_format, response = parse_generation_wrapper(raw, "bullet_contrast")

    assert rendered_format == "bulleted_list"
    assert "**Roth IRA**" in response
    assert "**Traditional IRA**" in response
    assert "- Tax: After-tax" in response
    assert "- RMDs: Required" in response
    assert "|" not in response


def test_table_strategy_preserves_data_table_label():
    raw = """
    {
      "rendered_format": "data_table",
      "response": "| Pros | Cons |\\n|---|---|\\n| Simple | Less custom |"
    }
    """

    rendered_format, response = parse_generation_wrapper(raw, "pros_cons_table")

    assert rendered_format == "data_table"
    assert "| Pros | Cons |" in response
