from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes.auth import get_current_admin_user
from app.core.config import Settings, get_settings
from app.db import BackupRecord, RestoreOperation, User, get_db
from app.services.backups import (
    BACKUP_SOURCE_MANUAL,
    BackupError,
    BackupNotFoundError,
    create_backup_record_from_command,
    get_backup_record_by_id,
    get_restore_operation_by_id,
    list_backup_records,
    list_restore_operations,
    restore_backup_record,
    sync_backup_records,
)

router = APIRouter(prefix="/admin/backups")


class BackupUserSummary(BaseModel):
    id: str
    username: str
    display_name: str | None


class BackupSummary(BaseModel):
    id: str
    storage_key: str
    filename: str
    relative_path: str
    trigger_source: str
    file_size_bytes: int
    sha256: str
    created_at: str
    created_by_user: BackupUserSummary | None


class RestoreOperationSummary(BaseModel):
    id: str
    status: str
    error_message: str | None
    requested_at: str
    started_at: str | None
    completed_at: str | None
    requested_by_user: BackupUserSummary | None
    backup: BackupSummary | None
    pre_restore_backup: BackupSummary | None


class BackupInventoryResponse(BaseModel):
    backups: list[BackupSummary]
    restores: list[RestoreOperationSummary]


class RestoreBackupRequest(BaseModel):
    confirmation_text: str = Field(min_length=1, max_length=32)


def serialize_backup_user(user: User) -> BackupUserSummary:
    return BackupUserSummary(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
    )


def serialize_backup(backup_record: BackupRecord) -> BackupSummary:
    return BackupSummary(
        id=backup_record.id,
        storage_key=backup_record.storage_key,
        filename=backup_record.filename,
        relative_path=backup_record.relative_path,
        trigger_source=backup_record.trigger_source,
        file_size_bytes=backup_record.file_size_bytes,
        sha256=backup_record.sha256,
        created_at=backup_record.created_at.isoformat(),
        created_by_user=(
            serialize_backup_user(backup_record.created_by_user)
            if backup_record.created_by_user is not None
            else None
        ),
    )


def serialize_restore_operation(restore_operation: RestoreOperation) -> RestoreOperationSummary:
    return RestoreOperationSummary(
        id=restore_operation.id,
        status=restore_operation.status,
        error_message=restore_operation.error_message,
        requested_at=restore_operation.requested_at.isoformat(),
        started_at=(
            restore_operation.started_at.isoformat() if restore_operation.started_at is not None else None
        ),
        completed_at=(
            restore_operation.completed_at.isoformat() if restore_operation.completed_at is not None else None
        ),
        requested_by_user=(
            serialize_backup_user(restore_operation.requested_by_user)
            if restore_operation.requested_by_user is not None
            else None
        ),
        backup=serialize_backup(restore_operation.backup_record)
        if restore_operation.backup_record is not None
        else None,
        pre_restore_backup=serialize_backup(restore_operation.pre_restore_backup)
        if restore_operation.pre_restore_backup is not None
        else None,
    )


@router.get("", response_model=BackupInventoryResponse)
def get_backups(
    _admin_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BackupInventoryResponse:
    sync_backup_records(db, settings=settings)
    db.commit()
    return BackupInventoryResponse(
        backups=[serialize_backup(backup_record) for backup_record in list_backup_records(db)],
        restores=[serialize_restore_operation(operation) for operation in list_restore_operations(db)],
    )


@router.post("", response_model=BackupSummary, status_code=status.HTTP_201_CREATED)
def post_backup(
    admin_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BackupSummary:
    try:
        backup_record = create_backup_record_from_command(
            db,
            settings=settings,
            source=BACKUP_SOURCE_MANUAL,
            requested_by_user=admin_user,
        )
        db.commit()
    except BackupError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return serialize_backup(backup_record)


@router.post("/{backup_id}/restore", response_model=RestoreOperationSummary)
def post_restore_backup(
    backup_id: str,
    payload: RestoreBackupRequest,
    admin_user: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RestoreOperationSummary:
    try:
        sync_backup_records(db, settings=settings)
        backup_record = get_backup_record_by_id(db, backup_id)
        bind = db.get_bind()
        restore_operation_id = restore_backup_record(
            db,
            settings=settings,
            requested_by_user=admin_user,
            backup_record=backup_record,
            confirmation_text=payload.confirmation_text,
        )
    except BackupNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BackupError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    follow_up_session_factory = sessionmaker(
        bind=bind,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    with follow_up_session_factory() as follow_up_db:
        restore_operation = get_restore_operation_by_id(follow_up_db, restore_operation_id)
        return serialize_restore_operation(restore_operation)
