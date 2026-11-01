"""Association model connecting roles and permissions."""

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RolePermission(Base):
    """Grant one permission to one role without duplicate assignments."""

    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    role_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("permissions.id", ondelete="RESTRICT"), nullable=False
    )

    role: Mapped["Role"] = relationship(back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship(back_populates="role_permissions")


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.permission import Permission
    from app.models.role import Role
