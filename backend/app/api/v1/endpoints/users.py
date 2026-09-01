from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import AuthenticationError
from app.core.security import hash_password, verify_password
from app.schemas.user import PasswordChange, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me", response_model=UserRead)
async def update_me(payload: UserUpdate, current_user: CurrentUser, db: DBSession) -> UserRead:
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    await db.flush()
    await db.commit()
    return UserRead.model_validate(current_user)


@router.post("/me/change-password", status_code=204)
async def change_password(
    payload: PasswordChange, current_user: CurrentUser, db: DBSession
) -> None:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise AuthenticationError("Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    await db.flush()
    await db.commit()
