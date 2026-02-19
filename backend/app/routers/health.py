"""FishCast health check endpoint.

Provides system status, engine version, and ruleset information.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response modeli.

    Attributes:
        status: Sistem durumu ("ok").
        engine_version: Skor motoru versiyonu.
        ruleset_version: Kural seti versiyonu (YYYYMMDD.N formatı).
        rules_count: Toplam kural sayısı.
    """
    status: str = Field(description="Sistem durumu")
    engine_version: str = Field(
        alias="engineVersion", description="Skor motoru versiyonu"
    )
    ruleset_version: str = Field(
        alias="rulesetVersion", description="Kural seti versiyonu"
    )
    rules_count: int = Field(
        alias="rulesCount", description="Toplam kural sayısı"
    )

    model_config = {"populate_by_name": True}


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Sistem sağlık kontrolü",
    description="API durumunu, motor ve kural seti versiyonlarını döner.",
)
async def health_check() -> HealthResponse:
    """Sistem sağlık kontrolü endpoint'i.

    Returns:
        HealthResponse: Sistem durumu, motor versiyonu, kural seti bilgisi.
    """
    return HealthResponse(
        status="ok",
        engine_version="1.0.0",
        ruleset_version="20260219.1",
        rules_count=24,
    )
