"""Convert policy versions to Semantic Versioning and add snapshot hashes.

Revision ID: p104b5231
Revises: p104b5221
"""

import hashlib
import json
from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "p104b5231"
down_revision: str | None = "p104b5221"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _snapshot_hash(row: sa.Row) -> str:
    snapshot = {
        "version": f"{row.version}.0.0",
        "name": row.name,
        "description": row.description,
        "policy_type": row.policy_type,
        "scope_type": row.scope_type,
        "scope_id": row.scope_id,
        "rules": row.rules,
        "change_reason": row.change_reason,
        "created_by": row.created_by,
    }
    canonical = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def upgrade() -> None:
    op.alter_column(
        "policies",
        "current_version",
        existing_type=sa.Integer(),
        type_=sa.String(length=32),
        postgresql_using="current_version::text",
    )
    op.execute(
        "UPDATE policies SET current_version = current_version || '.0.0'"
    )

    op.alter_column(
        "policy_versions",
        "version",
        existing_type=sa.Integer(),
        type_=sa.String(length=32),
        postgresql_using="version::text",
    )
    op.execute("UPDATE policy_versions SET version = version || '.0.0'")

    op.add_column(
        "policy_versions",
        sa.Column("snapshot_hash", sa.String(length=64), nullable=True),
    )
    bind = op.get_bind()
    versions = sa.table(
        "policy_versions",
        sa.column("id", sa.Uuid()),
        sa.column("version", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("policy_type", sa.String()),
        sa.column("scope_type", sa.String()),
        sa.column("scope_id", sa.String()),
        sa.column("rules", sa.JSON()),
        sa.column("change_reason", sa.String()),
        sa.column("created_by", sa.String()),
        sa.column("snapshot_hash", sa.String()),
    )
    rows = bind.execute(
        sa.select(
            versions.c.id,
            versions.c.version,
            versions.c.name,
            versions.c.description,
            versions.c.policy_type,
            versions.c.scope_type,
            versions.c.scope_id,
            versions.c.rules,
            versions.c.change_reason,
            versions.c.created_by,
        )
    ).mappings()
    for row in rows:
        snapshot = {
            "version": row["version"],
            "name": row["name"],
            "description": row["description"],
            "policy_type": row["policy_type"],
            "scope_type": row["scope_type"],
            "scope_id": row["scope_id"],
            "rules": row["rules"],
            "change_reason": row["change_reason"],
            "created_by": row["created_by"],
        }
        canonical = json.dumps(
            snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()
        bind.execute(
            versions.update()
            .where(versions.c.id == row["id"])
            .values(snapshot_hash=digest)
        )
    op.alter_column(
        "policy_versions",
        "snapshot_hash",
        existing_type=sa.String(length=64),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("policy_versions", "snapshot_hash")
    op.alter_column(
        "policy_versions",
        "version",
        existing_type=sa.String(length=32),
        type_=sa.Integer(),
        postgresql_using="split_part(version, '.', 1)::integer",
    )
    op.alter_column(
        "policies",
        "current_version",
        existing_type=sa.String(length=32),
        type_=sa.Integer(),
        postgresql_using="split_part(current_version, '.', 1)::integer",
    )
