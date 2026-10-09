"""Second factor on the report link: prove you are the named client.

WHY THE TOKEN ALONE IS NOT ENOUGH
---------------------------------
The signed link proves the URL was issued by us and has not been tampered
with. It proves nothing about WHO is holding it. Forward the email, paste
the URL into a group chat, leave it in a shared inbox, and the next reader
is the client as far as the server is concerned.

So opening a link now asks for something the holder has to KNOW. The token
says "this URL is genuine"; this module says "and you are the person it was
issued to". Two different questions, two different checks.

WHAT IS BEING VERIFIED, HONESTLY
--------------------------------
Year of birth, held per client in `clients.birth_year`. Where a client has
no year on file, DEFAULT_BIRTH_YEAR stands in.

That default is a demo placeholder and should be read as one: while every
client shares it, the answer is a constant, and a constant is not a secret.
The mechanism around it is real — per-client storage, attempt limiting,
constant-time comparison, a signed pass — so populating `birth_year` from
the firm's CRM turns this into an actual factor without touching code.

A year is a weak secret even when it IS per-client: four digits, and a
plausible range of maybe seventy. That is why the attempt limit below
matters more here than it would for a random code — unlimited guesses
would walk the whole range in under a minute.
"""

from __future__ import annotations

import os
import hashlib
import hmac
import time
from typing import Dict, Optional, Tuple

from ape.reporting.tokens import _b64, _secret, _unb64

# The demo year. Stands in for any client with no year on file — one
# imported after the backfill, for instance — and is the value written into
# `clients.birth_year` for every existing client, so all of them verify the
# same way.
#
# Hardcoded rather than read from the environment because it is a demo
# constant, not configuration: a real deployment does not raise this number,
# it replaces it with one year per client from the firm's CRM, at which
# point this is only reached by clients the CRM did not cover.
DEFAULT_BIRTH_YEAR = 1998

# ONE VISIT, NOT ONE FORTNIGHT.
#
# This used to last as long as the link itself — fourteen days — on the
# reasoning that re-asking for a fact that has not changed is friction for
# no gain. That reasoning was wrong about what the question is for.
#
# The year of birth does not prove the client is at the keyboard when they
# answer it; it proves they were there ONCE. A fortnight-long pass turns a
# single answer into two weeks of unchallenged access from that browser —
# on a shared laptop, a family iPad, an unlocked phone left on a desk. The
# link is emailed, so it outlives the moment it was opened, and the pass
# was outliving it too.
#
# Now it covers a sitting: long enough to read the report, ask the chat a
# few questions and play the podcast without being interrupted, short
# enough that coming back later asks again. Combined with a session cookie
# (see the set_cookie call in api.py), closing the browser also ends it.
PASS_TTL_SECONDS = int(os.getenv("APE_IDENTITY_PASS_TTL", str(30 * 60)))

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60

# Domain separator. Without it, an identity pass and a report token are the
# same construction over the same key, and one could be presented where the
# other is expected. The prefix makes the two signature spaces disjoint.
_PASS_CONTEXT = b"ape-identity-pass-v1|"


class IdentityError(ValueError):
    """Wrong answer, too many attempts, or a bad pass."""


# ---------------------------------------------------------------- attempts

# (report_id, client_id) -> (failed_count, first_failure_ts)
#
# In memory, so it resets when the process does and is not shared between
# instances. That is a real limit and it is the same single-instance
# assumption the local SQLite database already makes; a multi-instance
# deployment needs this in Redis or the database alongside that move.
_ATTEMPTS: Dict[Tuple[str, str], Tuple[int, float]] = {}


def _key(report_id: str, client_id: str) -> Tuple[str, str]:
    return (report_id, client_id)


def attempts_left(report_id: str, client_id: str) -> int:
    count, first = _ATTEMPTS.get(_key(report_id, client_id), (0, 0.0))
    if count and time.time() - first > LOCKOUT_SECONDS:
        return MAX_ATTEMPTS
    return max(0, MAX_ATTEMPTS - count)


