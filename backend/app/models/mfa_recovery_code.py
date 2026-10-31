"""Hashed, single-use MFA recovery codes."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user_mfa_method import UserMFAMethod


class MFARecoveryCode(Base):
    """Persist only a digest of each recovery code."""

    __tablename__ = "mfa_recovery_codes"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    mfa_method_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("user_mfa_methods.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    mfa_method: Mapped["UserMFAMethod"] = relationship(back_populates="recovery_codes")
