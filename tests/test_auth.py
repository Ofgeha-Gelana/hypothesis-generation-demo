"""Tests for JWT authentication middleware on protected endpoints."""
from tests.conftest import make_token, TEST_USER_ID, TEST_JWT_SECRET
import jwt


def test_no_token_returns_403(auth_client):
    response = auth_client.get("/projects")
    assert response.status_code == 403


def test_invalid_token_returns_403(auth_client):
    response = auth_client.get(
        "/projects",
        headers={"Authorization": "Bearer not.a.valid.token"},
    )
    assert response.status_code == 403


def test_token_signed_with_wrong_secret_returns_403(auth_client):
    bad_token = jwt.encode({"user_id": TEST_USER_ID}, "wrong-secret", algorithm="HS256")
    response = auth_client.get(
        "/projects",
        headers={"Authorization": f"Bearer {bad_token}"},
    )
    assert response.status_code == 403


def test_valid_token_is_accepted(auth_client):
    token = make_token()
    response = auth_client.get(
        "/projects",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
