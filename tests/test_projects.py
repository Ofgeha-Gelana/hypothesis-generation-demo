"""Tests for the /projects endpoints."""
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# GET /projects
# ---------------------------------------------------------------------------

def test_get_projects_returns_empty_list(client):
    response = client.get("/projects")
    assert response.status_code == 200
    assert response.json() == {"projects": []}


def test_get_projects_returns_project_list(client, mock_project_handler, mock_file_handler):
    mock_project_handler.get_projects.return_value = [
        {"id": "proj-1", "name": "Test Project", "gwas_file_id": "file-1", "phenotype": "T2D"},
    ]
    mock_project_handler.load_analysis_state.return_value = {"status": "Completed"}
    mock_file_handler.get_file_metadata.return_value = {
        "download_url": "http://example.com/file",
        "record_count": 100,
    }

    response = client.get("/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data["projects"]) == 1
    assert data["projects"][0]["id"] == "proj-1"
    assert data["projects"][0]["name"] == "Test Project"


# ---------------------------------------------------------------------------
# DELETE /projects
# ---------------------------------------------------------------------------

def test_delete_project_without_id_returns_400(client):
    response = client.delete("/projects")
    assert response.status_code == 400
    assert "Project ID is required" in response.json()["detail"]


def test_delete_project_not_found_returns_404(client, mock_project_handler):
    mock_project_handler.delete_project.return_value = False
    response = client.delete("/projects?id=nonexistent-id")
    assert response.status_code == 404


def test_delete_project_success_returns_200(client, mock_project_handler):
    mock_project_handler.delete_project.return_value = True
    response = client.delete("/projects?id=proj-1")
    assert response.status_code == 200
    assert response.json()["message"] == "Project deleted successfully"


# ---------------------------------------------------------------------------
# POST /projects/delete  (bulk)
# ---------------------------------------------------------------------------

def test_bulk_delete_missing_body_returns_400(client):
    response = client.post("/projects/delete", json={})
    assert response.status_code == 400


def test_bulk_delete_empty_list_returns_400(client):
    response = client.post("/projects/delete", json={"project_ids": []})
    assert response.status_code == 400


def test_bulk_delete_non_list_returns_400(client):
    response = client.post("/projects/delete", json={"project_ids": "proj-1"})
    assert response.status_code == 400
    assert "list" in response.json()["detail"].lower()


def test_bulk_delete_success(client, mock_project_handler):
    mock_project_handler.bulk_delete_projects.return_value = {
        "success": True,
        "deleted_count": 2,
        "total_requested": 2,
    }
    response = client.post(
        "/projects/delete",
        json={"project_ids": ["proj-1", "proj-2"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["deleted_count"] == 2
    assert body["total_requested"] == 2


def test_bulk_delete_partial_success_returns_207(client, mock_project_handler):
    mock_project_handler.bulk_delete_projects.return_value = {
        "success": False,
        "deleted_count": 1,
        "total_requested": 2,
        "errors": ["proj-2 not found"],
    }
    response = client.post(
        "/projects/delete",
        json={"project_ids": ["proj-1", "proj-2"]},
    )
    assert response.status_code == 207
    assert response.json()["deleted_count"] == 1
