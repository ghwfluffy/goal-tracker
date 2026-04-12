from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.core.config import ROOT_DIR, Settings
from app.db import BackupRecord, RestoreOperation, User
from app.services.auth import normalize_utc_datetime, utcnow

BACKUP_SOURCE_AUTOMATIC = "automatic"
BACKUP_SOURCE_MANUAL = "manual"
BACKUP_SOURCE_PRE_RESTORE = "pre_restore"
RESTORE_CONFIRMATION_TEXT = "RESTORE"
RESTORE_STATUS_RUNNING = "running"
RESTORE_STATUS_COMPLETED = "completed"
RESTORE_STATUS_FAILED = "failed"


class BackupError(Exception):
    pass


class BackupNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class BackupManifest:
    created_at: str
    file_size_bytes: int
    filename: str
    sha256: str
    source: str
    storage_key: str


def backup_directory(settings: Settings) -> Path:
    return Path(settings.backup_dir).resolve()


def backup_script_path() -> Path:
    return ROOT_DIR / "backup" / "create_backup.sh"


def restore_confirmation_is_valid(confirmation_text: str) -> bool:
    return confirmation_text.strip().upper() == RESTORE_CONFIRMATION_TEXT


def _backup_loading_options() -> tuple[Any, ...]:
    return (selectinload(BackupRecord.created_by_user),)


def _restore_loading_options() -> tuple[Any, ...]:
    return (
        selectinload(RestoreOperation.requested_by_user),
        selectinload(RestoreOperation.backup_record).selectinload(BackupRecord.created_by_user),
        selectinload(RestoreOperation.pre_restore_backup).selectinload(BackupRecord.created_by_user),
    )


def list_backup_records(db: Session) -> list[BackupRecord]:
    statement = (
        select(BackupRecord)
        .options(*_backup_loading_options())
        .order_by(BackupRecord.created_at.desc(), BackupRecord.filename.desc())
    )
    return list(db.scalars(statement))


def list_restore_operations(db: Session) -> list[RestoreOperation]:
    statement = (
        select(RestoreOperation)
        .options(*_restore_loading_options())
        .order_by(RestoreOperation.requested_at.desc(), RestoreOperation.id.desc())
    )
    return list(db.scalars(statement))


def get_restore_operation_by_id(db: Session, restore_operation_id: str) -> RestoreOperation:
    statement = (
        select(RestoreOperation)
        .options(*_restore_loading_options())
        .where(RestoreOperation.id == restore_operation_id)
    )
    restore_operation = db.scalar(statement)
    if restore_operation is None:
        raise BackupError("Restore operation was not found.")
    return restore_operation


def get_backup_record_by_id(db: Session, backup_id: str) -> BackupRecord:
    statement = select(BackupRecord).options(*_backup_loading_options()).where(BackupRecord.id == backup_id)
    backup_record = db.scalar(statement)
    if backup_record is None:
        raise BackupNotFoundError("Backup was not found.")
    return backup_record


def get_backup_record_by_storage_key(db: Session, storage_key: str) -> BackupRecord:
    statement = (
        select(BackupRecord)
        .options(*_backup_loading_options())
        .where(BackupRecord.storage_key == storage_key)
    )
    backup_record = db.scalar(statement)
    if backup_record is None:
        raise BackupNotFoundError("Backup was not found.")
    return backup_record


def parse_backup_manifest(path: Path) -> BackupManifest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupError(f"Backup manifest {path.name} is invalid.") from exc

    required_keys = {
        "created_at",
        "file_size_bytes",
        "filename",
        "sha256",
        "source",
        "storage_key",
    }
    if not required_keys.issubset(payload):
        raise BackupError(f"Backup manifest {path.name} is missing required fields.")

    return BackupManifest(
        created_at=str(payload["created_at"]),
        file_size_bytes=int(payload["file_size_bytes"]),
        filename=str(payload["filename"]),
        sha256=str(payload["sha256"]),
        source=str(payload["source"]),
        storage_key=str(payload["storage_key"]),
    )


