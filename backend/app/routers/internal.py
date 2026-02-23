"""FishCast internal endpoints.

POST /internal/calculate-scores — Cloud Scheduler cron trigger.
GET /_meta — Deploy guard: runtime config inspection.
Tüm 16 mera × 5 Tier1 tür hesaplar, Firestore'a yazar.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Request

from app.models.spot import SpotOut
from app.services.decision import compute_spot_scores, generate_decision
from app.services.firebase import get_firestore_db
from app.services.solunar import compute_solunar
from app.services.weather import get_weather

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Internal auth helper ---
_INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "")


def _verify_internal_auth(x_internal_secret: Optional[str]) -> None:
    """Verify shared secret for internal endpoints.

    If INTERNAL_SECRET env is set, requests MUST provide matching header.
    If INTERNAL_SECRET is empty (local dev), auth is skipped with a warning.
    """
    if not _INTERNAL_SECRET:
        logger.warning("INTERNAL_SECRET not set — internal endpoints unprotected (dev mode)")
        return
    if x_internal_secret != _INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Internal-Secret")


@router.post(
    "/internal/calculate-scores",
    summary="Skor hesaplama cron trigger",
    description="Tüm 16 mera için skorları hesaplar ve Firestore'a yazar. Cloud Scheduler 3h'te bir çağırır.",
)
async def calculate_scores(
    request: Request,
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret"),
) -> dict[str, Any]:
    """Tüm meraların skorlarını hesaplar ve Firestore'a yazar.

    1. Weather + Solunar verisi topla
    2. Her mera için: tür skorları + mode derivation
    3. Firestore: scores/{date}/spots/{spotId}
    4. Decision doc: decisions/{date}

    Returns:
        Hesaplama sonuç özeti.
    """
    _verify_internal_auth(x_internal_secret)

    spots: list[SpotOut] = request.app.state.spots
    rules = getattr(request.app.state, "rules", [])
    stormglass_key = getattr(request.app.state, "stormglass_api_key", None)

    now = datetime.now(tz=timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    logger.info("Skor hesaplama başladı: %s — %d mera", date_str, len(spots))

    # Fetch weather and solunar (pass Firestore db for Stormglass cache fallback)
    db = get_firestore_db()
    weather = await get_weather(stormglass_api_key=stormglass_key, firestore_db=db)
    solunar_data = compute_solunar()

    # v1.3: Pass configs for DI
    scoring_config = getattr(request.app.state, "scoring_config", None)
    seasonality_config = getattr(request.app.state, "seasonality_config", None)

    # Calculate scores for all spots
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

    # Write to Firestore
    db = get_firestore_db()
    firestore_written = 0

    if db:
        try:
            # Write score documents: scores/{date}/spots/{spotId}
            for spot in spots:
                result = spot_results[spot.id]
                doc_ref = db.collection("scores").document(date_str).collection("spots").document(spot.id)
                doc_ref.set({
                    "spotId": spot.id,
                    "date": date_str,
                    "meta": {
                        "contractVersion": "1.4.2",
                        "generatedAt": now.isoformat(),
                        "timezone": "Europe/Istanbul",
                    },
                    "overallScore": result["overallScore"],
                    "noGo": result["noGo"],
                    "weather": weather.to_dict(),
                    "solunar": solunar_data,
                    "speciesScores": result["speciesScores"],
                    "activeRules": result["activeRules"],
                })
                firestore_written += 1

            # Generate and write decision doc
            decision = generate_decision(
                spots=spots,
                weather=weather,
                solunar_data=solunar_data,
                rules=rules,
                now=now,
                scoring_config=scoring_config,
                seasonality_config=seasonality_config,
            )
            db.collection("decisions").document(date_str).set(decision)
            firestore_written += 1

            logger.info("Firestore'a %d doküman yazıldı", firestore_written)
        except Exception as e:
            logger.error("Firestore yazma hatası: %s", e)

    logger.info("Skor hesaplama tamamlandı: %d mera işlendi", len(spots))

    return {
        "status": "completed",
        "date": date_str,
        "spotsProcessed": len(spots),
        "firestoreWritten": firestore_written,
        "dataQuality": weather.data_quality.value,
        "dataIssues": weather.data_issues,
    }


@router.get(
    "/_meta",
    summary="Deploy meta bilgisi",
    description="Calisma ortami bilgisi. Deploy dogrulamasi icin kullanilir.",
)
async def get_meta(request: Request) -> dict[str, Any]:
    """Runtime configuration for deploy verification.

    Returns offlineMode, allowTraceFull, rulesetVersion, rulesCount, buildSha.
    Used by deploy.yml to assert production safety invariants.
    """
    rules = getattr(request.app.state, "rules", [])
    active_rules = [r for r in rules if r.get("enabled", True)]
    disabled_rules = [r for r in rules if not r.get("enabled", True)]
    return {
        "offlineMode": getattr(request.app.state, "offline_mode", False),
        "allowTraceFull": getattr(request.app.state, "allow_trace_full", False),
        "rulesetVersion": "20260223.1",
        "rulesCount": len(rules),
        "activeRulesCount": len(active_rules),
        "disabledRulesCount": len(disabled_rules),
        "disabledRuleIds": [r["id"] for r in disabled_rules],
        "buildSha": os.getenv("GIT_SHA", "unknown"),
        "dataSourceAvailability": {
            "openMeteo": True,
            "stormglass": bool(getattr(request.app.state, "stormglass_api_key", None)),
            "rainData": False,
            "currentSpeed": False,
            "windHistory48h": False,
        },
    }
