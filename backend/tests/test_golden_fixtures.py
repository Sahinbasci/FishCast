"""P0: Golden fixture tests (4 scenarios).

1. Off-season palamut Feb, favorable conditions
2. Summer low wind LRF
3. Nov cinekop core spots
4. Extreme wind NE + sheltered bebek
"""

from datetime import datetime
from unittest.mock import MagicMock

from app.models.enums import DataQuality
from app.services.scoring import calculate_species_score
from app.services.rules import build_rule_context, evaluate_rules, TIER1_SPECIES, load_and_validate_rules
from app.services.decision import _compute_sheltered_exceptions


class TestGoldenOffSeasonPalamut:
    """Golden #1: Off-season palamut Feb with favorable conditions."""

    def test_score_positive(self, scoring_config, seasonality_config, mock_weather):
        result = calculate_species_score(
            species_id="palamut",
            weather=mock_weather,
            solunar_data={"majorPeriods": [{"start": "10:00", "end": "12:00"}], "minorPeriods": [], "moonIllumination": 50, "solunarRating": 0.6},
            shore="european",
            rule_bonus=0,
            month=2,
            hour=10,
            minute=30,
            data_quality=DataQuality.live,
            has_reports_24h=False,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
        )
        assert result["score"] > 0, "Off-season palamut must have positive score"
        assert result["seasonStatus"] == "off"  # v1.3.1: emits "off" directly
        assert result["confidence"] > 0
        assert result["breakdown"]["seasonMultiplier"] == 1.0

    def test_parca_with_good_conditions(self, scoring_config, seasonality_config, mock_weather):
        """With good conditions, parça ihtimali should trigger."""
        # Set up favorable: high pressure score, good solunar
        mock_weather.pressure_hpa = 1015.0
        mock_weather.pressure_change_3h_hpa = -1.5
        mock_weather.wind_speed_kmh = 10.0
        mock_weather.sea_temp_c = 16.0

        result = calculate_species_score(
            species_id="palamut",
            weather=mock_weather,
            solunar_data={"majorPeriods": [{"start": "10:00", "end": "12:00"}], "minorPeriods": [], "moonIllumination": 80, "solunarRating": 0.8},
            shore="european",
            rule_bonus=0,
            month=2,
            hour=10,
            minute=30,
            data_quality=DataQuality.live,
            has_reports_24h=True,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
        )
        assert result["isParca"] is True, "Parça should trigger with good conditions in off-season"


class TestGoldenSummerLRF:
    """Golden #2: Summer low wind LRF Tarabya."""

    def test_summer_lrf_rules_fire(self, scoring_config, mock_weather, mock_spot, mock_solunar):
        """July, wind=8 → summer_low_wind_lrf should fire."""
        mock_weather.wind_speed_kmh = 8.0
        now = datetime(2026, 7, 15, 21, 0)

        rules = load_and_validate_rules()
        context = build_rule_context(mock_weather, mock_spot, mock_solunar, now)
        result = evaluate_rules(rules, context, TIER1_SPECIES, scoring_config)

        fired_ids = [r["ruleId"] for r in result.active_rules]
        assert "summer_low_wind_lrf" in fired_ids, \
            f"summer_low_wind_lrf should fire in July with wind=8, fired: {fired_ids}"

        # istavrit should get technique hint for LRF
        assert "lrf" in result.technique_hints.get("istavrit", [])


class TestGoldenNovCinekop:
    """Golden #3: Nov cinekop core spots."""

    def test_cinekop_peak_score(self, scoring_config, seasonality_config, mock_weather):
        """November cinekop should have peak season boost."""
        result = calculate_species_score(
            species_id="cinekop",
            weather=mock_weather,
            solunar_data={"majorPeriods": [{"start": "17:00", "end": "19:00"}], "minorPeriods": [], "moonIllumination": 50, "solunarRating": 0.6},
            shore="european",
            rule_bonus=10,
            month=11,
            hour=17,
            minute=30,
            data_quality=DataQuality.live,
            has_reports_24h=True,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
        )
        assert result["score"] >= 50, f"November cinekop should score well, got {result['score']}"
        assert result["seasonStatus"] == "peak"
        assert result["breakdown"]["seasonAdjustment"] > 0


class TestGoldenExtremeWindSheltered:
    """Golden #4: Extreme wind NE + sheltered bebek."""

    def test_nogo_triggers(self, scoring_config, mock_weather_extreme_wind, mock_spot_bebek, mock_solunar):
        """38 km/h NE should trigger noGo."""
        now = datetime(2026, 10, 15, 10, 0)
        rules = load_and_validate_rules()
        context = build_rule_context(mock_weather_extreme_wind, mock_spot_bebek, mock_solunar, now)
        result = evaluate_rules(rules, context, TIER1_SPECIES, scoring_config)
        assert result.is_no_go is True

    def test_sheltered_exception_bebek(self, scoring_config, mock_spot_bebek):
        """Bebek should appear in sheltered exceptions for NE wind."""
        exceptions = _compute_sheltered_exceptions(
            [mock_spot_bebek], "NE", scoring_config
        )
        assert len(exceptions) >= 1
        spot_ids = [e["spotId"] for e in exceptions]
        assert "bebek" in spot_ids

        bebek_exc = next(e for e in exceptions if e["spotId"] == "bebek")
        assert "lrf" in bebek_exc["allowedTechniques"]
        assert bebek_exc["warningLevel"] == "severe"
