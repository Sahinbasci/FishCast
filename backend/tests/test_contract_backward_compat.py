"""P0: Contract backward compatibility tests (G1).

Ensures v1.2 → v1.3 safe rollout:
- Both seasonAdjustment AND seasonMultiplier in breakdown
- seasonMultiplier always 1.0 (deprecated fallback)
- No score forced to 0 by seasonality (even off-season)
- Confidence > 0 always
"""

from app.models.enums import DataQuality
from app.services.scoring import calculate_species_score, compute_confidence


class TestDualFieldBreakdown:
    def test_breakdown_has_both_season_fields(self, scoring_config, seasonality_config, mock_weather):
        result = calculate_species_score(
            species_id="palamut",
            weather=mock_weather,
            solunar_data={"majorPeriods": [], "minorPeriods": [], "moonIllumination": 50, "solunarRating": 0.5},
            shore="european",
            rule_bonus=0,
            month=2,  # off-season
            hour=10,
            minute=0,
            data_quality=DataQuality.live,
            has_reports_24h=False,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
        )

        breakdown = result["breakdown"]
        assert "seasonAdjustment" in breakdown, "Missing seasonAdjustment (v1.3)"
        assert "seasonMultiplier" in breakdown, "Missing seasonMultiplier (compat)"

    def test_season_multiplier_always_one(self, scoring_config, seasonality_config, mock_weather):
        for month in [2, 6, 9, 11]:
            result = calculate_species_score(
                species_id="palamut",
                weather=mock_weather,
                solunar_data={"majorPeriods": [], "minorPeriods": [], "moonIllumination": 50, "solunarRating": 0.5},
                shore="european",
                rule_bonus=0,
                month=month,
                hour=10,
                minute=0,
                data_quality=DataQuality.live,
                has_reports_24h=False,
                scoring_config=scoring_config,
                seasonality_config=seasonality_config,
            )
            assert result["breakdown"]["seasonMultiplier"] == 1.0, \
                f"seasonMultiplier must be 1.0 (deprecated), got {result['breakdown']['seasonMultiplier']} for month={month}"


class TestNoScoreZeroedBySeason:
    def test_off_season_palamut_feb_not_zero(self, scoring_config, seasonality_config, mock_weather):
        """Palamut in Feb (off-season) must have score > 0."""
        result = calculate_species_score(
            species_id="palamut",
            weather=mock_weather,
            solunar_data={"majorPeriods": [{"start": "10:00", "end": "12:00"}], "minorPeriods": [], "moonIllumination": 50, "solunarRating": 0.5},
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
        assert result["score"] > 0, f"Off-season score must not be 0, got {result['score']}"

    def test_off_season_cinekop_summer_not_zero(self, scoring_config, seasonality_config, mock_weather):
        """Cinekop in July (off-season) must have score > 0."""
        result = calculate_species_score(
            species_id="cinekop",
            weather=mock_weather,
            solunar_data={"majorPeriods": [{"start": "10:00", "end": "12:00"}], "minorPeriods": [], "moonIllumination": 50, "solunarRating": 0.5},
            shore="european",
            rule_bonus=0,
            month=7,
            hour=10,
            minute=30,
            data_quality=DataQuality.live,
            has_reports_24h=False,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
        )
        assert result["score"] > 0, f"Off-season cinekop score must not be 0, got {result['score']}"


class TestConfidenceNeverZero:
    def test_off_season_confidence_positive(self, scoring_config):
        c = compute_confidence(
            data_quality=DataQuality.fallback,
            has_reports_24h=False,
            season_status="off",
            season_confidence_impact=0.35,
            scoring_config=scoring_config,
        )
        assert c > 0, f"Confidence must never be 0, got {c}"
        assert c >= 0.1, f"Confidence minimum is 0.1, got {c}"

    def test_peak_confidence_high(self, scoring_config):
        c = compute_confidence(
            data_quality=DataQuality.live,
            has_reports_24h=True,
            season_status="peak",
            season_confidence_impact=0.0,
            scoring_config=scoring_config,
        )
        assert c >= 0.8, f"Peak+live+reports confidence should be high, got {c}"


class TestSeasonStatusOff:
    """v1.3.1: Off-season palamut returns 'off' (not 'closed')."""

    def test_off_season_returns_off(self, scoring_config, seasonality_config, mock_weather):
        result = calculate_species_score(
            species_id="palamut",
            weather=mock_weather,
            solunar_data={"majorPeriods": [], "minorPeriods": [], "moonIllumination": 50, "solunarRating": 0.5},
            shore="european",
            rule_bonus=0,
            month=2,
            hour=10,
            minute=0,
            data_quality=DataQuality.live,
            has_reports_24h=False,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
        )
        assert result["seasonStatus"] == "off", \
            f"Off-season palamut should return 'off', got '{result['seasonStatus']}'"
        assert result["score"] > 0, "Off-season score must be positive"

    def test_closed_not_emitted_for_off_season(self, scoring_config, seasonality_config, mock_weather):
        """Scoring engine should never emit 'closed' for off-season species."""
        for month in [1, 2, 3, 4, 5, 6]:  # off-season months for palamut
            result = calculate_species_score(
                species_id="palamut",
                weather=mock_weather,
                solunar_data={"majorPeriods": [], "minorPeriods": [], "moonIllumination": 50, "solunarRating": 0.5},
                shore="european",
                rule_bonus=0,
                month=month,
                hour=10,
                minute=0,
                data_quality=DataQuality.live,
                has_reports_24h=False,
                scoring_config=scoring_config,
                seasonality_config=seasonality_config,
            )
            assert result["seasonStatus"] != "closed", \
                f"Should not emit 'closed' for month={month}, got '{result['seasonStatus']}'"
