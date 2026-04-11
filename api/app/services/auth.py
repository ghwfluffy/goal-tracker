from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings
from app.core.security import (
    decode_session_cookie,
    encode_session_cookie,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.db.models import AuthSession, User


class BootstrapError(Exception):
    pass


class AuthenticationError(Exception):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


def is_bootstrap_required(db: Session) -> bool:
    user_count = db.scalar(select(func.count()).select_from(User))
    return user_count == 0


def find_user_by_username(db: Session, username: str) -> User | None:
    statement = select(User).where(User.username == username)
    return db.scalar(statement)


def create_user(
    db: Session,
    *,
    username: str,
    password: str,
    is_admin: bool,
    is_example_data: bool = False,
) -> User:
    user = User(
        id=str(uuid4()),
        username=username,
        password_hash=hash_password(password),
        is_admin=is_admin,
        is_example_data=is_example_data,
    )
    db.add(user)
    db.flush()
    return user


def create_bootstrap_admin(
    db: Session,
    *,
    username: str,
    password: str,
) -> User:
    if not is_bootstrap_required(db):
        raise BootstrapError("Bootstrap is only allowed before the first account exists.")

    return create_user(
        db,
        username=username,
        password=password,
        is_admin=True,
    )


def verify_user_credentials(db: Session, *, username: str, password: str) -> User:
    user = find_user_by_username(db, username)
    if user is None or not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid username or password.")

    return user


def create_session(
    db: Session,
    *,
    user: User,
    settings: Settings,
    user_agent: str | None,
    ip_address: str | None,
) -> tuple[AuthSession, str]:
    now = utcnow()
    raw_token = generate_session_token()
    session_key = settings.session_key
    if session_key is None:
        raise RuntimeError("SESSION_KEY must be available before creating a session.")

    session = AuthSession(
        id=str(uuid4()),
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        last_seen_at=now,
        expires_at=now + timedelta(minutes=settings.session_duration_minutes),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(session)
    db.flush()
    return session, encode_session_cookie(raw_token, session_key)


def find_active_session(
    db: Session,
    *,
    cookie_value: str,
    settings: Settings,
) -> AuthSession | None:
    session_key = settings.session_key
    if session_key is None:
        return None

    raw_token = decode_session_cookie(cookie_value, session_key)
    if raw_token is None:
        return None

    now = utcnow()
    statement = (
        select(AuthSession)
        .options(joinedload(AuthSession.user))
        .where(AuthSession.token_hash == hash_session_token(raw_token))
    )
    session = db.scalar(statement)
    if session is None:
        return None

    if session.revoked_at is not None or session.expires_at <= now:
        return None

    session.last_seen_at = now
    db.flush()
    return session


def revoke_session(db: Session, session: AuthSession) -> None:
    session.revoked_at = utcnow()
    db.flush()
