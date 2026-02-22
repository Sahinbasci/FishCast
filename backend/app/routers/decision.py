"""FishCast decision endpoint.

GET /decision/today — Decision Output v1 (API_CONTRACTS.md full schema).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query, Request

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
async def decision_today(
    request: Request,
    trace_level: str = Query("none", alias="traceLevel", pattern="^(none|minimal|full)$"),
) -> dict[str, Any]:
    """Günlük karar çıktısını döner (Decision Output v1).

    API_CONTRACTS.md § GET /decision/today full schema ile uyumlu.

    Args:
        trace_level: Trace detail level (none|minimal|full).

    Returns:
        DecisionResponse dict.
    """
    spots: list[SpotOut] = request.app.state.spots
    rules = getattr(request.app.state, "rules", [])
    stormglass_key = getattr(request.app.state, "stormglass_api_key", None)

    # Fetch weather and solunar
    weather = await get_weather(stormglass_api_key=stormglass_key)
    solunar_data = compute_solunar()

    # v1.3: Pass configs for DI
    scoring_config = getattr(request.app.state, "scoring_config", None)
    seasonality_config = getattr(request.app.state, "seasonality_config", None)

    # v1.3.2: Trace guard — block full trace unless ALLOW_TRACE_FULL=true
    allow_full = getattr(request.app.state, "allow_trace_full", False)
    applied_level = trace_level if trace_level != "full" or allow_full else "minimal"

    # Generate decision
    decision = generate_decision(
        spots=spots,
        weather=weather,
        solunar_data=solunar_data,
        rules=rules,
        scoring_config=scoring_config,
        seasonality_config=seasonality_config,
        trace_level=applied_level,
    )

    # v1.3.2: If trace was downgraded, indicate in meta
    if applied_level != trace_level:
        decision["meta"]["traceLevelRequested"] = trace_level
        decision["meta"]["traceLevelApplied"] = applied_level

    return decision
