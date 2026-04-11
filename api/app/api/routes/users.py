from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.routes.auth import clear_session_cookie, get_current_user
from app.core.config import Settings, get_settings
from app.db import User, get_db
from app.services.profile import (
    ProfileError,
    change_password,
    delete_account,
    update_avatar,
    update_profile,
)

router = APIRouter(prefix="/users")


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    display_name: str | None
    timezone: str
    is_admin: bool
    is_example_data: bool
    avatar_version: str | None


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=100)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


def serialize_user_profile(user: User) -> UserProfileResponse:
    avatar_version = (
        user.avatar_updated_at.isoformat() if user.avatar_updated_at is not None else None
    )
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        timezone=user.timezone,
        is_admin=user.is_admin,
        is_example_data=user.is_example_data,
        avatar_version=avatar_version,
    )


@router.patch("/me", response_model=UserProfileResponse)
def patch_current_user_profile(
    payload: UpdateProfileRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserProfileResponse:
    try:
        updated_user = update_profile(
            db,
            user=user,
            display_name=payload.display_name,
            timezone=payload.timezone,
        )
        db.commit()
    except ProfileError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    return serialize_user_profile(updated_user)


@router.post("/me/avatar", response_model=UserProfileResponse)
async def post_current_user_avatar(
    avatar: Annotated[UploadFile, File(...)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserProfileResponse:
    avatar_bytes = await avatar.read()
    if avatar_bytes == b"":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Avatar file is empty."
        )

    try:
        updated_user = update_avatar(db, user=user, image_bytes=avatar_bytes)
        db.commit()
    except ProfileError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    return serialize_user_profile(updated_user)


@router.get("/me/avatar")
def get_current_user_avatar(
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    if user.avatar_png is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not set.")

    return Response(content=user.avatar_png, media_type="image/png")


@router.post("/me/change-password", response_model=UserProfileResponse)
def post_change_password(
    payload: ChangePasswordRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserProfileResponse:
    try:
        updated_user = change_password(
            db,
            user=user,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
        db.commit()
    except ProfileError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    return serialize_user_profile(updated_user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_account(
    payload: DeleteAccountRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    try:
        delete_account(db, user=user, password=payload.password)
        db.commit()
    except ProfileError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response, settings=settings)
    return response
