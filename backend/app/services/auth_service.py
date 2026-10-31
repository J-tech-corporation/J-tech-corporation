"""Authentication business logic independent of HTTP endpoints."""

from app.core.security import hash_password, password_needs_rehash, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthenticationError(Exception):
    """Raised when credentials are invalid or the account cannot sign in."""


class AuthenticationService:
    """Verify credentials and maintain password hashes for authenticated users."""

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    def authenticate(self, *, email: str, password: str) -> User:
        """Authenticate a user or raise a generic error without account disclosure."""
        user = self.user_repository.get_by_email(email)
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            self.user_repository.session.flush()

        return user
