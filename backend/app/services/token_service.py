"""JWT access-token and opaque refresh-token primitives."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.core.config import Settings, get_settings


class TokenConfigurationError(RuntimeError):
    """Raised when Ed25519 signing keys are not configured."""


class InvalidAccessTokenError(ValueError):
    """Raised when an access token is invalid or expired."""


class TokenService:
    """Issue EdDSA JWT access tokens and hash opaque refresh tokens."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _keys(self) -> tuple[str, str]:
        private_key = self.settings.jwt_private_key.get_secret_value()
        public_key = self.settings.jwt_public_key.get_secret_value()
        if not private_key or not public_key:
            raise TokenConfigurationError("JWT Ed25519 keys are not configured")
        return private_key, public_key

    def create_access_token(self, *, user_id: UUID, session_id: UUID) -> str:
        """Create a short-lived JWT; the private key is never returned or logged."""
        private_key, _ = self._keys()
        now = datetime.now(UTC)
        expires = now + timedelta(minutes=self.settings.access_token_minutes)
        return jwt.encode(
            {
                "sub": str(user_id),
                "sid": str(session_id),
                "iat": now,
                "exp": expires,
                "jti": secrets.token_urlsafe(16),
            },
            private_key,
            algorithm="EdDSA",
            headers={"kid": self.settings.jwt_key_id, "typ": "JWT"},
        )

    def decode_access_token(self, token: str) -> dict[str, object]:
        """Verify EdDSA signature and required claims using the public key only."""
        _, public_key = self._keys()
        try:
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["EdDSA"],
                options={"require": ["sub", "sid", "iat", "exp", "jti"]},
            )
            UUID(str(claims["sub"]))
            UUID(str(claims["sid"]))
            return claims
        except (jwt.InvalidTokenError, ValueError, KeyError) as exc:
            raise InvalidAccessTokenError("Invalid or expired access token") from exc

    def create_refresh_token(self) -> str:
        """Generate a high-entropy opaque token; persist only its SHA-256 hash."""
        return secrets.token_urlsafe(48)

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        """Return a one-way digest suitable for database lookup."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def refresh_expiry(self, *, now: datetime | None = None) -> datetime:
        """Return the configured absolute refresh-token expiry timestamp."""
        current = now or datetime.now(UTC)
        return current + timedelta(days=self.settings.refresh_token_days)
