from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import User

AVATAR_MAX_SIZE = (256, 256)


class ProfileError(Exception):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


def normalize_display_name(display_name: str | None) -> str | None:
    if display_name is None:
        return None

    normalized = display_name.strip()
    return normalized or None


def normalize_timezone(timezone: str | None) -> str:
    if timezone is None:
        return "America/Chicago"

    normalized = timezone.strip()
    if normalized == "":
        raise ProfileError("Timezone is required.")

    try:
        ZoneInfo(normalized)
    except ZoneInfoNotFoundError as exc:
        raise ProfileError("Timezone must be a valid IANA timezone.") from exc

    return normalized


def update_profile(
    db: Session,
    *,
    user: User,
    display_name: str | None,
    timezone: str | None,
) -> User:
    user.display_name = normalize_display_name(display_name)
    if timezone is not None:
        user.timezone = normalize_timezone(timezone)
    user.updated_at = utcnow()
    db.flush()
    return user


def update_avatar(db: Session, *, user: User, image_bytes: bytes) -> User:
    try:
        with Image.open(BytesIO(image_bytes)) as source_image:
            processed_image = source_image.convert("RGBA")
            processed_image.thumbnail(AVATAR_MAX_SIZE)
            output = BytesIO()
            processed_image.save(output, format="PNG")
    except UnidentifiedImageError as exc:
        raise ProfileError("Avatar upload must be a valid image file.") from exc

    user.avatar_png = output.getvalue()
    user.avatar_updated_at = utcnow()
    user.updated_at = utcnow()
    db.flush()
    return user


def change_password(
    db: Session,
    *,
    user: User,
    current_password: str,
    new_password: str,
) -> User:
    if not verify_password(current_password, user.password_hash):
        raise ProfileError("Current password is incorrect.")

    user.password_hash = hash_password(new_password)
    user.updated_at = utcnow()
    db.flush()
    return user


def delete_account(
    db: Session,
    *,
    user: User,
    password: str,
) -> None:
    if not verify_password(password, user.password_hash):
        raise ProfileError("Password confirmation failed.")

    db.delete(user)
    db.flush()