def _record_failure(report_id: str, client_id: str) -> None:
    k = _key(report_id, client_id)
    count, first = _ATTEMPTS.get(k, (0, 0.0))
    if count and time.time() - first > LOCKOUT_SECONDS:
        count, first = 0, 0.0          # window elapsed, start over
    _ATTEMPTS[k] = (count + 1, first or time.time())


def clear_attempts(report_id: str, client_id: str) -> None:
    _ATTEMPTS.pop(_key(report_id, client_id), None)


# ---------------------------------------------------------------- the check

def expected_year(session, client_id: str) -> int:
    """The year on file for this client, or the standing default."""
    from ape.db.models import Client
    try:
        row = session.get(Client, client_id)
    except Exception:
        row = None
    year = getattr(row, "birth_year", None) if row is not None else None
    return int(year) if year else DEFAULT_BIRTH_YEAR


def check_year(given: str, expected: int) -> bool:
    """Constant-time compare of a four-digit year.

    compare_digest rather than ==, for the same reason the token check uses
    it: a comparison that returns early leaks how much of the answer was
    right, and four digits is a small enough space that even a weak timing
    signal is worth removing.
    """
    cleaned = (given or "").strip()
    if len(cleaned) != 4 or not cleaned.isdigit():
        return False
    return hmac.compare_digest(cleaned, str(expected))


def verify_answer(session, report_id: str, client_id: str, given: str) -> None:
    """Raise IdentityError unless `given` is right and attempts remain."""
    if attempts_left(report_id, client_id) <= 0:
        raise IdentityError(
            "Too many incorrect attempts. Please wait 15 minutes and try "
            "again, or ask your adviser to re-send your report.")
    if not check_year(given, expected_year(session, client_id)):
        _record_failure(report_id, client_id)
        left = attempts_left(report_id, client_id)
        if left <= 0:
            raise IdentityError(
                "Too many incorrect attempts. Please wait 15 minutes and try "
                "again, or ask your adviser to re-send your report.")
        raise IdentityError(
            f"That does not match our records. "
            f"{left} attempt{'s' if left != 1 else ''} remaining.")
    clear_attempts(report_id, client_id)


# ------------------------------------------------------------- the pass

def mint_pass(report_id: str, client_id: str,
              ttl: int = PASS_TTL_SECONDS) -> str:
    """A signed note saying this browser answered correctly for this report.

    Bound to the report as well as the client, so a pass earned on one
    report does not silently unlock another.
    """
    exp = int(time.time()) + int(ttl)
    payload = f"{report_id}|{client_id}|{exp}".encode("utf-8")
    sig = hmac.new(_secret(), _PASS_CONTEXT + payload, hashlib.sha256).digest()
    return f"{_b64(payload)}.{_b64(sig)}"


def verify_pass(pass_value: str, report_id: str,
                client_id: Optional[str] = None) -> bool:
    """True only for an untampered, unexpired pass for THIS report."""
    if not pass_value or "." not in pass_value:
        return False
    body, _, sig = pass_value.partition(".")
    try:
        payload, given = _unb64(body), _unb64(sig)
    except Exception:
        return False

    expected = hmac.new(_secret(), _PASS_CONTEXT + payload,
                        hashlib.sha256).digest()
    if not hmac.compare_digest(expected, given):
        return False

    try:
        rid, cid, exp = payload.decode("utf-8").split("|")
    except ValueError:
        return False

    if int(exp) < int(time.time()):
        return False
    if rid != report_id:
        return False
    if client_id is not None and cid != client_id:
        return False
    return True


def cookie_name(report_id: str) -> str:
    """One cookie per report, so several open reports do not evict each other.

    Browsers key cookies by (name, domain, path), and the path is set to
    this report's URL when the cookie is written — so the name can stay
    constant while the paths keep them apart.
    """
    return "ape_idv"


def cookie_path(report_id: str) -> str:
    return f"/r/{report_id}"


# ------------------------------------------------------------- the page

