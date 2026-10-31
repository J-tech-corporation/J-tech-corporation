"""Issue, validate, list, and revoke trusted-device tokens."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.trusted_device import TrustedDevice


class TrustedDeviceService:
    """Store only device-token hashes and enforce 7/30/90-day expiry."""

    ALLOWED_DURATIONS = {7, 30, 90}

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_device(
        self, user_id: UUID, *, device_name: str | None = None,
        duration_days: int = 30, now: datetime | None = None,
    ) -> tuple[TrustedDevice, str]:
        """Create a trusted device after the caller has successfully verified MFA."""
        if duration_days not in self.ALLOWED_DURATIONS:
            raise ValueError("Trusted device duration must be 7, 30, or 90 days")
        current = now or datetime.now(UTC)
        raw_token = secrets.token_urlsafe(48)
        device = TrustedDevice(
            user_id=user_id,
            token_hash=self._hash(raw_token),
            device_name=device_name,
            created_at=current,
            expires_at=current + timedelta(days=duration_days),
        )
        self.session.add(device)
        self.session.flush()
        return device, raw_token

    def validate_device(
        self, user_id: UUID, raw_token: str, *, now: datetime | None = None
    ) -> bool:
        """Validate ownership, revocation, and expiry of a presented device token."""
        current = now or datetime.now(UTC)
        device = self.session.scalar(
            select(TrustedDevice).where(
                TrustedDevice.user_id == user_id,
                TrustedDevice.token_hash == self._hash(raw_token),
            )
        )
        if (
            device is None
            or device.revoked_at is not None
            or self._is_expired(device.expires_at, current)
        ):
            return False
        device.last_used_at = current
        self.session.flush()
        return True

    def list_devices(self, user_id: UUID) -> list[TrustedDevice]:
        """List all trusted devices for a user, including revoked devices."""
        return list(
            self.session.scalars(
                select(TrustedDevice)
                .where(TrustedDevice.user_id == user_id)
                .order_by(TrustedDevice.created_at.desc())
            )
        )

    def revoke_device(
        self, user_id: UUID, device_id: UUID, *, now: datetime | None = None
    ) -> bool:
        """Revoke one trusted device only when it belongs to the requesting user."""
        device = self.session.scalar(
            select(TrustedDevice).where(
                TrustedDevice.id == device_id, TrustedDevice.user_id == user_id
            ).with_for_update()
        )
        if device is None:
            return False
        if device.revoked_at is None:
            device.revoked_at = now or datetime.now(UTC)
            self.session.flush()
        return True

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_expired(expires_at: datetime, now: datetime) -> bool:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= now
