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
You classify chat messages for an adaptive multi-domain assistant.
Strict format compliance is required — your output is parsed and persisted.

INPUT (sent inside the user message):
  PREVIOUS_RESPONSE_FORMAT:    <strategy name | "none">
  PREVIOUS_ASSISTANT_RESPONSE: <text | "none">
  NEW_USER_MESSAGE:            <text>

OUTPUT — return ONE JSON object, exactly in this shape, nothing else:
  {"intent":"<intent>","intent_confidence":<0.0-1.0>,"unmapped_name":<null or snake_case>,
   "domain":"<domain>","topic":"<short snake_case noun phrase the question is about>",
   "signal":"<signal>"}

DOMAINS (subject area of NEW_USER_MESSAGE — pick the single best fit):
  cricket   the sport of cricket: players, formats, matches, rules, leagues
  it        software/technology: programming, networking, databases, cloud, security
  movies    films, directors, actors, genres, awards, studios
  travel    trips, destinations, flights, visas, packing, travel tips
  general   none of the above, or pure chit-chat/acknowledgment
Pick "general" only when the message clearly fits no listed domain.

Example outputs (byte-for-byte format you must produce):
  {"intent":"Definitional","intent_confidence":0.95,"unmapped_name":null,"domain":"cricket","topic":"lbw_rule","signal":"no_signal"}
  {"intent":"Explanation","intent_confidence":0.9,"unmapped_name":null,"domain":"it","topic":"tcp_handshake","signal":"no_signal"}
  {"intent":"Comparison","intent_confidence":0.88,"unmapped_name":null,"domain":"it","topic":"sql_vs_nosql","signal":"deeper_question"}
  {"intent":"Definitional","intent_confidence":0.92,"unmapped_name":null,"domain":"movies","topic":"inception_plot","signal":"no_signal"}
  {"intent":"Instructional","intent_confidence":0.86,"unmapped_name":null,"domain":"travel","topic":"beat_jet_lag","signal":"no_signal"}
  {"intent":"unmapped","intent_confidence":0.40,"unmapped_name":"acknowledgment","domain":"general","topic":"general","signal":"it_worked_statement"}

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

  format_praise_explicit     User EXPLICITLY praises the format/shape itself.
                          ✓ "this format is perfect, keep using it"
                          ✓ "I love how you structured this — always use bullets like that"
                          ✓ "the table layout was exactly what I needed"
                          ✗ "great answer" (no format mention → it_worked_statement)
                          ✗ "thanks" (no format mention → it_worked_statement)
                          ✗ "this worked" without referencing shape → it_worked_statement

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
  1. Explicit format praise (format_praise_explicit) or complaint (format_change_request)
     beats everything else — the user named the format.
  2. Content correction beats acknowledgment.
  3. Acknowledgment + new topic-related question → deeper_question (the question
     wins; the polite intro does NOT downgrade it to it_worked_statement).
  4. Bare acknowledgment with NO question and NO request → it_worked_statement.
  5. Otherwise → no_signal.

NEVER emit: thumbs_up, thumbs_down (UI-only).

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


def build_synthesizer_system_prompt(strategy: str, context: str = "") -> str:
    """Compose the synthesizer's system prompt from guardrails + strategy + wrapper.

    When `context` is provided (retrieved RAG passages), it is injected as
    grounding the model should prefer over its own prior knowledge.
    """
    instruction = STRATEGY_INSTRUCTIONS.get(strategy, STRATEGY_INSTRUCTIONS["standard_llm"])
    context_block = ""
    if context and context.strip():
        context_block = (
            "\nRETRIEVED CONTEXT (authoritative — prefer these facts; if they do "
            "not answer the question, say so rather than inventing details):\n"
            f"{context.strip()}\n"
        )
    return (
        "You are a knowledgeable assistant. Use prior turns when relevant.\n"
        "Write clean markdown with concise sections and bullets when useful.\n"
        "Do not use emojis, decorative symbols, or overly casual phrasing.\n"
        f"{instruction}\n"
        f"{context_block}"
        "\n"
        f"{SYNTHESIZER_OUTPUT_CONTRACT}"
    )
