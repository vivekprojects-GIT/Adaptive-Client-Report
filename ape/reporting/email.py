"""Email delivery — one interface, three backends.

    EMAIL_PROVIDER=file     (default)  writes .eml to data/generated/emails/
    EMAIL_PROVIDER=gmail               Gmail API, local OAuth desktop flow
    EMAIL_PROVIDER=stub                records the intent, sends nothing

`file` is the default rather than `stub` because a written .eml opens in any
mail client, so the actual rendered email can be inspected without
credentials and without sending anything to a real inbox.

THE SECURE LINK IS THE PAYLOAD
------------------------------
The email carries a link, not the report. An attachment cannot host the chat,
and the chat is where the learning signal comes from. The PDF stays available
behind the link as the downloadable record.
"""

from __future__ import annotations

import base64
import os
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

EMAIL_DIR = Path(__file__).resolve().parents[2] / "data" / "generated" / "emails"


def _build_message(to_email: str, client_name: str, report_url: str,
                   period: str, from_email: str) -> EmailMessage:
    msg = EmailMessage()
    msg["To"] = to_email
    msg["From"] = from_email
    msg["Subject"] = f"Your {period} portfolio report is ready"

    msg.set_content(
        f"Hi {client_name},\n\n"
        f"Your {period} portfolio report is ready.\n\n"
        f"Open your report:\n{report_url}\n\n"
        "For your security you'll be asked to confirm your year of birth\n"
        "the first time you open it.\n\n"
        "You can review it, highlight any section and ask questions about it,\n"
        "and download the PDF.\n"
    )
    msg.add_alternative(f"""\
<html><body style="font-family:-apple-system,Segoe UI,Arial,sans-serif;
  background:#f1f5f9;margin:0;padding:28px">
  <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:10px;
    padding:30px 34px">
    <h2 style="margin:0 0 4px;font-size:19px;color:#0f172a">
      Your {period} report is ready</h2>
    <p style="color:#64748b;font-size:14px;margin:0 0 20px">Hi {client_name},</p>
    <p style="color:#334155;font-size:14px;line-height:1.55;margin:0 0 22px">
      Your latest portfolio report covers performance, allocation, fees and
      any changes this period.
    </p>
    <p style="margin:0 0 22px">
      <a href="{report_url}" style="background:#1d4ed8;color:#fff;
        padding:12px 22px;text-decoration:none;border-radius:6px;
        font-weight:600;font-size:14px;display:inline-block">View my report</a>
    </p>
    <p style="color:#64748b;font-size:13px;line-height:1.55;margin:0">
      Inside the report you can highlight any section and ask questions about
      it, or download a PDF copy.
    </p>
    <p style="color:#64748b;font-size:13px;line-height:1.55;margin:14px 0 0">
      For your security, you'll be asked to confirm your year of birth the
      first time you open it.
    </p>
    <p style="color:#94a3b8;font-size:11.5px;margin:22px 0 0;
      border-top:1px solid #e2e8f0;padding-top:14px">
      This link is personal to you and expires. Forwarding it will not give
      anyone else access.
    </p>
  </div>
</body></html>""", subtype="html")
    return msg


TRIGGER_LABELS = {
    "explicit_negative": "said an answer or the report was unhelpful",
    "repeated_decline": "asked questions the report could not answer",
}


def _build_alert(adviser_email: str, adviser_name: str, client_name: str,
                 report_id: str, trigger: str, detail: str,
                 from_email: str) -> EmailMessage:
    """The adviser-facing alert.

    Deliberately carries NO client figures. This mail may sit in an inbox,
    be forwarded internally, or be read on a phone in public — the report
    itself is already behind two gates, and reproducing its numbers here
    would route around both. It says who, and why, and nothing else.
    """
    reason = TRIGGER_LABELS.get(trigger, trigger)
    msg = EmailMessage()
    msg["To"] = adviser_email
    msg["From"] = from_email
    msg["Subject"] = f"{client_name} may need a hand with their report"

    msg.set_content(
        f"Hi {adviser_name},\n\n"
        f"{client_name} {reason} while reading their report.\n\n"
        f"{detail}\n\n"
        f"Report: {report_id}\n\n"
        "This is an automatic notice based on how they used the report.\n"
        "No client figures are included in this email.\n"
    )
    msg.add_alternative(f"""\
<html><body style="font-family:-apple-system,Segoe UI,Arial,sans-serif;
  background:#f1f5f9;margin:0;padding:28px">
  <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:10px;
    padding:30px 34px">
    <p style="margin:0 0 6px;font-size:11px;letter-spacing:.12em;
      text-transform:uppercase;color:#b45309;font-weight:700">Client needs help</p>
    <h2 style="margin:0 0 16px;font-size:19px;color:#0f172a">
      {client_name} may need a hand</h2>
    <p style="color:#334155;font-size:14px;line-height:1.55;margin:0 0 14px">
      Hi {adviser_name}, {client_name} {reason} while reading their report.
    </p>
    <p style="color:#334155;font-size:14px;line-height:1.55;margin:0 0 20px;
      padding:12px 15px;background:#fef3c7;border-radius:7px">{detail}</p>
    <p style="color:#64748b;font-size:12.5px;margin:0">Report: {report_id}</p>
    <p style="color:#94a3b8;font-size:11.5px;margin:20px 0 0;
      border-top:1px solid #e2e8f0;padding-top:14px">
      Automatic notice based on how this client used their report.
      No client figures are included in this email.
    </p>
  </div>
</body></html>""", subtype="html")
    return msg


