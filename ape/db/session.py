"""Engine and session factory.

The database is chosen by DATABASE_URL alone:

    (unset)                                       -> SQLite at data/reporting.db
    postgresql+psycopg://user:pw@host:5432/apedb   -> PostgreSQL

Nothing else in the codebase names a dialect, so moving to Postgres is a
connection-string change. The one SQLite-specific line is the foreign-key
PRAGMA below — SQLite ignores FK constraints unless asked, which would let
orphaned rows accumulate locally and then fail on the first Postgres import.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ape.db.models import Base

DEFAULT_SQLITE_PATH = Path(__file__).resolve().parents[2] / "data" / "reporting.db"


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url
    DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"


_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        url = database_url()
        kwargs = {"future": True, "echo": False}
        if url.startswith("sqlite"):
            # check_same_thread: FastAPI serves requests on a thread pool.
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kwargs)
        if url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def _fk_on(dbapi_conn, _rec):     # noqa: ANN001
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False,
                                     future=True)
    return _engine


def init_db(drop: bool = False) -> None:
    engine = get_engine()
    if drop:
        Base.metadata.drop_all(engine)
    _migrate_report_type_scope(engine)
    Base.metadata.create_all(engine)


# Tables that gained `report_type` as part of their primary key when the
# learned profile and the composer's brief became per-report-type.
_SCOPED_TABLES = ("client_preferences", "client_skills")


def _migrate_report_type_scope(engine) -> None:
    """Add `report_type` to the scoped tables, preserving what is there.

    create_all() only creates tables it cannot see; it will not alter one
    that already exists, so without this an upgraded install keeps the old
    single-row-per-client schema and every write fails on the missing
    column. SQLite cannot ALTER a primary key either, so the table is
    rebuilt.

    Existing rows become the CLIENT-WIDE row (report_type=""), which is the
    honest reading of them: they were accumulated across every report type,
    so that is the scope they describe. No evidence is discarded and none
    is attributed to a report type it was not observed in.
    """
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    existing = set(insp.get_table_names())

    for table in _SCOPED_TABLES:
        if table not in existing:
            continue                       # create_all will build it fresh
        cols = {c["name"] for c in insp.get_columns(table)}
        if "report_type" in cols:
            continue                       # already migrated

        keep = [c for c in cols]
        col_list = ", ".join(f'"{c}"' for c in keep)
        with engine.begin() as conn:
            conn.execute(text(f'ALTER TABLE {table} RENAME TO {table}_old'))
            Base.metadata.tables[table].create(conn)
            conn.execute(text(
                f'INSERT INTO {table} ({col_list}, report_type) '
                f'SELECT {col_list}, \'\' FROM {table}_old'))
            conn.execute(text(f'DROP TABLE {table}_old'))
        print(f"[migrate] {table}: existing rows kept as the client-wide "
              f"scope (report_type='')", flush=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    get_engine()
    assert _SessionLocal is not None
    s = _SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_session() -> Session:
    """FastAPI dependency."""
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()
