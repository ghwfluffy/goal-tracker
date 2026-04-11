from __future__ import annotations

from datetime import UTC, datetime, timedelta
from string import ascii_letters, digits

from fastapi.testclient import TestClient


def bootstrap_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert response.status_code == 201


def test_admin_can_crud_invitation_codes_and_registration_tracks_created_users(
    client: TestClient,
) -> None:
    bootstrap_admin(client)

    create_response = client.post(
        "/api/v1/invitation-codes",
        json={"expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat()},
    )

    assert create_response.status_code == 201
    created_code = create_response.json()
    assert len(created_code["code"]) == 32
    assert all(character in ascii_letters + digits for character in created_code["code"])
    assert created_code["users_created"] == []

    update_response = client.patch(
        f"/api/v1/invitation-codes/{created_code['id']}",
        json={"expires_at": (datetime.now(UTC) + timedelta(days=14)).isoformat()},
    )
    assert update_response.status_code == 200

    with TestClient(client.app) as signup_client:
        register_response = signup_client.post(
            "/api/v1/auth/register",
            json={
                "username": "teammate",
                "password": "supersafepassword",
                "invitation_code": created_code["code"],
                "is_example_data": True,
            },
        )

    assert register_response.status_code == 201
    assert register_response.json()["user"]["username"] == "teammate"
    assert register_response.json()["user"]["is_example_data"] is True

    list_response = client.get("/api/v1/invitation-codes")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload["invitation_codes"]) == 1
    invitation_code = payload["invitation_codes"][0]
    assert invitation_code["id"] == created_code["id"]
    assert invitation_code["users_created"] == [
        {
            "id": register_response.json()["user"]["id"],
            "username": "teammate",
            "display_name": None,
            "is_example_data": True,
            "created_at": invitation_code["users_created"][0]["created_at"],
        }
    ]

    delete_response = client.delete(f"/api/v1/invitation-codes/{created_code['id']}")
    assert delete_response.status_code == 204

    with TestClient(client.app) as second_signup_client:
        deleted_response = second_signup_client.post(
            "/api/v1/auth/register",
            json={
                "username": "blocked-user",
                "password": "supersafepassword",
                "invitation_code": created_code["code"],
                "is_example_data": False,
            },
        )

    assert deleted_response.status_code == 422
    assert deleted_response.json()["detail"] == "Invitation code is invalid."

    list_after_delete_response = client.get("/api/v1/invitation-codes")
    assert list_after_delete_response.status_code == 200
    assert list_after_delete_response.json() == {"invitation_codes": []}


def test_non_admin_cannot_manage_invitation_codes(client: TestClient) -> None:
    bootstrap_admin(client)

    create_response = client.post(
        "/api/v1/invitation-codes",
        json={"expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat()},
    )
    assert create_response.status_code == 201

    with TestClient(client.app) as signup_client:
        register_response = signup_client.post(
            "/api/v1/auth/register",
            json={
                "username": "member",
                "password": "supersafepassword",
                "invitation_code": create_response.json()["code"],
                "is_example_data": False,
            },
        )
        assert register_response.status_code == 201

        list_response = signup_client.get("/api/v1/invitation-codes")
        assert list_response.status_code == 403
        assert list_response.json()["detail"] == "Administrator access required."
