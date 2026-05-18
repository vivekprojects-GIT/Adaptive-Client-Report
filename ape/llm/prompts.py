"""
Prompt templates for the two LLM calls per turn.

  - CLASSIFIER_PROMPT: single-call extraction of intent, topic, and signal.
  - synthesizer system prompt: built dynamically from strategy instructions.

Both are deliberately short. Long prompts are expensive to send and harder
to audit; keep them readable.
"""

from __future__ import annotations

from ..strategies import STRATEGY_INSTRUCTIONS


CLASSIFIER_PROMPT = """\
You classify chat messages for an adaptive financial assistant.
Strict format compliance is required — your output is parsed and persisted.

INPUT (sent inside the user message):
  PREVIOUS_RESPONSE_FORMAT:    <strategy name | "none">
  PREVIOUS_ASSISTANT_RESPONSE: <text | "none">
  NEW_USER_MESSAGE:            <text>

OUTPUT — return ONE JSON object, exactly in this shape, nothing else:
  {"intent":"<intent>","intent_confidence":<0.0-1.0>,"unmapped_name":<null or snake_case>,
   "topic":"<short snake_case noun phrase the question is about>",
   "signal":"<signal>"}

Example outputs (byte-for-byte format you must produce):
  {"intent":"Definitional","intent_confidence":0.95,"unmapped_name":null,"topic":"roth_ira","signal":"no_signal"}
  {"intent":"Comparison","intent_confidence":0.88,"unmapped_name":null,"topic":"roth_vs_traditional","signal":"deeper_question"}
  {"intent":"unmapped","intent_confidence":0.55,"unmapped_name":"challenge_thinking","topic":"general","signal":"no_signal"}
  // "That was very helpful. What is a 401k?" after a Roth IRA answer:
  {"intent":"Definitional","intent_confidence":0.92,"unmapped_name":null,"topic":"401k","signal":"deeper_question"}
  // "Perfect, thanks!" with no further question:
  {"intent":"unmapped","intent_confidence":0.40,"unmapped_name":"acknowledgment","topic":"general","signal":"it_worked_statement"}

INTENTS (pick based on NEW_USER_MESSAGE only):
  Decision        recommendation        e.g. "Should I X?", "Which X?"
  Explanation     mental model          e.g. "How does X work?", "Why is X?"
  Comparison      side-by-side          e.g. "X vs Y", "difference between"
  Instructional   step-by-step          e.g. "How do I X?", "Walk me through"
  Definitional    short definition      e.g. "What is X?", "Define X"
  Evaluation      validate a plan       e.g. "Does this look right?"
  unmapped        none of the above (provide a snake_case unmapped_name)

Confidence: 0.85+ clear · 0.6-0.84 ambiguous · <0.6 best guess.

SIGNALS (how NEW_USER_MESSAGE reacts to PREVIOUS_ASSISTANT_RESPONSE):

  format_change_request   User asks for a DIFFERENT SHAPE of the same answer.
                          ✓ "shorter please", "as a table", "use bullets",
                            "redo as an analogy", "TL;DR?"
                          ✗ NOT for asking more content ("explain more" → deeper_question)

  content_correction      User asserts a SPECIFIC FACT in the answer is wrong.
                          ✓ "actually the limit is $23k, not $22k"
                          ✓ "that's outdated — the rule changed in 2024"
                          ✗ NOT vague disagreement without a counter-fact

  reask_same_question     User repeats the SAME question, possibly rephrased,
                          because the prior answer missed or confused them.
                          ✓ "I meant — what IS a Roth IRA?" after a Roth answer
                          ✗ A NEW but related question is deeper_question, not reask

  it_worked_statement     PURE acknowledgment, NO new question or request.
                          ✓ "perfect, thanks", "got it", "that makes sense"
                          ✓ "that was very helpful" (statement, ends)
                          ✗ "Thanks. What's the contribution limit?" → deeper_question
                              (the question wins — see PRECEDENCE rule 3)

  deeper_question         A topic-related follow-up that BUILDS on the prior answer.
                          ✓ "And what about Roth?" after a 401k answer
                          ✓ "Thanks. So how is it taxed?" (ack + question → question wins)
                          ✓ "Interesting — what's the catch-up provision?"
                          ✗ Fresh question on an UNRELATED topic → no_signal

  no_signal               First turn, OR a fresh question on a topic unrelated
                          to the prior answer, OR no reaction at all.
                          ✓ "What is dollar-cost averaging?" after a Roth IRA answer
                          ✗ Any clear acknowledgment or topic-continuing question

PRECEDENCE — when a message could plausibly match multiple signals, decide in
this order (first match wins):
  1. Format request beats everything else.
  2. Content correction beats acknowledgment.
  3. Acknowledgment + new topic-related question → deeper_question (the question
     wins; the polite intro does NOT downgrade it to it_worked_statement).
  4. Bare acknowledgment with NO question and NO request → it_worked_statement.
  5. Otherwise → no_signal.

NEVER emit: thumbs_up, thumbs_down, copy_save, regenerate_click, session_abandon (UI-only).

RULES:
  1. Intent is decided ONLY by NEW_USER_MESSAGE.
  2. unmapped_name is non-null IF AND ONLY IF intent = "unmapped".
  3. topic is a short snake_case noun phrase. Use "general" if no clear topic.
  4. Output ONLY the JSON object — no prose, no markdown fences, no commentary.
"""


SYNTHESIZER_OUTPUT_CONTRACT = """\
OUTPUT FORMAT — wrap your reply as a single JSON object, NOTHING else:
  {"rendered_format": "<one of: paragraph, bulleted_list, numbered_steps, \
comparison_table, data_table, decision_recommendation, analogy_explainer, hybrid>",
   "response": "<the actual answer in markdown>"}
Choose `rendered_format` HONESTLY based on the SHAPE of `response`.
Do not include any text outside the JSON object.\
"""


def build_synthesizer_system_prompt(strategy: str) -> str:
    """Compose the synthesizer's system prompt from guardrails + strategy + wrapper."""
    instruction = STRATEGY_INSTRUCTIONS.get(strategy, STRATEGY_INSTRUCTIONS["standard_llm"])
    return (
        "You are a financial assistant. Use prior turns when relevant.\n"
        "Write clean markdown with concise sections and bullets when useful.\n"
        "Do not use emojis, decorative symbols, or overly casual phrasing.\n"
        f"{instruction}\n"
        "\n"
        f"{SYNTHESIZER_OUTPUT_CONTRACT}"
    )
