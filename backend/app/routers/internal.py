"""FishCast internal endpoints.

POST /internal/calculate-scores — Cloud Scheduler cron trigger.
Tüm 16 mera × 5 Tier1 tür hesaplar, Firestore'a yazar.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request

from app.models.spot import SpotOut
from app.services.decision import compute_spot_scores, generate_decision
from app.services.firebase import get_firestore_db
from app.services.solunar import compute_solunar
from app.services.weather import get_weather

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/internal/calculate-scores",
    summary="Skor hesaplama cron trigger",
    description="Tüm 16 mera için skorları hesaplar ve Firestore'a yazar. Cloud Scheduler 3h'te bir çağırır.",
)
async def calculate_scores(request: Request) -> dict[str, Any]:
    """Tüm meraların skorlarını hesaplar ve Firestore'a yazar.

    1. Weather + Solunar verisi topla
    2. Her mera için: tür skorları + mode derivation
    3. Firestore: scores/{date}/{spotId}
    4. Decision doc: decisions/{date}

    Returns:
        Hesaplama sonuç özeti.
    """
    spots: list[SpotOut] = request.app.state.spots
    rules = getattr(request.app.state, "rules", [])
    stormglass_key = getattr(request.app.state, "stormglass_api_key", None)

    now = datetime.now(tz=timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    logger.info("Skor hesaplama başladı: %s — %d mera", date_str, len(spots))

    # Fetch weather and solunar
    weather = await get_weather(stormglass_api_key=stormglass_key)
    solunar_data = compute_solunar()

    # Calculate scores for all spots
    spot_results: dict[str, dict[str, Any]] = {}
    for spot in spots:
        spot_results[spot.id] = compute_spot_scores(
            spot=spot,
            weather=weather,
            solunar_data=solunar_data,
            rules=rules,
            now=now,
        )

    # Write to Firestore
    db = get_firestore_db()
    firestore_written = 0

    if db:
        try:
            # Write score documents: scores/{date}/{spotId}
            for spot in spots:
                result = spot_results[spot.id]
                doc_ref = db.collection("scores").document(date_str).collection("spots").document(spot.id)
                doc_ref.set({
                    "spotId": spot.id,
                    "date": date_str,
                    "meta": {
                        "contractVersion": "1.2",
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
