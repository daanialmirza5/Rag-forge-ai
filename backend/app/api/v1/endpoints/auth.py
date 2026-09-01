from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DBSession
from app.schemas.token import RefreshRequest, TokenPair
from app.schemas.user import UserRead, UserRegister
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: DBSession) -> UserRead:
    user = await auth_service.register_user(
        db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        organization_name=payload.organization_name,
    )
    await db.commit()
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    db: DBSession,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenPair:
    user = await auth_service.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    tokens = await auth_service.issue_token_pair(
        db,
        user=user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(request: Request, payload: RefreshRequest, db: DBSession) -> TokenPair:
    tokens = await auth_service.rotate_refresh_token(
        db,
        raw_refresh_token=payload.refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, db: DBSession) -> None:
    await auth_service.revoke_refresh_token(db, raw_refresh_token=payload.refresh_token)
    await db.commit()


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
