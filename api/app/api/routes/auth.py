from __future__ import annotations

import base64
import hashlib
import json
from typing import Annotated, cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import (
    decode_session_cookie,
    encode_session_cookie,
    generate_session_token,
    hash_password,
)
from app.db import AuthSession, User, get_db
from app.services.auth import (
    AccountLockedError,
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
    timezone: str
    is_admin: bool
    is_example_data: bool
    avatar_version: str | None
    avatar_url: str | None = None


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
    avatar_version = user.avatar_updated_at.isoformat() if user.avatar_updated_at is not None else None
    return UserSummary(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        timezone=user.timezone,
        is_admin=user.is_admin,
        is_example_data=user.is_example_data,
        avatar_version=avatar_version,
        avatar_url=user.central_avatar_url,
    )


def set_session_cookie(response: Response, *, settings: Settings, cookie_value: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=cookie_value,
        max_age=settings.session_duration_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path=settings.resolved_session_cookie_path,
    )


def clear_session_cookie(response: Response, *, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path=settings.resolved_session_cookie_path,
    )


def base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def pkce_challenge(verifier: str) -> str:
    return base64url(hashlib.sha256(verifier.encode("ascii")).digest())


def safe_next_path(value: str | None) -> str:
    if value is None:
        return "/"
    stripped = value.strip()
    if not stripped.startswith("/") or stripped.startswith("//"):
        return "/"
    return stripped


def app_redirect_url(settings: Settings, path: str, query: dict[str, str] | None = None) -> str:
    split = urlsplit(f"{settings.public_base_url}{path}")
    query_items = dict(parse_qsl(split.query, keep_blank_values=True))
    query_items.update(query or {})
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query_items), split.fragment))


def oauth_error_response(
    settings: Settings,
    *,
    reason: str,
) -> RedirectResponse:
    return RedirectResponse(
        app_redirect_url(settings, "/", {"oauth_error": reason}),
        status_code=status.HTTP_302_FOUND,
    )


def encode_oauth_state_cookie(payload: dict[str, str], settings: Settings) -> str:
    serialized = base64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    return encode_session_cookie(serialized, settings.session_key or "")


def decode_oauth_state_cookie(cookie_value: str, settings: Settings) -> dict[str, str] | None:
    serialized = decode_session_cookie(cookie_value, settings.session_key or "")
    if serialized is None:
        return None
    try:
        padded = serialized + "=" * (-len(serialized) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in payload.items()):
        return None
    return cast(dict[str, str], payload)


def exchange_oauth_code(settings: Settings, *, code: str, verifier: str) -> dict[str, object]:
    token_response = httpx.post(
        f"{settings.normalized_oauth_server_base_url}/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": settings.oauth_client_id,
            "code": code,
            "redirect_uri": settings.oauth_redirect_uri,
            "code_verifier": verifier,
        },
        timeout=10,
    )
    token_response.raise_for_status()
    token_payload = token_response.json()
    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str):
        raise ValueError("OAuth token response did not include an access token.")
    userinfo_response = httpx.get(
        f"{settings.normalized_oauth_server_base_url}/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    userinfo_response.raise_for_status()
    userinfo = userinfo_response.json()
    if not isinstance(userinfo, dict):
        raise ValueError("OAuth userinfo response was invalid.")
    return userinfo


def coerce_oauth_userinfo(value: object, key: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"OAuth userinfo missing {key}.")
    return value.strip()


def unique_oauth_username(db: Session, preferred_username: str) -> str:
    base_username = preferred_username.strip()[:80] or "oauth-user"
    candidate = base_username
    suffix = 1
    while db.scalar(select(User.id).where(User.username == candidate)) is not None:
        suffix += 1
        candidate = f"{base_username}-{suffix}"
    return candidate


def find_or_create_oauth_user(db: Session, *, settings: Settings, userinfo: dict[str, object]) -> User:
    subject = coerce_oauth_userinfo(userinfo.get("sub"), "sub")
    username = coerce_oauth_userinfo(userinfo.get("preferred_username"), "preferred_username")
    provider = settings.normalized_auth_base_url
    user = db.scalar(
        select(User).where(
            User.identity_provider == provider,
            User.external_subject == subject,
        )
    )
    if user is None:
        user = db.scalar(
            select(User).where(
                User.username == username,
                User.identity_provider.is_(None),
                User.external_subject.is_(None),
            )
        )
        if user is None:
            user = User(
                id=str(uuid4()),
                username=unique_oauth_username(db, username),
                password_hash=hash_password(generate_session_token()),
                is_admin=bool(userinfo.get("is_admin")),
                is_example_data=False,
            )
            db.add(user)
        user.identity_provider = provider
        user.external_subject = subject
    name = userinfo.get("name")
    picture = userinfo.get("picture")
    user.display_name = name if isinstance(name, str) and name.strip() != "" else user.display_name
    user.central_avatar_url = picture if isinstance(picture, str) and picture.strip() != "" else None
    user.is_admin = bool(userinfo.get("is_admin"))
    db.flush()
    return user


def refresh_session_cookie(response: Response, request: Request, *, settings: Settings) -> None:
    cookie_value = request.cookies.get(settings.session_cookie_name)
    if cookie_value is None:
        return

    set_session_cookie(response, settings=settings, cookie_value=cookie_value)


def ensure_local_auth_mode(settings: Settings) -> None:
    if settings.auth_mode == "oauth":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Local authentication is disabled while AUTH_MODE=oauth.",
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
    settings: Annotated[Settings, Depends(get_settings)],
) -> BootstrapStatusResponse:
    if settings.auth_mode == "oauth":
        return BootstrapStatusResponse(bootstrap_required=False)
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
    ensure_local_auth_mode(settings)
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
    ensure_local_auth_mode(settings)
    try:
        upgrade_all_example_data_users(db)
        user = verify_user_credentials(
            db,
            username=normalized_username(payload.username),
            password=payload.password,
            settings=settings,
        )
        _, cookie_value = create_session(
            db,
            user=user,
            settings=settings,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client is not None else None,
        )
        db.commit()
    except AccountLockedError as exc:
        db.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except AuthenticationError as exc:
        db.commit()
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
    ensure_local_auth_mode(settings)
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


