"""SQLAlchemy engine and session helpers.

No database connection is opened at import time. Local and Cloud URLs are
selected explicitly through Settings and are never synchronized.
"""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


def create_database_engine(settings: Settings | None = None) -> Engine:
    """Create an engine for the explicitly selected Local or Cloud database."""
    active_settings = settings or get_settings()
    return create_engine(
        active_settings.get_database_url(),
        pool_pre_ping=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to the supplied engine."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped session and always close it afterward."""
    engine = create_database_engine()
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        yield session
