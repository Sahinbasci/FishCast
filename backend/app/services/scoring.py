"""FishCast scoring service — v1.3 hardened.

All configs injected via parameters (no module-level state).
Additive seasonality: NEVER hard-zeros a score.
Dual-field backward compat: seasonAdjustment (new) + seasonMultiplier (deprecated).

Formül (v1.3):
    score = clamp(0, 100, round(weighted_sum * 100 + season_adj) + capped_bonus)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from app.models.enums import DataQuality
from app.services.weather import MONTHLY_SEA_TEMP
from app.utils.wind import degrees_to_cardinal_8

logger = logging.getLogger(__name__)


# --- 1. Pressure Score ---

def pressure_score(hpa: float, change_3h: float) -> float:
    """Pressure parameter score (0.0-1.0)."""
    if 1010 <= hpa <= 1020:
        base = 1.0
    elif 1005 <= hpa < 1010 or 1020 < hpa <= 1025:
        base = 0.7
    elif 1000 <= hpa < 1005 or 1025 < hpa <= 1030:
        base = 0.4
    else:
        base = 0.2

    if change_3h < -2:
        base = min(1.0, base + 0.3)
    elif change_3h < -1:
        base = min(1.0, base + 0.15)
    elif change_3h > 2:
        base = max(0.0, base - 0.2)

    return base


# --- 2. Wind Score ---

def wind_score(kmh: float, dir_deg: int, shore: str) -> float:
    """Wind parameter score (0.0-1.0)."""
    if kmh < 5:
        base = 0.65
    elif kmh <= 15:
        base = 0.90
    elif kmh <= 25:
        base = 0.75
    elif kmh <= 35:
        base = 0.40
    else:
        return 0.0

    cardinal = degrees_to_cardinal_8(dir_deg)
    if kmh >= 25:
        if cardinal in ("NE", "N") and shore == "anatolian":
            base -= 0.15
        elif cardinal in ("NE", "N") and shore == "european":
            base += 0.08
        elif cardinal in ("SW", "S") and shore == "european":
            base -= 0.15
        elif cardinal in ("SW", "S") and shore == "anatolian":
            base += 0.05

    return max(0.0, min(1.0, base))


# --- 3. Sea Temp Score (config-driven) ---

def sea_temp_score(
    temp_c: Optional[float],
    species_id: str,
    scoring_config: Optional[dict[str, Any]] = None,
) -> float:
    """Sea temperature parameter score (0.0-1.0).

    Reads temp ranges from scoring_config["speciesTemp"] if available,
    falls back to hardcoded defaults for backward compat.
    """
    # Get species temp config
    if scoring_config and "speciesTemp" in scoring_config:
        spec = scoring_config["speciesTemp"].get(species_id)
    else:
        spec = None

    if spec is None:
        return 0.5

    if temp_c is None:
        temp_c = MONTHLY_SEA_TEMP.get(datetime.now().month, 15.0)

    t_min = spec["min"]
    t_max = spec["max"]
    pen = spec["pen"]

    if t_min <= temp_c <= t_max:
        mid = (t_min + t_max) / 2
        half_range = (t_max - t_min) / 2
        if half_range == 0:
            return 1.0
        distance = abs(temp_c - mid) / half_range
        return max(0.5, 1.0 - distance * 0.3)
    else:
        if temp_c < t_min:
            diff = t_min - temp_c
        else:
            diff = temp_c - t_max
        penalty = diff / pen
        return max(0.0, 0.5 - penalty)


# --- 4. Solunar Score ---

def solunar_score(current_hour: int, current_minute: int, solunar_data: dict[str, Any]) -> float:
    """Solunar parameter score (0.0-1.0)."""
    current_minutes = current_hour * 60 + current_minute

    def _time_to_minutes(time_str: str) -> int:
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])

    def _in_period(start_str: str, end_str: str) -> bool:
        start = _time_to_minutes(start_str)
        end = _time_to_minutes(end_str)
        if start <= end:
            return start <= current_minutes <= end
        return current_minutes >= start or current_minutes <= end

    def _approaching(start_str: str, minutes_before: int = 60) -> bool:
        start = _time_to_minutes(start_str)
        approach_start = (start - minutes_before) % 1440
        if approach_start <= start:
            return approach_start <= current_minutes < start
        return current_minutes >= approach_start or current_minutes < start

    for period in solunar_data.get("majorPeriods", []):
        if _in_period(period["start"], period["end"]):
            return 1.0

    for period in solunar_data.get("majorPeriods", []):
        if _approaching(period["start"]):
            return 0.7

    for period in solunar_data.get("minorPeriods", []):
        if _in_period(period["start"], period["end"]):
            return 0.7

    moon_illumination = solunar_data.get("moonIllumination", 50)
    moon_bonus = (moon_illumination / 100) * 0.2
    return 0.3 + moon_bonus


# --- 5. Time Score (config-driven) ---

def time_score(
    hour: int,
    species_id: str,
    scoring_config: Optional[dict[str, Any]] = None,
) -> float:
    """Time parameter score (0.0-1.0).

    Reads best hours from scoring_config["speciesBestHours"] if available.
    """
    default_hours = [(5, 8), (16, 19)]

    if scoring_config and "speciesBestHours" in scoring_config:
        raw = scoring_config["speciesBestHours"].get(species_id, default_hours)
        best_hours = [tuple(h) for h in raw]
    else:
        best_hours = default_hours

    base = 0.3

    for start, end in best_hours:
        if start <= end:
            if start <= hour <= end:
                base = 1.0
                break
        else:
            if hour >= start or hour <= end:
                base = 1.0
                break

    if base < 1.0:
        for start, end in best_hours:
            if abs(hour - start) <= 1 or abs(hour - end) <= 1:
                base = max(base, 0.6)
                break

    return base


# --- Season Adjustment (v1.3 additive — NEVER zeros) ---

def compute_season_adjustment(
    species_id: str,
    month: int,
    weighted_sum: float,
    seasonality_config: Optional[dict[str, Any]] = None,
) -> tuple[int, str, float, bool]:
    """Compute additive season adjustment from seasonality.yaml.

    Returns:
        (adjustment, season_status, confidence_impact, is_parca)
        - adjustment: additive points (+12 peak, +5 shoulder, -25 off, etc.)
        - season_status: "peak" | "shoulder" | "active" | "off"
        - confidence_impact: how much to reduce confidence (0.0 = none)
        - is_parca: True if parça ihtimali triggered (off-season + good conditions)
    """
    if not seasonality_config or "species" not in seasonality_config:
        return (0, "active", 0.0, False)

    sp_cfg = seasonality_config["species"].get(species_id)
    if not sp_cfg:
        return (0, "active", 0.0, False)

    peak_months = sp_cfg.get("peakMonths", [])
    shoulder_months = sp_cfg.get("shoulderMonths", [])
    off_months = sp_cfg.get("offMonths", [])

    if month in peak_months:
        return (
            sp_cfg.get("peakAdjustment", 10),
            "peak",
            0.0,
            False,
        )

    if month in shoulder_months:
        return (
            sp_cfg.get("shoulderAdjustment", 3),
            "shoulder",
            sp_cfg.get("confidenceImpact", 0.0) * 0.3,  # slight
            False,
        )

    if month in off_months:
        off_adj = sp_cfg.get("offAdjustment", -20)
        conf_impact = sp_cfg.get("confidenceImpact", 0.2)
        is_parca = False

        # Parça ihtimali: if conditions are strongly favorable, reduce penalty
        parca = sp_cfg.get("parcaBehavior", {})
        threshold = parca.get("parcaConditionThreshold", 0.6)
        reduction = parca.get("parcaPenaltyReduction", 0.5)

        if weighted_sum >= threshold:
            off_adj = round(off_adj * (1.0 - reduction))
            is_parca = True
            conf_impact = max(conf_impact * 0.5, parca.get("parcaConfidence", 0.3))

        return (off_adj, "off", conf_impact, is_parca)

    # Month not in any list → treat as active (year-round with no explicit off)
    return (0, "active", 0.0, False)


# --- Backward-compat season_multiplier (deprecated) ---

def season_multiplier(species_id: str, month: int) -> float:
    """DEPRECATED: Returns 1.0 always. Kept for backward compat only.

    Use compute_season_adjustment() for the real v1.3 logic.
    """
    return 1.0


# --- Confidence Computation (config-driven) ---

def compute_confidence(
    data_quality: DataQuality,
    has_reports_24h: bool,
    season_status: str,
    season_confidence_impact: float = 0.0,
    scoring_config: Optional[dict[str, Any]] = None,
    coord_accuracy: str = "approx",
    fired_rules_count: int = 0,
) -> float:
    """Compute confidence score (0.0-1.0).

    Reads thresholds from scoring_config["confidenceFactors"] if available.
    NEVER returns 0.0 — minimum 0.1 even for off-season.
    """
    if scoring_config and "confidenceFactors" in scoring_config:
        cf = scoring_config["confidenceFactors"]
        base_map = cf.get("dataQualityBase", {})
        base = base_map.get(data_quality.value, 0.5)
        report_boost = cf.get("reportBoost", 0.10)
        approx_penalty = cf.get("approxCoordPenalty", 0.05)
        rules_threshold = cf.get("firedRulesThreshold", 6)
        rules_penalty_per = cf.get("firedRulesPenalty", 0.03)
        max_rules_penalty = cf.get("maxFiredRulesPenalty", 0.15)
        season_off_penalty = cf.get("seasonOffPenalty", 0.20)
        season_shoulder_penalty = cf.get("seasonShoulderPenalty", 0.05)
    else:
        # Fallback defaults
        base_map_default = {
            "live": 0.85, "cached": 0.65, "fallback": 0.45,
        }
        base = base_map_default.get(data_quality.value, 0.5)
        report_boost = 0.10
        approx_penalty = 0.05
        rules_threshold = 6
        rules_penalty_per = 0.03
        max_rules_penalty = 0.15
        season_off_penalty = 0.20
        season_shoulder_penalty = 0.05

    if has_reports_24h:
        base += report_boost

    if coord_accuracy == "approx":
        base -= approx_penalty

    # Fired rules penalty
    extra_rules = max(0, fired_rules_count - rules_threshold)
    if extra_rules > 0:
        base -= min(max_rules_penalty, extra_rules * rules_penalty_per)

    # Season penalty
    if season_status == "off":
        base -= season_off_penalty
    elif season_status == "shoulder":
        base -= season_shoulder_penalty

    # Apply explicit confidence_impact from seasonality config
    base -= season_confidence_impact

    # Clamp: never 0.0, minimum 0.1
    return round(max(0.1, min(1.0, base)), 2)


# --- Wind Exposure Adjustment ---
# TODO(v2): Integrate into wind_score() for spot-specific wind impact.
# Currently unused — wind_score() only uses global wind data.
# Config exists in scoring_config.yaml["windExposureAdjustments"].

def compute_wind_exposure_adjustment(
    spot: Any,
    wind_cardinal: str,
    scoring_config: Optional[dict[str, Any]] = None,
) -> float:
    """Compute wind exposure adjustment for a spot.

    Reads spot's wind_exposure_map and scoring_config["windExposureAdjustments"].

    NOTE: Currently not called in the scoring pipeline. Preserved for v2 integration.
    """
    if scoring_config is None:
        return 0.0

    wem = getattr(spot, "wind_exposure_map", None) or {}
    if not wem:
        return 0.0

    from app.utils.wind import normalize_cardinal_8
    norm_cardinal = normalize_cardinal_8(wind_cardinal)

    exposure = wem.get(norm_cardinal, "neutral")

    adjustments = scoring_config.get("windExposureAdjustments", {})
    return adjustments.get(exposure, 0.0)


# --- Water Mass Proxy ---

def compute_water_mass_proxy(
    wind_cardinal: str,
    wind_speed_kmh: float,
    scoring_config: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Compute water mass proxy (Lodos vs Poyraz) from wind data.

    Returns:
        {"type": "lodos"|"poyraz"|"neutral", "strength": 0.0-1.0}
    """
    if scoring_config is None or "waterMassProxy" not in scoring_config:
        return {"type": "neutral", "strength": 0.0}

    from app.utils.wind import normalize_cardinal_8
    norm = normalize_cardinal_8(wind_cardinal)

    wmp = scoring_config["waterMassProxy"]
    lodos_dirs = wmp.get("lodosDirections", ["SW", "S"])
    poyraz_dirs = wmp.get("poyrazDirections", ["NE", "N"])
    weak_threshold = wmp.get("weakThreshold", 10)
    strong_threshold = wmp.get("strongThreshold", 20)

    if norm in lodos_dirs:
        proxy_type = "lodos"
    elif norm in poyraz_dirs:
        proxy_type = "poyraz"
    else:
        return {"type": "neutral", "strength": 0.0}

    if wind_speed_kmh < weak_threshold:
        strength = 0.0
    elif wind_speed_kmh >= strong_threshold:
        strength = 1.0
    else:
        strength = (wind_speed_kmh - weak_threshold) / (strong_threshold - weak_threshold)

    return {"type": proxy_type, "strength": round(strength, 2)}


