"""Tests for Argon2id password security primitives."""

import pytest

from app.core.security import (
    create_password_hasher,
    hash_password,
    password_needs_rehash,
    validate_new_password,
    verify_password,
)


def test_hash_password_uses_argon2id_and_verifies() -> None:
    password = "correct horse battery staple"
    password_hash = hash_password(password)
    assert password_hash.startswith("$argon2id$")
    assert verify_password(password, password_hash)
    assert not verify_password("incorrect password", password_hash)


def test_hash_password_rejects_empty_password() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        hash_password("")


@pytest.mark.parametrize("password", ["short", ""])
def test_validate_new_password_rejects_short_password(password: str) -> None:
    with pytest.raises(ValueError, match="at least 12"):
        validate_new_password(password)


def test_validate_new_password_accepts_long_passphrase() -> None:
    validate_new_password("this is a sufficiently long passphrase")


def test_validate_new_password_rejects_excessive_length() -> None:
    with pytest.raises(ValueError, match="must not exceed"):
        validate_new_password("a" * 1025)


def test_hasher_parameters_are_configurable() -> None:
    hasher = create_password_hasher(time_cost=2, memory_cost=19456, parallelism=1)
    password_hash = hasher.hash("benchmark password")
    assert hasher.verify(password_hash, "benchmark password")


def test_hasher_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError, match="parameters"):
        create_password_hasher(time_cost=0)


def test_password_needs_rehash_detects_parameter_change() -> None:
    low_cost_hasher = create_password_hasher(time_cost=1, memory_cost=8192, parallelism=1)
    password_hash = low_cost_hasher.hash("migration test password")
    assert password_needs_rehash(password_hash)


def test_password_needs_rehash_handles_invalid_hash() -> None:
    assert password_needs_rehash("not-an-argon2-hash")
