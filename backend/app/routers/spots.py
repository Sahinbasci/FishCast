"""FishCast spots (meralar) endpoints.

16 Istanbul kıyı merasını listeler ve filtreleme imkanı sağlar.
Veri kaynağı: startup'ta yüklenen spots.json (app.state).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.models.enums import RegionId, Shore
from app.models.spot import SpotOut

router = APIRouter()


@router.get(
    "/spots",
    response_model=list[SpotOut],
    summary="Tüm meraları listele",
    description="16 Istanbul kıyı merasını döner. regionId ve shore ile filtrelenebilir.",
)
async def list_spots(
    request: Request,
    region_id: Optional[RegionId] = Query(
        None, alias="regionId", description="Bölge filtresi (anadolu/avrupa/city_belt)"
    ),
    shore: Optional[Shore] = Query(
        None, description="Kıyı yakası filtresi (european/anatolian)"
    ),
) -> list[SpotOut]:
    """Tüm meraları döner, opsiyonel filtrelerle.

    Args:
        request: FastAPI request (app.state erişimi için).
        region_id: Bölge filtresi (opsiyonel).
        shore: Kıyı yakası filtresi (opsiyonel).

    Returns:
        Filtrelenmiş mera listesi.
    """
    spots: list[SpotOut] = request.app.state.spots

    result = spots
    if region_id is not None:
        result = [s for s in result if s.region_id == region_id]
    if shore is not None:
        result = [s for s in result if s.shore == shore]

    return result


@router.get(
    "/spots/{spot_id}",
    response_model=SpotOut,
    summary="Tek mera detayı",
    description="Belirtilen ID'ye sahip meranın detaylarını döner.",
)
async def get_spot(request: Request, spot_id: str) -> SpotOut:
    """Tek bir meranın detayını döner.

    Args:
        request: FastAPI request (app.state erişimi için).
        spot_id: Mera kimliği (örn: "bebek", "galata").

    Returns:
        Mera detayı.

    Raises:
        HTTPException: Mera bulunamazsa 404.
    """
    spots: list[SpotOut] = request.app.state.spots

    for spot in spots:
        if spot.id == spot_id:
            return spot

    raise HTTPException(status_code=404, detail=f"Mera bulunamadı: {spot_id}")
