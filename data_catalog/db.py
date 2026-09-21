"""Engine/session setup for the catalog's SQLite store.

Default location: data_catalog/catalog.db, next to this module, so the
bundled desktop app ships a single self-contained file with no external
service to run. Pass db_path=":memory:" for tests.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "catalog.db"


def make_engine(db_path: str | Path | None = None, *, echo: bool = False) -> Engine:
    if db_path == ":memory:":
        engine = create_engine(
            "sqlite:///:memory:",
            echo=echo,
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        path = Path(db_path) if db_path else DEFAULT_DB_PATH
        engine = create_engine(f"sqlite:///{path}", echo=echo, future=True)
    Base.metadata.create_all(engine)
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
