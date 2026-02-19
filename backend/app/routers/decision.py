"""FishCast decision endpoint.

GET /decision/today — Decision Output v1 (API_CONTRACTS.md full schema).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from app.models.spot import SpotOut
from app.services.decision import generate_decision
from app.services.solunar import compute_solunar
from app.services.weather import get_weather

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/decision/today",
    summary="Günlük karar çıktısı",
    description="Decision Output v1: 3 bölge önerisi, bestWindows, türler, teknikler, whyTR.",
)
async def decision_today(request: Request) -> dict[str, Any]:
    """Günlük karar çıktısını döner (Decision Output v1).

    API_CONTRACTS.md § GET /decision/today full schema ile uyumlu.

    Returns:
        DecisionResponse dict.
    """
    spots: list[SpotOut] = request.app.state.spots
    rules = getattr(request.app.state, "rules", [])
    stormglass_key = getattr(request.app.state, "stormglass_api_key", None)

    # Fetch weather and solunar
    weather = await get_weather(stormglass_api_key=stormglass_key)
    solunar_data = compute_solunar()

    # Generate decision
    decision = generate_decision(
        spots=spots,
        weather=weather,
        solunar_data=solunar_data,
        rules=rules,
    )

    return decision
