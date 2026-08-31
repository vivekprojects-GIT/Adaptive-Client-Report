"""Podcast: the spoken conversion, and the order it must happen in."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ape.reporting.podcast import to_spoken, _spoken_number, code_built_script
from ape.reporting.grounding import derived_facts, validate_block


def _check(text, facts):
    block = {"block_id": "p", "block_type": "narrative",
             "source_refs": ["portfolio_value"], "data": {"text": text}}
    return [f for f in validate_block(block, facts, locale="en")
            if f.kind == "ungrounded_number"]


FACTS = derived_facts({
    "portfolio_value": 1249327.22,
    "quarter_return_pct": 2.76,
    "benchmark_return_pct": 2.99,
})


def test_spelling_numbers_out_makes_the_gate_blind():
    """The reason validation runs BEFORE the spoken conversion.

    TTS reads "£1,249,327.22" badly, so the obvious instruction is "spell
    the figures out". Do that in the prompt and the grounding gate silently
    stops working: it finds claims by matching digit strings, and a script
    written in words contains none.

    This test exists to make that failure loud. If it ever starts failing —
    if a spelled-out invented figure gets BLOCKED — then the validator has
    learned to read words and this ordering constraint can be revisited.
    """
    invented = "GUEST: It was £1,249,327.22, up 7.41%."
    assert _check(invented, FACTS), "digits form should be caught"
    assert not _check(to_spoken(invented), FACTS), (
        "spelled-out form is NOT caught — which is exactly why the pipeline "
        "must validate first and convert second")


def test_true_figures_survive_both_forms():
    true = "GUEST: It was £1,249,327.22, up 2.76%."
    assert not _check(true, FACTS)
    assert "two point seven six percent" in to_spoken(true)


def test_conversion_shapes():
    assert _spoken_number("2.76%") == "two point seven six percent"
    assert _spoken_number("-0.23%") == "minus zero point two three percent"
    assert _spoken_number("£1") == "one pound"
    assert "million" in _spoken_number("£1,249,327.22")


def test_period_codes_and_prose_commas_are_left_alone():
    """2026Q2 is a period code, not a number; a comma is not a figure.

    Both crashed or corrupted an earlier version of the converter: a bare
    "[\\d,]+" matched a lone comma in ordinary prose and int("") raised,
    and "2026Q2" was rewritten into words mid-sentence.
    """
    assert to_spoken("HOST: In 2026Q2 we met.") == "HOST: In 2026Q2 we met."
    assert to_spoken("HOST: Warm, plain, clear.") == "HOST: Warm, plain, clear."


def test_no_space_is_eaten_before_a_figure():
    """An early regex swallowed the preceding space: "returnedtwo point"."""
    out = to_spoken("GUEST: returned 2.76% today.")
    assert "returned two point" in out
    assert "returnedtwo" not in out


class _Snap:
    """Minimal stand-in with the surface code_built_script uses."""
    benchmark_name = "60/40 Balanced Composite"

    def numeric_facts(self):
        return {"portfolio_value": 1249327.22, "quarter_return_pct": 2.76,
                "benchmark_return_pct": 2.99, "attr.US Equity": 1.94,
                "attr.Fees": -0.34, "fees.total": 2870.0}

    def label_terms(self):
        return ["60/40 Balanced Composite", "60/40"]


def test_code_built_script_is_grounded_by_construction():
    """The fallback must never need the gate's forgiveness."""
    snap = _Snap()
    script = code_built_script({"client_name": "Jordan Lee",
                                "period": "2026Q2"}, snap)
    facts = derived_facts(snap.numeric_facts())
    block = {"block_id": "p", "block_type": "narrative",
             "source_refs": ["portfolio_value"], "data": {"text": script}}
    findings = [f for f in validate_block(block, facts,
                                          labels=snap.label_terms(),
                                          locale="en")
                if f.kind == "ungrounded_number"]
    assert not findings, [f.detail for f in findings]
    assert script.count("HOST:") >= 4 and script.count("GUEST:") >= 4


# ── presentation: the length budget and the chart gate ──────────────────

def test_presentation_length_is_capped_in_code_not_only_in_the_prompt():
    """The free renderer is one CPU and 512MB.

    A five-minute presentation is not "a bit slower" than a two-minute one,
    it is the difference between finishing and being killed for memory. The
    prompt asks for 3-4 short sections; this asserts the code holds it there
    even when the model ignores that, because "usually respected" is not a
    budget.
    """
    from ape.reporting.presentation import (_fit_budget, estimate_seconds,
                                            MAX_SECTIONS, MAX_KEY_POINTS)

    bloated = [{"title": f"S{i}",
                "narration": "This is a sentence of about ten words in total here. " * 8,
                "key_points": ["a", "b", "c", "d", "e"]}
               for i in range(7)]
    assert estimate_seconds(bloated) > 180, "fixture should exceed the budget"

    fitted, note = _fit_budget(bloated)
    assert len(fitted) <= MAX_SECTIONS
    assert all(len(s["key_points"]) <= MAX_KEY_POINTS for s in fitted)
    assert estimate_seconds(fitted) <= 180, "must land inside the 1-3 minute range"
    assert note != "within budget"


def test_trimming_only_removes_so_grounding_still_holds():
    """Trimming runs AFTER the gate, which is only safe if it cannot add.

    A subset of checked sentences is still checked. If this ever started
    rewriting rather than dropping, the surviving text would be unverified.
    """
    from ape.reporting.presentation import _trim_to_words

    original = "One two three four five. Six seven eight nine ten. Eleven twelve."
    out = _trim_to_words(original, 6)
    assert out in original, "trimming must be a substring, never a rewrite"
    assert out.endswith("."), "should cut on a sentence boundary"


def test_chart_values_are_grounded_like_any_other_figure():
    """A bar is believed faster than a sentence and questioned less.

    Chart data arrives as JSON floats, so the prose scan walks straight
    past it. If these are not checked here they are not checked at all.
    """
    from ape.reporting.presentation import _visual_numbers, _matches_a_fact
    from ape.reporting.grounding import derived_facts

    facts = derived_facts({"portfolio_value": 1000.0,
                           "quarter_return_pct": 2.41,
                           "benchmark_return_pct": 3.77})

    sections = [{"title": "x", "narration": "y",
                 "visual": {"type": "bar_chart",
                            "data": {"Portfolio": 2.41, "Benchmark": 9.99}}}]
    found = dict((w.rsplit(".", 1)[-1], v) for w, v in _visual_numbers(sections))
    assert found == {"Portfolio": 2.41, "Benchmark": 9.99}

    assert _matches_a_fact(2.41, facts), "a true chart value must pass"
    assert not _matches_a_fact(9.99, facts), "an invented chart value must be caught"


def test_media_renders_share_one_lock():
    """One CPU does not care which feature asked.

    Separate locks let a podcast and a video render at the same time — two
    synthesis processes plus an encode on a box sized for one, which is how
    it crosses the memory limit rather than merely running slowly.
    """
    from ape.reporting import podcast, presentation
    assert podcast._RENDER_LOCK is presentation._RENDER_LOCK
