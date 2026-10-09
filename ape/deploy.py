"""Deployment hardening — everything a PUBLIC host needs that localhost
does not.

Three concerns, all env-driven so local development is untouched:

1. ADVISOR GATE (`ADVISOR_PASSWORD`)
   On a public Space the advisor and admin surfaces must not be open:
   anyone who found the URL could generate reports, rewrite templates and
   send email from the connected Gmail. When the env var is set, every
   route EXCEPT the client-facing ones requires a signed session cookie,
   obtained by posting the password to /login.

   What stays open, and why it is safe:
     /r/*      client viewer + chat + events — already gated per-report by
               an expiring HMAC token; a stranger cannot open anyone's
               report without the emailed link
     /health   liveness probes
     /login    the gate's own door

   The cookie is HMAC-signed with the same secret that signs report links,
   carries an expiry, and holds no data worth stealing beyond "an advisor
   logged in".

2. GMAIL TOKEN FROM SECRET (`GMAIL_TOKEN_JSON`)
   token.json is rightly git-ignored, so it cannot ride along in the
   image. On the Space its CONTENTS live in a secret; at boot they are
   written to disk where the provider expects a file.

3. BOOT SEEDING (`SEED_ON_EMPTY`, default on)
   Space storage is ephemeral: a rebuild wipes SQLite. An empty clients
   table on startup triggers the synthetic seeder, so the demo always
   boots with a full book. Learned state dies with the disk too — the
   durable fix is DATABASE_URL pointing at hosted Postgres, which needs
   no code change.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import subprocess
import sys
import time
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

ROOT = Path(__file__).resolve().parents[1]

COOKIE_NAME = "ape_advisor"
SESSION_TTL = 12 * 3600

# Prefixes reachable WITHOUT an advisor session. Everything else is gated
# when ADVISOR_PASSWORD is set. Deny-by-default: a new admin endpoint is
# born protected unless someone consciously lists it here.
# "/static" carries the chart runtime and the vendored ECharts build. It has
# to be public for the same reason "/r/" is: the person opening a report link
# is a client, not a signed-in advisor, and gating the script would leave
# them looking at a report whose charts never load. These are inert assets
# with no client data in them.
PUBLIC_PREFIXES = ("/r/", "/health", "/login", "/static/")


def _secret() -> bytes:
    s = (os.getenv("APE_REPORT_TOKEN_SECRET") or os.getenv("JWT_SECRET")
         or "dev-secret-do-not-use-in-prod")
    return s.encode()


def _sign_session(expires_at: int) -> str:
    payload = f"advisor|{expires_at}".encode()
    sig = hmac.new(_secret(), payload, hashlib.sha256).digest()
    return (base64.urlsafe_b64encode(payload).decode().rstrip("=") + "." +
            base64.urlsafe_b64encode(sig).decode().rstrip("="))


def _check_session(cookie: str) -> bool:
    try:
        p64, s64 = cookie.split(".")
        pad = lambda t: t + "=" * (-len(t) % 4)          # noqa: E731
        payload = base64.urlsafe_b64decode(pad(p64))
        sig = base64.urlsafe_b64decode(pad(s64))
        if not hmac.compare_digest(
                hmac.new(_secret(), payload, hashlib.sha256).digest(), sig):
            return False
        _, exp = payload.decode().split("|")
        return time.time() < int(exp)
    except Exception:
        return False


_LOGIN_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@300;400;500;700&display=swap">
<title>Advisor sign in</title>
<style>
 *{box-sizing:border-box}
 body{margin:0;min-height:100vh;display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);
   font:14px/1.5 "Ubuntu","Segoe UI Variable Text","Segoe UI",-apple-system,system-ui,Arial,sans-serif;
   color:#171a22;background:#f4f6f9}
 .brand{background:#121a38;color:#f8fafc;padding:40px 48px;display:flex;
   flex-direction:column;justify-content:space-between}
 .mark{font-size:12px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;
   color:#a6acb5;display:flex;flex-direction:column;gap:6px}
 .mark b{color:#fff;font-weight:500;font-size:26px;letter-spacing:-.01em;text-transform:none}
 .pitch{max-width:340px}
 .pitch{border-left:3px solid #72e7d6;padding-left:18px}
 .pitch h1{font-size:28px;font-weight:300;line-height:1.3;margin:0 0 10px;color:#fff;
   letter-spacing:-.01em}
 .pitch p{margin:0;color:#c7ccd3;font-size:13.5px}
 .legal{font-size:11.5px;color:#6e7480}
 .pane{display:flex;align-items:center;justify-content:center;padding:40px 24px}
 form{width:100%;max-width:340px}
 h2{font-size:26px;font-weight:300;margin:0 0 4px;letter-spacing:-.01em}
 .lede{color:#595e6a;font-size:13px;margin:0 0 24px}
 label{display:block;font-size:12px;font-weight:600;color:#3c414a;margin:0 0 6px}
 input{width:100%;height:38px;padding:0 11px;font:inherit;color:#171a22;background:#fff;
   border:1px solid #c7ccd3;border-radius:4px;margin:0 0 16px}
 input:focus{outline:none;border-color:#1d365a;box-shadow:0 0 0 3px rgba(29, 54, 90,.15)}
 button{width:100%;height:38px;background:#1d365a;color:#fff;border:0;border-radius:4px;
   font:inherit;font-weight:600;cursor:pointer}
 button:hover{background:#121a38}
 button:focus-visible{outline:2px solid #1d365a;outline-offset:2px}
 .err{margin:0 0 16px;padding:9px 11px;font-size:13px;color:#9e0029;background:#fbf2f3;
   border-left:3px solid #9e0029;border-radius:2px}
 @media (max-width:760px){body{grid-template-columns:1fr}
   .brand{padding:24px}.pitch,.legal{display:none}}

 .mark img{display:block;width:150px;height:auto;margin-bottom:6px}
 button{border-radius:999px;font-weight:500}
 input:focus{border-color:#3573c0;box-shadow:0 0 0 3px rgba(53,115,192,.16)}
</style></head><body>
<aside class="brand">
  <div class="mark"><img src="/static/brand/capgeminiWhite.svg" alt="Capgemini" width="150" height="34">Adaptive Client Reporting</div>
  <div class="pitch">
    <h1>Quarterly reporting, in each client's own language.</h1>
    <p>Generate, review and send client reports. Every figure is traced to
      the portfolio data before it reaches a client.</p>
  </div>
  <div class="legal">For authorised advisors only. Activity is recorded.</div>
</aside>
<main class="pane">
  <form method="post" action="/login">
    <h2>Advisor sign in</h2>
    <p class="lede">Clients open reports through their personal emailed link
      and do not sign in here.</p>
    __ERROR__
    <label for="pw">Password</label>
    <input id="pw" type="password" name="password" autocomplete="current-password" autofocus>
    <button type="submit">Sign in</button>
  </form>
</main>
</body></html>"""


