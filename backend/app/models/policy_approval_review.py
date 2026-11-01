"""Policy approval review model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.policy_approval_request import PolicyApprovalRequest


class PolicyApprovalReview(Base):
    """A review decision recorded against a policy approval request."""

    __tablename__ = "policy_approval_reviews"
    __table_args__ = (
        UniqueConstraint(
            "approval_request_id",
            "reviewer_id",
            "review_type",
            name="uq_policy_approval_reviews_request_reviewer_type",
        ),
        Index("ix_policy_approval_reviews_reviewer_id", "reviewer_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    approval_request_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("policy_approval_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    review_type: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    comments: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    approval_request: Mapped["PolicyApprovalRequest"] = relationship(back_populates="reviews")
