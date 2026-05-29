"""
SQLAlchemy setup.
DATABASE_URL из .env:
  - postgresql://user:pass@host/db  → PostgreSQL (prod)
  - sqlite:///./perinatal.db        → SQLite (dev/CI)
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ── URL ───────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./perinatal.db")

# Для SQLite: убираем asyncpg-префикс если вдруг передан
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

# WAL-mode для SQLite (конкурентные чтения)
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_wal(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA journal_mode=WAL")
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — sync DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Создание таблиц (вызывается при старте приложения)."""
    from app import models_db  # noqa: F401 — регистрация моделей
    Base.metadata.create_all(bind=engine)
