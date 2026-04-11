from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db import AuthSession, User, get_db
from app.services.auth import (
    AuthenticationError,
    BootstrapError,
    RegistrationError,
    create_bootstrap_admin,
    create_session,
    find_active_session,
    is_bootstrap_required,
    register_user,
    revoke_session,
    verify_user_credentials,
)
from app.services.example_data import upgrade_all_example_data_users

router = APIRouter(prefix="/auth")


class BootstrapStatusResponse(BaseModel):
    bootstrap_required: bool


class UserSummary(BaseModel):
    id: str
    username: str
    display_name: str | None
    is_admin: bool
    is_example_data: bool
    avatar_version: str | None


class SessionResponse(BaseModel):
    user: UserSummary


class BootstrapRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    invitation_code: str = Field(min_length=32, max_length=32)
    is_example_data: bool = False


def normalized_username(username: str) -> str:
    candidate = username.strip()
    if len(candidate) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Username must contain at least 3 non-space characters.",
        )
    return candidate


def serialize_user_summary(user: User) -> UserSummary:
    avatar_version = (
        user.avatar_updated_at.isoformat() if user.avatar_updated_at is not None else None
    )
    return UserSummary(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_admin=user.is_admin,
        is_example_data=user.is_example_data,
        avatar_version=avatar_version,
    )


def set_session_cookie(response: Response, *, settings: Settings, cookie_value: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=cookie_value,
        max_age=settings.session_duration_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
    )


def clear_session_cookie(response: Response, *, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
    )


def get_authenticated_session(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthSession:
    cookie_value = request.cookies.get(settings.session_cookie_name)
    if cookie_value is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    auth_session = find_active_session(db, cookie_value=cookie_value, settings=settings)
    if auth_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    db.commit()
    return auth_session


def get_current_user(
    auth_session: Annotated[AuthSession, Depends(get_authenticated_session)],
) -> User:
    return auth_session.user


def get_current_admin_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return user


@router.get("/bootstrap-status", response_model=BootstrapStatusResponse)
def get_bootstrap_status(
    db: Annotated[Session, Depends(get_db)],
) -> BootstrapStatusResponse:
    upgrade_all_example_data_users(db)
    db.commit()
    return BootstrapStatusResponse(bootstrap_required=is_bootstrap_required(db))


@router.post("/bootstrap", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_first_admin(
    payload: BootstrapRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    try:
        user = create_bootstrap_admin(
            db,
            username=normalized_username(payload.username),
            password=payload.password,
        )
        _, cookie_value = create_session(
            db,
            user=user,
            settings=settings,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client is not None else None,
        )
        db.commit()
    except BootstrapError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    set_session_cookie(response, settings=settings, cookie_value=cookie_value)
    return SessionResponse(user=serialize_user_summary(user))


@router.post("/login", response_model=SessionResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    try:
        upgrade_all_example_data_users(db)
        user = verify_user_credentials(
            db,
            username=normalized_username(payload.username),
            password=payload.password,
        )
        _, cookie_value = create_session(
            db,
            user=user,
            settings=settings,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client is not None else None,
        )
        db.commit()
    except AuthenticationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    set_session_cookie(response, settings=settings, cookie_value=cookie_value)
    return SessionResponse(user=serialize_user_summary(user))


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    try:
        upgrade_all_example_data_users(db)
        user = register_user(
            db,
            username=normalized_username(payload.username),
            password=payload.password,
            invitation_code_value=payload.invitation_code,
            is_example_data=payload.is_example_data,
        )
        _, cookie_value = create_session(
            db,
            user=user,
            settings=settings,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client is not None else None,
        )
        db.commit()
    except RegistrationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    set_session_cookie(response, settings=settings, cookie_value=cookie_value)
    return SessionResponse(user=serialize_user_summary(user))


@router.get("/me", response_model=SessionResponse)
def read_current_user(
    user: Annotated[User, Depends(get_current_user)],
) -> SessionResponse:
    return SessionResponse(user=serialize_user_summary(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    cookie_value = request.cookies.get(settings.session_cookie_name)
    if cookie_value is not None:
        auth_session = find_active_session(db, cookie_value=cookie_value, settings=settings)
        if auth_session is not None:
            revoke_session(db, auth_session)
            db.commit()

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response, settings=settings)
    return response
