"""Which voice reads a report aloud, per language.

WHY THIS FILE EXISTS
════════════════════════════════════════════════════════════════════════════

The podcast and the presentation were both narrated by an English voice, in
every language. The written script was Dutch, the slides were Dutch, and
then an English speaker read them aloud — which sounds less like an accent
and more like a mistake.

The cause was not the engine. Piper serves 51 languages and 175 voices,
downloaded on demand; we simply never asked for one. Both MCP calls sent
`{script, title}` and `{sections, title}` and nothing else, so the renderer
used its own English default, and a comment in podcast.py asserted that
English was all the engine had. It was not.

WHAT A "SPEAKER" IS, AND WHY THE PAIRS MATTER
────────────────────────────────────────────────────────────────────────────

A podcast has two parts, HOST and GUEST, and they must sound like two
people. Piper voice names are `<locale>-<speaker>-<quality>`, so
`de_DE-thorsten-medium` and `de_DE-thorsten-low` are ONE person recorded
twice, not two people. Pairing those would give a dialogue in which both
voices are the same man, which is worse than a single narrator because it
sounds like a fault rather than a choice.

So a pair here is always two distinct SPEAKER names. Where a language has
only one speaker, both parts share it deliberately — the dialogue still
reads correctly, it is simply narrated rather than performed, and that is
the honest best available.

WHERE A LANGUAGE IS MISSING
────────────────────────────────────────────────────────────────────────────

Seven of our locales have no piper voice at all: Bosnian, Croatian,
Lithuanian, Macedonian, Malay, Thai and Tagalog. Those fall back to English
audio, and `language_note` tells the client so. The written report and the
on-page script stay in their language either way — the fallback is only
ever about the sound.

That is the same rule the rest of the system runs on: what the client is
told never changes, only how it reaches them.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

# language code -> (host speaker, guest speaker)
#
# Chosen for two distinct speakers wherever the catalogue has them, and for
# `medium` quality over `low`/`x_low` where a speaker was recorded more than
# once. A single-speaker language repeats its one voice in both slots.
_VOICES: Dict[str, Tuple[str, str]] = {
    # ── two or more distinct speakers ───────────────────────────────────
    "en": ("en_GB-alan-medium", "en_GB-cori-medium"),
    "nl": ("nl_NL-pim-medium", "nl_NL-ronnie-medium"),
    "de": ("de_DE-thorsten-medium", "de_DE-kerstin-low"),
    "fr": ("fr_FR-tom-medium", "fr_FR-siwis-medium"),
    "es": ("es_ES-davefx-medium", "es_ES-sharvard-medium"),
    "it": ("it_IT-paola-medium", "it_IT-serena-medium"),
    "pt": ("pt_BR-faber-medium", "pt_BR-cadu-medium"),
    "pl": ("pl_PL-darkman-medium", "pl_PL-gosia-medium"),
    "ru": ("ru_RU-ruslan-medium", "ru_RU-irina-medium"),
    "uk": ("uk_UA-mykyta-high", "uk_UA-tetiana-high"),
    "cs": ("cs_CZ-jirka-medium", "cs_CZ-kasandra-medium"),
    "el": ("el_GR-rapunzelina-medium", "el_GR-joy-medium"),
    "hu": ("hu_HU-imre-medium", "hu_HU-anna-medium"),
    "is": ("is_IS-bui-medium", "is_IS-salka-medium"),
    "sv": ("sv_SE-nst-medium", "sv_SE-lisa-medium"),
    "nb": ("no_NO-talesyntese-medium", "no_NO-nvcc-medium"),
    "fa": ("fa_IR-amir-medium", "fa_IR-ganji-medium"),
    "ur": ("ur_PK-fasih-medium", "ur_PK-aegis_female-medium"),
    "vi": ("vi_VN-vais1000-medium", "vi_VN-vivos-x_low"),
    "zh": ("zh_CN-huayan-medium", "zh_CN-chaowen-medium"),
    # Traditional-script readers are Mandarin speakers (Taiwan, Hong Kong
    # business use), and Mandarin is what the catalogue offers. The SCRIPT
    # stays Traditional — see locales.py, where zh-hant is deliberately kept
    # from collapsing to zh — only the voice is shared.
    "zh-hant": ("zh_CN-huayan-medium", "zh_CN-chaowen-medium"),

    # ── one speaker: both parts share it ────────────────────────────────
    "ar": ("ar_JO-kareem-medium", "ar_JO-kareem-medium"),
    "bg": ("bg_BG-dimitar-medium", "bg_BG-dimitar-medium"),
    "bn": ("bn_BD-google-medium", "bn_BD-google-medium"),
    "da": ("da_DK-talesyntese-medium", "da_DK-talesyntese-medium"),
    "et": ("et_EE-news-medium", "et_EE-news-medium"),
    "fi": ("fi_FI-harri-medium", "fi_FI-harri-medium"),
    "he": ("he_IL-saspeech-medium", "he_IL-saspeech-medium"),
    "id": ("id_ID-news_tts-medium", "id_ID-news_tts-medium"),
    "ja": ("ja_JA-hi_fi_captain-medium", "ja_JA-hi_fi_captain-medium"),
    "ko": ("ko_KR-kss-medium", "ko_KR-kss-medium"),
    "lv": ("lv_LV-aivars-medium", "lv_LV-aivars-medium"),
    "ro": ("ro_RO-mihai-medium", "ro_RO-mihai-medium"),
    "sk": ("sk_SK-lili-medium", "sk_SK-lili-medium"),
    "sl": ("sl_SI-artur-medium", "sl_SI-artur-medium"),
    "sq": ("sq_AL-edon-medium", "sq_AL-edon-medium"),
    "sr": ("sr_RS-serbski_institut-medium", "sr_RS-serbski_institut-medium"),
    "sw": ("sw_CD-lanfrica-medium", "sw_CD-lanfrica-medium"),
    "tr": ("tr_TR-dfki-medium", "tr_TR-dfki-medium"),
}

# Locales we ship that piper cannot speak. Listed rather than inferred, so
# the gap is visible in the source instead of being an empty dict lookup.
NO_VOICE = frozenset({"bs", "hr", "lt", "mk", "ms", "th", "tl"})

# What `language_note` consults. Derived from the table above rather than
# hand-maintained beside it — the two drifting apart is exactly how a client
# gets told their audio is English while a Dutch voice reads it.
SPOKEN_LOCALES = frozenset(_VOICES)


def _norm(locale_code: Optional[str]) -> str:
    code = (locale_code or "en").strip().lower()
    if code in _VOICES:
        return code
    # "nl-BE" and "pt-BR" resolve to their base language, matching the way
    # locales.get() falls back. "zh-hant" is checked first above, so this
    # cannot silently turn Traditional Chinese into Simplified.
    return code.split("-")[0]


def pair(locale_code: Optional[str]) -> Tuple[str, str]:
    """(host, guest) for a two-voice podcast. English when unsupported."""
    return _VOICES.get(_norm(locale_code), _VOICES["en"])


def narrator(locale_code: Optional[str]) -> str:
    """The single voice a presentation is read in.

    The host half of the pair, so a client who plays both the video and the
    podcast hears the same person introduce their report twice.
    """
    return pair(locale_code)[0]


def is_spoken(locale_code: Optional[str]) -> bool:
    """True when we can narrate in this language rather than in English."""
    return _norm(locale_code) in _VOICES
