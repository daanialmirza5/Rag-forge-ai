"""Registration, login, and token lifecycle (issue / refresh / revoke)."""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AlreadyExistsError, AuthenticationError
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.token import TokenPair
from app.services import organization_service, user_service

# A fixed, never-matched hash so a login attempt against a nonexistent email
# still pays bcrypt's ~100ms verification cost — otherwise `authenticate_user`
# would return measurably faster for unregistered emails than for registered
# ones with a wrong password, a timing side-channel that leaks which emails
# have accounts.
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    organization_name: str,
) -> User:
    existing = await user_service.get_user_by_email(db, email)
    if existing is not None:
        raise AlreadyExistsError("An account with this email already exists")

    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    await db.flush()

    await organization_service.create_organization_with_owner(
        db, name=organization_name, owner=user
    )
    return user


async def authenticate_user(db: AsyncSession, *, email: str, password: str) -> User:
    user = await user_service.get_user_by_email(db, email)
    if user is None:
        verify_password(password, _DUMMY_PASSWORD_HASH)  # equalize timing — see comment above
        raise AuthenticationError("Incorrect email or password")
    if not verify_password(password, user.hashed_password):
        raise AuthenticationError("Incorrect email or password")
    if not user.is_active:
        raise AuthenticationError("This account has been deactivated")
    return user


async def issue_token_pair(
    db: AsyncSession,
    *,
    user: User,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenPair:
    default_org = await organization_service.list_user_organizations(db, user.id)
    org_id = str(default_org[0].id) if default_org else None

    access_token = create_access_token(subject=str(user.id), organization_id=org_id)

    raw_refresh = generate_opaque_token()
    refresh_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_opaque_token(raw_refresh),
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_row)
    await db.flush()

    return TokenPair(access_token=access_token, refresh_token=raw_refresh)


async def rotate_refresh_token(
    db: AsyncSession,
    *,
    raw_refresh_token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenPair:
    """Validates the presented refresh token, revokes it, and issues a new
    access+refresh pair (rotation — a replayed old token is a hard failure
    a real implementation would also use to revoke the whole token family)."""
    token_hash = hash_opaque_token(raw_refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    refresh_row = result.scalar_one_or_none()
    if refresh_row is None or not refresh_row.is_active:
        raise AuthenticationError("Refresh token expired or revoked")

    user = await user_service.get_user_by_id(db, refresh_row.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Account is inactive")

    refresh_row.revoked_at = datetime.now(UTC)
    await db.flush()

    return await issue_token_pair(db, user=user, user_agent=user_agent, ip_address=ip_address)


async def revoke_refresh_token(db: AsyncSession, *, raw_refresh_token: str) -> None:
    token_hash = hash_opaque_token(raw_refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    refresh_row = result.scalar_one_or_none()
    if refresh_row is not None and refresh_row.revoked_at is None:
        refresh_row.revoked_at = datetime.now(UTC)
        await db.flush()


async def get_user_from_subject(db: AsyncSession, subject: str) -> User:
    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise AuthenticationError("Invalid token subject") from exc
    user = await user_service.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    return user
