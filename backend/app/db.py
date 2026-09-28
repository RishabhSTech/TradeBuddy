"""
Persistence layer for the API service.

Two tables:
  - signals: every fresh Signal the scanner has found, plus its chart PNG
    (stored inline as base64 so we don't need a separate file volume/CDN).
  - config_blob: a single JSON row holding the user's runtime config
    overrides (indices/intervals/detectors/poll_seconds/...), so edits made
    from the dashboard survive a redeploy even though config.yaml itself is
    just the shipped default.

DATABASE_URL controls where this lives:
  - unset -> local SQLite file at backend/data/niftyscout.db (fine for a
    single Railway instance with a volume, or local dev)
  - postgres://... -> Railway's Postgres plugin (recommended for
    production: survives redeploys with zero extra config)
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

DEFAULT_SQLITE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "niftyscout.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.abspath(DEFAULT_SQLITE_PATH)}")

# Railway (and Heroku-style) Postgres URLs sometimes use the legacy
# "postgres://" scheme, which SQLAlchemy's psycopg2 dialect rejects.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    os.makedirs(os.path.dirname(os.path.abspath(DEFAULT_SQLITE_PATH)), exist_ok=True)
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


class SignalRow(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    index_key: Mapped[str] = mapped_column(String(32), index=True)
    interval: Mapped[str] = mapped_column(String(16))
    pattern: Mapped[str] = mapped_column(String(64))
    direction: Mapped[str] = mapped_column(String(16))
    breakout_price: Mapped[float] = mapped_column(Float)
    level: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    note: Mapped[str] = mapped_column(Text)
    chart_base64: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc)
    )


class ConfigBlob(Base):
    __tablename__ = "config_blob"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc),
        onupdate=lambda: dt.datetime.now(dt.timezone.utc),
    )


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)


def get_config_override() -> Optional[dict]:
    with get_session() as session:
        row = session.get(ConfigBlob, "runtime")
        return row.value if row else None


def save_config_override(value: dict) -> None:
    with get_session() as session:
        row = session.get(ConfigBlob, "runtime")
        if row is None:
            row = ConfigBlob(key="runtime", value=value)
            session.add(row)
        else:
            row.value = value
        session.commit()


def insert_signal(row: SignalRow) -> SignalRow:
    with get_session() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def list_signals(
    limit: int = 100,
    index_key: Optional[str] = None,
    pattern: Optional[str] = None,
) -> list[SignalRow]:
    with get_session() as session:
        stmt = select(SignalRow).order_by(SignalRow.timestamp.desc()).limit(limit)
        if index_key:
            stmt = stmt.where(SignalRow.index_key == index_key)
        if pattern:
            stmt = stmt.where(SignalRow.pattern == pattern)
        return list(session.scalars(stmt))
