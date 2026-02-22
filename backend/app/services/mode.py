"""FishCast mode derivation service.

SCORING_ENGINE.md § Mode Derivation algoritmasını implement eder.
6 öncelik seviyeli deterministik mode hesaplama: chasing|selective|holding.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def derive_mode(
    species_id: str,
    weather: Any,
    solunar_data: dict[str, Any],
    spot: Any,
    report_signals: Optional[dict[str, Any]] = None,
    pressure_config: Optional[dict[str, Any]] = None,
) -> str:
    """Tür davranış modunu derive eder.

    Priority sırası:
        P1: Report signals override (naturalBaitBias + cinekop/sarikanat/lufer)
        P2: Extreme conditions → holding
        P3: Onshore wind + low shelter + cinekop/sarikanat → holding
        P4: Good solunar + stable → chasing
        P5: Falling pressure → selective/chasing
        P6: Rising pressure → holding
        Default: chasing

    Args:
        species_id: Tür kimliği.
        weather: WeatherData objesi (wind_speed_kmh, wind_dir_deg,
                 pressure_change_3h_hpa, pressure_trend).
        solunar_data: Solunar verisi (solunarRating).
        spot: Spot objesi (wind_exposure.onshore_dirs_deg,
              wind_exposure.shelter_score_0to1).
        report_signals: Son 24h topluluk rapor sinyalleri (opsiyonel).

    Returns:
        Mode string: "chasing" | "selective" | "holding".
    """
    # P1: Report signals override (last 24h community data)
    if report_signals and report_signals.get("naturalBaitBias"):
        if species_id in ("cinekop", "sarikanat", "lufer"):
            return "selective"

    # P2: Extreme conditions → holding (config-driven thresholds)
    extreme_change = 3.0
    rapid_falling = -2.5
    rapid_rising = 2.5
    if pressure_config:
        extreme_change = pressure_config.get("extremeChangeThreshold", 3.0)
        rapid_falling = pressure_config.get("rapidFallingThreshold", -2.5)
        rapid_rising = pressure_config.get("rapidRisingThreshold", 2.5)

    if weather.wind_speed_kmh > 25:
        return "holding"
    if abs(weather.pressure_change_3h_hpa) > extreme_change:
        return "holding"

    # Rapid pressure changes override mode
    if weather.pressure_change_3h_hpa < rapid_falling:
        return "chasing"  # feeding frenzy
    if weather.pressure_change_3h_hpa > rapid_rising:
        return "holding"  # fish go deep

    # P3: Onshore wind check (species sensitive to exposure)
    try:
        onshore_dirs = spot.wind_exposure.onshore_dirs_deg
        shelter = spot.wind_exposure.shelter_score_0to1
        wind_dir = weather.wind_dir_deg

        # Check if wind is onshore (within ±22.5° of any onshore direction)
        is_onshore = False
        for onshore_deg in onshore_dirs:
            diff = abs(wind_dir - onshore_deg)
            if diff > 180:
                diff = 360 - diff
            if diff <= 45:
                is_onshore = True
                break

        if is_onshore and weather.wind_speed_kmh > 15 and shelter < 0.4:
            if species_id in ("cinekop", "sarikanat"):
                return "holding"
    except (AttributeError, TypeError):
        pass

    # P4: Good solunar + stable → chasing
    solunar_rating = solunar_data.get("solunarRating", 0.5)
    pressure_trend = weather.pressure_trend.value if hasattr(weather.pressure_trend, 'value') else weather.pressure_trend

    if solunar_rating >= 0.6 and pressure_trend == "stable":
        return "chasing"
    if solunar_rating >= 0.8:
        return "chasing"

    # P5: Falling pressure → selective for cinekop/sarikanat
    if pressure_trend == "falling" and weather.pressure_change_3h_hpa < -1:
        if species_id in ("cinekop", "sarikanat"):
            return "selective"
        return "chasing"

    # P6: Rising pressure → holding
    if pressure_trend == "rising" and weather.pressure_change_3h_hpa > 1:
        return "holding"

    # Default
    return "chasing"