@router.get("/oauth/login")
def oauth_login(
    settings: Annotated[Settings, Depends(get_settings)],
    next_path: str = Query(default="/", alias="next"),
) -> RedirectResponse:
    if settings.auth_mode != "oauth":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth mode is not enabled.",
        )
    state = generate_session_token()
    verifier = generate_session_token()
    response = RedirectResponse(
        f"{settings.normalized_auth_base_url}/oauth/authorize?"
        + urlencode(
            {
                "response_type": "code",
                "client_id": settings.oauth_client_id,
                "redirect_uri": settings.oauth_redirect_uri,
                "scope": settings.oauth_scope,
                "state": state,
                "code_challenge": pkce_challenge(verifier),
                "code_challenge_method": "S256",
            }
        ),
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        key=settings.oauth_state_cookie_name,
        value=encode_oauth_state_cookie(
            {"state": state, "verifier": verifier, "next": safe_next_path(next_path)},
            settings,
        ),
        max_age=300,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path=settings.resolved_session_cookie_path,
    )
    return response


@router.get("/oauth/callback")
def oauth_callback(
    code: str,
    state: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    if settings.auth_mode != "oauth":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth mode is not enabled.",
        )
    state_cookie = request.cookies.get(settings.oauth_state_cookie_name)
    state_payload = decode_oauth_state_cookie(state_cookie or "", settings)
    if state_payload is None or state_payload.get("state") != state:
        response = oauth_error_response(settings, reason="oauth_state")
        response.delete_cookie(
            key=settings.oauth_state_cookie_name,
            httponly=True,
            samesite="lax",
            secure=settings.session_cookie_secure,
            path=settings.resolved_session_cookie_path,
        )
        return response
    verifier = state_payload.get("verifier")
    if verifier is None:
        response = oauth_error_response(settings, reason="oauth_state")
        response.delete_cookie(
            key=settings.oauth_state_cookie_name,
            httponly=True,
            samesite="lax",
            secure=settings.session_cookie_secure,
            path=settings.resolved_session_cookie_path,
        )
        return response
    try:
        userinfo = exchange_oauth_code(settings, code=code, verifier=verifier)
        user = find_or_create_oauth_user(db, settings=settings, userinfo=userinfo)
        _, cookie_value = create_session(
            db,
            user=user,
            settings=settings,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client is not None else None,
        )
        db.commit()
    except (httpx.HTTPError, ValueError):
        db.rollback()
        response = oauth_error_response(settings, reason="oauth_failed")
        response.delete_cookie(
            key=settings.oauth_state_cookie_name,
            httponly=True,
            samesite="lax",
            secure=settings.session_cookie_secure,
            path=settings.resolved_session_cookie_path,
        )
        return response

    redirect_path = safe_next_path(state_payload.get("next"))
    response = RedirectResponse(
        app_redirect_url(settings, redirect_path),
        status_code=status.HTTP_302_FOUND,
    )
    set_session_cookie(response, settings=settings, cookie_value=cookie_value)
    response.delete_cookie(
        key=settings.oauth_state_cookie_name,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path=settings.resolved_session_cookie_path,
    )
    return response


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
