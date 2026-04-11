from __future__ import annotations

import secrets
from datetime import datetime
from string import ascii_letters, digits

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import InvitationCode, User
from app.services.auth import normalize_utc_datetime, utcnow

INVITATION_CODE_ALPHABET = ascii_letters + digits
INVITATION_CODE_LENGTH = 32
MAX_GENERATION_ATTEMPTS = 10


class InvitationCodeError(Exception):
    pass


class InvitationCodeNotFoundError(Exception):
    pass


def normalize_invitation_expiration(expires_at: datetime) -> datetime:
    normalized = normalize_utc_datetime(expires_at)
    if normalized <= utcnow():
        raise InvitationCodeError("Expiration must be in the future.")
    return normalized


def generate_invitation_code_value() -> str:
    return "".join(secrets.choice(INVITATION_CODE_ALPHABET) for _ in range(INVITATION_CODE_LENGTH))


def list_invitation_codes(db: Session) -> list[InvitationCode]:
    statement = (
        select(InvitationCode)
        .options(
            selectinload(InvitationCode.created_by_user),
            selectinload(InvitationCode.created_users),
        )
        .order_by(InvitationCode.created_at.desc())
    )
    return list(db.scalars(statement))


def find_invitation_code_by_id(db: Session, invitation_code_id: str) -> InvitationCode | None:
    statement = (
        select(InvitationCode)
        .options(
            selectinload(InvitationCode.created_by_user),
            selectinload(InvitationCode.created_users),
        )
        .where(InvitationCode.id == invitation_code_id)
    )
    return db.scalar(statement)


def get_invitation_code_by_id(db: Session, invitation_code_id: str) -> InvitationCode:
    invitation_code = find_invitation_code_by_id(db, invitation_code_id)
    if invitation_code is None:
        raise InvitationCodeNotFoundError("Invitation code was not found.")
    return invitation_code


def create_invitation_code(
    db: Session,
    *,
    expires_at: datetime,
    created_by_user: User,
) -> InvitationCode:
    normalized_expiration = normalize_invitation_expiration(expires_at)
    now = utcnow()

    for _ in range(MAX_GENERATION_ATTEMPTS):
        code_value = generate_invitation_code_value()
        existing = db.scalar(select(InvitationCode.id).where(InvitationCode.code == code_value))
        if existing is not None:
            continue

        invitation_code = InvitationCode(
            id=secrets.token_hex(18),
            code=code_value,
            created_by_user_id=created_by_user.id,
            expires_at=normalized_expiration,
            updated_at=now,
        )
        db.add(invitation_code)
        db.flush()
        return get_invitation_code_by_id(db, invitation_code.id)

    raise InvitationCodeError("Unable to generate a unique invitation code.")


def update_invitation_code(
    db: Session,
    *,
    invitation_code: InvitationCode,
    expires_at: datetime,
) -> InvitationCode:
    if invitation_code.revoked_at is not None:
        raise InvitationCodeError("Revoked invitation codes cannot be updated.")

    invitation_code.expires_at = normalize_invitation_expiration(expires_at)
    invitation_code.updated_at = utcnow()
    db.flush()
    return get_invitation_code_by_id(db, invitation_code.id)


def revoke_invitation_code(db: Session, *, invitation_code: InvitationCode) -> None:
    if invitation_code.revoked_at is None:
        invitation_code.revoked_at = utcnow()
        invitation_code.updated_at = utcnow()
        db.flush()
