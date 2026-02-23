"""Tests for internal endpoint authentication and _meta endpoint.

POST /internal/calculate-scores requires X-Internal-Secret header when
INTERNAL_SECRET env var is set. Without INTERNAL_SECRET, proceeds with warning.

GET /_meta returns runtime config including activeRulesCount and disabledRulesCount.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    """Create a TestClient with mocked Firebase and offline mode."""
    with patch("app.main.initialize_firebase") as mock_firebase, \
         patch.dict("os.environ", {"OFFLINE_MODE": "true"}, clear=False):
        mock_firebase.return_value = None
        with TestClient(app) as c:
            yield c


class TestInternalAuth:
    """POST /api/v1/internal/calculate-scores authentication tests."""

    def test_missing_secret_when_required_returns_403(self):
        """POST without X-Internal-Secret when INTERNAL_SECRET is set → 403."""
        with patch("app.main.initialize_firebase"), \
             patch.dict("os.environ", {
                 "OFFLINE_MODE": "true",
                 "INTERNAL_SECRET": "my-secret-key-123",
             }, clear=False), \
             patch("app.routers.internal._INTERNAL_SECRET", "my-secret-key-123"):
            with TestClient(app) as c:
                resp = c.post("/api/v1/internal/calculate-scores")
                assert resp.status_code == 403
                assert "Invalid or missing" in resp.json()["detail"]

    def test_wrong_secret_returns_403(self):
        """POST with wrong X-Internal-Secret → 403."""
        with patch("app.main.initialize_firebase"), \
             patch.dict("os.environ", {
                 "OFFLINE_MODE": "true",
                 "INTERNAL_SECRET": "my-secret-key-123",
             }, clear=False), \
             patch("app.routers.internal._INTERNAL_SECRET", "my-secret-key-123"):
            with TestClient(app) as c:
                resp = c.post(
                    "/api/v1/internal/calculate-scores",
                    headers={"X-Internal-Secret": "wrong-secret"},
                )
                assert resp.status_code == 403

    def test_correct_secret_proceeds(self):
        """POST with correct X-Internal-Secret → proceeds (mock weather)."""
        with patch("app.main.initialize_firebase"), \
             patch.dict("os.environ", {
                 "OFFLINE_MODE": "true",
                 "INTERNAL_SECRET": "correct-secret",
             }, clear=False), \
             patch("app.routers.internal._INTERNAL_SECRET", "correct-secret"), \
             patch("app.routers.internal.get_weather", new_callable=AsyncMock) as mock_weather, \
             patch("app.routers.internal.compute_solunar") as mock_solunar, \
             patch("app.routers.internal.get_firestore_db") as mock_db:

            # Setup mock returns
            weather_obj = MagicMock()
            weather_obj.data_quality = MagicMock(value="fallback")
            weather_obj.data_issues = ["test"]
            weather_obj.wind_speed_kmh = 10.0
            weather_obj.wind_dir_deg = 45
            weather_obj.wind_direction_cardinal = "NE"
            weather_obj.pressure_hpa = 1015.0
            weather_obj.pressure_change_3h_hpa = -0.5
            weather_obj.pressure_trend = MagicMock(value="stable")
            weather_obj.air_temp_c = 15.0
            weather_obj.cloud_cover_pct = 40.0
            weather_obj.sea_temp_c = 16.0
            weather_obj.wave_height_m = 0.5
            weather_obj.to_dict.return_value = {
                "windSpeedKmh": 10.0, "windDirDeg": 45,
                "windDirectionCardinal": "NE", "windDirectionTR": "poyraz",
                "pressureHpa": 1015.0, "pressureChange3hHpa": -0.5,
                "pressureTrend": "stable", "airTempC": 15.0,
                "seaTempC": 16.0, "waveHeightM": 0.5, "cloudCoverPct": 40.0,
            }
            mock_weather.return_value = weather_obj
            mock_solunar.return_value = {
                "majorPeriods": [], "minorPeriods": [],
                "moonPhase": "waxing_gibbous", "moonIllumination": 65.0,
                "solunarRating": 0.6,
            }
            mock_db.return_value = None  # No Firestore

            with TestClient(app) as c:
                resp = c.post(
                    "/api/v1/internal/calculate-scores",
                    headers={"X-Internal-Secret": "correct-secret"},
                )
                # Should not be 403 — auth passed
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "completed"
                assert data["spotsProcessed"] == 16

    def test_no_internal_secret_env_proceeds_with_warning(self):
        """POST without INTERNAL_SECRET env var → proceeds (dev mode)."""
        with patch("app.main.initialize_firebase"), \
             patch.dict("os.environ", {"OFFLINE_MODE": "true"}, clear=False), \
             patch("app.routers.internal._INTERNAL_SECRET", ""), \
             patch("app.routers.internal.get_weather", new_callable=AsyncMock) as mock_weather, \
             patch("app.routers.internal.compute_solunar") as mock_solunar, \
             patch("app.routers.internal.get_firestore_db") as mock_db:

            weather_obj = MagicMock()
            weather_obj.data_quality = MagicMock(value="fallback")
            weather_obj.data_issues = []
            weather_obj.wind_speed_kmh = 10.0
            weather_obj.wind_dir_deg = 45
            weather_obj.wind_direction_cardinal = "NE"
            weather_obj.pressure_hpa = 1015.0
            weather_obj.pressure_change_3h_hpa = -0.5
            weather_obj.pressure_trend = MagicMock(value="stable")
            weather_obj.air_temp_c = 15.0
            weather_obj.cloud_cover_pct = 40.0
            weather_obj.sea_temp_c = 16.0
            weather_obj.wave_height_m = 0.5
            weather_obj.to_dict.return_value = {
                "windSpeedKmh": 10.0, "windDirDeg": 45,
                "windDirectionCardinal": "NE", "windDirectionTR": "poyraz",
                "pressureHpa": 1015.0, "pressureChange3hHpa": -0.5,
                "pressureTrend": "stable", "airTempC": 15.0,
                "seaTempC": 16.0, "waveHeightM": 0.5, "cloudCoverPct": 40.0,
            }
            mock_weather.return_value = weather_obj
            mock_solunar.return_value = {
                "majorPeriods": [], "minorPeriods": [],
                "moonPhase": "new_moon", "moonIllumination": 0.0,
                "solunarRating": 0.3,
            }
            mock_db.return_value = None

            with TestClient(app) as c:
                # No header, no INTERNAL_SECRET → proceeds (dev mode)
                resp = c.post("/api/v1/internal/calculate-scores")
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "completed"


class TestMetaEndpoint:
    """GET /api/v1/_meta returns runtime configuration."""

    def test_meta_returns_200(self, client):
        """_meta endpoint should return HTTP 200."""
        resp = client.get("/api/v1/_meta")
        assert resp.status_code == 200

    def test_meta_contains_active_rules_count(self, client):
        """_meta should return activeRulesCount."""
        resp = client.get("/api/v1/_meta")
        data = resp.json()
        assert "activeRulesCount" in data
        assert isinstance(data["activeRulesCount"], int)
        assert data["activeRulesCount"] > 0

    def test_meta_contains_disabled_rules_count(self, client):
        """_meta should return disabledRulesCount."""
        resp = client.get("/api/v1/_meta")
        data = resp.json()
        assert "disabledRulesCount" in data
        assert isinstance(data["disabledRulesCount"], int)
        assert data["disabledRulesCount"] >= 0

    def test_meta_active_plus_disabled_equals_total(self, client):
        """activeRulesCount + disabledRulesCount == rulesCount."""
        resp = client.get("/api/v1/_meta")
        data = resp.json()
        total = data["rulesCount"]
        active = data["activeRulesCount"]
        disabled = data["disabledRulesCount"]
        assert active + disabled == total

    def test_meta_contains_disabled_rule_ids(self, client):
        """_meta should return disabledRuleIds list."""
        resp = client.get("/api/v1/_meta")
        data = resp.json()
        assert "disabledRuleIds" in data
        assert isinstance(data["disabledRuleIds"], list)
        # Known disabled rules
        disabled_ids = data["disabledRuleIds"]
        assert "post_poyraz_migration" in disabled_ids
        assert "after_rain_bonus" in disabled_ids
        assert "strong_current_warning" in disabled_ids

    def test_meta_contains_offline_mode(self, client):
        """_meta should reflect OFFLINE_MODE setting."""
        resp = client.get("/api/v1/_meta")
        data = resp.json()
        assert "offlineMode" in data
        # We set OFFLINE_MODE=true in the fixture
        assert data["offlineMode"] is True

    def test_meta_contains_build_sha(self, client):
        """_meta should contain buildSha."""
        resp = client.get("/api/v1/_meta")
        data = resp.json()
        assert "buildSha" in data

    def test_meta_contains_data_source_availability(self, client):
        """_meta should contain dataSourceAvailability."""
        resp = client.get("/api/v1/_meta")
        data = resp.json()
        assert "dataSourceAvailability" in data
        dsa = data["dataSourceAvailability"]
        assert "openMeteo" in dsa
        assert "stormglass" in dsa
        assert "rainData" in dsa
        # Rain data not yet available
        assert dsa["rainData"] is False

    def test_meta_contains_ruleset_version(self, client):
        """_meta should contain rulesetVersion."""
        resp = client.get("/api/v1/_meta")
        data = resp.json()
        assert "rulesetVersion" in data
        assert isinstance(data["rulesetVersion"], str)
