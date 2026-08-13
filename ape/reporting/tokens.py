"""Signed report-access tokens.

    /r/{report_id}?token=<signed>

The token is the whole authorisation. Knowing a report_id must never be
enough — report ids are guessable (`R_C1001_2026Q2`), so an unauthenticated
`/r/{id}` would expose every client's report to anyone who could count.

HMAC-SHA256 over a compact payload rather than a JWT library: there is one
issuer and one verifier, both in this process, so the extra dependency buys
nothing. Swapping to real JWT later changes only this module.

    payload = report_id|client_id|scope|expiry
    token   = base64url(payload) + "." + base64url(hmac(payload))

THE SECRET IS THE WHOLE SECURITY MODEL
-------------------------------------
Report ids are guessable, so an unsigned or weakly-signed link exposes
every client. `_secret()` therefore refuses to fall back: no secret means
no links, rather than links anyone can forge. See the note there.

WHAT THE TOKEN DOES NOT DO
--------------------------
It cannot be revoked. Anyone the client forwards the email to has access for
the remaining lifetime. Mitigations, in order of effort: a shorter TTL, a
`jti` checked against a denylist, or exchanging the token for a session
cookie on first open. None are implemented; the TTL is the only control.

The token also travels in the QUERY STRING, so it lands in server access
logs, browser history and any Referer header the viewer emits. Moving it
to a POST body or swapping it for a cookie on first open would fix that;
neither is done.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import Optional, Tuple

# Long-ish by default because the report itself has a long tail: clients open
# quarterly reports days or weeks after delivery, and the signal window for
# learning is two weeks. A 24h link would go dead before most clients ever
# clicked it, losing both the read and the learning signal.
DEFAULT_TTL_SECONDS = 14 * 24 * 3600

SCOPE_VIEW = "report:view"


class TokenError(ValueError):
    """Invalid, tampered with, or expired."""


MIN_SECRET_LEN = 32


def _secret() -> bytes:
    """The signing key, or a refusal to sign at all.

    This used to fall back to a hardcoded string when the variable was
    unset. That string is in a public repository, and the token is the
    ONLY thing protecting a report — report ids are guessable by design.
    So the fallback let anyone who had read the source mint a valid link
    for any client, and the failure was silent: links worked, nothing
    logged, nothing looked wrong.

    Now it fails closed. A deployment without a secret cannot issue or
    accept links at all, which is loud, immediate, and fixable — the
    alternative is a system that appears to work while authorising
    strangers.

    A short secret is refused for the same reason: HMAC is only as strong
    as its key, and "test" is brute-forceable in seconds.
    """
    s = os.getenv("APE_REPORT_TOKEN_SECRET") or os.getenv("JWT_SECRET")
    if not s or not s.strip():
        raise TokenError(
            "APE_REPORT_TOKEN_SECRET is not set. Report links cannot be "
            "signed or verified without it. Generate one with:\n"
            "    python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    s = s.strip()
    if len(s) < MIN_SECRET_LEN:
        raise TokenError(
            f"APE_REPORT_TOKEN_SECRET is only {len(s)} characters; "
            f"{MIN_SECRET_LEN} is the minimum. A guessable signing key is "
            f"the same as no key — every client's report becomes reachable "
            f"by anyone who guesses it."
        )
    return s.encode("utf-8")


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(txt: str) -> bytes:
    return base64.urlsafe_b64decode(txt + "=" * (-len(txt) % 4))


def mint(report_id: str, client_id: str, ttl: int = DEFAULT_TTL_SECONDS,
         scope: str = SCOPE_VIEW) -> str:
    exp = int(time.time()) + int(ttl)
    payload = f"{report_id}|{client_id}|{scope}|{exp}".encode("utf-8")
    sig = hmac.new(_secret(), payload, hashlib.sha256).digest()
    return f"{_b64(payload)}.{_b64(sig)}"


def verify(token: str, report_id: Optional[str] = None) -> Tuple[str, str, str]:
    """Returns (report_id, client_id, scope). Raises TokenError otherwise."""
    if not token or "." not in token:
        raise TokenError("missing or malformed token")
    body, _, sig = token.partition(".")
    try:
        payload = _unb64(body)
        given = _unb64(sig)
    except Exception:
        raise TokenError("malformed token encoding")

    expected = hmac.new(_secret(), payload, hashlib.sha256).digest()
    # compare_digest, not ==, so a wrong signature cannot be found byte by
    # byte from response timing.
    if not hmac.compare_digest(expected, given):
        raise TokenError("signature does not match")

    try:
        rid, cid, scope, exp = payload.decode("utf-8").split("|")
    except ValueError:
        raise TokenError("unexpected payload shape")

    if int(exp) < int(time.time()):
        raise TokenError("token expired")
    # The token names ONE report. Presenting a valid token for report A
    # against report B is the cross-client case and must fail.
    if report_id is not None and rid != report_id:
        raise TokenError("token is not valid for this report")
    return rid, cid, scope


def report_url(report_id: str, client_id: str, base_url: Optional[str] = None,
               ttl: int = DEFAULT_TTL_SECONDS) -> str:
    base = (base_url or os.getenv("APP_BASE_URL")
            or "http://localhost:7901").rstrip("/")
    return f"{base}/r/{report_id}?token={mint(report_id, client_id, ttl)}"
