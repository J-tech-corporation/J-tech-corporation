"""Tests for authentication request and response schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    BootstrapRequest,
    LoginRequest,
    MFAVerificationRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    TokenResponse,
)


def test_bootstrap_request_normalizes_email_and_name() -> None:
    request = BootstrapRequest(
        bootstrap_secret="one-time-secret",
        email=" CEO@Example.COM ",
        full_name=" CEO ",
        password="a sufficiently long password",
    )
    assert request.email == "ceo@example.com"
    assert request.full_name == "CEO"


def test_bootstrap_request_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        BootstrapRequest(
            bootstrap_secret="secret",
            email="ceo@example.com",
            full_name="CEO",
            password="short",
        )


def test_login_request_normalizes_email() -> None:
    request = LoginRequest(email=" User@Example.com ", password="legacy-password")
    assert request.email == "user@example.com"


def test_schemas_reject_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(email="user@example.com", password="password", role="CEO")


def test_mfa_request_accepts_totp_or_recovery_code() -> None:
    request = MFAVerificationRequest(challenge_id="challenge-123", code="123456")
    recovery = MFAVerificationRequest(challenge_id="challenge-123", code="ABCD-EFGH-IJKL")
    assert request.code == "123456"
    assert recovery.code == "ABCD-EFGH-IJKL"


def test_password_reset_requires_long_new_password() -> None:
    with pytest.raises(ValidationError):
        PasswordResetRequest(token="t" * 32, new_password="too-short")


def test_password_change_hides_secrets_in_repr() -> None:
    request = PasswordChangeRequest(
        current_password="old-password",
        new_password="new password with enough length",
    )
    assert "old-password" not in repr(request)
    assert "new password with enough length" not in repr(request)


def test_token_response_has_bearer_defaults() -> None:
    response = TokenResponse(access_token="header.payload.signature", expires_in=900)
    assert response.token_type == "Bearer"
    assert response.expires_in == 900
