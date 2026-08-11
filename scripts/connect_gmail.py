"""One-time Gmail authorisation for local testing.

    1. Google Cloud Console -> new project -> enable Gmail API
    2. OAuth consent screen -> External -> Testing -> add your Gmail as a test user
    3. Credentials -> OAuth client ID -> Application type: Desktop app
    4. Download and save the JSON here as credentials.json
    5. python scripts/connect_gmail.py

Opens a browser, you consent, and token.json is written. The token carries a
refresh token, so this is needed once per machine, not per send.

Scope is gmail.send only: the narrowest scope that can send a message. It
grants no ability to read the mailbox, which matters because this is a real
personal account.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    sys.exit("pip install google-api-python-client google-auth "
             "google-auth-oauthlib google-auth-httplib2")

creds_path = ROOT / "credentials.json"
if not creds_path.is_file():
    sys.exit(f"credentials.json not found at {creds_path}\n"
             "Download it from Google Cloud Console (Desktop app OAuth client).")

flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
creds = flow.run_local_server(port=0)
(ROOT / "token.json").write_text(creds.to_json(), encoding="utf-8")
print(f"Gmail connected. token.json written to {ROOT / 'token.json'}")
print("Set EMAIL_PROVIDER=gmail in .env to use it.")
