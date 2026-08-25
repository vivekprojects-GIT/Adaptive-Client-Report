"""Locale rules: how a language writes numbers, and what to call things.

WHY THIS EXISTS AT ALL
----------------------
Translating a report is not a text problem. It is a NUMBER problem, and the
number problem is the dangerous half.

English writes one-point-two-million as   1,234,567.89
Dutch writes the same value as            1.234.567,89

The separators are swapped. Feed a Dutch figure to a parser that assumes
English and "1.234.567,89" reads as 1.234 — three orders of magnitude wrong,
silently. The grounding gate is the one thing standing between a client and
an invented figure, so a locale bug there is not a formatting annoyance; it
is the gate failing open.

So locale is resolved ONCE, here, and every part of the system that reads or
writes a number asks this module rather than assuming a convention.

WHAT IS DELIBERATELY NOT HERE
-----------------------------
No translation of the FIGURES themselves. A number means the same thing in
every language; only its rendering changes. `format_number` re-renders a
float, it never re-computes one — so a translated report cannot drift from
the English one by construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class Locale:
    """One language's conventions.

    `code` is the short tag used everywhere else in the system (stored on
    the client row, passed to the composer, sent to the model).
    """
    code: str
    label: str            # shown in the admin UI
    endonym: str          # what speakers call it, for the client-facing side
    thousands: str
    decimal: str
    # What the model is told to write in. Kept as a full phrase rather than
    # a bare code because "write in nl" is a weaker instruction than
    # "write in Dutch (Nederlands)".
    prompt_name: str
    # Arabic and Hebrew read right to left. This is not cosmetic: a page of
    # Arabic laid out left-to-right has its columns, its table headers and
    # its KPI captions in the wrong order, and reads as broken rather than
    # as merely ugly. The renderer sets dir on <html> from this flag.
    #
    # Digits stay left-to-right inside RTL text — the browser's bidi
    # algorithm handles that, and it is why a figure keeps its meaning
    # without any work here.
    rtl: bool = False


LOCALES: Dict[str, Locale] = {
    "en": Locale("en", "English", "English", ",", ".", "English"),
    "nl": Locale("nl", "Dutch", "Nederlands", ".", ",", "Dutch (Nederlands)"),
    "de": Locale("de", "German", "Deutsch", ".", ",", "German (Deutsch)"),
    "fr": Locale("fr", "French", "Français", " ", ",",
                 "French (Français)"),
    "es": Locale("es", "Spanish", "Español", ".", ",", "Spanish (Español)"),
    "it": Locale("it", "Italian", "Italiano", ".", ",", "Italian (Italiano)"),

    # ── Added to cover every country in COUNTRIES ────────────────────────
    # Translations for these live in labels_extra.py and are UNREVIEWED
    # drafts. They are listed here as equals because the rendering pipeline
    # treats them as equals; the assurance difference is recorded in that
    # module and surfaced by scripts/review_sheet.py, not hidden by leaving
    # the language out.
    "pt": Locale("pt", "Portuguese", "Português", ".", ",", "Portuguese (Português)"),
    "sv": Locale("sv", "Swedish", "Svenska", " ", ",", "Swedish (Svenska)"),
    "da": Locale("da", "Danish", "Dansk", ".", ",", "Danish (Dansk)"),
    "nb": Locale("nb", "Norwegian", "Norsk", " ", ",", "Norwegian Bokmal (Norsk)"),
    "fi": Locale("fi", "Finnish", "Suomi", " ", ",", "Finnish (Suomi)"),
    "pl": Locale("pl", "Polish", "Polski", " ", ",", "Polish (Polski)"),
    "cs": Locale("cs", "Czech", "Čeština", " ", ",", "Czech (Čeština)"),
    "el": Locale("el", "Greek", "Ελληνικά", ".", ",", "Greek (Ελληνικά)"),
    "tr": Locale("tr", "Turkish", "Türkçe", ".", ",", "Turkish (Türkçe)"),
    "ja": Locale("ja", "Japanese", "日本語", ",", ".", "Japanese (日本語)"),
    "zh": Locale("zh", "Chinese (Simplified)", "简体中文", ",", ".",
                 "Simplified Chinese (简体中文)"),
    # Hong Kong and Taiwan do not read Simplified. Treating them as one
    # language because the code prefix matches would be the same class of
    # error as treating Dutch and German as one because both are Germanic.
    "zh-hant": Locale("zh-hant", "Chinese (Traditional)", "繁體中文", ",", ".",
                      "Traditional Chinese (繁體中文)"),
    "ko": Locale("ko", "Korean", "한국어", ",", ".", "Korean (한국어)"),
    "ar": Locale("ar", "Arabic", "العربية", ",", ".", "Arabic (العربية)", rtl=True),
    "he": Locale("he", "Hebrew", "עברית", ",", ".", "Hebrew (עברית)", rtl=True),

    # ── Remaining languages needed to cover every country ─────────
    "ru": Locale("ru", "Russian", "Русский", " ", ",",
                     "Russian (Русский)"),
    "uk": Locale("uk", "Ukrainian", "Українська", " ", ",",
                     "Ukrainian (Українська)"),
    "bg": Locale("bg", "Bulgarian", "Български", " ", ",",
                     "Bulgarian (Български)"),
    "mk": Locale("mk", "Macedonian", "Македонски", ".", ",",
                     "Macedonian (Македонски)"),
    "sr": Locale("sr", "Serbian", "Srpski", ".", ",",
                     "Serbian (Srpski)"),
    "hr": Locale("hr", "Croatian", "Hrvatski", ".", ",",
                     "Croatian (Hrvatski)"),
    "bs": Locale("bs", "Bosnian", "Bosanski", ".", ",",
                     "Bosnian (Bosanski)"),
    "sk": Locale("sk", "Slovak", "Slovenčina", " ", ",",
                     "Slovak (Slovenčina)"),
    "sl": Locale("sl", "Slovenian", "Slovenščina", ".", ",",
                     "Slovenian (Slovenščina)"),
    "ro": Locale("ro", "Romanian", "Română", ".", ",",
                     "Romanian (Română)"),
    "hu": Locale("hu", "Hungarian", "Magyar", " ", ",",
                     "Hungarian (Magyar)"),
    "et": Locale("et", "Estonian", "Eesti", " ", ",",
                     "Estonian (Eesti)"),
    "lv": Locale("lv", "Latvian", "Latviešu", " ", ",",
                     "Latvian (Latviešu)"),
    "lt": Locale("lt", "Lithuanian", "Lietuvių", " ", ",",
                     "Lithuanian (Lietuvių)"),
    "is": Locale("is", "Icelandic", "Íslenska", ".", ",",
                     "Icelandic (Íslenska)"),
    "id": Locale("id", "Indonesian", "Bahasa Indonesia", ".", ",",
                     "Indonesian (Bahasa Indonesia)"),
    "ms": Locale("ms", "Malay", "Bahasa Melayu", ",", ".",
                     "Malay (Bahasa Melayu)"),
    "vi": Locale("vi", "Vietnamese", "Tiếng Việt", ".", ",",
                     "Vietnamese (Tiếng Việt)"),
    "tl": Locale("tl", "Filipino", "Filipino", ",", ".",
                     "Filipino"),
    "th": Locale("th", "Thai", "ไทย", ",", ".",
                     "Thai (ไทย)"),
    "fa": Locale("fa", "Persian", "فارسی", ",", ".",
                     "Persian (فارسی)", rtl=True),
    "ur": Locale("ur", "Urdu", "اردو", ",", ".",
                     "Urdu (اردو)", rtl=True),
    "bn": Locale("bn", "Bengali", "বাংলা", ",", ".",
                     "Bengali (বাংলা)"),
    "sw": Locale("sw", "Swahili", "Kiswahili", ",", ".",
                     "Swahili (Kiswahili)"),
    "sq": Locale("sq", "Albanian", "Shqip", ".", ",",
                     "Albanian (Shqip)"),
}

DEFAULT_LOCALE = "en"


# Country -> the language a report for that country defaults to.
#
# A DEFAULT, never a rule. Belgium reads Dutch or French depending on the
# client, Switzerland three ways, and plenty of Dutch clients want their
# reporting in English. So the advisor picks a country and the language
# fills itself in, and they can still change it — auto-selection that
# cannot be overridden would be worse than no auto-selection at all.
COUNTRIES: Dict[str, Dict[str, str]] = {
    # Andorra, Armenia, Azerbaijan and Georgia are pointed at a
    # drafted language rather than their own (Catalan, Armenian,
    # Azerbaijani, Georgian) because those four are not written yet.
    # The advisor can still override, and adding the language later
    # is a one-line change here plus its labels.
    # A-Z by label. Each country maps to the language its wealth
    # reporting is actually written in, which is not always the language
    # most spoken there — see the module docstring.

    # A
    "AF": {"label": "Afghanistan",                       "language": "fa", "currency": "؋"},
    "AL": {"label": "Albania",                           "language": "sq", "currency": "L"},
    "DZ": {"label": "Algeria",                           "language": "ar", "currency": "د.ج"},
    "AD": {"label": "Andorra",                           "language": "es", "currency": "€"},
    "AO": {"label": "Angola",                            "language": "pt", "currency": "Kz"},
    "AG": {"label": "Antigua and Barbuda",               "language": "en", "currency": "$"},
    "AR": {"label": "Argentina",                         "language": "es", "currency": "$"},
    "AM": {"label": "Armenia",                           "language": "en", "currency": "֏"},
    "AW": {"label": "Aruba",                             "language": "nl", "currency": "ƒ"},
    "AU": {"label": "Australia",                         "language": "en", "currency": "$"},
    "AT": {"label": "Austria",                           "language": "de", "currency": "€"},
    "AZ": {"label": "Azerbaijan",                        "language": "en", "currency": "₼"},

    # B
    "BS": {"label": "Bahamas",                           "language": "en", "currency": "$"},
    "BH": {"label": "Bahrain",                           "language": "ar", "currency": "BD"},
    "BD": {"label": "Bangladesh",                        "language": "bn", "currency": "৳"},
    "BB": {"label": "Barbados",                          "language": "en", "currency": "$"},
    "BY": {"label": "Belarus",                           "language": "ru", "currency": "Br"},
    "BE": {"label": "Belgium",                           "language": "nl", "currency": "€"},
    "BZ": {"label": "Belize",                            "language": "en", "currency": "$"},
    "BJ": {"label": "Benin",                             "language": "fr", "currency": "CFA"},
    "BM": {"label": "Bermuda",                           "language": "en", "currency": "$"},
    "BT": {"label": "Bhutan",                            "language": "en", "currency": "Nu."},
    "BO": {"label": "Bolivia",                           "language": "es", "currency": "Bs"},
    "BA": {"label": "Bosnia and Herzegovina",            "language": "bs", "currency": "KM"},
    "BW": {"label": "Botswana",                          "language": "en", "currency": "P"},
    "BR": {"label": "Brazil",                            "language": "pt", "currency": "R$"},
    "VG": {"label": "British Virgin Islands",            "language": "en", "currency": "$"},
    "BN": {"label": "Brunei",                            "language": "ms", "currency": "$"},
    "BG": {"label": "Bulgaria",                          "language": "bg", "currency": "лв"},
    "BF": {"label": "Burkina Faso",                      "language": "fr", "currency": "CFA"},
    "BI": {"label": "Burundi",                           "language": "fr", "currency": "FBu"},

    # C
    "KH": {"label": "Cambodia",                          "language": "en", "currency": "៛"},
    "CM": {"label": "Cameroon",                          "language": "fr", "currency": "CFA"},
    "CA": {"label": "Canada",                            "language": "en", "currency": "$"},
    "CV": {"label": "Cape Verde",                        "language": "pt", "currency": "$"},
    "KY": {"label": "Cayman Islands",                    "language": "en", "currency": "$"},
    "CF": {"label": "Central African Republic",          "language": "fr", "currency": "CFA"},
    "TD": {"label": "Chad",                              "language": "fr", "currency": "CFA"},
    "CL": {"label": "Chile",                             "language": "es", "currency": "$"},
    "CN": {"label": "China",                             "language": "zh", "currency": "¥"},
    "CO": {"label": "Colombia",                          "language": "es", "currency": "$"},
    "KM": {"label": "Comoros",                           "language": "fr", "currency": "CF"},
    "CD": {"label": "Congo (DRC)",                       "language": "fr", "currency": "FC"},
    "CG": {"label": "Congo (Republic)",                  "language": "fr", "currency": "CFA"},
    "CR": {"label": "Costa Rica",                        "language": "es", "currency": "₡"},
    "CI": {"label": "Côte d'Ivoire",                     "language": "fr", "currency": "CFA"},
    "HR": {"label": "Croatia",                           "language": "hr", "currency": "€"},
    "CU": {"label": "Cuba",                              "language": "es", "currency": "$"},
    "CW": {"label": "Curaçao",                           "language": "nl", "currency": "ƒ"},
    "CY": {"label": "Cyprus",                            "language": "el", "currency": "€"},
    "CZ": {"label": "Czechia",                           "language": "cs", "currency": "Kč"},

    # D
    "DK": {"label": "Denmark",                           "language": "da", "currency": "kr"},
    "DJ": {"label": "Djibouti",                          "language": "fr", "currency": "Fdj"},
    "DM": {"label": "Dominica",                          "language": "en", "currency": "$"},
    "DO": {"label": "Dominican Republic",                "language": "es", "currency": "$"},

    # E
    "EC": {"label": "Ecuador",                           "language": "es", "currency": "$"},
    "EG": {"label": "Egypt",                             "language": "ar", "currency": "E£"},
    "SV": {"label": "El Salvador",                       "language": "es", "currency": "$"},
    "GQ": {"label": "Equatorial Guinea",                 "language": "es", "currency": "CFA"},
    "ER": {"label": "Eritrea",                           "language": "en", "currency": "Nfk"},
    "EE": {"label": "Estonia",                           "language": "et", "currency": "€"},
    "SZ": {"label": "Eswatini",                          "language": "en", "currency": "L"},
    "ET": {"label": "Ethiopia",                          "language": "en", "currency": "Br"},

    # F
    "FJ": {"label": "Fiji",                              "language": "en", "currency": "$"},
    "FI": {"label": "Finland",                           "language": "fi", "currency": "€"},
    "FR": {"label": "France",                            "language": "fr", "currency": "€"},

    # G
    "GA": {"label": "Gabon",                             "language": "fr", "currency": "CFA"},
    "GM": {"label": "Gambia",                            "language": "en", "currency": "D"},
    "GE": {"label": "Georgia",                           "language": "en", "currency": "₾"},
    "DE": {"label": "Germany",                           "language": "de", "currency": "€"},
    "GH": {"label": "Ghana",                             "language": "en", "currency": "₵"},
    "GI": {"label": "Gibraltar",                         "language": "en", "currency": "£"},
    "GR": {"label": "Greece",                            "language": "el", "currency": "€"},
    "GL": {"label": "Greenland",                         "language": "da", "currency": "kr"},
    "GD": {"label": "Grenada",                           "language": "en", "currency": "$"},
    "GT": {"label": "Guatemala",                         "language": "es", "currency": "Q"},
    "GG": {"label": "Guernsey",                          "language": "en", "currency": "£"},
    "GN": {"label": "Guinea",                            "language": "fr", "currency": "FG"},
    "GW": {"label": "Guinea-Bissau",                     "language": "pt", "currency": "CFA"},
    "GY": {"label": "Guyana",                            "language": "en", "currency": "$"},

    # H
    "HT": {"label": "Haiti",                             "language": "fr", "currency": "G"},
    "HN": {"label": "Honduras",                          "language": "es", "currency": "L"},
    "HK": {"label": "Hong Kong SAR",                     "language": "zh-hant", "currency": "$"},
    "HU": {"label": "Hungary",                           "language": "hu", "currency": "Ft"},

    # I
    "IS": {"label": "Iceland",                           "language": "is", "currency": "kr"},
    "IN": {"label": "India",                             "language": "en", "currency": "₹"},
    "ID": {"label": "Indonesia",                         "language": "id", "currency": "Rp"},
    "IR": {"label": "Iran",                              "language": "fa", "currency": "﷼"},
    "IQ": {"label": "Iraq",                              "language": "ar", "currency": "ع.د"},
    "IE": {"label": "Ireland",                           "language": "en", "currency": "€"},
    "IM": {"label": "Isle of Man",                       "language": "en", "currency": "£"},
    "IL": {"label": "Israel",                            "language": "he", "currency": "₪"},
    "IT": {"label": "Italy",                             "language": "it", "currency": "€"},

    # J
    "JM": {"label": "Jamaica",                           "language": "en", "currency": "$"},
    "JP": {"label": "Japan",                             "language": "ja", "currency": "¥"},
    "JE": {"label": "Jersey",                            "language": "en", "currency": "£"},
    "JO": {"label": "Jordan",                            "language": "ar", "currency": "JD"},

    # K
    "KZ": {"label": "Kazakhstan",                        "language": "ru", "currency": "₸"},
    "KE": {"label": "Kenya",                             "language": "en", "currency": "KSh"},
    "KI": {"label": "Kiribati",                          "language": "en", "currency": "$"},
    "XK": {"label": "Kosovo",                            "language": "sq", "currency": "€"},
    "KW": {"label": "Kuwait",                            "language": "ar", "currency": "KD"},
    "KG": {"label": "Kyrgyzstan",                        "language": "ru", "currency": "с"},

    # L
    "LA": {"label": "Laos",                              "language": "en", "currency": "₭"},
    "LV": {"label": "Latvia",                            "language": "lv", "currency": "€"},
    "LB": {"label": "Lebanon",                           "language": "ar", "currency": "ل.ل"},
    "LS": {"label": "Lesotho",                           "language": "en", "currency": "L"},
    "LR": {"label": "Liberia",                           "language": "en", "currency": "$"},
    "LY": {"label": "Libya",                             "language": "ar", "currency": "ل.د"},
    "LI": {"label": "Liechtenstein",                     "language": "de", "currency": "CHF"},
    "LT": {"label": "Lithuania",                         "language": "lt", "currency": "€"},
    "LU": {"label": "Luxembourg",                        "language": "fr", "currency": "€"},

    # M
    "MO": {"label": "Macao SAR",                         "language": "zh-hant", "currency": "MOP"},
    "MG": {"label": "Madagascar",                        "language": "fr", "currency": "Ar"},
    "MW": {"label": "Malawi",                            "language": "en", "currency": "MK"},
    "MY": {"label": "Malaysia",                          "language": "ms", "currency": "RM"},
    "MV": {"label": "Maldives",                          "language": "en", "currency": "Rf"},
    "ML": {"label": "Mali",                              "language": "fr", "currency": "CFA"},
    "MT": {"label": "Malta",                             "language": "en", "currency": "€"},
    "MH": {"label": "Marshall Islands",                  "language": "en", "currency": "$"},
    "MR": {"label": "Mauritania",                        "language": "ar", "currency": "UM"},
    "MU": {"label": "Mauritius",                         "language": "en", "currency": "₨"},
    "MX": {"label": "Mexico",                            "language": "es", "currency": "$"},
    "FM": {"label": "Micronesia",                        "language": "en", "currency": "$"},
    "MD": {"label": "Moldova",                           "language": "ro", "currency": "L"},
    "MC": {"label": "Monaco",                            "language": "fr", "currency": "€"},
    "MN": {"label": "Mongolia",                          "language": "en", "currency": "₮"},
    "ME": {"label": "Montenegro",                        "language": "sr", "currency": "€"},
    "MA": {"label": "Morocco",                           "language": "fr", "currency": "د.م."},
    "MZ": {"label": "Mozambique",                        "language": "pt", "currency": "MT"},
    "MM": {"label": "Myanmar",                           "language": "en", "currency": "K"},

    # N
    "NA": {"label": "Namibia",                           "language": "en", "currency": "$"},
    "NR": {"label": "Nauru",                             "language": "en", "currency": "$"},
    "NP": {"label": "Nepal",                             "language": "en", "currency": "₨"},
    "NL": {"label": "Netherlands",                       "language": "nl", "currency": "€"},
    "NZ": {"label": "New Zealand",                       "language": "en", "currency": "$"},
    "NI": {"label": "Nicaragua",                         "language": "es", "currency": "C$"},
    "NE": {"label": "Niger",                             "language": "fr", "currency": "CFA"},
    "NG": {"label": "Nigeria",                           "language": "en", "currency": "₦"},
    "MK": {"label": "North Macedonia",                   "language": "mk", "currency": "ден"},
    "NO": {"label": "Norway",                            "language": "nb", "currency": "kr"},

    # O
    "OM": {"label": "Oman",                              "language": "ar", "currency": "ر.ع."},

    # P
    "PK": {"label": "Pakistan",                          "language": "ur", "currency": "₨"},
    "PW": {"label": "Palau",                             "language": "en", "currency": "$"},
    "PS": {"label": "Palestine",                         "language": "ar", "currency": "₪"},
    "PA": {"label": "Panama",                            "language": "es", "currency": "$"},
    "PG": {"label": "Papua New Guinea",                  "language": "en", "currency": "K"},
    "PY": {"label": "Paraguay",                          "language": "es", "currency": "₲"},
    "PE": {"label": "Peru",                              "language": "es", "currency": "S/"},
    "PH": {"label": "Philippines",                       "language": "tl", "currency": "₱"},
    "PL": {"label": "Poland",                            "language": "pl", "currency": "zł"},
    "PT": {"label": "Portugal",                          "language": "pt", "currency": "€"},
    "PR": {"label": "Puerto Rico",                       "language": "es", "currency": "$"},

    # Q
    "QA": {"label": "Qatar",                             "language": "ar", "currency": "ر.ق"},

    # R
    "RO": {"label": "Romania",                           "language": "ro", "currency": "lei"},
    "RU": {"label": "Russia",                            "language": "ru", "currency": "₽"},
    "RW": {"label": "Rwanda",                            "language": "en", "currency": "FRw"},

    # S
    "KN": {"label": "Saint Kitts and Nevis",             "language": "en", "currency": "$"},
    "LC": {"label": "Saint Lucia",                       "language": "en", "currency": "$"},
    "VC": {"label": "Saint Vincent and the Grenadines",  "language": "en", "currency": "$"},
    "WS": {"label": "Samoa",                             "language": "en", "currency": "T"},
    "SM": {"label": "San Marino",                        "language": "it", "currency": "€"},
    "ST": {"label": "São Tomé and Príncipe",             "language": "pt", "currency": "Db"},
    "SA": {"label": "Saudi Arabia",                      "language": "ar", "currency": "SAR"},
    "SN": {"label": "Senegal",                           "language": "fr", "currency": "CFA"},
    "RS": {"label": "Serbia",                            "language": "sr", "currency": "дин"},
    "SC": {"label": "Seychelles",                        "language": "en", "currency": "₨"},
    "SL": {"label": "Sierra Leone",                      "language": "en", "currency": "Le"},
    "SG": {"label": "Singapore",                         "language": "en", "currency": "$"},
    "SK": {"label": "Slovakia",                          "language": "sk", "currency": "€"},
    "SI": {"label": "Slovenia",                          "language": "sl", "currency": "€"},
    "SB": {"label": "Solomon Islands",                   "language": "en", "currency": "$"},
    "SO": {"label": "Somalia",                           "language": "en", "currency": "Sh"},
    "ZA": {"label": "South Africa",                      "language": "en", "currency": "R"},
    "KR": {"label": "South Korea",                       "language": "ko", "currency": "₩"},
    "SS": {"label": "South Sudan",                       "language": "en", "currency": "£"},
    "ES": {"label": "Spain",                             "language": "es", "currency": "€"},
    "LK": {"label": "Sri Lanka",                         "language": "en", "currency": "₨"},
    "SD": {"label": "Sudan",                             "language": "ar", "currency": "ج.س."},
    "SR": {"label": "Suriname",                          "language": "nl", "currency": "$"},
    "SE": {"label": "Sweden",                            "language": "sv", "currency": "kr"},
    "CH": {"label": "Switzerland",                       "language": "de", "currency": "CHF"},
    "SY": {"label": "Syria",                             "language": "ar", "currency": "ل.س"},

    # T
    "TW": {"label": "Taiwan",                            "language": "zh-hant", "currency": "NT$"},
    "TJ": {"label": "Tajikistan",                        "language": "ru", "currency": "ЅМ"},
    "TZ": {"label": "Tanzania",                          "language": "sw", "currency": "TSh"},
    "TH": {"label": "Thailand",                          "language": "th", "currency": "฿"},
    "TL": {"label": "Timor-Leste",                       "language": "pt", "currency": "$"},
    "TG": {"label": "Togo",                              "language": "fr", "currency": "CFA"},
    "TO": {"label": "Tonga",                             "language": "en", "currency": "T$"},
    "TT": {"label": "Trinidad and Tobago",               "language": "en", "currency": "$"},
    "TN": {"label": "Tunisia",                           "language": "ar", "currency": "د.ت"},
    "TR": {"label": "Türkiye",                           "language": "tr", "currency": "₺"},
    "TM": {"label": "Turkmenistan",                      "language": "ru", "currency": "m"},
    "TV": {"label": "Tuvalu",                            "language": "en", "currency": "$"},

    # U
    "UG": {"label": "Uganda",                            "language": "en", "currency": "USh"},
    "UA": {"label": "Ukraine",                           "language": "uk", "currency": "₴"},
    "AE": {"label": "United Arab Emirates",              "language": "ar", "currency": "AED"},
    "GB": {"label": "United Kingdom",                    "language": "en", "currency": "£"},
    "US": {"label": "United States",                     "language": "en", "currency": "$"},
    "UY": {"label": "Uruguay",                           "language": "es", "currency": "$"},
    "UZ": {"label": "Uzbekistan",                        "language": "ru", "currency": "so'm"},

    # V
    "VU": {"label": "Vanuatu",                           "language": "en", "currency": "VT"},
    "VA": {"label": "Vatican City",                      "language": "it", "currency": "€"},
    "VE": {"label": "Venezuela",                         "language": "es", "currency": "Bs"},
    "VN": {"label": "Vietnam",                           "language": "vi", "currency": "₫"},

    # Y
    "YE": {"label": "Yemen",                             "language": "ar", "currency": "﷼"},

    # Z
    "ZM": {"label": "Zambia",                            "language": "en", "currency": "ZK"},
    "ZW": {"label": "Zimbabwe",                          "language": "en", "currency": "$"},
}
DEFAULT_COUNTRY = "GB"


def language_for_country(country: Optional[str]) -> str:
    """The language to preselect when an advisor picks a country."""
    if not country:
        return DEFAULT_LOCALE
    row = COUNTRIES.get(str(country).strip().upper())
    return row["language"] if row else DEFAULT_LOCALE


def currency_for_country(country: Optional[str]) -> str:
    row = COUNTRIES.get(str(country or "").strip().upper())
    return row["currency"] if row else "£"


def countries() -> list:
    """For the advisor dropdown, alphabetical by label."""
    return sorted(
        ({"code": c, "label": v["label"], "language": v["language"],
          "currency": v["currency"]} for c, v in COUNTRIES.items()),
        key=lambda r: r["label"])


def get(code: Optional[str]) -> Locale:
    """Resolve a code to a Locale, falling back to English.

    Falls back rather than raising: an unknown code on one client's row must
    not take down report generation for everyone. The fallback is the
    safe direction — English formatting on a Dutch report is visibly odd and
    gets reported; a crash mid-batch is worse and a wrong number is worst.
    """
    if not code:
        return LOCALES[DEFAULT_LOCALE]
    c = str(code).strip().lower()
    # Full code first. Truncating to two characters up front — which is what
    # this did — silently resolved "zh-hant" to "zh" and served Simplified
    # Chinese to Hong Kong. The prefix fallback is still wanted, so that
    # "en-GB" or "de-CH" land on their base language instead of English.
    if c in LOCALES:
        return LOCALES[c]
    return LOCALES.get(c[:2], LOCALES[DEFAULT_LOCALE])


def is_rtl(code: Optional[str]) -> bool:
    """Whether this language reads right to left."""
    return get(code).rtl


def supported() -> list:
    return [{"code": l.code, "label": l.label, "endonym": l.endonym}
            for l in LOCALES.values()]


# ---------------------------------------------------------------- parsing

def to_float(raw: str, code: Optional[str] = None) -> Optional[float]:
    """Read a locale-formatted number string into a float.

    Returns None when the string is not a number in this locale, rather
    than guessing. A caller that cannot parse a figure must treat it as
    unverified, never as zero.

    The order matters: strip the thousands separator FIRST, then swap the
    decimal separator to a period. Doing it the other way round on Dutch
    turns "1.234,56" into "1234.56" only by luck of ordering, and breaks
    outright on locales where the two characters differ from these.
    """
    loc = get(code)
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    # Currency symbols and spaces are not part of the value.
    for ch in "£$€   ":
        s = s.replace(ch, "")
    s = s.replace(loc.thousands, "")
    if loc.decimal != ".":
        s = s.replace(loc.decimal, ".")
    try:
        return float(s)
    except ValueError:
        return None


# --------------------------------------------------------------- rendering

def format_number(value: float, code: Optional[str] = None,
                  dp: int = 2) -> str:
    """Render a float using this locale's separators.

    Never re-computes: the caller supplies the value, this only chooses how
    it looks. That is what keeps a translated report numerically identical
    to the English one.
    """
    loc = get(code)
    neg = value < 0
    s = f"{abs(float(value)):,.{dp}f}"        # always English first
    whole, _, frac = s.partition(".")
    whole = whole.replace(",", "\x00")        # placeholder, then substitute
    whole = whole.replace("\x00", loc.thousands)
    out = whole + (loc.decimal + frac if frac else "")
    return ("-" + out) if neg else out


def format_currency(value: float, symbol: str = "£",
                    code: Optional[str] = None, dp: int = 2) -> str:
    return f"{symbol}{format_number(value, code, dp)}"
