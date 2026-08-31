"""Relational schema — shared domain tables, keyed by client_id.

═══════════════════════════════════════════════════════════════════════════
ONE TABLE PER CONCEPT, NOT ONE PER CLIENT
═══════════════════════════════════════════════════════════════════════════

1,000 clients means 1,000 rows in `holdings`, not 1,000 `holdings` tables.
Per-client tables make migrations, cross-client analytics and APE learning
(which is inherently population-level) impractical. Every row carries
`client_id`; that is the isolation key, enforced in every query.

═══════════════════════════════════════════════════════════════════════════
IMMUTABLE SNAPSHOTS
═══════════════════════════════════════════════════════════════════════════

A report is generated from a `report_snapshot`, and every portfolio fact
hangs off that snapshot rather than off the client. So:

    C1001 ── snapshot 2025Q4 ── holdings / allocations / performance / fees
          ── snapshot 2026Q1 ── ...
          ── snapshot 2026Q2 ── ...

Regenerating a Q1 report next year reproduces the Q1 figures exactly,
because today's portfolio moving cannot alter a closed snapshot. Without
this an old report silently rewrites itself, which for a document already
sent to a client is indefensible.

═══════════════════════════════════════════════════════════════════════════
PORTABILITY
═══════════════════════════════════════════════════════════════════════════

SQLite locally, PostgreSQL later — same models, same queries, connection
string only. Deliberately avoided: server-side defaults, JSONB-specific
operators, and sequences. JSON columns use SQLAlchemy's portable `JSON`,
which maps to TEXT on SQLite and JSONB on Postgres.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Client / portfolio
# ---------------------------------------------------------------------------

class Client(Base):
    __tablename__ = "clients"

    client_id:   Mapped[str] = mapped_column(String(32), primary_key=True)
    name:        Mapped[str] = mapped_column(String(120))
    email:       Mapped[str] = mapped_column(String(200), index=True)
    segment_id:  Mapped[str] = mapped_column(String(64), index=True)
    persona:     Mapped[str] = mapped_column(String(64), default="")
    risk_profile: Mapped[str] = mapped_column(String(32), default="Moderate")
    adviser:     Mapped[str] = mapped_column(String(120), default="")
    status:      Mapped[str] = mapped_column(String(24), default="active")
    # Second factor when opening a report link. Nullable because the client
    # feed does not carry it yet — identity.DEFAULT_BIRTH_YEAR stands in
    # until a firm populates this from its CRM. Only the year is stored:
    # it is all the check needs, and a full date of birth is more personal
    # data than the check justifies holding.
    birth_year:  Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Where an adviser alert gets sent. Nullable for the same reason as
    # birth_year above — the client feed does not carry it yet, and
    # alerts.DEFAULT_ADVISER_EMAIL stands in until a firm's adviser
    # roster is connected.
    adviser_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # Which language this client's report is written in, and which number
    # convention it uses. Nullable = English, so an unset feed behaves
    # exactly as it did before locales existed.
    language: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=_now)

    snapshots: Mapped[list["ReportSnapshot"]] = relationship(back_populates="client")


class ReportSnapshot(Base):
    """Frozen portfolio facts for one client and one period. Never updated."""

    __tablename__ = "report_snapshots"
    __table_args__ = (
        UniqueConstraint("client_id", "period", "version", name="uq_snapshot"),
        Index("ix_snapshot_client_period", "client_id", "period"),
    )

    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id:   Mapped[str] = mapped_column(ForeignKey("clients.client_id"), index=True)
    period:      Mapped[str] = mapped_column(String(16), index=True)
    as_of_date:  Mapped[str] = mapped_column(String(16))
    version:     Mapped[int] = mapped_column(Integer, default=1)
    portfolio_value: Mapped[float] = mapped_column(Float)
    risk_level:  Mapped[str] = mapped_column(String(32), default="Moderate")
    source_version: Mapped[str] = mapped_column(String(32), default="synthetic-v1")
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=_now)

    client: Mapped["Client"] = relationship(back_populates="snapshots")


# NOTE ON THE `snapshot` / `report` RELATIONSHIPS BELOW
# -----------------------------------------------------
# They exist for INSERT ORDERING, not for convenient traversal. A bare
# ForeignKey column does not tell the ORM's unit of work that the parent row
# must be written first, so without a mapped relationship the child rows are
# inserted before their snapshot and the flush fails on the foreign key.


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (Index("ix_holdings_snapshot", "snapshot_id"),)

    snapshot: Mapped["ReportSnapshot"] = relationship()

    id:          Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("report_snapshots.snapshot_id"), index=True)
    client_id:   Mapped[str] = mapped_column(String(32), index=True)
    symbol:      Mapped[str] = mapped_column(String(24))
    name:        Mapped[str] = mapped_column(String(160))
    asset_class: Mapped[str] = mapped_column(String(64), index=True)
    quantity:    Mapped[float] = mapped_column(Float, default=0.0)
    market_value: Mapped[float] = mapped_column(Float)
    weight_pct:  Mapped[float] = mapped_column(Float)
    return_pct:  Mapped[float] = mapped_column(Float, default=0.0)
    contribution_pct: Mapped[float] = mapped_column(Float, default=0.0)


class Allocation(Base):
    __tablename__ = "allocations"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "asset_class", name="uq_alloc"),
    )

    snapshot: Mapped["ReportSnapshot"] = relationship()

    id:          Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("report_snapshots.snapshot_id"), index=True)
    client_id:   Mapped[str] = mapped_column(String(32), index=True)
    asset_class: Mapped[str] = mapped_column(String(64))
    weight_pct:  Mapped[float] = mapped_column(Float)
    target_weight_pct: Mapped[float] = mapped_column(Float, default=0.0)
    return_pct:  Mapped[float] = mapped_column(Float, default=0.0)
    contribution_pct: Mapped[float] = mapped_column(Float, default=0.0)
    market_value: Mapped[float] = mapped_column(Float, default=0.0)


class Performance(Base):
    __tablename__ = "performance"

    snapshot: Mapped["ReportSnapshot"] = relationship()

    id:          Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("report_snapshots.snapshot_id"),
                                             unique=True, index=True)
    client_id:   Mapped[str] = mapped_column(String(32), index=True)
    period:      Mapped[str] = mapped_column(String(16))
    portfolio_return_pct: Mapped[float] = mapped_column(Float)
    benchmark_name:       Mapped[str] = mapped_column(String(80), default="")
    benchmark_return_pct: Mapped[float] = mapped_column(Float)
    excess_return_pct:    Mapped[float] = mapped_column(Float)
    volatility_pct:       Mapped[float] = mapped_column(Float, default=0.0)


class Fee(Base):
    __tablename__ = "fees"

    snapshot: Mapped["ReportSnapshot"] = relationship()

    id:          Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("report_snapshots.snapshot_id"), index=True)
    client_id:   Mapped[str] = mapped_column(String(32), index=True)
    fee_type:    Mapped[str] = mapped_column(String(48))
    amount:      Mapped[float] = mapped_column(Float)


class CashFlow(Base):
    __tablename__ = "cash_flows"

    snapshot: Mapped["ReportSnapshot"] = relationship()

    id:          Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("report_snapshots.snapshot_id"), index=True)
    client_id:   Mapped[str] = mapped_column(String(32), index=True)
    flow_type:   Mapped[str] = mapped_column(String(48))   # contribution | withdrawal | income
    amount:      Mapped[float] = mapped_column(Float)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_client_period", "client_id", "period"),)

    report_id:   Mapped[str] = mapped_column(String(80), primary_key=True)
    client_id:   Mapped[str] = mapped_column(ForeignKey("clients.client_id"), index=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("report_snapshots.snapshot_id"))
    period:      Mapped[str] = mapped_column(String(16))
    report_type: Mapped[str] = mapped_column(String(64), index=True)
    # The ARM that produced this report. Recorded so a reward can find its way
    # back to the exact arm, and so a bad template version stays detectable.
    template_arm:     Mapped[str] = mapped_column(String(64), index=True)
    template_id:      Mapped[str] = mapped_column(String(80), default="")
    selection_method: Mapped[str] = mapped_column(String(24), default="")
    status:      Mapped[str] = mapped_column(String(24), default="DRAFT")
    report_version: Mapped[int] = mapped_column(Integer, default=1)
    html_path:   Mapped[str] = mapped_column(String(300), default="")
    pdf_path:    Mapped[str] = mapped_column(String(300), default="")
    validation:  Mapped[str] = mapped_column(String(32), default="")
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=_now)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sent_at:     Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Reward attribution — mirrors the APE turn_record contract.
    reward_status:     Mapped[str] = mapped_column(String(16), default="PENDING")
    normalized_reward: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # The rendered podcast, once it exists. NULL means nobody has asked.
    # The script is kept beside the URL deliberately: the audio lives on a
    # third party's disk for 24 hours, and when it expires the script is
    # the only record of what the client was actually told.
    podcast_url:    Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    podcast_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    podcast_at:     Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ReportBlock(Base):
    """One rendered block. `block_id` is what a client highlight resolves to,
    which is why it is stored rather than only living inside report.json."""

    __tablename__ = "report_blocks"
    __table_args__ = (
        UniqueConstraint("report_id", "block_id", name="uq_report_block"),
        Index("ix_blocks_report", "report_id"),
    )

    report: Mapped["Report"] = relationship()

    id:        Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    block_id:  Mapped[str] = mapped_column(String(80), index=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.report_id"), index=True)
    client_id: Mapped[str] = mapped_column(String(32), index=True)
    block_type: Mapped[str] = mapped_column(String(48))
    section_id: Mapped[str] = mapped_column(String(64), default="")
    title:      Mapped[str] = mapped_column(String(200), default="")
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    # The snapshot fields this block's figures came from. Highlight -> block
    # -> source_refs -> frozen facts is the grounded answer path, and it
    # needs no retrieval at all.
    source_refs: Mapped[list] = mapped_column(JSON, default=list)
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class Delivery(Base):
    __tablename__ = "deliveries"

    report: Mapped["Report"] = relationship()

    id:        Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.report_id"), index=True)
    client_id: Mapped[str] = mapped_column(String(32), index=True)
    to_email:  Mapped[str] = mapped_column(String(200))
    provider:  Mapped[str] = mapped_column(String(32))
    status:    Mapped[str] = mapped_column(String(32))
    message_id: Mapped[str] = mapped_column(String(200), default="")
    sent_at:   Mapped[datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Conversation + signals (D2)
# ---------------------------------------------------------------------------

class Conversation(Base):
    __tablename__ = "conversations"

    report: Mapped["Report"] = relationship()

    conversation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.client_id"), index=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.report_id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conv", "conversation_id", "created_at"),)

    conversation: Mapped["Conversation"] = relationship()

    message_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.conversation_id"),
                                                 index=True)
    client_id: Mapped[str] = mapped_column(String(32), index=True)
    report_id: Mapped[str] = mapped_column(String(80), index=True)
    role:      Mapped[str] = mapped_column(String(16))          # client | assistant
    content:   Mapped[str] = mapped_column(Text)
    content_intent:  Mapped[str] = mapped_column(String(48), default="")
    format_intents:  Mapped[list] = mapped_column(JSON, default=list)
    # The D2 ARM that produced this answer. Reward attaches here, not to the
    # report template — a thumbs-down on an answer says nothing about whether
    # the report should have been a table.
    answer_strategy: Mapped[str] = mapped_column(String(48), default="")
    # HOW this answer was produced: llm, llm_retry, llm_stream,
    # llm_stream_retry, declined_ungrounded, no_key. Returned to the caller
    # all along but never stored, which meant the transcript could not
    # distinguish a real answer from a refusal after the fact — and "how
    # often does the report fail to answer this client" is exactly the
    # question the adviser alerts need to ask.
    author: Mapped[str] = mapped_column(String(32), default="", index=True)
    block_ids: Mapped[list] = mapped_column(JSON, default=list)
    # What the answer was made OF, kept so a restored conversation is the
    # same conversation. Sources are the sections it cited; widget is the
    # chart it was shown with, SVG and all.
    #
    # Follow-up chips are deliberately NOT stored. They are a suggestion
    # about what to ask NEXT, and next has already happened by the time
    # anyone re-reads this — restoring them would put a stale prompt under
    # an answer whose conversation moved on. They are regenerated live.
    sources: Mapped[list] = mapped_column(JSON, default=list)
    widget:  Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Event(Base):
    """Every observable client action. The raw material for both rewards and
    the preference profile."""

    __tablename__ = "events"
    __table_args__ = (Index("ix_events_client_time", "client_id", "created_at"),)

    event_id:  Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(32), index=True)
    report_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    message_id: Mapped[str] = mapped_column(String(64), default="")
    block_id:  Mapped[str] = mapped_column(String(80), default="")
    event_type: Mapped[str] = mapped_column(String(48), index=True)
    signal_type: Mapped[str] = mapped_column(String(48), default="")
    signal_strength: Mapped[float] = mapped_column(Float, default=0.0)
    # Which decision this evidence belongs to. Keeping it explicit stops
    # answer-format feedback leaking into report-template rewards.
    applies_to: Mapped[str] = mapped_column(String(8), default="")   # D1 | D2 | ""
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AdviserAlert(Base):
    """A client looked like they needed a human, and their adviser was told.

    Separate from `events` on purpose. An event is something the client did;
    an alert is something WE decided and acted on. Mixing them would make
    "why did this adviser get an email" impossible to answer later, and that
    question is exactly what someone asks when the channel is noisy.

    The row is written whether or not the email left the building —
    `delivery_status` carries the outcome. Losing the record of a client who
    needed help because SMTP was down is the worst possible failure here.
    """

    __tablename__ = "adviser_alerts"
    __table_args__ = (Index("ix_alerts_client_time", "client_id", "created_at"),)

    alert_id:  Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(32), index=True)
    report_id: Mapped[str] = mapped_column(String(80), index=True, default="")
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    trigger:   Mapped[str] = mapped_column(String(48), index=True)
    detail:    Mapped[str] = mapped_column(Text, default="")
    adviser_email: Mapped[str] = mapped_column(String(200), default="")
    delivery_status: Mapped[str] = mapped_column(String(200), default="pending")
    # Read state is the adviser's, not the client's. Kept here rather than
    # inferred from "has the adviser opened the dashboard" because an
    # adviser scanning a list has not necessarily dealt with anything in it.
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)


# ---------------------------------------------------------------------------
# APE state
# ---------------------------------------------------------------------------

class ClientPreference(Base):
    """The learned presentation profile — the bridge between chat learning
    and next-quarter report personalisation.

    SCOPED BY REPORT TYPE. How someone wants a quarterly review is not how
    they want a tax summary: one is read for reassurance, the other for a
    number. A single profile per client averaged those together and handed
    the same nine floats to every report the advisor produced.

    `report_type=""` is the CLIENT-WIDE row — everything learned about this
    person across all report types. Every signal updates both it and the
    row for the type it happened in, so the wide row never stops growing
    and a report type nobody has interacted with yet still starts from
    what is known about the client rather than from nothing.
    """

    __tablename__ = "client_preferences"

    client_id: Mapped[str] = mapped_column(ForeignKey("clients.client_id"), primary_key=True)
    report_type: Mapped[str] = mapped_column(String(64), primary_key=True, default="")
    concise:   Mapped[float] = mapped_column(Float, default=0.5)
    detail:    Mapped[float] = mapped_column(Float, default=0.5)
    visual:    Mapped[float] = mapped_column(Float, default=0.5)
    table_pref: Mapped[float] = mapped_column(Float, default=0.5)
    comparison: Mapped[float] = mapped_column(Float, default=0.5)
    numeric_precision: Mapped[float] = mapped_column(Float, default=0.5)
    narrative: Mapped[float] = mapped_column(Float, default=0.5)
    step_by_step: Mapped[float] = mapped_column(Float, default=0.5)
    technical_depth: Mapped[float] = mapped_column(Float, default=0.5)
    meaningful_signal_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    DIMENSION_COLUMNS = ("concise", "detail", "visual", "table_pref", "comparison",
                         "numeric_precision", "narrative", "step_by_step",
                         "technical_depth")

    def as_dimensions(self) -> dict:
        """Keyed by the shared vocabulary — `table_pref` is stored under that
        name only because `table` is reserved in some SQL dialects."""
        d = {c: getattr(self, c) for c in self.DIMENSION_COLUMNS}
        d["table"] = d.pop("table_pref")
        return d


class ClientSkill(Base):
    """What this client's own behaviour has taught us, in words.

    The bandit's arm rewards cannot help a COMPOSED layout — there is no
    arm to reward. This is the composer's memory instead: a brief rebuilt
    from highlights, questions and past engagement, handed back to the
    model next time so each report starts from what the last one revealed.

    Stored rather than derived on demand so an advisor can read what the
    system believes about a client and override it — `advisor_note` takes
    precedence over anything inferred, because a human who knows the client
    is better evidence than behaviour.

    SCOPED BY REPORT TYPE, like the preference profile. "Returns to the
    fees section every quarter" is a fact about quarterly reviews, and
    carrying it into a risk report is stating something never observed
    there. `report_type=""` is the client-wide brief, used when a type has
    too little history of its own to generalise from.
    """

    __tablename__ = "client_skills"

    report_type: Mapped[str] = mapped_column(String(64), primary_key=True,
                                             default="")
    client_id:  Mapped[str] = mapped_column(ForeignKey("clients.client_id"),
                                            primary_key=True)
    brief:      Mapped[str] = mapped_column(Text, default="")
    # Preferences the client stated in their own words, as
    # [{aspect, phrase, count, actionable}]. The nine dimensions are a
    # closed vocabulary and cannot hold "put the fee line first" or "send
    # this as a video"; this can. `actionable` records whether the
    # composer can act on it or whether it needs a human.
    stated_prefs: Mapped[list] = mapped_column(JSON, default=list)
    advisor_note: Mapped[str] = mapped_column(Text, default="")
    top_blocks:    Mapped[list] = mapped_column(JSON, default=list)
    ignored_blocks: Mapped[list] = mapped_column(JSON, default=list)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ApeState(Base):
    """One arm, at one scope. Beta parameters because D1 selection is
    Thompson sampling; `alpha`/`beta` are the posterior, `total_reward` and
    `selection_count` the raw evidence behind them."""

    __tablename__ = "ape_state"
    __table_args__ = (
        UniqueConstraint("scope_type", "scope_id", "decision", "context", "arm_id",
                         name="uq_ape_arm"),
        Index("ix_ape_cell", "scope_type", "scope_id", "context"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope_type: Mapped[str] = mapped_column(String(16))      # GLOBAL | SEGMENT | CLIENT
    scope_id:   Mapped[str] = mapped_column(String(64), default="_global")
    decision:   Mapped[str] = mapped_column(String(4), default="D1")   # D1 | D2
    # report_type for D1, question intent for D2.
    context:    Mapped[str] = mapped_column(String(64))
    arm_id:     Mapped[str] = mapped_column(String(64))
    alpha:      Mapped[float] = mapped_column(Float, default=1.0)
    beta:       Mapped[float] = mapped_column(Float, default=1.0)
    selection_count: Mapped[int] = mapped_column(Integer, default=0)
    reward_count:    Mapped[int] = mapped_column(Integer, default=0)
    total_reward:    Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


ALL_TABLES = [
    Client, ReportSnapshot, Holding, Allocation, Performance, Fee, CashFlow,
    Report, ReportBlock, Delivery, Conversation, Message, Event,
    ClientPreference, ApeState,
]
