"""Locale handling — the number half, which is the dangerous half.

Translating prose is cosmetic. Translating FIGURES is not: English and Dutch
swap the thousands and decimal separators, so the same characters mean
different values in each. The grounding gate is what stands between a client
and a wrong number, so a locale bug there is the gate failing — either
rejecting correct answers or, worse, accepting incorrect ones.
"""

from __future__ import annotations

import pytest

from ape.reporting.grounding import extract_numbers
from ape.reporting.locales import (DEFAULT_LOCALE, LOCALES, format_number, get,
                                   to_float)

PORTFOLIO = 4_207_125.24


# --------------------------------------------------------------- the core bug

def test_dutch_figure_is_not_read_as_english():
    """The regression this whole module exists to prevent.

    "€1.234.567,89" is one-point-two-million in Dutch. Parsed with English
    rules it reads as 1.234 — three orders of magnitude out, with no error
    raised. Silent, and in the direction that matters.
    """
    raw = "€1.234.567,89"
    assert extract_numbers(raw, "nl")[0][0] == pytest.approx(1_234_567.89)
    assert extract_numbers(raw, "en")[0][0] != pytest.approx(1_234_567.89)


@pytest.mark.parametrize("code,written", [
    ("en", "£4,207,125.24"),
    ("nl", "£4.207.125,24"),
    ("de", "£4.207.125,24"),
])
def test_same_value_written_each_way(code, written):
    assert extract_numbers(written, code)[0][0] == pytest.approx(PORTFOLIO)


# ------------------------------------------------------- no English regression

@pytest.mark.parametrize("written,expected", [
    ("£4,207,125.24", 4_207_125.24),
    ("4.74%", 4.74),
    ("£4.21m", 4_210_000.0),
    ("-1.33%", -1.33),
    ("£14,304.22", 14_304.22),
    ("2,150", 2150.0),
])
def test_english_unchanged(written, expected):
    """Locale support must not have moved anything for existing clients.

    Every one of these is a shape the system already handled; the locale
    parameter defaults to English precisely so no existing caller changes
    behaviour.
    """
    assert extract_numbers(written)[0][0] == pytest.approx(expected)


def test_default_locale_is_english():
    assert get(None).code == DEFAULT_LOCALE == "en"


# --------------------------------------------------------------- decimal places

def test_decimal_places_counted_in_the_right_locale():
    """dp drives the tolerance, so counting it wrong mis-sizes the gate.

    "1.234" is 3 dp in English and 0 dp in Dutch (it is 1234). Scoring the
    Dutch form as 3 dp would hand it a tolerance a thousand times tighter
    than it should have.
    """
    assert extract_numbers("1.234", "en")[0][1] == 3
    assert extract_numbers("1.234", "nl")[0][1] == 0


# ------------------------------------------------------------------ round trip

@pytest.mark.parametrize("code", sorted(LOCALES))
def test_format_then_parse_is_lossless(code):
    """Rendering and reading must be exact inverses in every locale.

    If they are not, a report can state a figure its own validator then
    rejects — the system disagreeing with itself in front of a client.
    """
    assert to_float(format_number(PORTFOLIO, code), code) == pytest.approx(PORTFOLIO)


@pytest.mark.parametrize("code", sorted(LOCALES))
def test_formatting_never_changes_the_value(code):
    """Only the rendering may differ between languages, never the number."""
    for value in (0.0, 1234.5, -98_765.43, PORTFOLIO):
        assert to_float(format_number(value, code), code) == pytest.approx(value)


# ------------------------------------------------------------------- fallbacks

@pytest.mark.parametrize("code", ["", None, "zz", "klingon", "  "])
def test_unknown_locale_falls_back_to_english(code):
    """An unknown code on one client's row must not break generation.

    Falling back is the safe direction: English formatting on a Dutch
    report is visibly wrong and gets reported, whereas a crash takes down a
    batch and a silently wrong number reaches someone.
    """
    assert get(code).code == "en"


def test_unparseable_string_returns_none_not_zero():
    """A figure that cannot be read is unverified, never zero.

    Returning 0.0 would let a malformed figure quietly compare against a
    real fact of zero and pass.
    """
    assert to_float("not a number", "en") is None
    assert to_float("", "nl") is None
