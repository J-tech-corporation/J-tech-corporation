"""Policy approval request model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.policy import Policy
    from app.models.policy_approval_review import PolicyApprovalReview


class PolicyApprovalRequest(Base):
    """A request to approve one immutable policy version snapshot."""

    __tablename__ = "policy_approval_requests"
    __table_args__ = (
        Index("ix_policy_approval_requests_policy_status", "policy_id", "status"),
        Index("ix_policy_approval_requests_submitted_at", "submitted_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    policy_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("policies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING_APPROVAL", nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    policy: Mapped["Policy"] = relationship()
    reviews: Mapped[list["PolicyApprovalReview"]] = relationship(
        back_populates="approval_request", cascade="all, delete-orphan"
    )
