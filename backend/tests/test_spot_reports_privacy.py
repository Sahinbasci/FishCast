"""Tests for spot reports privacy: aggregate-only for public.

Ensures GET /reports/spot/{id} returns:
- Public (no auth): aggregate summary only (totalReports, speciesCounts, techniqueCounts)
- Auth: user's own raw reports for that spot
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mocked Firebase but real lifespan."""
    with patch("app.services.firebase.initialize_firebase"):
        from app.main import app
        with TestClient(app) as c:
            yield c


class TestSpotReportsPrivacy:
    def test_public_spot_reports_returns_aggregates_only(self, client):
        """GET /reports/spot/{id} without auth returns aggregate summary, no raw reports."""
        # Mock Firestore to return some reports
        mock_db = MagicMock()
        mock_doc1 = MagicMock()
        mock_doc1.to_dict.return_value = {
            "species": "istavrit",
            "quantity": 5,
            "technique": "capari",
            "userId": "user-1",
        }
        mock_doc2 = MagicMock()
        mock_doc2.to_dict.return_value = {
            "species": "istavrit",
            "quantity": 3,
            "technique": "yemli_dip",
            "userId": "user-2",
        }
        mock_doc3 = MagicMock()
        mock_doc3.to_dict.return_value = {
            "species": "cinekop",
            "quantity": 2,
            "technique": "capari",
            "userId": "user-1",
        }

        # Set up Firestore query chain
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.stream.return_value = [mock_doc1, mock_doc2, mock_doc3]
        mock_db.collection.return_value = mock_query

        with patch("app.routers.reports.get_firestore_db", return_value=mock_db), \
             patch("app.routers.reports.get_auth_user", new_callable=AsyncMock, return_value=None):
            response = client.get("/api/v1/reports/spot/tarabya")

        assert response.status_code == 200
        data = response.json()

        # Must have aggregate fields
        assert "totalReports" in data
        assert "speciesCounts" in data
        assert "techniqueCounts" in data
        assert "period" in data
        assert data["period"] == "24h"
        assert data["totalReports"] == 3

        # Species counts: istavrit=8 (5+3), cinekop=2
        assert data["speciesCounts"]["istavrit"] == 8
        assert data["speciesCounts"]["cinekop"] == 2

        # Technique counts: capari=2, yemli_dip=1
        assert data["techniqueCounts"]["capari"] == 2
        assert data["techniqueCounts"]["yemli_dip"] == 1

        # Must NOT have raw reports list
        assert "reports" not in data

    def test_authed_spot_reports_returns_own_list(self, client):
        """GET /reports/spot/{id} with auth returns user's own raw reports."""
        mock_user = {"uid": "test-user-123", "email": "test@example.com"}

        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "species": "istavrit",
            "quantity": 5,
            "technique": "capari",
            "userId": "test-user-123",
            "spotId": "tarabya",
            "timestamp": "2026-02-22T10:00:00+00:00",
        }

        # Set up Firestore query chain
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]
        mock_db.collection.return_value = mock_query

        with patch("app.routers.reports.get_firestore_db", return_value=mock_db), \
             patch("app.routers.reports.get_auth_user", new_callable=AsyncMock, return_value=mock_user):
            response = client.get(
                "/api/v1/reports/spot/tarabya",
                headers={"Authorization": "Bearer valid_token"},
            )

        assert response.status_code == 200
        data = response.json()

        # Must have raw reports list
        assert "reports" in data
        assert "totalCount" in data
        assert data["totalCount"] == 1
        assert data["reports"][0]["species"] == "istavrit"

        # Must NOT have aggregate fields
        assert "speciesCounts" not in data
        assert "techniqueCounts" not in data

    def test_public_spot_reports_invalid_spot_returns_404(self, client):
        """GET /reports/spot/{id} with invalid spot returns 404."""
        response = client.get("/api/v1/reports/spot/nonexistent_spot")
        assert response.status_code == 404

    def test_public_spot_reports_no_db_returns_empty_aggregates(self, client):
        """GET /reports/spot/{id} without Firestore returns empty aggregates."""
        with patch("app.routers.reports.get_firestore_db", return_value=None), \
             patch("app.routers.reports.get_auth_user", new_callable=AsyncMock, return_value=None):
            response = client.get("/api/v1/reports/spot/tarabya")

        assert response.status_code == 200
        data = response.json()
        assert data["totalReports"] == 0
        assert data["speciesCounts"] == {}
        assert data["techniqueCounts"] == {}
