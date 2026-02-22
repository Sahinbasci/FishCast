"""FishCast wind direction normalization utility.

Single canonical normalization point for all wind direction handling.
Converts degrees → 8-cardinal and normalizes 16-point → 8-cardinal.
"""

from __future__ import annotations

# Canonical 8-cardinal set (clockwise from N)
CARDINAL_8 = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")

# 16-point and alternate forms → canonical 8-cardinal
_NORMALIZE_MAP: dict[str, str] = {
    "NNE": "NE",
    "ENE": "NE",
    "ESE": "SE",
    "SSE": "SE",
    "SSW": "SW",
    "WSW": "SW",
    "WNW": "NW",
    "NNW": "NW",
}


def degrees_to_cardinal_8(deg: float) -> str:
    """Convert degrees (0-359) to 8-point cardinal direction.

    Args:
        deg: Wind direction in degrees (meteorological convention).

    Returns:
        One of N, NE, E, SE, S, SW, W, NW.
    """
    return CARDINAL_8[round(deg / 45) % 8]


def normalize_cardinal_8(card: str) -> str:
    """Normalize any cardinal string to 8-point canonical form.

    Handles 16-point (NNE, WSW, etc.) → 8-point (NE, SW, etc.).
    Already-canonical values pass through unchanged.

    Args:
        card: Cardinal direction string (any case).

    Returns:
        Canonical 8-point cardinal string.
    """
    upper = card.upper().strip()
    return _NORMALIZE_MAP.get(upper, upper)
