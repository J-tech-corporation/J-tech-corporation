"""SQLAlchemy model package.

Import model modules here as they are introduced so Alembic can discover
their tables through Base.metadata.
"""

from app.models.base import Base

__all__ = ["Base"]
