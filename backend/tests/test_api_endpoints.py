"""Smoke tests for FishCast API endpoints using FastAPI TestClient.

Tests basic endpoint availability and response structure.
Mocks Firebase and weather for offline/isolated testing.
"""

import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    """Create a TestClient with mocked Firebase and offline mode.

    Uses the app lifespan (which loads real data files) but mocks
    Firebase initialization so no credentials are needed.
    """
    with patch("app.main.initialize_firebase") as mock_firebase, \
         patch.dict("os.environ", {"OFFLINE_MODE": "true"}, clear=False):
        mock_firebase.return_value = None
        with TestClient(app) as c:
            yield c


class TestHealthEndpoint:
    """GET /api/v1/health returns system status."""

    def test_health_returns_200(self, client):
        """Health check should return HTTP 200."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_health_returns_status_ok(self, client):
        """Health response should contain status: ok."""
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_contains_engine_version(self, client):
        """Health response should contain engineVersion."""
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "engineVersion" in data
        assert isinstance(data["engineVersion"], str)

    def test_health_contains_rules_count(self, client):
        """Health response should contain rulesCount > 0."""
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "rulesCount" in data
        assert data["rulesCount"] > 0


class TestSpotsEndpoint:
    """GET /api/v1/spots returns list of fishing spots."""

    def test_spots_returns_200(self, client):
        """Spots endpoint should return HTTP 200."""
        resp = client.get("/api/v1/spots")
        assert resp.status_code == 200

    def test_spots_returns_list(self, client):
        """Spots should return a list."""
        resp = client.get("/api/v1/spots")
        data = resp.json()
        assert isinstance(data, list)

    def test_spots_count_is_16(self, client):
        """Should return exactly 16 spots."""
        resp = client.get("/api/v1/spots")
        data = resp.json()
        assert len(data) == 16

    def test_spot_has_required_fields(self, client):
        """Each spot should have id, name, shore, regionId."""
        resp = client.get("/api/v1/spots")
        data = resp.json()
        first_spot = data[0]
        assert "id" in first_spot
        assert "name" in first_spot
        assert "shore" in first_spot
        assert "regionId" in first_spot

    def test_spots_filter_by_shore(self, client):
        """Filter spots by shore=european should return only European spots."""
        resp = client.get("/api/v1/spots?shore=european")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        for spot in data:
            assert spot["shore"] == "european"


class TestSpeciesEndpoint:
    """GET /api/v1/species returns list of fish species."""

    def test_species_returns_200(self, client):
        """Species endpoint should return HTTP 200."""
        resp = client.get("/api/v1/species")
        assert resp.status_code == 200

    def test_species_returns_list(self, client):
        """Species should return a list."""
        resp = client.get("/api/v1/species")
        data = resp.json()
        assert isinstance(data, list)

    def test_species_count_is_9(self, client):
        """Should return exactly 9 species (5 Tier 1 + 4 Tier 2)."""
        resp = client.get("/api/v1/species")
        data = resp.json()
        assert len(data) == 9

    def test_species_has_required_fields(self, client):
        """Each species should have id, name, tier."""
        resp = client.get("/api/v1/species")
        data = resp.json()
        first = data[0]
        assert "id" in first
        assert "name" in first
        assert "tier" in first

    def test_species_filter_by_tier1(self, client):
        """Filter by tier=1 should return Tier 1 species only."""
        resp = client.get("/api/v1/species?tier=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        for sp in data:
            assert sp["tier"] == 1

    def test_species_filter_by_tier2(self, client):
        """Filter by tier=2 should return Tier 2 species only."""
        resp = client.get("/api/v1/species?tier=2")
        assert resp.status_code == 200
        data = resp.json()
        for sp in data:
            assert sp["tier"] == 2


class TestTechniquesEndpoint:
    """GET /api/v1/techniques returns list of fishing techniques."""

    def test_techniques_returns_200(self, client):
        """Techniques endpoint should return HTTP 200."""
        resp = client.get("/api/v1/techniques")
        assert resp.status_code == 200

    def test_techniques_returns_list(self, client):
        """Techniques should return a list."""
        resp = client.get("/api/v1/techniques")
        data = resp.json()
        assert isinstance(data, list)

    def test_techniques_count_is_7(self, client):
        """Should return exactly 7 techniques."""
        resp = client.get("/api/v1/techniques")
        data = resp.json()
        assert len(data) == 7

    def test_technique_has_required_fields(self, client):
        """Each technique should have id and name."""
        resp = client.get("/api/v1/techniques")
        data = resp.json()
        first = data[0]
        assert "id" in first
        assert "name" in first


class TestRootEndpoint:
    """GET / returns API info."""

    def test_root_returns_200(self, client):
        """Root endpoint should return HTTP 200."""
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_contains_message(self, client):
        """Root response should contain a message."""
        resp = client.get("/")
        data = resp.json()
        assert "message" in data

    def test_root_contains_docs_link(self, client):
        """Root response should contain docs link."""
        resp = client.get("/")
        data = resp.json()
        assert "docs" in data


class TestNotFound:
    """404 for unknown endpoints and resources."""

    def test_unknown_spot_returns_404(self, client):
        """GET /api/v1/spots/unknown should return 404."""
        resp = client.get("/api/v1/spots/unknown_spot_xyz")
        assert resp.status_code == 404

    def test_unknown_species_returns_404(self, client):
        """GET /api/v1/species/unknown should return 404."""
        resp = client.get("/api/v1/species/unknown_species_xyz")
        assert resp.status_code == 404

    def test_unknown_technique_returns_404(self, client):
        """GET /api/v1/techniques/unknown should return 404."""
        resp = client.get("/api/v1/techniques/unknown_technique_xyz")
        assert resp.status_code == 404
