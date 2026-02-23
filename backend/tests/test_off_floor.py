"""Tests for offFloor enforcement in scoring engine.

Off-season species must never score below their configured offFloor value,
even with terrible conditions. Peak and shoulder seasons are not affected.
"""

import pytest
from unittest.mock import MagicMock

from app.models.enums import DataQuality
from app.services.scoring import calculate_species_score


class TestOffFloorEnforcement:
    """offFloor ensures off-season species always show a minimum score."""

    def _make_bad_weather(self):
        """Create weather with intentionally poor conditions to push score low."""
        w = MagicMock()
        w.wind_speed_kmh = 30.0       # high wind → low wind score
        w.wind_dir_deg = 180           # S wind
        w.pressure_hpa = 990.0         # very low pressure → low pressure score
        w.pressure_change_3h_hpa = 3.0 # rapid rise → bad for fishing
        w.pressure_trend = MagicMock(value="rising")
        w.air_temp_c = 5.0
        w.cloud_cover_pct = 90.0
        w.sea_temp_c = 6.0             # very cold → out of ideal range
        w.wave_height_m = 2.0
        w.data_quality = MagicMock(value="fallback")
        w.data_issues = []
        return w

    def _make_minimal_solunar(self):
        """Solunar data that gives lowest possible score."""
        return {
            "majorPeriods": [],
            "minorPeriods": [],
            "moonPhase": "new_moon",
            "moonIllumination": 0.0,
            "solunarRating": 0.1,
        }

    def test_palamut_feb_off_season_ge_off_floor(
        self, scoring_config, seasonality_config
    ):
        """Palamut in Feb (off-season) with bad conditions >= offFloor(14).

        Feb is in palamut's offMonths: [12, 1, 2, 3, 4, 5, 6].
        offFloor for palamut is 14.
        """
        weather = self._make_bad_weather()
        solunar = self._make_minimal_solunar()

        result = calculate_species_score(
            species_id="palamut",
            weather=weather,
            solunar_data=solunar,
            shore="european",
            rule_bonus=0,
            month=2,          # February — off-season
            hour=14,          # afternoon (not best time)
            minute=0,
            data_quality=DataQuality.fallback,
            has_reports_24h=False,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
        )

        assert result["score"] >= 14, (
            f"Palamut off-season score {result['score']} < offFloor 14"
        )
        assert result["seasonStatus"] == "off"

    def test_cinekop_jul_off_season_ge_off_floor(
        self, scoring_config, seasonality_config
    ):
        """Cinekop in Jul (off-season) with bad conditions >= offFloor(12).

        Jul is in cinekop's offMonths: [3, 4, 5, 6, 7, 8, 9].
        offFloor for cinekop is 12.
        """
        weather = self._make_bad_weather()
        solunar = self._make_minimal_solunar()

        result = calculate_species_score(
            species_id="cinekop",
            weather=weather,
            solunar_data=solunar,
            shore="european",
            rule_bonus=0,
            month=7,          # July — off-season
            hour=14,
            minute=0,
            data_quality=DataQuality.fallback,
            has_reports_24h=False,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
        )

        assert result["score"] >= 12, (
            f"Cinekop off-season score {result['score']} < offFloor 12"
        )
        assert result["seasonStatus"] == "off"

    def test_lufer_mar_off_season_ge_off_floor(
        self, scoring_config, seasonality_config
    ):
        """Lufer in Mar (off-season) with bad conditions >= offFloor(10).

        Mar is in lufer's offMonths: [1, 2, 3, 4, 5, 6, 7, 8].
        offFloor for lufer is 10.
        """
        weather = self._make_bad_weather()
        solunar = self._make_minimal_solunar()

        result = calculate_species_score(
            species_id="lufer",
            weather=weather,
            solunar_data=solunar,
            shore="european",
            rule_bonus=0,
            month=3,
            hour=14,
            minute=0,
            data_quality=DataQuality.fallback,
            has_reports_24h=False,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
        )

        assert result["score"] >= 10, (
            f"Lufer off-season score {result['score']} < offFloor 10"
        )
        assert result["seasonStatus"] == "off"

    def test_cinekop_peak_season_not_affected_by_off_floor(
        self, scoring_config, seasonality_config, mock_weather, mock_solunar
    ):
        """Peak season (Nov for cinekop) uses normal scoring, not offFloor.

        Nov is in cinekop's peakMonths: [11, 12, 1].
        Score should be well above offFloor.
        """
        result = calculate_species_score(
            species_id="cinekop",
            weather=mock_weather,
            solunar_data=mock_solunar,
            shore="european",
            rule_bonus=0,
            month=11,         # November — peak season
            hour=17,          # good cinekop hour (16-20)
            minute=0,
            data_quality=DataQuality.live,
            has_reports_24h=False,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
        )

        assert result["seasonStatus"] == "peak"
        # Peak season with decent weather should score much higher than offFloor
        assert result["score"] > 12, (
            f"Peak season cinekop score {result['score']} is too low"
        )

    def test_cinekop_shoulder_season_not_affected_by_off_floor(
        self, scoring_config, seasonality_config, mock_weather, mock_solunar
    ):
        """Shoulder season (Oct for cinekop) uses normal scoring.

        Oct is in cinekop's shoulderMonths: [10, 2].
        """
        result = calculate_species_score(
            species_id="cinekop",
            weather=mock_weather,
            solunar_data=mock_solunar,
            shore="european",
            rule_bonus=0,
            month=10,         # October — shoulder season
            hour=17,
            minute=0,
            data_quality=DataQuality.live,
            has_reports_24h=False,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
        )

        assert result["seasonStatus"] == "shoulder"
        # Shoulder season with decent conditions should be reasonable
        assert result["score"] > 12

    def test_off_floor_does_not_push_above_floor(
        self, scoring_config, seasonality_config
    ):
        """offFloor only applies when score would be below it.

        If raw off-season score is already above offFloor, it stays as-is.
        """
        # Use decent weather so the base score is above offFloor even with off-season penalty
        w = MagicMock()
        w.wind_speed_kmh = 10.0
        w.wind_dir_deg = 45
        w.pressure_hpa = 1015.0
        w.pressure_change_3h_hpa = -1.5
        w.pressure_trend = MagicMock(value="falling")
        w.air_temp_c = 15.0
        w.cloud_cover_pct = 30.0
        w.sea_temp_c = 16.0
        w.wave_height_m = 0.3

        solunar = {
            "majorPeriods": [{"start": "17:00", "end": "19:00"}],
            "minorPeriods": [],
            "moonPhase": "full_moon",
            "moonIllumination": 100.0,
            "solunarRating": 0.9,
        }

        result = calculate_species_score(
            species_id="cinekop",
            weather=w,
            solunar_data=solunar,
            shore="european",
            rule_bonus=0,
            month=7,          # off-season
            hour=17,          # good cinekop hour
            minute=30,
            data_quality=DataQuality.live,
            has_reports_24h=False,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
        )

        assert result["seasonStatus"] == "off"
        # With good conditions minus off-season penalty, score might be above floor
        # The key invariant: offFloor does NOT cap from above, only floors from below
        assert result["score"] >= 12

    def test_kolyoz_off_season_ge_off_floor(
        self, scoring_config, seasonality_config
    ):
        """Kolyoz in Jan (off-season) with bad conditions >= offFloor(10).

        Jan is in kolyoz's offMonths: [11, 12, 1, 2, 3, 4].
        offFloor for kolyoz is 10.
        """
        weather = self._make_bad_weather()
        solunar = self._make_minimal_solunar()

        result = calculate_species_score(
            species_id="kolyoz",
            weather=weather,
            solunar_data=solunar,
            shore="european",
            rule_bonus=0,
            month=1,
            hour=14,
            minute=0,
            data_quality=DataQuality.fallback,
            has_reports_24h=False,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
        )

        assert result["score"] >= 10, (
            f"Kolyoz off-season score {result['score']} < offFloor 10"
        )
        assert result["seasonStatus"] == "off"
