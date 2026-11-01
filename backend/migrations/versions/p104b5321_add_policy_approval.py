"""Add policy approval request and review tables.

Revision ID: p104b5321
Revises: p104b5231
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "p104b5321"
down_revision: str | None = "p104b5231"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_approval_requests",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("policy_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["policy_id"], ["policies.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_policy_approval_requests_policy_id",
        "policy_approval_requests",
        ["policy_id"],
        unique=False,
    )
    op.create_index(
        "ix_policy_approval_requests_status",
        "policy_approval_requests",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_policy_approval_requests_policy_status",
        "policy_approval_requests",
        ["policy_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_policy_approval_requests_submitted_at",
        "policy_approval_requests",
        ["submitted_at"],
        unique=False,
    )

    op.create_table(
        "policy_approval_reviews",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("approval_request_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", sa.String(length=128), nullable=False),
        sa.Column("review_type", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("comments", sa.String(length=2000), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["approval_request_id"],
            ["policy_approval_requests.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "approval_request_id",
            "reviewer_id",
            "review_type",
            name="uq_policy_approval_reviews_request_reviewer_type",
        ),
    )
    op.create_index(
        "ix_policy_approval_reviews_approval_request_id",
        "policy_approval_reviews",
        ["approval_request_id"],
        unique=False,
    )
    op.create_index(
        "ix_policy_approval_reviews_reviewer_id",
        "policy_approval_reviews",
        ["reviewer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_policy_approval_reviews_reviewer_id", table_name="policy_approval_reviews")
    op.drop_index(
        "ix_policy_approval_reviews_approval_request_id",
        table_name="policy_approval_reviews",
    )
    op.drop_table("policy_approval_reviews")
    op.drop_index("ix_policy_approval_requests_submitted_at", table_name="policy_approval_requests")
    op.drop_index(
        "ix_policy_approval_requests_policy_status",
        table_name="policy_approval_requests",
    )
    op.drop_index("ix_policy_approval_requests_status", table_name="policy_approval_requests")
    op.drop_index("ix_policy_approval_requests_policy_id", table_name="policy_approval_requests")
    op.drop_table("policy_approval_requests")
