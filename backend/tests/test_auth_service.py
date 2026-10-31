"""Tests for authentication business logic."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Base
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthenticationError, AuthenticationService


@pytest.fixture
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()


def create_auth_service(session: Session) -> tuple[AuthenticationService, UserRepository]:
    repository = UserRepository(session)
    return AuthenticationService(repository), repository


def test_authenticate_returns_user_for_valid_credentials(session: Session) -> None:
    service, repository = create_auth_service(session)
    user = repository.create_user(
        email="ceo@example.test",
        full_name="CEO",
        password_hash=hash_password("correct horse battery staple"),
    )

    authenticated_user = service.authenticate(
        email="CEO@example.test", password="correct horse battery staple"
    )
    assert authenticated_user is user


def test_authenticate_uses_same_error_for_unknown_user_and_wrong_password(session: Session) -> None:
    service, repository = create_auth_service(session)
    repository.create_user(
        email="ceo@example.test",
        full_name="CEO",
        password_hash=hash_password("correct horse battery staple"),
    )

    with pytest.raises(AuthenticationError) as unknown_user:
        service.authenticate(email="missing@example.test", password="wrong password")
    with pytest.raises(AuthenticationError) as wrong_password:
        service.authenticate(email="ceo@example.test", password="wrong password")

    assert str(unknown_user.value) == str(wrong_password.value)


def test_authenticate_rejects_inactive_user(session: Session) -> None:
    service, repository = create_auth_service(session)
    repository.create_user(
        email="inactive@example.test",
        full_name="Inactive",
        password_hash=hash_password("correct horse battery staple"),
    )
    user = repository.get_by_email("inactive@example.test")
    assert user is not None
    user.is_active = False

    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        service.authenticate(email="inactive@example.test", password="correct horse battery staple")


def test_authenticate_rehashes_valid_password_when_needed(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, repository = create_auth_service(session)
    user = repository.create_user(
        email="ceo@example.test",
        full_name="CEO",
        password_hash=hash_password("correct horse battery staple"),
    )
    original_hash = user.password_hash
    monkeypatch.setattr("app.services.auth_service.password_needs_rehash", lambda _: True)

    authenticated_user = service.authenticate(
        email="ceo@example.test", password="correct horse battery staple"
    )

    assert authenticated_user is user
    assert user.password_hash != original_hash