def challenge_html(report_id: str, token: str, first_name: str = "",
                   error: str = "") -> str:
    """The 'confirm it's you' page.

    A plain form POST, not fetch(): this is the gate, and a gate that
    depends on JavaScript is a gate that fails open for anyone whose
    script did not run.

    The page greets by first name only. The link was already proven
    genuine by the token, so showing who it was issued to is not a leak —
    but a full name, portfolio value or period would be, since whoever is
    looking has not yet proved they are the client.
    """
    greeting = f"Hello {_esc(first_name)}," if first_name else "Hello,"
    err = ""
    if error:
        err = (f'<p role="alert" style="margin:0 0 16px;padding:9px 11px;'
               f'background:#fbf2f3;border-left:3px solid #9e0029;border-radius:2px;'
               f'color:#9e0029;font-size:13px;line-height:1.5">{_esc(error)}</p>')

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@300;400;500;700&display=swap">
<title>Confirm it's you</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin:0; background:#f4f6f9; min-height:100vh;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    padding:24px; box-sizing:border-box;
    font-family:"Ubuntu","Segoe UI Variable Text","Segoe UI",-apple-system,system-ui,Arial,sans-serif;
    color:#171a22; }}
  .mark b {{ color:#1d365a; font-weight:500; letter-spacing:0;
    text-transform:none; font-size:14px; }}
  .mark {{ font-size:11px; font-weight:600; letter-spacing:.09em;
    text-transform:uppercase; color:#595e6a; margin:0 0 14px; width:100%;
    max-width:400px; }}
  .card {{ background:#fff; border:1px solid #e6e9ed; border-top:3px solid #1d365a;
    border-radius:4px; padding:28px 28px 22px; max-width:400px; width:100%;
    box-sizing:border-box; }}
  h1 {{ font-size:24px; font-weight:300; margin:0 0 6px; letter-spacing:-.01em; }}
  .sub {{ color:#595e6a; font-size:13.5px; line-height:1.55; margin:0 0 22px; }}
  label {{ display:block; font-size:12px; font-weight:600; color:#3c414a;
    margin:0 0 6px; }}
  input {{ width:100%; box-sizing:border-box; font:inherit; font-size:16px;
    height:40px; padding:0 12px; border:1px solid #c7ccd3; border-radius:4px;
    letter-spacing:.14em; font-variant-numeric:tabular-nums; color:#171a22; }}
  input:focus {{ outline:none; border-color:#1d365a;
    box-shadow:0 0 0 3px rgba(29, 54, 90,.15); }}
  button {{ width:100%; margin-top:16px; height:40px; background:#1d365a; color:#fff;
    border:0; border-radius:4px; font:inherit; font-size:14px;
    font-weight:600; cursor:pointer; }}
  button:hover {{ background:#121a38; }}
  button:focus-visible {{ outline:2px solid #1d365a; outline-offset:2px; }}
  .foot {{ margin:20px 0 0; padding-top:14px; border-top:1px solid #f1f4f7;
    color:#6e7480; font-size:11.5px; line-height:1.55; }}
  .mark img {{ display:block; width:120px; height:auto; margin:0 0 12px; }}
  button {{ border-radius:999px; font-weight:500; }}
  input:focus {{ border-color:#3573c0; box-shadow:0 0 0 3px rgba(53,115,192,.16); }}
</style></head><body>
  <p class="mark"><img src="/static/brand/capgeminiBlue.svg" alt="Capgemini" width="120" height="27">Your quarterly report</p>
  <div class="card">
    <h1>Confirm it's you</h1>
    <p class="sub">{greeting} before we open your report, please confirm
      your year of birth. This keeps your report private if the link is
      ever forwarded.</p>
    {err}
    <form method="post" action="/r/{_esc(report_id)}/verify">
      <input type="hidden" name="token" value="{_esc(token)}">
      <label for="y">Year of birth</label>
      <input id="y" name="birth_year" inputmode="numeric" pattern="[0-9]{{4}}"
             maxlength="4" placeholder="YYYY" autocomplete="off" required
             autofocus>
      <button type="submit">Open my report</button>
    </form>
    <p class="foot">If you did not expect this report, or you cannot
      confirm these details, please contact your adviser.</p>
  </div>
</body></html>"""


def _esc(text: str) -> str:
    import html
    return html.escape(str(text or ""), quote=True)
