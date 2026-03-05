"""
Integration tests for the /api/collections endpoint.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from main import app

from handler.database import db_collection_handler
from handler.filesystem.resources_handler import FSResourcesHandler
from models.collection import Collection
from models.user import User


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def collection(admin_user: User) -> Collection:
    col = Collection(
        name="Test Collection",
        description="A test collection",
        is_public=False,
        is_favorite=False,
        user_id=admin_user.id,
    )
    return db_collection_handler.add_collection(col)


# ---------------------------------------------------------------------------
# GET /api/collections
# ---------------------------------------------------------------------------


class TestGetCollections:
    def test_get_collections_returns_200(
        self, client: TestClient, access_token: str
    ):
        response = client.get(
            "/api/collections",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_get_collections_requires_auth(self, client: TestClient):
        response = client.get("/api/collections")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_get_collections_includes_created_collection(
        self,
        client: TestClient,
        access_token: str,
        collection: Collection,
    ):
        response = client.get(
            "/api/collections",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        ids = [c["id"] for c in response.json()]
        assert collection.id in ids


# ---------------------------------------------------------------------------
# GET /api/collections/{id}
# ---------------------------------------------------------------------------


class TestGetCollection:
    def test_get_collection_by_id(
        self,
        client: TestClient,
        access_token: str,
        collection: Collection,
    ):
        response = client.get(
            f"/api/collections/{collection.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["id"] == collection.id
        assert body["name"] == "Test Collection"

    def test_get_collection_not_found(
        self, client: TestClient, access_token: str
    ):
        response = client.get(
            "/api/collections/999999",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# POST /api/collections
# ---------------------------------------------------------------------------


class TestAddCollection:
    @patch.object(FSResourcesHandler, "get_cover", new_callable=AsyncMock)
    def test_create_collection(
        self,
        mock_get_cover: AsyncMock,
        client: TestClient,
        access_token: str,
    ):
        mock_get_cover.return_value = ("", "")

        response = client.post(
            "/api/collections",
            headers={"Authorization": f"Bearer {access_token}"},
            data={"name": "Brand New Collection", "description": "Created via test"},
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["name"] == "Brand New Collection"

    @patch.object(FSResourcesHandler, "get_cover", new_callable=AsyncMock)
    def test_create_duplicate_collection_returns_error(
        self,
        mock_get_cover: AsyncMock,
        client: TestClient,
        access_token: str,
        collection: Collection,
    ):
        mock_get_cover.return_value = ("", "")

        response = client.post(
            "/api/collections",
            headers={"Authorization": f"Bearer {access_token}"},
            data={"name": collection.name, "description": "Duplicate"},
        )
        assert response.status_code == status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# PUT /api/collections/{id}
# ---------------------------------------------------------------------------


class TestUpdateCollection:
    @patch.object(FSResourcesHandler, "get_cover", new_callable=AsyncMock)
    @patch.object(FSResourcesHandler, "cover_exists", return_value=False)
    def test_update_collection_name(
        self,
        mock_cover_exists,
        mock_get_cover: AsyncMock,
        client: TestClient,
        access_token: str,
        collection: Collection,
    ):
        mock_get_cover.return_value = ("", "")

        response = client.put(
            f"/api/collections/{collection.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            data={
                "name": "Renamed Collection",
                "description": collection.description or "",
                "rom_ids": "[]",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["name"] == "Renamed Collection"

    def test_update_nonexistent_collection_returns_404(
        self,
        client: TestClient,
        access_token: str,
    ):
        response = client.put(
            "/api/collections/999999",
            headers={"Authorization": f"Bearer {access_token}"},
            data={"name": "Any", "description": "", "rom_ids": "[]"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# DELETE /api/collections/{id}
# ---------------------------------------------------------------------------


class TestDeleteCollection:
    @patch.object(FSResourcesHandler, "remove_directory", new_callable=AsyncMock)
    def test_delete_collection(
        self,
        mock_remove_dir: AsyncMock,
        client: TestClient,
        access_token: str,
        collection: Collection,
    ):
        mock_remove_dir.return_value = None

        response = client.delete(
            f"/api/collections/{collection.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert db_collection_handler.get_collection(collection.id) is None

    @patch.object(FSResourcesHandler, "remove_directory", new_callable=AsyncMock)
    def test_delete_nonexistent_collection_returns_404(
        self,
        mock_remove_dir: AsyncMock,
        client: TestClient,
        access_token: str,
    ):
        response = client.delete(
            "/api/collections/999999",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# GET /api/collections/identifiers
# ---------------------------------------------------------------------------


class TestCollectionIdentifiers:
    def test_get_identifiers(
        self,
        client: TestClient,
        access_token: str,
        collection: Collection,
    ):
        response = client.get(
            "/api/collections/identifiers",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        ids = response.json()
        assert isinstance(ids, list)
        assert collection.id in ids
