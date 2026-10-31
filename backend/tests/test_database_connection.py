"""Optional integration test for a real PostgreSQL connection."""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def test_postgresql_connection() -> None:
    """Connect to the explicitly supplied test database and execute SELECT 1."""
    database_url = os.getenv("ATECH_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set ATECH_TEST_DATABASE_URL to run the PostgreSQL integration test.")

    parsed_url = make_url(database_url)
    if parsed_url.get_backend_name() != "postgresql":
        pytest.fail("ATECH_TEST_DATABASE_URL must use a PostgreSQL URL.")

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()
