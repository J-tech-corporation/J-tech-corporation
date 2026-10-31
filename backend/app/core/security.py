"""Argon2id password hashing primitives."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 1024

def create_password_hasher(*, time_cost: int = 3, memory_cost: int = 65536, parallelism: int = 4) -> PasswordHasher:
    """Create a configurable Argon2id hasher for deployment benchmarking."""
    if time_cost < 1 or memory_cost < 8 or parallelism < 1:
        raise ValueError("Invalid Argon2id parameters")
    return PasswordHasher(time_cost=time_cost, memory_cost=memory_cost, parallelism=parallelism, hash_len=32, salt_len=16)

_password_hasher = create_password_hasher()

def validate_new_password(password: str) -> None:
    """Enforce the new-password length policy."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError("Password must be at least 12 characters")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError("Password must not exceed 1024 characters")

def hash_password(password: str) -> str:
    """Hash a non-empty password using Argon2id."""
    if not password:
        raise ValueError("Password must not be empty")
    return _password_hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its stored Argon2 hash."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False

def password_needs_rehash(password_hash: str) -> bool:
    """Check whether a hash should be upgraded to current parameters."""
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, VerificationError):
        return True
