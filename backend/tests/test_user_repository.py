"""Tests for the user repository using isolated SQLite databases."""

from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base
from app.repositories.user_repository import DuplicateUserError, UserRepository


@pytest.fixture
 def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()


def test_create_user_normalizes_email_and_persists_fields(session: Session) -> None:
    repository = UserRepository(session)

    user = repository.create_user(
        email="  CEO@Example.Test ",
        full_name="  A-TECH CEO  ",
        password_hash="argon2id-test-hash",
    )

    assert isinstance(user.id, UUID)
    assert user.email == "ceo@example.test"
    assert user.full_name == "A-TECH CEO"
    assert repository.get_by_id(user.id) is user
    assert repository.get_by_email("CEO@example.test") is user
    assert repository.email_exists(" ceo@example.test ")


def test_create_user_rejects_duplicate_email(session: Session) -> None:
    repository = UserRepository(session)
    repository.create_user(
        email="ceo@example.test",
        full_name="CEO",
        password_hash="argon2id-test-hash",
    )

    with pytest.raises(DuplicateUserError):
        repository.create_user(
            email=" CEO@EXAMPLE.TEST ",
            full_name="Another CEO",
            password_hash="another-hash",
        )


def test_get_by_id_returns_none_for_unknown_user(session: Session) -> None:
    assert UserRepository(session).get_by_id(UUID("00000000-0000-0000-0000-000000000001")) is None
