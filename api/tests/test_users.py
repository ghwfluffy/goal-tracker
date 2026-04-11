from __future__ import annotations

import base64

from fastapi.testclient import TestClient

ONE_BY_ONE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4//8/AwAI/AL+X7xL4QAAAABJRU5ErkJggg=="
)


def bootstrap_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert response.status_code == 201


def test_update_profile_changes_display_name(client: TestClient) -> None:
    bootstrap_admin(client)

    response = client.patch("/api/v1/users/me", json={"display_name": "Taylor"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["display_name"] == "Taylor"

    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["user"]["display_name"] == "Taylor"


def test_upload_avatar_stores_png_and_exposes_it(client: TestClient) -> None:
    bootstrap_admin(client)

    upload_response = client.post(
        "/api/v1/users/me/avatar",
        files={"avatar": ("avatar.png", ONE_BY_ONE_PNG, "image/png")},
    )

    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["avatar_version"] is not None

    avatar_response = client.get("/api/v1/users/me/avatar")
    assert avatar_response.status_code == 200
    assert avatar_response.headers["content-type"] == "image/png"
    assert avatar_response.content.startswith(b"\x89PNG")


def test_change_password_requires_current_password(client: TestClient) -> None:
    bootstrap_admin(client)

    bad_response = client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "wrongpassword", "new_password": "newpassword1"},
    )
    assert bad_response.status_code == 422

    good_response = client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "supersafepassword", "new_password": "newpassword1"},
    )
    assert good_response.status_code == 200

    client.post("/api/v1/auth/logout")
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "newpassword1"},
    )
    assert login_response.status_code == 200


def test_delete_account_removes_user_and_allows_bootstrap_again(client: TestClient) -> None:
    bootstrap_admin(client)

    response = client.request(
        "DELETE",
        "/api/v1/users/me",
        json={"password": "supersafepassword"},
    )

    assert response.status_code == 204
    bootstrap_status_response = client.get("/api/v1/auth/bootstrap-status")
    assert bootstrap_status_response.status_code == 200
    assert bootstrap_status_response.json() == {"bootstrap_required": True}
