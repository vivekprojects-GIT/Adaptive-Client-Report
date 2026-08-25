"""Notify the adviser when a client is struggling, not just when they click.

WHY NOT EVERY QUESTION
-----------------------
A client asking questions is the product working — that's engagement, not
distress, and it already feeds the preference profile. Alerting on every
question would train advisers to ignore the channel within a week.

What actually indicates a client needs a human is narrower, and closed-
vocabulary on purpose — the same design already used for intents, event
types, and chart bindings elsewhere in this codebase:

    EXPLICIT_NEGATIVE   the client said so — a thumbs-down on an answer
                         or the report itself. The strongest possible
                         signal because it needs no inference at all.

    REPEATED_DECLINE    the report told the SAME client, twice in one
                         conversation, that it could not answer. Once is
                         a client asking something out of scope (normal).
                         Twice is a client stuck on something the report
                         genuinely cannot help with — which is exactly
                         when a human should step in.

Nothing here reads question TEXT for sentiment. That would be guessing;
these two triggers are structural facts already sitting in the database.

COOLDOWN
--------
One trigger firing twice in five minutes is the same problem, not two.
`_recent_alert()` checks for a prior alert on this (client, report) pair
inside COOLDOWN_MINUTES before sending another — the fix for "this client
got 3 emails about the same conversation" that a naive version would ship.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ape.db.models import AdviserAlert, Client, Message

TRIGGER_EXPLICIT_NEGATIVE = "explicit_negative"
TRIGGER_REPEATED_DECLINE = "repeated_decline"

VALID_TRIGGERS = {TRIGGER_EXPLICIT_NEGATIVE, TRIGGER_REPEATED_DECLINE}

COOLDOWN_MINUTES = 30

# Two declines in the SAME conversation is the threshold, not one. A single
# decline is a client asking something out of scope, which is normal and
# does not deserve to interrupt an adviser's day.
DECLINE_THRESHOLD = 2

# Demo fallback when a client's adviser has no email on file yet — same
# honest-placeholder pattern as identity.DEFAULT_BIRTH_YEAR: real machinery,
# a stand-in value, replaced by real adviser records without touching code.
import os
DEFAULT_ADVISER_EMAIL = os.getenv("APE_DEFAULT_ADVISER_EMAIL",
                                  "advisers@example.local")

# Email is OFF by default, and the in-app bell is the delivery channel.
#
# Two reasons, both learned the hard way. First, sending mail from the
# answer path froze the chat: the send happened inside the SSE generator,
# so the stream could not close, the browser's reader never finished, and
# the viewer's `busy` flag stayed true — a dead send button that looked
# like the report had hung. Measured at 8s for one slow round trip, and
# unbounded if the provider stalls.
#
# Second, EMAIL_PROVIDER=gmail sends REAL mail. An alerting feature that
# silently starts emailing real addresses the moment it is merged is not
# a feature anyone asked for. Turning this on should be a decision.
ALERT_EMAIL_ENABLED = os.getenv("APE_ALERT_EMAIL", "0").lower() in (
    "1", "true", "yes", "on")


def _recent_alert(session: Session, client_id: str, report_id: str,
                  trigger: str) -> bool:
    cutoff = datetime.utcnow() - timedelta(minutes=COOLDOWN_MINUTES)
    row = session.scalars(
        select(AdviserAlert).where(
            AdviserAlert.client_id == client_id,
            AdviserAlert.report_id == report_id,
            AdviserAlert.trigger == trigger,
            AdviserAlert.created_at >= cutoff,
        ).limit(1)).first()
    return row is not None


def _adviser_contact(session: Session, client_id: str) -> tuple[str, str]:
    """(adviser_name, adviser_email) — the second falls back honestly."""
    client = session.get(Client, client_id)
    name = (client.adviser if client else "") or "your client's adviser"
    email = (getattr(client, "adviser_email", None) if client else None)
    return name, (email or DEFAULT_ADVISER_EMAIL)


def maybe_alert(session: Session, client_id: str, report_id: str,
                trigger: str, detail: str,
                conversation_id: str = "") -> Optional[dict]:
    """Send an adviser alert if the trigger is real and not on cooldown.

    Returns the alert record as a dict when one was sent, None when the
    trigger was suppressed by cooldown — callers that want to know why can
    check `_recent_alert` directly; this stays quiet on the common path.
    """
    if trigger not in VALID_TRIGGERS:
        return None
    if _recent_alert(session, client_id, report_id, trigger):
        return None

    adviser_name, adviser_email = _adviser_contact(session, client_id)
    client = session.get(Client, client_id)
    client_name = client.display_name if hasattr(client, "display_name") else (
        getattr(client, "name", client_id))

    row = AdviserAlert(
        alert_id=f"alert_{uuid.uuid4().hex[:12]}", client_id=client_id,
        report_id=report_id, conversation_id=conversation_id,
        trigger=trigger, detail=detail, adviser_email=adviser_email,
    )
    # The row is the alert. It is written synchronously because it is a
    # local insert measured in microseconds, and because the notification
    # bell reads it — an adviser sees this the moment it happens whether
    # or not any mail is configured.
    row.delivery_status = "in_app" if not ALERT_EMAIL_ENABLED else "queued"
    session.add(row)
    session.flush()
    alert_id = row.alert_id

    if ALERT_EMAIL_ENABLED:
        # Off the request thread, always. Nothing the client is waiting on
        # may block on someone else's mail server.
        _dispatch_email_async(alert_id, adviser_email, adviser_name,
                              client_name, report_id, trigger, detail)

    return {"alert_id": alert_id, "trigger": trigger,
            "adviser_email": adviser_email, "status": row.delivery_status}


def _dispatch_email_async(alert_id: str, adviser_email: str,
                          adviser_name: str, client_name: str,
                          report_id: str, trigger: str, detail: str) -> None:
    """Send in a daemon thread, then record the outcome in its own session.

    A separate session on purpose: the caller's transaction belongs to the
    client's request and may commit or roll back long before the mail
    server answers. Writing the delivery result through it would either
    block that request or lose the result.
    """
    import threading

    def _run() -> None:
        from ape.db.session import session_scope
        from ape.reporting.email import get_provider
        status = "sent"
        try:
            get_provider().send_adviser_alert(
                adviser_email=adviser_email, adviser_name=adviser_name,
                client_name=client_name, report_id=report_id,
                trigger=trigger, detail=detail)
        except Exception as exc:                   # noqa: BLE001
            status = f"failed: {exc}"[:200]
        try:
            with session_scope() as db:
                row = db.get(AdviserAlert, alert_id)
                if row is not None:
                    row.delivery_status = status
        except Exception:
            pass       # the alert itself is already safely recorded

    threading.Thread(target=_run, name=f"alert-mail-{alert_id}",
                     daemon=True).start()


def check_repeated_decline(session: Session, client_id: str, report_id: str,
                           conversation_id: str) -> Optional[dict]:
    """Call after persisting a declined-answer message.

    Counts declines in THIS conversation only — a client stuck across two
    unrelated report openings is two separate, milder problems, not one
    urgent one.
    """
    from sqlalchemy import func
    n = session.scalar(
        select(func.count()).select_from(Message).where(
            Message.conversation_id == conversation_id,
            Message.author == "declined_ungrounded",
        ))
    if n is None or n < DECLINE_THRESHOLD:
        return None
    return maybe_alert(
        session, client_id, report_id, TRIGGER_REPEATED_DECLINE,
        detail=f"The report could not answer this client's question "
               f"{n} times in one conversation.",
        conversation_id=conversation_id)
