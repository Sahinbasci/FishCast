"""FishCast spot (mera) Pydantic models.

Aligned with ARCHITECTURE.md § Spots Dataset and API_CONTRACTS.md canonical types.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    CoordAccuracy,
    CrowdRisk,
    RegionGroup,
    RegionId,
    Shore,
    SpeciesId,
    TechniqueId,
)


class WindExposure(BaseModel):
    """Rüzgar maruziyeti bilgisi.

    Attributes:
        onshore_dirs_deg: Kıyıya vuran rüzgar yönleri (derece).
        offshore_dirs_deg: Kıyıdan esen rüzgar yönleri (derece).
        shelter_score_0to1: Korunma skoru (0=açık, 1=tamamen korunaklı).
    """
    model_config = ConfigDict(populate_by_name=True)

    onshore_dirs_deg: list[int] = Field(alias="onshoreDirsDeg")
    offshore_dirs_deg: list[int] = Field(alias="offshoreDirsDeg")
    shelter_score_0to1: float = Field(
        alias="shelterScore0to1", ge=0.0, le=1.0
    )


class SpotOut(BaseModel):
    """API response modeli: tek bir mera (spot).

    Tüm field'lar ARCHITECTURE.md § Spots Dataset ile uyumludur.
    JSON camelCase alias'ları ile serialize edilir.
    """
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    lat: float
    lng: float
    accuracy: CoordAccuracy
    shore: Shore
    region_id: RegionId = Field(alias="regionId")
    region_group: RegionGroup = Field(alias="regionGroup")
    pelagic_corridor: bool = Field(alias="pelagicCorridor")
    urban_crowd_risk: CrowdRisk = Field(alias="urbanCrowdRisk")
    primary_species: list[SpeciesId] = Field(alias="primarySpecies")
    primary_techniques: list[TechniqueId] = Field(alias="primaryTechniques")
    technique_bias: list[TechniqueId] = Field(alias="techniqueBias")
    features: list[str]
    depth: str
    current_exposure: str = Field(alias="currentExposure")
    wind_exposure: WindExposure = Field(alias="windExposure")
    special_rules: list[str] = Field(alias="specialRules")
    description: Optional[str] = None
