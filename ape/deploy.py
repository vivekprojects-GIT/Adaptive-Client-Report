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
PUBLIC_PREFIXES = ("/r/", "/health", "/login")


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


_LOGIN_PAGE = """<!doctype html><meta charset="utf-8">
<title>Advisor sign in</title>
<div style="font-family:'Segoe UI',system-ui,Arial;max-width:340px;
  margin:16vh auto;color:#0f172a">
  <h2 style="font-size:19px;margin:0 0 4px">Advisor sign in</h2>
  <p style="color:#64748b;font-size:13.5px;margin:0 0 18px">
    This area is for advisors. Clients open reports through their
    personal emailed link and do not sign in.</p>
  <form method="post" action="/login">
    <input type="password" name="password" placeholder="Password" autofocus
      style="width:100%;box-sizing:border-box;padding:10px 12px;font-size:14px;
      border:1px solid #cbd5e1;border-radius:7px;margin-bottom:10px">
    <button style="width:100%;padding:10px;background:#1d4ed8;color:#fff;
      border:0;border-radius:7px;font-size:14px;font-weight:600;
      cursor:pointer">Sign in</button>
  </form>
  __ERROR__
</div>"""


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
                '<p style="color:#b91c1c;font-size:13px">Wrong password.</p>'),
                status_code=401)
        resp = RedirectResponse("/", status_code=302)
        resp.set_cookie(
            COOKIE_NAME, _sign_session(int(time.time()) + SESSION_TTL),
            max_age=SESSION_TTL, httponly=True, samesite="lax",
            secure=bool(os.getenv("APP_BASE_URL", "").startswith("https")))
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