class EmailProvider(Protocol):
    def send_report_ready(self, to_email: str, client_name: str,
                          report_url: str, period: str) -> Dict[str, Any]: ...

    def send_adviser_alert(self, adviser_email: str, adviser_name: str,
                           client_name: str, report_id: str,
                           trigger: str, detail: str) -> Dict[str, Any]: ...


class FileEmailProvider:
    """Writes the exact MIME message to disk. Nothing leaves the machine."""

    name = "file"

    def send_report_ready(self, to_email, client_name, report_url, period):
        EMAIL_DIR.mkdir(parents=True, exist_ok=True)
        msg = _build_message(to_email, client_name, report_url, period,
                             os.getenv("EMAIL_FROM", "reports@example.local"))
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe = to_email.replace("@", "_at_").replace(".", "_")
        path = EMAIL_DIR / f"{stamp}_{safe}.eml"
        path.write_bytes(msg.as_bytes())
        return {"status": "written", "provider": "file", "path": str(path),
                "to": to_email, "url": report_url}

    def send_adviser_alert(self, adviser_email, adviser_name, client_name,
                           report_id, trigger, detail):
        EMAIL_DIR.mkdir(parents=True, exist_ok=True)
        msg = _build_alert(adviser_email, adviser_name, client_name,
                           report_id, trigger, detail,
                           os.getenv("EMAIL_FROM", "reports@example.local"))
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe = adviser_email.replace("@", "_at_").replace(".", "_")
        path = EMAIL_DIR / f"{stamp}_ALERT_{safe}.eml"
        path.write_bytes(msg.as_bytes())
        return {"status": "written", "provider": "file", "path": str(path),
                "to": adviser_email, "trigger": trigger}


class StubEmailProvider:
    name = "stub"

    def send_report_ready(self, to_email, client_name, report_url, period):
        return {"status": "sent (stub)", "provider": "stub",
                "to": to_email, "url": report_url}

    def send_adviser_alert(self, adviser_email, adviser_name, client_name,
                           report_id, trigger, detail):
        return {"status": "sent (stub)", "provider": "stub",
                "to": adviser_email, "trigger": trigger}


class GmailEmailProvider:
    """Gmail API via a local OAuth desktop flow.

    Requires `token.json`, produced once by scripts/connect_gmail.py. The
    token carries a refresh token, so after the first browser consent this
    runs unattended.

    Scope is gmail.send only — the narrowest scope that can send, and it
    grants no read access to the mailbox.
    """

    name = "gmail"
    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    def __init__(self, token_path: Optional[str] = None):
        # ANCHORED TO THE REPO, not to the working directory.
        #
        # This defaulted to the bare string "token.json", which Python
        # resolves against wherever the process happens to have been
        # started. Run the app from the repo root and Gmail worked; start
        # it from anywhere else — a service directory, a deploy script, a
        # different shell — and the very same authorised token became
        # invisible, reporting "token.json not found — run
        # scripts/connect_gmail.py", which sends you off to redo an
        # authorisation that was already done.
        #
        # EMAIL_DIR above already does it correctly; this now matches.
        # An explicit GMAIL_TOKEN_PATH still wins, and a relative one is
        # resolved against the repo rather than the cwd for the same reason.
        _root = Path(__file__).resolve().parents[2]
        raw = token_path or os.getenv("GMAIL_TOKEN_PATH", "token.json")
        p = Path(raw)
        self.token_path = str(p if p.is_absolute() else (_root / p))

    def _service(self):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError(
                "Gmail provider needs: pip install google-api-python-client "
                "google-auth google-auth-oauthlib google-auth-httplib2"
            ) from exc

        if not Path(self.token_path).is_file():
            raise RuntimeError(
                f"{self.token_path} not found — run scripts/connect_gmail.py once "
                "to authorise this machine."
            )
        creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            Path(self.token_path).write_text(creds.to_json(), encoding="utf-8")
        return build("gmail", "v1", credentials=creds)

    def send_report_ready(self, to_email, client_name, report_url, period):
        service = self._service()
        msg = _build_message(to_email, client_name, report_url, period,
                             os.getenv("EMAIL_FROM", "me"))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        res = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"status": "sent", "provider": "gmail", "message_id": res.get("id"),
                "to": to_email, "url": report_url}

    def send_adviser_alert(self, adviser_email, adviser_name, client_name,
                           report_id, trigger, detail):
        service = self._service()
        msg = _build_alert(adviser_email, adviser_name, client_name,
                           report_id, trigger, detail,
                           os.getenv("EMAIL_FROM", "me"))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        res = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"status": "sent", "provider": "gmail", "message_id": res.get("id"),
                "to": adviser_email, "trigger": trigger}


_PROVIDERS = {"file": FileEmailProvider, "gmail": GmailEmailProvider,
              "stub": StubEmailProvider}


def get_provider(name: Optional[str] = None) -> EmailProvider:
    key = (name or os.getenv("EMAIL_PROVIDER", "file")).lower()
    cls = _PROVIDERS.get(key)
    if cls is None:
        raise ValueError(f"unknown EMAIL_PROVIDER '{key}'; "
                         f"expected one of {', '.join(_PROVIDERS)}")
    return cls()