def sync_backup_records(db: Session, *, settings: Settings) -> list[BackupRecord]:
    directory = backup_directory(settings)
    directory.mkdir(parents=True, exist_ok=True)

    existing_records = {backup_record.storage_key: backup_record for backup_record in list_backup_records(db)}

    for manifest_path in sorted(directory.glob("*.json")):
        manifest = parse_backup_manifest(manifest_path)
        dump_path = directory / manifest.filename
        if not dump_path.exists():
            continue

        record = existing_records.get(manifest.storage_key)
        if record is None:
            record = BackupRecord(
                id=str(uuid4()),
                storage_key=manifest.storage_key,
                filename=manifest.filename,
                relative_path=manifest.filename,
                trigger_source=manifest.source,
                file_size_bytes=manifest.file_size_bytes,
                sha256=manifest.sha256,
                created_at=normalize_utc_datetime(
                    datetime_from_isoformat(manifest.created_at),
                ),
                updated_at=utcnow(),
            )
            db.add(record)
            existing_records[manifest.storage_key] = record
        else:
            record.filename = manifest.filename
            record.relative_path = manifest.filename
            record.trigger_source = manifest.source
            record.file_size_bytes = manifest.file_size_bytes
            record.sha256 = manifest.sha256
            record.created_at = normalize_utc_datetime(datetime_from_isoformat(manifest.created_at))
            record.updated_at = utcnow()

    db.flush()
    return list_backup_records(db)


def datetime_from_isoformat(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise BackupError(f"Backup timestamp {value!r} is invalid.") from exc


def run_backup_command(settings: Settings, *, source: str) -> str:
    script_path = backup_script_path()
    if not script_path.exists():
        raise BackupError(f"Backup script {script_path} is missing.")

    env = {
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "POSTGRES_HOST": settings.postgres_host,
        "POSTGRES_PORT": str(settings.postgres_port),
        "POSTGRES_DB": settings.postgres_db,
        "POSTGRES_USER": settings.postgres_user,
        "POSTGRES_PASSWORD": settings.postgres_password,
        "BACKUP_DIR": str(backup_directory(settings)),
        "BACKUP_UID": str(settings.backup_uid),
        "BACKUP_GID": str(settings.backup_gid),
    }

    completed = subprocess.run(
        [str(script_path), source],
        capture_output=True,
        check=False,
        env=env,
        text=True,
        timeout=settings.backup_command_timeout_seconds,
    )
    if completed.returncode != 0:
        raise BackupError((completed.stderr or completed.stdout).strip() or "Backup command failed.")

    stdout_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip() != ""]
    if len(stdout_lines) == 0:
        raise BackupError("Backup command did not return a storage key.")
    storage_key = stdout_lines[-1]
    if storage_key == "":
        raise BackupError("Backup command did not return a storage key.")
    return storage_key


def create_backup_record_from_command(
    db: Session,
    *,
    settings: Settings,
    source: str,
    requested_by_user: User | None,
) -> BackupRecord:
    storage_key = run_backup_command(settings, source=source)
    sync_backup_records(db, settings=settings)
    backup_record = get_backup_record_by_storage_key(db, storage_key)
    if requested_by_user is not None:
        backup_record.created_by_user_id = requested_by_user.id
        backup_record.updated_at = utcnow()
        db.flush()
    return backup_record


def backup_file_path(settings: Settings, backup_record: BackupRecord) -> Path:
    return backup_directory(settings) / backup_record.relative_path


def dispose_engine_connections(bind: Engine) -> None:
    if bind.url.get_backend_name() == "postgresql":
        bind.dispose()