def install(app) -> None:
    """Wire the gate + login routes onto the FastAPI app. Call once at
    import time in api.py; a no-op gate when ADVISOR_PASSWORD is unset."""

    @app.middleware("http")
    async def advisor_gate(request: Request, call_next):  # noqa: ANN001
        password = os.getenv("ADVISOR_PASSWORD", "")
        if not password:
            return await call_next(request)              # gate disabled

        path = request.url.path
        if path == "/login" or any(path == p.rstrip("/") or path.startswith(p)
                                   for p in PUBLIC_PREFIXES):
            return await call_next(request)

        cookie = request.cookies.get(COOKIE_NAME, "")
        if _check_session(cookie):
            return await call_next(request)

        # Browsers get the login page; API callers get an honest 401.
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse("/login", status_code=302)
        return JSONResponse({"detail": "advisor session required"},
                            status_code=401)

    @app.get("/login", response_class=HTMLResponse)
    def login_page():
        return HTMLResponse(_LOGIN_PAGE.replace("__ERROR__", ""))

    @app.post("/login")
    async def login_submit(request: Request):
        form = await request.form()
        given = str(form.get("password", ""))
        expected = os.getenv("ADVISOR_PASSWORD", "")
        if not expected or not hmac.compare_digest(given, expected):
            return HTMLResponse(_LOGIN_PAGE.replace(
                "__ERROR__",
                '<p class="err" role="alert">That password is not correct.</p>'),
                status_code=401)
        resp = RedirectResponse("/", status_code=302)
        # Secure must follow the SCHEME THIS REQUEST ARRIVED ON, not
        # APP_BASE_URL. Keying it off the configured public URL meant that
        # once APP_BASE_URL was https (for the deployed host), local http
        # logins set a Secure cookie the browser silently discarded — the
        # sign-in appeared to succeed and every following request was still
        # unauthenticated. Behind a proxy, x-forwarded-proto is the truth.
        scheme = (request.headers.get("x-forwarded-proto")
                  or request.url.scheme or "http")
        resp.set_cookie(
            COOKIE_NAME, _sign_session(int(time.time()) + SESSION_TTL),
            max_age=SESSION_TTL, httponly=True, samesite="lax",
            secure=(scheme == "https"))
        return resp


# ---------------------------------------------------------------------------
# Boot tasks
# ---------------------------------------------------------------------------

def materialise_gmail_token() -> None:
    """GMAIL_TOKEN_JSON secret -> the token file the provider reads."""
    blob = os.getenv("GMAIL_TOKEN_JSON", "").strip()
    if not blob:
        return
    path = Path(os.getenv("GMAIL_TOKEN_PATH", str(ROOT / "token.json")))
    if path.is_file():
        return                                    # real file wins
    path.write_text(blob, encoding="utf-8")
    print(f"[deploy] gmail token materialised at {path}", flush=True)


def seed_if_empty() -> None:
    """Ephemeral disk means an empty book on rebuild; reseed it."""
    if os.getenv("SEED_ON_EMPTY", "1") not in ("1", "true", "yes"):
        return
    try:
        from ape.db.session import init_db, session_scope
        from ape.db.models import Client
        init_db()
        with session_scope() as db:
            n = db.query(Client).count()
        if n > 0:
            print(f"[deploy] SQL book present ({n} clients)", flush=True)
            return
        print("[deploy] SQL book empty — seeding synthetic data", flush=True)
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "seed_sql_synthetic.py")],
            cwd=str(ROOT), capture_output=True, text=True, timeout=300)
        tail = (r.stdout or r.stderr).strip().splitlines()[-3:]
        for line in tail:
            print(f"[deploy]   {line}", flush=True)
    except Exception as exc:                       # boot must not die on this
        print(f"[deploy] seeding skipped: {exc}", flush=True)


def run_boot_tasks() -> None:
    materialise_gmail_token()
    seed_if_empty()
