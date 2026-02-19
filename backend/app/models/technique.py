"""FishCast technique (teknik) Pydantic models.

Aligned with INSTRUCTIONS.md § Teknikler and API_CONTRACTS.md canonical types.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SpeciesId, TechniqueId


class TechniqueOut(BaseModel):
    """API response modeli: tek bir avlanma tekniği.

    Attributes:
        id: Teknik kimliği (enum).
        name: Türkçe ad.
        description: Teknik açıklaması.
        target_species: Hedef türler.
        tips: Kullanım ipuçları (Türkçe).
    """
    model_config = ConfigDict(populate_by_name=True)

    id: TechniqueId
    name: str
    description: str
    target_species: list[SpeciesId] = Field(alias="targetSpecies")
    tips: str
