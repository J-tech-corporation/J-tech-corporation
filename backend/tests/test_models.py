"""Tests for identity model metadata, relationships, and constraints."""

from uuid import UUID

import pytest
from datetime import UTC, datetime
from sqlalchemy import Uuid, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Base, Permission, RefreshToken, Role, User, UserRole, UserSession


def test_identity_tables_are_registered_with_uuid_primary_keys() -> None:
    expected_tables = {
        "users", "roles", "permissions", "user_roles", "user_sessions", "refresh_tokens"
    }

    assert expected_tables.issubset(Base.metadata.tables)
    for table_name in expected_tables:
        id_column = Base.metadata.tables[table_name].c.id
        assert isinstance(id_column.type, Uuid)
        assert id_column.primary_key


def test_user_role_relationships_work_with_isolated_sqlite() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            user = User(
                email="ceo@example.test",
                full_name="A-TECH CEO",
                password_hash="argon2id-placeholder-hash",
            )
            role = Role(name="CEO", description="Chief executive")
            permission = Permission(code="system.approve", description="Approve proposals")
            assignment = UserRole(user=user, role=role)

            session.add_all([user, role, permission, assignment])
            session.commit()

            assert isinstance(user.id, UUID)
            assert user.user_roles[0].role.name == "CEO"
            assert role.user_roles[0].user.email == "ceo@example.test"
            assert permission.code == "system.approve"
    finally:
        engine.dispose()


def test_duplicate_user_role_assignment_is_rejected() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            user = User(
                email="agent@example.test",
                full_name="Agent",
                password_hash="argon2id-placeholder-hash",
            )
            role = Role(name="Agent")
            session.add_all([user, role])
            session.flush()

            session.add_all(
                [
                    UserRole(user_id=user.id, role_id=role.id),
                    UserRole(user_id=user.id, role_id=role.id),
                ]
            )
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()


def test_role_name_and_permission_code_are_unique() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            session.add_all([Role(name="CEO"), Role(name="CEO")])
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            session.add_all(
                [
                    Permission(code="system.approve"),
                    Permission(code="system.approve"),
                ]
            )
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()


def test_user_session_and_refresh_token_relationships_work_with_sqlite() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            user = User(
                email="session@example.test",
                full_name="Session User",
                password_hash="argon2id-placeholder-hash",
            )
            user_session = UserSession(
                user=user,
                expires_at=datetime.now(UTC),
            )
            refresh_token = RefreshToken(
                session=user_session,
                token_hash="a" * 64,
                expires_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            )
            session.add(user)
            session.commit()

            assert user.sessions[0].id == user_session.id
            assert user_session.refresh_tokens[0].token_hash == refresh_token.token_hash
    finally:
        engine.dispose()
