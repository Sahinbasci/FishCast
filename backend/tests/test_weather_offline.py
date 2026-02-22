"""Tests for weather service offline mode and caching.

Ensures OFFLINE_MODE=true produces zero external API calls,
and the in-memory cache works correctly.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from app.services.weather import (
    WeatherData,
    _offline_weather,
    get_weather,
    _weather_cache,
)


class TestOfflineWeather:
    def test_offline_returns_weather_data(self):
        """_offline_weather returns a valid WeatherData instance."""
        w = _offline_weather()
        assert isinstance(w, WeatherData)
        assert w.wind_speed_kmh == 10.0
        assert w.wind_dir_deg == 45
        assert w.sea_temp_c is not None
        assert w.data_quality.value == "fallback"
        assert len(w.data_issues) == 1
        assert "OFFLINE_MODE" in w.data_issues[0]

    @pytest.mark.asyncio
    async def test_get_weather_offline_no_api_calls(self):
        """get_weather with offline_mode=True makes zero external calls."""
        with patch("app.services.weather.fetch_open_meteo") as mock_meteo, \
             patch("app.services.weather.fetch_stormglass") as mock_storm:
            result = await get_weather(offline_mode=True)

            mock_meteo.assert_not_called()
            mock_storm.assert_not_called()
            assert result.data_quality.value == "fallback"
            assert "OFFLINE_MODE" in result.data_issues[0]

    @pytest.mark.asyncio
    async def test_get_weather_online_calls_apis(self):
        """get_weather with offline_mode=False calls Open-Meteo."""
        mock_response = {
            "windSpeedKmh": 15.0,
            "windDirDeg": 90,
            "pressureHpa": 1010.0,
            "pressureChange3hHpa": -1.0,
            "airTempC": 18.0,
            "cloudCoverPct": 60.0,
            "status": "ok",
        }
        # Clear cache to force API call
        _weather_cache.clear()

        with patch("app.services.weather.fetch_open_meteo", new_callable=AsyncMock, return_value=mock_response), \
             patch("app.services.weather.fetch_stormglass", new_callable=AsyncMock, return_value=None):
            result = await get_weather(offline_mode=False)

            assert result.wind_speed_kmh == 15.0
            assert result.air_temp_c == 18.0


class TestWeatherCache:
    @pytest.mark.asyncio
    async def test_cache_hit_avoids_api_call(self):
        """Second call within TTL should use cache, not call APIs."""
        _weather_cache.clear()

        mock_response = {
            "windSpeedKmh": 12.0,
            "windDirDeg": 45,
            "pressureHpa": 1015.0,
            "pressureChange3hHpa": 0.0,
            "airTempC": 14.0,
            "cloudCoverPct": 30.0,
            "status": "ok",
        }

        with patch("app.services.weather.fetch_open_meteo", new_callable=AsyncMock, return_value=mock_response) as mock_meteo, \
             patch("app.services.weather.fetch_stormglass", new_callable=AsyncMock, return_value=None):
            # First call: should call API
            await get_weather(offline_mode=False)
            assert mock_meteo.call_count == 1

            # Second call: should hit cache
            await get_weather(offline_mode=False)
            assert mock_meteo.call_count == 1  # Still 1 — cache hit

        _weather_cache.clear()
