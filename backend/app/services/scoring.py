"""FishCast scoring service.

SCORING_ENGINE.md'deki TÜM formülleri implement eder:
- 5 parametre fonksiyonu (0.0-1.0)
- Tür-özel ağırlık tablosu
- Sezon çarpanı
- Final skor hesaplama (clamp + bonus cap +30)
- Confidence computation
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from app.models.enums import DataQuality, SpeciesId
from app.services.weather import MONTHLY_SEA_TEMP, deg_to_cardinal

logger = logging.getLogger(__name__)


# --- Tür-Özel Ağırlıklar (SCORING_ENGINE.md) ---
# Sıra: basınç, rüzgar, su_sıcaklığı, solunar, zaman

SPECIES_WEIGHTS: dict[str, dict[str, float]] = {
    "istavrit":  {"pressure": 0.15, "wind": 0.20, "sea_temp": 0.25, "solunar": 0.20, "time": 0.20},
    "cinekop":   {"pressure": 0.25, "wind": 0.20, "sea_temp": 0.15, "solunar": 0.20, "time": 0.20},
    "sarikanat": {"pressure": 0.25, "wind": 0.20, "sea_temp": 0.15, "solunar": 0.20, "time": 0.20},
    "palamut":   {"pressure": 0.20, "wind": 0.20, "sea_temp": 0.20, "solunar": 0.20, "time": 0.20},
    "karagoz":   {"pressure": 0.15, "wind": 0.15, "sea_temp": 0.20, "solunar": 0.25, "time": 0.25},
}

# --- Tür-Özel Su Sıcaklığı Aralıkları (SCORING_ENGINE.md) ---

SPECIES_TEMP: dict[str, dict[str, float]] = {
    "istavrit":  {"min": 10, "max": 22, "pen": 20},
    "cinekop":   {"min": 12, "max": 20, "pen": 20},
    "sarikanat": {"min": 12, "max": 20, "pen": 20},
    "palamut":   {"min": 14, "max": 22, "pen": 20},
    "karagoz":   {"min": 10, "max": 26, "pen": 10},
}

# --- Sezon Tanımları ---

SPECIES_SEASON: dict[str, dict[str, list[int]]] = {
    "istavrit":  {"months": list(range(1, 13)), "peak": [9, 10, 11]},
    "cinekop":   {"months": [9, 10, 11, 12], "peak": [10, 11]},
    "sarikanat": {"months": [9, 10, 11, 12], "peak": [10, 11]},
    "palamut":   {"months": [8, 9, 10, 11], "peak": [9, 10]},
    "karagoz":   {"months": list(range(1, 13)), "peak": [4, 5, 10, 11]},
}

# --- Tür-Özel En İyi Saatler ---

SPECIES_BEST_HOURS: dict[str, list[tuple[int, int]]] = {
    "istavrit":  [(5, 8), (16, 19)],
    "cinekop":   [(16, 20)],
    "sarikanat": [(16, 20)],
    "palamut":   [(5, 9), (16, 19)],
    "karagoz":   [(20, 23), (0, 5)],  # gece aktif
}


# --- 1. Basınç Skoru (SCORING_ENGINE.md § Basınç) ---

def pressure_score(hpa: float, change_3h: float) -> float:
    """Basınç parametresi skoru (0.0-1.0).

    Args:
        hpa: Hava basıncı (hPa).
        change_3h: 3 saatlik basınç değişimi (hPa).

    Returns:
        Basınç skoru (0.0-1.0).
    """
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


# --- 2. Rüzgar Skoru (SCORING_ENGINE.md § Rüzgar) ---

def wind_score(kmh: float, dir_deg: int, shore: str) -> float:
    """Rüzgar parametresi skoru (0.0-1.0).

    Args:
        kmh: Rüzgar hızı (km/h).
        dir_deg: Rüzgar yönü (derece).
        shore: Kıyı yakası ("european" veya "anatolian").

    Returns:
        Rüzgar skoru (0.0-1.0).
    """
    if kmh < 5:
        base = 0.65
    elif kmh <= 15:
        base = 0.90
    elif kmh <= 25:
        base = 0.75
    elif kmh <= 35:
        base = 0.40
    else:
        return 0.0  # NO-GO via rule engine

    cardinal = deg_to_cardinal(dir_deg)
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


# --- 3. Su Sıcaklığı Skoru (SCORING_ENGINE.md § Su Sıcaklığı) ---

def sea_temp_score(temp_c: Optional[float], species_id: str) -> float:
    """Su sıcaklığı parametresi skoru (0.0-1.0).

    Args:
        temp_c: Su sıcaklığı (°C). None ise aylık ortalama kullanılır.
        species_id: Tür kimliği.

    Returns:
        Su sıcaklığı skoru (0.0-1.0).
    """
    if species_id not in SPECIES_TEMP:
        return 0.5

    spec = SPECIES_TEMP[species_id]

    if temp_c is None:
        temp_c = MONTHLY_SEA_TEMP.get(datetime.now().month, 15.0)

    if spec["min"] <= temp_c <= spec["max"]:
        # İdeal aralıkta — mesafeye göre skor
        mid = (spec["min"] + spec["max"]) / 2
        half_range = (spec["max"] - spec["min"]) / 2
        if half_range == 0:
            return 1.0
        distance = abs(temp_c - mid) / half_range
        return max(0.5, 1.0 - distance * 0.3)
    else:
        # Aralık dışı — penalty
        if temp_c < spec["min"]:
            diff = spec["min"] - temp_c
        else:
            diff = temp_c - spec["max"]
        penalty = diff / spec["pen"]
        return max(0.0, 0.5 - penalty)


# --- 4. Solunar Skoru (SCORING_ENGINE.md § Solunar) ---

def solunar_score(current_hour: int, current_minute: int, solunar_data: dict[str, Any]) -> float:
    """Solunar parametresi skoru (0.0-1.0).

    Major period=1.0, approaching major=0.7, minor period=0.7,
    outside=0.3+moon_bonus.

    Args:
        current_hour: Mevcut saat (0-23).
        current_minute: Mevcut dakika (0-59).
        solunar_data: Solunar verisi (majorPeriods, minorPeriods, moonIllumination).

    Returns:
        Solunar skoru (0.0-1.0).
    """
    current_minutes = current_hour * 60 + current_minute

    def _time_to_minutes(time_str: str) -> int:
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])

    def _in_period(start_str: str, end_str: str) -> bool:
        start = _time_to_minutes(start_str)
        end = _time_to_minutes(end_str)
        if start <= end:
            return start <= current_minutes <= end
        # Wraps midnight
        return current_minutes >= start or current_minutes <= end

    def _approaching(start_str: str, minutes_before: int = 60) -> bool:
        start = _time_to_minutes(start_str)
        approach_start = (start - minutes_before) % 1440
        if approach_start <= start:
            return approach_start <= current_minutes < start
        return current_minutes >= approach_start or current_minutes < start

    # Check major periods
    for period in solunar_data.get("majorPeriods", []):
        if _in_period(period["start"], period["end"]):
            return 1.0

    # Check approaching major
    for period in solunar_data.get("majorPeriods", []):
        if _approaching(period["start"]):
            return 0.7

    # Check minor periods
    for period in solunar_data.get("minorPeriods", []):
        if _in_period(period["start"], period["end"]):
            return 0.7

    # Outside any period
    moon_illumination = solunar_data.get("moonIllumination", 50)
    moon_bonus = (moon_illumination / 100) * 0.2
    return 0.3 + moon_bonus


# --- 5. Zaman Skoru (SCORING_ENGINE.md § Zaman) ---

def time_score(hour: int, species_id: str) -> float:
    """Zaman parametresi skoru (0.0-1.0).

    Tür-özel en iyi saatler. Gece bonusu: karagöz +0.3.

    Args:
        hour: Mevcut saat (0-23).
        species_id: Tür kimliği.

    Returns:
        Zaman skoru (0.0-1.0).
    """
    best_hours = SPECIES_BEST_HOURS.get(species_id, [(5, 8), (16, 19)])
    base = 0.3  # default outside best hours

    for start, end in best_hours:
        if start <= end:
            if start <= hour <= end:
                base = 1.0
                break
        else:
            # Wraps midnight (e.g., 20-5)
            if hour >= start or hour <= end:
                base = 1.0
                break

    # Transition bonus: 1 hour before/after best hours
    if base < 1.0:
        for start, end in best_hours:
            if abs(hour - start) <= 1 or abs(hour - end) <= 1:
                base = max(base, 0.6)
                break

    return base


# --- Sezon Çarpanı ---

def season_multiplier(species_id: str, month: int) -> float:
    """Sezon çarpanı: out_of_season=0.0, in_season=1.0, peak=1.2.

    Args:
        species_id: Tür kimliği.
        month: Ay (1-12).

    Returns:
        Sezon çarpanı (0.0, 1.0, veya 1.2).
    """
    season = SPECIES_SEASON.get(species_id)
    if not season:
        return 1.0

    if month not in season["months"]:
        return 0.0
    if month in season["peak"]:
        return 1.2
    return 1.0


# --- Confidence Computation (SCORING_ENGINE.md § Confidence) ---

def compute_confidence(
    data_quality: DataQuality,
    has_reports_24h: bool,
    season_mult: float,
) -> float:
    """Confidence hesaplar.

    Args:
        data_quality: Veri kalitesi (live/cached/fallback).
        has_reports_24h: Son 24h'te rapor var mı.
        season_mult: Sezon çarpanı.

    Returns:
        Confidence değeri (0.0-1.0).
    """
    base_map = {
        DataQuality.live: 0.9,
        DataQuality.cached: 0.7,
        DataQuality.fallback: 0.5,
    }
    base = base_map.get(data_quality, 0.5)

    if has_reports_24h:
        base = min(1.0, base + 0.1)

    if season_mult == 0:
        return 0.0
    if season_mult < 1.0:
        base *= 0.9

    return round(base, 2)


# --- Best Time Derivation ---

def derive_best_time(species_id: str) -> Optional[str]:
    """Tür için en iyi zaman aralığını string olarak döner.

    Args:
        species_id: Tür kimliği.

    Returns:
        "HH:MM-HH:MM" formatında string veya None.
    """
    best_hours = SPECIES_BEST_HOURS.get(species_id)
    if not best_hours:
        return None

    # En yüksek öncelikli pencereyi döner
    start, end = best_hours[0]
    return f"{start:02d}:00-{end:02d}:00"


# --- Final Skor Hesaplama ---

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
) -> dict[str, Any]:
    """Tek bir tür için final skor hesaplar.

    Formül (SCORING_ENGINE.md):
        TürSkoru = clamp(0, 100,
            round(Σ(ağırlık_i × param_skor_i) × 100 × sezon_çarpanı)
            + min(30, Σ(kural_bonusu))
        )

    Args:
        species_id: Tür kimliği.
        weather: WeatherData objesi.
        solunar_data: Solunar verisi dict.
        shore: Kıyı yakası.
        rule_bonus: Kurallardan gelen bonus (cap'lenmemiş).
        month: Ay (1-12).
        hour: Saat (0-23).
        minute: Dakika (0-59).
        data_quality: Veri kalitesi.
        has_reports_24h: Son 24h'te rapor var mı.

    Returns:
        Skor detay dict'i.
    """
    weights = SPECIES_WEIGHTS.get(species_id)
    if not weights:
        return {"score": 0, "breakdown": {}}

    # Parametre skorları
    p_score = pressure_score(weather.pressure_hpa, weather.pressure_change_3h_hpa)
    w_score = wind_score(weather.wind_speed_kmh, weather.wind_dir_deg, shore)
    st_score = sea_temp_score(weather.sea_temp_c, species_id)
    sol_score = solunar_score(hour, minute, solunar_data)
    t_score = time_score(hour, species_id)

    # Weighted sum
    weighted_sum = (
        weights["pressure"] * p_score
        + weights["wind"] * w_score
        + weights["sea_temp"] * st_score
        + weights["solunar"] * sol_score
        + weights["time"] * t_score
    )

    # Sezon çarpanı
    s_mult = season_multiplier(species_id, month)

    # Rule bonus cap: +30 max, negatifler cap'lenmez
    capped_bonus = min(30, rule_bonus) if rule_bonus > 0 else rule_bonus

    # Final skor
    raw_score = round(weighted_sum * 100 * s_mult) + capped_bonus
    final_score = max(0, min(100, raw_score))

    # Confidence
    confidence = compute_confidence(data_quality, has_reports_24h, s_mult)

    # Season status
    if s_mult == 0:
        season_status = "closed"
    elif s_mult >= 1.2:
        season_status = "peak"
    else:
        season_status = "active"

    return {
        "score": final_score,
        "confidence": confidence,
        "seasonStatus": season_status,
        "seasonMultiplier": s_mult,
        "bestTime": derive_best_time(species_id),
        "breakdown": {
            "pressure": round(p_score, 2),
            "wind": round(w_score, 2),
            "seaTemp": round(st_score, 2),
            "solunar": round(sol_score, 2),
            "time": round(t_score, 2),
            "seasonMultiplier": s_mult,
            "rulesBonus": capped_bonus,
        },
    }
