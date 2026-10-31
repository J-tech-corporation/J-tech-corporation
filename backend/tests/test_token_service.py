"""Tests for Ed25519 access tokens and opaque refresh-token primitives."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import SecretStr

from app.core.config import Settings
from app.services.token_service import (
    InvalidAccessTokenError,
    TokenConfigurationError,
    TokenService,
)


@pytest.fixture
def token_service() -> TokenService:
    private = Ed25519PrivateKey.generate()
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    settings = Settings(
        _env_file=None,
        jwt_private_key=SecretStr(private_pem),
        jwt_public_key=SecretStr(public_pem),
        jwt_key_id="test-key-1",
    )
    return TokenService(settings)


def test_access_token_round_trip_and_required_claims(token_service: TokenService) -> None:
    user_id, session_id = uuid4(), uuid4()
    token = token_service.create_access_token(user_id=user_id, session_id=session_id)
    claims = token_service.decode_access_token(token)

    assert claims["sub"] == str(user_id)
    assert claims["sid"] == str(session_id)
    assert jwt.get_unverified_header(token)["kid"] == "test-key-1"


def test_access_token_rejects_tampering(token_service: TokenService) -> None:
    token = token_service.create_access_token(user_id=uuid4(), session_id=uuid4())
    with pytest.raises(InvalidAccessTokenError):
        token_service.decode_access_token(token + "tampered")


def test_access_token_requires_configured_keys() -> None:
    service = TokenService(Settings(_env_file=None))
    with pytest.raises(TokenConfigurationError):
        service.create_access_token(user_id=uuid4(), session_id=uuid4())


def test_refresh_token_is_random_and_stored_as_hash(token_service: TokenService) -> None:
    first = token_service.create_refresh_token()
    second = token_service.create_refresh_token()

    assert first != second
    assert len(token_service.hash_refresh_token(first)) == 64
    assert token_service.hash_refresh_token(first) != first


def test_refresh_expiry_uses_configured_seven_days(token_service: TokenService) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert token_service.refresh_expiry(now=now) == now + timedelta(days=7)
