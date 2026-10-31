"""Tests for Alembic configuration and model metadata discovery."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.models import Base


BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_alembic_configuration_loads_migration_script_directory() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    script_directory = ScriptDirectory.from_config(config)

    assert script_directory.dir == str(BACKEND_DIR / "migrations")
    assert (BACKEND_DIR / "migrations" / "env.py").is_file()


def test_alembic_target_metadata_is_available() -> None:
    expected_tables = {"users", "roles", "permissions", "user_roles"}

    assert Base.metadata is not None
    assert expected_tables.issubset(Base.metadata.tables)
