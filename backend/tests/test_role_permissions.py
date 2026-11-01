"""Tests for role-permission associations and constraints."""

from uuid import UUID

import pytest
from sqlalchemy import Uuid, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Base, Permission, Role, RolePermission


def test_role_permission_table_is_registered_with_uuid_primary_key() -> None:
    table = Base.metadata.tables["role_permissions"]
    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.primary_key


def test_role_permission_relationships_work_with_sqlite() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            role = Role(name="QA", description="Quality assurance")
            permission = Permission(code="tasks:approve", description="Approve task submissions")
            assignment = RolePermission(role=role, permission=permission)

            session.add(assignment)
            session.commit()

            assert isinstance(assignment.id, UUID)
            assert role.role_permissions[0].permission.code == "tasks:approve"
            assert permission.role_permissions[0].role.name == "QA"
    finally:
        engine.dispose()


def test_duplicate_role_permission_assignment_is_rejected() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            role = Role(name="Mentor")
            permission = Permission(code="tasks:review")
            session.add_all([role, permission])
            session.flush()

            session.add_all(
                [
                    RolePermission(role_id=role.id, permission_id=permission.id),
                    RolePermission(role_id=role.id, permission_id=permission.id),
                ]
            )
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()


def test_role_permission_restricts_permission_deletion() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            role = Role(name="Frontend")
            permission = Permission(code="projects:read")
            session.add(RolePermission(role=role, permission=permission))
            session.commit()

            session.delete(permission)
            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()
