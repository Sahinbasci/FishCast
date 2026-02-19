"""FishCast species (türler) endpoints.

9 balık türünü (5 Tier 1 + 4 Tier 2) listeler ve filtreleme imkanı sağlar.
Veri kaynağı: startup'ta yüklenen species.json (app.state).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.models.species_model import SpeciesOut

router = APIRouter()


@router.get(
    "/species",
    response_model=list[SpeciesOut],
    summary="Tüm türleri listele",
    description="9 balık türünü döner. tier parametresi ile filtrelenebilir.",
)
async def list_species(
    request: Request,
    tier: Optional[int] = Query(
        None, ge=1, le=2, description="Tier filtresi (1=skorlanır, 2=sadece bilgi)"
    ),
) -> list[SpeciesOut]:
    """Tüm balık türlerini döner, opsiyonel tier filtresi ile.

    Args:
        request: FastAPI request (app.state erişimi için).
        tier: Tier filtresi (opsiyonel, 1 veya 2).

    Returns:
        Filtrelenmiş tür listesi.
    """
    species_list: list[SpeciesOut] = request.app.state.species

    if tier is not None:
        return [s for s in species_list if s.tier == tier]

    return species_list


@router.get(
    "/species/{species_id}",
    response_model=SpeciesOut,
    summary="Tek tür detayı",
    description="Belirtilen ID'ye sahip balık türünün detaylarını döner.",
)
async def get_species(request: Request, species_id: str) -> SpeciesOut:
    """Tek bir balık türünün detayını döner.

    Args:
        request: FastAPI request (app.state erişimi için).
        species_id: Tür kimliği (örn: "cinekop", "karagoz").

    Returns:
        Tür detayı.

    Raises:
        HTTPException: Tür bulunamazsa 404.
    """
    species_list: list[SpeciesOut] = request.app.state.species

    for species in species_list:
        if species.id == species_id:
            return species

    raise HTTPException(
        status_code=404, detail=f"Tür bulunamadı: {species_id}"
    )
