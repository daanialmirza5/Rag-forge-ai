"""Shared FastAPI dependencies: DB session, current user resolution, and
per-workspace RBAC guards.
"""

import uuid
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

import jwt
from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import TokenType, decode_token
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.services import auth_service, workspace_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DBSession,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User:
    if token is None:
        raise AuthenticationError("Not authenticated")
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Access token has expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Could not validate credentials") from exc

    if payload.get("type") != TokenType.ACCESS.value:
        raise AuthenticationError("Wrong token type")

    subject = payload.get("sub")
    if subject is None:
        raise AuthenticationError("Malformed token")

    return await auth_service.get_user_from_subject(db, subject)


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise PermissionDeniedError("Superuser access required")
    return current_user


CurrentSuperuser = Annotated[User, Depends(require_superuser)]


async def get_request_context(
    x_forwarded_for: Annotated[str | None, Header(include_in_schema=False)] = None,
) -> dict[str, str | None]:
    ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else None
    return {"ip_address": ip}


def require_workspace_role(
    minimum_role: str,
) -> Callable[..., Coroutine[Any, Any, WorkspaceMember]]:
    """Dependency factory: `Depends(require_workspace_role("editor"))` on a
    route with a `workspace_id` path param resolves and validates the
    caller's membership, raising 403 if their role doesn't meet the bar."""

    async def _dependency(
        workspace_id: uuid.UUID,
        db: DBSession,
        current_user: CurrentUser,
    ) -> WorkspaceMember:
        return await workspace_service.require_workspace_role(
            db,
            workspace_id=workspace_id,
            user_id=current_user.id,
            minimum_role=minimum_role,
        )

    return _dependency
