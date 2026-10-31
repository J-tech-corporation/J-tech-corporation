"""Encrypted MFA authenticator methods for a user."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.mfa_recovery_code import MFARecoveryCode
    from app.models.user import User


class UserMFAMethod(Base):
    """TOTP method; the authenticator secret is encrypted before persistence."""

    __tablename__ = "user_mfa_methods"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method_type: Mapped[str] = mapped_column(String(32), default="totp", nullable=False)
    encrypted_secret: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="mfa_methods")
    recovery_codes: Mapped[list["MFARecoveryCode"]] = relationship(
        back_populates="mfa_method", cascade="all, delete-orphan"
    )
