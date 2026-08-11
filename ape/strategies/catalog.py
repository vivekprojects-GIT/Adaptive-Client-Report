"""
INTENT_STRATEGIES — for each D2 intent, the candidate answer formats (arms).

═══════════════════════════════════════════════════════════════════════════
THIS IS D2 ONLY
═══════════════════════════════════════════════════════════════════════════

    D2  a client's QUESTION about their report -> how to ANSWER it.
        Intent is classified from natural language. Arms are answer formats.
        That is what this file describes.

    D1  report type -> which report TEMPLATE to build.
        Report type is SELECTED, never classified, and its arms are templates.
        That lives in config (`report_type` / `template` entities), not here.

═══════════════════════════════════════════════════════════════════════════
WHY THIS FILE IS LOAD-BEARING
═══════════════════════════════════════════════════════════════════════════

`cleanup_non_canonical_intents` runs on EVERY startup and deletes any intent
or policy whose id is not a key here. So this dict is not documentation — it
is the allowlist that decides what survives a restart. Leaving it as the old
chat taxonomy silently wiped the entire D2 configuration on every boot.

Add an intent here before seeding it, or it will be deleted the next time
the app starts.

Catalog order matters: it is the tiebreaker when several arms have count=0,
so round-robin visits them in the order listed.
"""

from __future__ import annotations

from typing import Dict, List


INTENT_STRATEGIES: Dict[str, List[str]] = {
    "report_summary": [
        "concise_direct",
        "structured_bullets",
        "detailed_narrative",
    ],
    "performance_question": [
        "concise_direct",
        "comparison_table",
        "detailed_narrative",
        "visual_explanation",
    ],
    "benchmark_comparison": [
        "comparison_table",
        "concise_direct",
        "visual_explanation",
    ],
    "allocation_question": [
        "visual_explanation",
        "comparison_table",
        "structured_bullets",
    ],
    "risk_question": [
        "detailed_narrative",
        "concise_direct",
        "structured_bullets",
    ],
    "holdings_question": [
        "comparison_table",
        "structured_bullets",
        "concise_direct",
    ],
    "fees_cashflow_question": [
        "comparison_table",
        "concise_direct",
        "structured_bullets",
    ],
    "explain_selected_content": [
        "detailed_narrative",
        "concise_direct",
        "step_by_step",
    ],
    "other_report_question": [
        "concise_direct",
        "structured_bullets",
        "detailed_narrative",
    ],
    # Fallback for anything the classifier cannot place. Deliberately a single
    # safe arm: with no idea what was asked, exploring formats is noise.
    "unmapped": [
        "concise_direct",
    ],
}


# Closed set of valid intent labels. Anything else is coerced to "unmapped".
VALID_INTENTS = set(INTENT_STRATEGIES.keys())


# Old chat-product strategy ids. Boot-time reconciliation marks any lingering
# policy or instruction rows for these INACTIVE so the bandit cannot pick them,
# while preserving history for audit.
DEPRECATED_STRATEGY_IDS = (
    "standard_llm",
    "decision_card",
    "pros_cons_table",
    "step_by_step_reasoning",
    "short_paragraph",
    "bullet_summary",
    "analogy_explanation",
    "bullet_contrast",
    "numbered_steps",
    "checklist",
    "phased_workflow",
    "one_liner",
    "definition_plus_example",
    "definition_with_pointer",
    "statement_with_caveats",
    "statement_with_actions",
    "three_section_review",
)
