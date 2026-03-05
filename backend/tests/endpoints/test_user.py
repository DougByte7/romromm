"""
Integration tests for the /api/users endpoint.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from main import app

from handler.auth import auth_handler
from handler.database import db_user_handler
from models.user import Role, User


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def editor_token(editor_user: User):
    from datetime import timedelta

    from endpoints.auth import ACCESS_TOKEN_EXPIRE_MINUTES
    from handler.auth import oauth_handler

    data = {
        "sub": editor_user.username,
        "iss": "romm:oauth",
        "scopes": " ".join(editor_user.oauth_scopes),
        "type": "access",
    }
    return oauth_handler.create_oauth_token(
        data=data, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )


# ---------------------------------------------------------------------------
# GET /api/users
# ---------------------------------------------------------------------------


class TestGetUsers:
    def test_get_users_returns_200(
        self, client: TestClient, access_token: str, admin_user: User
    ):
        response = client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert isinstance(body, list)
        assert any(u["id"] == admin_user.id for u in body)

    def test_get_users_requires_auth(self, client: TestClient):
        response = client.get("/api/users")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ---------------------------------------------------------------------------
# GET /api/users/me
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    def test_get_me_returns_current_user(
        self, client: TestClient, access_token: str, admin_user: User
    ):
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["id"] == admin_user.id
        assert body["username"] == admin_user.username

    def test_get_me_requires_auth(self, client: TestClient):
        response = client.get("/api/users/me")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ---------------------------------------------------------------------------
# GET /api/users/{id}
# ---------------------------------------------------------------------------


class TestGetUser:
    def test_get_user_by_id(
        self, client: TestClient, access_token: str, admin_user: User
    ):
        response = client.get(
            f"/api/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["id"] == admin_user.id

    def test_get_nonexistent_user_returns_404(
        self, client: TestClient, access_token: str
    ):
        response = client.get(
            "/api/users/999999",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# GET /api/users/identifiers
# ---------------------------------------------------------------------------


class TestGetUserIdentifiers:
    def test_get_identifiers(
        self, client: TestClient, access_token: str, admin_user: User
    ):
        response = client.get(
            "/api/users/identifiers",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        ids = response.json()
        assert isinstance(ids, list)
        assert admin_user.id in ids


# ---------------------------------------------------------------------------
# POST /api/users
# ---------------------------------------------------------------------------


class TestAddUser:
    def test_create_user_as_admin(
        self, client: TestClient, access_token: str
    ):
        response = client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "username": "new_test_user",
                "email": "new_test_user@example.com",
                "password": "Str0ngP@ss!",
                "role": "viewer",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["username"] == "new_test_user"
        assert body["role"] == "viewer"

    def test_create_duplicate_user_returns_400(
        self, client: TestClient, access_token: str, admin_user: User
    ):
        response = client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "username": admin_user.username,
                "email": "another@example.com",
                "password": "Str0ngP@ss!",
                "role": "viewer",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_user_with_invalid_password_returns_400(
        self, client: TestClient, access_token: str
    ):
        response = client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "username": "valid_user_99",
                "email": "valid99@example.com",
                "password": "weak",
                "role": "viewer",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_user_without_admin_scope_returns_403(
        self,
        client: TestClient,
        editor_token: str,
        admin_user: User,
    ):
        response = client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {editor_token}"},
            json={
                "username": "another_user",
                "email": "another@example.com",
                "password": "Str0ngP@ss!",
                "role": "viewer",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# PUT /api/users/{id}
# ---------------------------------------------------------------------------


class TestUpdateUser:
    def test_update_own_user(
        self, client: TestClient, access_token: str, admin_user: User
    ):
        response = client.put(
            f"/api/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            data={"username": admin_user.username},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_update_nonexistent_user_returns_404(
        self, client: TestClient, access_token: str
    ):
        response = client.put(
            "/api/users/999999",
            headers={"Authorization": f"Bearer {access_token}"},
            data={"username": "ghost"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_non_admin_cannot_update_other_user(
        self,
        client: TestClient,
        editor_token: str,
        admin_user: User,
    ):
        response = client.put(
            f"/api/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {editor_token}"},
            data={"username": "hijacked"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# DELETE /api/users/{id}
# ---------------------------------------------------------------------------


class TestDeleteUser:
    def test_delete_user_as_admin(
        self, client: TestClient, access_token: str, viewer_user: User
    ):
        response = client.delete(
            f"/api/users/{viewer_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert db_user_handler.get_user(viewer_user.id) is None

    def test_cannot_delete_yourself(
        self, client: TestClient, access_token: str, admin_user: User
    ):
        response = client.delete(
            f"/api/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_delete_last_admin(
        self, client: TestClient, access_token: str, admin_user: User
    ):
        response = client.delete(
            f"/api/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_nonexistent_user_returns_404(
        self, client: TestClient, access_token: str
    ):
        response = client.delete(
            "/api/users/999999",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
