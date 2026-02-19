"""FishCast solunar service.

ephem kütüphanesiyle ay fazı, major/minor periyotlar ve solunar rating hesaplar.
Istanbul koordinatları: lat=41.01, lng=28.98.
ARRAY formatı zorunlu: majorPeriods[], minorPeriods[].
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

ISTANBUL_LAT = 41.01
ISTANBUL_LNG = 28.98

# Moon phase names
MOON_PHASES = [
    "new_moon", "waxing_crescent", "first_quarter", "waxing_gibbous",
    "full_moon", "waning_gibbous", "last_quarter", "waning_crescent",
]


def _time_str(dt: datetime) -> str:
    """datetime'ı HH:MM string formatına çevirir.

    Args:
        dt: datetime objesi.

    Returns:
        "HH:MM" formatında string.
    """
    return dt.strftime("%H:%M")


def _compute_moon_phase_name(illumination: float, is_waxing: bool) -> str:
    """Ay illumination ve büyüme/küçülme durumundan faz adı döner.

    Args:
        illumination: Ay aydınlanma yüzdesi (0-100).
        is_waxing: Ay büyüyor mu.

    Returns:
        Moon phase string.
    """
    if illumination < 5:
        return "new_moon"
    elif illumination > 95:
        return "full_moon"
    elif is_waxing:
        if illumination < 35:
            return "waxing_crescent"
        elif illumination < 65:
            return "first_quarter"
        else:
            return "waxing_gibbous"
    else:
        if illumination < 35:
            return "waning_crescent"
        elif illumination < 65:
            return "last_quarter"
        else:
            return "waning_gibbous"


def compute_solunar(
    date: Optional[datetime] = None,
    lat: float = ISTANBUL_LAT,
    lng: float = ISTANBUL_LNG,
) -> dict[str, Any]:
    """Solunar verilerini hesaplar.

    ephem kütüphanesiyle ay transit/antitransit zamanlarını hesaplar,
    major (transit/antitransit ±1h) ve minor (rise/set ±30min) periyotları üretir.

    Args:
        date: Hesaplama tarihi. None ise bugün.
        lat: Enlem.
        lng: Boylam.

    Returns:
        dict: majorPeriods[], minorPeriods[], moonPhase, moonIllumination, solunarRating.
    """
    try:
        import ephem
    except ImportError:
        logger.warning("ephem kütüphanesi yüklü değil — varsayılan solunar verisi döndürülüyor")
        return _default_solunar()

    if date is None:
        date = datetime.now(tz=timezone.utc)

    try:
        observer = ephem.Observer()
        observer.lat = str(lat)
        observer.lon = str(lng)
        observer.elevation = 0
        observer.date = ephem.Date(date)

        moon = ephem.Moon()
        moon.compute(observer)

        # Moon illumination (0-100)
        moon_illumination = round(moon.phase, 1)

        # Determine waxing/waning
        tomorrow_observer = ephem.Observer()
        tomorrow_observer.lat = str(lat)
        tomorrow_observer.lon = str(lng)
        tomorrow_observer.date = ephem.Date(date + timedelta(days=1))
        moon_tomorrow = ephem.Moon()
        moon_tomorrow.compute(tomorrow_observer)
        is_waxing = moon_tomorrow.phase > moon.phase

        moon_phase = _compute_moon_phase_name(moon_illumination, is_waxing)

        # Moon rise/set/transit times for major/minor periods
        major_periods: list[dict[str, str]] = []
        minor_periods: list[dict[str, str]] = []

        # Set observer to midnight local (Istanbul UTC+3)
        local_midnight = date.replace(hour=0, minute=0, second=0, microsecond=0)
        if local_midnight.tzinfo is None:
            local_midnight = local_midnight.replace(tzinfo=timezone.utc)
        observer.date = ephem.Date(local_midnight)

        try:
            # Moon transit (culmination) — major period
            transit = observer.next_transit(ephem.Moon())
            transit_dt = ephem.Date(transit).datetime().replace(tzinfo=timezone.utc)
            # Istanbul UTC+3 offset
            transit_local = transit_dt + timedelta(hours=3)
            major_periods.append({
                "start": _time_str(transit_local - timedelta(hours=1)),
                "end": _time_str(transit_local + timedelta(hours=1)),
            })
        except Exception:
            pass

        try:
            # Moon anti-transit (opposite) — major period
            anti_transit = observer.next_antitransit(ephem.Moon())
            anti_dt = ephem.Date(anti_transit).datetime().replace(tzinfo=timezone.utc)
            anti_local = anti_dt + timedelta(hours=3)
            major_periods.append({
                "start": _time_str(anti_local - timedelta(hours=1)),
                "end": _time_str(anti_local + timedelta(hours=1)),
            })
        except Exception:
            pass

        try:
            # Moon rise — minor period
            rise = observer.next_rising(ephem.Moon())
            rise_dt = ephem.Date(rise).datetime().replace(tzinfo=timezone.utc)
            rise_local = rise_dt + timedelta(hours=3)
            minor_periods.append({
                "start": _time_str(rise_local - timedelta(minutes=30)),
                "end": _time_str(rise_local + timedelta(minutes=30)),
            })
        except ephem.NeverUpError:
            pass
        except Exception:
            pass

        try:
            # Moon set — minor period
            setting = observer.next_setting(ephem.Moon())
            set_dt = ephem.Date(setting).datetime().replace(tzinfo=timezone.utc)
            set_local = set_dt + timedelta(hours=3)
            minor_periods.append({
                "start": _time_str(set_local - timedelta(minutes=30)),
                "end": _time_str(set_local + timedelta(minutes=30)),
            })
        except ephem.NeverUpError:
            pass
        except Exception:
            pass

        # Solunar rating (0-1)
        # Based on moon illumination and number of active periods
        base_rating = 0.3
        # Full/new moon boost
        if moon_illumination > 90 or moon_illumination < 10:
            base_rating += 0.3
        elif moon_illumination > 40 and moon_illumination < 60:
            base_rating += 0.15
        # Period count bonus
        total_periods = len(major_periods) + len(minor_periods)
        base_rating += min(0.3, total_periods * 0.1)
        solunar_rating = round(min(1.0, base_rating), 2)

        return {
            "majorPeriods": major_periods,
            "minorPeriods": minor_periods,
            "moonPhase": moon_phase,
            "moonIllumination": moon_illumination,
            "solunarRating": solunar_rating,
        }

    except Exception as e:
        logger.error("Solunar hesaplama hatası: %s", e)
        return _default_solunar()


def _default_solunar() -> dict[str, Any]:
    """ephem olmadığında veya hata durumunda varsayılan solunar verisi.

    Returns:
        Default solunar dict.
    """
    return {
        "majorPeriods": [
            {"start": "06:00", "end": "08:00"},
            {"start": "18:00", "end": "20:00"},
        ],
        "minorPeriods": [
            {"start": "12:00", "end": "13:00"},
            {"start": "00:00", "end": "01:00"},
        ],
        "moonPhase": "waxing_crescent",
        "moonIllumination": 35.0,
        "solunarRating": 0.5,
    }
