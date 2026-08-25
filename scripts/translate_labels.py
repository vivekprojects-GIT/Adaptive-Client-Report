#!/usr/bin/env python
"""Draft label translations offline, for a human to review before committing.

    python scripts/translate_labels.py --endpoint http://localhost:5000/translate

WHY THIS IS A SCRIPT AND NOT A SERVICE CALL
-------------------------------------------
Nothing here runs while a client is reading a report. Labels must render
identically every time — the same table header cannot be worded one way in
March and another in April because a translation service was retrained in
between. So translation happens ONCE, at build time, the output is reviewed
by a person, and what ships is a frozen dictionary and a lookup.

That also keeps it outside the grounding gate entirely, which is the reason
prose is NOT translated this way: prose carries figures, and a translator
that renders words while leaving "£4,207,125.24" untouched produces text
that parses as different values under Dutch rules. Labels carry no figures,
so the objection does not apply to them.

WHAT IT ACTUALLY PRODUCES
-------------------------
A review file, not a patched labels.py. The interesting column is the
DISAGREEMENT: where the machine's translation differs from what is already
in the dictionary, that is precisely where a native speaker should look.
Financial vocabulary is where hand-written guesses go wrong — "Fixed
Income" translated literally gives the salary sense, not the instrument.

Running it does not change any shipped behaviour. Someone has to read the
output and edit ape/reporting/labels.py by hand, on purpose.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ape.reporting.labels import LABELS          # noqa: E402
from ape.reporting.locales import LOCALES        # noqa: E402

DEFAULT_ENDPOINT = "http://localhost:5000/translate"

# Strings that must never be sent to a translator, even from this script.
# They are in the dictionary as keys but are not words — see labels.py.
SKIP_PREFIXES = ("alloc.", "R_", "hold.")


def translate(endpoint: str, text: str, target: str,
              timeout: float = 20.0, retries: int = 2) -> Optional[str]:
    """One LibreTranslate call. Returns None on failure rather than raising.

    A failed call must not abort the whole run — losing forty good drafts
    because the fortieth timed out would make the script useless on a slow
    local instance. The failure is recorded in the review file instead.
    """
    import requests

    payload = {"q": text, "source": "en", "target": target, "format": "text"}
    for attempt in range(retries + 1):
        try:
            r = requests.post(endpoint, json=payload, timeout=timeout)
            if r.status_code != 200:
                if attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return None
            return (r.json() or {}).get("translatedText") or None
        except Exception:
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return None
    return None


def check_endpoint(endpoint: str) -> bool:
    got = translate(endpoint, "Fixed Income", "nl", timeout=10, retries=0)
    if got is None:
        print(f"Cannot reach a translator at {endpoint}\n"
              f"\n"
              f"  Start one locally with Docker:\n"
              f"    docker run -ti --rm -p 5000:5000 libretranslate/libretranslate\n"
              f"\n"
              f"  It downloads language models on first run, so give it a"
              f" few minutes.\n"
              f"  Then re-run this script.", file=sys.stderr)
        return False
    print(f"translator reachable at {endpoint}   "
          f"(sanity check: 'Fixed Income' -> {got!r})")
    return True


def build(endpoint: str, targets: List[str],
          only_missing: bool) -> Dict[str, Dict[str, dict]]:
    """{english: {locale: {'current':…, 'machine':…, 'agree': bool}}}"""
    out: Dict[str, Dict[str, dict]] = {}
    keys = [k for k in LABELS if not k.startswith(SKIP_PREFIXES)]
    total = len(keys) * len(targets)
    done = 0

    for english in keys:
        row: Dict[str, dict] = {}
        for loc in targets:
            done += 1
            current = LABELS[english].get(loc, "")
            if only_missing and current:
                continue
            machine = translate(endpoint, english, loc)
            row[loc] = {
                "current": current,
                "machine": machine or "",
                "failed": machine is None,
                "agree": bool(machine) and machine.strip().lower()
                         == current.strip().lower(),
            }
            print(f"  [{done:>3}/{total}] {loc}  {english[:34]:<34} "
                  f"-> {machine or '(failed)'}")
        if row:
            out[english] = row
    return out


def write_review(data: Dict[str, Dict[str, dict]], path: Path,
                 targets: List[str]) -> None:
    lines = [
        "# Label translation review",
        "",
        "Machine drafts from LibreTranslate, against what is currently in",
        "`ape/reporting/labels.py`. **Nothing is applied automatically.**",
        "",
        "Read the DISAGREE section first — that is where a hand-written",
        "guess and the machine differ, which is where financial vocabulary",
        "usually goes wrong. A native speaker decides; neither column is",
        "automatically right.",
        "",
    ]

    disagree, agree, failed, new = [], [], [], []
    for english, row in data.items():
        for loc, r in row.items():
            entry = (english, loc, r)
            if r["failed"]:
                failed.append(entry)
            elif not r["current"]:
                new.append(entry)
            elif r["agree"]:
                agree.append(entry)
            else:
                disagree.append(entry)

    def table(title: str, rows: list, note: str = "") -> None:
        lines.append(f"## {title} ({len(rows)})")
        if note:
            lines.append("")
            lines.append(note)
        lines.append("")
        if not rows:
            lines.append("_none_")
            lines.append("")
            return
        lines.append("| English | Locale | In labels.py | Machine draft |")
        lines.append("|---|---|---|---|")
        for english, loc, r in sorted(rows):
            lines.append(f"| {english} | {loc} | {r['current'] or '—'} "
                         f"| {r['machine'] or '—'} |")
        lines.append("")

    table("Disagree — review these", disagree,
          "The existing value was written by hand and is not authoritative.")
    table("New — no current translation", new)
    table("Agree", agree, "Machine matches what is already there.")
    table("Failed to translate", failed,
          "The translator did not answer. Re-run, or fill in by hand.")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_snippet(data: Dict[str, Dict[str, dict]], path: Path) -> None:
    """A paste-ready dict of the MACHINE drafts only.

    Separate from the review file on purpose: a reviewer should read the
    comparison before they copy anything, and mixing the two invites
    pasting first.
    """
    body = {e: {l: r["machine"] for l, r in row.items() if r["machine"]}
            for e, row in data.items()}
    body = {e: v for e, v in body.items() if v}
    path.write_text(
        "# Machine drafts — REVIEW BEFORE USE. Not valid labels.py on its own.\n"
        "# Merge accepted entries into LABELS in ape/reporting/labels.py.\n"
        + json.dumps(body, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--locales", default="",
                    help="comma-separated; default is every non-English locale")
    ap.add_argument("--only-missing", action="store_true",
                    help="skip labels that already have a translation")
    ap.add_argument("--out-dir", default=str(ROOT / "data" / "generated"))
    args = ap.parse_args()

    targets = ([c.strip() for c in args.locales.split(",") if c.strip()]
               or [c for c in LOCALES if c != "en"])
    unknown = [c for c in targets if c not in LOCALES]
    if unknown:
        print(f"unknown locale(s): {unknown}", file=sys.stderr)
        return 2

    if not check_endpoint(args.endpoint):
        return 1

    print(f"\ntranslating {len(LABELS)} labels into {targets}"
          f"{' (missing only)' if args.only_missing else ''}\n")
    data = build(args.endpoint, targets, args.only_missing)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    review = out_dir / "label_translation_review.md"
    snippet = out_dir / "label_translation_drafts.json"
    write_review(data, review, targets)
    write_snippet(data, snippet)

    print(f"\nreview  : {review}")
    print(f"drafts  : {snippet}")
    print("\nNothing was changed in ape/reporting/labels.py. Read the review,")
    print("then edit it by hand.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
