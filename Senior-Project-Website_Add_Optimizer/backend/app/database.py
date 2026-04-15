"""Database configuration for synchronous SQLAlchemy sessions."""

import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def _build_database_url() -> str:
    """Build and normalize the database URL from environment variables."""
    raw_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/optimizer_db",
    )
    if "asyncpg" in raw_url:
        return raw_url.replace("asyncpg", "psycopg2", 1)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return raw_url


DATABASE_URL = _build_database_url()
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session for each request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
