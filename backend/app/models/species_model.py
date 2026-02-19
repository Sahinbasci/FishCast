"""FishCast species (tür) Pydantic models.

Aligned with API_CONTRACTS.md canonical types and INSTRUCTIONS.md § MVP Tür Listesi.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SpeciesId, TechniqueId


class SeasonInfo(BaseModel):
    """Sezon bilgisi.

    Attributes:
        months: Aktif aylar (1-12).
        peak: Pik aylar (1-12).
    """
    months: list[int] = Field(min_length=1)
    peak: list[int]


class TempRange(BaseModel):
    """İdeal su sıcaklığı aralığı (°C).

    Attributes:
        min: Minimum ideal sıcaklık.
        max: Maksimum ideal sıcaklık.
    """
    min: float
    max: float


class TechniqueRating(BaseModel):
    """Teknik ve etkinlik derecesi.

    Attributes:
        id: Teknik kimliği.
        name: Teknik adı (Türkçe).
        rating: Etkinlik derecesi (1=düşük, 2=orta, 3=yüksek).
    """
    id: TechniqueId
    name: str
    rating: int = Field(ge=1, le=3)


class BaitInfo(BaseModel):
    """Yem bilgisi.

    Attributes:
        id: Yem kimliği.
        name: Yem adı (Türkçe).
    """
    id: str
    name: str


class SpeciesOut(BaseModel):
    """API response modeli: tek bir balık türü.

    Attributes:
        id: Tür kimliği (enum).
        name: Türkçe ad.
        tier: 1=skorlanır, 2=sadece bilgi.
        season: Sezon ayları ve pik dönem.
        ideal_temp: İdeal su sıcaklığı aralığı (°C).
        size: Yaygın boy aralığı.
        legal_min_size: Yasal minimum boy (varsa).
        primary_techniques: Önerilen teknikler ve etkinlik dereceleri.
        best_baits: En iyi yemler.
        tips: Avlanma ipuçları (Türkçe).
    """
    model_config = ConfigDict(populate_by_name=True)

    id: SpeciesId
    name: str
    tier: int = Field(ge=1, le=2)
    season: SeasonInfo
    ideal_temp: TempRange = Field(alias="idealTemp")
    size: str
    legal_min_size: Optional[str] = Field(alias="legalMinSize", default=None)
    primary_techniques: list[TechniqueRating] = Field(alias="primaryTechniques")
    best_baits: list[BaitInfo] = Field(alias="bestBaits")
    tips: str
