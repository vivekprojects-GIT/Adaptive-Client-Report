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