def run_restore_command(
    settings: Settings,
    *,
    backup_path: Path,
) -> None:
    file_path = backup_path
    if not file_path.exists():
        raise BackupError("Backup file is no longer available on disk.")

    env = {
        "PGPASSWORD": settings.postgres_password,
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    }

    terminate_existing_connections = subprocess.run(
        [
            "psql",
            "--host",
            settings.postgres_host,
            "--port",
            str(settings.postgres_port),
            "--username",
            settings.postgres_user,
            "--dbname",
            "postgres",
            "--command",
            (
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                f"WHERE datname = '{settings.postgres_db}' "
                "AND pid <> pg_backend_pid();"
            ),
        ],
        capture_output=True,
        check=False,
        env=env,
        text=True,
        timeout=settings.backup_command_timeout_seconds,
    )
    if terminate_existing_connections.returncode != 0:
        raise BackupError(
            (terminate_existing_connections.stderr or terminate_existing_connections.stdout).strip()
            or "Unable to prepare the database for restore."
        )

    restore = subprocess.run(
        [
            "pg_restore",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "--host",
            settings.postgres_host,
            "--port",
            str(settings.postgres_port),
            "--username",
            settings.postgres_user,
            "--dbname",
            settings.postgres_db,
            str(file_path),
        ],
        capture_output=True,
        check=False,
        env=env,
        text=True,
        timeout=settings.backup_command_timeout_seconds,
    )
    if restore.returncode != 0:
        raise BackupError((restore.stderr or restore.stdout).strip() or "Restore command failed.")


def create_restore_operation(
    db: Session,
    *,
    requested_by_user: User,
    backup_record: BackupRecord,
    pre_restore_backup: BackupRecord,
) -> RestoreOperation:
    restore_operation = RestoreOperation(
        id=str(uuid4()),
        requested_by_user_id=requested_by_user.id,
        backup_record_id=backup_record.id,
        pre_restore_backup_id=pre_restore_backup.id,
        status=RESTORE_STATUS_RUNNING,
        requested_at=utcnow(),
        started_at=utcnow(),
    )
    db.add(restore_operation)
    db.flush()
    return restore_operation


def update_restore_operation_status(
    db: Session,
    *,
    restore_operation_id: str,
    status: str,
    error_message: str | None = None,
) -> RestoreOperation:
    statement = (
        select(RestoreOperation)
        .options(*_restore_loading_options())
        .where(RestoreOperation.id == restore_operation_id)
    )
    restore_operation = db.scalar(statement)
    if restore_operation is None:
        raise BackupError("Restore operation was not found after execution.")

    restore_operation.status = status
    restore_operation.error_message = error_message
    restore_operation.completed_at = utcnow()
    db.flush()
    return restore_operation


def restore_backup_record(
    db: Session,
    *,
    settings: Settings,
    requested_by_user: User,
    backup_record: BackupRecord,
    confirmation_text: str,
) -> str:
    if not restore_confirmation_is_valid(confirmation_text):
        raise BackupError("Type RESTORE to confirm this operation.")

    bind = cast(Engine, db.get_bind())
    follow_up_session_factory = sessionmaker(
        bind=bind,
        autoflush=False,
        autocommit=False,
        future=True,
    )

    pre_restore_backup = create_backup_record_from_command(
        db,
        settings=settings,
        source=BACKUP_SOURCE_PRE_RESTORE,
        requested_by_user=requested_by_user,
    )
    restore_path = backup_file_path(settings, backup_record)
    restore_operation = create_restore_operation(
        db,
        requested_by_user=requested_by_user,
        backup_record=backup_record,
        pre_restore_backup=pre_restore_backup,
    )
    restore_operation_id = restore_operation.id
    db.commit()
    db.close()

    dispose_engine_connections(bind)

    try:
        run_restore_command(settings, backup_path=restore_path)
        with follow_up_session_factory() as follow_up_db:
            sync_backup_records(follow_up_db, settings=settings)
            update_restore_operation_status(
                follow_up_db,
                restore_operation_id=restore_operation_id,
                status=RESTORE_STATUS_COMPLETED,
            )
            follow_up_db.commit()
            return restore_operation_id
    except BackupError as exc:
        with follow_up_session_factory() as follow_up_db:
            try:
                sync_backup_records(follow_up_db, settings=settings)
                update_restore_operation_status(
                    follow_up_db,
                    restore_operation_id=restore_operation_id,
                    status=RESTORE_STATUS_FAILED,
                    error_message=str(exc),
                )
                follow_up_db.commit()
            except Exception:  # noqa: BLE001
                follow_up_db.rollback()
        raise BackupError(str(exc)) from exc
