"""Tests for trusted-device token lifecycle and ownership."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base, User
from app.services.trusted_device_service import TrustedDeviceService


@pytest.fixture
def device_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def make_user(session: Session, email: str) -> User:
    user = User(email=email, full_name="Test User", password_hash="argon2id-placeholder")
    session.add(user)
    session.flush()
    return user


def test_create_and_validate_trusted_device(device_session: Session) -> None:
    user = make_user(device_session, "device@example.test")
    service = TrustedDeviceService(device_session)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    device, raw_token = service.create_device(
        user.id, device_name="Desktop", duration_days=30, now=now
    )

    assert raw_token not in device.token_hash
    assert device.expires_at == now + timedelta(days=30)
    assert service.validate_device(user.id, raw_token, now=now + timedelta(days=1))


def test_rejects_invalid_duration(device_session: Session) -> None:
    user = make_user(device_session, "invalid-duration@example.test")
    service = TrustedDeviceService(device_session)

    with pytest.raises(ValueError, match="7, 30, or 90"):
        service.create_device(user.id, duration_days=14)


def test_expired_and_revoked_devices_are_rejected(device_session: Session) -> None:
    user = make_user(device_session, "expired@example.test")
    service = TrustedDeviceService(device_session)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    device, token = service.create_device(user.id, duration_days=7, now=now)

    assert not service.validate_device(user.id, token, now=now + timedelta(days=8))
    assert service.revoke_device(user.id, device.id, now=now + timedelta(days=1))
    assert not service.validate_device(user.id, token, now=now + timedelta(days=2))


def test_revoke_is_scoped_to_owner(device_session: Session) -> None:
    user = make_user(device_session, "owner@example.test")
    other = make_user(device_session, "other@example.test")
    service = TrustedDeviceService(device_session)
    device, _ = service.create_device(user.id)

    assert not service.revoke_device(other.id, device.id)
    assert service.revoke_device(user.id, device.id)


def test_list_devices_returns_only_users_devices(device_session: Session) -> None:
    user = make_user(device_session, "list@example.test")
    other = make_user(device_session, "list-other@example.test")
    service = TrustedDeviceService(device_session)
    service.create_device(user.id, device_name="Laptop")
    service.create_device(other.id, device_name="Phone")

    devices = service.list_devices(user.id)
    assert len(devices) == 1
    assert devices[0].device_name == "Laptop"
