"""Seed instructions, signal routing and the reward scale for report chat.

Completes the D2 configuration:

  instructions   one per answer strategy — the prompt the synthesiser follows
  signal routing what each observable client action means, on both axes
  reward scale   what each category is worth

DESIGN RULE CARRIED OVER FROM APE: instructions are PURE FORMAT. They say
nothing about content, tone, or what the answer should conclude — only what
shape it takes. Grounding ("answer only from the supplied report context")
lives in the system prompt, where it applies to every strategy equally and
cannot be weakened by a strategy author.

    python scripts/seed_instructions_signals.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

from ape.config import ConfigManager  # noqa: E402
from ape.store import MongoStore  # noqa: E402

VERSION = "v1"

# ---------------------------------------------------------------------------
# Instructions — one per D2 arm. Format only.
# ---------------------------------------------------------------------------
INSTRUCTIONS = {
    "concise_direct":
        "Answer in at most three sentences. Lead with the figure or the direct "
        "answer, then at most one sentence of context. No preamble and no "
        "restating of the question.",

    "structured_bullets":
        "Answer as three to five bullet points, each starting with '- ' and each "
        "no longer than one line. No introductory sentence. Put the point that "
        "answers the question first.",

    "comparison_table":
        "Answer as a markdown table with the compared items as rows. Include the "
        "figures being compared and a difference column where a difference is "
        "meaningful. At most one sentence beneath the table.",

    "step_by_step":
        "Answer as numbered steps, in the order things happened or should be "
        "understood. One idea per step, no step longer than two sentences.",

    "visual_explanation":
        "Lead with the chart or figure that answers the question, naming the "
        "report block it comes from, then explain what it shows in at most two "
        "sentences. Do not repeat every number already visible in the visual.",

    "detailed_narrative":
        "Answer in two to three short paragraphs. State the figure, then explain "
        "what drove it and what it means for this client. Define any technical "
        "term inline the first time it is used.",
}

# ---------------------------------------------------------------------------
# Signal routing.
#
# Two axes, deliberately independent:
#   FORMAT  — was this the right SHAPE of answer?   (drives the D2 bandit)
#   CONTENT — was the answer CORRECT / sufficient?  (analytics + escalation)
#
# The distinction that matters most, from the spec: "this number is wrong" is
# a CONTENT failure and must NOT penalise the answer format. Punishing the
# shape for a data error teaches the bandit the wrong lesson and would slowly
# drive every client toward whichever format happened to have fewer data bugs.
#
# `consumers` gates who may act on a signal. Only signals listing "bandit"
# can move an arm; everything else is evidence for humans and dashboards.
# ---------------------------------------------------------------------------
E_POS, E_NEG = "explicit_positive", "explicit_negative"
I_POS, I_NEG = "inferred_positive", "inferred_negative"
BANDIT = ["bandit", "analytics"]
ANALYTICS = ["analytics"]

SIGNALS = [
    # name,                    src,      fmt_cat, cont_cat, consumers,  freq,      quality
    ("thumbs_up",              "ui",     I_POS,   I_POS,    BANDIT,     "moderate", "medium"),
    ("thumbs_down",            "ui",     I_NEG,   I_NEG,    BANDIT,     "moderate", "medium"),
    ("response_copy",          "ui",     I_POS,   I_POS,    BANDIT,     "moderate", "medium"),

    # Explicit format requests — the client is telling us the shape was wrong.
    # Strongest format evidence we ever get, and silent on content.
    ("format_change_request",  "llm",    E_NEG,   None,     BANDIT,     "moderate", "high"),
    ("table_request",          "llm",    E_NEG,   None,     BANDIT,     "moderate", "high"),
    ("visual_request",         "llm",    E_NEG,   None,     BANDIT,     "rare",     "high"),
    ("comparison_request",     "llm",    E_NEG,   None,     BANDIT,     "moderate", "high"),
    ("exact_numbers_request",  "llm",    E_NEG,   None,     BANDIT,     "moderate", "high"),
    ("more_detail_request",    "llm",    E_NEG,   None,     BANDIT,     "moderate", "high"),
    ("simplify_request",       "llm",    E_NEG,   None,     BANDIT,     "moderate", "high"),
    ("concise_request",        "llm",    E_NEG,   None,     BANDIT,     "rare",     "high"),
    ("step_by_step_request",   "llm",    E_NEG,   None,     BANDIT,     "rare",     "high"),
    ("keep_format_request",    "llm",    E_POS,   None,     BANDIT,     "rare",     "high"),
    ("format_positive_feedback", "llm",  E_POS,   None,     BANDIT,     "rare",     "high"),

    # Content axis. content_correction is explicitly NOT bandit-consumed.
    ("content_correction",     "llm",    None,    E_NEG,    ANALYTICS,  "rare",     "high"),
    ("reask_same_question",    "llm",    I_NEG,   I_NEG,    BANDIT,     "moderate", "medium"),
    ("clarification_request",  "llm",    I_NEG,   None,     BANDIT,     "moderate", "low"),
    ("successful_resolution",  "llm",    I_POS,   I_POS,    BANDIT,     "moderate", "medium"),

    # Viewer behaviour. Weak on its own — highlight and dwell say a passage drew
    # attention, not whether it worked, so they inform analytics only.
    ("chart_expand",           "derived", I_POS,  None,     BANDIT,     "moderate", "low"),
    ("table_expand",           "derived", I_POS,  None,     BANDIT,     "moderate", "low"),
    ("pdf_download",           "derived", I_POS,  None,     BANDIT,     "moderate", "low"),
    ("citation_click",         "derived", I_POS,  None,     ANALYTICS,  "moderate", "low"),
    ("block_highlight",        "derived", None,   None,     ANALYTICS,  "frequent", "low"),
    ("section_dwell",          "derived", None,   None,     ANALYTICS,  "frequent", "low"),
    ("report_open",            "derived", None,   None,     ANALYTICS,  "frequent", "low"),

    ("no_signal",              "system",  None,   None,     [],         "frequent", "low"),
]

# ---------------------------------------------------------------------------
# Reward scale. Explicit statements outweigh inferred behaviour 2:1.
# ---------------------------------------------------------------------------
REWARD_SCALE = {
    E_POS: 2.0,
    E_NEG: -2.0,
    I_POS: 1.0,
    I_NEG: -1.0,
}


def main() -> None:
    store = MongoStore()
    cfg = ConfigManager(store)

    for strategy_id, text in INSTRUCTIONS.items():
        cfg.publish_instruction(strategy_id=strategy_id, version=VERSION,
                                instruction_text=text, changed_by="seed_instr")
        cfg.activate_instruction(strategy_id=strategy_id, version=VERSION,
                                 changed_by="seed_instr")
    print(f"instructions : {len(INSTRUCTIONS)} published + activated ({VERSION})")

    for i, (name, src, fmt, cont, cons, freq, qual) in enumerate(SIGNALS, start=1):
        cfg.update_signal_rule(
            signal_name=name,
            format_relevant=fmt is not None,
            content_relevant=cont is not None,
            format_category=fmt,
            content_category=cont,
            source=src,
            feature_id=i,
            expected_frequency=freq,
            evidence_quality=qual,
            consumers=cons,
            changed_by="seed_instr",
        )
    print(f"signals      : {len(SIGNALS)}")

    for cat, val in REWARD_SCALE.items():
        cfg.update_reward_value(category=cat, normalized_reward=val,
                                changed_by="seed_instr")
    print(f"reward scale : {len(REWARD_SCALE)}")

    print()
    bandit = [s[0] for s in SIGNALS if "bandit" in s[4]]
    print(f"bandit-consumed signals ({len(bandit)}):")
    print("  " + ", ".join(bandit))
    print()
    print("analytics-only (cannot move an arm):")
    print("  " + ", ".join(s[0] for s in SIGNALS if "bandit" not in s[4]))


if __name__ == "__main__":
    main()
