"""Regressions for the grounding gate — the two ways it has failed silently.

Both bugs here shared a symptom that looked like the model misbehaving:
answers that were correct got refused, so a client asking a perfectly
answerable question was told the report did not contain the answer. Neither
was visible by reading the source.
"""

from __future__ import annotations

import io
import pathlib

import pytest

from ape.reporting.grounding import _MULT_SUFFIX, _matches, extract_numbers

APE = pathlib.Path(__file__).resolve().parents[1] / "ape"

# \n, \t and \r are the only control characters with any business in source.
ALLOWED_CONTROLS = "\n\t\r"


def test_no_stray_control_characters_in_source():
    """A literal control byte where an escape was intended.

    `re.compile(r"(m|M|k|K)\\b")` written into a file through a shell
    heredoc can arrive with the two characters `\\b` collapsed into one
    0x08 byte. The line still READS correctly — grep, editors and code
    review all render the byte invisibly — but the pattern now demands a
    literal backspace and therefore never matches.

    That is exactly how the multiplier check below silently died, so the
    guard is on the whole package rather than the one regex: any file can
    acquire one the same way.
    """
    offenders = []
    for path in sorted(APE.rglob("*.py")):
        text = io.open(path, encoding="utf-8").read()
        for index, char in enumerate(text):
            if ord(char) < 32 and char not in ALLOWED_CONTROLS:
                line = text[:index].count("\n") + 1
                offenders.append(f"{path.relative_to(APE.parent)}:{line} "
                                 f"{hex(ord(char))}")
    assert not offenders, (
        "literal control characters in source (an escape such as \\b that "
        "was written as a raw byte):\n  " + "\n  ".join(offenders))


def test_multiplier_suffix_is_detected():
    """The suffix must be recognised, or every rounded figure loses its
    tolerance and gets rejected as ungrounded."""
    for written in ("£4.21m", "£4.21M", "£14.3K", "£4.21 million"):
        raw = extract_numbers(written)[0][2]
        assert _MULT_SUFFIX.search(raw), f"{written!r} not seen as rounded"


PORTFOLIO_VALUE = 4_207_125.24


@pytest.mark.parametrize("written", ["£4.21m", "£4.21M", "£4.21 million",
                                     "£4.2m", "£4,207,125"])
def test_correctly_rounded_figures_are_accepted(written):
    """An abbreviated figure is the SAME fact, and must pass the gate.

    Rejecting it made the model look wrong when it was right: "your
    portfolio grew to £4.21m" is a true statement about £4,207,125.24, and
    refusing it turned a good answer into "the report does not contain
    what I'd need".
    """
    value, dp, raw, _ = extract_numbers(written)[0]
    assert _matches(value, dp, [PORTFOLIO_VALUE],
                    bool(_MULT_SUFFIX.search(raw)))


@pytest.mark.parametrize("written", ["£4.3m", "£5m", "£3.9m"])
def test_wrong_rounded_figures_are_still_rejected(written):
    """The tolerance must not become a licence to invent.

    0.5% of this portfolio is about £21,000, so a figure outside that band
    is a different number and has to fail.
    """
    value, dp, raw, _ = extract_numbers(written)[0]
    assert not _matches(value, dp, [PORTFOLIO_VALUE],
                        bool(_MULT_SUFFIX.search(raw)))


@pytest.mark.parametrize("written,actual", [("£10,518.81", 10_517.81),
                                            ("£4,207,999", PORTFOLIO_VALUE)])
def test_full_precision_figures_are_held_to_the_penny(written, actual):
    """A figure written out in full claims that precision.

    The relative band exists only for deliberately rounded renderings; if
    it applied here, £10,518.81 would pass as £10,517.81 and the gate would
    be waving through a wrong number to the penny.
    """
    value, dp, raw, _ = extract_numbers(written)[0]
    assert not _matches(value, dp, [actual], bool(_MULT_SUFFIX.search(raw)))


# ---------------------------------------------------------- label exemption

def test_number_position_is_the_digits_not_the_match():
    """extract_numbers must report where the DIGITS start.

    The pattern allows an optional currency symbol followed by \s*, so a
    match routinely begins at the SPACE before the number. Reporting that
    position put every space-preceded figure one character outside any
    label span, and the exemption for proper names containing digits
    silently never fired.
    """
    text = "against the 60/40 Balanced Composite"
    starts = {raw: pos for _v, _dp, raw, pos in extract_numbers(text)}
    assert text[starts["60"]] == "6", "start must land on the digit, not the space"
    assert text[starts["40"]] == "4"


def test_benchmark_name_digits_are_exempt():
    """"60/40 Balanced Composite" is a NAME, not two claims.

    Three of four demo clients have a benchmark named this way, so this
    was a routine intermittent failure that looked random because it
    depended on how the model happened to phrase itself.
    """
    from ape.reporting.grounding import _inside, _label_spans
    labels = ["60/40 Balanced Composite", "60/40"]
    for text in ("against the 60/40 Balanced Composite benchmark",
                 "against the 60/40 benchmark",
                 "your 60/40 portfolio"):
        spans = _label_spans(text, labels)
        for _v, _dp, raw, pos in extract_numbers(text):
            assert _inside(pos, spans), f"{raw!r} not exempt in {text!r}"


def test_a_real_claim_near_a_label_is_still_checked():
    """The exemption must not become a hole.

    A figure OUTSIDE the label span is still a claim, even in a sentence
    that also names the benchmark.
    """
    from ape.reporting.grounding import _inside, _label_spans
    text = "the 60/40 Balanced Composite returned 99.99%"
    spans = _label_spans(text, ["60/40 Balanced Composite", "60/40"])
    exempt = {raw: _inside(pos, spans)
              for _v, _dp, raw, pos in extract_numbers(text)}
    assert exempt["60"] and exempt["40"]
    assert not exempt["99.99%"], "a real claim must stay checked"
