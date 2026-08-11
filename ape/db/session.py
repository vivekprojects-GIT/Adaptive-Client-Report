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
    Base.metadata.create_all(engine)


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
