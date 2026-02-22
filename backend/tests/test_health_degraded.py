"""v1.3.2: Health block tests.

Ensures _compute_health_block returns correct status, reasonsCode (machine codes),
reasonsTR (Turkish text), and reasons alias based on data quality and missing fields.
"""

from __future__ import annotations

from typing import Optional
from unittest.mock import MagicMock

from app.services.decision import _compute_health_block


def _make_weather(
    dq: str = "live",
    sea_temp_c: Optional[float] = 16.0,
    wave_height_m: Optional[float] = 0.5,
    data_issues: Optional[list[str]] = None,
) -> MagicMock:
    """Create a mock weather object for health block testing."""
    w = MagicMock()
    w.data_quality = MagicMock(value=dq)
    w.sea_temp_c = sea_temp_c
    w.wave_height_m = wave_height_m
    w.wind_speed_kmh = 12.0
    w.wind_direction_cardinal = "NE"
    w.pressure_trend = MagicMock(value="stable")
    w.data_issues = data_issues or []
    return w


class TestHealthBlock:
    def test_live_data_good_health(self):
        """Live data with no issues → good, empty reasonsCode."""
        weather = _make_weather(dq="live")
        health = _compute_health_block(weather)
        assert health["status"] == "good"
        assert health["reasonsCode"] == []
        assert health["reasonsTR"] == []
        assert health["reasons"] == health["reasonsTR"]

    def test_cached_data_degraded(self):
        """Cached data → degraded + data_quality_cached code."""
        weather = _make_weather(dq="cached")
        health = _compute_health_block(weather)
        assert health["status"] == "degraded"
        assert "data_quality_cached" in health["reasonsCode"]
        assert health["reasons"] == health["reasonsTR"]

    def test_fallback_data_bad(self):
        """Fallback data → bad + data_quality_fallback code."""
        weather = _make_weather(dq="fallback")
        health = _compute_health_block(weather)
        assert health["status"] == "bad"
        assert "data_quality_fallback" in health["reasonsCode"]
        assert health["reasons"] == health["reasonsTR"]

    def test_missing_sea_temp_bad(self):
        """Live but sea_temp=None → bad + missing_sea_temp code."""
        weather = _make_weather(dq="live", sea_temp_c=None)
        health = _compute_health_block(weather)
        assert health["status"] == "bad"
        assert "missing_sea_temp" in health["reasonsCode"]
        assert any("sıcaklığı" in r.lower() or "sicakligi" in r.lower() for r in health["reasonsTR"])
        assert health["reasons"] == health["reasonsTR"]

    def test_missing_wave_height_degraded(self):
        """Live but wave=None → degraded + missing_wave_height code."""
        weather = _make_weather(dq="live", wave_height_m=None)
        health = _compute_health_block(weather)
        assert health["status"] == "degraded"
        assert "missing_wave_height" in health["reasonsCode"]
        assert any("dalga" in r.lower() for r in health["reasonsTR"])
        assert health["reasons"] == health["reasonsTR"]

    def test_normalized_fields_present(self):
        """Normalized dict has wind and pressure fields."""
        weather = _make_weather(dq="live")
        health = _compute_health_block(weather)
        norm = health["normalized"]
        assert "windSpeedKmhRaw" in norm
        assert "windCardinalDerived" in norm
        assert "pressureTrendDerived" in norm
        assert norm["windSpeedKmhRaw"] == 12.0
        assert norm["windCardinalDerived"] == "NE"
        assert norm["pressureTrendDerived"] == "stable"

    def test_provider_issue_codes(self):
        """data_issues list → provider_issue codes (one per issue)."""
        weather = _make_weather(dq="live", data_issues=["Rüzgar verisi güncellenmedi", "Basınç okuma hatası"])
        health = _compute_health_block(weather)
        assert health["status"] == "good"
        assert health["reasonsCode"].count("provider_issue") == 2
        assert len(health["reasonsTR"]) == 2
        assert health["reasons"] == health["reasonsTR"]

    def test_reasons_alias_matches_reasonsTR(self):
        """reasons field is always identical to reasonsTR."""
        weather = _make_weather(dq="cached", sea_temp_c=None, data_issues=["Test issue"])
        health = _compute_health_block(weather)
        assert health["reasons"] is health["reasonsTR"]