# --- Best Time Derivation ---

def derive_best_time(
    species_id: str,
    scoring_config: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """Derive best time string for species."""
    if scoring_config and "speciesBestHours" in scoring_config:
        raw = scoring_config["speciesBestHours"].get(species_id)
    else:
        raw = None

    if not raw:
        return None

    start, end = raw[0]
    return f"{start:02d}:00-{end:02d}:00"


# --- Final Score Calculation (v1.3) ---

def calculate_species_score(
    species_id: str,
    weather: Any,
    solunar_data: dict[str, Any],
    shore: str,
    rule_bonus: int,
    month: int,
    hour: int,
    minute: int,
    data_quality: DataQuality,
    has_reports_24h: bool,
    scoring_config: Optional[dict[str, Any]] = None,
    seasonality_config: Optional[dict[str, Any]] = None,
    coord_accuracy: str = "approx",
    fired_rules_count: int = 0,
) -> dict[str, Any]:
    """Calculate final species score with v1.3 additive seasonality.

    Formula (v1.3):
        score = clamp(0, 100, round(weighted_sum * 100 + season_adj) + capped_bonus)

    Returns dual-field breakdown for backward compat:
        seasonAdjustment (authoritative, new)
        seasonMultiplier (always 1.0, deprecated)
    """
    # Get weights from config
    if scoring_config and "speciesWeights" in scoring_config:
        weights = scoring_config["speciesWeights"].get(species_id)
    else:
        weights = None

    if not weights:
        return {"score": 0, "confidence": 0.1, "seasonStatus": "active",
                "bestTime": None, "breakdown": {}, "isParca": False}

    # Parameter scores
    p_score = pressure_score(weather.pressure_hpa, weather.pressure_change_3h_hpa)
    w_score = wind_score(weather.wind_speed_kmh, weather.wind_dir_deg, shore)
    st_score = sea_temp_score(weather.sea_temp_c, species_id, scoring_config)
    sol_score = solunar_score(hour, minute, solunar_data)
    t_score = time_score(hour, species_id, scoring_config)

    # Weighted sum (0.0-1.0)
    weighted_sum = (
        weights["pressure"] * p_score
        + weights["wind"] * w_score
        + weights["sea_temp"] * st_score
        + weights["solunar"] * sol_score
        + weights["time"] * t_score
    )

    # Season adjustment (additive, NEVER zeros)
    season_adj, season_status, conf_impact, is_parca = compute_season_adjustment(
        species_id, month, weighted_sum, seasonality_config
    )

    # Rule bonus — already capped by category in rules.py
    # Apply totalCap as final safety net
    if scoring_config and "ruleBonusCaps" in scoring_config:
        caps = scoring_config["ruleBonusCaps"]
        total_cap = caps.get("totalCap", 25)
        negative_floor = caps.get("negativeFloor", -20)
    else:
        total_cap = 30
        negative_floor = -20
    if rule_bonus > 0:
        capped_bonus = min(total_cap, rule_bonus)
    else:
        capped_bonus = max(negative_floor, rule_bonus)

    # Final score (v1.3 additive)
    raw_score = round(weighted_sum * 100 + season_adj) + capped_bonus
    final_score = max(0, min(100, raw_score))

    # offFloor enforcement: off-season species never below configured floor
    # This ensures "parca ihtimali" (stray fish) is always visible
    off_floor = 10  # default
    if season_status == "off" and seasonality_config and "species" in seasonality_config:
        sp_cfg = seasonality_config["species"].get(species_id, {})
        off_floor = sp_cfg.get("offFloor", 10)
        if final_score < off_floor:
            final_score = off_floor

    # Confidence
    confidence = compute_confidence(
        data_quality=data_quality,
        has_reports_24h=has_reports_24h,
        season_status=season_status,
        season_confidence_impact=conf_impact,
        scoring_config=scoring_config,
        coord_accuracy=coord_accuracy,
        fired_rules_count=fired_rules_count,
    )

    return {
        "score": final_score,
        "confidence": confidence,
        "seasonStatus": season_status,
        "bestTime": derive_best_time(species_id, scoring_config),
        "isParca": is_parca,
        "breakdown": {
            "pressure": round(p_score, 2),
            "wind": round(w_score, 2),
            "seaTemp": round(st_score, 2),
            "solunar": round(sol_score, 2),
            "time": round(t_score, 2),
            # v1.3 dual-field backward compat
            "seasonAdjustment": season_adj,
            "seasonMultiplier": 1.0,  # DEPRECATED — always 1.0
            "rulesBonus": capped_bonus,
        },
    }
