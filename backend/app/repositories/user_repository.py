"""Database access methods for user identity records."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class DuplicateUserError(ValueError):
    """Raised when attempting to create a user with an existing email."""


class UserRepository:
    """Encapsulate user queries and persistence using a caller-owned session."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_id: UUID) -> User | None:
        """Return a user by primary key, if present."""
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        """Return a user by normalized email address, if present."""
        normalized_email = email.strip().lower()
        statement = select(User).where(User.email == normalized_email)
        return self.session.scalar(statement)

    def email_exists(self, email: str) -> bool:
        """Check whether a normalized email address is already registered."""
        return self.get_by_email(email) is not None

    def create_user(self, *, email: str, full_name: str, password_hash: str) -> User:
        """Add a user and flush it without committing the caller's transaction."""
        normalized_email = email.strip().lower()
        if self.email_exists(normalized_email):
            raise DuplicateUserError("A user with this email already exists")

        user = User(
            email=normalized_email,
            full_name=full_name.strip(),
            password_hash=password_hash,
        )
        self.session.add(user)
        self.session.flush()
        return user
