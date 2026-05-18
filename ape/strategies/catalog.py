"""
INTENT_STRATEGIES — for each intent, the candidate strategies (bandit arms).

The bandit explores within an intent's catalog. Catalog order matters: it's
the tiebreaker when multiple strategies have count=0 (UCB's infinite explore
bonus picks them in catalog order on first encounter).

`standard_llm` is included as the first option for every non-trivial intent.
It's the "no format constraint" baseline — the LLM picks its own shape.
For unmapped intents, it's the only option.
"""

from __future__ import annotations

from typing import Dict, List


INTENT_STRATEGIES: Dict[str, List[str]] = {
    "Decision": [
        "standard_llm",
        "decision_card",
        "pros_cons_table",
        "step_by_step_reasoning",
    ],
    "Explanation": [
        "standard_llm",
        "short_paragraph",
        "bullet_summary",
        "analogy_explanation",
    ],
    "Comparison": [
        "standard_llm",
        "comparison_table",
        "pros_cons_table",
        "bullet_contrast",
    ],
    "Instructional": [
        "standard_llm",
        "numbered_steps",
        "checklist",
        "phased_workflow",
    ],
    "Definitional": [
        "standard_llm",
        "one_liner",
        "definition_plus_example",
        "definition_with_pointer",
    ],
    "Evaluation": [
        "standard_llm",
        "affirm_with_calibration",
        "affirm_and_strengthen",
        "concerned_pushback",
    ],
    "unmapped": ["standard_llm"],
}


# Closed set of valid intent labels. Anything else gets coerced to "unmapped"
# by the classifier output normalizer.
VALID_INTENTS = set(INTENT_STRATEGIES.keys())
