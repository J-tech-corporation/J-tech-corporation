"""Tests for session lifecycle and refresh-token rotation."""

from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Base, RefreshToken, User, UserSession
from app.services.session_service import SessionError, SessionService
from app.services.token_service import TokenService


@pytest.fixture
def session_context():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()


def make_service(session: Session) -> SessionService:
    private = Ed25519PrivateKey.generate()
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    settings = Settings(
        _env_file=None,
        jwt_private_key=SecretStr(private_pem),
        jwt_public_key=SecretStr(public_pem),
    )
    return SessionService(session, TokenService(settings))


def make_user(session: Session) -> User:
    user = User(
        email="ceo@example.test",
        full_name="CEO",
        password_hash="argon2id-test-hash",
    )
    session.add(user)
    session.flush()
    return user


def test_create_session_persists_only_refresh_hash(session_context: Session) -> None:
    service = make_service(session_context)
    user = make_user(session_context)
    user_session, access, raw_refresh = service.create_session(
        user, device_name="CEO Desktop", ip_address="127.0.0.1"
    )

    stored = session_context.scalar(select(RefreshToken))
    assert user_session.user_id == user.id
    assert access
    assert stored is not None
    assert stored.token_hash != raw_refresh
    assert stored.token_hash == service.token_service.hash_refresh_token(raw_refresh)


def test_refresh_rotation_consumes_old_token_and_issues_new_pair(
    session_context: Session,
) -> None:
    service = make_service(session_context)
    user = make_user(session_context)
    _, _, original = service.create_session(user)

    user_session, access, replacement = service.rotate_refresh_token(original)

    assert access
    assert replacement != original
    old_record = session_context.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == service.token_service.hash_refresh_token(original)
        )
    )
    assert old_record is not None and old_record.used_at is not None
    assert user_session.last_active_at is not None


def test_refresh_token_reuse_revokes_entire_session(session_context: Session) -> None:
    service = make_service(session_context)
    user = make_user(session_context)
    user_session, _, original = service.create_session(user)
    service.rotate_refresh_token(original)

    with pytest.raises(SessionError, match="reuse detected"):
        service.rotate_refresh_token(original)

    session_context.refresh(user_session)
    assert user_session.revoked_at is not None
    assert all(token.revoked_at is not None for token in user_session.refresh_tokens)


def test_revoke_session_is_scoped_to_owner(session_context: Session) -> None:
    service = make_service(session_context)
    user = make_user(session_context)
    other = User(
        email="other@example.test", full_name="Other", password_hash="argon2id-test-hash"
    )
    session_context.add(other)
    session_context.flush()
    user_session, _, _ = service.create_session(user)

    assert not service.revoke_session(user_session.id, user_id=other.id)
    assert service.revoke_session(user_session.id, user_id=user.id)
    session_context.refresh(user_session)
    assert user_session.revoked_at is not None


def test_revoke_all_sessions_revokes_refresh_tokens(session_context: Session) -> None:
    service = make_service(session_context)
    user = make_user(session_context)
    first, _, _ = service.create_session(user, device_name="Desktop")
    second, _, _ = service.create_session(user, device_name="Mobile")

    assert service.revoke_all_sessions(user.id) == 2
    session_context.refresh(first)
    session_context.refresh(second)
    assert first.revoked_at is not None and second.revoked_at is not None
    assert all(
        token.revoked_at is not None
        for item in (first, second)
        for token in item.refresh_tokens
    )


def test_expired_refresh_token_is_rejected(session_context: Session) -> None:
    service = make_service(session_context)
    user = make_user(session_context)
    now = datetime.now(UTC)
    _, _, raw = service.create_session(user, now=now - timedelta(days=8))

    with pytest.raises(SessionError, match="Invalid refresh token"):
        service.rotate_refresh_token(raw, now=now)
