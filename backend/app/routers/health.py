"""FishCast health check endpoint.

Provides system status, engine version, and ruleset information.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Request

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response modeli."""
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
    active_rules: int = Field(
        alias="activeRules", description="Aktif kural sayısı"
    )
    disabled_rules: int = Field(
        alias="disabledRules", description="Disabled kural sayısı"
    )
    contract_version: str = Field(
        alias="contractVersion", description="API contract versiyonu"
    )

    model_config = {"populate_by_name": True}


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Sistem sağlık kontrolü",
    description="API durumunu, motor ve kural seti versiyonlarını döner.",
)
async def health_check(request: Request) -> HealthResponse:
    """Sistem sağlık kontrolü endpoint'i."""
    rules = getattr(request.app.state, "rules", [])
    active = sum(1 for r in rules if r.get("enabled", True))
    disabled = len(rules) - active
    return HealthResponse(
        status="ok",
        engine_version="1.0.0",
        ruleset_version="20260223.1",
        rules_count=len(rules),
        active_rules=active,
        disabled_rules=disabled,
        contract_version="1.4.2",
    )
