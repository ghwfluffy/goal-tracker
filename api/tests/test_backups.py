from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services import backups as backup_service


def bootstrap_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert response.status_code == 201


def create_member_client(client: TestClient) -> TestClient:
    create_code_response = client.post(
        "/api/v1/invitation-codes",
        json={"expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat()},
    )
    assert create_code_response.status_code == 201

    member_client = TestClient(client.app)
    register_response = member_client.post(
        "/api/v1/auth/register",
        json={
            "username": "member",
            "password": "supersafepassword",
            "invitation_code": create_code_response.json()["code"],
            "is_example_data": False,
        },
    )
    assert register_response.status_code == 201
    return member_client


def write_fake_backup(
    directory: Path,
    *,
    storage_key: str,
    source: str,
    payload: bytes = b"fake-backup",
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    dump_path = directory / f"{storage_key}.dump"
    manifest_path = directory / f"{storage_key}.json"
    dump_path.write_bytes(payload)
    manifest_path.write_text(
        json.dumps(
            {
                "created_at": datetime(2026, 4, 12, 16, 0, tzinfo=UTC).isoformat(),
                "file_size_bytes": len(payload),
                "filename": dump_path.name,
                "sha256": "a" * 64,
                "source": source,
                "storage_key": storage_key,
            }
        ),
        encoding="utf-8",
    )


def test_admin_can_list_create_and_restore_backups(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    get_settings.cache_clear()
    bootstrap_admin(client)

    write_fake_backup(tmp_path, storage_key="20260412T160000Z_automatic_seed", source="automatic")

    created_storage_keys: list[str] = []

    def fake_run_backup_command(*_args: object, **kwargs: object) -> str:
        source = str(kwargs["source"])
        storage_key = f"20260412T160000Z_{source}_{len(created_storage_keys)}"
        write_fake_backup(tmp_path, storage_key=storage_key, source=source, payload=source.encode("utf-8"))
        created_storage_keys.append(storage_key)
        return storage_key

    restore_targets: list[str] = []

    def fake_run_restore_command(*_args: object, **kwargs: object) -> None:
        backup_path = cast(Path, kwargs["backup_path"])
        restore_targets.append(backup_path.stem)

    monkeypatch.setattr(backup_service, "run_backup_command", fake_run_backup_command)
    monkeypatch.setattr(backup_service, "run_restore_command", fake_run_restore_command)

    list_response = client.get("/api/v1/admin/backups")
    assert list_response.status_code == 200
    inventory = list_response.json()
    assert [backup["storage_key"] for backup in inventory["backups"]] == ["20260412T160000Z_automatic_seed"]
    assert inventory["restores"] == []

    create_response = client.post("/api/v1/admin/backups")
    assert create_response.status_code == 201
    created_backup = create_response.json()
    assert created_backup["trigger_source"] == "manual"
    assert created_backup["created_by_user"]["username"] == "admin"

    restore_response = client.post(
        f"/api/v1/admin/backups/{created_backup['id']}/restore",
        json={"confirmation_text": "RESTORE"},
    )
    assert restore_response.status_code == 200
    restore_payload = restore_response.json()
    assert restore_payload["status"] == "completed"
    assert restore_payload["backup"]["id"] == created_backup["id"]
    assert restore_payload["pre_restore_backup"]["trigger_source"] == "pre_restore"
    assert restore_targets == [created_backup["storage_key"]]

    refreshed_inventory = client.get("/api/v1/admin/backups")
    assert refreshed_inventory.status_code == 200
    refreshed_payload = refreshed_inventory.json()
    assert len(refreshed_payload["backups"]) == 3
    assert refreshed_payload["restores"][0]["status"] == "completed"


def test_backup_restore_requires_admin_access(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    get_settings.cache_clear()
    bootstrap_admin(client)
    member_client = create_member_client(client)
    write_fake_backup(tmp_path, storage_key="20260412T160000Z_automatic_seed", source="automatic")

    try:
        assert member_client.get("/api/v1/admin/backups").status_code == 403
        assert member_client.post("/api/v1/admin/backups").status_code == 403
    finally:
        member_client.close()


def test_restore_requires_explicit_confirmation(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    get_settings.cache_clear()
    bootstrap_admin(client)
    write_fake_backup(tmp_path, storage_key="20260412T160000Z_manual_seed", source="manual")

    inventory_response = client.get("/api/v1/admin/backups")
    assert inventory_response.status_code == 200
    backup_id = inventory_response.json()["backups"][0]["id"]

    restore_response = client.post(
        f"/api/v1/admin/backups/{backup_id}/restore",
        json={"confirmation_text": "cancel"},
    )
    assert restore_response.status_code == 422
    assert restore_response.json()["detail"] == "Type RESTORE to confirm this operation."
