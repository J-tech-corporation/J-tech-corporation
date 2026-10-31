"""Password hashing primitives. Authentication flows are added in P1-04."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id defaults."""
    if not password:
        raise ValueError("Password must not be empty")
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether a plaintext password matches its stored hash."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False
