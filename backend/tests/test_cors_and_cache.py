"""Tests for CORS origin parsing and weather LRU cache.

C) Validates CORS_ALLOWED_ORIGINS parsing in main.py.
D) Validates weather cache is bounded, LRU, and handles eviction.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_cors(monkeypatch):
    """Create a test client with custom CORS origins via env var."""
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.fishcast.app, https://staging.fishcast.app , ,https://extra.com")
    # Force re-import to pick up env var
    import importlib
    import app.main
    with patch("app.services.firebase.initialize_firebase"):
        importlib.reload(app.main)
        with TestClient(app.main.app) as c:
            yield c
    # Restore
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    importlib.reload(app.main)


@pytest.fixture
def client_default_cors(monkeypatch):
    """Create a test client with default CORS (no env var)."""
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    import importlib
    import app.main
    with patch("app.services.firebase.initialize_firebase"):
        importlib.reload(app.main)
        with TestClient(app.main.app) as c:
            yield c
    importlib.reload(app.main)


class TestCORSParsing:
    def test_allowed_origin_gets_cors_headers(self, client_with_cors):
        """Request from allowed origin gets Access-Control-Allow-Origin."""
        response = client_with_cors.get(
            "/api/v1/health",
            headers={"Origin": "https://app.fishcast.app"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://app.fishcast.app"

    def test_disallowed_origin_no_cors_headers(self, client_with_cors):
        """Request from disallowed origin gets no CORS header."""
        response = client_with_cors.get(
            "/api/v1/health",
            headers={"Origin": "https://evil.com"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers

    def test_trimmed_origin_with_whitespace(self, client_with_cors):
        """Origin with surrounding whitespace in env var still works."""
        response = client_with_cors.get(
            "/api/v1/health",
            headers={"Origin": "https://staging.fishcast.app"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://staging.fishcast.app"

    def test_empty_segment_ignored(self, client_with_cors):
        """Empty segments between commas are skipped."""
        response = client_with_cors.get(
            "/api/v1/health",
            headers={"Origin": "https://extra.com"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://extra.com"

    def test_default_origins_include_localhost(self, client_default_cors):
        """When env var unset, localhost:3000 is allowed."""
        response = client_default_cors.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_default_origins_include_127(self, client_default_cors):
        """When env var unset, 127.0.0.1:3000 is allowed."""
        response = client_default_cors.get(
            "/api/v1/health",
            headers={"Origin": "http://127.0.0.1:3000"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"


class TestWeatherCacheBound:
    @pytest.mark.asyncio
    async def test_cache_evicts_lru_when_full(self):
        """Weather LRU cache evicts least-recently-used entries when exceeding MAX_CACHE_SIZE."""
        from app.services.weather import _weather_cache, _MAX_CACHE_SIZE, _cache_put, _cache_get
        from app.services.weather import WeatherData
        from app.models.enums import DataQuality

        _weather_cache.clear()

        # Create a small weather data fixture
        def make_weather(wind: float = 10.0) -> WeatherData:
            return WeatherData(
                wind_speed_kmh=wind, wind_dir_deg=0,
                pressure_hpa=1013.0, pressure_change_3h_hpa=0.0,
                air_temp_c=15.0, cloud_cover_pct=50.0,
                sea_temp_c=12.0, wave_height_m=0.3,
                data_quality=DataQuality.live, data_issues=[],
            )

        # Fill cache to exactly MAX_CACHE_SIZE
        for i in range(_MAX_CACHE_SIZE):
            await _cache_put(f"key_{i}", make_weather(float(i)))

        assert len(_weather_cache) == _MAX_CACHE_SIZE

        # Adding one more should evict the first (LRU)
        await _cache_put("extra_key", make_weather(99.0))
        assert len(_weather_cache) == _MAX_CACHE_SIZE
        # key_0 should be evicted (it was first/least-recently-used)
        assert await _cache_get("key_0") is None
        # extra_key should exist
        assert await _cache_get("extra_key") is not None

        _weather_cache.clear()

    @pytest.mark.asyncio
    async def test_cache_lru_order_preserved(self):
        """Reading a cached entry moves it to end, preventing eviction."""
        from app.services.weather import _weather_cache, _MAX_CACHE_SIZE, _cache_put, _cache_get
        from app.services.weather import WeatherData
        from app.models.enums import DataQuality

        _weather_cache.clear()

        def make_weather(wind: float = 10.0) -> WeatherData:
            return WeatherData(
                wind_speed_kmh=wind, wind_dir_deg=0,
                pressure_hpa=1013.0, pressure_change_3h_hpa=0.0,
                air_temp_c=15.0, cloud_cover_pct=50.0,
                sea_temp_c=12.0, wave_height_m=0.3,
                data_quality=DataQuality.live, data_issues=[],
            )

        # Insert A, B, C (with MAX_CACHE_SIZE=3 for this test)
        # We'll fill cache to MAX_CACHE_SIZE and then read key_0 to promote it
        for i in range(_MAX_CACHE_SIZE):
            await _cache_put(f"key_{i}", make_weather(float(i)))

        # Read key_0 to promote it to most-recently-used
        result = await _cache_get("key_0")
        assert result is not None

        # Now add a new entry — should evict key_1 (the actual LRU), NOT key_0
        await _cache_put("new_key", make_weather(100.0))
        assert len(_weather_cache) == _MAX_CACHE_SIZE

        # key_0 should still exist (was promoted by read)
        assert await _cache_get("key_0") is not None
        # key_1 should be evicted (it was the true LRU after key_0 was promoted)
        assert await _cache_get("key_1") is None
        # new_key should exist
        assert await _cache_get("new_key") is not None

        _weather_cache.clear()
