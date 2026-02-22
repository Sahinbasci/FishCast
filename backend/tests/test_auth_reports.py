"""Tests for report endpoint auth requirements.

Ensures POST /reports requires valid Firebase Auth token (401 without).
Uses TestClient with lifespan to load spots from data files.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mocked Firebase but real lifespan (loads spots)."""
    with patch("app.services.firebase.initialize_firebase"):
        from app.main import app
        with TestClient(app) as c:
            yield c


class TestReportAuth:
    def test_post_report_no_auth_returns_401(self, client):
        """POST /reports without auth token returns 401."""
        response = client.post(
            "/api/v1/reports",
            json={
                "spotId": "tarabya",
                "species": "istavrit",
                "quantity": 5,
                "avgSize": "20cm",
                "technique": "capari",
            },
        )
        assert response.status_code == 401

    def test_post_report_invalid_token_returns_401(self, client):
        """POST /reports with invalid Bearer token returns 401."""
        with patch("app.services.firebase.verify_firebase_token", new_callable=AsyncMock, return_value=None):
            response = client.post(
                "/api/v1/reports",
                json={
                    "spotId": "tarabya",
                    "species": "istavrit",
                    "quantity": 5,
                    "avgSize": "20cm",
                    "technique": "capari",
                },
                headers={"Authorization": "Bearer invalid_token"},
            )
            assert response.status_code == 401

    def test_get_user_reports_no_auth_returns_401(self, client):
        """GET /reports/user without auth returns 401."""
        response = client.get("/api/v1/reports/user")
        assert response.status_code == 401

    def test_post_report_with_valid_auth_succeeds(self, client):
        """POST /reports with valid auth creates report (201)."""
        mock_user = {"uid": "test-user-123", "email": "test@example.com"}
        with patch("app.services.firebase.verify_firebase_token", new_callable=AsyncMock, return_value=mock_user), \
             patch("app.services.firebase.get_firestore_db", return_value=None):
            response = client.post(
                "/api/v1/reports",
                json={
                    "spotId": "tarabya",
                    "species": "istavrit",
                    "quantity": 5,
                    "avgSize": "20cm",
                    "technique": "capari",
                },
                headers={"Authorization": "Bearer valid_token"},
            )
            assert response.status_code == 201
            data = response.json()
            assert data["spotId"] == "tarabya"
            assert data["species"] == "istavrit"

    def test_post_report_invalid_spot_returns_404(self, client):
        """POST /reports with non-existent spot returns 404."""
        mock_user = {"uid": "test-user-123", "email": "test@example.com"}
        with patch("app.services.firebase.verify_firebase_token", new_callable=AsyncMock, return_value=mock_user):
            response = client.post(
                "/api/v1/reports",
                json={
                    "spotId": "nonexistent_spot",
                    "species": "istavrit",
                    "quantity": 5,
                    "avgSize": "20cm",
                    "technique": "capari",
                },
                headers={"Authorization": "Bearer valid_token"},
            )
            assert response.status_code == 404

    def test_expired_token_returns_401(self, client):
        """POST /reports with expired token returns 401."""
        # Simulate ExpiredIdTokenError
        class ExpiredIdTokenError(Exception):
            pass

        def raise_expired(token, check_revoked=False):
            raise ExpiredIdTokenError("Token expired")

        with patch("app.services.firebase._initialized", True), \
             patch("firebase_admin.auth.verify_id_token", side_effect=raise_expired):
            response = client.post(
                "/api/v1/reports",
                json={
                    "spotId": "tarabya",
                    "species": "istavrit",
                    "quantity": 5,
                    "avgSize": "20cm",
                    "technique": "capari",
                },
                headers={"Authorization": "Bearer expired_token"},
            )
            assert response.status_code == 401

    def test_revoked_token_returns_401(self, client):
        """POST /reports with revoked token returns 401."""
        # Simulate RevokedIdTokenError
        class RevokedIdTokenError(Exception):
            pass

        def raise_revoked(token, check_revoked=False):
            raise RevokedIdTokenError("Token revoked")

        with patch("app.services.firebase._initialized", True), \
             patch("firebase_admin.auth.verify_id_token", side_effect=raise_revoked):
            response = client.post(
                "/api/v1/reports",
                json={
                    "spotId": "tarabya",
                    "species": "istavrit",
                    "quantity": 5,
                    "avgSize": "20cm",
                    "technique": "capari",
                },
                headers={"Authorization": "Bearer revoked_token"},
            )
            assert response.status_code == 401
