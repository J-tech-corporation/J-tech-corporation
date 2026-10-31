"""Tests for encrypted TOTP setup and one-time recovery codes."""

from datetime import UTC, datetime

import pyotp
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Base, MFARecoveryCode, User, UserMFAMethod
from app.services.mfa_service import MFAConfigurationError, MFAError, MFAService


@pytest.fixture
def mfa_context():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    settings = Settings(
        _env_file=None,
        mfa_encryption_key=Fernet.generate_key().decode("ascii"),
    )
    with Session(engine) as session:
        yield session, settings
    engine.dispose()


def make_user(session: Session) -> User:
    user = User(
        email="mfa@example.test", full_name="MFA User", password_hash="argon2id-placeholder"
    )
    session.add(user)
    session.flush()
    return user


def test_totp_setup_encrypts_secret_and_confirmation_enables_method(mfa_context) -> None:
    session, settings = mfa_context
    user = make_user(session)
    service = MFAService(session, settings)
    method, secret, uri = service.begin_totp_setup(user)

    assert secret not in method.encrypted_secret
    assert uri.startswith("otpauth://totp/")
    assert not method.is_enabled
    codes = service.confirm_totp_setup(
        user.id, method.id, pyotp.TOTP(secret).now()
    )

    assert method.is_enabled
    assert len(codes) == 10
    assert service.verify_totp(user.id, pyotp.TOTP(secret).now())


def test_totp_rejects_invalid_code(mfa_context) -> None:
    session, settings = mfa_context
    user = make_user(session)
    service = MFAService(session, settings)
    method, _, _ = service.begin_totp_setup(user)

    with pytest.raises(MFAError, match="Invalid or expired"):
        service.confirm_totp_setup(user.id, method.id, "000000")


def test_recovery_code_can_only_be_used_once(mfa_context) -> None:
    session, settings = mfa_context
    user = make_user(session)
    service = MFAService(session, settings)
    method, secret, _ = service.begin_totp_setup(user)
    codes = service.confirm_totp_setup(user.id, method.id, pyotp.TOTP(secret).now())

    assert service.verify_recovery_code(user.id, codes[0])
    assert not service.verify_recovery_code(user.id, codes[0])
    stored = session.scalar(
        select(MFARecoveryCode).where(MFARecoveryCode.mfa_method_id == method.id)
    )
    assert stored is not None
    assert codes[0] not in stored.code_hash
    assert stored.used_at is not None


def test_mfa_encryption_requires_valid_configured_key(mfa_context) -> None:
    session, _ = mfa_context
    user = make_user(session)
    service = MFAService(session, Settings(_env_file=None))

    with pytest.raises(MFAConfigurationError):
        service.begin_totp_setup(user)


def test_disable_totp_removes_method_and_recovery_codes(mfa_context) -> None:
    session, settings = mfa_context
    user = make_user(session)
    service = MFAService(session, settings)
    method, secret, _ = service.begin_totp_setup(user)
    service.confirm_totp_setup(user.id, method.id, pyotp.TOTP(secret).now())

    assert service.disable_totp(user.id, method.id)
    assert session.scalar(select(UserMFAMethod).where(UserMFAMethod.id == method.id)) is None
