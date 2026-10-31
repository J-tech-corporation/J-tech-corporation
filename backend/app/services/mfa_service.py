"""TOTP enrollment, verification, and one-time recovery-code handling."""

import hashlib
import secrets
from datetime import UTC, datetime
from uuid import UUID

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.models.mfa_recovery_code import MFARecoveryCode
from app.models.user import User
from app.models.user_mfa_method import UserMFAMethod


class MFAError(ValueError):
    """Raised for invalid MFA setup or verification operations."""


class MFAConfigurationError(RuntimeError):
    """Raised when the MFA encryption key is not configured correctly."""


class MFAService:
    """Manage encrypted TOTP secrets and hashed single-use recovery codes."""

    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    def _cipher(self) -> Fernet:
        key = self.settings.mfa_encryption_key.get_secret_value()
        try:
            return Fernet(key.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise MFAConfigurationError(
                "Set ATECH_MFA_ENCRYPTION_KEY to a valid Fernet key"
            ) from exc

    def begin_totp_setup(
        self, user: User, *, issuer: str = "A-TECH Corporation"
    ) -> tuple[UserMFAMethod, str, str]:
        """Create a pending TOTP method and return its secret and provisioning URI once."""
        if self.session.scalar(
            select(UserMFAMethod.id).where(
                UserMFAMethod.user_id == user.id,
                UserMFAMethod.method_type == "totp",
                UserMFAMethod.is_enabled.is_(True),
            )
        ):
            raise MFAError("An enabled TOTP method already exists")
        secret = pyotp.random_base32()
        method = UserMFAMethod(
            user=user,
            method_type="totp",
            encrypted_secret=self._cipher().encrypt(secret.encode()).decode("ascii"),
            is_enabled=False,
        )
        self.session.add(method)
        self.session.flush()
        uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=issuer)
        return method, secret, uri

    def confirm_totp_setup(
        self, user_id: UUID, method_id: UUID, code: str, *, now: datetime | None = None
    ) -> list[str]:
        """Verify initial TOTP, enable the method, and issue recovery codes once."""
        method = self._get_method(user_id, method_id)
        if method.is_enabled:
            raise MFAError("TOTP method is already enabled")
        secret = self._decrypt_secret(method.encrypted_secret)
        verified_at = now or datetime.now(UTC)
        if not pyotp.TOTP(secret).verify(
            code, for_time=verified_at.timestamp(), valid_window=1
        ):
            raise MFAError("Invalid or expired MFA code")
        method.is_enabled = True
        method.verified_at = verified_at
        codes = [secrets.token_hex(5).upper() for _ in range(10)]
        method.recovery_codes = [
            MFARecoveryCode(code_hash=self._hash_code(value)) for value in codes
        ]
        self.session.flush()
        return codes

    def verify_totp(
        self, user_id: UUID, code: str, *, now: datetime | None = None
    ) -> bool:
        """Verify a current TOTP code against the user's enabled method."""
        method = self.session.scalar(
            select(UserMFAMethod).where(
                UserMFAMethod.user_id == user_id,
                UserMFAMethod.method_type == "totp",
                UserMFAMethod.is_enabled.is_(True),
            )
        )
        if method is None:
            return False
        secret = self._decrypt_secret(method.encrypted_secret)
        return pyotp.TOTP(secret).verify(
            code, for_time=(now or datetime.now(UTC)).timestamp(), valid_window=1
        )

    def verify_recovery_code(
        self, user_id: UUID, code: str, *, now: datetime | None = None
    ) -> bool:
        """Consume a recovery code exactly once."""
        method = self.session.scalar(
            select(UserMFAMethod)
            .where(UserMFAMethod.user_id == user_id, UserMFAMethod.is_enabled.is_(True))
            .options(selectinload(UserMFAMethod.recovery_codes))
        )
        if method is None:
            return False
        digest = self._hash_code(code)
        record = self.session.scalar(
            select(MFARecoveryCode)
            .where(
                MFARecoveryCode.mfa_method_id == method.id,
                MFARecoveryCode.code_hash == digest,
                MFARecoveryCode.used_at.is_(None),
            )
            .with_for_update()
        )
        if record is None:
            return False
        record.used_at = now or datetime.now(UTC)
        self.session.flush()
        return True

    def disable_totp(self, user_id: UUID, method_id: UUID) -> bool:
        """Delete the selected MFA method and its recovery codes."""
        method = self.session.scalar(
            select(UserMFAMethod).where(
                UserMFAMethod.id == method_id, UserMFAMethod.user_id == user_id
            )
        )
        if method is None:
            return False
        self.session.delete(method)
        self.session.flush()
        return True

    def _get_method(self, user_id: UUID, method_id: UUID) -> UserMFAMethod:
        method = self.session.scalar(
            select(UserMFAMethod).where(
                UserMFAMethod.id == method_id, UserMFAMethod.user_id == user_id
            )
        )
        if method is None:
            raise MFAError("MFA method not found")
        return method

    def _decrypt_secret(self, encrypted_secret: str) -> str:
        try:
            return self._cipher().decrypt(encrypted_secret.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeEncodeError, ValueError) as exc:
            raise MFAConfigurationError("Unable to decrypt stored MFA secret") from exc

    @staticmethod
    def _hash_code(code: str) -> str:
        return hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()
