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
    <p style="color:#94a3b8;font-size:11.5px;margin:22px 0 0;
      border-top:1px solid #e2e8f0;padding-top:14px">
      This link is personal to you and expires. Please do not forward it.
    </p>
  </div>
</body></html>""", subtype="html")
    return msg


class EmailProvider(Protocol):
    def send_report_ready(self, to_email: str, client_name: str,
                          report_url: str, period: str) -> Dict[str, Any]: ...


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


class StubEmailProvider:
    name = "stub"

    def send_report_ready(self, to_email, client_name, report_url, period):
        return {"status": "sent (stub)", "provider": "stub",
                "to": to_email, "url": report_url}


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
        self.token_path = token_path or os.getenv("GMAIL_TOKEN_PATH", "token.json")

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


_PROVIDERS = {"file": FileEmailProvider, "gmail": GmailEmailProvider,
              "stub": StubEmailProvider}


def get_provider(name: Optional[str] = None) -> EmailProvider:
    key = (name or os.getenv("EMAIL_PROVIDER", "file")).lower()
    cls = _PROVIDERS.get(key)
    if cls is None:
        raise ValueError(f"unknown EMAIL_PROVIDER '{key}'; "
                         f"expected one of {', '.join(_PROVIDERS)}")
    return cls()
