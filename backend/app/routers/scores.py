"""FishCast scores endpoints.

GET /scores/today — tüm mera özet skorları.
GET /scores/spot/{spotId} — detaylı skor (speciesScores MAP→ARRAY transform).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app.models.spot import SpotOut
from app.services.decision import SPECIES_NAME_TR, compute_spot_scores
from app.services.solunar import compute_solunar
from app.services.weather import get_weather

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_scores_for_spots(
    spots: list[SpotOut],
    rules: list[dict[str, Any]],
    stormglass_key: str | None = None,
    scoring_config: dict[str, Any] | None = None,
    seasonality_config: dict[str, Any] | None = None,
    offline_mode: bool = False,
) -> tuple[dict[str, Any], Any, dict[str, Any]]:
    """Tum mera'lar icin weather + solunar + scores hesaplar."""
    weather = await get_weather(stormglass_api_key=stormglass_key, offline_mode=offline_mode)
    solunar_data = compute_solunar()
    now = datetime.now()

    spot_results: dict[str, dict[str, Any]] = {}
    for spot in spots:
        spot_results[spot.id] = compute_spot_scores(
            spot=spot,
            weather=weather,
            solunar_data=solunar_data,
            rules=rules,
            now=now,
            scoring_config=scoring_config,
            seasonality_config=seasonality_config,
        )

    return spot_results, weather, solunar_data


@router.get(
    "/scores/today",
    summary="Bugünün tüm mera özet skorları",
    description="16 meranın overallScore, noGo durumu ve tür skorlarını döner.",
)
async def scores_today(request: Request) -> list[dict[str, Any]]:
    """Tüm meraların bugünkü özet skorlarını döner.

    Returns:
        Mera özet skorları listesi.
    """
    spots: list[SpotOut] = request.app.state.spots
    rules = getattr(request.app.state, "rules", [])
    stormglass_key = getattr(request.app.state, "stormglass_api_key", None)

    scoring_config = getattr(request.app.state, "scoring_config", None)
    seasonality_config = getattr(request.app.state, "seasonality_config", None)

    offline_mode = getattr(request.app.state, "offline_mode", False)
    spot_results, weather, _ = await _get_scores_for_spots(
        spots, rules, stormglass_key,
        scoring_config=scoring_config,
        seasonality_config=seasonality_config,
        offline_mode=offline_mode,
    )

    result: list[dict[str, Any]] = []
    for spot in spots:
        sr = spot_results[spot.id]
        result.append({
            "spotId": spot.id,
            "spotName": spot.name,
            "regionId": spot.region_id.value,
            "overallScore": sr["overallScore"],
            "noGo": sr["noGo"],
            "weather": weather.to_dict(),
            "topSpecies": _get_top_species(sr["speciesScores"]),
        })

    return result


def _get_top_species(species_scores: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    """speciesScores'dan top N türü döner (score DESC).

    Args:
        species_scores: Species scores map.
        limit: Maksimum sayı.

    Returns:
        Top türler listesi.
    """
    sorted_species = sorted(
        species_scores.items(),
        key=lambda x: (-x[1]["score"], x[0]),
    )[:limit]

    return [
        {
            "speciesId": sp_id,
            "speciesNameTR": SPECIES_NAME_TR.get(sp_id, sp_id),
            "score0to100": data["score"],
            "mode": data["mode"],
        }
        for sp_id, data in sorted_species
    ]


@router.get(
    "/scores/spot/{spot_id}",
    summary="Tek mera detaylı skoru",
    description="Belirtilen meranın detaylı skor bilgisini döner. speciesScores ARRAY olarak.",
)
async def score_spot_detail(
    request: Request,
    spot_id: str,
    trace_level: str = Query("none", alias="traceLevel", pattern="^(none|minimal|full)$"),
) -> dict[str, Any]:
    """Tek bir meranın detaylı skorunu döner.

    speciesScores MAP → ARRAY transform burada yapılır.
    Sort: score DESC, speciesId ASC (tie-break).

    Args:
        spot_id: Mera kimliği.
        trace_level: Trace detail level (none|minimal|full).

    Returns:
        Detaylı skor dict'i.

    Raises:
        HTTPException: Mera bulunamazsa 404.
    """
    spots: list[SpotOut] = request.app.state.spots
    rules = getattr(request.app.state, "rules", [])
    stormglass_key = getattr(request.app.state, "stormglass_api_key", None)

    spot = next((s for s in spots if s.id == spot_id), None)
    if spot is None:
        raise HTTPException(status_code=404, detail=f"Mera bulunamadı: {spot_id}")

    scoring_config = getattr(request.app.state, "scoring_config", None)
    seasonality_config = getattr(request.app.state, "seasonality_config", None)

    # v1.3.2: Trace guard — block full trace unless ALLOW_TRACE_FULL=true
    allow_full = getattr(request.app.state, "allow_trace_full", False)
    applied_level = trace_level if trace_level != "full" or allow_full else "minimal"

    offline_mode = getattr(request.app.state, "offline_mode", False)
    weather = await get_weather(stormglass_api_key=stormglass_key, offline_mode=offline_mode)
    solunar_data = compute_solunar()
    now = datetime.now()

    result = compute_spot_scores(
        spot=spot,
        weather=weather,
        solunar_data=solunar_data,
        rules=rules,
        now=now,
        scoring_config=scoring_config,
        seasonality_config=seasonality_config,
        trace_level=applied_level,
    )

    # MAP → ARRAY Transform (API_CONTRACTS.md § MAP vs ARRAY Transform)
    # Sort: score DESC, speciesId ASC (tie-break)
    species_array: list[dict[str, Any]] = []
    for sp_id, sp_data in sorted(
        result["speciesScores"].items(),
        key=lambda x: (-x[1]["score"], x[0]),
    ):
        species_array.append({
            "speciesId": sp_id,
            "speciesNameTR": SPECIES_NAME_TR.get(sp_id, sp_id),
            "score0to100": sp_data["score"],
            "suppressedByNoGo": sp_data["suppressedByNoGo"],
            "bestTime": sp_data.get("bestTime"),
            "confidence0to1": sp_data["confidence0to1"],
            "seasonStatus": sp_data["seasonStatus"],
            "mode": sp_data["mode"],
            "recommendedTechniques": sp_data.get("recommendedTechniques", []),
            "avoidTechniques": sp_data.get("avoidTechniques", []),
            "breakdown": sp_data.get("breakdown"),
        })

    response: dict[str, Any] = {
        "spotId": spot_id,
        "date": now.strftime("%Y-%m-%d"),
        "meta": {
            "contractVersion": "1.3",
            "generatedAt": now.isoformat(),
            "timezone": "Europe/Istanbul",
        },
        "overallScore": result["overallScore"],
        "noGo": result["noGo"],
        "weather": weather.to_dict(),
        "solunar": solunar_data,
        "speciesScores": species_array,
        "activeRules": result["activeRules"],
    }
    if "trace" in result:
        response["trace"] = result["trace"]

    # v1.3.2: If trace was downgraded, indicate in meta
    if applied_level != trace_level:
        response["meta"]["traceLevelRequested"] = trace_level
        response["meta"]["traceLevelApplied"] = applied_level

    return response
