"""
STRATEGY_INSTRUCTIONS — one-line directive per strategy.

Each strategy maps to a single sentence appended to the synthesizer's system
prompt. There are NO large rulebooks — every strategy is one sentence so the
catalog stays inspectable.

Adding a new strategy:
  1. Add an entry here.
  2. Add it to the relevant intent(s) in `catalog.py`.
  3. Add its expected `rendered_format` in `FORMAT_EXPECTATIONS` below
     so format_compliance computes correctly.
"""

from __future__ import annotations

from typing import Dict


STRATEGY_INSTRUCTIONS: Dict[str, str] = {
    "standard_llm":             "Respond in whatever format you think best fits the question.",

    # Decision strategies
    "decision_card":            "Format your response as a decision card with a clear recommendation and 2-3 supporting reasons.",
    "pros_cons_table":          "Format your response as a two-column pros/cons table.",
    "step_by_step_reasoning":   "Walk through your reasoning as a numbered list of steps before stating the final recommendation.",

    # Explanation strategies
    "short_paragraph":          "Respond in a short paragraph (3-4 sentences max).",
    "bullet_summary":           "Respond as a flat bulleted list of key points.",
    "analogy_explanation":      "Explain using a simple, concrete analogy.",

    # Comparison strategies
    "comparison_table":         "Produce a markdown table comparing the options across relevant dimensions. Return only the table.",
    "bullet_contrast":          "Produce two parallel labelled bullet blocks with the same number of bullets. Do not use markdown tables, pipe characters, or table headers. Return only the two bullet blocks.",

    # Instructional strategies
    "numbered_steps":           "Provide numbered, sequential action steps.",
    "checklist":                "Provide a markdown checklist using `- [ ]` items.",
    "phased_workflow":          "Group the answer into 2-3 named phases with steps under each phase.",

    # Definitional strategies
    "one_liner":                "Respond in exactly one sentence.",
    "definition_plus_example":  "Give a one-sentence definition followed by a concrete example.",
    "definition_with_pointer":  "Give a one-sentence definition and one pointer for next step.",

    # Evaluation strategies
    "affirm_with_calibration":  "Affirm what is correct first, then add calibration notes about what to watch.",
    "affirm_and_strengthen":    "Affirm the plan and suggest 2-3 ways to strengthen it.",
    "concerned_pushback":       "Lead with a concrete concern, explain why, then suggest an adjustment.",
}


# Expected rendered_format per strategy. Used by `compute_format_compliance`
# to check whether the LLM honored the strategy instruction.
# `standard_llm` is special: it's always compliant by definition (no specific
# shape was requested).
FORMAT_EXPECTATIONS: Dict[str, str] = {
    "standard_llm":             "*",   # any rendered_format is compliant
    "decision_card":            "decision_recommendation",
    "pros_cons_table":          "comparison_table",
    "step_by_step_reasoning":   "numbered_steps",
    "short_paragraph":          "paragraph",
    "bullet_summary":           "bulleted_list",
    "analogy_explanation":      "analogy_explainer",
    "comparison_table":         "comparison_table",
    "bullet_contrast":          "bulleted_list",
    "numbered_steps":           "numbered_steps",
    "checklist":                "bulleted_list",
    "phased_workflow":          "numbered_steps",
    "one_liner":                "paragraph",
    "definition_plus_example":  "paragraph",
    "definition_with_pointer":  "paragraph",
    "affirm_with_calibration":  "paragraph",
    "affirm_and_strengthen":    "paragraph",
    "concerned_pushback":       "paragraph",
}


# Closed set of `rendered_format` values the LLM may declare.
RENDERED_FORMAT_VOCABULARY = {
    "paragraph",
    "bulleted_list",
    "numbered_steps",
    "comparison_table",
    "data_table",
    "decision_recommendation",
    "analogy_explainer",
    "hybrid",
}


def compute_format_compliance(suggested_strategy: str, rendered_format: str) -> bool:
    """Per spec §17: standard_llm is always compliant; other strategies are
    compliant iff `rendered_format` matches the strategy's expected format.

    Unknown strategies default to compliant (defensive — don't penalize the
    bandit for an incomplete config).
    """
    if suggested_strategy == "standard_llm":
        return True
    expected = FORMAT_EXPECTATIONS.get(suggested_strategy)
    if expected is None or expected == "*":
        return True
    return rendered_format == expected
