"""Tests for mode derivation engine (app.services.mode.derive_mode).

6 priority levels:
    P1: Report signals override → selective for cinekop/sarikanat/lufer
    P2: Extreme conditions (wind >25 or |pressure_change| >3) → holding
    P3: Onshore wind + low shelter + cinekop/sarikanat → holding
    P4: Good solunar + stable pressure → chasing
    P5: Falling pressure + cinekop → selective
    P6: Rising pressure → holding
    Default: chasing
"""

import pytest
from unittest.mock import MagicMock

from app.services.mode import derive_mode


class TestModeDerivation:
    """derive_mode follows strict priority order P1 > P2 > ... > P6 > default."""

    def _make_weather(
        self,
        wind_speed_kmh=10.0,
        wind_dir_deg=45,
        pressure_change_3h_hpa=-0.5,
        pressure_trend="stable",
    ):
        """Create a mock weather object with configurable fields."""
        w = MagicMock()
        w.wind_speed_kmh = wind_speed_kmh
        w.wind_dir_deg = wind_dir_deg
        w.pressure_change_3h_hpa = pressure_change_3h_hpa
        w.pressure_trend = MagicMock(value=pressure_trend)
        return w

    def _make_spot(
        self,
        onshore_dirs_deg=None,
        shelter_score=0.6,
    ):
        """Create a mock spot with wind exposure."""
        spot = MagicMock()
        spot.wind_exposure = MagicMock()
        spot.wind_exposure.onshore_dirs_deg = onshore_dirs_deg or [225]
        spot.wind_exposure.shelter_score_0to1 = shelter_score
        return spot

    def _make_solunar(self, rating=0.5):
        """Create solunar data dict with configurable rating."""
        return {"solunarRating": rating}

    # --- P1: Report signals override ---

    def test_p1_report_signals_cinekop_selective(self):
        """P1: Natural bait bias + cinekop → selective."""
        weather = self._make_weather()
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.9)  # would be chasing at P4
        report_signals = {"naturalBaitBias": True}

        mode = derive_mode("cinekop", weather, solunar, spot, report_signals=report_signals)
        assert mode == "selective"

    def test_p1_report_signals_sarikanat_selective(self):
        """P1: Natural bait bias + sarikanat → selective."""
        weather = self._make_weather()
        spot = self._make_spot()
        solunar = self._make_solunar()
        report_signals = {"naturalBaitBias": True}

        mode = derive_mode("sarikanat", weather, solunar, spot, report_signals=report_signals)
        assert mode == "selective"

    def test_p1_report_signals_lufer_selective(self):
        """P1: Natural bait bias + lufer → selective."""
        weather = self._make_weather()
        spot = self._make_spot()
        solunar = self._make_solunar()
        report_signals = {"naturalBaitBias": True}

        mode = derive_mode("lufer", weather, solunar, spot, report_signals=report_signals)
        assert mode == "selective"

    def test_p1_report_signals_istavrit_not_affected(self):
        """P1: Natural bait bias for istavrit → not affected (falls through)."""
        weather = self._make_weather()
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.6)
        report_signals = {"naturalBaitBias": True}

        mode = derive_mode("istavrit", weather, solunar, spot, report_signals=report_signals)
        # istavrit is not in the P1 target species list, falls to P4 (good solunar + stable)
        assert mode == "chasing"

    def test_p1_no_report_signals_falls_through(self):
        """P1: Without report signals, falls through to lower priorities."""
        weather = self._make_weather()
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.6)

        mode = derive_mode("cinekop", weather, solunar, spot, report_signals=None)
        # No report signals, solunar 0.6 + stable → P4 chasing
        assert mode == "chasing"

    # --- P2: Extreme conditions ---

    def test_p2_extreme_wind_holding(self):
        """P2: Wind > 25 km/h → holding."""
        weather = self._make_weather(wind_speed_kmh=28.0)
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.9)  # would be chasing at P4

        mode = derive_mode("istavrit", weather, solunar, spot)
        assert mode == "holding"

    def test_p2_extreme_pressure_change_positive_holding(self):
        """P2: |pressure_change| > 3.0 (positive) → holding."""
        weather = self._make_weather(pressure_change_3h_hpa=3.5, pressure_trend="rising")
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.9)

        mode = derive_mode("istavrit", weather, solunar, spot)
        assert mode == "holding"

    def test_p2_extreme_pressure_change_negative_holding(self):
        """P2: |pressure_change| > 3.0 (negative) → holding."""
        weather = self._make_weather(pressure_change_3h_hpa=-3.5, pressure_trend="falling")
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.9)

        mode = derive_mode("istavrit", weather, solunar, spot)
        assert mode == "holding"

    def test_p2_exactly_25_not_extreme(self):
        """P2: Wind exactly 25 (not >25) is NOT extreme."""
        weather = self._make_weather(wind_speed_kmh=25.0)
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.6)

        mode = derive_mode("istavrit", weather, solunar, spot)
        # 25 is not > 25, falls through to P4 (good solunar + stable)
        assert mode == "chasing"

    def test_p2_rapid_falling_chasing(self):
        """P2 extension: Rapid pressure fall (< -2.5) → chasing (feeding frenzy)."""
        weather = self._make_weather(pressure_change_3h_hpa=-2.8, pressure_trend="falling")
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.3)

        mode = derive_mode("istavrit", weather, solunar, spot)
        # -2.8 → abs(2.8) < 3.0 so NOT caught by extreme check,
        # but < -2.5 → rapid falling → chasing
        assert mode == "chasing"

    def test_p2_rapid_rising_holding(self):
        """P2 extension: Rapid pressure rise (> 2.5) → holding."""
        weather = self._make_weather(pressure_change_3h_hpa=2.8, pressure_trend="rising")
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.9)

        mode = derive_mode("istavrit", weather, solunar, spot)
        # 2.8 → abs(2.8) < 3.0 so NOT caught by extreme check,
        # but > 2.5 → rapid rising → holding
        assert mode == "holding"

    # --- P3: Onshore wind + low shelter ---

    def test_p3_onshore_low_shelter_cinekop_holding(self):
        """P3: Onshore wind (>15) + low shelter (<0.4) + cinekop → holding."""
        # Onshore direction is 225 (SW), wind from 225 → onshore
        weather = self._make_weather(wind_speed_kmh=20.0, wind_dir_deg=225)
        spot = self._make_spot(onshore_dirs_deg=[225], shelter_score=0.3)
        solunar = self._make_solunar(rating=0.9)  # would be chasing at P4

        mode = derive_mode("cinekop", weather, solunar, spot)
        assert mode == "holding"

    def test_p3_onshore_low_shelter_sarikanat_holding(self):
        """P3: Onshore wind + low shelter + sarikanat → holding."""
        weather = self._make_weather(wind_speed_kmh=20.0, wind_dir_deg=225)
        spot = self._make_spot(onshore_dirs_deg=[225], shelter_score=0.3)
        solunar = self._make_solunar(rating=0.9)

        mode = derive_mode("sarikanat", weather, solunar, spot)
        assert mode == "holding"

    def test_p3_onshore_high_shelter_falls_through(self):
        """P3: Onshore wind but high shelter (>=0.4) → falls through."""
        weather = self._make_weather(wind_speed_kmh=20.0, wind_dir_deg=225)
        spot = self._make_spot(onshore_dirs_deg=[225], shelter_score=0.5)
        solunar = self._make_solunar(rating=0.6)

        mode = derive_mode("cinekop", weather, solunar, spot)
        # shelter >= 0.4, so P3 doesn't trigger → P4 (good solunar + stable)
        assert mode == "chasing"

    def test_p3_istavrit_not_affected(self):
        """P3: Only cinekop/sarikanat are affected, not istavrit."""
        weather = self._make_weather(wind_speed_kmh=20.0, wind_dir_deg=225)
        spot = self._make_spot(onshore_dirs_deg=[225], shelter_score=0.3)
        solunar = self._make_solunar(rating=0.6)

        mode = derive_mode("istavrit", weather, solunar, spot)
        # istavrit not in P3 target → falls to P4
        assert mode == "chasing"

    # --- P4: Good solunar + stable ---

    def test_p4_good_solunar_stable_chasing(self):
        """P4: solunarRating >= 0.6 + stable pressure → chasing."""
        weather = self._make_weather(pressure_trend="stable")
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.6)

        mode = derive_mode("istavrit", weather, solunar, spot)
        assert mode == "chasing"

    def test_p4_excellent_solunar_overrides_trend(self):
        """P4: solunarRating >= 0.8 → chasing regardless of trend."""
        weather = self._make_weather(pressure_trend="rising", pressure_change_3h_hpa=0.8)
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.8)

        mode = derive_mode("istavrit", weather, solunar, spot)
        assert mode == "chasing"

    def test_p4_low_solunar_falls_through(self):
        """P4: solunarRating < 0.6 without stable → falls through."""
        weather = self._make_weather(pressure_trend="falling", pressure_change_3h_hpa=-1.2)
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.4)

        mode = derive_mode("cinekop", weather, solunar, spot)
        # Falls to P5: falling pressure + cinekop → selective
        assert mode == "selective"

    # --- P5: Falling pressure ---

    def test_p5_falling_pressure_cinekop_selective(self):
        """P5: Falling pressure (< -1) + cinekop → selective."""
        weather = self._make_weather(
            pressure_change_3h_hpa=-1.2,
            pressure_trend="falling",
        )
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.4)

        mode = derive_mode("cinekop", weather, solunar, spot)
        assert mode == "selective"

    def test_p5_falling_pressure_istavrit_chasing(self):
        """P5: Falling pressure + istavrit (not cinekop/sarikanat) → chasing."""
        weather = self._make_weather(
            pressure_change_3h_hpa=-1.2,
            pressure_trend="falling",
        )
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.4)

        mode = derive_mode("istavrit", weather, solunar, spot)
        assert mode == "chasing"

    # --- P6: Rising pressure ---

    def test_p6_rising_pressure_holding(self):
        """P6: Rising pressure (> 1) → holding."""
        weather = self._make_weather(
            pressure_change_3h_hpa=1.5,
            pressure_trend="rising",
        )
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.4)

        mode = derive_mode("istavrit", weather, solunar, spot)
        assert mode == "holding"

    def test_p6_slight_rise_not_enough(self):
        """P6: pressure_change > 0 but <= 1 with rising trend → not enough for P6."""
        weather = self._make_weather(
            pressure_change_3h_hpa=0.8,
            pressure_trend="rising",
        )
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.4)

        mode = derive_mode("istavrit", weather, solunar, spot)
        # P6 condition: pressure_trend == "rising" AND change > 1 → not met (0.8 <= 1)
        # Falls to default
        assert mode == "chasing"

    # --- Default ---

    def test_default_chasing(self):
        """Default: no priority matches → chasing."""
        weather = self._make_weather(
            pressure_change_3h_hpa=0.0,
            pressure_trend="stable",
        )
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.3)

        mode = derive_mode("palamut", weather, solunar, spot)
        # solunar 0.3 + stable → P4 condition (0.6) not met
        # Not falling → P5 not met
        # Not rising → P6 not met
        # Default → chasing
        assert mode == "chasing"

    # --- P1 overrides P2 ---

    def test_p1_overrides_extreme_wind(self):
        """P1 has higher priority than P2: report signals override even extreme wind."""
        weather = self._make_weather(wind_speed_kmh=30.0)  # would be P2 holding
        spot = self._make_spot()
        solunar = self._make_solunar()
        report_signals = {"naturalBaitBias": True}

        mode = derive_mode("cinekop", weather, solunar, spot, report_signals=report_signals)
        assert mode == "selective"  # P1 wins

    # --- Pressure config override ---

    def test_pressure_config_overrides_thresholds(self):
        """Custom pressure_config changes extreme/rapid thresholds."""
        weather = self._make_weather(pressure_change_3h_hpa=2.0, pressure_trend="rising")
        spot = self._make_spot()
        solunar = self._make_solunar(rating=0.4)

        # Default thresholds: extreme=3.0, rapid_rising=2.5
        # With custom: extreme=1.5 → 2.0 > 1.5 → holding from P2 extreme
        pressure_config = {
            "extremeChangeThreshold": 1.5,
            "rapidFallingThreshold": -2.5,
            "rapidRisingThreshold": 2.5,
        }

        mode = derive_mode("istavrit", weather, solunar, spot, pressure_config=pressure_config)
        assert mode == "holding"
