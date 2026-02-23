"""Tests for pressure trend timezone fix.

Verifies that _compute_pressure_change_3h() uses Istanbul local hour
(not UTC) when indexing into the hourly pressure array.
"""

import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.services.weather import _compute_pressure_change_3h

ISTANBUL_TZ = ZoneInfo("Europe/Istanbul")


class TestPressureChange3h:
    """_compute_pressure_change_3h uses Istanbul hour for array indexing."""

    @pytest.fixture
    def hourly_24(self):
        """24-element pressure array with a clear 3h diff at every position.

        Values: 1000.0, 1001.0, 1002.0, ..., 1023.0
        So pressure_change = hourly[now_idx] - hourly[now_idx - 3] = 3.0 always
        """
        return [1000.0 + i for i in range(24)]

    def test_midday_istanbul_hour(self, hourly_24):
        """At Istanbul hour 12, should compute hourly[12] - hourly[9] = 3.0."""
        now = datetime(2026, 2, 23, 12, 0, 0, tzinfo=ISTANBUL_TZ)
        result = _compute_pressure_change_3h(hourly_24, now=now)
        assert result == pytest.approx(3.0)

    def test_utc_vs_istanbul_difference(self, hourly_24):
        """A UTC datetime should be converted to Istanbul time before indexing.

        UTC 10:00 = Istanbul 13:00 (UTC+3).
        Should compute hourly[13] - hourly[10] = 3.0
        """
        now_utc = datetime(2026, 2, 23, 10, 0, 0, tzinfo=timezone.utc)
        result = _compute_pressure_change_3h(hourly_24, now=now_utc)
        # Istanbul hour is 13 (UTC+3), so [13] - [10] = 3.0
        assert result == pytest.approx(3.0)

    def test_utc_naive_treated_as_utc_then_converted(self, hourly_24):
        """Naive datetime (no tzinfo) is treated as UTC then converted to Istanbul."""
        # Naive hour 10 → treated as UTC → Istanbul hour 13
        now_naive = datetime(2026, 2, 23, 10, 0, 0)
        result = _compute_pressure_change_3h(hourly_24, now=now_naive)
        # Should use Istanbul hour 13: [13] - [10] = 3.0
        assert result == pytest.approx(3.0)

    def test_midnight_edge_case(self, hourly_24):
        """Hour=0 in Istanbul: now_idx=0, past_idx=max(0, 0-3)=0 → diff = 0."""
        now = datetime(2026, 2, 23, 0, 0, 0, tzinfo=ISTANBUL_TZ)
        result = _compute_pressure_change_3h(hourly_24, now=now)
        # hourly[0] - hourly[0] = 0.0
        assert result == pytest.approx(0.0)

    def test_hour_1_edge_case(self, hourly_24):
        """Hour=1: now_idx=1, past_idx=max(0, 1-3)=0 → diff = 1.0."""
        now = datetime(2026, 2, 23, 1, 0, 0, tzinfo=ISTANBUL_TZ)
        result = _compute_pressure_change_3h(hourly_24, now=now)
        assert result == pytest.approx(1.0)

    def test_hour_2_edge_case(self, hourly_24):
        """Hour=2: now_idx=2, past_idx=max(0, 2-3)=0 → diff = 2.0."""
        now = datetime(2026, 2, 23, 2, 0, 0, tzinfo=ISTANBUL_TZ)
        result = _compute_pressure_change_3h(hourly_24, now=now)
        assert result == pytest.approx(2.0)

    def test_late_night_hour_23(self, hourly_24):
        """Hour=23: now_idx=23, past_idx=20 → diff = 3.0."""
        now = datetime(2026, 2, 23, 23, 0, 0, tzinfo=ISTANBUL_TZ)
        result = _compute_pressure_change_3h(hourly_24, now=now)
        assert result == pytest.approx(3.0)

    def test_short_array_returns_zero(self):
        """Arrays with < 4 items should return 0.0 (insufficient data)."""
        now = datetime(2026, 2, 23, 12, 0, 0, tzinfo=ISTANBUL_TZ)
        assert _compute_pressure_change_3h([], now=now) == 0.0
        assert _compute_pressure_change_3h([1013.0], now=now) == 0.0
        assert _compute_pressure_change_3h([1013.0, 1014.0], now=now) == 0.0
        assert _compute_pressure_change_3h([1013.0, 1014.0, 1015.0], now=now) == 0.0

    def test_four_elements_is_minimum(self):
        """Exactly 4 elements should work (indices 0-3)."""
        now = datetime(2026, 2, 23, 3, 0, 0, tzinfo=ISTANBUL_TZ)
        hourly = [1010.0, 1011.0, 1012.0, 1013.0]
        result = _compute_pressure_change_3h(hourly, now=now)
        # now_idx = min(3, 3) = 3, past_idx = max(0, 3-3) = 0
        assert result == pytest.approx(3.0)

    def test_none_at_now_index_returns_zero(self, hourly_24):
        """None value at current hour index should return 0.0."""
        hourly = list(hourly_24)
        hourly[12] = None
        now = datetime(2026, 2, 23, 12, 0, 0, tzinfo=ISTANBUL_TZ)
        result = _compute_pressure_change_3h(hourly, now=now)
        assert result == 0.0

    def test_none_at_past_index_returns_zero(self, hourly_24):
        """None value at past hour index should return 0.0."""
        hourly = list(hourly_24)
        hourly[9] = None  # past_idx for hour 12
        now = datetime(2026, 2, 23, 12, 0, 0, tzinfo=ISTANBUL_TZ)
        result = _compute_pressure_change_3h(hourly, now=now)
        assert result == 0.0

    def test_both_none_returns_zero(self):
        """All None values should return 0.0."""
        hourly = [None] * 24
        now = datetime(2026, 2, 23, 12, 0, 0, tzinfo=ISTANBUL_TZ)
        result = _compute_pressure_change_3h(hourly, now=now)
        assert result == 0.0

    def test_falling_pressure(self):
        """Decreasing pressure should produce negative change."""
        # 1020 at hour 9, 1015 at hour 12 → change = -5
        hourly = [1020.0] * 24
        hourly[12] = 1015.0
        now = datetime(2026, 2, 23, 12, 0, 0, tzinfo=ISTANBUL_TZ)
        result = _compute_pressure_change_3h(hourly, now=now)
        assert result == pytest.approx(-5.0)

    def test_hour_exceeds_array_length(self):
        """When Istanbul hour exceeds array length, now_idx is clamped."""
        hourly = [1010.0, 1011.0, 1012.0, 1013.0, 1014.0]  # only 5 elements
        # Istanbul hour 23 → now_idx = min(23, 4) = 4
        now = datetime(2026, 2, 23, 23, 0, 0, tzinfo=ISTANBUL_TZ)
        result = _compute_pressure_change_3h(hourly, now=now)
        # now_idx=4, past_idx=max(0, 4-3)=1 → [4]-[1] = 1014-1011 = 3.0
        assert result == pytest.approx(3.0)
