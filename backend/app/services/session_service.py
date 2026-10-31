"""Create, rotate, list, and revoke authenticated sessions."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.user_session import UserSession
from app.services.token_service import TokenService


class SessionError(Exception):
    """Raised when a session or refresh token is invalid."""


class SessionService:
    """Manage per-device sessions; callers own transaction commit/rollback.

    When reuse is detected, the caller must commit the transaction before
    returning the security error so the session revocation is persisted.
    """

    def __init__(
        self, session: Session, token_service: TokenService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or (token_service.settings if token_service else None)
        self.token_service = token_service or TokenService(settings)

    def create_session(
        self, user: User, *, device_name: str | None = None,
        user_agent: str | None = None, ip_address: str | None = None,
        now: datetime | None = None,
    ) -> tuple[UserSession, str, str]:
        """Create a device session and return (session, access JWT, raw refresh token)."""
        current = now or datetime.now(UTC)
        expires_at = self.token_service.refresh_expiry(now=current)
        user_session = UserSession(
            user=user,
            device_name=device_name,
            user_agent=user_agent,
            ip_address=ip_address,
            last_active_at=current,
            expires_at=expires_at,
        )
        self.session.add(user_session)
        self.session.flush()
        raw_refresh = self.token_service.create_refresh_token()
        self.session.add(
            RefreshToken(
                session=user_session,
                token_hash=self.token_service.hash_refresh_token(raw_refresh),
                expires_at=expires_at,
            )
        )
        self.session.flush()
        access_token = self.token_service.create_access_token(
            user_id=user.id, session_id=user_session.id
        )
        return user_session, access_token, raw_refresh

    def rotate_refresh_token(
        self, raw_token: str, *, now: datetime | None = None
    ) -> tuple[UserSession, str, str]:
        """Atomically consume a refresh token and issue its replacement pair."""
        current = now or datetime.now(UTC)
        token_hash = self.token_service.hash_refresh_token(raw_token)
        stored = self.session.scalar(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .options(joinedload(RefreshToken.session).joinedload(UserSession.user))
            .with_for_update()
        )
        if stored is None:
            raise SessionError("Invalid refresh token")

        user_session = stored.session
        if stored.used_at is not None:
            user_session.revoked_at = current
            for token in user_session.refresh_tokens:
                if token.revoked_at is None:
                    token.revoked_at = current
            self.session.flush()
            raise SessionError("Refresh token reuse detected; session revoked")

        if (
            stored.revoked_at is not None
            or user_session.revoked_at is not None
            or self._is_expired(user_session.expires_at, current)
            or self._is_expired(stored.expires_at, current)
            or not user_session.user.is_active
        ):
            raise SessionError("Invalid refresh token")

        stored.used_at = current
        user_session.last_active_at = current
        new_raw = self.token_service.create_refresh_token()
        new_expiry = self.token_service.refresh_expiry(now=current)
        user_session.expires_at = new_expiry
        self.session.add(
            RefreshToken(
                session=user_session,
                token_hash=self.token_service.hash_refresh_token(new_raw),
                expires_at=new_expiry,
            )
        )
        self.session.flush()
        access = self.token_service.create_access_token(
            user_id=user_session.user_id, session_id=user_session.id
        )
        return user_session, access, new_raw

    def revoke_session(
        self, session_id: UUID, *, user_id: UUID, now: datetime | None = None
    ) -> bool:
        """Revoke one session owned by the given user; return whether it existed."""
        user_session = self.session.scalar(
            select(UserSession).where(
                UserSession.id == session_id, UserSession.user_id == user_id
            ).with_for_update()
        )
        if user_session is None:
            return False
        self._revoke(user_session, now or datetime.now(UTC))
        return True

    def revoke_all_sessions(self, user_id: UUID, *, now: datetime | None = None) -> int:
        """Revoke all active sessions for one user and their refresh tokens."""
        current = now or datetime.now(UTC)
        sessions = list(
            self.session.scalars(
                select(UserSession).where(
                    UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
                ).with_for_update()
            )
        )
        for user_session in sessions:
            self._revoke(user_session, current)
        return len(sessions)

    def list_sessions(self, user_id: UUID) -> list[UserSession]:
        """List sessions belonging to a user, newest first."""
        return list(
            self.session.scalars(
                select(UserSession)
                .where(UserSession.user_id == user_id)
                .order_by(UserSession.created_at.desc())
            )
        )

    @staticmethod
    def _is_expired(expires_at: datetime, now: datetime) -> bool:
        """Compare database timestamps consistently across timezone-aware backends."""
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= now

    def _revoke(self, user_session: UserSession, when: datetime) -> None:
        user_session.revoked_at = when
        for token in user_session.refresh_tokens:
            if token.revoked_at is None:
                token.revoked_at = when
        self.session.flush()
