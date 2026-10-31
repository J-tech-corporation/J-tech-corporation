"""Tests for database configuration and SQLAlchemy session helpers."""

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.core.database import create_database_engine, create_session_factory


def test_local_and_cloud_database_urls_are_selected_separately() -> None:
    settings = Settings(
        _env_file=None,
        database_environment="local",
        local_database_url="postgresql+psycopg://local-user:local-pass@localhost/local_db",
        cloud_database_url="postgresql+psycopg://cloud-user:cloud-pass@cloud.invalid/cloud_db",
    )

    assert make_url(settings.get_database_url()).database == "local_db"

    cloud_settings = settings.model_copy(update={"database_environment": "cloud"})
    assert make_url(cloud_settings.get_database_url()).database == "cloud_db"


def test_missing_selected_database_url_fails_closed() -> None:
    settings = Settings(_env_file=None, database_environment="cloud")

    with pytest.raises(ValueError, match="not configured for 'cloud'"):
        settings.get_database_url()


def test_engine_and_session_factory_work_with_isolated_sqlite() -> None:
    settings = Settings(
        _env_file=None,
        database_environment="local",
        local_database_url="sqlite+pysqlite:///:memory:",
    )
    engine = create_database_engine(settings)

    try:
        session_factory = create_session_factory(engine)
        with session_factory() as session:
            assert session.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()
