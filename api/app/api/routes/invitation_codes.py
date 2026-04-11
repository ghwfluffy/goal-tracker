from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_admin_user
from app.db import InvitationCode, User, get_db
from app.services.invitations import (
    InvitationCodeError,
    InvitationCodeNotFoundError,
    create_invitation_code,
    get_invitation_code_by_id,
    list_invitation_codes,
    update_invitation_code,
)
from app.services.invitations import (
    delete_invitation_code as delete_invitation_code_record,
)

router = APIRouter(prefix="/invitation-codes")


class InvitationCodeUserSummary(BaseModel):
    id: str
    username: str
    display_name: str | None
    is_example_data: bool
    created_at: str


class InvitationCodeSummary(BaseModel):
    id: str
    code: str
    created_by_username: str | None
    expires_at: str
    created_at: str
    users_created: list[InvitationCodeUserSummary]


class InvitationCodeListResponse(BaseModel):
    invitation_codes: list[InvitationCodeSummary]


class CreateInvitationCodeRequest(BaseModel):
    expires_at: datetime


class UpdateInvitationCodeRequest(BaseModel):
    expires_at: datetime


def serialize_invitation_code_user(user: User) -> InvitationCodeUserSummary:
    return InvitationCodeUserSummary(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_example_data=user.is_example_data,
        created_at=user.created_at.isoformat(),
    )


def serialize_invitation_code(invitation_code: InvitationCode) -> InvitationCodeSummary:
    users_created = sorted(
        invitation_code.created_users,
        key=lambda user: user.created_at,
    )
    return InvitationCodeSummary(
        id=invitation_code.id,
        code=invitation_code.code,
        created_by_username=(
            invitation_code.created_by_user.username
            if invitation_code.created_by_user is not None
            else None
        ),
        expires_at=invitation_code.expires_at.isoformat(),
        created_at=invitation_code.created_at.isoformat(),
        users_created=[serialize_invitation_code_user(user) for user in users_created],
    )


@router.get("", response_model=InvitationCodeListResponse)
def get_invitation_codes(
    _admin_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> InvitationCodeListResponse:
    return InvitationCodeListResponse(
        invitation_codes=[serialize_invitation_code(code) for code in list_invitation_codes(db)]
    )


@router.post("", response_model=InvitationCodeSummary, status_code=status.HTTP_201_CREATED)
def post_invitation_code(
    payload: CreateInvitationCodeRequest,
    admin_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> InvitationCodeSummary:
    try:
        invitation_code = create_invitation_code(
            db,
            expires_at=payload.expires_at,
            created_by_user=admin_user,
        )
        db.commit()
    except InvitationCodeError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_invitation_code(invitation_code)


@router.patch("/{invitation_code_id}", response_model=InvitationCodeSummary)
def patch_invitation_code(
    invitation_code_id: str,
    payload: UpdateInvitationCodeRequest,
    _admin_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> InvitationCodeSummary:
    try:
        invitation_code = get_invitation_code_by_id(db, invitation_code_id)
        updated_invitation_code = update_invitation_code(
            db,
            invitation_code=invitation_code,
            expires_at=payload.expires_at,
        )
        db.commit()
    except InvitationCodeNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvitationCodeError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_invitation_code(updated_invitation_code)


@router.delete("/{invitation_code_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invitation_code(
    invitation_code_id: str,
    _admin_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        invitation_code = get_invitation_code_by_id(db, invitation_code_id)
        delete_invitation_code_record(db, invitation_code=invitation_code)
        db.commit()
    except InvitationCodeNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
