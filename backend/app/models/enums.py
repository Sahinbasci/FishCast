"""FishCast canonical enum definitions.

All enums sourced from ARCHITECTURE.md § Enum Tanımları.
These are the SINGLE SOURCE OF TRUTH for enum values across the backend.
"""

from enum import Enum


class SpeciesId(str, Enum):
    """Balık türü kimliği. Tier 1 (5) + Tier 2 (4)."""
    istavrit = "istavrit"
    cinekop = "cinekop"
    sarikanat = "sarikanat"
    palamut = "palamut"
    karagoz = "karagoz"
    lufer = "lufer"
    levrek = "levrek"
    kolyoz = "kolyoz"
    mirmir = "mirmir"


class TechniqueId(str, Enum):
    """Avlanma tekniği kimliği (7 teknik)."""
    capari = "capari"
    kursun_arkasi = "kursun_arkasi"
    spin = "spin"
    lrf = "lrf"
    surf = "surf"
    yemli_dip = "yemli_dip"
    shore_jig = "shore_jig"


class BaitId(str, Enum):
    """Yem türü kimliği."""
    istavrit_fileto = "istavrit_fileto"
    krace_fileto = "krace_fileto"
    hamsi_fileto = "hamsi_fileto"
    karides = "karides"
    midye = "midye"
    deniz_kurdu = "deniz_kurdu"
    boru_kurdu = "boru_kurdu"
    mamun = "mamun"


class Shore(str, Enum):
    """Kıyı yakası."""
    european = "european"
    anatolian = "anatolian"


class RegionId(str, Enum):
    """Bölge kimliği (3 bölge)."""
    anadolu = "anadolu"
    avrupa = "avrupa"
    city_belt = "city_belt"


class RegionGroup(str, Enum):
    """Bölge grubu."""
    bosporus_core = "bosporus_core"
    city_belt = "city_belt"
    marmara_kiyi = "marmara_kiyi"


class SpeciesMode(str, Enum):
    """Tür davranış modu."""
    chasing = "chasing"
    selective = "selective"
    holding = "holding"


class DataQuality(str, Enum):
    """Veri kalitesi durumu (enum string, object degil)."""
    live = "live"
    cached = "cached"
    fallback = "fallback"


class PressureTrend(str, Enum):
    """Basınç trendi."""
    falling = "falling"
    rising = "rising"
    stable = "stable"


class DataSourceStatus(str, Enum):
    """Veri kaynağı durumu."""
    ok = "ok"
    cached = "cached"
    fallback = "fallback"
    error = "error"


class SeasonStatus(str, Enum):
    """Sezon durumu."""
    peak = "peak"
    active = "active"
    closed = "closed"


class CrowdRisk(str, Enum):
    """Kalabalık riski."""
    low = "low"
    medium = "medium"
    high = "high"


class CoordAccuracy(str, Enum):
    """Koordinat doğruluğu."""
    approx = "approx"
    verified = "verified"


class WindCardinal(str, Enum):
    """Rüzgar yönü (8 ana yön)."""
    N = "N"
    NE = "NE"
    E = "E"
    SE = "SE"
    S = "S"
    SW = "SW"
    W = "W"
    NW = "NW"
