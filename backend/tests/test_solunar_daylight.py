"""P0: Daylight computation tests (G4)."""

from datetime import datetime, timezone


class TestComputeDaylight:
    def test_midday_is_daylight(self):
        """Istanbul midday should be daylight."""
        from app.services.solunar import compute_daylight
        date = datetime(2026, 6, 21, 9, 0, tzinfo=timezone.utc)  # noon Istanbul
        result = compute_daylight(date)

        assert result["isDaylight"] is True
        assert "sunriseLocal" in result
        assert "sunsetLocal" in result
        assert result["tz"] == "Europe/Istanbul"

    def test_midnight_is_not_daylight(self):
        """Istanbul midnight should not be daylight."""
        from app.services.solunar import compute_daylight
        date = datetime(2026, 6, 21, 21, 0, tzinfo=timezone.utc)  # midnight Istanbul
        result = compute_daylight(date)

        assert result["isDaylight"] is False

    def test_sunrise_sunset_format(self):
        """Sunrise/sunset should be HH:MM format."""
        from app.services.solunar import compute_daylight
        date = datetime(2026, 3, 21, 9, 0, tzinfo=timezone.utc)
        result = compute_daylight(date)

        assert ":" in result["sunriseLocal"]
        assert ":" in result["sunsetLocal"]
        parts = result["sunriseLocal"].split(":")
        assert len(parts) == 2
        assert 0 <= int(parts[0]) <= 23
        assert 0 <= int(parts[1]) <= 59

    def test_tz_field(self):
        """tz must always be Europe/Istanbul."""
        from app.services.solunar import compute_daylight
        result = compute_daylight()
        assert result["tz"] == "Europe/Istanbul"

    def test_fallback_when_no_date(self):
        """Should work with None date (defaults to now)."""
        from app.services.solunar import compute_daylight
        result = compute_daylight(None)
        assert "isDaylight" in result
        assert "sunriseLocal" in result
        assert "sunsetLocal" in result
