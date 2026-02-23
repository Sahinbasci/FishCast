"""FishCast weather service.

Open-Meteo (hava) ve Stormglass (su) verilerini toplar, normalize eder.
Fallback: Stormglass fail → Firestore cache → MONTHLY_SEA_TEMP.
dataQuality derivation: live/cached/fallback.

Units Table (INSTRUCTIONS.md):
    windSpeedKmh (km/h), windDirDeg (0-359°), pressureHpa (hPa),
    airTempC (°C), seaTempC (°C), waveHeightM (m), cloudCoverPct (0-100%).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

import httpx

from app.models.enums import DataQuality, PressureTrend, WindCardinal
from app.utils.wind import degrees_to_cardinal_8

logger = logging.getLogger(__name__)

# --- Constants ---

ISTANBUL_LAT = 41.01
ISTANBUL_LNG = 28.98

# In-memory LRU cache for weather responses (avoids hammering external APIs)
# OrderedDict for O(1) eviction, asyncio.Lock for concurrency safety
_weather_cache: OrderedDict[str, tuple[float, "WeatherData"]] = OrderedDict()
_CACHE_TTL_SECONDS = 600  # 10 minutes
_MAX_CACHE_SIZE = 50  # Max entries; evict LRU when exceeded
_cache_lock = asyncio.Lock()


async def _cache_get(key: str) -> "WeatherData | None":
    """Thread-safe LRU cache read with TTL check.

    On hit: moves entry to end (most-recently-used).
    On miss or expired: returns None.
    """
    now_ts = time.monotonic()
    async with _cache_lock:
        if key not in _weather_cache:
            return None
        cached_ts, cached_data = _weather_cache[key]
        if now_ts - cached_ts >= _CACHE_TTL_SECONDS:
            # Expired — remove
            del _weather_cache[key]
            return None
        # Hit — move to end (most recently used)
        _weather_cache.move_to_end(key)
        return cached_data


async def _cache_put(key: str, data: "WeatherData") -> None:
    """Thread-safe LRU cache write with bounded size.

    If cache exceeds MAX_CACHE_SIZE, evicts least-recently-used (first) entry.
    """
    now_ts = time.monotonic()
    async with _cache_lock:
        # If key already exists, update and move to end
        if key in _weather_cache:
            _weather_cache[key] = (now_ts, data)
            _weather_cache.move_to_end(key)
        else:
            _weather_cache[key] = (now_ts, data)
        # Evict LRU entries (first in OrderedDict) if over limit
        while len(_weather_cache) > _MAX_CACHE_SIZE:
            _weather_cache.popitem(last=False)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
STORMGLASS_URL = "https://api.stormglass.io/v2/weather/point"

# SCORING_ENGINE.md § Su Sıcaklığı — aylık ortalama fallback
MONTHLY_SEA_TEMP: dict[int, float] = {
    1: 9.0, 2: 8.0, 3: 9.0, 4: 11.0, 5: 15.0, 6: 20.0,
    7: 24.0, 8: 25.0, 9: 23.0, 10: 19.0, 11: 15.0, 12: 11.0,
}

# INSTRUCTIONS.md § Wind Direction Derivation
_CARDINAL_DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
CARDINAL_TO_TR: dict[str, str] = {
    "N": "yıldız", "NE": "poyraz", "E": "gün_doğusu", "SE": "kıble",
    "S": "keşişleme", "SW": "lodos", "W": "gün_batısı", "NW": "karayel",
}


# --- Wind Direction ---

def deg_to_cardinal(deg: float) -> str:
    """Derece cinsinden rüzgar yönünü 8-yön kardinale çevirir.

    Delegates to canonical utils.wind.degrees_to_cardinal_8.

    Args:
        deg: Rüzgar yönü (0-359 derece).

    Returns:
        Kardinal yön string'i (N, NE, E, SE, S, SW, W, NW).
    """
    return degrees_to_cardinal_8(deg)


def cardinal_to_tr(cardinal: str) -> str:
    """Kardinal yönü Türkçe rüzgar adına çevirir.

    Args:
        cardinal: Kardinal yön (N, NE, etc.).

    Returns:
        Türkçe rüzgar adı (poyraz, lodos, etc.).
    """
    return CARDINAL_TO_TR.get(cardinal, cardinal)


# --- Pressure Trend ---

def derive_pressure_trend(change_3h_hpa: float) -> PressureTrend:
    """3 saatlik basınç değişiminden trend derive eder.

    Args:
        change_3h_hpa: 3 saatlik basınç değişimi (hPa).

    Returns:
        PressureTrend enum.
    """
    if change_3h_hpa < -0.5:
        return PressureTrend.falling
    elif change_3h_hpa > 0.5:
        return PressureTrend.rising
    return PressureTrend.stable


ISTANBUL_TZ = ZoneInfo("Europe/Istanbul")


def _compute_pressure_change_3h(
    pressure_hourly: list[float | None],
    now: datetime | None = None,
) -> float:
    """Compute 3-hour pressure change from Istanbul-local-indexed hourly data.

    Open-Meteo returns hourly arrays indexed by the timezone requested
    (Europe/Istanbul). We MUST use Istanbul local hour for correct indexing.

    Args:
        pressure_hourly: Hourly pressure values indexed 0-23 by Istanbul local time.
        now: Current datetime (for testing). Defaults to now in Istanbul TZ.

    Returns:
        Pressure change over last 3 hours (hPa). 0.0 if data insufficient.
    """
    if len(pressure_hourly) < 4:
        return 0.0

    if now is None:
        now = datetime.now(tz=ISTANBUL_TZ)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc).astimezone(ISTANBUL_TZ)
    else:
        now = now.astimezone(ISTANBUL_TZ)

    istanbul_hour = now.hour
    now_idx = min(istanbul_hour, len(pressure_hourly) - 1)
    past_idx = max(0, now_idx - 3)

    if pressure_hourly[now_idx] is not None and pressure_hourly[past_idx] is not None:
        return pressure_hourly[now_idx] - pressure_hourly[past_idx]
    return 0.0


# --- Weather Data Model ---

class WeatherData:
    """Normalize edilmiş hava ve su verisi.

    Tüm field'lar INSTRUCTIONS.md Units Table'a uygun birimlerle.
    """

    def __init__(
        self,
        wind_speed_kmh: float,
        wind_dir_deg: int,
        pressure_hpa: float,
        pressure_change_3h_hpa: float,
        air_temp_c: float,
        cloud_cover_pct: float,
        sea_temp_c: Optional[float],
        wave_height_m: Optional[float],
        data_quality: DataQuality,
        data_issues: list[str],
    ):
        self.wind_speed_kmh = wind_speed_kmh
        self.wind_dir_deg = wind_dir_deg
        self.wind_direction_cardinal = deg_to_cardinal(wind_dir_deg)
        self.wind_direction_tr = cardinal_to_tr(self.wind_direction_cardinal)
        self.pressure_hpa = pressure_hpa
        self.pressure_change_3h_hpa = pressure_change_3h_hpa
        self.pressure_trend = derive_pressure_trend(pressure_change_3h_hpa)
        self.air_temp_c = air_temp_c
        self.cloud_cover_pct = cloud_cover_pct
        self.sea_temp_c = sea_temp_c
        self.wave_height_m = wave_height_m
        self.data_quality = data_quality
        self.data_issues = data_issues

    def to_dict(self) -> dict[str, Any]:
        """Firestore/API serialization için dict döner."""
        return {
            "windSpeedKmh": round(self.wind_speed_kmh, 1),
            "windDirDeg": self.wind_dir_deg,
            "windDirectionCardinal": self.wind_direction_cardinal,
            "windDirectionTR": self.wind_direction_tr,
            "pressureHpa": round(self.pressure_hpa, 1),
            "pressureChange3hHpa": round(self.pressure_change_3h_hpa, 1),
            "pressureTrend": self.pressure_trend.value,
            "airTempC": round(self.air_temp_c, 1),
            "seaTempC": round(self.sea_temp_c, 1) if self.sea_temp_c is not None else None,
            "waveHeightM": round(self.wave_height_m, 2) if self.wave_height_m is not None else None,
            "cloudCoverPct": round(self.cloud_cover_pct, 0),
        }


# --- Open-Meteo Fetch ---

async def fetch_open_meteo(
    lat: float = ISTANBUL_LAT,
    lng: float = ISTANBUL_LNG,
) -> Optional[dict[str, Any]]:
    """Open-Meteo API'den hava verisi çeker.

    Args:
        lat: Enlem.
        lng: Boylam.

    Returns:
        Normalize edilmiş hava verisi dict veya None (hata durumunda).
    """
    params = {
        "latitude": lat,
        "longitude": lng,
        "current": "temperature_2m,wind_speed_10m,wind_direction_10m,surface_pressure,cloud_cover",
        "hourly": "surface_pressure",
        "timezone": "Europe/Istanbul",
        "forecast_days": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        current = data.get("current", {})
        hourly = data.get("hourly", {})

        wind_speed_kmh = current.get("wind_speed_10m", 0)
        wind_dir_deg = int(current.get("wind_direction_10m", 0))
        pressure_hpa = current.get("surface_pressure", 1013)
        air_temp_c = current.get("temperature_2m", 15)
        cloud_cover_pct = current.get("cloud_cover", 50)

        # pressureChange3hHpa: son 3 saatlik fark
        # Open-Meteo returns hourly data indexed by Istanbul local time
        # (timezone param = "Europe/Istanbul"), so we must use Istanbul hour.
        pressure_change_3h_hpa = _compute_pressure_change_3h(
            hourly.get("surface_pressure", [])
        )

        return {
            "windSpeedKmh": wind_speed_kmh,
            "windDirDeg": wind_dir_deg,
            "pressureHpa": pressure_hpa,
            "pressureChange3hHpa": pressure_change_3h_hpa,
            "airTempC": air_temp_c,
            "cloudCoverPct": cloud_cover_pct,
            "status": "ok",
        }
    except Exception as e:
        logger.error("Open-Meteo fetch hatası: %s", e)
        return None


# --- Stormglass Fetch ---

async def fetch_stormglass(
    api_key: Optional[str] = None,
    lat: float = ISTANBUL_LAT,
    lng: float = ISTANBUL_LNG,
) -> Optional[dict[str, Any]]:
    """Stormglass API'den su verisi çeker.

    Args:
        api_key: Stormglass API key.
        lat: Enlem.
        lng: Boylam.

    Returns:
        Su verisi dict veya None (hata veya key yoksa).
    """
    if not api_key:
        logger.warning("Stormglass API key yok, fallback kullanılacak")
        return None

    params = {
        "lat": lat,
        "lng": lng,
        "params": "waterTemperature,waveHeight",
    }
    headers = {"Authorization": api_key}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(STORMGLASS_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        hours = data.get("hours", [])
        if not hours:
            return None

        latest = hours[0]
        sea_temp = latest.get("waterTemperature", {}).get("sg")
        wave_height = latest.get("waveHeight", {}).get("sg")

        return {
            "seaTempC": sea_temp,
            "waveHeightM": wave_height,
            "status": "ok",
        }
    except Exception as e:
        logger.error("Stormglass fetch hatası: %s", e)
        return None


# --- Stormglass Cache (Firestore) ---

async def get_cached_stormglass(db: Any) -> Optional[dict[str, Any]]:
    """Firestore'dan Stormglass cache okur (3h TTL).

    Args:
        db: Firestore client.

    Returns:
        Cache'lenmiş su verisi veya None (expired/yok).
    """
    if db is None:
        return None
    try:
        doc_ref = db.collection("cache").document("stormglass_latest")
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            updated_at = data.get("updatedAt")
            if updated_at:
                from datetime import timedelta
                age = datetime.now(tz=timezone.utc) - updated_at
                if age < timedelta(hours=3):
                    return {
                        "seaTempC": data.get("seaTempC"),
                        "waveHeightM": data.get("waveHeightM"),
                        "status": "cached",
                    }
    except Exception as e:
        logger.error("Stormglass cache okuma hatası: %s", e)
    return None


async def set_stormglass_cache(db: Any, sea_temp_c: float, wave_height_m: Optional[float]) -> None:
    """Stormglass verisini Firestore'a cache'ler.

    Args:
        db: Firestore client.
        sea_temp_c: Su sıcaklığı (°C).
        wave_height_m: Dalga yüksekliği (m).
    """
    if db is None:
        return
    try:
        doc_ref = db.collection("cache").document("stormglass_latest")
        doc_ref.set({
            "seaTempC": sea_temp_c,
            "waveHeightM": wave_height_m,
            "updatedAt": datetime.now(tz=timezone.utc),
        })
    except Exception as e:
        logger.error("Stormglass cache yazma hatası: %s", e)


# --- Offline Fixture ---

def _offline_weather() -> WeatherData:
    """Returns deterministic fixture weather data for OFFLINE_MODE.

    Zero external API calls. Used by smoke tests and CI.
    """
    month = datetime.now().month
    return WeatherData(
        wind_speed_kmh=10.0,
        wind_dir_deg=45,
        pressure_hpa=1015.0,
        pressure_change_3h_hpa=-0.5,
        air_temp_c=15.0,
        cloud_cover_pct=40.0,
        sea_temp_c=MONTHLY_SEA_TEMP[month],
        wave_height_m=0.3,
        data_quality=DataQuality.fallback,
        data_issues=["OFFLINE_MODE: fixture verisi kullaniliyor"],
    )


# --- Composite Weather Fetch ---

async def get_weather(
    stormglass_api_key: Optional[str] = None,
    firestore_db: Any = None,
    lat: float = ISTANBUL_LAT,
    lng: float = ISTANBUL_LNG,
    offline_mode: bool = False,
) -> WeatherData:
    """Tum hava ve su verilerini toplar, normalize eder.

    Provider priority:
        1. Open-Meteo (hava) — fail durumunda default values
        2. Stormglass (su) — fail -> Firestore cache -> MONTHLY_SEA_TEMP fallback

    Args:
        stormglass_api_key: Stormglass API key (opsiyonel).
        firestore_db: Firestore client (cache icin, opsiyonel).
        lat: Enlem.
        lng: Boylam.
        offline_mode: True ise external API cagrilmaz (fixture doner).

    Returns:
        WeatherData: Normalize edilmis hava verisi. ASLA None donmez.
    """
    # OFFLINE_MODE: return fixture, zero external calls
    if offline_mode:
        logger.info("OFFLINE_MODE: fixture weather verisi kullaniliyor")
        return _offline_weather()

    # In-memory LRU cache check
    cache_key = f"{lat:.2f}_{lng:.2f}"
    cached_data = await _cache_get(cache_key)
    if cached_data is not None:
        logger.info("Weather cache hit: %s", cache_key)
        return cached_data

    data_issues: list[str] = []
    quality_flags: list[str] = []

    # --- Open-Meteo ---
    meteo = await fetch_open_meteo(lat, lng)
    if meteo is None:
        # Fallback: default values
        meteo = {
            "windSpeedKmh": 10.0,
            "windDirDeg": 0,
            "pressureHpa": 1013.0,
            "pressureChange3hHpa": 0.0,
            "airTempC": 15.0,
            "cloudCoverPct": 50.0,
            "status": "fallback",
        }
        data_issues.append("Hava verisi alinamadi — varsayilan degerler kullaniliyor")
        quality_flags.append("fallback")
    else:
        quality_flags.append("live")

    # --- Stormglass ---
    sea_data = await fetch_stormglass(stormglass_api_key, lat, lng)
    sea_temp_c: Optional[float] = None
    wave_height_m: Optional[float] = None

    if sea_data and sea_data.get("seaTempC") is not None:
        # Live data
        sea_temp_c = sea_data["seaTempC"]
        wave_height_m = sea_data.get("waveHeightM")
        quality_flags.append("live")
        # Cache for future
        await set_stormglass_cache(firestore_db, sea_temp_c, wave_height_m)
    else:
        # Try Firestore cache
        cached = await get_cached_stormglass(firestore_db)
        if cached and cached.get("seaTempC") is not None:
            sea_temp_c = cached["seaTempC"]
            wave_height_m = cached.get("waveHeightM")
            data_issues.append("Su sicakligi: cache'ten (Stormglass gecici olarak erisilemez)")
            quality_flags.append("cached")
        else:
            # MONTHLY_SEA_TEMP fallback
            month = datetime.now().month
            sea_temp_c = MONTHLY_SEA_TEMP[month]
            wave_height_m = None
            data_issues.append(
                f"Su sicakligi: aylik ortalama ({sea_temp_c}C) kullaniliyor — "
                "Stormglass verisi alinamadi"
            )
            quality_flags.append("fallback")

    # --- dataQuality derivation ---
    if "fallback" in quality_flags:
        data_quality = DataQuality.fallback
    elif "cached" in quality_flags:
        data_quality = DataQuality.cached
    else:
        data_quality = DataQuality.live

    result = WeatherData(
        wind_speed_kmh=meteo["windSpeedKmh"],
        wind_dir_deg=meteo["windDirDeg"],
        pressure_hpa=meteo["pressureHpa"],
        pressure_change_3h_hpa=meteo["pressureChange3hHpa"],
        air_temp_c=meteo["airTempC"],
        cloud_cover_pct=meteo["cloudCoverPct"],
        sea_temp_c=sea_temp_c,
        wave_height_m=wave_height_m,
        data_quality=data_quality,
        data_issues=data_issues,
    )

    # Store in LRU cache (bounded, thread-safe)
    await _cache_put(cache_key, result)

    return result
