"""FishCast techniques (teknikler) endpoints.

7 avlanma tekniğini listeler.
Veri kaynağı: startup'ta yüklenen techniques.json (app.state).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.models.technique import TechniqueOut

router = APIRouter()


@router.get(
    "/techniques",
    response_model=list[TechniqueOut],
    summary="Tüm teknikleri listele",
    description="7 avlanma tekniğini döner.",
)
async def list_techniques(request: Request) -> list[TechniqueOut]:
    """Tüm avlanma tekniklerini döner.

    Args:
        request: FastAPI request (app.state erişimi için).

    Returns:
        Teknik listesi.
    """
    return request.app.state.techniques


@router.get(
    "/techniques/{technique_id}",
    response_model=TechniqueOut,
    summary="Tek teknik detayı",
    description="Belirtilen ID'ye sahip tekniğin detaylarını döner.",
)
async def get_technique(request: Request, technique_id: str) -> TechniqueOut:
    """Tek bir tekniğin detayını döner.

    Args:
        request: FastAPI request (app.state erişimi için).
        technique_id: Teknik kimliği (örn: "spin", "lrf").

    Returns:
        Teknik detayı.

    Raises:
        HTTPException: Teknik bulunamazsa 404.
    """
    techniques: list[TechniqueOut] = request.app.state.techniques

    for technique in techniques:
        if technique.id == technique_id:
            return technique

    raise HTTPException(
        status_code=404, detail=f"Teknik bulunamadı: {technique_id}"
    )
