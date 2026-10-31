"""Tests for the initial identity schema migration."""

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


BACKEND_DIR = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    BACKEND_DIR
    / "migrations"
    / "versions"
    / "p103b4a1c2d3_initial_identity.py"
)


def load_migration():
    spec = importlib.util.spec_from_file_location(
        "initial_identity_migration", MIGRATION_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_initial_identity_migration_upgrade_and_downgrade() -> None:
    migration = load_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()

        inspector = inspect(connection)
        assert set(inspector.get_table_names()) == {
            "roles",
            "permissions",
            "users",
            "user_roles",
        }
        assert {
            index["name"]
            for index in inspector.get_indexes("users")
        } == {"ix_users_email"}
        assert {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("user_roles")
        } == {"uq_user_roles_user_role"}
        assert len(inspector.get_foreign_keys("user_roles")) == 2

        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.downgrade()

        assert inspect(connection).get_table_names() == []

    engine.dispose()
